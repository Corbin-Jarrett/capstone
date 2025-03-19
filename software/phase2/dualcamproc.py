# Capstone Eyecan Multiprocessing with both cameras
# import apriltag
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

# for ble connection
import asyncio
from bleak import BleakClient, BleakScanner, BleakError

# ble constants 

# UUIDs (Must match the ESP32 code)
ESP32_SERVICE_UUID = "0000181A-0000-1000-8000-00805F9B34FB"
READ_CHAR_UUID = "0000FEF4-0000-1000-8000-00805F9B34FB"
WRITE_CHAR_UUID = "0000DEAD-0000-1000-8000-00805F9B34FB"
# global variables
delim = ', '
signal = 1
threshold_1 = 10
threshold_2 = 5
esp32_address = None

# change this to false if not interested in the image
GUI_THERMAL = True
GUI_NOIR = True

# set cv_filter parameters
par = {'blur_ks':3, 'd':5, 'sigmaColor': 27, 'sigmaSpace': 27}

# threshold temperature degrees celsius
hazard_temp = 40

# scaling factor from pixels to cm
scale_factor = 1.08

# frame size of the thermal camera
thermal_frame_x = 80
thermal_frame_y = 62

max_hazards = 9
max_hands = 1

dminav = RollingAverageFilter(N=10)
dmaxav = RollingAverageFilter(N=10)

# Shared process data
lock = multiprocessing.Lock()
noir_ready = multiprocessing.Value('i', 0, lock=lock)
thermal_ready = multiprocessing.Value('i', 0, lock=lock)
# Set up arrays for shared camera data
manager = multiprocessing.Manager()
hand_data = manager.list([0]*(max_hands + 1))
thermal_data = manager.list([0]*(max_hazards + 1))

async def find_esp32():
    # Scan for BLE devices and return the address of ESP32. 
    print("Scanning for ESP32 BLE server...")
    devices = await BleakScanner.discover()
    
    for device in devices:
        if device.name == None:
            continue
        if "BLE-Server-EyeCan" in device.name:  # Match the ESP32 device name
            print(device)
            print(f"Found ESP32: {device.address}")
            return device.address
    return None

async def ble_message(client, user_distance, threshold_outer=-1):            
        # Write message to ESP32
        if not client.is_connected:
            print("CLIENT IS NOT CONNECTED")
            return
        message = str(signal) + delim + str(user_distance) + delim + str(threshold_outer) + delim + str(threshold_2) + '\r'
        print(f"Sending: {message}")
        await client.write_gatt_char(WRITE_CHAR_UUID, message.encode(), response=True)
        print("Message sent!")

