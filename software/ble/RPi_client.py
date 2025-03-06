'''
 4TB6 Capstone Project - EyeCan
 RPi Python Code to connect to ESP via ble and send command
'''

import asyncio
from bleak import BleakClient, BleakScanner
import time

delim = ', '
signal = 1
threshold_1 = 10
threshold_2 = 5
user_distance = 0

# UUIDs (Must match the ESP32 code)
ESP32_SERVICE_UUID = "0000181A-0000-1000-8000-00805F9B34FB"
READ_CHAR_UUID = "0000FEF4-0000-1000-8000-00805F9B34FB"
WRITE_CHAR_UUID = "0000DEAD-0000-1000-8000-00805F9B34FB"

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

async def main():
    # Connect to ESP32
    esp32_address = await find_esp32()
    while not esp32_address:
        print("ESP32 not found. Make sure it's advertising.")
        esp32_address = await find_esp32()
    
    async with BleakClient(esp32_address) as client:
        print(f"Connected to {esp32_address}")

        # Read data from ESP32
        #read_data = await client.read_gatt_char(READ_CHAR_UUID)
        #print(f"Received from ESP32: {read_data.decode()}")

        while (1):
            # Write message to ESP32
            for user_distance in [8, 4, 12]:
                message = str(signal) + delim + str(user_distance) + delim + str(threshold_1) + delim + str(threshold_2) + '\r'
                print(f"Sending: {message}")
                await client.write_gatt_char(WRITE_CHAR_UUID, message.encode(), response=True)
                print("Message sent!")
                time.sleep(5)



# Run the asyncio event loop
asyncio.run(main())