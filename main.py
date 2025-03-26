import time
import pyb
import gc
import os
import uasyncio as asyncio

# Import our classes
import secrets_keys
from config import Config
import logger
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from distance_detector import DistanceDetector
from file_manager import FileManager
from photo_manager import PhotoManager
from cloud_manager import CloudManager
from telegram import TelegramBot  # Direct Telegram library
from video_manager import VideoManager  # New import for video management

# LEDs for visual feedback
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

# Global variables
camera_detector = None
audio_detector = None
distance_detector = None
cloud_manager = None
photo_manager = None
file_manager = None
telegram_bot = None
video_manager = None  # New variable for video management
loop = None

# Loop control variables
last_motion_time = 0
last_distance_time = 0
last_sync_time = 0
last_check_state_time = 0
last_cloud_sync_time = 0
last_distance_recalibration = 0
main_interval = 100  # Interval in milliseconds for the main loop execution

# Callback for the Telegram bot - full version with all functionalities
def telegram_callback(bot, msg_type, chat_name, sender_name, chat_id, text, entry):
    global cloud_manager

    print(f"TELEGRAM: {msg_type}, {chat_name}, {sender_name}, {chat_id}, {text}")

    # Check if the user is authorized
    is_authorized = _is_authorized(chat_id)
    if not is_authorized:
        bot.send(chat_id, "⛔ You are not authorized to use this bot.")
        print(f"Unauthorized user: {chat_id}")
        return

    # Process commands
    try:
        # Start command
        if text == "/start":
            bot.send(chat_id,
                "🤖 *Welcome to the Nicla Vision monitoring system!*\n\n"
                "You can control the system with the following commands:\n"
                "/status - View the system status\n"
                "/enable - Enable the system\n"
                "/disable - Disable the system\n"
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
                "/audio_on - Enable audio monitoring\n"
                "/audio_off - Disable audio monitoring\n"
                "/distance_on - Enable distance monitoring\n"
                "/distance_off - Disable distance monitoring\n"
                "/photo - Take an instant photo\n"
                "/photos_on - Enable automatic photo sending\n"
                "/photos_off - Disable automatic photo sending\n"
                "/video - Record an instant video\n"
                "/videos_on - Enable automatic video recording\n"
                "/videos_off - Disable automatic video recording\n\n"
                
                "*Threshold Settings:*\n"
                "/set_motion_threshold X - Set motion threshold (0.5-50)\n"
                "/set_audio_threshold X - Set audio threshold (500-20000)\n"
                "/set_distance_threshold X - Set distance threshold (10-2000)\n\n"
                
                "*Video Settings:*\n"
                "/set_video_duration X - Set video duration in seconds (3-30)\n"
                "/set_video_fps X - Set video frames per second (5-30)\n" 
                "/set_video_quality X - Set video quality (10-100)\n\n"
                
                "*Photo Settings:*\n"
                "/set_photo_quality X - Set photo quality (10-100)\n"
                "/set_telegram_photo_quality X - Set Telegram photo quality (10-100)\n\n"
                
                "*Other Settings:*\n"
                "/set_inhibit_period X - Set inhibition period in seconds (1-30)\n"
                "/set_audio_gain X - Set audio gain in dB (0-48)\n"
                "/set_distance_recalibration X - Set distance recalibration interval (60-3600)\n\n"
                
                "*Storage Settings:*\n"
                "/set_max_images X - Set maximum images to keep (5-100)\n"
                "/set_max_videos X - Set maximum videos to keep (2-20)\n"
                "/set_max_telegram_photos X - Set maximum Telegram photos (2-20)"
            )

        # Status command updated to include photo and video sending status
        elif text == "/status":
            status_msg = (
                "📊 *Monitoring system status*\n\n"
                f"System: {'🟢 Active' if Config.GLOBAL_ENABLE else '🔴 Disabled'}\n"
                f"Camera monitoring: {'🟢 Active' if Config.CAMERA_MONITORING_ENABLED else '🔴 Disabled'}\n"
                f"Audio monitoring: {'🟢 Active' if Config.AUDIO_MONITORING_ENABLED else '🔴 Disabled'}\n"
                f"Distance monitoring: {'🟢 Active' if Config.DISTANCE_MONITORING_ENABLED else '🔴 Disabled'}\n"
                f"Automatic photo sending: {'🟢 Active' if Config.SEND_PHOTOS_TELEGRAM else '🔴 Disabled'}\n"
                f"Video recording: {'🟢 Enabled' if Config.RECORD_VIDEO_ENABLED else '🔴 Disabled'}\n\n"
                f"Motion threshold: {Config.MOTION_THRESHOLD}%\n"
                f"Audio threshold: {Config.SOUND_THRESHOLD}\n"
                f"Distance threshold: {Config.DISTANCE_THRESHOLD}mm\n"
            )
            bot.send(chat_id, status_msg)

        # Global enable/disable
        elif text == "/enable":
            if cloud_manager:
                Config.GLOBAL_ENABLE = True
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "✅ Monitoring system enabled")
                logger.info("System enabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to enable: Cloud manager not available")

        elif text == "/disable":
            if cloud_manager:
                Config.GLOBAL_ENABLE = False
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "🔴 Monitoring system disabled")
                logger.info("System disabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to disable: Cloud manager not available")

        # Camera enable/disable
        elif text == "/camera_on":
            if cloud_manager:
                Config.CAMERA_MONITORING_ENABLED = True
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "📸 Camera monitoring enabled")
                logger.info("Camera monitoring enabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to enable camera: Cloud manager not available")

        elif text == "/camera_off":
            if cloud_manager:
                Config.CAMERA_MONITORING_ENABLED = False
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "🚫 Camera monitoring disabled")
                logger.info("Camera monitoring disabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to disable camera: Cloud manager not available")

        # Audio enable/disable
        elif text == "/audio_on":
            if cloud_manager:
                Config.AUDIO_MONITORING_ENABLED = True
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "🎤 Audio monitoring enabled")
                logger.info("Audio monitoring enabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to enable audio: Cloud manager not available")

        elif text == "/audio_off":
            if cloud_manager:
                Config.AUDIO_MONITORING_ENABLED = False
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "🚫 Audio monitoring disabled")
                logger.info("Audio monitoring disabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to disable audio: Cloud manager not available")

        # Distance sensor enable/disable
        elif text == "/distance_on":
            if cloud_manager:
                Config.DISTANCE_MONITORING_ENABLED = True
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "📏 Distance monitoring enabled")
                logger.info("Distance monitoring enabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to enable distance: Cloud manager not available")

        elif text == "/distance_off":
            if cloud_manager:
                Config.DISTANCE_MONITORING_ENABLED = False
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, "🚫 Distance monitoring disabled")
                logger.info("Distance monitoring disabled via Telegram")
            else:
                bot.send(chat_id, "❌ Unable to disable distance: Cloud manager not available")

        # Threshold settings
        elif text.startswith("/set_motion_threshold "):
            _set_threshold(bot, chat_id, "motion", text)

        elif text.startswith("/set_audio_threshold "):
            _set_threshold(bot, chat_id, "audio", text)

        elif text.startswith("/set_distance_threshold "):
            _set_threshold(bot, chat_id, "distance", text)

        elif text == "/photo" or text == "/foto":
            bot.send(chat_id, "📸 Taking an instant photo...")

            try:
                # Take a photo specifically optimized for Telegram
                if photo_manager.capture_telegram_photo():
                    photo_path = photo_manager.last_photo_path
                    logger.info(f"Instant photo taken: {photo_path}")

                    # Send the photo directly using the blocking method to ensure delivery
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

        # Command to enable/disable automatic photo sending
        elif text == "/photos_on":
            Config.SEND_PHOTOS_TELEGRAM = True
            bot.send(chat_id, "✅ Automatic photo sending enabled")
            logger.info(f"Automatic photo sending enabled by chat_id {chat_id}")
            if cloud_manager:
                cloud_manager.sync_to_cloud()

        elif text == "/photos_off":
            Config.SEND_PHOTOS_TELEGRAM = False
            bot.send(chat_id, "🚫 Automatic photo sending disabled")
            logger.info(f"Automatic photo sending disabled by chat_id {chat_id}")
            if cloud_manager:
                cloud_manager.sync_to_cloud()

        # Commands for video management
        elif text == "/videos_on":
            Config.RECORD_VIDEO_ENABLED = True
            bot.send(chat_id, "✅ Video recording enabled")
            logger.info(f"Video recording enabled by chat_id {chat_id}")
            if cloud_manager:
                cloud_manager.sync_to_cloud()

        elif text == "/videos_off":
            Config.RECORD_VIDEO_ENABLED = False
            bot.send(chat_id, "🚫 Video recording disabled")
            logger.info(f"Video recording disabled by chat_id {chat_id}")
            if cloud_manager:
                cloud_manager.sync_to_cloud()

        elif text == "/video":
            bot.send(chat_id, "🎥 Starting instant video recording...")
            try:
                if video_manager and video_manager.record_video("manual"):
                    video_path = video_manager.last_video_path
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
                bot.send(chat_id, f"❌ Error while recording the video: {e}")

        elif text.startswith("/set_video_duration "):
            _set_parameter(bot, chat_id, "video_duration", text)
            
        elif text.startswith("/set_video_fps "):
            _set_parameter(bot, chat_id, "video_fps", text)
            
        elif text.startswith("/set_video_quality "):
            _set_parameter(bot, chat_id, "video_quality", text)

        # Aggiungere comandi per i parametri foto
        elif text.startswith("/set_photo_quality "):
            _set_parameter(bot, chat_id, "photo_quality", text)
            
        elif text.startswith("/set_telegram_photo_quality "):
            _set_parameter(bot, chat_id, "telegram_photo_quality", text)

        # Aggiungere comandi per gli altri parametri
        elif text.startswith("/set_inhibit_period "):
            _set_parameter(bot, chat_id, "inhibit_period", text)
            
        elif text.startswith("/set_audio_gain "):
            _set_parameter(bot, chat_id, "audio_gain", text)
            
        elif text.startswith("/set_distance_recalibration "):
            _set_parameter(bot, chat_id, "distance_recalibration", text)

        # Aggiungere comandi per i parametri di archiviazione
        elif text.startswith("/set_max_images "):
            _set_parameter(bot, chat_id, "max_images", text)
            
        elif text.startswith("/set_max_videos "):
            _set_parameter(bot, chat_id, "max_videos", text)
            
        elif text.startswith("/set_max_telegram_photos "):
            _set_parameter(bot, chat_id, "max_telegram_photos", text)

        # Unrecognized command
        else:
            bot.send(chat_id, "❓ Unrecognized command. Use /help to see available commands.")

    except Exception as e:
        logger.error(f"Error processing Telegram command: {e}")
        bot.send(chat_id, f"❌ Error processing the command: {e}")

    # Visual feedback
    green_led.on()
    pyb.delay(100)
    green_led.off()

