# Phase 2

## Setup

1. Install system packages if missing using ```sudo apt install python3-<package name>```
	- pyqt6
	- python3-opencv
2. Make a virtual environment using ```python3 -m venv --system-site-packages myenv```
3. Activate venv ```source myenv/bin/activate```
4. Install Requirements ```python -m pip install -r requirements.txt```
5. Ensure hardware is connected and run eyecan.py
 
## Background
Phase 1 can capture frames from picamera and thermal cameras.
This data can be processed and camera feeds displayed.
Each camera and the data processing are done in separate processes and all synchronized.

## Goals
1. Hand detection using picamera
2. User Interface
3. Bootup sequence
4. Bluetooth Low Energy Communication between RPi and ESP
5. Communicating frame data between processes
