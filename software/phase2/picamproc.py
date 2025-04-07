from sharedcode import *
from picamera2 import Picamera2
import mediapipe as mp
import math
import time

def depthlandmarks(hands, frame):

    # detect hand
    results = hands.process(frame)

    # draw hand landmarks if detected
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            wrist_landmark = hand_landmarks.landmark[0]
            index_finger_mcp_landmark = hand_landmarks.landmark[5]
            depth_dist = math.sqrt(((wrist_landmark.x - index_finger_mcp_landmark.x)**2)+((wrist_landmark.y-index_finger_mcp_landmark.y)**2))
            return depth_dist

    return 0

def picamcapture(picam_ready, thermal_ready, hand_data, depth_data):
    """
    hand_data[0]: number of hands detected
    hand_data[1]: distance betwen knucle and wrist for depth
    hand_data[2]: array of 21 landmarks for hand 1
    """
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
        static_image_mode = False,  # False for real-time tracking
        max_num_hands = max_hands,  # Detect up to max_hands hand
        min_detection_confidence = 0.5,  # Confidence threshold
        min_tracking_confidence = 0.5
    )
    mp_draw = mp.solutions.drawing_utils  # Utility to draw landmarks

    """
    If depth should be calibrated, manually capture frames when user says
    Take each distance between landmarks for lowest and highest measurements
    Use values to determine depth
    """
    if calibrate_depth:
        print("Place hand on surface")
        while depth_data[0] <= 0:
            frame_cropped = picam2.capture_array()[30:340,120:550] # y, x
            depth_data[0] = depthlandmarks(hands, frame_cropped)

        print("Place hand aligned at upper position")
        time.sleep(3)
        while depth_data[1] <= 0:
            frame_cropped = picam2.capture_array()[30:340,120:550] # y, x
            depth_data[1] = depthlandmarks(hands, frame_cropped)

    while True:
        try:
            local_ready = False
            # need to sync reading between processes
            # keep checking if both readys are true
            # print("checking if ready in cam")
            while not local_ready:
                local_ready = (picam_ready.value == 1) and (thermal_ready.value == 1)

            # print(f"picam capture time: {time.time()}")
            # capture next frame as 3D numpy array
            frame_cropped = picam2.capture_array()[30:340,120:550] # y, x

            # detect hand
            results = hands.process(frame_cropped)

            hand_count = 0

            # draw hand landmarks if detected
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    hand_count += 1
                    temp = [0]*21
                    mp_draw.draw_landmarks(frame_cropped, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    for i, landmark in enumerate(hand_landmarks.landmark):
                        temp[i] = [int(thermal_frame_x*landmark.x), int(thermal_frame_y*landmark.y)]
                        # print(f"Landmark {i}: x={scaled_x}, y={scaled_y}")
                    hand_data[hand_count + 1] = temp
                    wrist_landmark = hand_landmarks.landmark[0]
                    index_finger_mcp_landmark = hand_landmarks.landmark[5]
                    depth_dist = math.sqrt(((wrist_landmark.x - index_finger_mcp_landmark.x)**2)+((wrist_landmark.y-index_finger_mcp_landmark.y)**2))
                    hand_data[1] = depth_dist
            hand_data[0] = hand_count

            if GUI_PICAM:
                # cv.imshow("picam", frame) # display frame
                cv.imshow("picamcrop", frame_cropped)
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break

            # make picam ready false
            picam_ready.value = 0

        except KeyboardInterrupt:
            break
    
    # stop picam once while loop finished
    picam2.stop()