def noircapture(noir_ready, thermal_ready, data):
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

    while True:
        try:
            local_ready = False
            # need to sync reading between processes
            # keep checking if both readys are true
            # print("checking if ready in noir")
            while not local_ready:
                local_ready = (noir_ready.value == 1) and (thermal_ready.value == 1)

            # print(f"noir capture time: {time.time()}")
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
                    # hand_data[hand_count]
                    mp_draw.draw_landmarks(frame_cropped, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    for i, landmark in enumerate(hand_landmarks.landmark):
                        temp[i] = [int(thermal_frame_x*landmark.x), int(thermal_frame_y*landmark.y)]
                        # print(f"Landmark {i}: x={scaled_x}, y={scaled_y}")
                    hand_data[hand_count] = temp
            hand_data[0] = hand_count

            if GUI_NOIR:
                # cv.imshow("noir", frame) # display frame
                cv.imshow("noircrop", frame_cropped)
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break

            # make noir ready false
            noir_ready.value = 0

        except KeyboardInterrupt:
            break
    
    # stop picam once while loop finished
    picam2.stop()


def thermalcapture(noir_ready, thermal_ready, hazard_data):
    # Make an instance of the MI48, attaching USB for 
    # both control and data interface.
    mi48, connected_port, port_names = connect_senxor()

    # set desired FPS
    mi48.set_fps(20)

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
                local_ready = (noir_ready.value == 1) and (thermal_ready.value == 1)

            # print(f"thermal capture time: {time.time()}")

            data, header = mi48.read()

            if data is None:
                # logger.critical('NONE data received instead of GFRA')
                print("NO DATA FROM THERMAL CAMERA")
                mi48.stop()

            #regular image
            min_temp = dminav(data.min())  # + 1.5
            max_temp = dmaxav(data.max())  # - 1.5
            frame = cv.flip(data_to_frame(data, (thermal_frame_x,thermal_frame_y), hflip=False),0)
            # frame2 = np.clip(frame, min_temp, max_temp)
            filt_uint8 = cv_filter(remap(frame), par, use_median=True,
                                use_bilat=True, use_nlm=False)
            
            # #hazard
            thresh = (hazard_temp-min_temp)/(max_temp-min_temp)*(255-min_temp)
            ret, thresh_image_hazard = cv.threshold(remap(frame), thresh, 255, cv.THRESH_BINARY)
            contours_hazard, ret = cv.findContours(thresh_image_hazard, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            hazard_count = 0
            # Loop through the contours and filter based on area to detect the hand
            for contour in contours_hazard:
                area = cv.contourArea(contour)
                #print(f"Contour area: {area}")  # Debugging line
                # Filter out small contours that are likely noise
                if area > 1:
                    if hazard_count < max_hazards:
                        hazard_count += 1
                        hazard_data[hazard_count] = contour
                    # convex hull
                    hull = cv.convexHull(contour)
                    cv.drawContours(filt_uint8, [hull], -1, (255,255,0), 1)
                    # print("hazard detected")

            # print(hazards_contour_list)
            hazard_data[0] = hazard_count

            if GUI_THERMAL:
                cv_render(filt_uint8, colormap='rainbow2')
                key = cv.waitKey(1)  # & 0xFF
                if key == ord("q"):
                    break
            
            # make thermal ready false
            thermal_ready.value = 0

        except KeyboardInterrupt:
            break
    # close it once finished the while loop
    mi48.stop()

# Connect to ESP32
esp32_address = asyncio.run(find_esp32())
while not esp32_address:
    print("ESP32 not found. Make sure it's advertising.")
    esp32_address = asyncio.run(find_esp32())
    
# set up processes
p1 = multiprocessing.Process(target=noircapture, args=(noir_ready, thermal_ready, hand_data))
p2 = multiprocessing.Process(target=thermalcapture, args=(noir_ready, thermal_ready, thermal_data))
p1.start()
p2.start()


async def main():
    while True:
        try:
            async with BleakClient(esp32_address, timeout=10.0) as client:
                print(f"Connected to {esp32_address}")

                await asyncio.sleep(5)  # Add delay for ESP32 to stabilize connection

                # main while loop
                while client.is_connected:
                    #try:
                        # change GUI in here

                        # check if noir and thermal are ready
                        # print(f"checking if image captured: {time.time()}")
                        local_ready = False
                        while not local_ready:
                            local_ready = (noir_ready.value == 0) and (thermal_ready.value == 0)

                        # go through each hazard contour and find distance to each hand point
                        dist_array = []
                        num_hazards = thermal_data[0]
                        num_hands = hand_data[0]
                        for i in range(num_hazards):
                            contour = thermal_data[i+1]

                            for j in range(num_hands):
                                for point in hand_data[j+1]:
                                    dist = cv.pointPolygonTest(contour,point,True)
                                    # print(f"distance between hazard {i} and point {point}: {dist}")
                                    dist_array.append(dist)

                        if dist_array:
                            pixel_distance = max(dist_array)
                            cm_distance = scale_factor*pixel_distance
                            print(f"closest distance: {cm_distance} cm")
                            await ble_message(client, cm_distance, threshold_1)
                        else:
                            await ble_message(client, 0)
                        # print(thermal_data)
                        # print(hand_data)


                        # ready for another image
                        # print(f"ready to capture image: {time.time()}")
                        noir_ready.value = 1
                        thermal_ready.value = 1

        except BleakError as e:
            print(f"Connection failed: {e}. Retrying in 1 second...")

        except KeyboardInterrupt:
            return

        # await asyncio.sleep(1)  # Wait before reconnecting


asyncio.run(main())

# wait for them to finish
p1.join()
p2.join()

# stop capture and quit
cv.destroyAllWindows()
