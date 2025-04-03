'''
 4TB6 Capstone Project - EyeCan
 Python Code to connect to ESP via ble and send command
'''

import asyncio
from bleak import BleakClient, BleakScanner, BleakError
import time

delim = ', '
signal = 1
threshold_1 = 10
threshold_2 = 5
esp32_address = None

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

async def ble_message(client, user_distance, threshold_outer=-1):            
       # Write message to ESP32
        if not client.is_connected:
            print("CLIENT IS NOT CONNECTED")
            return
        message = str(signal) + delim + str(user_distance) + delim + str(threshold_outer) + delim + str(threshold_2) + '\r'
        print(f"Sending: {message}")
        await client.write_gatt_char(WRITE_CHAR_UUID, message.encode(), response=False) # not currently handling response so will continue immediately
        print("Message sent!")

async def connect_ble(client):
    while True:
        try:
            print(f"Attempting to connect to {esp32_address}...")
            await asyncio.wait_for(client.connect(), timeout=10)
            
            if client.is_connected:
                print(f"Connected to {esp32_address}")
                return
        except asyncio.TimeoutError:
            print("Connection attempt timed out. Retrying in 1 second...")
        except BleakError as e:
            print(f"BLE connection failed: {e}. Retrying in 1 second...")
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying in 1 second...")

        await asyncio.sleep(1)  # Wait before retrying

# Connect to ESP32
esp32_address = asyncio.run(find_esp32())
while not esp32_address:
    print("ESP32 not found. Make sure it's advertising.")
    esp32_address = asyncio.run(find_esp32())
        

async def main():
    client = BleakClient(esp32_address, timeout=10.0)
    await connect_ble(client)

    while True:
        try:
            while client.is_connected:
                await ble_message(client, -6, threshold_1)
                await asyncio.sleep(10)

            if not client.is_connected:
                await connect_ble(client)
                await asyncio.sleep(1)

        except BleakError as e:
            print(f"Connection failed: {e}. Retrying in 1 second...")
            await asyncio.sleep(1)  # Wait before reconnecting

        except TimeoutError:
            print(f"Connection Timeout. Retrying in 1 second...")
            await asyncio.sleep(1)  # Wait before reconnecting

        except KeyboardInterrupt:
            return

        finally:
            if client.is_connected:
                print("Disconnecting...")
                await client.disconnect()

asyncio.run(main())
