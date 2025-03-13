import os
import time
import pyb
import sensor
import image
import gc

# LED per feedback visivo
green_led = pyb.LED(2)

def debug_print(msg):
    print(msg)

class CameraDetector:
    def __init__(self, config):
        self.config = config
        self.prev_pixels = None
        self.camera_enabled = False
        
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
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=2000)
            
            self.camera_enabled = True
            debug_print("Camera inizializzata per motion detection")
            debug_print(f"Dimensione immagine: {sensor.width()}x{sensor.height()}")
        except Exception as e:
            debug_print(f"Errore camera motion: {e}")
    
    def check_motion(self):
        """Controlla se c'è movimento nell'inquadratura"""
        if not self.camera_enabled:
            return False
        
        try:
            img = sensor.snapshot()
            
            # Calcola la media dell'immagine
            hist = img.get_histogram()
            mean = hist.get_statistics().mean()
            
            # Se è il primo frame, memorizza il valore e esci
            if self.prev_pixels is None:
                self.prev_pixels = mean
                return False
            
            # Calcola la variazione percentuale
            diff_percent = abs(mean - self.prev_pixels) / self.prev_pixels * 100
            
            # Aggiorna il valore precedente
            self.prev_pixels = mean
            
            # Verifica se la variazione supera la soglia
            if diff_percent > self.config.MOTION_THRESHOLD:
                debug_print(f"Movimento rilevato: {diff_percent:.2f}%")
                return True
                
        except Exception as e:
            debug_print(f"Errore motion detection: {e}")
            
        return False
    
    def reset_detection(self):
        """Resetta il rilevamento del movimento (da chiamare dopo aver cambiato modalità camera)"""
        self.prev_pixels = None