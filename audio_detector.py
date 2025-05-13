import time
import pyb
import audio
import sensor
import logger
import secrets_keys

# LED for debugging
green_led = pyb.LED(2)

# Global variable for the AudioDetector instance (will be set during initialization)
global_audio_detector = None

# Global callback function for audio
def global_audio_callback(buf):
    global global_audio_detector
    if global_audio_detector:
        global_audio_detector.process_audio(buf)

class AudioDetector:
    def __init__(self, config, file_manager, photo_manager):
        global global_audio_detector
        global_audio_detector = self  # Assign this instance to the global variable
        
        self.config = config
        self.file_manager = file_manager
        self.photo_manager = photo_manager
        self.cloud_manager = None  # Will be set by the main
        self.telegram_manager = None  # Will be set by the main
        self.video_manager = None  # Will be set by the main
        self.audio_enabled = False
        self.last_capture_time = 0
        self.is_processing = False  # Flag to prevent overlapping processing
        self.last_threshold_change_time = 0  # Track when threshold was last changed
        self.threshold_change_cooldown = 2  # Cooldown period in seconds after threshold change
        self.audio_streaming_active = False  # Track if streaming is active
        self.init_audio()

    def init_audio(self):
        """Initialize audio only"""
        logger.info("Initializing audio detector...")

        # Audio (initialization only, streaming is started separately)
        try:
            audio.init(channels=1, frequency=16000, gain_db=self.config.AUDIO_GAIN, highpass=0.9883)
            self.audio_enabled = True
            logger.info(f"Audio initialized with gain {self.config.AUDIO_GAIN}dB")
        except Exception as e:
            logger.error(f"Audio error: {e}")

    def process_audio(self, buf):
        """Process audio data received from the callback"""
        # IMPORTANT: Multiple layers of validation to prevent false positives and duplicated messages
        
        # Check if already processing to prevent overlapping executions
        if self.is_processing:
            return
            
        # Check if audio detection is enabled
        if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
            return
            
        # Check if audio streaming is actually active
        if not self.audio_streaming_active:
            return
            
        # Check if we're in the cooldown period after a threshold change
        current_time = time.time()
        if current_time - self.last_threshold_change_time < self.threshold_change_cooldown:
            return

        # Lock the processing to prevent concurrent execution
        self.is_processing = True
        
        try:
            # Convert bytes to signed int values
            samples = [buf[i] | (buf[i+1] << 8) for i in range(0, len(buf), 2)]
            
            # Check for empty buffer
            if not samples:
                self.is_processing = False
                return
                
            # Calculate the average audio level
            level = sum(abs(s) for s in samples) / len(samples)

            # Check against threshold - make sure threshold is valid
            if self.config.SOUND_THRESHOLD <= 0:
                self.is_processing = False
                return
                
            # Verify level exceeds threshold
            if level > self.config.SOUND_THRESHOLD:
                logger.info(f"Sound detected: {level} (threshold: {self.config.SOUND_THRESHOLD})")
                
                # Check inhibition period
                if current_time - self.last_capture_time < self.config.INHIBIT_PERIOD:
                    self.is_processing = False
                    return
                    
                # Update last capture time immediately to prevent duplicate triggers
                self.last_capture_time = current_time
                
                # Blink green LED for debugging
                green_led.on()
                
                # Double-check that audio monitoring is still enabled
                # This prevents notifications if the feature was turned off during processing
                if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                    green_led.off()
                    self.is_processing = False
                    return
                
                # Capture photo
                photo_path = None
                telegram_photo_path = None
                
                # First save a normal photo for local storage
                if self.photo_manager.capture_save_photo("audio_alert", "sound", int(level)):
                    photo_path = self.photo_manager.last_photo_path
                    
                    # Triple-check that audio monitoring is still enabled
                    # This prevents notifications if the feature was turned off during photo capture
                    if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                        green_led.off()
                        self.is_processing = False
                        return
                    
                    # Now capture a photo optimized for Telegram if photo sending is enabled
                    if hasattr(self.config, 'SEND_PHOTOS_TELEGRAM') and self.config.SEND_PHOTOS_TELEGRAM:
                        if self.photo_manager.capture_telegram_photo("audio_alert", f"tg_sound", int(level)):
                            telegram_photo_path = self.photo_manager.last_photo_path

                    # Final check before video recording
                    if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                        green_led.off()
                        self.is_processing = False
                        return
                        
                    # Record video if enabled
                    if hasattr(self.config, 'RECORD_VIDEO_ENABLED') and self.config.RECORD_VIDEO_ENABLED and self.video_manager:
                        if self.video_manager.record_video("audio", f"sound_{int(level)}"):
                            video_path = self.video_manager.last_video_path
                            
                            # Check settings again after recording
                            if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                                green_led.off()
                                self.is_processing = False
                                return
                            
                            # Telegram notification
                            if self.telegram_manager and hasattr(self.config, 'SEND_VIDEOS_TELEGRAM') and self.config.SEND_VIDEOS_TELEGRAM:
                                try:
                                    for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                        if chat_id != "*":  # Ignore the asterisk
                                            self.telegram_manager.send_message(chat_id, "🎥 Sound video recording completed!")
                                            self.telegram_manager.send_video(
                                                chat_id,
                                                video_path,
                                                f"🎥 Sound detection video - Level: {int(level)}"
                                            )
                                except Exception as e:
                                    logger.error(f"Error sending video to Telegram: {e}")
                    
                    # Final check before sending cloud notifications
                    if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                        green_led.off()
                        self.is_processing = False
                        return
                    
                    # Cloud notification if available
                    if self.cloud_manager:
                        self.cloud_manager.notify_event("Audio", f"Level: {int(level)}")
                    
                    # Final check before sending Telegram notifications
                    if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
                        green_led.off()
                        self.is_processing = False
                        return
                    
                    # Telegram notification if available
                    if self.telegram_manager:
                        try:
                            for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                if chat_id != "*":  # Ignore the asterisk
                                    # Send text message
                                    self.telegram_manager.send_message(chat_id, f"🔊 Sound detected! Level: {int(level)}")
                                    
                                    # Send photo (only if enabled and available)
                                    if hasattr(self.config, 'SEND_PHOTOS_TELEGRAM') and self.config.SEND_PHOTOS_TELEGRAM and telegram_photo_path:
                                        self.telegram_manager.send_photo(
                                            chat_id, 
                                            telegram_photo_path, 
                                            f"🔊 Audio detection photo - Level: {int(level)}"
                                        )
                        except Exception as e:
                            logger.error(f"Error sending Telegram notification: {e}")
                
                green_led.off()
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
        finally:
            # Always unlock processing state
            self.is_processing = False

    def start_audio_detection(self):
        """Start audio detection"""
        if not self.audio_enabled:
            logger.warning("Audio not available for detection")
            return False

        try:
            # Mark the time of activation for the cooldown
            self.last_threshold_change_time = time.time()
            
            # Start audio streaming with the global callback
            audio.start_streaming(global_audio_callback)
            self.audio_streaming_active = True
            logger.info("Audio streaming started")
            return True
        except Exception as e:
            logger.error(f"Error starting audio streaming: {e}")
            self.audio_streaming_active = False
            return False

    def stop_audio_detection(self):
        """Stop audio detection"""
        try:
            # First mark streaming as inactive (this will block new callbacks from processing)
            self.audio_streaming_active = False
            
            # Give time for any in-flight callbacks to complete
            time.sleep(0.1)
            
            # Actually stop the streaming
            audio.stop_streaming()
            logger.info("Audio streaming stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping audio streaming: {e}")
            return False
    
    def update_threshold(self, new_threshold):
        """Update the sound threshold with proper handling"""
        self.last_threshold_change_time = time.time()
        self.config.SOUND_THRESHOLD = new_threshold
        logger.info(f"Sound threshold updated to {new_threshold}")
        
    def set_cloud_manager(self, cloud_manager):
        """Set the reference to the cloud manager"""
        self.cloud_manager = cloud_manager

    def set_telegram_manager(self, telegram_manager):
        """Set the reference to the Telegram manager"""
        self.telegram_manager = telegram_manager
        
    def set_video_manager(self, video_manager):
        """Set the reference to the video manager"""
        self.video_manager = video_manager
