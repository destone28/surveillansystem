import sensor

class Config:
    # Debug
    DEBUG = True
    VERBOSE_DEBUG = False  # Solo per messaggi verbosi di debug
    LOG_TO_CLOUD = True    # Invia log importanti anche al cloud
    
    # Global Enable
    GLOBAL_ENABLE = False
    
    # Monitoring enable/disable flags
    CAMERA_MONITORING_ENABLED = False   # Abilita/disabilita monitoraggio via camera
    AUDIO_MONITORING_ENABLED = False    # Abilita/disabilita monitoraggio via microfono
    DISTANCE_MONITORING_ENABLED = False # Abilita/disabilita monitoraggio via sensore ToF
    
    # Camera settings
    MOTION_THRESHOLD = 5       # Soglia per il rilevamento del movimento (%)
    MOTION_THRESHOLD_MIN = 0.5 # Valore minimo
    MOTION_THRESHOLD_MAX = 50  # Valore massimo
    FRAME_SIZE = sensor.QVGA   # Risoluzione per rilevamento movimento
    PHOTO_SIZE = sensor.QVGA   # Risoluzione per le foto
    MAX_IMAGES = 20            # Numero massimo di immagini da mantenere per camera
    PHOTO_QUALITY = 90         # Qualità dell'immagine JPEG (0-100)
    
    # Audio settings
    SOUND_THRESHOLD = 8723     # Soglia per rilevamento suoni
    SOUND_THRESHOLD_MIN = 500  # Valore minimo suggerito
    SOUND_THRESHOLD_MAX = 20000 # Valore massimo suggerito
    MAX_AUDIO_PHOTOS = 20      # Numero massimo di foto
    AUDIO_GAIN = 24            # Guadagno audio in dB
    
    # Distance settings
    DISTANCE_THRESHOLD = 100   # Soglia di tolleranza in mm (ridotto per maggiore sensibilità)
    DISTANCE_THRESHOLD_MIN = 10 # Valore minimo
    DISTANCE_THRESHOLD_MAX = 2000 # Valore massimo
    DISTANCE_RECALIBRATION = 300 # Ricalibrare ogni 300 secondi
    
    # Video settings
    VIDEO_DURATION = 18        # Durata del video in secondi
    VIDEO_DURATION_MIN = 3     # Durata minima
    VIDEO_DURATION_MAX = 30    # Durata massima
    VIDEO_FPS = 16             # Frame per secondo
    VIDEO_FPS_MIN = 5          # FPS minimo
    VIDEO_FPS_MAX = 30         # FPS massimo
    VIDEO_QUALITY = 49         # Qualità video (0-100)
    VIDEO_QUALITY_MIN = 10     # Qualità minima
    VIDEO_QUALITY_MAX = 100    # Qualità massima
    
    # General settings
    INHIBIT_PERIOD = 3         # Secondi di inibizione (ridotto per rilevare più eventi)
    INHIBIT_PERIOD_MIN = 1     # Valore minimo
    INHIBIT_PERIOD_MAX = 30    # Valore massimo
    
    # System intervals
    FILESYSTEM_SYNC_INTERVAL = 30   # Intervallo sincronizzazione filesystem (secondi)
    CLOUD_SYNC_INTERVAL = 5        # Intervallo sincronizzazione con cloud (secondi)
    DETECTOR_CHECK_INTERVAL = 2     # Intervallo controllo stato detector (secondi)
    
    # Cloud settings
    CLOUD_ENABLED = True       # Abilita/disabilita connessione cloud
    
    # Telegram settings
    TELEGRAM_ENABLED = True           # Abilita/disabilita bot Telegram
    # TELEGRAM_TOKEN e TELEGRAM_AUTHORIZED_USERS da aggiungere in secrets_keys.py
    
    # WiFi settings - Presi da secrets.py per compatibilità con TelegramBot
    WIFI_SSID = "Uaifai"      
    WIFI_PASS = "#QuestaQui23!" 
    
    # Istanza cloud_manager
    cloud_manager = None
    
    @classmethod
    def set_cloud_manager(cls, cloud_manager):
        """Imposta il riferimento all'istanza del cloud manager"""
        cls.cloud_manager = cloud_manager
        
    @classmethod
    def validate_threshold(cls, value, min_val, max_val, default=None):
        """Convalida un valore di soglia entro i limiti specificati"""
        if value is None and default is not None:
            return default
        
        if value < min_val:
            return min_val
        elif value > max_val:
            return max_val
        
        return value