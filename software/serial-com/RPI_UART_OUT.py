# Serial communication output
# Run: python UART_OUT.py

import serial
from time import sleep
delim = ', '
signal = 1
threshold_1 = 10
threshold_2 = 5
user_distance = 8

ser = serial.Serial ("/dev/ttyS0", 115200)      #Open port with baud rate
while True:
    message = str(signal) + delim + user_distance + delim + threshold_1 + delim + threshold_2 + '\r\n'
    #transmit data serially 
    ser.write(bytes(message, 'utf8'))  #create byte object with data string
    print('Raspberry Pi 4b data sent: ' + message + '\n')
    sleep(10)