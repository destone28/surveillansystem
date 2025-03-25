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
        
        # Sets the reference to the cloud manager for logging
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
            
            # Creates the Arduino Cloud client in synchronous mode
            self.client = ArduinoCloudClient(
                device_id=DEVICE_ID,
                username=DEVICE_ID,
                password=SECRET_KEY,
                sync_mode=True  # Use synchronous mode instead of asynchronous
            )
            
            # Registers variables with callbacks
            self._register_variables()
            
            logger.info("Arduino IoT Cloud initialized", cloud=False)
            return True
        except Exception as e:
            logger.error(f"Cloud initialization error: {e}")
            return False
            
    def _register_variables(self):
        """Registers variables and callbacks for Arduino IoT Cloud"""
        try:
            # Global activation variable - Ensure the Bool type is correct
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
            # logger.info("Synchronizing state from cloud...", cloud=False)
            
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
                
                # logger.info(f"State synchronized from cloud: Global={self.config.GLOBAL_ENABLE}, Camera={self.config.CAMERA_MONITORING_ENABLED}, Audio={self.config.AUDIO_MONITORING_ENABLED}, Distance={self.config.DISTANCE_MONITORING_ENABLED}")
                return True
            
            except Exception as e:
                logger.error(f"Cloud variable reading error: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Cloud synchronization error: {e}")
            return False

    def sync_to_cloud(self):
        """Synchronizes the state from local configuration to cloud variables"""
        if not self.is_connected or not self.client:
            return False
            
        try:
            logger.info("Synchronizing state to cloud...", cloud=False)
            
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
                
                # Update system status
                status_msg = f"System {'active' if self.config.GLOBAL_ENABLE else 'inactive'} | Camera: {'ON' if self.config.CAMERA_MONITORING_ENABLED else 'OFF'} | Audio: {'ON' if self.config.AUDIO_MONITORING_ENABLED else 'OFF'} | Distance: {'ON' if self.config.DISTANCE_MONITORING_ENABLED else 'OFF'}"
                self.client["system_status"] = status_msg
                
                # Force update for synchronization
                self.client.update()
                
                logger.info(f"State synchronized to cloud")
                return True
                
            except Exception as e:
                logger.error(f"Cloud variable writing error: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Cloud synchronization error: {e}")
            return False
