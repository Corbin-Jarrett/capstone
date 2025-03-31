# Capstone Eyecan Multiprocessing with both cameras
from sharedcode import *
import picamproc, thermcamproc # import processing files
import signal
import time
import numpy as np
import multiprocessing
import math

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

# scaling factor from pixels to cm
scale_factor = 1.08

# Shared process data
lock = multiprocessing.Lock()
picam_ready = multiprocessing.Value('i', 0, lock=lock)
thermal_ready = multiprocessing.Value('i', 0, lock=lock)
# Set up arrays for shared camera data
manager = multiprocessing.Manager()
hand_data = manager.list([0]*(max_hands + 2)) # adding one for hand count and one for depth
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
        await client.write_gatt_char(WRITE_CHAR_UUID, message.encode(), response=False) # not currently handling response so will continue immediately
        print("Message sent!")

# Connect to ESP32
esp32_address = asyncio.run(find_esp32())
while not esp32_address:
    print("ESP32 not found. Make sure it's advertising.")
    esp32_address = asyncio.run(find_esp32())
    
# set up processes
p1 = multiprocessing.Process(target=picamproc.picamcapture, args=(picam_ready, thermal_ready, hand_data))
p2 = multiprocessing.Process(target=thermcamproc.thermalcapture, args=(picam_ready, thermal_ready, thermal_data))
p1.start()
p2.start()


async def main():
    while True:
        try:
            async with BleakClient(esp32_address, timeout=10.0) as client:
                print(f"Connected to {esp32_address}")

                await asyncio.sleep(2)  # Add delay for ESP32 to stabilize connection

                # main while loop
                while client.is_connected:
                    #try:
                        # change GUI in here

                        # check if noir and thermal are ready
                        # print(f"checking if image captured: {time.time()}")
                        local_ready = False
                        while not local_ready:
                            local_ready = (picam_ready.value == 0) and (thermal_ready.value == 0)

                        # go through each hazard contour and find distance to each hand point
                        dist_array = []
                        num_hazards = thermal_data[0]
                        num_hands = hand_data[0]
                        hand_depth = 232*(hand_data[1]-0.125) # numbers come from manual calibration
                        for i in range(num_hazards):
                            contour = thermal_data[i+1]

                            for j in range(num_hands):
                                for point in hand_data[j+2]:
                                    dist = cv.pointPolygonTest(contour,point,True)
                                    # print(f"distance between hazard {i} and point {point}: {dist}")
                                    dist_array.append(dist)

                        # if dist_array is empty, either no hand or hazard detected
                        if dist_array:
                            pixel_distance = max(dist_array)
                            cm_distance = scale_factor*pixel_distance
                            dist_3d = (math.sqrt((cm_distance**2) + (hand_depth**2))) - 5   # set 5 cm as height of hazard
                            print(f"closest distance: {dist_3d} cm")
                            await ble_message(client, cm_distance, threshold_1)
                        else:
                            await ble_message(client, 0)

                        # ready for another image
                        # print(f"ready to capture image: {time.time()}")
                        picam_ready.value = 1
                        thermal_ready.value = 1

        except BleakError as e:
            print(f"Connection failed: {e}. Retrying in 1 second...")
            await asyncio.sleep(1)  # Wait before reconnecting

        except TimeoutError:
            print(f"Connection Timeout. Retrying in 1 second...")
            await asyncio.sleep(1)  # Wait before reconnecting

        except KeyboardInterrupt:
            return


asyncio.run(main())

# wait for them to finish
p1.join()
p2.join()

# stop capture and quit
cv.destroyAllWindows()
