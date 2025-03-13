import time
import pyb
import gc
import os

# Import delle nostre classi
from config import Config
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from distance_detector import DistanceDetector
from file_manager import FileManager
from photo_manager import PhotoManager

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
        
        # Inizializza il photo manager (gestore foto)
        photo_manager = PhotoManager(Config, file_manager)
        
        # Prepara la camera per il motion detection se necessario
        if Config.CAMERA_MONITORING_ENABLED:
            photo_manager.init_camera_for_motion()
        
        # Inizializza i detector solo se abilitati
        camera_detector = None
        audio_detector = None
        distance_detector = None
        
        # Inizializza il rilevatore di movimento via camera se abilitato
        if Config.CAMERA_MONITORING_ENABLED:
            camera_detector = CameraDetector(Config)
            debug_print("Rilevatore camera inizializzato")
        
        # Inizializza il rilevatore audio se abilitato
        if Config.AUDIO_MONITORING_ENABLED:
            audio_detector = AudioDetector(Config, file_manager, photo_manager)
            audio_detector.start_audio_detection()
            debug_print("Rilevatore audio inizializzato e avviato")
        
        # Inizializza il rilevatore di distanza se abilitato
        if Config.DISTANCE_MONITORING_ENABLED:
            distance_detector = DistanceDetector(Config)
            if distance_detector.distance_enabled:
                debug_print(f"Rilevatore distanza inizializzato, distanza base: {distance_detector.base_distance}mm")
            else:
                debug_print("Errore inizializzazione sensore distanza")
        
        debug_print("Sistema di sorveglianza avviato")
        debug_print(f"Camera monitoring: {'ENABLED' if Config.CAMERA_MONITORING_ENABLED else 'DISABLED'}")
        debug_print(f"Audio monitoring: {'ENABLED' if Config.AUDIO_MONITORING_ENABLED else 'DISABLED'}")
        debug_print(f"Distance monitoring: {'ENABLED' if Config.DISTANCE_MONITORING_ENABLED else 'DISABLED'}")
        
        # Configura un handler per il pulsante RESET (se possibile)
        try:
            def reset_pressed(line):
                debug_print("Reset pressed, syncing filesystem...")
                file_manager.sync_filesystem()
                debug_print("Safe to reset now")
            
            # Configura interrupt sul pulsante RESET (se disponibile)
            extint = pyb.ExtInt(pyb.Pin('RESET'), pyb.ExtInt.IRQ_FALLING, pyb.Pin.PULL_UP, reset_pressed)
            debug_print("Reset button handler configured")
        except:
            debug_print("Reset button handler not available")
        
        # Segnala avvio con LED blu
        blue_led.on()
        time.sleep(1)
        blue_led.off()
        
        # Loop principale
        last_motion_time = 0
        last_distance_time = 0
        last_sync_time = 0
        sync_interval = 30  # secondi
        
        while True:
            try:
                current_time = time.time()
                
                # Sincronizzazione periodica del filesystem
                if current_time - last_sync_time > sync_interval:
                    file_manager.sync_filesystem()
                    last_sync_time = current_time
                
                # Controllo camera solo se abilitato
                if Config.CAMERA_MONITORING_ENABLED and camera_detector:
                    if current_time - last_motion_time > Config.INHIBIT_PERIOD:
                        if camera_detector.check_motion():
                            debug_print("Movimento rilevato, cattura foto...")
                            green_led.on()
                            time.sleep(0.1)
                            green_led.off()
                            
                            # Cattura una foto usando il photo manager
                            if photo_manager.capture_save_photo("camera_alert"):
                                last_motion_time = current_time
                                # Reset del rilevamento di movimento
                                camera_detector.reset_detection()
                
                # Controllo distanza solo se abilitato
                if Config.DISTANCE_MONITORING_ENABLED and distance_detector and distance_detector.distance_enabled:
                    if current_time - last_distance_time > Config.INHIBIT_PERIOD:
                        if distance_detector.check_distance():
                            debug_print("Distanza variata, cattura foto...")
                            green_led.on()
                            time.sleep(0.1)
                            green_led.off()
                            
                            # Cattura una foto nella cartella distance_alert
                            if photo_manager.capture_save_photo("distance_alert", "dist"):
                                last_distance_time = current_time
                
                # Breve pausa per ridurre il carico CPU
                pyb.delay(100)
                
                # Lampeggia il LED blu ogni 30 cicli per indicare che il sistema è in esecuzione
                if int(time.time() * 10) % 30 == 0:
                    blue_led.toggle()
                
            except Exception as e:
                debug_print(f"Errore nel loop principale: {e}")
                time.sleep(1)
                
    except Exception as e:
        debug_print(f"Errore fatale: {e}")
        red_led.on()
    finally:
        # Assicurati di fermare lo streaming audio se il programma termina
        if 'audio_detector' in locals() and audio_detector:
            try:
                audio_detector.stop_audio_detection()
            except:
                pass

if __name__ == "__main__":
    main()