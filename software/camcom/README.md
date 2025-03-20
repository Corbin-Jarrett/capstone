# Camera and Communication Integration

## Requirements
1. Make virtual environment
```python -m venv myenv```
2. Activate venv
```source myenv/bin/activate```
3. Install Requirements
```python -m pip install -r requirements.txt```

## Files Guide
stream_usb_v2.py : Demo thermal camera code that we built off
RPI_UART_OUT.py : Simple code for the Pi to communicate data to the ESP.
dualcam.py : First file where both cameras are accessed and displayed at the same time.
dualcamthread.py : Each camera's capture and processing is done in a separate thread.
dualcamproc.py : Switch from threading to a process for each camera and the main one.

## More about Multiprocessing implementation
There are three processes:
    - 1 main process for controlling when to capture a frame
    - 1 process for NoIR camera
    - 1 process for thermal camera

The processes for the cameras are synced so they capture a frame at the same time.
