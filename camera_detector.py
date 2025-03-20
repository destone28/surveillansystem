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
        print("### INIZIALIZZAZIONE CAMERA DETECTOR ROBUSTO ###")
        self.config = config
        self.prev_brightness = None
        self.camera_enabled = False
        self.frame_count = 0
        self.error_count = 0

        # Stampa configurazione
        print(f"Motion threshold configurato: {self.config.MOTION_THRESHOLD}")

        # Garbage collection
        gc.collect()
        print(f"Memoria libera: {gc.mem_free()} bytes")

        # Inizializza la camera
        self.init_camera()

    def init_camera(self):
        """Inizializza la camera con impostazioni minimali"""
        print(">> Inizializzazione camera...")
        try:
            # Reset completo
            sensor.reset()

            # Usa bianco e nero e risoluzione minima
            sensor.set_pixformat(sensor.GRAYSCALE)
            sensor.set_framesize(sensor.QQVGA)  # 160x120

            # Skip frames per stabilizzazione
            sensor.skip_frames(time=300)

            # Cattura frame iniziale e pulisci memoria
            print(">> Stabilizzazione sensore...")
            sensor.snapshot()
            gc.collect()

            self.camera_enabled = True
            print(">> Camera inizializzata con successo")

            # Segnale visivo
            green_led.on()
            time.sleep(0.2)
            green_led.off()

        except Exception as e:
            print(f"!!! ERRORE INIZIALIZZAZIONE CAMERA: {e}")
            logger.error(f"Errore inizializzazione camera: {e}")
            self.camera_enabled = False

    def check_motion(self):
        """Metodo robusto di rilevamento movimento con protezione errori"""
        if not self.camera_enabled:
            return False

        try:
            # Incrementa contatore frame
            self.frame_count += 1

            # Cattura un frame
            img = sensor.snapshot()

            # Calcola luminosità media
            try:
                hist = img.get_histogram()
                stats = hist.get_statistics()
                current_mean = float(stats.mean())
            except Exception as e:
                print(f">> Errore calcolo statistica: {e}")
                # Valore fallback
                current_mean = 128.0

            # Debug periodico
            if self.frame_count % 100 == 0:
                print(f">> Frame #{self.frame_count}, Luminosità media: {current_mean:.2f}")
                print(f">> Memoria libera: {gc.mem_free()} bytes")

            # Se è il primo frame, salva valore e esci
            if self.prev_brightness is None:
                self.prev_brightness = float(current_mean)
                print(f">> Primo frame, luminosità base: {current_mean:.2f}")
                return False

            # Calcola differenza di luminosità in percentuale
            try:
                diff = abs(current_mean - float(self.prev_brightness))
                diff_percent = (diff / 255.0) * 100.0
            except (TypeError, ValueError) as e:
                print(f">> Errore calcolo diff: {e}, reset brightness")
                self.prev_brightness = float(current_mean)
                return False

            # Aggiorna valore precedente gradualmente
            try:
                self.prev_brightness = float(0.7 * float(self.prev_brightness) + 0.3 * float(current_mean))
            except Exception as e:
                print(f">> Errore aggiornamento brightness: {e}")
                self.prev_brightness = float(current_mean)

            # Reset errori consecutivi
            self.error_count = 0

            # Debug
            if self.frame_count % 100 == 0:
                print(f">> Differenza luminosità: {diff_percent:.2f}% (threshold: {self.config.MOTION_THRESHOLD}%)")
                # print(f">> Tipo prev_brightness: {type(self.prev_brightness)}")

            # Verifica se supera la soglia
            if diff_percent > self.config.MOTION_THRESHOLD:
                print(f"!!! MOVIMENTO RILEVATO !!! diff: {diff_percent:.2f}%")
                red_led.on()
                time.sleep(0.1)
                red_led.off()
                return True

        except Exception as e:
            self.error_count += 1
            print(f"!!! ERRORE MOTION CHECK ({self.error_count}): {e}")
            logger.error(f"Errore motion check: {e}")

            # Reset in caso di errori ripetuti
            if self.error_count >= 3:
                print(">> Reset completo a causa di errori ripetuti")
                self.prev_brightness = None
                gc.collect()  # Libera memoria

        return False

    def reset_detection(self):
        """Reset completo del rilevamento"""
        print(">> Reset rilevamento movimento")
        # Reset sicuro
        try:
            self.prev_brightness = None
            self.error_count = 0
            self.frame_count = 0

            # Forza GC per liberare memoria
            gc.collect()

            logger.info("Reset rilevamento movimento")
        except Exception as e:
            print(f">> Errore durante reset: {e}")
