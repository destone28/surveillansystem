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
    MOTION_THRESHOLD = 1000    # Soglia per il rilevamento del movimento (%)
    FRAME_SIZE = sensor.QVGA   # Risoluzione per rilevamento movimento
    PHOTO_SIZE = sensor.QVGA   # Risoluzione per le foto
    MAX_IMAGES = 20            # Numero massimo di immagini da mantenere per camera
    PHOTO_QUALITY = 90         # Qualità dell'immagine JPEG (0-100)
    
    # Audio settings
    SOUND_THRESHOLD = 8723     # Soglia per rilevamento suoni
    MAX_PHOTOS = 20            # Numero massimo di foto da mantenere per audio
    FRAME_QUALITY = 35         # Qualità delle foto salvate dall'audio
    
    # Distance settings
    DISTANCE_THRESHOLD = 817   # Soglia di tolleranza in mm per rilevamento distanza
    
    # Video settings
    VIDEO_DURATION = 18        # Durata del video in secondi
    VIDEO_FPS = 16             # Frame per secondo
    VIDEO_QUALITY = 49         # Qualità video (0-100)
    
    # General settings
    INHIBIT_PERIOD = 8         # Secondi di inibizione tra una foto e l'altra
    
    # Cloud settings
    CLOUD_ENABLED = True       # Abilita/disabilita connessione cloud
    
    # Istanza cloud_manager (verrà impostata dopo l'inizializzazione)
    cloud_manager = None
    
    @classmethod
    def set_cloud_manager(cls, cloud_manager):
        """Imposta il riferimento all'istanza del cloud manager"""
        cls.cloud_manager = cloud_manager