# Copyright (C) Meridian Innovation Ltd. Hong Kong, 2020. All rights reserved.
#
import sys
sys.path.append("/home/test/myenv/lib/python3.11/site-packages")
import os
import signal
import time
import logging
import serial
import numpy as np
from matplotlib import pyplot as plt

try:
    import cv2 as cv
except:
    print("Please install OpenCV (or link existing installation)"
          " to see the thermal image")
    exit(1)

from senxor.mi48 import MI48, format_header, format_framestats
from senxor.utils import data_to_frame, remap, cv_filter,\
                         cv_render, RollingAverageFilter,\
                         connect_senxor

# This will enable mi48 logging debug messages
logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOGLEVEL", "DEBUG"))


# Make the a global variable and use it as an instance of the mi48.
# This allows it to be used directly in a signal_handler.
global mi48

# define a signal handler to ensure clean closure upon CTRL+C
# or kill from terminal
def signal_handler(sig, frame):
    """Ensure clean exit in case of SIGINT or SIGTERM"""
    logger.info("Exiting due to SIGINT or SIGTERM")
    mi48.stop()
    cv.destroyAllWindows()
    logger.info("Done.")
    sys.exit(0)

# Define the signals that should be handled to ensure clean exit
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Make an instance of the MI48, attaching USB for 
# both control and data interface.
# can try connect_senxor(src='/dev/ttyS3') or similar if default cannot be found
mi48, connected_port, port_names = connect_senxor()

# print out camera info
logger.info('Camera info:')
logger.info(mi48.camera_info)

# set desired FPS
if len(sys.argv) == 2:
    STREAM_FPS = int(sys.argv[1])
else:
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

# change this to false if not interested in the image
GUI = True

# set cv_filter parameters
par = {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}

# threshold temperatures
hand_temp = [23,35]
hazard_temp = 40

dminav = RollingAverageFilter(N=10)
dmaxav = RollingAverageFilter(N=10)

while True:
    data, header = mi48.read()
    # data_hand, header_hand = mi48.read()
    # data_hazard, header_hazard = mi48.read()

    if data is None:
        logger.critical('NONE data received instead of GFRA')
        mi48.stop()
        sys.exit(1)

    #regular image
    min_temp = dminav(data.min())  # + 1.5
    max_temp = dmaxav(data.max())  # - 1.5
    frame = data_to_frame(data, (80,62), hflip=False);
    # frame2 = np.clip(frame, min_temp, max_temp)
    filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                           use_bilat=True, use_nlm=False)
    
    #hand
    # convert to grayscale temp for threshold, linear transformation
    thresh_low = 0+(hand_temp[0]-min_temp)/(max_temp-min_temp)*(255-min_temp)
    thresh_high = 0+(hand_temp[1]-min_temp)/(max_temp-min_temp)*(255-min_temp)

    ret, thresh_image_hand_lower = cv.threshold(remap(frame), thresh_low, 255, cv.THRESH_BINARY)
    ret, thresh_image_hand_upper = cv.threshold(remap(frame), thresh_high, 255, cv.THRESH_BINARY_INV)

    thresh_image_hand = np.logical_and(thresh_image_hand_lower,thresh_image_hand_upper).astype(np.uint8)
    contours_hand, ret = cv.findContours(thresh_image_hand, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # Loop through the contours and filter based on area to detect the hand
    for contour in contours_hand:
        area = cv.contourArea(contour)
        #print(f"Contour area: {area}")  # Debugging line

        # Filter out small contours that are likely noise
        if area > 25:  # Adjust the minimum area based on hand size and image resolution
            # convex hull
            hull = cv.convexHull(contour)
            cv.drawContours(filt_uint8, [hull], -1, (0,255,0), 3)
            print("hand detected")
            # print(f"Bounding box hand: x={x}, y={y}, w={w}, h={h}")  # Debugging line


    # #hazard
    thresh = 0+(hazard_temp-min_temp)/(max_temp-min_temp)*(255-min_temp)
    ret, thresh_image_hazard = cv.threshold(remap(frame), thresh, 255, cv.THRESH_BINARY)
    contours_hazard, ret = cv.findContours(thresh_image_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # Loop through the contours and filter based on area to detect the hand
    for contour in contours_hazard:
        area = cv.contourArea(contour)
        #print(f"Contour area: {area}")  # Debugging line

        # Filter out small contours that are likely noise
        if area > 1:  # Adjust the minimum area based on hand size and image resolution
            # convex hull
            hull = cv.convexHull(contour)
            cv.drawContours(filt_uint8, [hull], -1, (0,255,0), 1)
            print("hazard detected")
            # print(f"Bounding box hazard: x={x}, y={y}, w={w}, h={h}")  # Debugging line
    
    if header is not None:
        logger.debug('  '.join([format_header(header),
                                format_framestats(data)]))
    else:
        logger.debug(format_framestats(data))

    if GUI:
        # cv_render(filt_uint8, resize=(400,310), colormap='ironbow')
        # cv_render(filt_uint8, resize=(400,310), colormap='rainbow2')
        # Show the result with bounding boxes around the detected hand
        cv_render(filt_uint8,  colormap='rainbow2')
        # cv_render(remap(frame), resize=(400,310), colormap='rainbow2')
        key = cv.waitKey(1)  # & 0xFF
        if key == ord("q"):
            break

# stop capture and quit
mi48.stop()
cv.destroyAllWindows()
