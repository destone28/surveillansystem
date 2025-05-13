import sensor
import time
import mjpeg
import os
import gc
import pyb
import logger

# LEDs for debugging
red_led = pyb.LED(1)
blue_led = pyb.LED(3)

class VideoManager:
    def __init__(self, config, file_manager):
        """
        Video manager responsible for recording and saving videos
        
        Args:
            config: System configuration
            file_manager: Reference to the file manager
        """
        self.config = config
        self.file_manager = file_manager
        self.camera_enabled = False
        self.current_mode = None  # No initial mode
        self.last_video_path = None  # Tracks the last saved video
        self.telegram_manager = None  # Will be set by the main program
        
        # Create directories for videos
        self.file_manager.ensure_directory("camera_videos")
        self.file_manager.ensure_directory("audio_videos")
        self.file_manager.ensure_directory("distance_videos")
        
        # Initial attempt to initialize the camera
        try:
            sensor.reset()
            self.camera_enabled = True
            logger.info("Camera available for VideoManager")
        except Exception as e:
            logger.error(f"Error initializing camera in VideoManager: {e}")
    
    def init_camera_for_video(self):
        """Initializes the camera for video recording (RGB565)"""
        if not self.camera_enabled:
            logger.warning("Camera not available for video")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)  # RGB565 for video
            sensor.set_framesize(sensor.QVGA)    # QVGA (320x240) for video
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=1000)  # Wait for stabilization
            
            self.current_mode = "video"
            logger.info("Camera initialized for video recording")
            return True
        except Exception as e:
            logger.error(f"Camera video error: {e}")
            return False
    
    def record_video(self, event_type, extra_info=None):
        """
        Records a video and saves it in the appropriate directory
        
        Args:
            event_type: Type of event ("camera", "audio", "distance")
            extra_info: Additional information to include in the file name
            
        Returns:
            bool: True if the video was recorded and saved, False otherwise
        """
        if not self.camera_enabled:
            logger.warning("Camera not available for video")
            return False
            
        # Store the current mode to restore it later
        prev_mode = self.current_mode
        
        try:
            # Initialize the camera for video
            if not self.init_camera_for_video():
                return False
                
            # Force garbage collection before starting recording
            gc.collect()
            
            # Determine the save directory based on the event type
            if event_type == "camera":
                directory = "camera_videos"
            elif event_type == "audio":
                directory = "audio_videos"
            elif event_type == "distance":
                directory = "distance_videos"
            else:
                directory = "other_videos"
                
            # Ensure the directory exists
            self.file_manager.ensure_directory(directory)
                
            # Generate filename with timestamp
            timestamp = int(time.time())
            
            if extra_info:
                filename = f"{directory}/video_{timestamp}_{extra_info}.mjpeg"
            else:
                filename = f"{directory}/video_{timestamp}.mjpeg"
                
            logger.info(f"Starting video recording: {filename}")
            
            # Turn on the red LED during recording
            red_led.on()
            blue_led.on()  # Add blue LED to distinguish video recording
            
            # Create the Mjpeg object
            video = mjpeg.Mjpeg(filename)
            
            # Record the video for the configured duration
            frames_to_record = self.config.VIDEO_DURATION * self.config.VIDEO_FPS
            
            clock = time.clock()  # To track FPS
            
            start_time = time.time()
            actual_frames = 0
            
            while time.time() - start_time < self.config.VIDEO_DURATION:
                if actual_frames >= frames_to_record:
                    break
                    
                clock.tick()
                
                # Force garbage collection periodically
                if actual_frames % 5 == 0:
                    gc.collect()
                    
                img = sensor.snapshot()
                
                # Add timestamp to the video
                current_time = time.localtime()
                timestamp_text = f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
                img.draw_string(5, 5, timestamp_text, color=(255, 255, 255), scale=2)
                
                # Add event type label
                event_label = f"Event: {event_type.upper()}"
                img.draw_string(5, sensor.height() - 20, event_label, color=(255, 255, 255), scale=2)
                
                # Use reduced quality for video to save memory
                quality = min(self.config.VIDEO_QUALITY, 50)
                
                # Write the frame to the video with the specified quality
                video.write(img, quality=self.config.VIDEO_QUALITY)
                actual_frames += 1
                
                # If recording faster than the target FPS, add a delay
                target_frame_time = 1.0 / self.config.VIDEO_FPS
                elapsed = clock.avg() / 1000.0  # convert to seconds
                
                if elapsed < target_frame_time:
                    delay = target_frame_time - elapsed
                    time.sleep(delay)
                    
                # Debug update every 10 frames
                if actual_frames % 10 == 0:
                    logger.debug(f"Video recording: {actual_frames}/{frames_to_record} frames, FPS: {clock.fps()}", verbose=True)
                    
                    # Toggle blue LED for visual feedback during recording
                    if actual_frames % 20 == 0:
                        blue_led.toggle()
            
            # Close the video
            video.close()
            
            # Turn off the LEDs
            red_led.off()
            blue_led.off()
            
            # Update the last video path
            self.last_video_path = filename
            logger.info(f"Video saved: {self.last_video_path}, {actual_frames} frames")
            
            # Force memory cleanup
            gc.collect()
            
            # Handle FIFO file management
            max_videos = 5  # Default limit
            if hasattr(self.config, 'MAX_VIDEOS'):
                max_videos = self.config.MAX_VIDEOS
                
            self.file_manager.manage_files(directory, max_videos)
            
            return True
            
        except Exception as e:
            logger.error(f"Video recording error: {e}")
            red_led.off()
            blue_led.off()
            return False
            
        finally:
            # Force garbage collection
            gc.collect()
            
            # Restore the previous camera mode
            if prev_mode == "motion":
                # Restore the mode for motion detection
                try:
                    sensor.reset()
                    sensor.set_pixformat(sensor.GRAYSCALE)
                    sensor.set_framesize(self.config.FRAME_SIZE)
                    sensor.set_vflip(False)
                    sensor.set_hmirror(True)
                    sensor.skip_frames(time=500)
                    self.current_mode = "motion"
                except Exception as e:
                    logger.error(f"Error restoring motion camera mode: {e}")
