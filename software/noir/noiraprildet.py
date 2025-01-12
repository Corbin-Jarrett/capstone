import cv2
from picamera2 import Picamera2
# from picamera2.encoders import Encoder
import time
import apriltag # need venv
import numpy as np

# initialize camera
picam2 = Picamera2()
# configurations (see documentation for details)
# check and choose a mode
# print(picam2.sensor_modes)
mode = picam2.sensor_modes[3] # 3 or 7 are best
video_config = picam2.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth': mode['bit_depth']}, main={'format': 'BGR888'})
# picam2.set_controls({"FrameDurationLimits": (40000,40000)}) # set controls (see documentation)

# start camera
picam2.start(config=video_config)

time.sleep(2) # give time for camera to set up

while True:

    # capture next frame as 3D numpy array
    frame = picam2.capture_array()
    cv2.imshow("noir", frame) # display frame

    # identify april tag(s)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # define the AprilTags detector options and then detect AprilTags
    print("[INFO] detecting AprilTags...")
    # Using Tag36h11 family
    detector = apriltag.Detector()

    detections = detector.detect(gray)

    print("[INFO] {} total AprilTags detected".format(len(detections)))

    # map hand from april tag



    # if q pressed, exit loop
    if cv2.waitKey(5) == ord('q'):
        break

picam2.stop()
