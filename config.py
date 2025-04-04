import sensor

class Config:
    # Debug
    DEBUG = False
    VERBOSE_DEBUG = False  # Only for verbose debug messages
    LOG_TO_CLOUD = True    # Send important logs to the cloud as well

    # Global Enable
    GLOBAL_ENABLE = False

    # Monitoring enable/disable flags
    CAMERA_MONITORING_ENABLED = False   # Enable/disable monitoring via camera
    AUDIO_MONITORING_ENABLED = False    # Enable/disable monitoring via microphone
    DISTANCE_MONITORING_ENABLED = False # Enable/disable monitoring via ToF sensor

    # Camera settings
    MOTION_THRESHOLD = 5       # Threshold for motion detection (%)
    MOTION_THRESHOLD_MIN = 0.5 # Minimum value
    MOTION_THRESHOLD_MAX = 50  # Maximum value
    FRAME_SIZE = sensor.QVGA   # Resolution for motion detection
    PHOTO_SIZE = sensor.QVGA   # Resolution for photos
    MAX_IMAGES = 20            # Maximum number of images to keep per camera
    PHOTO_QUALITY = 90         # JPEG image quality (0-100)

    # Audio settings
    SOUND_THRESHOLD = 2812     # Threshold for sound detection
    SOUND_THRESHOLD_MIN = 500  # Suggested minimum value
    SOUND_THRESHOLD_MAX = 20000 # Suggested maximum value
    MAX_AUDIO_PHOTOS = 20      # Maximum number of photos
    AUDIO_GAIN = 24            # Audio gain in dB

    # Distance settings
    DISTANCE_THRESHOLD = 100   # Tolerance threshold in mm (reduced for higher sensitivity)
    DISTANCE_THRESHOLD_MIN = 10 # Minimum value
    DISTANCE_THRESHOLD_MAX = 2000 # Maximum value
    DISTANCE_RECALIBRATION = 300 # Recalibrate every 300 seconds

    # Video settings - TODO CHECK THIS TO BE DELETED
    VIDEO_DURATION = 5        # Video duration in seconds
    VIDEO_DURATION_MIN = 3     # Minimum duration
    VIDEO_DURATION_MAX = 30    # Maximum duration
    VIDEO_FPS = 15             # Frames per second
    VIDEO_FPS_MIN = 5          # Minimum FPS
    VIDEO_FPS_MAX = 30         # Maximum FPS
    VIDEO_QUALITY = 50         # Video quality (0-100)
    VIDEO_QUALITY_MIN = 10     # Minimum quality
    VIDEO_QUALITY_MAX = 100    # Maximum quality

    # General settings
    INHIBIT_PERIOD = 3         # Inhibition seconds (reduced to detect more events)
    INHIBIT_PERIOD_MIN = 1     # Minimum value
    INHIBIT_PERIOD_MAX = 30    # Maximum value

    # System intervals
    FILESYSTEM_SYNC_INTERVAL = 30   # Filesystem sync interval (seconds)
    CLOUD_SYNC_INTERVAL = 5        # Cloud sync interval (seconds)
    DETECTOR_CHECK_INTERVAL = 2     # Detector state check interval (seconds)

    # Cloud settings
    CLOUD_ENABLED = True       # Enable/disable cloud connection

    # Telegram settings
    TELEGRAM_ENABLED = True           # Enable/disable Telegram bot

    # Telegram photo settings
    SEND_PHOTOS_TELEGRAM = True       # Enable/disable automatic photo sending via Telegram
    MAX_TELEGRAM_PHOTOS = 5           # Maximum number of Telegram photos to keep per category
    TELEGRAM_PHOTO_QUALITY = 100      # Quality for Telegram photos (0-100)
    TELEGRAM_PHOTO_SIZE = sensor.HD   # Resolution for Telegram photos

    # Video recordings settings
    RECORD_VIDEO_ENABLED = True      # Enable/disable video recording
    SEND_VIDEOS_TELEGRAM = True      # Enable/disable video sending via Telegram
    MAX_VIDEOS = 5                   # Maximum number of videos to keep per category
    MAX_VIDEO_SIZE_TELEGRAM = 10000000  # Maximum video size for Telegram (10MB)

    # Cloud manager instance
    cloud_manager = None

    @classmethod
    def set_cloud_manager(cls, cloud_manager):
        """Set the reference to the cloud manager instance"""
        cls.cloud_manager = cloud_manager

    @classmethod
    def validate_threshold(cls, value, min_val, max_val, default=None):
        """Validate a threshold value within the specified limits"""
        if value is None and default is not None:
            return default

        if value < min_val:
            return min_val
        elif value > max_val:
            return max_val

        return value
