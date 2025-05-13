import time
import pyb
import gc
import os
import uasyncio as asyncio

# Import of our classes
import secrets_keys
from config import Config
import logger
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from distance_detector import DistanceDetector
from file_manager import FileManager
from photo_manager import PhotoManager
from cloud_manager import CloudManager
from video_manager import VideoManager
from telegram_manager import TelegramManager

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
telegram_manager = None
video_manager = None
loop = None

# Control variables for the loop
last_motion_time = 0
last_audio_time = 0
last_distance_time = 0
last_sync_time = 0
last_check_state_time = 0
last_cloud_sync_time = 0
last_distance_recalibration = 0
last_audio_recalibration = 0
main_interval = 100  # Interval in milliseconds for the main loop execution

# Asynchronous task that runs the main loop
async def main_loop():
    global camera_detector, audio_detector, distance_detector
    global cloud_manager, last_motion_time, last_audio_time, last_distance_time
    global last_sync_time, last_check_state_time, last_cloud_sync_time
    global last_distance_recalibration, last_audio_recalibration
    global video_manager, telegram_manager

    print("Starting the main loop...")

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

                # Detector management based on global state
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
                            audio_detector = AudioDetector(Config)
                            if audio_detector.start_audio_detection():
                                logger.info("Audio detector initialized and started (on-demand)")
                            else:
                                logger.error("Failed to start audio detection")
                    else:
                        if audio_detector:
                            # Stop audio detection properly
                            if hasattr(audio_detector, 'audio_streaming_active') and audio_detector.audio_streaming_active:
                                logger.info("Stopping audio detector due to configuration change")
                                audio_detector.stop_audio_detection()
                                # Pause to ensure all pending operations are completed
                                time.sleep(0.3)
                            
                            # Remove reference
                            audio_detector = None
                            logger.info("Audio detector deactivated")
                            
                            # Force garbage collection
                            gc.collect()

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
                            # Periodic recalibration of the distance sensor
                            distance_detector.recalibrate()
                            last_distance_recalibration = current_time
                    else:
                        if distance_detector:
                            distance_detector = None
                            logger.info("Distance detector deactivated")
                else:
                    # Deactivation of all detectors if GLOBAL_ENABLE is disabled
                    if camera_detector:
                        camera_detector = None
                        logger.info("Camera detector deactivated (global disable)")

                    if audio_detector:
                        if hasattr(audio_detector, 'stop_audio_detection'):
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
                        event_msg = "Camera detected, capturing photo..."
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
                                cloud_manager.notify_event("Camera", "Camera trigger")

                            # Video recording if enabled
                            video_path = None
                            if Config.RECORD_VIDEO_ENABLED:
                                if video_manager.record_video("camera"):
                                    video_path = video_manager.last_video_path

                            # Telegram notification
                            if telegram_manager:
                                telegram_manager.notify_motion_event(telegram_photo_path, video_path)

            # For audio sound detection
            if Config.AUDIO_MONITORING_ENABLED and audio_detector and audio_detector.audio_streaming_active:
                if current_time - last_audio_time > Config.INHIBIT_PERIOD:
                    # Use the same pattern as camera and distance detection
                    sound_detected, level = audio_detector.check_sound()
                    
                    if sound_detected:
                        event_msg = f"Sound detected: level={level:.1f}, capturing photo..."
                        logger.info(event_msg)
                        green_led.on()
                        time.sleep(0.1)
                        green_led.off()
                        
                        # Capture photo (standard for local storage)
                        photo_path = None
                        telegram_photo_path = None
                        
                        # First save a normal photo for local storage
                        if photo_manager.capture_save_photo("audio_alert", "sound", int(level)):
                            photo_path = photo_manager.last_photo_path
                            last_audio_time = current_time
                            
                            # Now capture a photo optimized for Telegram if photo sending is enabled
                            if Config.SEND_PHOTOS_TELEGRAM:
                                if photo_manager.capture_telegram_photo("audio_alert", f"tg_sound", int(level)):
                                    telegram_photo_path = photo_manager.last_photo_path
                            
                            # Cloud notification
                            if cloud_manager:
                                cloud_manager.notify_event("Audio", f"Level: {int(level)}")
                            
                            # Video recording if enabled
                            video_path = None
                            if Config.RECORD_VIDEO_ENABLED:
                                if video_manager.record_video("audio", f"sound_{int(level)}"):
                                    video_path = video_manager.last_video_path
                            
                            # Telegram notification
                            if telegram_manager:
                                telegram_manager.notify_audio_event(int(level), telegram_photo_path, video_path)

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

                            # Video recording if enabled
                            video_path = None
                            if Config.RECORD_VIDEO_ENABLED:
                                if video_manager.record_video("distance", f"dist_{int(current_distance)}"):
                                    video_path = video_manager.last_video_path

                            # Telegram notification with TelegramManager
                            if telegram_manager:
                                telegram_manager.notify_distance_event(current_distance, telegram_photo_path, video_path)
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
    global cloud_manager, photo_manager, file_manager, telegram_manager, video_manager, loop

    try:
        # Memory cleanup at startup
        gc.collect()

        # Initialization of the asynchronous loop
        loop = asyncio.get_event_loop()

        # Initialization of the file manager (necessary for basic operations)
        file_manager = FileManager()

        # Initialization of the cloud manager (before others to allow configuration)
        if Config.CLOUD_ENABLED:
            cloud_manager = CloudManager(Config)

            # WiFi connection
            if cloud_manager.connect_wifi():
                if cloud_manager.init_cloud():
                    try:
                        # Start cloud connection
                        cloud_manager.start()

                        # Synchronize settings from the cloud
                        logger.info("Synchronizing initial state from the cloud...")
                        for i in range(3):  # A few synchronization attempts
                            time.sleep(0.5)
                            if cloud_manager.sync_from_cloud():
                                logger.info("Initial synchronization completed")
                                break

                    except Exception as e:
                        logger.error(f"Error during cloud client startup: {e}")

        # Initialization of the photo manager anyway
        photo_manager = PhotoManager(Config, file_manager)

        # Initialization of the video manager
        video_manager = VideoManager(Config, file_manager)

        # Startup indication with blue LED
        blue_led.on()
        time.sleep(1)
        blue_led.off()

        # Start main loop task
        asyncio.create_task(main_loop())

        # Initialization and startup of TelegramManager
        if hasattr(Config, 'TELEGRAM_ENABLED') and Config.TELEGRAM_ENABLED:
            try:
                print("Initializing TelegramManager...")
                # Create and configure TelegramManager
                telegram_manager = TelegramManager(Config)
                
                # Set references to other managers
                if cloud_manager:
                    telegram_manager.set_cloud_manager(cloud_manager)
                telegram_manager.set_photo_manager(photo_manager)
                telegram_manager.set_video_manager(video_manager)
                
                # Initialization and startup
                if telegram_manager.initialize():
                    telegram_manager.start_bot()
                    
                    # Indicate Telegram startup completion with LED
                    for _ in range(3):
                        green_led.on()
                        time.sleep(0.1)
                        green_led.off()
                        time.sleep(0.1)
                    
                    print("TelegramManager started!")
                    
                    # Send startup message
                    telegram_manager.send_startup_message()
                else:
                    print("Error initializing TelegramManager")
            except Exception as e:
                print(f"Error initializing Telegram: {e}")

        print("System started, waiting for messages...")

        # Run the loop forever as in example.py
        loop.run_forever()

    except Exception as e:
        # For fatal errors, also print to the standard console
        print(f"FATAL ERROR: {e}")

        # Attempt to log the error in the cloud as well
        try:
            if cloud_manager and cloud_manager.is_connected:
                cloud_manager.update_status(f"CRITICAL ERROR: {e}")
        except:
            pass

        # Turn on red LED to indicate error
        red_led.on()
    finally:
        # Ensure audio streaming is stopped if the program ends
        if audio_detector:
            try:
                audio_detector.stop_audio_detection()
            except:
                pass

        # Stop the Telegram bot
        if telegram_manager:
            try:
                telegram_manager.stop_bot()
            except:
                pass

if __name__ == "__main__":
    main()