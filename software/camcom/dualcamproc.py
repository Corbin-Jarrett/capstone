# Copyright (C) Meridian Innovation Ltd. Hong Kong, 2020. All rights reserved.
#
import sys
# sys.path.append("/home/test/myenv/lib/python3.11/site-packages")
import os
import signal
import time
import logging
import serial
import numpy as np
from picamera2 import Picamera2
import apriltag
import shapely
import multiprocessing
import cv2 as cv

from senxor.mi48 import MI48, format_header, format_framestats
from senxor.utils import data_to_frame, remap, cv_filter,\
                         cv_render, RollingAverageFilter,\
                         connect_senxor

# This will enable mi48 logging debug messages
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))

# # define a signal handler to ensure clean closure upon CTRL+C
# # or kill from terminal
# def signal_handler(sig, frame):
#     """Ensure clean exit in case of SIGINT or SIGTERM"""
#     # logger.info("Exiting due to SIGINT or SIGTERM")
#     mi48.stop()
#     picam2.stop()
#     cv.destroyAllWindows()
#     # logger.info("Done.")
#     sys.exit(0)

# # Define the signals that should be handled to ensure clean exit
# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)

# change this to false if not interested in the image
GUI_THERMAL = True
GUI_NOIR = True

# set cv_filter parameters
par = {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}

# threshold temperatures
hand_temp = [23,35]
hazard_temp = 40

dminav = RollingAverageFilter(N=10)
dmaxav = RollingAverageFilter(N=10)

# set up serial connection to ESP
ser = serial.Serial ("/dev/ttyS0", 115200)      #Open port with baud rate
# function to write data to ESP. user_distance is in cm
def writeSerial(signal, user_distance):
    delim = ', '
    threshold_1 = 30 # needs to be minimum 30
    threshold_2 = 5

    message = str(signal) + delim + str(user_distance) + delim + str(threshold_1) + delim + str(threshold_2) + '\r'
    #transmit data serially 
    ser.write(bytes(message, 'utf8'))  #create byte object with data string

# complete = multiprocessing.Value('i', 0)

def noircapture():
    global picam2
    # initialize camera
    picam2 = Picamera2()
    # configurations (see documentation for details)
    # check and choose a mode
    # print(picam2.sensor_modes)
    mode = picam2.sensor_modes[3] # 3 or 7 are best
    video_config = picam2.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']}, main={'format': 'BGR888'})
    # start camera
    picam2.start(config=video_config)

    while True:
        try:
            # capture next frame as 3D numpy array
            frame = picam2.capture_array()

            # identify april tag(s)
            gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            # define the AprilTags detector options and then detect AprilTags
            # print("[INFO] detecting AprilTags...")
            detector = apriltag.Detector()
            detections = detector.detect(gray)
            print("[INFO] {} total AprilTags detected".format(len(detections)))
            # print("[INFO] {} total AprilTags detected".format(0))

            if GUI_NOIR:
                cv.imshow("noir", frame) # display frame
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break
        except KeyboardInterrupt:
            break
    
    # stop picam once while loop finished
    picam2.stop()



