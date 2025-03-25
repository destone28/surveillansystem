import time
from vl53l1x import VL53L1X
from machine import I2C
import pyb
import logger

class DistanceDetector:
    def __init__(self, config):
        self.config = config
        self.tof = None
        self.base_distance = None
        self.distance_enabled = False
        self.last_distances = []  # Buffer for moving average
        self.debug_counter = 0
        
        self.init_distance_sensor()
        
    def init_distance_sensor(self):
        """Initializes the ToF distance sensor VL53L1X"""
        logger.info("Initializing ToF distance sensor...")
        
        try:
            # Initialize I2C
            i2c = I2C(2)
            time.sleep(0.1)  # Short pause after I2C initialization
            
            # Initialize the sensor
            self.tof = VL53L1X(i2c)
            time.sleep(0.5)  # Pause for stabilization
            
            # Set the measurement mode to long range
            if hasattr(self.tof, 'set_measurement_timing_budget'):
                self.tof.set_measurement_timing_budget(50000)  # Use 50ms for higher accuracy
            
            # Initial calibration: multiple readings
            self.calibrate_distance()
            
            if self.base_distance > 0:
                self.distance_enabled = True
                logger.info(f"ToF sensor initialized: {self.base_distance}mm")
            else:
                logger.error("Error reading initial distance from ToF sensor")
        except Exception as e:
            logger.error(f"Error initializing ToF sensor: {e}")
            
    def calibrate_distance(self):
        """Calibrates the base distance with the average of multiple readings"""
        readings = []
        valid_readings = 0
        
        # Perform 5 readings for stable calibration
        for i in range(5):
            dist = self.read_distance_raw()
            if dist > 0:
                readings.append(dist)
                valid_readings += 1
            time.sleep(0.1)
        
        # Calculate the average of valid readings
        if valid_readings > 0:
            self.base_distance = sum(readings) / valid_readings
            self.last_distances = [self.base_distance] * 3  # Initialize buffer
            logger.info(f"Base distance calibrated: {self.base_distance:.1f}mm ({valid_readings} readings)")
        else:
            self.base_distance = 0
            logger.error("Calibration failed: no valid readings")
            
    def read_distance_raw(self):
        """Reads the raw distance from the ToF sensor"""
        try:
            if self.tof:
                # The read() function returns the distance in millimeters
                distance = self.tof.read()
                return distance
            return 0
        except Exception as e:
            logger.debug(f"Error reading raw distance from ToF: {e}", verbose=True)
            return 0
            
    def read_distance(self):
        """Reads the filtered distance from the ToF sensor"""
        raw_distance = self.read_distance_raw()
        
        if raw_distance <= 0:
            return 0
            
        # Add to the buffer and keep only the last 3 values
        self.last_distances.append(raw_distance)
        if len(self.last_distances) > 3:
            self.last_distances.pop(0)
            
        # Calculate the average to reduce noise
        avg_distance = sum(self.last_distances) / len(self.last_distances)
        return avg_distance
            
    def check_distance(self):
        """Checks if the current distance exceeds the threshold"""
        if not self.distance_enabled:
            return False
            
        try:
            # Increment the debug counter
            self.debug_counter += 1
            
            # Periodic log every 20 checks
            if self.debug_counter % 20 == 0:
                logger.debug(f"Distance check active, threshold: {self.config.DISTANCE_THRESHOLD}mm", verbose=True)
            
            current_distance = self.read_distance()
            if current_distance <= 0:  # Invalid reading
                return False
                
            diff = abs(current_distance - self.base_distance)
            
            # More frequent log for debugging
            if self.debug_counter % 10 == 0:
                logger.debug(f"Current distance: {current_distance:.1f}mm, base: {self.base_distance:.1f}mm, diff: {diff:.1f}mm", verbose=True)
            
            if diff > self.config.DISTANCE_THRESHOLD:
                logger.info(f"Alert! Distance changed: {current_distance:.1f}mm (diff: {diff:.1f}mm)")
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking distance: {e}")
            return False
            
    def recalibrate(self):
        """Recalibrates the base distance"""
        try:
            logger.info("Recalibrating distance sensor...")
            self.calibrate_distance()
            return self.base_distance > 0
        except Exception as e:
            logger.error(f"Error recalibrating ToF: {e}")
            return False