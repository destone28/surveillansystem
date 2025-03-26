import time
import pyb
import uasyncio as asyncio
import logger
import secrets_keys
from telegram import TelegramBot

# LED for visual feedback
green_led = pyb.LED(2)

class TelegramManager:
    def __init__(self, config):
        """
        Manages all functionalities related to the Telegram bot
        
        Args:
            config: Reference to the system configuration
        """
        self.config = config
        self.bot = None
        self.cloud_manager = None
        self.debug = config.DEBUG
        self.authorized_users = secrets_keys.TELEGRAM_AUTHORIZED_USERS
        
        # References to other managers (will be set by the main)
        self.photo_manager = None
        self.video_manager = None
        
        # Flag to control initialization
        self.is_initialized = False
    
    def initialize(self):
        """Initializes the Telegram bot"""
        try:
            logger.info("Initializing the Telegram bot...")
            self.bot = TelegramBot(secrets_keys.TELEGRAM_TOKEN, self._telegram_callback)
            self.bot.debug = self.config.DEBUG
            
            # Signal initialization completion with LED
            for _ in range(3):
                green_led.on()
                time.sleep(0.1)
                green_led.off()
                time.sleep(0.1)
            
            logger.info("Telegram bot initialized")
            self.is_initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {e}")
            return False
    
    def start_bot(self):
        """Starts the Telegram bot asynchronously"""
        if not self.is_initialized:
            logger.error("Cannot start the bot: not initialized")
            return False
        
        try:
            asyncio.create_task(self.bot.run())
            logger.info("Telegram bot started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            return False
    
    def stop_bot(self):
        """Stops the Telegram bot"""
        if self.bot:
            try:
                self.bot.stop()
                logger.info("Telegram bot stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")
                return False
        return False
    
    def send_startup_message(self):
        """Sends a startup message to all authorized users"""
        if not self.is_initialized:
            return False
        
        try:
            for chat_id in self.authorized_users:
                if chat_id != "*":  # Ignore the asterisk
                    self.bot.send(chat_id, "🟢 Nicla Vision monitoring system started and ready!")
            return True
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")
            return False
    
    def send_message_to_all(self, message):
        """Sends a message to all authorized users"""
        if not self.is_initialized:
            return False
        
        try:
            for chat_id in self.authorized_users:
                if chat_id != "*":  # Ignore the asterisk
                    self.bot.send(chat_id, message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to all: {e}")
            return False
    
    def send_photo_to_all(self, photo_path, caption=None):
        """Sends a photo to all authorized users"""
        if not self.is_initialized or not self.config.SEND_PHOTOS_TELEGRAM:
            return False
        
        try:
            for chat_id in self.authorized_users:
                if chat_id != "*":  # Ignore the asterisk
                    self.bot.send_photo(chat_id, photo_path, caption)
            return True
        except Exception as e:
            logger.error(f"Error sending photo to all: {e}")
            return False
    
    def send_video_to_all(self, video_path, caption=None):
        """Sends a video to all authorized users"""
        if not self.is_initialized or not self.config.SEND_VIDEOS_TELEGRAM:
            return False
        
        try:
            for chat_id in self.authorized_users:
                if chat_id != "*":  # Ignore the asterisk
                    self.bot.send_video(chat_id, video_path, caption)
            return True
        except Exception as e:
            logger.error(f"Error sending video to all: {e}")
            return False
    
    def notify_motion_event(self, photo_path=None, video_path=None):
        """Notifies a motion detection event"""
        if not self.is_initialized:
            return False
            
        try:
            # Send text message
            self.send_message_to_all("🚨 Motion detected!")
            
            # Send photo if available and photo sending is enabled
            if photo_path and self.config.SEND_PHOTOS_TELEGRAM:
                self.send_photo_to_all(photo_path, "📸 Motion detection photo")
            
            # Send video if available and video sending is enabled
            if video_path and self.config.SEND_VIDEOS_TELEGRAM:
                self.send_message_to_all("🎥 Video recording completed!")
                self.send_video_to_all(video_path, "🎥 Motion detection video")
                
            return True
        except Exception as e:
            logger.error(f"Error notifying motion event: {e}")
            return False
    
    def notify_audio_event(self, level, photo_path=None, video_path=None):
        """Notifies an audio detection event"""
        if not self.is_initialized:
            return False
            
        try:
            # Send text message
            self.send_message_to_all(f"🔊 Sound detected! Level: {int(level)}")
            
            # Send photo if available and photo sending is enabled
            if photo_path and self.config.SEND_PHOTOS_TELEGRAM:
                self.send_photo_to_all(photo_path, f"🔊 Audio detection photo - Level: {int(level)}")
            
            # Send video if available and video sending is enabled
            if video_path and self.config.SEND_VIDEOS_TELEGRAM:
                self.send_message_to_all("🎥 Audio video recording completed!")
                self.send_video_to_all(video_path, f"🎥 Audio detection video - Level: {int(level)}")
                
            return True
        except Exception as e:
            logger.error(f"Error notifying audio event: {e}")
            return False
    
    def notify_distance_event(self, distance, photo_path=None, video_path=None):
        """Notifies a distance variation detection event"""
        if not self.is_initialized:
            return False
            
        try:
            # Send text message
            self.send_message_to_all(f"📏 Distance variation: {int(distance)}mm")
            
            # Send photo if available and photo sending is enabled
            if photo_path and self.config.SEND_PHOTOS_TELEGRAM:
                self.send_photo_to_all(photo_path, f"📏 Distance variation photo: {int(distance)}mm")
            
            # Send video if available and video sending is enabled
            if video_path and self.config.SEND_VIDEOS_TELEGRAM:
                self.send_message_to_all("🎥 Distance video recording completed!")
                self.send_video_to_all(video_path, f"🎥 Distance variation video: {int(distance)}mm")
                
            return True
        except Exception as e:
            logger.error(f"Error notifying distance event: {e}")
            return False
    
    def set_cloud_manager(self, cloud_manager):
        """Sets the reference to the cloud manager"""
        self.cloud_manager = cloud_manager
    
    def set_photo_manager(self, photo_manager):
        """Sets the reference to the photo manager"""
        self.photo_manager = photo_manager
    
    def set_video_manager(self, video_manager):
        """Sets the reference to the video manager"""
        self.video_manager = video_manager
    
    def _telegram_callback(self, bot, msg_type, chat_name, sender_name, chat_id, text, entry):
        """
        Callback for messages received by the Telegram bot.
        Handles all commands and actions requested by the user.
        """
        logger.info(f"TELEGRAM: {msg_type}, {chat_name}, {sender_name}, {chat_id}, {text}")

        # Check if the user is authorized
        if not self._is_authorized(chat_id):
            bot.send(chat_id, "⛔ You are not authorized to use this bot.")
            logger.warning(f"Unauthorized user: {chat_id}")
            return

        # Command processing
        try:
            # Start command
            if text == "/start":
                bot.send(chat_id,
                    "🤖 *Welcome to the Nicla Vision monitoring system!*\n\n"
                    "You can control the system with the following commands:\n"
                    "/status - View the system status\n"
                    "/enable - Enable the system\n"
                    "/disable - Disable the system\n"
                    "/show_settings - Show all current settings\n"
                    "/help - Show all available commands"
                )

            # Help command
            elif text == "/help":
                bot.send(chat_id,
                    "📋 *Available commands:*\n\n"
                    "/status - Show the system status\n"
                    "/enable - Enable global monitoring\n"
                    "/disable - Disable global monitoring\n"
                    "/camera_on - Enable camera monitoring\n"
                    "/camera_off - Disable camera monitoring\n"
                    "/audio_on - Enable microphone monitoring\n"
                    "/audio_off - Disable microphone monitoring\n"
                    "/distance_on - Enable distance sensor monitoring\n"
                    "/distance_off - Disable distance sensor monitoring\n"
                    "/photo - Take an instant photo\n"
                    "/photos_on - Enable automatic photo sending\n"
                    "/photos_off - Disable automatic photo sending\n"
                    "/video - Record an instant video\n"
                    "/videos_on - Enable automatic video recording\n"
                    "/videos_off - Disable automatic video recording\n\n"
                    
                    "*Threshold settings:*\n"
                    "/set_motion_threshold X - Set motion threshold (0.5-50)\n"
                    "/set_audio_threshold X - Set audio threshold (500-20000)\n"
                    "/set_distance_threshold X - Set distance threshold (10-2000)\n\n"
                    
                    "*Video settings:*\n"
                    "/set_video_duration X - Set video duration in seconds (3-30)\n"
                    "/set_video_fps X - Set frames per second (5-30)\n" 
                    "/set_video_quality X - Set video quality (10-100)\n\n"
                    
                    "*Photo settings:*\n"
                    "/set_photo_quality X - Set photo quality (10-100)\n"
                    "/set_telegram_photo_quality X - Set Telegram photo quality (10-100)\n\n"
                    
                    "*Other settings:*\n"
                    "/set_inhibit_period X - Set inhibition period in seconds (1-30)\n"
                    "/set_audio_gain X - Set audio gain in dB (0-48)\n"
                    "/set_distance_recalibration X - Set distance recalibration interval (60-3600)\n\n"
                    
                    "*Storage settings:*\n"
                    "/set_max_images X - Set maximum number of images (5-100)\n"
                    "/set_max_videos X - Set maximum number of videos (2-20)\n"
                    "/set_max_telegram_photos X - Set maximum number of Telegram photos (2-20)\n\n"

                    "*Other information:*\n"
                    "/show_settings - Show all current settings"
                )

            # Status command
            elif text == "/status":
                status_msg = (
                    "📊 *Monitoring system status*\n\n"
                    f"System: {'🟢 Active' if self.config.GLOBAL_ENABLE else '🔴 Disabled'}\n"
                    f"Camera monitoring: {'🟢 Active' if self.config.CAMERA_MONITORING_ENABLED else '🔴 Disabled'}\n"
                    f"Audio monitoring: {'🟢 Active' if self.config.AUDIO_MONITORING_ENABLED else '🔴 Disabled'}\n"
                    f"Distance monitoring: {'🟢 Active' if self.config.DISTANCE_MONITORING_ENABLED else '🔴 Disabled'}\n"
                    f"Automatic photo sending: {'🟢 Active' if self.config.SEND_PHOTOS_TELEGRAM else '🔴 Disabled'}\n"
                    f"Video recording: {'🟢 Enabled' if self.config.RECORD_VIDEO_ENABLED else '🔴 Disabled'}\n\n"
                    f"Motion threshold: {self.config.MOTION_THRESHOLD}%\n"
                    f"Audio threshold: {self.config.SOUND_THRESHOLD}\n"
                    f"Distance threshold: {self.config.DISTANCE_THRESHOLD}mm\n"
                )
                bot.send(chat_id, status_msg)

            # Enable/disable global
            elif text == "/enable":
                if self.cloud_manager:
                    self.config.GLOBAL_ENABLE = True
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "✅ Monitoring system enabled")
                    logger.info("System enabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to enable: Cloud manager not available")

            elif text == "/disable":
                if self.cloud_manager:
                    self.config.GLOBAL_ENABLE = False
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "🔴 Monitoring system disabled")
                    logger.info("System disabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to disable: Cloud manager not available")

            # Enable/disable camera
            elif text == "/camera_on":
                if self.cloud_manager:
                    self.config.CAMERA_MONITORING_ENABLED = True
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "📸 Camera monitoring enabled")
                    logger.info("Camera monitoring enabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to enable camera: Cloud manager not available")

            elif text == "/camera_off":
                if self.cloud_manager:
                    self.config.CAMERA_MONITORING_ENABLED = False
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "🚫 Camera monitoring disabled")
                    logger.info("Camera monitoring disabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to disable camera: Cloud manager not available")

            # Enable/disable audio
            elif text == "/audio_on":
                if self.cloud_manager:
                    self.config.AUDIO_MONITORING_ENABLED = True
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "🎤 Audio monitoring enabled")
                    logger.info("Audio monitoring enabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to enable audio: Cloud manager not available")

            elif text == "/audio_off":
                if self.cloud_manager:
                    self.config.AUDIO_MONITORING_ENABLED = False
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "🚫 Audio monitoring disabled")
                    logger.info("Audio monitoring disabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to disable audio: Cloud manager not available")

            # Enable/disable distance sensor
            elif text == "/distance_on":
                if self.cloud_manager:
                    self.config.DISTANCE_MONITORING_ENABLED = True
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "📏 Distance monitoring enabled")
                    logger.info("Distance monitoring enabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to enable distance: Cloud manager not available")

            elif text == "/distance_off":
                if self.cloud_manager:
                    self.config.DISTANCE_MONITORING_ENABLED = False
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, "🚫 Distance monitoring disabled")
                    logger.info("Distance monitoring disabled via Telegram")
                else:
                    bot.send(chat_id, "❌ Unable to disable distance: Cloud manager not available")

            # Threshold settings
            elif text.startswith("/set_motion_threshold "):
                self._set_threshold(bot, chat_id, "motion", text)

            elif text.startswith("/set_audio_threshold "):
                self._set_threshold(bot, chat_id, "audio", text)

            elif text.startswith("/set_distance_threshold "):
                self._set_threshold(bot, chat_id, "distance", text)

            # Instant photo command
            elif text == "/photo" or text == "/foto":
                bot.send(chat_id, "📸 Taking an instant photo...")

                try:
                    # Take a photo optimized for Telegram
                    if self.photo_manager and self.photo_manager.capture_telegram_photo():
                        photo_path = self.photo_manager.last_photo_path
                        logger.info(f"Instant photo taken: {photo_path}")

                        # Send the photo directly using the blocking method
                        success = bot.send_photo(chat_id, photo_path, "📷 Instant photo requested via Telegram")

                        if success:
                            logger.info(f"Instant photo sent to chat_id {chat_id}")
                        else:
                            logger.error("Error sending the photo")
                            bot.send(chat_id, "⚠️ Issues sending the photo, but the image was captured")
                    else:
                        bot.send(chat_id, "❌ Error: unable to take the photo")
                except Exception as e:
                    logger.error(f"Error taking instant photo: {e}")
                    bot.send(chat_id, f"❌ Error while taking the photo: {e}")

            # Enable/disable automatic photo sending
            elif text == "/photos_on":
                self.config.SEND_PHOTOS_TELEGRAM = True
                bot.send(chat_id, "✅ Automatic photo sending enabled")
                logger.info(f"Automatic photo sending enabled by chat_id {chat_id}")
                if self.cloud_manager:
                    self.cloud_manager.sync_to_cloud()

            elif text == "/photos_off":
                self.config.SEND_PHOTOS_TELEGRAM = False
                bot.send(chat_id, "🚫 Automatic photo sending disabled")
                logger.info(f"Automatic photo sending disabled by chat_id {chat_id}")
                if self.cloud_manager:
                    self.cloud_manager.sync_to_cloud()

            # Commands for video management
            elif text == "/videos_on":
                self.config.RECORD_VIDEO_ENABLED = True
                bot.send(chat_id, "✅ Video recording enabled")
                logger.info(f"Video recording enabled by chat_id {chat_id}")
                if self.cloud_manager:
                    self.cloud_manager.sync_to_cloud()

            elif text == "/videos_off":
                self.config.RECORD_VIDEO_ENABLED = False
                bot.send(chat_id, "🚫 Video recording disabled")
                logger.info(f"Video recording disabled by chat_id {chat_id}")
                if self.cloud_manager:
                    self.cloud_manager.sync_to_cloud()

            # Instant video command
            elif text == "/video":
                bot.send(chat_id, "🎥 Recording an instant video...")
                try:
                    if self.video_manager and self.video_manager.record_video("manual"):
                        video_path = self.video_manager.last_video_path
                        logger.info(f"Instant video recorded: {video_path}")

                        bot.send(chat_id, "✅ Video successfully recorded! Sending...")

                        # Send the video
                        success = bot.send_video(chat_id, video_path, "🎥 Instant video requested via Telegram")

                        if success:
                            logger.info(f"Instant video sent to chat_id {chat_id}")
                        else:
                            logger.error("Error sending the video")
                            bot.send(chat_id, "⚠️ Issues sending the video, but the recording was completed")
                    else:
                        bot.send(chat_id, "❌ Error: unable to record the video")
                except Exception as e:
                    logger.error(f"Error recording instant video: {e}")
                    bot.send(chat_id, f"❌ Error during video recording: {e}")

            # Parameter settings
            elif text.startswith("/set_video_duration "):
                self._set_parameter(bot, chat_id, "video_duration", text)
                
            elif text.startswith("/set_video_fps "):
                self._set_parameter(bot, chat_id, "video_fps", text)
                
            elif text.startswith("/set_video_quality "):
                self._set_parameter(bot, chat_id, "video_quality", text)

            # Photo parameters
            elif text.startswith("/set_photo_quality "):
                self._set_parameter(bot, chat_id, "photo_quality", text)
                
            elif text.startswith("/set_telegram_photo_quality "):
                self._set_parameter(bot, chat_id, "telegram_photo_quality", text)

            # Other parameters
            elif text.startswith("/set_inhibit_period "):
                self._set_parameter(bot, chat_id, "inhibit_period", text)
                
            elif text.startswith("/set_audio_gain "):
                self._set_parameter(bot, chat_id, "audio_gain", text)
                
            elif text.startswith("/set_distance_recalibration "):
                self._set_parameter(bot, chat_id, "distance_recalibration", text)

            # Storage parameters
            elif text.startswith("/set_max_images "):
                self._set_parameter(bot, chat_id, "max_images", text)
                
            elif text.startswith("/set_max_videos "):
                self._set_parameter(bot, chat_id, "max_videos", text)
                
            elif text.startswith("/set_max_telegram_photos "):
                self._set_parameter(bot, chat_id, "max_telegram_photos", text)

            # Show settings
            elif text == "/show_settings":
                settings_report = self._generate_settings_report()
                bot.send(chat_id, settings_report)

            # Unrecognized command
            else:
                bot.send(chat_id, "❓ Unrecognized command. Use /help to see the available commands.")

        except Exception as e:
            logger.error(f"Error processing Telegram command: {e}")
            bot.send(chat_id, f"❌ Error processing the command: {e}")

        # Visual feedback
        green_led.on()
        pyb.delay(100)
        green_led.off()
    
    def _is_authorized(self, chat_id):
        """
        Checks if a user is authorized
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            bool: True if the user is authorized, False otherwise
        """
        # If the list is empty or contains an asterisk, everyone is authorized
        if not self.authorized_users or "*" in self.authorized_users:
            return True

        # Otherwise, check if the ID is in the list
        return str(chat_id) in self.authorized_users
    
    def _set_threshold(self, bot, chat_id, threshold_type, command):
        """
        Sets a detection threshold
        
        Args:
            bot: Telegram bot instance
            chat_id: Telegram chat ID
            threshold_type: Type of threshold ("motion", "audio", "distance")
            command: Full command received
        """
        try:
            # Extract the value from the command
            value = float(command.split(" ")[1])

            if self.cloud_manager:
                if threshold_type == "motion":
                    # Validate and set the threshold
                    validated = self.config.validate_threshold(
                        value,
                        self.config.MOTION_THRESHOLD_MIN,
                        self.config.MOTION_THRESHOLD_MAX,
                        self.config.MOTION_THRESHOLD
                    )

                    self.config.MOTION_THRESHOLD = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📊 Motion threshold set to {validated}%")
                    logger.info(f"Motion threshold changed to {validated}% via Telegram")

                elif threshold_type == "audio":
                    # Validate and set the threshold
                    validated = self.config.validate_threshold(
                        value,
                        self.config.SOUND_THRESHOLD_MIN,
                        self.config.SOUND_THRESHOLD_MAX,
                        self.config.SOUND_THRESHOLD
                    )

                    self.config.SOUND_THRESHOLD = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🔊 Audio threshold set to {validated}")
                    logger.info(f"Audio threshold changed to {validated} via Telegram")

                elif threshold_type == "distance":
                    # Validate and set the threshold
                    validated = self.config.validate_threshold(
                        value,
                        self.config.DISTANCE_THRESHOLD_MIN,
                        self.config.DISTANCE_THRESHOLD_MAX,
                        self.config.DISTANCE_THRESHOLD
                    )

                    self.config.DISTANCE_THRESHOLD = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📏 Distance threshold set to {validated}mm")
                    logger.info(f"Distance threshold changed to {validated}mm via Telegram")

                else:
                    bot.send(chat_id, "❌ Invalid threshold type")
            else:
                bot.send(chat_id, "❌ Unable to set the threshold: Cloud manager not available")
        except ValueError:
            bot.send(chat_id, "❌ Invalid value. Use a number.")
        except Exception as e:
            logger.error(f"Error setting threshold {threshold_type}: {e}")
            bot.send(chat_id, f"❌ Error setting threshold: {e}")
    
    def _set_parameter(self, bot, chat_id, param_type, command):
        """
        Sets a configuration parameter
        
        Args:
            bot: Telegram bot instance
            chat_id: Telegram chat ID
            param_type: Type of parameter
            command: Full command received
        """
        try:
            # Extract the value from the command
            value_str = command.split(" ")[1]
            
            # Convert to the appropriate type (float or int)
            if param_type in ["video_duration", "video_fps", "video_quality", 
                             "photo_quality", "telegram_photo_quality", 
                             "inhibit_period", "audio_gain", "distance_recalibration",
                             "max_images", "max_videos", "max_telegram_photos"]:
                # These parameters are integers
                value = int(value_str)
            else:
                # Default to float for other parameters
                value = float(value_str)

            if self.cloud_manager:
                # Video parameters
                if param_type == "video_duration":
                    validated = self.config.validate_threshold(
                        value,
                        self.config.VIDEO_DURATION_MIN,
                        self.config.VIDEO_DURATION_MAX,
                        self.config.VIDEO_DURATION
                    )
                    self.config.VIDEO_DURATION = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🎥 Video duration set to {validated}s")
                    logger.info(f"Video duration changed to {validated}s via Telegram")
                    
                elif param_type == "video_fps":
                    validated = self.config.validate_threshold(
                        value,
                        self.config.VIDEO_FPS_MIN,
                        self.config.VIDEO_FPS_MAX,
                        self.config.VIDEO_FPS
                    )
                    self.config.VIDEO_FPS = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🎥 Video FPS set to {validated}")
                    logger.info(f"Video FPS changed to {validated} via Telegram")
                    
                elif param_type == "video_quality":
                    validated = self.config.validate_threshold(
                        value,
                        self.config.VIDEO_QUALITY_MIN,
                        self.config.VIDEO_QUALITY_MAX,
                        self.config.VIDEO_QUALITY
                    )
                    self.config.VIDEO_QUALITY = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🎥 Video quality set to {validated}%")
                    logger.info(f"Video quality changed to {validated}% via Telegram")
                    
                # Photo parameters
                elif param_type == "photo_quality":
                    validated = self.config.validate_threshold(
                        value,
                        10,  # Minimum quality
                        100,  # Maximum quality
                        self.config.PHOTO_QUALITY
                    )
                    self.config.PHOTO_QUALITY = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📷 Photo quality set to {validated}%")
                    logger.info(f"Photo quality changed to {validated}% via Telegram")
                    
                elif param_type == "telegram_photo_quality":
                    validated = self.config.validate_threshold(
                        value,
                        10,  # Minimum quality
                        100,  # Maximum quality
                        self.config.TELEGRAM_PHOTO_QUALITY
                    )
                    self.config.TELEGRAM_PHOTO_QUALITY = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📱 Telegram photo quality set to {validated}%")
                    logger.info(f"Telegram photo quality changed to {validated}% via Telegram")
                    
                # Other parameters
                elif param_type == "inhibit_period":
                    validated = self.config.validate_threshold(
                        value,
                        self.config.INHIBIT_PERIOD_MIN,
                        self.config.INHIBIT_PERIOD_MAX,
                        self.config.INHIBIT_PERIOD
                    )
                    self.config.INHIBIT_PERIOD = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"⏱️ Inhibition period set to {validated}s")
                    logger.info(f"Inhibition period changed to {validated}s via Telegram")
                    
                elif param_type == "audio_gain":
                    validated = self.config.validate_threshold(
                        value,
                        0,  # Minimum gain
                        48,  # Maximum gain
                        self.config.AUDIO_GAIN
                    )
                    self.config.AUDIO_GAIN = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🔊 Audio gain set to {validated}dB")
                    logger.info(f"Audio gain changed to {validated}dB via Telegram")
                    
                elif param_type == "distance_recalibration":
                    validated = self.config.validate_threshold(
                        value,
                        60,  # Minimum time (1 minute)
                        3600,  # Maximum time (1 hour)
                        self.config.DISTANCE_RECALIBRATION
                    )
                    self.config.DISTANCE_RECALIBRATION = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📏 Distance recalibration interval set to {validated}s")
                    logger.info(f"Distance recalibration interval changed to {validated}s via Telegram")
                    
                # Storage parameters
                elif param_type == "max_images":
                    validated = self.config.validate_threshold(
                        value,
                        5,  # Minimum images
                        100,  # Maximum images
                        self.config.MAX_IMAGES
                    )
                    self.config.MAX_IMAGES = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🖼️ Maximum number of images set to {validated}")
                    logger.info(f"Maximum number of images changed to {validated} via Telegram")
                    
                elif param_type == "max_videos":
                    validated = self.config.validate_threshold(
                        value,
                        2,  # Minimum videos
                        20,  # Maximum videos
                        self.config.MAX_VIDEOS
                    )
                    self.config.MAX_VIDEOS = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"🎬 Maximum number of videos set to {validated}")
                    logger.info(f"Maximum number of videos changed to {validated} via Telegram")
                    
                elif param_type == "max_telegram_photos":
                    validated = self.config.validate_threshold(
                        value,
                        2,  # Minimum photos
                        20,  # Maximum photos
                        self.config.MAX_TELEGRAM_PHOTOS
                    )
                    self.config.MAX_TELEGRAM_PHOTOS = validated
                    self.cloud_manager.sync_to_cloud()
                    bot.send(chat_id, f"📱 Maximum number of Telegram photos set to {validated}")
                    logger.info(f"Maximum number of Telegram photos changed to {validated} via Telegram")
                    
                else:
                    bot.send(chat_id, "❌ Invalid parameter type")
            else:
                bot.send(chat_id, "❌ Unable to set the parameter: Cloud manager not available")
        except ValueError:
            bot.send(chat_id, "❌ Invalid value. Use a number.")
        except Exception as e:
            logger.error(f"Error setting parameter {param_type}: {e}")
            bot.send(chat_id, f"❌ Error setting parameter: {e}")

    def _generate_settings_report(self):
        """
        Generates a formatted report with all configurable parameter values
        
        Returns:
            str: Formatted report with all parameters
        """
        try:
            report = []
            
            # Header
            report.append("📊 *CURRENT SYSTEM SETTINGS*\n")
            
            # System status
            report.append("*System Status:*")
            report.append(f"- System: {'✅ Enabled' if self.config.GLOBAL_ENABLE else '❌ Disabled'}")
            report.append(f"- Camera Monitoring: {'✅ Active' if self.config.CAMERA_MONITORING_ENABLED else '❌ Inactive'}")
            report.append(f"- Audio Monitoring: {'✅ Active' if self.config.AUDIO_MONITORING_ENABLED else '❌ Inactive'}")
            report.append(f"- Distance Monitoring: {'✅ Active' if self.config.DISTANCE_MONITORING_ENABLED else '❌ Inactive'}")
            report.append("")
            
            # Threshold settings
            report.append("*Threshold Settings:*")
            report.append(f"- Motion Threshold: {self.config.MOTION_THRESHOLD}% (min: {self.config.MOTION_THRESHOLD_MIN}, max: {self.config.MOTION_THRESHOLD_MAX})")
            report.append(f"- Audio Threshold: {self.config.SOUND_THRESHOLD} (min: {self.config.SOUND_THRESHOLD_MIN}, max: {self.config.SOUND_THRESHOLD_MAX})")
            report.append(f"- Distance Threshold: {self.config.DISTANCE_THRESHOLD}mm (min: {self.config.DISTANCE_THRESHOLD_MIN}, max: {self.config.DISTANCE_THRESHOLD_MAX})")
            report.append(f"- Inhibition Period: {self.config.INHIBIT_PERIOD}s (min: {self.config.INHIBIT_PERIOD_MIN}, max: {self.config.INHIBIT_PERIOD_MAX})")
            report.append("")
            
            # Video settings
            report.append("*Video Settings:*")
            report.append(f"- Video Recording: {'✅ Enabled' if self.config.RECORD_VIDEO_ENABLED else '❌ Disabled'}")
            report.append(f"- Send Videos on Telegram: {'✅ Enabled' if self.config.SEND_VIDEOS_TELEGRAM else '❌ Disabled'}")
            report.append(f"- Video Duration: {self.config.VIDEO_DURATION}s (min: {self.config.VIDEO_DURATION_MIN}, max: {self.config.VIDEO_DURATION_MAX})")
            report.append(f"- Video FPS: {self.config.VIDEO_FPS} (min: {self.config.VIDEO_FPS_MIN}, max: {self.config.VIDEO_FPS_MAX})")
            report.append(f"- Video Quality: {self.config.VIDEO_QUALITY}% (min: {self.config.VIDEO_QUALITY_MIN}, max: {self.config.VIDEO_QUALITY_MAX})")
            report.append("")
            
            # Photo settings
            report.append("*Photo Settings:*")
            report.append(f"- Send Photos on Telegram: {'✅ Enabled' if self.config.SEND_PHOTOS_TELEGRAM else '❌ Disabled'}")
            report.append(f"- Photo Quality: {self.config.PHOTO_QUALITY}% (min: 10, max: 100)")
            report.append(f"- Telegram Photo Quality: {self.config.TELEGRAM_PHOTO_QUALITY}% (min: 10, max: 100)")
            report.append(f"- Photo Resolution: {self.config.PHOTO_SIZE}")
            report.append("")
            
            # Other settings
            report.append("*Other Settings:*")
            report.append(f"- Audio Gain: {self.config.AUDIO_GAIN}dB (min: 0, max: 48)")
            report.append(f"- Distance Recalibration: {self.config.DISTANCE_RECALIBRATION}s (min: 60, max: 3600)")
            report.append("")
            
            # Storage settings
            report.append("*Storage Settings:*")
            report.append(f"- Max Images: {self.config.MAX_IMAGES} (min: 5, max: 100)")
            report.append(f"- Max Videos: {self.config.MAX_VIDEOS} (min: 2, max: 20)")
            report.append(f"- Max Telegram Photos: {self.config.MAX_TELEGRAM_PHOTOS} (min: 2, max: 20)")
            
            # Join all report lines with a newline
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generating settings report: {e}")
            return "❌ Error generating the settings report."
