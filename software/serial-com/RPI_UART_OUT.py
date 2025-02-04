# Serial communication output
# Run: python UART_OUT.py

import serial
from time import sleep
delim = ', '
signal = 1
threshold_1 = 10
threshold_2 = 5
user_distance = 0

ser = serial.Serial ("/dev/ttyS0", 115200)      #Open port with baud rate
while True:
    # send distance within first threshold
    user_distance = 8
    message = str(signal) + delim + str(user_distance) + delim + str(threshold_1) + delim + str(threshold_2) + '\r'
    #transmit data serially 
    ser.write(bytes(message, 'utf8'))  #create byte object with data string
    print('Raspberry Pi 4b data sent: ' + message + '\n')
    sleep(5)
    
    # send distance within closer threshold
    user_distance = 3
    message = str(signal) + delim + str(user_distance) + delim + str(threshold_1) + delim + str(threshold_2) + '\r'
    #transmit data serially 
    ser.write(bytes(message, 'utf8'))  #create byte object with data string
    print('Raspberry Pi 4b data sent: ' + message + '\n')
    sleep(5)
    
    # send out of threshold distance to turn off LEDs
    user_distance = 12
    message = str(signal) + delim + str(user_distance) + delim + str(threshold_1) + delim + str(threshold_2) + '\r'
    #transmit data serially 
    ser.write(bytes(message, 'utf8'))  #create byte object with data string
    print('Raspberry Pi 4b data sent: ' + message + '\n')
    sleep(10)