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
        # Check if audio is enabled AND if audio monitoring is active
        if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
            return

        try:
            # Convert bytes to signed int values
            samples = [buf[i] | (buf[i+1] << 8) for i in range(0, len(buf), 2)]
            # Calculate the average audio level
            level = sum(abs(s) for s in samples) / len(samples)

            if level > self.config.SOUND_THRESHOLD:
                logger.info(f"Sound detected: {level} (threshold: {self.config.SOUND_THRESHOLD})")
                
                # Check inhibition period
                current_time = time.time()
                if current_time - self.last_capture_time < self.config.INHIBIT_PERIOD:
                    return
                    
                self.last_capture_time = current_time
                
                # Turn on green LED for debugging
                green_led.on()
                
                # Capture photo
                photo_path = None
                telegram_photo_path = None
                
                # First save a normal photo for local storage
                if self.photo_manager.capture_save_photo("audio_alert", "sound", int(level)):
                    photo_path = self.photo_manager.last_photo_path
                    
                    # Now capture a photo optimized for Telegram if photo sending is enabled
                    if hasattr(self.config, 'SEND_PHOTOS_TELEGRAM') and self.config.SEND_PHOTOS_TELEGRAM:
                        if self.photo_manager.capture_telegram_photo("audio_alert", f"tg_sound", int(level)):
                            telegram_photo_path = self.photo_manager.last_photo_path

                    # Record video if enabled
                    video_path = None
                    if hasattr(self.config, 'RECORD_VIDEO_ENABLED') and self.config.RECORD_VIDEO_ENABLED and self.video_manager:
                        if self.video_manager.record_video("audio", f"sound_{int(level)}"):
                            video_path = self.video_manager.last_video_path
                    
                    # Cloud notification if available
                    if self.cloud_manager:
                        self.cloud_manager.notify_event("Audio", f"Level: {int(level)}")
                    
                    # Telegram notification via TelegramManager
                    try:
                        # Use the telegram_manager (internal bot)
                        if self.telegram_manager and telegram_photo_path and video_path:
                            # If using the new TelegramManager
                            if hasattr(self.telegram_manager, 'notify_audio_event'):
                                self.telegram_manager.notify_audio_event(level, telegram_photo_path, video_path)
                            # Fallback to the old direct method
                            else:
                                for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                    if chat_id != "*":  # Ignore the asterisk
                                        # Send text message
                                        self.telegram_manager.send(chat_id, f"🔊 Sound detected! Level: {int(level)}")
                                        
                                        # Send photo (only if enabled and available)
                                        if hasattr(self.config, 'SEND_PHOTOS_TELEGRAM') and self.config.SEND_PHOTOS_TELEGRAM and telegram_photo_path:
                                            self.telegram_manager.send_photo(
                                                chat_id, 
                                                telegram_photo_path, 
                                                f"🔊 Audio detection photo - Level: {int(level)}"
                                            )
                                            
                                        # Send video (only if enabled and available)
                                        if hasattr(self.config, 'SEND_VIDEOS_TELEGRAM') and self.config.SEND_VIDEOS_TELEGRAM and video_path:
                                            self.telegram_manager.send(chat_id, "🎥 Audio video recording completed!")
                                            self.telegram_manager.send_video(
                                                chat_id,
                                                video_path,
                                                f"🎥 Audio detection video - Level: {int(level)}"
                                            )
                    except Exception as e:
                        logger.error(f"Telegram notification error: {e}")
                
                green_led.off()
        except Exception as e:
            logger.error(f"Audio processing error: {e}")

    def start_audio_detection(self):
        """Start audio detection"""
        if not self.audio_enabled:
            logger.warning("Audio not available for detection")
            return False

        try:
            # Start audio streaming with the global callback
            audio.start_streaming(global_audio_callback)
            logger.info("Audio streaming started")
            return True
        except Exception as e:
            logger.error(f"Error starting audio streaming: {e}")
            return False

    def stop_audio_detection(self):
        """Stop audio detection"""
        try:
            audio.stop_streaming()
            logger.info("Audio streaming stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping audio streaming: {e}")
            return False
        
    def set_cloud_manager(self, cloud_manager):
        """Set the reference to the cloud manager"""
        self.cloud_manager = cloud_manager

    def set_telegram_manager(self, telegram_manager):
        """Set the reference to the Telegram manager"""
        self.telegram_manager = telegram_manager
        
    def set_video_manager(self, video_manager):
        """Set the reference to the Video manager"""
        self.video_manager = video_manager