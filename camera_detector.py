import os
import time
import pyb
import sensor
import image
import gc
import logger

# LED for visual feedback
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

class CameraDetector:
    def __init__(self, config):
        print("### INITIALIZATION OF SIMPLIFIED CAMERA DETECTOR SUCCESSFUL ###")
        self.config = config
        self.prev_brightness = None
        self.camera_enabled = False
        self.frame_count = 0
        
        # Print configuration
        print(f"Configured motion threshold: {self.config.MOTION_THRESHOLD}")
        
        # Garbage collection
        gc.collect()
        print(f"Free memory: {gc.mem_free()} bytes")
        
        # Initialize the camera
        self.init_camera()
    
    def init_camera(self):
        """Initialize the camera with minimal settings"""
        print(">> Simplified camera initialization...")
        try:
            # Full reset
            sensor.reset()
            
            # Use grayscale and minimal resolution
            sensor.set_pixformat(sensor.GRAYSCALE)
            sensor.set_framesize(sensor.QQVGA)  # 160x120
            
            # Skip frames for stabilization
            sensor.skip_frames(time=300)
            
            # Capture initial frame
            print(">> Sensor stabilization...")
            sensor.snapshot()
            
            self.camera_enabled = True
            print(">> Camera successfully initialized")
            
            # Visual signal
            green_led.on()
            time.sleep(0.2)
            green_led.off()
            
        except Exception as e:
            print(f"!!! CAMERA INITIALIZATION ERROR: {e}")
            logger.error(f"Camera initialization error: {e}")
    
    def check_motion(self):
        """Ultra-simplified motion detection method"""
        if not self.camera_enabled:
            return False
        
        try:
            # Increment frame counter
            self.frame_count += 1
            
            # Capture a frame
            img = sensor.snapshot()
            
            # Calculate average brightness using the histogram
            # This is more reliable and avoids type issues
            hist = img.get_histogram()
            stats = hist.get_statistics()
            current_mean = stats.mean()  # This will always be a single numeric value
            
            # Debug every 20 frames
            if self.frame_count % 20 == 0:
                print(f">> Frame #{self.frame_count}, Average brightness: {current_mean:.2f}")
            
            # If it's the first frame, save the value and exit
            if self.prev_brightness is None:
                self.prev_brightness = current_mean
                print(f">> First frame, base brightness: {current_mean:.2f}")
                return False
            
            # Calculate brightness difference in percentage
            diff = abs(current_mean - self.prev_brightness)
            diff_percent = (diff / 255) * 100
            
            # Gradually update the previous value (ensuring it's numeric)
            # This resolves the type issue
            self.prev_brightness = (self.prev_brightness * 0.7) + (current_mean * 0.3)
            
            # Debug
            if self.frame_count % 20 == 0:
                print(f">> Brightness difference: {diff_percent:.2f}% (threshold: {self.config.MOTION_THRESHOLD}%)")
                print(f">> Type of prev_brightness: {type(self.prev_brightness)}")
            
            # Check if it exceeds the threshold
            if diff_percent > self.config.MOTION_THRESHOLD:
                print(f"!!! MOTION DETECTED !!! diff: {diff_percent:.2f}%")
                red_led.on()
                time.sleep(0.1)
                red_led.off()
                return True
                
        except Exception as e:
            print(f"!!! MOTION CHECK ERROR: {e}")
            logger.error(f"Motion check error: {e}")
            # Important: reset the value for safety
            self.prev_brightness = None
            
        return False
    
    def reset_detection(self):
        """Reset motion detection"""
        print(">> Resetting motion detection")
        # Ensure proper reset
        self.prev_brightness = None  # This resolves the issue after a reset
        self.frame_count = 0  # Also reset the frame counter
        logger.info("Motion detection reset")