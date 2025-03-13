import sensor

class Config:
    # Debug
    DEBUG = True

    # Camera settings
    MOTION_THRESHOLD = 4       # Soglia per il rilevamento del movimento (%)
    FRAME_SIZE = sensor.VGA    # Risoluzione per rilevamento movimento
    PHOTO_SIZE = sensor.VGA    # Risoluzione per le foto
    MAX_IMAGES = 20            # Numero massimo di immagini da mantenere per camera
    PHOTO_QUALITY = 90         # Qualità dell'immagine JPEG (0-100)

    # Audio settings
    SOUND_THRESHOLD = 700      # Soglia per rilevamento suoni
    MAX_PHOTOS = 20            # Numero massimo di foto da mantenere per audio
    FRAME_QUALITY = 35         # Qualità delle foto salvate dall'audio

    # General settings
    INHIBIT_PERIOD = 2         # Secondi di inibizione tra una foto e l'altra