def thermalcapture():
    global mi48
    # Make an instance of the MI48, attaching USB for 
    # both control and data interface.
    # can try connect_senxor(src='/dev/ttyS3') or similar if default cannot be found
    mi48, connected_port, port_names = connect_senxor()

    # print out camera info
    # logger.info('Camera info:')
    # logger.info(mi48.camera_info)

    # set desired FPS
    STREAM_FPS = 20
    mi48.set_fps(STREAM_FPS)

    # see if filtering is available in MI48 and set it up
    mi48.disable_filter(f1=True, f2=True, f3=True)
    mi48.set_filter_1(85)
    mi48.enable_filter(f1=True, f2=False, f3=False, f3_ks_5=False)
    mi48.set_offset_corr(0.0)

    mi48.set_sens_factor(100)
    mi48.get_sens_factor()

    # initiate continuous frame acquisition
    with_header = True
    mi48.start(stream=True, with_header=with_header)


    while True:
        try:
            # THERMAL STUFF
            hand_found = False

            # need to sync reading between threads
            data, header = mi48.read()

            if data is None:
                # logger.critical('NONE data received instead of GFRA')
                print("NO DATA FROM THERMAL CAMERA")
                mi48.stop()

            #regular image
            min_temp = dminav(data.min())  # + 1.5
            max_temp = dmaxav(data.max())  # - 1.5
            frame = data_to_frame(data, (80,62), hflip=True)
            # frame2 = np.clip(frame, min_temp, max_temp)
            filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                                use_bilat=True, use_nlm=False)
            
            #hand
            # convert to grayscale temp for threshold, linear transformation
            thresh_low = (hand_temp[0]-min_temp)/(max_temp-min_temp)*(255-min_temp)
            thresh_high = (hand_temp[1]-min_temp)/(max_temp-min_temp)*(255-min_temp)

            ret, thresh_image_hand_lower = cv.threshold(remap(frame), thresh_low, 255, cv.THRESH_BINARY)
            ret, thresh_image_hand_upper = cv.threshold(remap(frame), thresh_high, 255, cv.THRESH_BINARY_INV)

            thresh_image_hand = np.logical_and(thresh_image_hand_lower,thresh_image_hand_upper).astype(np.uint8)
            contours_hand, ret = cv.findContours(thresh_image_hand, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            # Loop through the contours and filter based on area to detect the hand
            contour_max = []
            max_area = 25
            for contour in contours_hand:
                area = cv.contourArea(contour)
                #print(f"Contour area: {area}")  # Debugging line

                # Filter out small contours that are likely noise
                if area > max_area:  # Adjust the minimum area based on hand size and image resolution
                    max_area = area
                    hand_found = True
                    contour_max = contour
                    # print("hand detected")

            if len(contour_max) > 0:
                # convex hull
                hull = cv.convexHull(contour_max)
                cv.drawContours(filt_uint8, [hull], -1, (255,255,0), 2)

            print(f"len contour: {len(contour_max)}")

            # #hazard
            thresh = (hazard_temp-min_temp)/(max_temp-min_temp)*(255-min_temp)
            ret, thresh_image_hazard = cv.threshold(remap(frame), thresh, 255, cv.THRESH_BINARY)
            contours_hazard, ret = cv.findContours(thresh_image_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            # Loop through the contours and filter based on area to detect the hand
            for contour in contours_hazard:
                area = cv.contourArea(contour)
                #print(f"Contour area: {area}")  # Debugging line
                # Filter out small contours that are likely noise
                if area > 1:  # Adjust the minimum area based on hand size and image resolution
                    if (hand_found):
                        polygon_hazard = np.squeeze(contour)
                        if not np.array_equal(polygon_hazard[0], polygon_hazard[-1]):
                            polygon_hazard = np.vstack([polygon_hazard, polygon_hazard[0]]) #close polygon
                        centroid = shapely.centroid(shapely.geometry.Polygon(polygon_hazard))
                        distance = cv.pointPolygonTest(contour_max, (centroid.x, centroid.y), True)
                        print(distance)

                        writeSerial(1,abs(distance))
                    else:
                        writeSerial(0,0)
                    # convex hull
                    hull = cv.convexHull(contour)
                    cv.drawContours(filt_uint8, [hull], -1, (255,255,0), 1)
                    # print("hazard detected")
            
            if GUI_THERMAL:
                cv_render(filt_uint8, colormap='rainbow2')
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break
        except KeyboardInterrupt:
            break
    # close it once finished the while loop
    mi48.stop()
        # if header is not None:
        #     logger.debug('  '.join([format_header(header),
        #                             format_framestats(data)]))
        # else:
        #     logger.debug(format_framestats(data))

# set up processes
p1 = multiprocessing.Process(target=noircapture)
p2 = multiprocessing.Process(target=thermalcapture)
p1.start()
p2.start()

# main while loop
while True:
    try:
        # change GUI in here
        time.sleep(0.25)

    except KeyboardInterrupt:
        break

# wait for them to finish
p1.join()
p2.join()

# stop capture and quit
cv.destroyAllWindows()