# Function to check if a user is authorized
def _is_authorized(chat_id):
    # If the list is empty or contains an asterisk, everyone is authorized
    if not secrets_keys.TELEGRAM_AUTHORIZED_USERS or "*" in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
        return True

    # Otherwise, check if the ID is in the list
    return str(chat_id) in secrets_keys.TELEGRAM_AUTHORIZED_USERS

# Function to set thresholds
def _set_threshold(bot, chat_id, threshold_type, command):
    global cloud_manager

    try:
        # Extract the value from the command string
        value = float(command.split(" ")[1])

        if cloud_manager:
            if threshold_type == "motion":
                # Validate and set the threshold
                validated = Config.validate_threshold(
                    value,
                    Config.MOTION_THRESHOLD_MIN,
                    Config.MOTION_THRESHOLD_MAX,
                    Config.MOTION_THRESHOLD
                )

                Config.MOTION_THRESHOLD = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📊 Motion threshold set to {validated}%")
                logger.info(f"Motion threshold changed to {validated}% via Telegram")

            elif threshold_type == "audio":
                # Validate and set the threshold
                validated = Config.validate_threshold(
                    value,
                    Config.SOUND_THRESHOLD_MIN,
                    Config.SOUND_THRESHOLD_MAX,
                    Config.SOUND_THRESHOLD
                )

                Config.SOUND_THRESHOLD = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🔊 Audio threshold set to {validated}")
                logger.info(f"Audio threshold changed to {validated} via Telegram")

            elif threshold_type == "distance":
                # Validate and set the threshold
                validated = Config.validate_threshold(
                    value,
                    Config.DISTANCE_THRESHOLD_MIN,
                    Config.DISTANCE_THRESHOLD_MAX,
                    Config.DISTANCE_THRESHOLD
                )

                Config.DISTANCE_THRESHOLD = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📏 Distance threshold set to {validated}mm")
                logger.info(f"Distance threshold changed to {validated}mm via Telegram")

            else:
                bot.send(chat_id, "❌ Invalid threshold type")
        else:
            bot.send(chat_id, "❌ Unable to set threshold: Cloud manager not available")
    except ValueError:
        bot.send(chat_id, "❌ Invalid value. Use a number.")
    except Exception as e:
        logger.error(f"Error setting threshold {threshold_type}: {e}")
        bot.send(chat_id, f"❌ Error setting threshold: {e}")

