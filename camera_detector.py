import os
import time
import pyb
import sensor
import image
import gc
import logger

# LED per feedback visivo
green_led = pyb.LED(2)

class CameraDetector:
    def __init__(self, config):
        self.config = config
        self.prev_img = None
        self.prev_pixels = None
        self.camera_enabled = False
        self.debug_counter = 0
        
        # Forza il garbage collection all'avvio
        gc.collect()
        
        # Inizializza la camera per il motion detection
        self.init_camera()
    
    def init_camera(self):
        """Inizializza la camera per il rilevamento del movimento"""
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.GRAYSCALE)  # Usa scala di grigi per il motion detection
            sensor.set_framesize(self.config.FRAME_SIZE)
            sensor.set_contrast(3)  # Aumenta il contrasto per migliorare il rilevamento movimento
            sensor.set_brightness(0)
            sensor.set_saturation(0)
            sensor.set_auto_gain(False)  # Disabilita auto gain per rilevazione più stabile
            sensor.set_auto_whitebal(False)  # Disabilita white balance per rilevazione più stabile
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=500)  # Ridotto per migliorare i tempi di risposta
            
            # Attendi che la camera si stabilizzi
            for i in range(5):
                sensor.snapshot()
                time.sleep(0.1)
            
            self.camera_enabled = True
            logger.info("Camera inizializzata per motion detection")
            logger.info(f"Dimensione immagine: {sensor.width()}x{sensor.height()}")
        except Exception as e:
            logger.error(f"Errore camera motion: {e}")
    
    def check_motion(self):
        """Controlla se c'è movimento nell'inquadratura"""
        if not self.camera_enabled:
            return False
        
        try:
            # Cattura l'immagine corrente
            current_img = sensor.snapshot()
            
            # Aumenta il contatore di debug
            self.debug_counter += 1
            
            # Log periodico ogni 50 frame
            if self.debug_counter % 50 == 0:
                logger.debug(f"Camera motion check attivo, soglia: {self.config.MOTION_THRESHOLD}%", verbose=True)
            
            # Se è il primo frame, memorizza e esci
            if self.prev_img is None:
                self.prev_img = current_img.copy()
                return False
            
            # Calcola la differenza tra i frame
            diff = current_img.difference(self.prev_img)
            
            # Calcola la percentuale di pixel cambiati
            stats = diff.get_statistics()
            diff_percent = (stats.mean() / 255) * 100  # Normalizza in percentuale
            
            # Aggiorna l'immagine precedente (a intervalli, non sempre)
            if self.debug_counter % 3 == 0:  # Ogni 3 frame
                self.prev_img = current_img.copy()
            
            # Verifica se la variazione supera la soglia
            if diff_percent > self.config.MOTION_THRESHOLD:
                logger.info(f"Movimento rilevato: {diff_percent:.2f}% (soglia: {self.config.MOTION_THRESHOLD}%)")
                return True
                
        except Exception as e:
            logger.error(f"Errore motion detection: {e}")
            # Reset in caso di errore
            self.prev_img = None
            
        return False
    
    def reset_detection(self):
        """Resetta il rilevamento del movimento"""
        self.prev_img = None
        self.prev_pixels = None
        logger.info("Reset rilevamento movimento")