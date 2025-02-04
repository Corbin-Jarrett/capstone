# UART Serial Communication

## Requirements for flashing code to ESP32
The following setup is needed to build, flash and monitor the ESP code in the folder *ESP_UART_IN*.

### Drivers
ESP32-WROOM-32 is configured to use the CP210x USB to UART Bridge VCP Drivers.
Download them here: *https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers?tab=downloads*.
NOTE: For other variant of the ESP32, you might need the CH340 drivers.
Download them here: *http://www.wch-ic.com/downloads/CH341SER_ZIP.html*.

### Build/Deploy/Monitor
To build, deploy and monitor the ESP, you need to install ESP-IDF Tools. 
Follow the installation guide here: *https://espressif-docs.readthedocs-hosted.com/projects/esp-idf/en/stable/get-started/index.html#step-1-install-prerequisites*.
Note: this code requires at least ESP-IDF 5.0 or later, we used version 5.4 of ESP-IDF.

Once installed, open esp-idf 5.4 cmd.
cd to the project folder *ESP_UART_IN*.
`idf.py build` to build.
`idf.py -p PORT flash monitor` to flash and monitor.
(monitor is optional, allows you to see any output).

## Requirements for RPi 4b
The following setup in the configuration is needed to configure the RPi 4b to allow serial communication.
More information can be found in the documentation here: *https://www.electronicwings.com/raspberry-pi/raspberry-pi-uart-communication-using-python-and-c*.

### Configuration
In the RPi, enter the command:
`sudo raspi-config`.
Select Interface Options -> Serial Port.
For option "Would you like a login shell to be accessible over serial?" Select No.
For option "Would you like the serial port hardware to be enabled?" Select Yes.
Select Ok.
Reboot the RPi.

Check serial pin mapping with command:
`ls -l /dev`.
The following mapping is required:
`serial0 -> ttyS0`.

### Note on the Serial Communication Port
Ports on the RPi 4b:
`/dev/ttyAMA0 -> Bluetooth`
`/dev/ttyS0 -> GPIO serial port.`.
We are currently using the "mini-uart" which is */dev/ttyS0*. They can be swapped for faster performance of serial communication but then it will not be able to use bluetooth. 

## Physical Setup
The ESP32's GPIO 16 is the RX pin for the UART1 receiver and should be connected to the RPi 4b's TX pin (GPIO 14 / pin 8). They also need a common ground connected.
Note: GPIO 3 is also RX but for UART0 which is also used by logging and had overflow issues.

## Tutorial
More information on UART between RPi and ESP32 can be found in this video: *https://www.youtube.com/watch?v=qG8n44cgshg*.
