import time
import pyb
import audio
import sensor

# LED per debug
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

# Variabile globale per l'istanza di AudioDetector (sarà impostata durante l'inizializzazione)
global_audio_detector = None

def debug_print(msg):
    print(msg)

# Funzione di callback globale per l'audio
def global_audio_callback(buf):
    global global_audio_detector
    if global_audio_detector:
        global_audio_detector.process_audio(buf)

class AudioDetector:
    def __init__(self, config, file_manager, camera_detector):
        global global_audio_detector
        global_audio_detector = self  # Assegna questa istanza alla variabile globale

        self.config = config
        self.file_manager = file_manager
        self.camera_detector = camera_detector  # Riferimento al camera_detector
        self.audio_enabled = False
        self.last_capture_time = 0
        self.init_audio()

    def init_audio(self):
        """Inizializza solo l'audio (la camera sarà gestita dal CameraDetector)"""
        debug_print("Inizializzazione audio detector...")

        # Audio (solo inizializzazione, lo streaming viene avviato separatamente)
        try:
            audio.init(channels=1, frequency=16000, gain_db=24, highpass=0.9883)
            self.audio_enabled = True
            debug_print("Audio inizializzato")
        except Exception as e:
            debug_print(f"Errore audio: {e}")

    def capture_photo(self, level):
        """Cattura una foto quando viene rilevato un suono"""
        # Controlla il periodo di inibizione
        current_time = time.time()
        if current_time - self.last_capture_time < self.config.INHIBIT_PERIOD:
            return

        self.last_capture_time = current_time

        try:
            # Accende il LED rosso durante la cattura
            red_led.on()

            # Usa il camera_detector per preparare la camera
            self.camera_detector.init_camera_for_photo()

            # Cattura l'immagine
            img = sensor.snapshot()

            # Genera il timestamp per il nome del file
            timestamp = time.localtime()
            filename = f"audio_alert/sound_{timestamp[0]}{timestamp[1]:02d}{timestamp[2]:02d}_{timestamp[3]:02d}{timestamp[4]:02d}{timestamp[5]:02d}_{int(level)}.jpg"

            # Salva l'immagine compressa
            img.compress(quality=self.config.FRAME_QUALITY)
            img.save(filename)
            debug_print(f"Foto da audio salvata: {filename}")

            # Controlla il numero di file nella cartella e applica la logica FIFO
            self.file_manager.manage_files("audio_alert", self.config.MAX_PHOTOS)

            red_led.off()

            # Reinizializza la camera per il rilevamento del movimento
            self.camera_detector.init_camera_for_motion()
            return True
        except Exception as e:
            debug_print(f"Errore nella cattura foto da audio: {e}")
            red_led.off()

            # Tenta di reinizializzare la camera per il rilevamento del movimento
            try:
                self.camera_detector.init_camera_for_motion()
            except:
                pass

            return False

    def process_audio(self, buf):
        """Elabora i dati audio ricevuti dalla callback"""
        if not self.audio_enabled:
            return

        try:
            # Converte i byte in valori signed int
            samples = [buf[i] | (buf[i+1] << 8) for i in range(0, len(buf), 2)]
            # Calcola il valore medio del livello audio
            level = sum(abs(s) for s in samples) / len(samples)

            if level > self.config.SOUND_THRESHOLD:
                debug_print(f"Suono rilevato: {level}")
                # Lampeggia LED per debug
                green_led.on()
                # Cattura una foto
                self.capture_photo(level)
                green_led.off()
        except Exception as e:
            debug_print(f"Errore elaborazione audio: {e}")

    def start_audio_detection(self):
        """Avvia il rilevamento audio"""
        if not self.audio_enabled:
            debug_print("Audio non disponibile per il rilevamento")
            return False

        try:
            # Avvia lo streaming audio con la callback globale
            audio.start_streaming(global_audio_callback)
            debug_print("Streaming audio avviato")
            return True
        except Exception as e:
            debug_print(f"Errore avvio streaming audio: {e}")
            return False

    def stop_audio_detection(self):
        """Ferma il rilevamento audio"""
        try:
            audio.stop_streaming()
            debug_print("Streaming audio fermato")
            return True
        except Exception as e:
            debug_print(f"Errore stop streaming audio: {e}")
            return False
