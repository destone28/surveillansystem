import time
import pyb
import audio
import sensor
import logger

# LED per debug
green_led = pyb.LED(2)

# Variabile globale per l'istanza di AudioDetector (sarà impostata durante l'inizializzazione)
global_audio_detector = None

# Funzione di callback globale per l'audio
def global_audio_callback(buf):
    global global_audio_detector
    if global_audio_detector:
        global_audio_detector.process_audio(buf)

class AudioDetector:
    def __init__(self, config, file_manager, photo_manager):
        global global_audio_detector
        global_audio_detector = self  # Assegna questa istanza alla variabile globale
        
        self.config = config
        self.file_manager = file_manager
        self.photo_manager = photo_manager
        self.cloud_manager = None  # Sarà impostato dal main
        self.telegram_manager = None  # Sarà impostato dal main
        self.audio_enabled = False
        self.last_capture_time = 0
        self.init_audio()

    def init_audio(self):
        """Inizializza solo l'audio"""
        logger.info("Inizializzazione audio detector...")

        # Audio (solo inizializzazione, lo streaming viene avviato separatamente)
        try:
            audio.init(channels=1, frequency=16000, gain_db=self.config.AUDIO_GAIN, highpass=0.9883)
            self.audio_enabled = True
            logger.info(f"Audio inizializzato con gain {self.config.AUDIO_GAIN}dB")
        except Exception as e:
            logger.error(f"Errore audio: {e}")

    def process_audio(self, buf):
        """Elabora i dati audio ricevuti dalla callback"""
        # Verifica se l'audio è abilitato E se il monitoraggio audio è attivo
        if not self.audio_enabled or not self.config.AUDIO_MONITORING_ENABLED or not self.config.GLOBAL_ENABLE:
            return

        try:
            # Converte i byte in valori signed int
            samples = [buf[i] | (buf[i+1] << 8) for i in range(0, len(buf), 2)]
            # Calcola il valore medio del livello audio
            level = sum(abs(s) for s in samples) / len(samples)

            if level > self.config.SOUND_THRESHOLD:
                logger.info(f"Suono rilevato: {level} (soglia: {self.config.SOUND_THRESHOLD})")
                
                # Controlla il periodo di inibizione
                current_time = time.time()
                if current_time - self.last_capture_time < self.config.INHIBIT_PERIOD:
                    return
                    
                self.last_capture_time = current_time
                
                # Lampeggia LED verde per debug
                green_led.on()
                
                # Cattura foto usando PhotoManager
                if self.photo_manager.capture_save_photo("audio_alert", "sound", int(level)):
                    # Notifica cloud se disponibile
                    if self.cloud_manager:
                        self.cloud_manager.notify_event("Audio", f"Livello: {int(level)}")
                    
                    # Notifica Telegram se disponibile
                    if self.telegram_manager:
                        try:
                            for chat_id in self.config.TELEGRAM_AUTHORIZED_USERS:
                                if chat_id != "*":  # Ignora l'asterisco
                                    self.telegram_manager.send(chat_id, f"🔊 Suono rilevato! Livello: {int(level)}")
                        except Exception as e:
                            logger.error(f"Errore notifica Telegram: {e}")
                
                green_led.off()
        except Exception as e:
            logger.error(f"Errore elaborazione audio: {e}")

    def start_audio_detection(self):
        """Avvia il rilevamento audio"""
        if not self.audio_enabled:
            logger.warning("Audio non disponibile per il rilevamento")
            return False

        try:
            # Avvia lo streaming audio con la callback globale
            audio.start_streaming(global_audio_callback)
            logger.info("Streaming audio avviato")
            return True
        except Exception as e:
            logger.error(f"Errore avvio streaming audio: {e}")
            return False

    def stop_audio_detection(self):
        """Ferma il rilevamento audio"""
        try:
            audio.stop_streaming()
            logger.info("Streaming audio fermato")
            return True
        except Exception as e:
            logger.error(f"Errore stop streaming audio: {e}")
            return False
        
    def set_cloud_manager(self, cloud_manager):
        """Imposta il riferimento al cloud manager"""
        self.cloud_manager = cloud_manager

    def set_telegram_manager(self, telegram_manager):
        """Imposta il riferimento al telegram manager"""
        self.telegram_manager = telegram_manager