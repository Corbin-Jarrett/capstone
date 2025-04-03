# Capstone Eyecan Multiprocessing with both cameras
from picamera2 import Picamera2
import cv2 as cv
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QStackedWidget, QSlider
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set the window title
        self.setWindowTitle("EyeCan")

        # Create stacked widget to manage multiple pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Set the background colour of all pages
        self.stack.setStyleSheet("background-color: #ff9c9d;")

        # Create pages
        self.start = QWidget()
        self.home = QWidget()
        self.calibration = QWidget()
        self.parameters = QWidget()

        # Set up pages
        self.setup_start()
        self.setup_home()
        self.setup_calibration()
        self.setup_parameters()

        # Add pages to stack
        self.stack.addWidget(self.start)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.calibration)
        self.stack.addWidget(self.parameters)

        # Initialize variables
        self.haptic_sensitivity = 50

    def setup_start(self):
        layout = QVBoxLayout()
        self.start.setLayout(layout)
        
        # Add a label
        label = QLabel("This is the Start page", self.start)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Add a button
        button = QPushButton("Power On", self.start)
        button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        button.clicked.connect(self.switch_to_home)  # Connect button to function
        layout.addWidget(button)

    def setup_home(self):
        layout = QVBoxLayout()
        self.home.setLayout(layout)
        
        # Add a label for the video feed
        self.video_label = QLabel(self.home)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.video_label)
        
        # Start the camera feed
        self.start_camera()

        # Add a button to power off
        button = QPushButton("Power Off", self.home)
        button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        button.clicked.connect(self.switch_to_start)  # Connect button to function
        layout.addWidget(button)

        # Add a button for changing to calibration page
        calibration_button = QPushButton("Calibrate", self.home)
        calibration_button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        calibration_button.clicked.connect(self.switch_to_calibration)  # Connect button to function
        layout.addWidget(calibration_button)

        # Add a button for changing to parameters page
        parameters_button = QPushButton("Modify Parameters", self.home)
        parameters_button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        parameters_button.clicked.connect(self.switch_to_parameters)  # Connect button to function
        layout.addWidget(parameters_button)

    def setup_calibration(self):
        layout = QVBoxLayout()
        self.calibration.setLayout(layout)
        
        # Add a label
        label = QLabel("This is the Calibration page", self.calibration)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Add a button
        button = QPushButton("Return Home", self.calibration)
        button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        button.clicked.connect(self.switch_to_home)  # Connect button to function
        layout.addWidget(button)

    def setup_parameters(self):
        layout = QVBoxLayout()
        self.parameters.setLayout(layout)
        
        # Add a label
        self.parameters.label = QLabel("Haptic Sensitivity: 50", self.parameters)
        self.parameters.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.parameters.label)

        # Slider widget
        haptic_slider = QSlider(Qt.Orientation.Horizontal, self.parameters)  # Horizontal slider
        haptic_slider.setMinimum(0)  # Min value
        haptic_slider.setMaximum(100)  # Max value
        haptic_slider.setValue(50)  # Default value
        haptic_slider.setTickInterval(10)  # Tick marks every 10
        haptic_slider.setTickPosition(QSlider.TickPosition.TicksBelow)  # Show tick marks
        haptic_slider.setFixedWidth(400)
        haptic_slider.valueChanged.connect(self.update_haptic_value)
        layout.addWidget(haptic_slider, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add a button
        button = QPushButton("Return Home", self.parameters)
        button.setStyleSheet("background-color: #940220; color: white; border-radius: 5px; padding: 10px; font-size: 24px; font-weight: bold; outline: none;")
        button.clicked.connect(self.switch_to_home)  # Connect button to function
        layout.addWidget(button)

    # Function that runs when the "Power On" button is clicked
    def switch_to_home(self):
        self.stack.setCurrentWidget(self.home)

    # Function that runs when the "Power Off" or "Return Home" buttons are clicked
    def switch_to_start(self):
        self.stop_camera()
        self.stack.setCurrentWidget(self.start)

    # Function that runs when the "Calibration" button is clicked
    def switch_to_calibration(self):
        self.stack.setCurrentWidget(self.calibration)
    
    # Function that runs when the "Modify Parameters" button is clicked
    def switch_to_parameters(self):
        self.stack.setCurrentWidget(self.parameters)

    # Function that runs when the Haptic Feedback slider is moved
    def update_haptic_value(self, value):
        self.parameters.label.setText(f"Haptic Sensitivity: {value}")
        self.haptic_sensitivity = value

    def start_camera(self):
        self.camera = Picamera2()  # Initialize the Pi Camera
        self.camera.configure(self.camera.create_preview_configuration())  
        self.camera.start()  # Start capturing
        
        self.timer = QTimer()  # Create a timer to update the video feed
        self.timer.timeout.connect(self.update_frame)  
        self.timer.start(30)  # Update every 30ms (~30 FPS)
    
    def update_frame(self):
        frame = self.camera.capture_array()  # Get a NumPy array of the frame
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)  # Convert BGR to RGB

        # Convert NumPy array to QImage
        height, width, channel = frame.shape
        bytes_per_line = channel * width
        qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)

        # Set image to QLabel
        self.video_label.setPixmap(QPixmap.fromImage(qimg))

    def stop_camera(self):
        if hasattr(self, 'timer'):
            self.timer.stop()  # Stop the timer
        if hasattr(self, 'camera'):
            self.camera.stop()  # Stop the camera

# Main function to run the application
def main():
    app = QApplication(sys.argv)  # Create the application object
    window = MainWindow()  # Create the main window
    window.showMaximized()  # Show the window
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
