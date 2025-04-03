# Bluetooth Low Energy

## Requirements

### RPi 4b
Need to install bleak python package.
`sudo apt-get install bleak`

### ESP 32
Ensure Bluetooth is Enabled in menuconfig.
`idf.py menuconfig`
Go to *Component Config > Bluetooth*
Enable `Bluetooth`

Enable NimBLE in menuconfig.
`idf.py menuconfig`
Go to *Component Config > Bluetooth > Host*
Select `NimBLE - BLE only`

Press `S` to Save
Press `Q` to Quit

Tutorial used for ESP 32 server code: *https://innovationyourself.com/esp32-bluetooth-low-energy-tutorial/* and *https://innovationyourself.com/ble-data-exchange-tutorial-with-esp-idf/*

To build and flash with ESP-IDF:
`idf.py set-target esp32s3`  !! changed to esp32-s3
`idf.py build`
`idf.py -p COMX flash monitor` COMX is the port for windows, use monitor to see output