import time
import pyb
import gc

# Import delle nostre classi
from config import Config
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from file_manager import FileManager

# LED per feedback visivo
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

def debug_print(msg):
    if Config.DEBUG:
        print(msg)

def main():
    try:
        # Pulisci la memoria all'avvio
        gc.collect()

        # Inizializza il file manager
        file_manager = FileManager()

        # Inizializza il rilevatore di movimento via camera
        camera_detector = CameraDetector(Config)

        # Inizializza il rilevatore audio e passa il camera_detector
        audio_detector = AudioDetector(Config, file_manager, camera_detector)

        # Avvia il rilevamento audio
        audio_detector.start_audio_detection()

        debug_print("Sistema di sorveglianza avviato")
        blue_led.on()
        time.sleep(1)
        blue_led.off()

        # Loop principale
        last_motion_time = 0

        while True:
            try:
                current_time = time.time()

                # Controlla se siamo fuori dal periodo di inibizione per la camera
                if current_time - last_motion_time > Config.INHIBIT_PERIOD:
                    if camera_detector.check_motion():
                        debug_print("Movimento rilevato, cattura foto...")
                        green_led.on()
                        time.sleep(0.1)
                        green_led.off()

                        # Cattura una foto
                        if camera_detector.capture_photo(file_manager):
                            last_motion_time = current_time

                # Breve pausa per ridurre il carico CPU
                pyb.delay(100)

            except Exception as e:
                debug_print(f"Errore nel loop principale: {e}")
                time.sleep(1)

    except Exception as e:
        debug_print(f"Errore fatale: {e}")
        red_led.on()
    finally:
        # Assicurati di fermare lo streaming audio se il programma termina
        try:
            audio_detector.stop_audio_detection()
        except:
            pass

if __name__ == "__main__":
    main()
