import cv2 as cv

GUI_THERMAL = True
GUI_PICAM = True

# frame size of the thermal camera
thermal_frame_x = 80
thermal_frame_y = 62

max_hazards = 9
max_hands = 1

calibrate_depth = False
hand_height_measurement = 40 # cm
max_hazard_height = 10 # cm