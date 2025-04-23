#!/usr/bin/env python3
# filepath: untitled:Untitled-1

import sys
import os
import time
import cv2
import numpy as np
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
                            QSpinBox, QDoubleSpinBox, QFileDialog, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

# Import Thorlabs SDK
try:
    from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCamera
    from thorlabs_tsi_sdk.tl_camera_enums import SENSOR_TYPE
except ImportError:
    print("Error: Thorlabs TSI SDK not found. Please install it using:")
    print("pip install thorlabs_tsi_sdk")
    sys.exit(1)

class ThorlabsCameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.camera = None
        self.sdk = None
        self.recording = False
        self.video_writer = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.fps = 30
        # Recording limit attributes
        self.record_duration_limit = 0
        self.record_frame_limit = 0
        self.recorded_frame_count = 0
        
        self.init_ui()
        self.connect_camera()
        
    def init_ui(self):
        # Main window setup
        self.setWindowTitle("Thorlabs Camera Control")
        self.setGeometry(100, 100, 1000, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Camera display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        main_layout.addWidget(self.image_label)
        
        # Status bar for information
        self.statusBar().showMessage("Starting camera...")
        
        # Control panel
        controls_layout = QHBoxLayout()
        
        # --- Exposure Controls ---
        exposure_group = QGroupBox("Exposure Control")
        exposure_layout = QVBoxLayout()
        exposure_group.setLayout(exposure_layout)
        
        # Exposure slider and value display
        exposure_header = QHBoxLayout()
        exposure_layout.addLayout(exposure_header)
        
        exposure_header.addWidget(QLabel("Exposure Time (ms):"))
        self.exposure_value = QDoubleSpinBox()
        self.exposure_value.setRange(0.1, 1000.0)
        self.exposure_value.setValue(10.0)
        self.exposure_value.setSingleStep(1.0)
        self.exposure_value.valueChanged.connect(self.set_exposure)
        exposure_header.addWidget(self.exposure_value)
        
        self.exposure_slider = QSlider(Qt.Horizontal)
        self.exposure_slider.setRange(1, 10000)  # 0.1 ms to 1000 ms (scaled by 10)
        self.exposure_slider.setValue(100)  # 10.0 ms default
        self.exposure_slider.valueChanged.connect(self.exposure_slider_changed)
        exposure_layout.addWidget(self.exposure_slider)
        
        # --- Framerate Controls ---
        framerate_group = QGroupBox("Framerate Control")
        framerate_layout = QVBoxLayout()
        framerate_group.setLayout(framerate_layout)
        
        framerate_header = QHBoxLayout()
        framerate_layout.addLayout(framerate_header)
        
        framerate_header.addWidget(QLabel("Frame Rate (FPS):"))
        self.framerate_value = QSpinBox()
        self.framerate_value.setRange(1, 100)
        self.framerate_value.setValue(30)
        self.framerate_value.valueChanged.connect(self.set_framerate)
        framerate_header.addWidget(self.framerate_value)
        
        self.framerate_slider = QSlider(Qt.Horizontal)
        self.framerate_slider.setRange(1, 100)
        self.framerate_slider.setValue(30)
        self.framerate_slider.valueChanged.connect(self.framerate_slider_changed)
        framerate_layout.addWidget(self.framerate_slider)
        
        # Actual FPS display
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Actual FPS:"))
        self.fps_label = QLabel("0")
        fps_layout.addWidget(self.fps_label)
        framerate_layout.addLayout(fps_layout)
        
        # --- Recording Controls ---
        recording_group = QGroupBox("Recording")
        recording_layout = QVBoxLayout()
        recording_group.setLayout(recording_layout)
        
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        recording_layout.addWidget(self.record_button)
        
        self.recording_label = QLabel("Not Recording")
        recording_layout.addWidget(self.recording_label)
        # Controls for recording limits
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (s):"))
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0, 3600)
        self.duration_spinbox.setValue(0)
        duration_layout.addWidget(self.duration_spinbox)
        recording_layout.addLayout(duration_layout)
        frames_layout = QHBoxLayout()
        frames_layout.addWidget(QLabel("Frame Count:"))
        self.framecount_spinbox = QSpinBox()
        self.framecount_spinbox.setRange(0, 1000000)
        self.framecount_spinbox.setValue(0)
        frames_layout.addWidget(self.framecount_spinbox)
        recording_layout.addLayout(frames_layout)
        
        # Add control groups to main control layout
        controls_layout.addWidget(exposure_group)
        controls_layout.addWidget(framerate_group)
        controls_layout.addWidget(recording_group)
        
        # Add control panel to main layout
        main_layout.addLayout(controls_layout)
        
    def connect_camera(self):
        try:
            # Initialize SDK
            self.sdk = TLCameraSDK()
            available_cameras = self.sdk.discover_available_cameras()
            
            if not available_cameras:
                self.statusBar().showMessage("No cameras found!")
                return
            
            # Connect to the first available camera
            self.camera = self.sdk.open_camera(available_cameras[0])
            
            # Configure camera
            self.camera.frames_per_trigger_zero_for_unlimited = 0  # Continuous acquisition
            self.camera.exposure_time_us = int(self.exposure_value.value() * 1000)  # Convert ms to μs
            self.camera.image_poll_timeout_ms = 1000  # 1 second timeout
            
            # Start the camera
            self.camera.arm(2)  # 2 buffers for frame acquisition
            self.camera.issue_software_trigger()
            
            # Start the timer for frame updating
            self.set_framerate(self.framerate_value.value())
            self.timer.start(int(1000 / self.fps))
            
            self.statusBar().showMessage(f"Connected to {self.camera.name}")
            
        except Exception as e:
            self.statusBar().showMessage(f"Error connecting to camera: {str(e)}")
            print(f"Error: {str(e)}")
    
    def update_frame(self):
        if not self.camera:
            return
        
        try:
            # Trigger acquisition of the next frame for live display
            self.camera.issue_software_trigger()
            # Get frame from camera
            frame = self.camera.get_pending_frame_or_null()
            if frame is None:
                return
            
            # Determine frame dimensions, fallback to camera sensor size if necessary
            try:
                width = frame.image_buffer_size_pixels_horizontal
                height = frame.image_buffer_size_pixels_vertical
            except AttributeError:
                width = self.camera.sensor_width_pixels
                height = self.camera.sensor_height_pixels
            
            bit_depth = self.camera.bit_depth
            
            # Convert frame to numpy array
            image_data = frame.image_buffer
            
            # Create numpy array from image data
            if bit_depth <= 8:
                image = np.frombuffer(image_data, dtype=np.uint8).reshape(height, width)
            else:
                # For 16-bit images, we need to rescale to 8-bit for display
                image = np.frombuffer(image_data, dtype=np.uint16).reshape(height, width)
                image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            
            # Record video if needed
            if self.recording and self.video_writer:
                # OpenCV expects BGR format, but our image is grayscale
                # Convert to BGR by duplicating the channels
                color_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                self.video_writer.write(color_image)
                # Update recording duration and frame count
                duration = time.time() - self.recording_start_time
                self.recorded_frame_count += 1
                self.recording_label.setText(f"Recording: {duration:.1f}s, Frames: {self.recorded_frame_count}")
                # Auto-stop if limits reached
                if (self.record_duration_limit > 0 and duration >= self.record_duration_limit) or (self.record_frame_limit > 0 and self.recorded_frame_count >= self.record_frame_limit):
                    self.toggle_recording()
                    return
                
            # Display the image
            q_image = QImage(image.data, width, height, width, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image)
            
            # Scale pixmap to fit the label while maintaining aspect ratio
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.width(), 
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            
            # Calculate and show actual FPS
            self.frame_count += 1
            elapsed = time.time() - self.last_frame_time
            if elapsed >= 1.0:  # Update FPS display every second
                actual_fps = self.frame_count / elapsed
                self.fps_label.setText(f"{actual_fps:.1f}")
                self.frame_count = 0
                self.last_frame_time = time.time()
                
        except Exception as e:
            self.statusBar().showMessage(f"Error acquiring frame: {str(e)}")
            print(f"Frame error: {str(e)}")
    
    def exposure_slider_changed(self):
        # Convert slider value (which is integer) to actual exposure in ms
        exposure_ms = self.exposure_slider.value() / 10.0
        self.exposure_value.blockSignals(True)
        self.exposure_value.setValue(exposure_ms)
        self.exposure_value.blockSignals(False)
        self.set_exposure(exposure_ms)
    
    def set_exposure(self, value_ms):
        if self.camera:
            # Convert from ms to μs for the camera
            self.camera.exposure_time_us = int(value_ms * 1000)
            self.statusBar().showMessage(f"Exposure set to {value_ms} ms")
            # Update slider if value was changed directly
            slider_value = int(value_ms * 10)
            if self.exposure_slider.value() != slider_value:
                self.exposure_slider.blockSignals(True)
                self.exposure_slider.setValue(slider_value)
                self.exposure_slider.blockSignals(False)
    
    def framerate_slider_changed(self):
        fps = self.framerate_slider.value()
        self.framerate_value.blockSignals(True)
        self.framerate_value.setValue(fps)
        self.framerate_value.blockSignals(False)
        self.set_framerate(fps)
    
    def set_framerate(self, fps):
        self.fps = fps
        if self.timer.isActive():
            self.timer.stop()
            self.timer.start(int(1000 / fps))
        self.statusBar().showMessage(f"Frame rate set to {fps} FPS")
        # Update slider if value was changed directly
        if self.framerate_slider.value() != fps:
            self.framerate_slider.blockSignals(True)
            self.framerate_slider.setValue(fps)
            self.framerate_slider.blockSignals(False)
    
    def toggle_recording(self):
        if not self.recording:
            # Start recording
            try:
                filename, _ = QFileDialog.getSaveFileName(
                    self, "Save Video", 
                    f"camera_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                    "Video Files (*.mp4)"
                )
                if filename:
                    # Use sensor dimensions for resolution to avoid missing frame attributes
                    if self.camera:
                        width = self.camera.sensor_width_pixels
                        height = self.camera.sensor_height_pixels
                    else:
                        width, height = 1280, 1024
                    
                    # Initialize video writer with MJPG codec which has good compatibility with MP4
                    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                    # Ensure filename has .mp4 extension
                    if not filename.lower().endswith('.mp4'):
                        filename = filename + '.mp4'
                    
                    self.video_writer = cv2.VideoWriter(
                        filename, fourcc, self.fps, (width, height)
                    )
                    
                    if self.video_writer.isOpened():
                        self.recording = True
                        self.recording_start_time = time.time()
                        # Initialize recording limits
                        self.record_duration_limit = self.duration_spinbox.value()
                        self.record_frame_limit = self.framecount_spinbox.value()
                        self.recorded_frame_count = 0
                        self.record_button.setText("Stop Recording")
                        self.recording_label.setText("Recording started")
                        self.statusBar().showMessage(f"Recording to {filename}")
                    else:
                        self.statusBar().showMessage("Failed to create video writer")
            except Exception as e:
                self.statusBar().showMessage(f"Recording error: {str(e)}")
                print(f"Recording error: {str(e)}")
                self.video_writer = None
        else:
            # Stop recording
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            self.recording = False
            self.record_button.setText("Start Recording")
            self.recording_label.setText("Not Recording")
            self.statusBar().showMessage("Recording stopped")
    
    def closeEvent(self, event):
        # Cleanup when application is closed
        if self.recording and self.video_writer:
            self.video_writer.release()
        
        if self.camera:
            self.camera.disarm()
            self.camera.dispose()
        
        if self.sdk:
            self.sdk.dispose()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ThorlabsCameraApp()
    window.show()
    sys.exit(app.exec_())