# Function to set parameters
def _set_parameter(bot, chat_id, param_type, command):
    global cloud_manager

    try:
        # Extract the value from the command string
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

        if cloud_manager:
            # Video parameters
            if param_type == "video_duration":
                validated = Config.validate_threshold(
                    value,
                    Config.VIDEO_DURATION_MIN,
                    Config.VIDEO_DURATION_MAX,
                    Config.VIDEO_DURATION
                )
                Config.VIDEO_DURATION = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🎥 Video duration set to {validated}s")
                logger.info(f"Video duration changed to {validated}s via Telegram")
                
            elif param_type == "video_fps":
                validated = Config.validate_threshold(
                    value,
                    Config.VIDEO_FPS_MIN,
                    Config.VIDEO_FPS_MAX,
                    Config.VIDEO_FPS
                )
                Config.VIDEO_FPS = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🎥 Video FPS set to {validated}")
                logger.info(f"Video FPS changed to {validated} via Telegram")
                
            elif param_type == "video_quality":
                validated = Config.validate_threshold(
                    value,
                    Config.VIDEO_QUALITY_MIN,
                    Config.VIDEO_QUALITY_MAX,
                    Config.VIDEO_QUALITY
                )
                Config.VIDEO_QUALITY = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🎥 Video quality set to {validated}%")
                logger.info(f"Video quality changed to {validated}% via Telegram")
                
            # Photo parameters
            elif param_type == "photo_quality":
                validated = Config.validate_threshold(
                    value,
                    10,  # Min quality
                    100,  # Max quality
                    Config.PHOTO_QUALITY
                )
                Config.PHOTO_QUALITY = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📷 Photo quality set to {validated}%")
                logger.info(f"Photo quality changed to {validated}% via Telegram")
                
            elif param_type == "telegram_photo_quality":
                validated = Config.validate_threshold(
                    value,
                    10,  # Min quality
                    100,  # Max quality
                    Config.TELEGRAM_PHOTO_QUALITY
                )
                Config.TELEGRAM_PHOTO_QUALITY = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📱 Telegram photo quality set to {validated}%")
                logger.info(f"Telegram photo quality changed to {validated}% via Telegram")
                
            # Other parameters
            elif param_type == "inhibit_period":
                validated = Config.validate_threshold(
                    value,
                    Config.INHIBIT_PERIOD_MIN,
                    Config.INHIBIT_PERIOD_MAX,
                    Config.INHIBIT_PERIOD
                )
                Config.INHIBIT_PERIOD = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"⏱️ Inhibit period set to {validated}s")
                logger.info(f"Inhibit period changed to {validated}s via Telegram")
                
            elif param_type == "audio_gain":
                validated = Config.validate_threshold(
                    value,
                    0,  # Min gain
                    48,  # Max gain
                    Config.AUDIO_GAIN
                )
                Config.AUDIO_GAIN = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🔊 Audio gain set to {validated}dB")
                logger.info(f"Audio gain changed to {validated}dB via Telegram")
                
                # Reinitialize audio detector if active
                global audio_detector
                if audio_detector:
                    audio_detector.stop_audio_detection()
                    audio_detector.init_audio()
                    audio_detector.start_audio_detection()
                    bot.send(chat_id, "🔄 Audio detector reinitialized with new gain")
                
            elif param_type == "distance_recalibration":
                validated = Config.validate_threshold(
                    value,
                    60,  # Min time (1 minute)
                    3600,  # Max time (1 hour)
                    Config.DISTANCE_RECALIBRATION
                )
                Config.DISTANCE_RECALIBRATION = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📏 Distance recalibration interval set to {validated}s")
                logger.info(f"Distance recalibration interval changed to {validated}s via Telegram")
                
            # Storage parameters
            elif param_type == "max_images":
                validated = Config.validate_threshold(
                    value,
                    5,  # Min images
                    100,  # Max images
                    Config.MAX_IMAGES
                )
                Config.MAX_IMAGES = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🖼️ Maximum images set to {validated}")
                logger.info(f"Maximum images changed to {validated} via Telegram")
                
            elif param_type == "max_videos":
                validated = Config.validate_threshold(
                    value,
                    2,  # Min videos
                    20,  # Max videos
                    Config.MAX_VIDEOS
                )
                Config.MAX_VIDEOS = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"🎬 Maximum videos set to {validated}")
                logger.info(f"Maximum videos changed to {validated} via Telegram")
                
            elif param_type == "max_telegram_photos":
                validated = Config.validate_threshold(
                    value,
                    2,  # Min photos
                    20,  # Max photos
                    Config.MAX_TELEGRAM_PHOTOS
                )
                Config.MAX_TELEGRAM_PHOTOS = validated
                cloud_manager.sync_to_cloud()
                bot.send(chat_id, f"📱 Maximum Telegram photos set to {validated}")
                logger.info(f"Maximum Telegram photos changed to {validated} via Telegram")
                
            else:
                bot.send(chat_id, "❌ Invalid parameter type")
        else:
            bot.send(chat_id, "❌ Unable to set parameter: Cloud manager not available")
    except ValueError:
        bot.send(chat_id, "❌ Invalid value. Please use a number.")
    except Exception as e:
        logger.error(f"Error setting parameter {param_type}: {e}")
        bot.send(chat_id, f"❌ Error setting parameter: {e}")

