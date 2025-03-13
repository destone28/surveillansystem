import os
import time
import pyb
import sensor
import image
import gc

# LED per feedback visivo
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

def debug_print(msg):
    print(msg)

class CameraDetector:
    def __init__(self, config):
        self.config = config
        self.prev_pixels = None
        self.camera_enabled = False
        self.current_mode = "motion"  # "motion" o "photo"

        # Forza il garbage collection all'avvio
        gc.collect()

        self.init_camera_for_motion()

    def init_camera_for_motion(self):
        """Inizializza la camera per il rilevamento del movimento"""
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.GRAYSCALE)  # Usa scala di grigi per il motion detection
            sensor.set_framesize(self.config.FRAME_SIZE)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=2000)

            self.camera_enabled = True
            self.current_mode = "motion"
            debug_print("Camera inizializzata per motion detection")
            debug_print(f"Dimensione immagine: {sensor.width()}x{sensor.height()}")
        except Exception as e:
            debug_print(f"Errore camera motion: {e}")

    def init_camera_for_photo(self):
        """Inizializza la camera per scattare foto"""
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(self.config.PHOTO_SIZE)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=100)

            self.camera_enabled = True
            self.current_mode = "photo"
            debug_print("Camera inizializzata per foto")
        except Exception as e:
            debug_print(f"Errore camera photo: {e}")

    def check_motion(self):
        """Controlla se c'è movimento nell'inquadratura"""
        if not self.camera_enabled:
            return False

        # Se la camera è in modalità foto, reinizializzala per il motion detection
        if self.current_mode != "motion":
            self.init_camera_for_motion()

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

    def capture_photo(self, file_manager, directory="camera_alert"):
        """Cattura una foto e la salva nella cartella specificata (default: camera_alert)"""
        if not self.camera_enabled:
            debug_print("Camera non disponibile per foto")
            return False

        try:
            # Passa alla modalità foto se necessario
            if self.current_mode != "photo":
                self.init_camera_for_photo()

            # Accendi il LED rosso quando scatti
            red_led.on()

            # Cattura l'immagine
            img = sensor.snapshot()

            # Crea un nome file con timestamp
            timestamp = int(time.time())
            filename = f"{directory}/img_{timestamp}.jpg"

            # Salva l'immagine usando il file manager migliorato
            success = file_manager.save_image(img, filename, self.config.PHOTO_QUALITY)

            # Gestisci la logica FIFO
            if success:
                file_manager.manage_files(directory, self.config.MAX_IMAGES)

            # Spegni il LED rosso
            red_led.off()

            # Reset della variabile di rilevamento e torna alla modalità di rilevamento
            self.prev_pixels = None
            if self.current_mode != "motion":
                self.init_camera_for_motion()

            return success
        except Exception as e:
            debug_print(f"Errore nella cattura della foto: {e}")
            red_led.off()

            # Tenta di tornare alla modalità motion comunque
            try:
                if self.current_mode != "motion":
                    self.init_camera_for_motion()
            except:
                pass

            return False
