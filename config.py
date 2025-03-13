import sensor

class Config:
    # Debug
    DEBUG = True

    # Monitoring enable/disable flags
    CAMERA_MONITORING_ENABLED = True   # Abilita/disabilita monitoraggio via camera
    AUDIO_MONITORING_ENABLED = True    # Abilita/disabilita monitoraggio via microfono
    DISTANCE_MONITORING_ENABLED = True # Abilita/disabilita monitoraggio via sensore ToF

    # Camera settings
    MOTION_THRESHOLD = 4       # Soglia per il rilevamento del movimento (%)
    FRAME_SIZE = sensor.QVGA    # Risoluzione per rilevamento movimento
    PHOTO_SIZE = sensor.QVGA    # Risoluzione per le foto
    MAX_IMAGES = 20            # Numero massimo di immagini da mantenere per camera
    PHOTO_QUALITY = 90         # Qualità dell'immagine JPEG (0-100)

    # Audio settings
    SOUND_THRESHOLD = 700      # Soglia per rilevamento suoni
    MAX_PHOTOS = 20            # Numero massimo di foto da mantenere per audio
    FRAME_QUALITY = 35         # Qualità delle foto salvate dall'audio

    # Distance settings
    DISTANCE_THRESHOLD = 1000  # Soglia di tolleranza in mm per rilevamento distanza

    # General settings
    INHIBIT_PERIOD = 2         # Secondi di inibizione tra una foto e l'altra
