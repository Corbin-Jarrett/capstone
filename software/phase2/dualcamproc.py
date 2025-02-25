# Capstone Eyecan Multiprocessing with both cameras
# import apriltag
import sys
# sys.path.append("/home/test/myenv/lib/python3.11/site-packages")
import os
import signal
import time
import serial
import numpy as np
from picamera2 import Picamera2
import multiprocessing
import cv2 as cv
import mediapipe as mp

from senxor.mi48 import MI48, format_header, format_framestats
from senxor.utils import data_to_frame, remap, cv_filter,\
                         cv_render, RollingAverageFilter,\
                         connect_senxor


# change this to false if not interested in the image
GUI_THERMAL = False
GUI_NOIR = True

# set cv_filter parameters
par = {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}

# threshold temperature
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

noir_ready = multiprocessing.Value('i', 0)
thermal_ready = multiprocessing.Value('i', 0)
lock = multiprocessing.Lock()

def noircapture(noir_ready, thermal_ready, lock):
    # initialize camera
    picam2 = Picamera2()
    # configurations (see documentation for details)
    # check and choose a mode
    # print(picam2.sensor_modes)
    mode = picam2.sensor_modes[5]
    video_config = picam2.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']}, main={'format': 'BGR888'})
    # start camera
    picam2.start(config=video_config)

    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,  # False for real-time tracking
        max_num_hands=2,  # Detect up to 2 hands
        min_detection_confidence=0.5,  # Confidence threshold
        min_tracking_confidence=0.5
    )
    mp_draw = mp.solutions.drawing_utils  # Utility to draw landmarks

    while True:
        try:
            local_ready = False
            # need to sync reading between processes
            # keep checking if both readys are true
            # print("checking if ready in noir")
            while not local_ready:
                lock.acquire()
                local_ready = (noir_ready.value == 1) and (thermal_ready.value == 1)
                lock.release()

            # print(f"noir capture time: {time.time()}")
            # capture next frame as 3D numpy array
            frame = picam2.capture_array()
            frame_cropped = frame[30:380,120:560] # y, x

            # detect hand
            results = hands.process(frame_cropped)

            # draw hand landmarks if detected
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame_cropped, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
            # detector = apriltag.Detector()
            # detections = detector.detect(gray)
            # print("[INFO] {} total AprilTags detected".format(len(detections)))

            if GUI_NOIR:
                # cv.imshow("noir", frame) # display frame
                cv.imshow("noircrop", frame_cropped)
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break

            # make noir ready false
            lock.acquire()
            noir_ready.value = 0
            lock.release()

        except KeyboardInterrupt:
            break
    
    # stop picam once while loop finished
    picam2.stop()


def thermalcapture(noir_ready, thermal_ready, lock):
    # Make an instance of the MI48, attaching USB for 
    # both control and data interface.
    mi48, connected_port, port_names = connect_senxor()

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
            local_ready = False
            # need to sync reading between processes
            # keep checking if both readys are true
            # print("checking if ready in thermal")
            while not local_ready:
                lock.acquire()
                local_ready = (noir_ready.value == 1) and (thermal_ready.value == 1)
                lock.release()

            # print(f"thermal capture time: {time.time()}")

            data, header = mi48.read()

            if data is None:
                # logger.critical('NONE data received instead of GFRA')
                print("NO DATA FROM THERMAL CAMERA")
                mi48.stop()

            #regular image
            min_temp = dminav(data.min())  # + 1.5
            max_temp = dmaxav(data.max())  # - 1.5
            frame = cv.flip(data_to_frame(data, (80,62), hflip=False),0)
            # frame2 = np.clip(frame, min_temp, max_temp)
            filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                                use_bilat=True, use_nlm=False)
            
            # #hazard
            thresh = (hazard_temp-min_temp)/(max_temp-min_temp)*(255-min_temp)
            ret, thresh_image_hazard = cv.threshold(remap(frame), thresh, 255, cv.THRESH_BINARY)
            contours_hazard, ret = cv.findContours(thresh_image_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            hazards_contour_list = []
            # Loop through the contours and filter based on area to detect the hand
            for contour in contours_hazard:
                area = cv.contourArea(contour)
                #print(f"Contour area: {area}")  # Debugging line
                # Filter out small contours that are likely noise
                if area > 1:  # Adjust the minimum area based on hand size and image resolution
                    # convex hull
                    hull = cv.convexHull(contour)
                    cv.drawContours(filt_uint8, [hull], -1, (255,255,0), 1)
                    hazards_contour_list.append(contour)
                    # print("hazard detected")

            # print(hazards_contour_list)
            
            if GUI_THERMAL:
                cv_render(filt_uint8, colormap='rainbow2')
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break
            
            # make thermal ready false
            lock.acquire()
            thermal_ready.value = 0
            lock.release()

        except KeyboardInterrupt:
            break
    # close it once finished the while loop
    mi48.stop()

# set up processes
p1 = multiprocessing.Process(target=noircapture, args=(noir_ready, thermal_ready, lock))
p2 = multiprocessing.Process(target=thermalcapture, args=(noir_ready, thermal_ready, lock))
p1.start()
p2.start()

# main while loop
while True:
    try:
        # change GUI in here

        # check if noir and thermal are ready
        # print(f"checking if image captured: {time.time()}")
        local_ready = False
        while not local_ready:
            lock.acquire()
            local_ready = (noir_ready.value == 0) and (thermal_ready.value == 0)
            lock.release()

        # do some kind of processing
        # time.sleep(0.5)

        # ready for another image
        # print(f"ready to capture image: {time.time()}")
        lock.acquire()
        noir_ready.value = 1
        thermal_ready.value = 1
        lock.release()

        # time.sleep(0.5)

    except KeyboardInterrupt:
        break

# wait for them to finish
p1.join()
p2.join()

# stop capture and quit
cv.destroyAllWindows()