# Asynchronous task that runs the main loop
async def main_loop():
    global camera_detector, audio_detector, distance_detector
    global cloud_manager, last_motion_time, last_distance_time
    global last_sync_time, last_check_state_time, last_cloud_sync_time
    global last_distance_recalibration, video_manager

    print("Starting main loop...")

    while True:
        try:
            current_time = time.time()

            # Check cloud connection
            if cloud_manager and cloud_manager.is_connected:
                cloud_manager.check_connection()

            # Filesystem synchronization
            if current_time - last_sync_time > Config.FILESYSTEM_SYNC_INTERVAL:
                file_manager.sync_filesystem()
                last_sync_time = current_time

            # Cloud synchronization
            if cloud_manager and cloud_manager.is_connected and (current_time - last_cloud_sync_time > Config.CLOUD_SYNC_INTERVAL):
                cloud_manager.sync_from_cloud()
                last_cloud_sync_time = current_time

            # Detector initialization management
            if current_time - last_check_state_time > Config.DETECTOR_CHECK_INTERVAL:
                last_check_state_time = current_time

                # Manage detectors based on global state
                if Config.GLOBAL_ENABLE:
                    # Camera detector
                    if Config.CAMERA_MONITORING_ENABLED:
                        if not camera_detector:
                            photo_manager.init_camera_for_motion()
                            camera_detector = CameraDetector(Config)
                            logger.info("Camera detector initialized (on-demand)")
                    else:
                        if camera_detector:
                            camera_detector = None
                            logger.info("Camera detector deactivated")

                    # Audio detector
                    if Config.AUDIO_MONITORING_ENABLED:
                        if not audio_detector:
                            audio_detector = AudioDetector(Config, file_manager, photo_manager)
                            audio_detector.start_audio_detection()
                            if cloud_manager:
                                audio_detector.set_cloud_manager(cloud_manager)
                            if telegram_bot:
                                audio_detector.set_telegram_manager(telegram_bot)
                            if video_manager:  # Added reference to video manager
                                audio_detector.set_video_manager(video_manager)
                            logger.info("Audio detector initialized and started (on-demand)")
                    else:
                        if audio_detector:
                            audio_detector.stop_audio_detection()
                            audio_detector = None
                            logger.info("Audio detector deactivated")

                    # Distance detector
                    if Config.DISTANCE_MONITORING_ENABLED:
                        if not distance_detector:
                            distance_detector = DistanceDetector(Config)
                            if distance_detector.distance_enabled:
                                logger.info(f"Distance detector initialized (on-demand), base distance: {distance_detector.base_distance:.1f}mm")
                            else:
                                logger.warning("Error initializing distance sensor")
                                distance_detector = None
                        elif current_time - last_distance_recalibration > Config.DISTANCE_RECALIBRATION:
                            # Periodically recalibrate the distance sensor
                            distance_detector.recalibrate()
                            last_distance_recalibration = current_time
                    else:
                        if distance_detector:
                            distance_detector = None
                            logger.info("Distance detector deactivated")
                else:
                    # Deactivate all detectors if GLOBAL_ENABLE is disabled
                    if camera_detector:
                        camera_detector = None
                        logger.info("Camera detector deactivated (global disable)")

                    if audio_detector:
                        audio_detector.stop_audio_detection()
                        audio_detector = None
                        logger.info("Audio detector deactivated (global disable)")

                    if distance_detector:
                        distance_detector = None
                        logger.info("Distance detector deactivated (global disable)")

            # EVENT DETECTION SECTION
            # For camera motion detection
            if Config.CAMERA_MONITORING_ENABLED and camera_detector:
                if current_time - last_motion_time > Config.INHIBIT_PERIOD:
                    if camera_detector.check_motion():
                        event_msg = "Motion detected, capturing photo..."
                        logger.info(event_msg)
                        green_led.on()
                        time.sleep(0.1)
                        green_led.off()

                        # Capture photo (standard for local storage)
                        photo_path = None
                        telegram_photo_path = None

                        # First save a normal photo for local storage
                        if photo_manager.capture_save_photo("camera_alert"):
                            photo_path = photo_manager.last_photo_path
                            last_motion_time = current_time

                            # Now capture a photo optimized for Telegram if photo sending is enabled
                            if Config.SEND_PHOTOS_TELEGRAM:
                                if photo_manager.capture_telegram_photo("camera_alert", "tg"):
                                    telegram_photo_path = photo_manager.last_photo_path

                            # Reset motion detection
                            camera_detector.reset_detection()

                            # Cloud notification
                            if cloud_manager:
                                cloud_manager.notify_event("Motion", "Camera trigger")

                            # Record video if enabled
                            if Config.RECORD_VIDEO_ENABLED:
                                if video_manager.record_video("camera"):
                                    video_path = video_manager.last_video_path

                                    # Telegram notification
                                    if telegram_bot and Config.SEND_VIDEOS_TELEGRAM:
                                        try:
                                            for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                                if chat_id != "*":  # Ignore the asterisk
                                                    telegram_bot.send(chat_id, "🎥 Motion video recording completed!")
                                                    telegram_bot.send_video(
                                                        chat_id,
                                                        video_path,
                                                        "🎥 Motion detection video"
                                                    )
                                        except Exception as e:
                                            logger.error(f"Error sending video via Telegram: {e}")

                            # Telegram notification with text AND photo
                            if telegram_bot:
                                try:
                                    for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                        if chat_id != "*":  # Ignore the asterisk
                                            # First send a text message (maintain compatibility)
                                            telegram_bot.send(chat_id, "🚨 Motion detected!")

                                            # Then send the photo if photo sending is enabled and the photo was saved successfully
                                            if Config.SEND_PHOTOS_TELEGRAM and telegram_photo_path:
                                                telegram_bot.send_photo(
                                                    chat_id,
                                                    telegram_photo_path,
                                                    "📸 Motion detection photo"
                                                )
                                except Exception as e:
                                    logger.error(f"Error sending Telegram notification: {e}")

            # For distance variation detection
            if Config.DISTANCE_MONITORING_ENABLED and distance_detector and distance_detector.distance_enabled:
                if current_time - last_distance_time > Config.INHIBIT_PERIOD:
                    if distance_detector.check_distance():
                        current_distance = distance_detector.read_distance()
                        event_msg = f"Distance changed: {current_distance:.1f}mm, capturing photo..."
                        logger.info(event_msg)
                        green_led.on()
                        time.sleep(0.1)
                        green_led.off()

                        # Capture photo
                        photo_path = None
                        telegram_photo_path = None

                        # First save a normal photo for local storage
                        if photo_manager.capture_save_photo("distance_alert", "dist", int(current_distance)):
                            photo_path = photo_manager.last_photo_path
                            last_distance_time = current_time

                            # Now capture a photo optimized for Telegram if photo sending is enabled
                            if Config.SEND_PHOTOS_TELEGRAM:
                                if photo_manager.capture_telegram_photo("distance_alert", f"tg_dist", int(current_distance)):
                                    telegram_photo_path = photo_manager.last_photo_path

                            # Cloud notification
                            if cloud_manager:
                                cloud_manager.notify_event("Distance", f"Distance: {int(current_distance)}mm")

                            # Record video if enabled
                            if Config.RECORD_VIDEO_ENABLED:
                                if video_manager.record_video("distance", f"dist_{int(current_distance)}"):
                                    video_path = video_manager.last_video_path

                                    # Telegram notification
                                    if telegram_bot and Config.SEND_VIDEOS_TELEGRAM:
                                        try:
                                            for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                                if chat_id != "*":  # Ignore the asterisk
                                                    telegram_bot.send(chat_id, "🎥 Distance video recording completed!")
                                                    telegram_bot.send_video(
                                                        chat_id,
                                                        video_path,
                                                        f"🎥 Distance variation video: {int(current_distance)}mm"
                                                    )
                                        except Exception as e:
                                            logger.error(f"Error sending video via Telegram: {e}")

                            # Telegram notification
                            if telegram_bot:
                                try:
                                    for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                        if chat_id != "*":  # Ignore the asterisk
                                            # First send a text message
                                            telegram_bot.send(chat_id, f"📏 Distance variation: {int(current_distance)}mm")

                                            # Then send the photo if it was saved successfully
                                            if Config.SEND_PHOTOS_TELEGRAM and telegram_photo_path:
                                                telegram_bot.send_photo(
                                                    chat_id,
                                                    telegram_photo_path,
                                                    f"📏 Distance variation photo: {int(current_distance)}mm"
                                                )
                                except Exception as e:
                                    logger.error(f"Error sending Telegram notification: {e}")
            else:
                # System disabled
                if int(time.time() * 2) % 10 == 0:
                    red_led.toggle()

            # System activity indication
            if int(time.time() * 10) % 30 == 0:
                blue_led.toggle()

        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        # Wait for the next iteration (asynchronously)
        await asyncio.sleep_ms(main_interval)

