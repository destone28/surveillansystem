import sensor
import time
import pyb

# LED for visual feedback
red_led = pyb.LED(1)

def debug_print(msg):
    print(msg)

class PhotoManager:
    def __init__(self, config, file_manager):
        """
        Photo manager responsible for capturing and saving images
        
        Args:
            config: System configuration
            file_manager: Reference to the file manager
        """
        self.config = config
        self.file_manager = file_manager
        self.camera_enabled = False
        self.current_mode = None  # No initial mode
        self.last_photo_path = None  # Tracks the last saved photo path
        
        # Initial attempt to initialize the camera
        try:
            sensor.reset()
            self.camera_enabled = True
            debug_print("Camera available for the PhotoManager")
        except Exception as e:
            debug_print(f"Error initializing camera in PhotoManager: {e}")
    
    def init_camera_for_motion(self):
        """Initializes the camera for motion detection (grayscale)"""
        if not self.camera_enabled:
            debug_print("Camera not available")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.GRAYSCALE)  # Use grayscale for motion detection
            sensor.set_framesize(self.config.FRAME_SIZE)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=2000)
            
            self.current_mode = "motion"
            debug_print("Camera initialized for motion detection")
            debug_print(f"Image size: {sensor.width()}x{sensor.height()}")
            return True
        except Exception as e:
            debug_print(f"Camera camera error: {e}")
            return False
    
    def init_camera_for_photo(self, for_telegram=False):
        """
        Initializes the camera for taking photos (RGB)
        
        Args:
            for_telegram: If True, use a lower resolution for photos intended for Telegram
        """
        if not self.camera_enabled:
            debug_print("Camera not available")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)
            
            # Use a lower resolution if the photo is for Telegram
            if for_telegram and hasattr(self.config, 'TELEGRAM_PHOTO_SIZE'):
                sensor.set_framesize(self.config.TELEGRAM_PHOTO_SIZE)
                debug_print("Camera initialized for Telegram photos at low resolution")
            else:
                sensor.set_framesize(self.config.PHOTO_SIZE)
                debug_print("Camera initialized for standard resolution photos")
                
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=100)
            
            self.current_mode = "photo"
            debug_print("Camera initialized for photos")
            return True
        except Exception as e:
            debug_print(f"Photo camera error: {e}")
            return False
    
    def capture_save_photo(self, directory, prefix=None, extra_info=None, for_telegram=False):
        """
        Captures a photo and saves it in the specified directory
        
        Args:
            directory: The directory where the image will be saved
            prefix: Optional prefix for the file name (default: 'img')
            extra_info: Additional information to include in the file name
            for_telegram: If True, uses lower quality for photos intended for Telegram
            
        Returns:
            bool: True if the photo was captured and saved, False otherwise
        """
        if not self.camera_enabled:
            debug_print("Camera not available for photos")
            return False
            
        # Switch to photo mode if necessary
        if self.current_mode != "photo":
            if not self.init_camera_for_photo(for_telegram):
                return False
        
        try:
            # Turn on the red LED during capture
            red_led.on()
            
            # Capture the image
            img = sensor.snapshot()
            
            # Generate file name with timestamp
            timestamp = int(time.time())
            
            # Default prefix if not provided
            if not prefix:
                prefix = "img"
                
            # File name format
            if extra_info:
                filename = f"{directory}/{prefix}_{timestamp}_{extra_info}.jpg"
            else:
                filename = f"{directory}/{prefix}_{timestamp}.jpg"
            
            # Determine photo quality based on destination
            if for_telegram and hasattr(self.config, 'TELEGRAM_PHOTO_QUALITY'):
                quality = self.config.TELEGRAM_PHOTO_QUALITY
            else:
                quality = self.config.PHOTO_QUALITY
            
            # Save the image
            success = self.file_manager.save_image(img, filename, quality)
            
            # Save the path of the last photo for reference
            if success:
                self.last_photo_path = filename
                debug_print(f"Last photo path updated: {self.last_photo_path}")
                
                # Handle FIFO logic
                max_files = self.config.MAX_TELEGRAM_PHOTOS if directory == "telegram_request" else self.config.MAX_IMAGES
                self.file_manager.manage_files(directory, max_files)
            
            # Turn off the red LED
            red_led.off()
            
            return success
        except Exception as e:
            debug_print(f"Error capturing photo: {e}")
            red_led.off()
            return False
        finally:
            # In any case, attempt to restore the camera to motion detection mode
            # if it was in that mode before
            if self.current_mode == "photo" and getattr(self, 'previous_mode', None) == "motion":
                self.init_camera_for_motion()
                
    def capture_telegram_photo(self, directory="telegram_request", prefix="tg", extra_info=None):
        """
        Captures a photo specifically optimized for Telegram
        
        Args:
            directory: The directory where the image will be saved
            prefix: Prefix for the file name
            extra_info: Additional information to include in the file name
            
        Returns:
            bool: True if the photo was captured and saved, False otherwise
        """
        # Ensure the directory exists
        try:
            self.file_manager.ensure_directory(directory)
        except:
            pass
            
        # Store the current mode to restore it later
        prev_mode = self.current_mode
        
        # Configure the camera with very low resolution for Telegram
        if hasattr(sensor, 'QQVGA'):  # 160x120
            size_to_use = sensor.QQVGA
        elif hasattr(sensor, 'QQCIF'):  # 88x72
            size_to_use = sensor.QQCIF
        else:
            size_to_use = sensor.QVGA  # Fallback to slightly higher resolution if necessary
            
        try:
            # Configure the camera for maximum compression
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)  # RGB565 for color but with less data than JPEG
            sensor.set_framesize(size_to_use)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=100)
            
            # Capture the image
            red_led.on()
            img = sensor.snapshot()
            red_led.off()
            
            # Generate file name with timestamp
            timestamp = int(time.time())
            
            # File name format
            if extra_info:
                filename = f"{directory}/{prefix}_{timestamp}_{extra_info}.jpg"
            else:
                filename = f"{directory}/{prefix}_{timestamp}.jpg"
            
            # Use very low quality to reduce file size
            quality = 35  # Very low JPEG quality (0-100)
            if hasattr(self.config, 'TELEGRAM_PHOTO_QUALITY'):
                quality = self.config.TELEGRAM_PHOTO_QUALITY
            
            # Save the image
            success = self.file_manager.save_image(img, filename, quality)
            
            if success:
                self.last_photo_path = filename
                debug_print(f"Telegram photo saved: {self.last_photo_path}")
                
                # Handle FIFO logic (fewer files for Telegram photos)
                max_files = 5
                if hasattr(self.config, 'MAX_TELEGRAM_PHOTOS'):
                    max_files = self.config.MAX_TELEGRAM_PHOTOS
                    
                self.file_manager.manage_files(directory, max_files)
                
            return success
            
        except Exception as e:
            debug_print(f"Error capturing photo for Telegram: {e}")
            return False
        finally:
            # Restore the previous mode
            if prev_mode == "motion":
                self.init_camera_for_motion()