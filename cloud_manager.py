import network
import time
from arduino_iot_cloud import ArduinoCloudClient
from secrets_keys import WIFI_SSID, WIFI_PASS, DEVICE_ID, SECRET_KEY
import logger

class CloudManager:
    def __init__(self, config):
        """
        Manages the connection with Arduino IoT Cloud and synchronizes variables.

        Args:
            config: System configuration object
        """
        self.config = config
        self.client = None
        self.wifi = None
        self.is_connected = False
        self.last_connection_check = 0
        self.connection_check_interval = 5  # Reduced for greater responsiveness
        self.log_messages = []  # Buffer for log messages

        # Set the reference to the cloud manager for logging
        logger.set_cloud_manager(self)

    def connect_wifi(self):
        """Connects the device to the WiFi network"""
        try:
            logger.info("Connecting to WiFi...", cloud=False)
            self.wifi = network.WLAN(network.STA_IF)
            self.wifi.active(True)

            if not self.wifi.isconnected():
                self.wifi.connect(WIFI_SSID, WIFI_PASS)

                # Wait for connection with timeout
                start_time = time.time()
                while not self.wifi.isconnected():
                    if time.time() - start_time > 20:  # 20-second timeout
                        logger.error("WiFi connection timeout")
                        return False
                    time.sleep(0.5)

            logger.info(f"WiFi connected: {self.wifi.ifconfig()}", cloud=False)
            return True
        except Exception as e:
            logger.error(f"WiFi connection error: {e}")
            return False

    def init_cloud(self):
        """Initializes the connection to Arduino IoT Cloud"""
        try:
            logger.info("Initializing Arduino IoT Cloud...", cloud=False)

            # Create the Arduino Cloud client in synchronous mode
            self.client = ArduinoCloudClient(
                device_id=DEVICE_ID,
                username=DEVICE_ID,
                password=SECRET_KEY,
                sync_mode=True  # Use synchronous mode instead of asynchronous
            )

            # Register variables with callbacks
            if self._register_variables():
                self.is_connected = True
                logger.info("Arduino IoT Cloud initialized", cloud=False)
                return True
            return False
        except Exception as e:
            logger.error(f"Cloud initialization error: {e}")
            return False

    def _register_variables(self):
        """Registers variables and callbacks for Arduino IoT Cloud"""
        try:
            # Global enable variable - Ensure the Bool type is correct
            self.client.register("global_enable", value=self.config.GLOBAL_ENABLE,
                               on_write=self._on_global_enable_change)

            # Monitoring control variables
            self.client.register("audio_monitoring", value=self.config.AUDIO_MONITORING_ENABLED,
                               on_write=self._on_audio_monitoring_change)
            self.client.register("camera_monitoring", value=self.config.CAMERA_MONITORING_ENABLED,
                               on_write=self._on_camera_monitoring_change)
            self.client.register("distance_monitoring", value=self.config.DISTANCE_MONITORING_ENABLED,
                               on_write=self._on_distance_monitoring_change)

            # Detection parameters
            self.client.register("sound_threshold", value=self.config.SOUND_THRESHOLD,
                               on_write=self._on_sound_threshold_change)
            self.client.register("motion_threshold", value=self.config.MOTION_THRESHOLD,
                               on_write=self._on_motion_threshold_change)
            self.client.register("distance_threshold", value=self.config.DISTANCE_THRESHOLD,
                               on_write=self._on_distance_threshold_change)

            # Video parameters
            self.client.register("video_duration", value=self.config.VIDEO_DURATION,
                               on_write=self._on_video_duration_change)
            self.client.register("video_fps", value=self.config.VIDEO_FPS,
                               on_write=self._on_video_fps_change)
            self.client.register("video_quality", value=self.config.VIDEO_QUALITY,
                               on_write=self._on_video_quality_change)

            # General parameters
            self.client.register("inhibit_period", value=self.config.INHIBIT_PERIOD,
                               on_write=self._on_inhibit_period_change)

            # Status and notification variables
            self.client.register("system_status", value="Initializing...")
            self.client.register("last_event", value="No events")
            self.client.register("last_event_time", value="")  # Empty string instead of 0
            self.client.register("log_messages", value="")
            self.client.register("current_video", value="")
            self.client.register("event_type", value="")
            self.client.register("video_list", value="[]")

            # Video recording
            self.client.register("record_video_enabled", value=self.config.RECORD_VIDEO_ENABLED,
                            on_write=self._on_record_video_enabled_change)
            self.client.register("send_videos_telegram", value=self.config.SEND_VIDEOS_TELEGRAM,
                            on_write=self._on_send_videos_telegram_change)

            # Photo parameters
            self.client.register("photo_quality", value=self.config.PHOTO_QUALITY,
                            on_write=self._on_photo_quality_change)
            self.client.register("telegram_photo_quality", value=self.config.TELEGRAM_PHOTO_QUALITY,
                            on_write=self._on_telegram_photo_quality_change)

            # Audio parameters
            self.client.register("audio_gain", value=self.config.AUDIO_GAIN,
                            on_write=self._on_audio_gain_change)

            # Distance parameters
            self.client.register("distance_recalibration", value=self.config.DISTANCE_RECALIBRATION,
                            on_write=self._on_distance_recalibration_change)

            # Storage parameters
            self.client.register("max_images", value=self.config.MAX_IMAGES,
                            on_write=self._on_max_images_change)
            self.client.register("max_videos", value=self.config.MAX_VIDEOS,
                            on_write=self._on_max_videos_change)
            self.client.register("max_telegram_photos", value=self.config.MAX_TELEGRAM_PHOTOS,
                            on_write=self._on_max_telegram_photos_change)

            logger.info("Cloud variables registered", cloud=False)
            return True
        except Exception as e:
            logger.error(f"Variable registration error: {e}")
            return False

    def sync_from_cloud(self):
        """Synchronizes the state from cloud variables to local configuration"""
        if not self.is_connected or not self.client:
            return False

        try:
            # logger.info("Synchronizing state from the cloud...", cloud=False)

            # Read variables from the cloud and update local configuration
            try:
                # First request an update from the cloud
                self.client.update()

                # Main settings
                self.config.GLOBAL_ENABLE = self.client["global_enable"]
                self.config.CAMERA_MONITORING_ENABLED = self.client["camera_monitoring"]
                self.config.AUDIO_MONITORING_ENABLED = self.client["audio_monitoring"]
                self.config.DISTANCE_MONITORING_ENABLED = self.client["distance_monitoring"]

                # Thresholds
                self.config.SOUND_THRESHOLD = self.config.validate_threshold(
                    self.client["sound_threshold"],
                    self.config.SOUND_THRESHOLD_MIN,
                    self.config.SOUND_THRESHOLD_MAX,
                    self.config.SOUND_THRESHOLD
                )

                self.config.MOTION_THRESHOLD = self.config.validate_threshold(
                    self.client["motion_threshold"],
                    self.config.MOTION_THRESHOLD_MIN,
                    self.config.MOTION_THRESHOLD_MAX,
                    self.config.MOTION_THRESHOLD
                )

                self.config.DISTANCE_THRESHOLD = self.config.validate_threshold(
                    self.client["distance_threshold"],
                    self.config.DISTANCE_THRESHOLD_MIN,
                    self.config.DISTANCE_THRESHOLD_MAX,
                    self.config.DISTANCE_THRESHOLD
                )

                # Video settings
                self.config.VIDEO_DURATION = self.config.validate_threshold(
                    self.client["video_duration"],
                    self.config.VIDEO_DURATION_MIN,
                    self.config.VIDEO_DURATION_MAX,
                    self.config.VIDEO_DURATION
                )

                self.config.VIDEO_FPS = self.config.validate_threshold(
                    self.client["video_fps"],
                    self.config.VIDEO_FPS_MIN,
                    self.config.VIDEO_FPS_MAX,
                    self.config.VIDEO_FPS
                )

                self.config.VIDEO_QUALITY = self.config.validate_threshold(
                    self.client["video_quality"],
                    self.config.VIDEO_QUALITY_MIN,
                    self.config.VIDEO_QUALITY_MAX,
                    self.config.VIDEO_QUALITY
                )

                # Other settings
                self.config.INHIBIT_PERIOD = self.config.validate_threshold(
                    self.client["inhibit_period"],
                    self.config.INHIBIT_PERIOD_MIN,
                    self.config.INHIBIT_PERIOD_MAX,
                    self.config.INHIBIT_PERIOD
                )

                # Video settings
                self.config.RECORD_VIDEO_ENABLED = self.client["record_video_enabled"]
                self.config.SEND_VIDEOS_TELEGRAM = self.client["send_videos_telegram"]

                # Photo settings
                if "photo_quality" in self.client:
                    self.config.PHOTO_QUALITY = self.config.validate_threshold(
                        self.client["photo_quality"],
                        10, 100,
                        self.config.PHOTO_QUALITY
                    )

                if "telegram_photo_quality" in self.client:
                    self.config.TELEGRAM_PHOTO_QUALITY = self.config.validate_threshold(
                        self.client["telegram_photo_quality"],
                        10, 100,
                        self.config.TELEGRAM_PHOTO_QUALITY
                    )

                # Audio settings
                if "audio_gain" in self.client:
                    self.config.AUDIO_GAIN = self.config.validate_threshold(
                        self.client["audio_gain"],
                        0, 48,
                        self.config.AUDIO_GAIN
                    )

                # Distance settings
                if "distance_recalibration" in self.client:
                    self.config.DISTANCE_RECALIBRATION = self.config.validate_threshold(
                        self.client["distance_recalibration"],
                        60, 3600,
                        self.config.DISTANCE_RECALIBRATION
                    )

                # Storage settings
                if "max_images" in self.client:
                    self.config.MAX_IMAGES = self.config.validate_threshold(
                        self.client["max_images"],
                        5, 100,
                        self.config.MAX_IMAGES
                    )

                if "max_videos" in self.client:
                    self.config.MAX_VIDEOS = self.config.validate_threshold(
                        self.client["max_videos"],
                        2, 20,
                        self.config.MAX_VIDEOS
                    )

                if "max_telegram_photos" in self.client:
                    self.config.MAX_TELEGRAM_PHOTOS = self.config.validate_threshold(
                        self.client["max_telegram_photos"],
                        2, 20,
                        self.config.MAX_TELEGRAM_PHOTOS
                    )

                # logger.info(f"State synchronized from the cloud: Global={self.config.GLOBAL_ENABLE}, Camera={self.config.CAMERA_MONITORING_ENABLED}, Audio={self.config.AUDIO_MONITORING_ENABLED}, Distance={self.config.DISTANCE_MONITORING_ENABLED}")
                return True

            except Exception as e:
                logger.error(f"Error reading cloud variables: {e}")
                return False

        except Exception as e:
            logger.error(f"Error synchronizing from the cloud: {e}")
            return False

    def sync_to_cloud(self):
        """Synchronizes the state from the local configuration to the cloud variables"""
        if not self.is_connected or not self.client:
            return False

        try:
            logger.info("Synchronizing state to the cloud...", cloud=False)

            # Update cloud variables with local configuration values
            try:
                self.client["global_enable"] = self.config.GLOBAL_ENABLE
                self.client["camera_monitoring"] = self.config.CAMERA_MONITORING_ENABLED
                self.client["audio_monitoring"] = self.config.AUDIO_MONITORING_ENABLED
                self.client["distance_monitoring"] = self.config.DISTANCE_MONITORING_ENABLED
                self.client["sound_threshold"] = self.config.SOUND_THRESHOLD
                self.client["motion_threshold"] = self.config.MOTION_THRESHOLD
                self.client["distance_threshold"] = self.config.DISTANCE_THRESHOLD
                self.client["video_duration"] = self.config.VIDEO_DURATION
                self.client["video_fps"] = self.config.VIDEO_FPS
                self.client["video_quality"] = self.config.VIDEO_QUALITY
                self.client["inhibit_period"] = self.config.INHIBIT_PERIOD
                self.client["record_video_enabled"] = self.config.RECORD_VIDEO_ENABLED
                self.client["send_videos_telegram"] = self.config.SEND_VIDEOS_TELEGRAM

                # Photo settings
                if hasattr(self.config, 'PHOTO_QUALITY'):
                    self.client["photo_quality"] = self.config.PHOTO_QUALITY
                if hasattr(self.config, 'TELEGRAM_PHOTO_QUALITY'):
                    self.client["telegram_photo_quality"] = self.config.TELEGRAM_PHOTO_QUALITY

                # Audio settings
                if hasattr(self.config, 'AUDIO_GAIN'):
                    self.client["audio_gain"] = self.config.AUDIO_GAIN

                # Distance settings
                if hasattr(self.config, 'DISTANCE_RECALIBRATION'):
                    self.client["distance_recalibration"] = self.config.DISTANCE_RECALIBRATION

                # Storage settings
                if hasattr(self.config, 'MAX_IMAGES'):
                    self.client["max_images"] = self.config.MAX_IMAGES
                if hasattr(self.config, 'MAX_VIDEOS'):
                    self.client["max_videos"] = self.config.MAX_VIDEOS
                if hasattr(self.config, 'MAX_TELEGRAM_PHOTOS'):
                    self.client["max_telegram_photos"] = self.config.MAX_TELEGRAM_PHOTOS

                # Update system status
                self._update_system_status()

                # Force update for synchronization
                self.client.update()

                logger.info(f"State synchronized to the cloud")
                return True

            except Exception as e:
                logger.error(f"Error writing cloud variables: {e}")
                return False

        except Exception as e:
            logger.error(f"Error synchronizing to the cloud: {e}")
            return False

    # Variable callbacks remain unchanged but logs are updated
    def _on_camera_monitoring_change(self, client, value):
        """Callback when camera monitoring changes"""
        try:
            self.config.CAMERA_MONITORING_ENABLED = value
            msg = f"Camera monitoring {'enabled' if value else 'disabled'}"
            logger.info(msg)

            # Update status and log
            self._update_system_status()
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()
        except Exception as e:
            logger.error(f"Error callback camera monitoring: {e}")

    def _on_audio_monitoring_change(self, client, value):
        """Callback when audio monitoring changes"""
        try:
            self.config.AUDIO_MONITORING_ENABLED = value
            msg = f"Audio monitoring {'enabled' if value else 'disabled'}"
            logger.info(msg)

            # Update status and log
            self._update_system_status()
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()
        except Exception as e:
            logger.error(f"Error callback audio monitoring: {e}")

    def _on_distance_monitoring_change(self, client, value):
        """Callback when distance monitoring changes"""
        try:
            self.config.DISTANCE_MONITORING_ENABLED = value
            msg = f"Distance monitoring {'enabled' if value else 'disabled'}"
            logger.info(msg)

            # Update status and log
            self._update_system_status()
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()
        except Exception as e:
            logger.error(f"Error callback distance monitoring: {e}")

    def _on_sound_threshold_change(self, client, value):
        """Callback when the sound threshold changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.SOUND_THRESHOLD_MIN,
                self.config.SOUND_THRESHOLD_MAX,
                self.config.SOUND_THRESHOLD
            )

            if validated_value != value:
                logger.warning(f"Sound threshold corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["sound_threshold"] = validated_value

            self.config.SOUND_THRESHOLD = validated_value
            msg = f"Sound threshold set to {validated_value}"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Sound threshold set to {validated_value}"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback sound threshold: {e}")

    def _on_motion_threshold_change(self, client, value):
        """Callback when the motion threshold changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.MOTION_THRESHOLD_MIN,
                self.config.MOTION_THRESHOLD_MAX,
                self.config.MOTION_THRESHOLD
            )

            if validated_value != value:
                logger.warning(f"Motion threshold corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["motion_threshold"] = validated_value

            self.config.MOTION_THRESHOLD = validated_value
            msg = f"Motion threshold set to {validated_value}%"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Motion threshold set to {validated_value}%"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback motion threshold: {e}")

    def _on_distance_threshold_change(self, client, value):
        """Callback when the distance threshold changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.DISTANCE_THRESHOLD_MIN,
                self.config.DISTANCE_THRESHOLD_MAX,
                self.config.DISTANCE_THRESHOLD
            )

            if validated_value != value:
                logger.warning(f"Distance threshold corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["distance_threshold"] = validated_value

            self.config.DISTANCE_THRESHOLD = validated_value
            msg = f"Distance threshold set to {validated_value}mm"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Distance threshold set to {validated_value}mm"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback distance threshold: {e}")

    def _on_inhibit_period_change(self, client, value):
        """Callback when the inhibit period changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.INHIBIT_PERIOD_MIN,
                self.config.INHIBIT_PERIOD_MAX,
                self.config.INHIBIT_PERIOD
            )

            if validated_value != value:
                logger.warning(f"Inhibit period corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["inhibit_period"] = validated_value

            self.config.INHIBIT_PERIOD = validated_value
            msg = f"Inhibit period set to {validated_value}s"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Inhibit period set to {validated_value}s"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback inhibit period: {e}")

    def _on_global_enable_change(self, client, value):
        """Callback when the global switch changes state"""
        try:
            self.config.GLOBAL_ENABLE = value
            status_msg = f"System {'enabled' if value else 'disabled'} globally"
            logger.info(status_msg)

            # Update status and log
            client["system_status"] = status_msg
            self.add_log_message(status_msg)

            # If globally disabled, ensure all sensors are turned off
            if not value:
                self.config.CAMERA_MONITORING_ENABLED = False
                self.config.AUDIO_MONITORING_ENABLED = False
                self.config.DISTANCE_MONITORING_ENABLED = False
                client["camera_monitoring"] = False
                client["audio_monitoring"] = False
                client["distance_monitoring"] = False
                self.add_log_message("All sensors disabled")

            # Update required in synchronous mode
            client.update()
        except Exception as e:
            logger.error(f"Error callback global enable: {e}")

    def _on_video_duration_change(self, client, value):
        """Callback when the video duration changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.VIDEO_DURATION_MIN,
                self.config.VIDEO_DURATION_MAX,
                self.config.VIDEO_DURATION
            )

            if validated_value != value:
                logger.warning(f"Video duration corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["video_duration"] = validated_value

            self.config.VIDEO_DURATION = validated_value
            msg = f"Video duration set to {validated_value}s"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Video duration set to {validated_value}s"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback video duration: {e}")

    def _on_video_fps_change(self, client, value):
        """Callback when the video FPS changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.VIDEO_FPS_MIN,
                self.config.VIDEO_FPS_MAX,
                self.config.VIDEO_FPS
            )

            if validated_value != value:
                logger.warning(f"Video FPS corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["video_fps"] = validated_value

            self.config.VIDEO_FPS = validated_value
            msg = f"Video FPS set to {validated_value}"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Video FPS set to {validated_value}"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback video FPS: {e}")

    def _on_video_quality_change(self, client, value):
        """Callback when the video quality changes"""
        try:
            validated_value = self.config.validate_threshold(
                value,
                self.config.VIDEO_QUALITY_MIN,
                self.config.VIDEO_QUALITY_MAX,
                self.config.VIDEO_QUALITY
            )

            if validated_value != value:
                logger.warning(f"Video quality corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["video_quality"] = validated_value

            self.config.VIDEO_QUALITY = validated_value
            msg = f"Video quality set to {validated_value}%"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Video quality set to {validated_value}%"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback video quality: {e}")

    def _on_record_video_enabled_change(self, client, value):
        """Callback when the video recording setting changes"""
        try:
            self.config.RECORD_VIDEO_ENABLED = value
            msg = f"Video recording {'enabled' if value else 'disabled'}"
            logger.info(msg)

            # Update status and log
            client["system_status"] = msg
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback record video enabled: {e}")

    def _on_send_videos_telegram_change(self, client, value):
        """Callback when the Telegram video sending setting changes"""
        try:
            self.config.SEND_VIDEOS_TELEGRAM = value
            msg = f"Telegram video sending {'enabled' if value else 'disabled'}"
            logger.info(msg)

            # Update status and log
            client["system_status"] = msg
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback send videos telegram: {e}")

    def _on_photo_quality_change(self, client, value):
        """Callback when the photo quality changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 10, 100, self.config.PHOTO_QUALITY
            )

            if validated_value != value:
                logger.warning(f"Photo quality corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["photo_quality"] = validated_value

            self.config.PHOTO_QUALITY = validated_value
            msg = f"Photo quality set to {validated_value}%"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Photo quality set to {validated_value}%"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback photo quality: {e}")

    def _on_telegram_photo_quality_change(self, client, value):
        """Callback when the Telegram photo quality changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 10, 100, self.config.TELEGRAM_PHOTO_QUALITY
            )

            if validated_value != value:
                logger.warning(f"Telegram photo quality corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["telegram_photo_quality"] = validated_value

            self.config.TELEGRAM_PHOTO_QUALITY = validated_value
            msg = f"Telegram photo quality set to {validated_value}%"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Telegram photo quality set to {validated_value}%"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback telegram photo quality: {e}")

    def _on_audio_gain_change(self, client, value):
        """Callback when the audio gain changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 0, 48, self.config.AUDIO_GAIN
            )

            if validated_value != value:
                logger.warning(f"Audio gain corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["audio_gain"] = validated_value

            self.config.AUDIO_GAIN = validated_value
            msg = f"Audio gain set to {validated_value}dB"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Audio gain set to {validated_value}dB"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback audio gain: {e}")

    def _on_distance_recalibration_change(self, client, value):
        """Callback when the distance recalibration interval changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 60, 3600, self.config.DISTANCE_RECALIBRATION
            )

            if validated_value != value:
                logger.warning(f"Distance recalibration corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["distance_recalibration"] = validated_value

            self.config.DISTANCE_RECALIBRATION = validated_value
            msg = f"Distance recalibration interval set to {validated_value}s"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Distance recalibration: {validated_value}s"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback distance recalibration: {e}")

    def _on_max_images_change(self, client, value):
        """Callback when the maximum number of images changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 5, 100, self.config.MAX_IMAGES
            )

            if validated_value != value:
                logger.warning(f"Max images corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["max_images"] = validated_value

            self.config.MAX_IMAGES = validated_value
            msg = f"Maximum number of images set to {validated_value}"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Max images: {validated_value}"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error callback max images: {e}")

    def _on_max_videos_change(self, client, value):
        """Callback when the maximum number of videos changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 2, 20, self.config.MAX_VIDEOS
            )

            if validated_value != value:
                logger.warning(f"Max videos corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["max_videos"] = validated_value

            self.config.MAX_VIDEOS = validated_value
            msg = f"Maximum number of videos set to {validated_value}"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Max videos: {validated_value}"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error in max videos callback: {e}")

    def _on_max_telegram_photos_change(self, client, value):
        """Callback when the maximum number of Telegram photos changes"""
        try:
            validated_value = self.config.validate_threshold(
                value, 2, 20, self.config.MAX_TELEGRAM_PHOTOS
            )

            if validated_value != value:
                logger.warning(f"Max Telegram photos corrected from {value} to {validated_value}")
                # Also correct the value in the cloud
                client["max_telegram_photos"] = validated_value

            self.config.MAX_TELEGRAM_PHOTOS = validated_value
            msg = f"Maximum number of Telegram photos set to {validated_value}"
            logger.info(msg)

            # Temporarily update status and log
            temp_status = f"Max Telegram photos: {validated_value}"
            client["system_status"] = temp_status
            self.add_log_message(msg)

            # Update required in synchronous mode
            client.update()

            # After a while, restore the normal status
            time.sleep(0.5)
            self._update_system_status()
            client.update()
        except Exception as e:
            logger.error(f"Error in max Telegram photos callback: {e}")

    def start(self):
        """Starts the connection to the cloud"""
        try:
            if self.client:
                try:
                    # Set the client as connected
                    self.is_connected = True
                    logger.info("Arduino IoT Cloud connection started")

                    # Bidirectional synchronization at startup
                    for i in range(3):  # Multiple attempts
                        time.sleep(0.5)
                        # First sync from the cloud to the local config
                        if self.sync_from_cloud():
                            logger.info("Initial configuration synchronized from the cloud")
                            break

                    # Then sync from the local config to the cloud (for safety)
                    time.sleep(0.5)
                    self.sync_to_cloud()

                    # Initial log message
                    self.add_log_message("System started and connected to the cloud")

                    # Update system status
                    self._update_system_status()
                    self.client.update()

                    return True
                except Exception as e:
                    logger.error(f"Error during cloud client startup: {str(e)}")
                    # Alternative attempt
                    logger.info("Alternative attempt to connect to the cloud...")
                    time.sleep(1)
                    self.client.update()
                    self.is_connected = True
                    self.sync_from_cloud()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error starting cloud connection: {e}")
            return False

    def check_connection(self):
        """Checks the connection status and attempts reconnection if necessary"""
        current_time = time.time()

        # Additional call for synchronous mode
        if self.is_connected and self.client:
            try:
                self.client.update()
            except Exception as e:
                logger.debug(f"Error updating cloud client: {e}", verbose=True)
                self.is_connected = False

        # Check the connection at regular intervals
        if current_time - self.last_connection_check < self.connection_check_interval:
            return self.is_connected

        self.last_connection_check = current_time

        # Check the WiFi connection
        if self.wifi and not self.wifi.isconnected():
            logger.warning("WiFi disconnected, attempting reconnection...")
            try:
                self.wifi.connect(WIFI_SSID, WIFI_PASS)
                time.sleep(5)

                if self.wifi.isconnected():
                    logger.info("WiFi reconnected")
                    # Also try to reconnect to the cloud
                    try:
                        self.client.update()
                        self.is_connected = True
                        logger.info("Cloud connection reestablished")
                    except Exception as e:
                        logger.error(f"Error reconnecting to the cloud: {e}")
                        self.is_connected = False
                else:
                    logger.error("WiFi reconnection failed")
                    self.is_connected = False
            except Exception as e:
                logger.error(f"Error during reconnection: {e}")
                self.is_connected = False

        # Additional client update for synchronous mode
        if self.is_connected and self.client:
            try:
                logger.debug("Updating cloud state...", verbose=True)
                self.client.update()
            except Exception as e:
                logger.error(f"Error updating cloud client: {e}")
                self.is_connected = False

        return self.is_connected

    def update_status(self, status):
        """Updates the system status on the cloud"""
        if self.client and self.is_connected:
            try:
                self.client["system_status"] = status
                # In synchronous mode, update() is required after each change
                self.client.update()
                return True
            except Exception as e:
                logger.error(f"Error updating status: {e}")
                return False
        return False

    def _update_system_status(self):
        """Updates the system status based on the current configuration"""
        if not self.is_connected or not self.client:
            return False

        try:
            # Compose the status message
            status_msg = f"System {'active' if self.config.GLOBAL_ENABLE else 'inactive'} | Camera: {'ON' if self.config.CAMERA_MONITORING_ENABLED else 'OFF'} | Audio: {'ON' if self.config.AUDIO_MONITORING_ENABLED else 'OFF'} | Distance: {'ON' if self.config.DISTANCE_MONITORING_ENABLED else 'OFF'}"

            # Update the cloud variable
            self.client["system_status"] = status_msg

            return True
        except Exception as e:
            logger.error(f"Error updating system status: {e}")
            return False

    def add_log_message(self, message):
        """Adds a message to the cloud log"""
        if self.client and self.is_connected:
            try:
                # Record timestamp
                timestamp = time.localtime()
                time_str = f"{timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"

                # Format the message
                log_msg = f"[{time_str}] {message}"

                # Add to the local buffer
                self.log_messages.append(log_msg)

                # Keep only the last message
                if len(self.log_messages) > 1:
                    self.log_messages = self.log_messages[-1:]

                # Update the cloud variable
                self.client["log_messages"] = "\n".join(self.log_messages)

                # In synchronous mode, update() is required after each change
                self.client.update()

                return True
            except Exception as e:
                logger.error(f"Error adding log: {e}")
                return False
        return False

    def notify_event(self, event_type, details=""):
        """Notifies an event on the cloud"""
        if self.client and self.is_connected:
            try:
                # Record timestamp
                timestamp = time.localtime()
                time_str = f"{timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"

                # Format the event message
                event_msg = f"{event_type}: {details}"

                # Update the cloud variables
                self.client["last_event"] = event_msg
                self.client["last_event_time"] = time_str
                self.client["event_type"] = event_type

                # Also add to the log
                self.add_log_message(f"Event: {event_msg}")

                # Update status to show the event
                temp_status = f"Event {event_type} detected: {details}"
                self.client["system_status"] = temp_status

                # In synchronous mode, update() is required after each change
                self.client.update()

                # After a while, restore the normal status
                time.sleep(2)
                self._update_system_status()
                self.client.update()

                return True
            except Exception as e:
                logger.error(f"Error notifying event: {e}")
                return False
        return False