def main():
    global camera_detector, audio_detector, distance_detector
    global cloud_manager, photo_manager, file_manager, telegram_bot, video_manager, loop

    try:
        # Clean memory at startup
        gc.collect()

        # Initialize the asynchronous loop
        loop = asyncio.get_event_loop()

        # Initialize the file manager (necessary for basic operations)
        file_manager = FileManager()

        # Initialize the cloud manager (before others to allow configuration)
        if Config.CLOUD_ENABLED:
            cloud_manager = CloudManager(Config)

            # Connect to WiFi
            if cloud_manager.connect_wifi():
                if cloud_manager.init_cloud():
                    try:
                        # Start the cloud connection
                        cloud_manager.start()

                        # Sync settings from the cloud
                        logger.info("Initial state synchronization from the cloud...")
                        for i in range(3):  # A few synchronization attempts
                            time.sleep(0.5)
                            if cloud_manager.sync_from_cloud():
                                logger.info("Initial synchronization completed")
                                break

                    except Exception as e:
                        logger.error(f"Error during cloud client startup: {e}")

        # Initialize the photo manager anyway
        photo_manager = PhotoManager(Config, file_manager)

        # Initialize the video manager
        video_manager = VideoManager(Config, file_manager)

        # Signal startup with blue LED
        blue_led.on()
        time.sleep(1)
        blue_led.off()

        # Start the main loop task
        asyncio.create_task(main_loop())

        # Start the Telegram bot
        if hasattr(Config, 'TELEGRAM_ENABLED') and Config.TELEGRAM_ENABLED:
            try:
                print("Initializing Telegram bot...")
                telegram_bot = TelegramBot(secrets_keys.TELEGRAM_TOKEN, telegram_callback)
                telegram_bot.debug = Config.DEBUG  # Enable debug

                print("Starting Telegram bot...")
                asyncio.create_task(telegram_bot.run())

                # Set the reference to the Telegram manager in the video manager
                if video_manager:
                    video_manager.set_telegram_manager(telegram_bot)

                # Signal Telegram startup completion with LED
                for _ in range(3):
                    green_led.on()
                    time.sleep(0.1)
                    green_led.off()
                    time.sleep(0.1)

                print("Telegram bot started!")

                # Send startup message to all authorized users
                for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                    if chat_id != "*":  # Ignore the asterisk
                        try:
                            telegram_bot.send(chat_id, "🟢 Nicla Vision monitoring system started and ready!")
                        except Exception as e:
                            print(f"Error sending message to {chat_id}: {e}")

            except Exception as e:
                print(f"Error initializing Telegram: {e}")

        print("System started, waiting for messages...")

        # Run the loop forever as in example.py
        loop.run_forever()

    except Exception as e:
        # For fatal errors, also print to standard console
        print(f"FATAL ERROR: {e}")

        # Attempt to log the error in the cloud as well
        try:
            if cloud_manager and cloud_manager.is_connected:
                cloud_manager.update_status(f"CRITICAL ERROR: {e}")
        except:
            pass

        # Turn on red LED to signal error
        red_led.on()
    finally:
        # Ensure audio streaming is stopped if the program ends
        if audio_detector:
            try:
                audio_detector.stop_audio_detection()
            except:
                pass

        # Stop the Telegram bot
        if telegram_bot:
            try:
                telegram_bot.stop()
            except:
                pass

if __name__ == "__main__":
    main()
