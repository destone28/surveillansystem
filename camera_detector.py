import os
import time
import pyb
import sensor
import image
import gc
import logger

# LED per feedback visivo
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

class CameraDetector:
    def __init__(self, config):
        print("### INIZIALIZZAZIONE CAMERA DETECTOR SEMPLIFICATO CORRETTO ###")
        self.config = config
        self.prev_brightness = None
        self.camera_enabled = False
        self.frame_count = 0
        
        # Stampa configurazione
        print(f"Motion threshold configurato: {self.config.MOTION_THRESHOLD}")
        
        # Garbage collection
        gc.collect()
        print(f"Memoria libera: {gc.mem_free()} bytes")
        
        # Inizializza la camera
        self.init_camera()
    
    def init_camera(self):
        """Inizializza la camera con impostazioni minimali"""
        print(">> Inizializzazione camera semplificata...")
        try:
            # Reset completo
            sensor.reset()
            
            # Usa bianco e nero e risoluzione minima
            sensor.set_pixformat(sensor.GRAYSCALE)
            sensor.set_framesize(sensor.QQVGA)  # 160x120
            
            # Skip frames per stabilizzazione
            sensor.skip_frames(time=300)
            
            # Cattura frame iniziale
            print(">> Stabilizzazione sensore...")
            sensor.snapshot()
            
            self.camera_enabled = True
            print(">> Camera inizializzata con successo")
            
            # Segnale visivo
            green_led.on()
            time.sleep(0.2)
            green_led.off()
            
        except Exception as e:
            print(f"!!! ERRORE INIZIALIZZAZIONE CAMERA: {e}")
            logger.error(f"Errore inizializzazione camera: {e}")
    
    def check_motion(self):
        """Metodo ultra-semplificato di rilevamento del movimento"""
        if not self.camera_enabled:
            return False
        
        try:
            # Incrementa contatore frame
            self.frame_count += 1
            
            # Cattura un frame
            img = sensor.snapshot()
            
            # Calcolo luminosità media usando l'istogramma
            # Questo è più affidabile e non ha problemi di tipo
            hist = img.get_histogram()
            stats = hist.get_statistics()
            current_mean = stats.mean()  # Questo sarà sempre un valore numerico singolo
            
            # Debug ogni 20 frame
            if self.frame_count % 20 == 0:
                print(f">> Frame #{self.frame_count}, Luminosità media: {current_mean:.2f}")
            
            # Se è il primo frame, salva valore e esci
            if self.prev_brightness is None:
                self.prev_brightness = current_mean
                print(f">> Primo frame, luminosità base: {current_mean:.2f}")
                return False
            
            # Calcola differenza di luminosità in percentuale
            diff = abs(current_mean - self.prev_brightness)
            diff_percent = (diff / 255) * 100
            
            # Aggiorna valore precedente gradualmente (assicurandoci che sia numerico)
            # Questo risolve il problema di tipo
            self.prev_brightness = (self.prev_brightness * 0.7) + (current_mean * 0.3)
            
            # Debug
            if self.frame_count % 20 == 0:
                print(f">> Differenza luminosità: {diff_percent:.2f}% (threshold: {self.config.MOTION_THRESHOLD}%)")
                print(f">> Tipo prev_brightness: {type(self.prev_brightness)}")
            
            # Verifica se supera la soglia
            if diff_percent > self.config.MOTION_THRESHOLD:
                print(f"!!! MOVIMENTO RILEVATO !!! diff: {diff_percent:.2f}%")
                red_led.on()
                time.sleep(0.1)
                red_led.off()
                return True
                
        except Exception as e:
            print(f"!!! ERRORE MOTION CHECK: {e}")
            logger.error(f"Errore motion check: {e}")
            # Importante: reset del valore per sicurezza
            self.prev_brightness = None
            
        return False
    
    def reset_detection(self):
        """Resetta il rilevamento"""
        print(">> Reset rilevamento movimento")
        # Assicuriamoci di resettare correttamente
        self.prev_brightness = None  # Questo risolve il problema dopo un reset
        self.frame_count = 0  # Resettiamo anche il contatore frame
        logger.info("Reset rilevamento movimento")