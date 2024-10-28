# Display webcam or video
# Adds a mask to the video for a particular HSV colour
# see https://docs.opencv.org/3.4/df/d9d/tutorial_py_colorspaces.html
import cv2

# source of video
cap = cv2.VideoCapture(0) # laptop camera
# cap = cv2.VideoCapture("path\to\file") # video in filesystem

# read frame, calculate mask, display frame and mask
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ranges of colours are in (H,S,V) format
    # cv2.inRange(hsv, lower, upper)
    # to determine lower and upper use an HSV colour picker online

    ## mask of GREEN (36,25,25) ~ (89,255,255) 
    # mask = cv2.inRange(hsv, (36, 25, 25), (89,255,255))

    ## mask of RED
    # mask = cv2.inRange(hsv, (175,50,20), (180,255,255))

    ## mask of BLUE
    mask = cv2.inRange(hsv, (90,150,90), (135,255,255))

    # make everything matching colour in original image turn red
    red_overlay = frame.copy()
    red_overlay[mask > 0] = (0,5,255)

    # display
    cv2.imshow('Video Capture', frame)
    cv2.imshow('mask',mask)
    # to display mask and input video
    #cv2.imshow('mask AND video', cv2.bitwise_and(frame,frame,mask=mask))

    cv2.imshow('mask AND video', red_overlay)

    # if q pressed, exit loop
    if cv2.waitKey(5) == ord('q'):
        break

# clean up
cap.release()
cv2.destroyAllWindows()
