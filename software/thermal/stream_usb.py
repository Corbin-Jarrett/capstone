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
    STREAM_FPS = 15
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

dminav = RollingAverageFilter(N=10)
dmaxav = RollingAverageFilter(N=10)

var = True

while var:
    data, header = mi48.read()
    data_hand, header_hand = mi48.read()
    data_hazard, header_hazard = mi48.read()

    if data is None:
        logger.critical('NONE data received instead of GFRA')
        mi48.stop()
        sys.exit(1)

    # for row in data_hand:  # Iterate over each row
    for i in range(len(data_hand)):
        if data_hand[i] < 23 or data_hand[i] > 30:
            data_hand[i] = 0

    # for row in data_hazard:  # Iterate over each row
    for i in range(len(data_hazard)):
        if data_hazard[i] < 40:
            data_hazard[i] = 0
    
    #regular image
    min_temp = dminav(data.min())  # + 1.5
    max_temp = dmaxav(data.max())  # - 1.5
    frame = data_to_frame(data, (80,62), hflip=False);
    frame = np.clip(frame, min_temp, max_temp)
    filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                           use_bilat=True, use_nlm=False)
    #hand image
    min_temp_hand = dminav(data_hand.min())  # + 1.5
    max_temp_hand = dmaxav(data_hand.max())  # - 1.5
    frame_hand = data_to_frame(data_hand, (80,62), hflip=False);
    frame_hand = np.clip(frame_hand, min_temp_hand, max_temp_hand)
    filt_uint8_hand = cv_filter(remap(frame_hand), par, use_median=True,
                           use_bilat=True, use_nlm=False)

    # #hazard image
    min_temp_hazard = dminav(data_hazard.min())  # + 1.5
    max_temp_hazard = dmaxav(data_hazard.max())  # - 1.5
    frame_hazard = data_to_frame(data_hazard, (80,62), hflip=False);
    frame_hazard = np.clip(frame_hazard, min_temp_hazard, max_temp_hazard)
    filt_uint8_hazard = cv_filter(remap(frame_hazard), par, use_median=True,
                           use_bilat=True, use_nlm=False)
    
    #hand
    _, thresh_image_hand = cv.threshold(filt_uint8_hand, 80, 255, cv.THRESH_BINARY)
    contours_hand, _ = cv.findContours(filt_uint8_hand, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # Loop through the contours and filter based on area to detect the hand
    for contour in contours_hand:
        area = cv.contourArea(contour)
        #print(f"Contour area: {area}")  # Debugging line

        # Filter out small contours that are likely noise
        if area > 50:  # Adjust the minimum area based on hand size and image resolution
            # Get the bounding box of the contour
            x, y, w, h = cv.boundingRect(contour)

            # Draw the bounding box around the detected hand
            cv.rectangle(filt_uint8, (x, y), (x + w, y + h), (255, 255, 0), 1)
            print(f"Bounding box hand: x={x}, y={y}, w={w}, h={h}")  # Debugging line

    # #hazard
    _, thresh_image_hazard = cv.threshold(filt_uint8_hazard, 80, 255, cv.THRESH_BINARY)
    contours_hazard, _ = cv.findContours(filt_uint8_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    # Loop through the contours and filter based on area to detect the hand
    for contour in contours_hazard:
        area = cv.contourArea(contour)
        #print(f"Contour area: {area}")  # Debugging line

        # Filter out small contours that are likely noise
        if area > 1:  # Adjust the minimum area based on hand size and image resolution
            # Get the bounding box of the contour
            x, y, w, h = cv.boundingRect(contour)

            # Draw the bounding box around the detected hand
            cv.rectangle(filt_uint8, (x, y), (x + w, y + h), (255, 255, 0), 1)
            print(f"Bounding box hazard: x={x}, y={y}, w={w}, h={h}")  # Debugging line
    
    if header is not None:
        logger.debug('  '.join([format_header(header),
                                format_framestats(data)]))
    else:
        logger.debug(format_framestats(data))

    if GUI:
#        cv_render(filt_uint8, resize=(400,310), colormap='ironbow')
        #cv_render(filt_uint8, resize=(400,310), colormap='rainbow2')
        # Show the result with bounding boxes around the detected hand
        cv_render(filt_uint8, resize=(400, 310), colormap='rainbow2')
        # cv_render(remap(frame), resize=(400,310), colormap='rainbow2')
        key = cv.waitKey(1)  # & 0xFF
        if key == ord("q"):
            break
#    time.sleep(1)

# stop capture and quit
mi48.stop()
cv.destroyAllWindows()
