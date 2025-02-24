
import asyncio
from bleak import BleakClient, BleakScanner

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

async def connect_to_esp32():
    # Connect to ESP32, read data, and write a command.
    esp32_address = await find_esp32()
    if not esp32_address:
        print("ESP32 not found. Make sure it's advertising.")
        return

    async with BleakClient(esp32_address) as client:
        print(f"Connected to {esp32_address}")

        # Read data from ESP32
        read_data = await client.read_gatt_char(READ_CHAR_UUID)
        print(f"Received from ESP32: {read_data.decode()}")

        # Write command to ESP32
        command = "LED ON"
        print(f"Sending: {command}")
        await client.write_gatt_char(WRITE_CHAR_UUID, command.encode(), response=True)

        print("Command sent!")

# Run the asyncio event loop
asyncio.run(connect_to_esp32())