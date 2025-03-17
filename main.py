import time
import pyb
import gc
import os

# Import delle nostre classi
from config import Config
import logger
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from distance_detector import DistanceDetector
from file_manager import FileManager
from photo_manager import PhotoManager
from cloud_manager import CloudManager

# LED per feedback visivo
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

def main():
    try:
        # Pulisci la memoria all'avvio
        gc.collect()
        
        # Inizializza il file manager (necessario per le operazioni di base)
        file_manager = FileManager()
        
        # Inizializza il cloud manager (prima degli altri per consentire la configurazione)
        cloud_manager = None
        if Config.CLOUD_ENABLED:
            cloud_manager = CloudManager(Config)
            
            # Connetti al WiFi
            if cloud_manager.connect_wifi():
                if cloud_manager.init_cloud():
                    try:
                        # Avvia la connessione cloud
                        cloud_manager.start()
                        
                        # Sincronizza le impostazioni dal cloud
                        logger.info("Sincronizzazione iniziale dello stato dal cloud...")
                        for i in range(3):  # Alcuni tentativi di sincronizzazione
                            time.sleep(0.5)
                            if cloud_manager.sync_from_cloud():
                                logger.info("Sincronizzazione iniziale completata")
                                break
                            
                    except Exception as e:
                        logger.error(f"Errore durante l'avvio del client cloud: {e}")
        
        # Inizializza il photo manager (gestore foto) comunque
        photo_manager = PhotoManager(Config, file_manager)
        
        # Inizializzazione dinamica dei detector - verranno creati solo quando necessario
        camera_detector = None
        audio_detector = None
        distance_detector = None
        
        # Notifica avvio al cloud
        if cloud_manager and cloud_manager.is_connected:
            cloud_manager.update_status("Sistema avviato, in attesa di comandi")
            cloud_manager.add_log_message("Sistema avviato correttamente")
            
            # Invia lo stato corrente al cloud per sicurezza
            cloud_manager.sync_to_cloud()
        
        # Segnala avvio con LED blu
        blue_led.on()
        time.sleep(1)
        blue_led.off()
        
        # Loop principale
        last_motion_time = 0
        last_distance_time = 0
        last_sync_time = 0
        last_check_state_time = 0
        last_cloud_sync_time = 0
        
        # Intervalli vari
        sync_interval = 30            # Sincronizzazione filesystem (secondi)
        check_state_interval = 3      # Controllo stato sensori (secondi)
        cloud_sync_interval = 10      # Sincronizzazione cloud-config (secondi)
        
        # Loop principale
        while True:
            try:
                current_time = time.time()
                
                # Controlla la connessione cloud con frequenza adeguata
                if cloud_manager:
                    cloud_manager.check_connection()
                
                # Sincronizzazione periodica del filesystem
                if current_time - last_sync_time > sync_interval:
                    file_manager.sync_filesystem()
                    last_sync_time = current_time
                
                # Sincronizzazione periodica tra cloud e configurazione locale
                if cloud_manager and cloud_manager.is_connected and (current_time - last_cloud_sync_time > cloud_sync_interval):
                    cloud_manager.sync_from_cloud()
                    last_cloud_sync_time = current_time
                
                # Controlla periodicamente se i detector devono essere creati o distrutti
                if current_time - last_check_state_time > check_state_interval:
                    last_check_state_time = current_time
                    
                    if Config.GLOBAL_ENABLE:
                        # Camera: crea se abilitato ma non esistente
                        if Config.CAMERA_MONITORING_ENABLED and not camera_detector:
                            photo_manager.init_camera_for_motion()
                            camera_detector = CameraDetector(Config)
                            logger.info("Rilevatore camera inizializzato (on-demand)")
                        # Camera: distruggi se disabilitato ma esistente
                        elif not Config.CAMERA_MONITORING_ENABLED and camera_detector:
                            camera_detector = None
                            logger.info("Rilevatore camera disattivato")
                        
                        # Audio: crea se abilitato ma non esistente
                        if Config.AUDIO_MONITORING_ENABLED and not audio_detector:
                            audio_detector = AudioDetector(Config, file_manager, photo_manager)
                            audio_detector.start_audio_detection()
                            if cloud_manager:
                                audio_detector.set_cloud_manager(cloud_manager)
                            logger.info("Rilevatore audio inizializzato e avviato (on-demand)")
                        # Audio: distruggi se disabilitato ma esistente
                        elif not Config.AUDIO_MONITORING_ENABLED and audio_detector:
                            audio_detector.stop_audio_detection()
                            audio_detector = None
                            logger.info("Rilevatore audio disattivato")
                        
                        # Distanza: crea se abilitato ma non esistente
                        if Config.DISTANCE_MONITORING_ENABLED and not distance_detector:
                            distance_detector = DistanceDetector(Config)
                            if distance_detector.distance_enabled:
                                logger.info(f"Rilevatore distanza inizializzato (on-demand), distanza base: {distance_detector.base_distance}mm")
                            else:
                                logger.warning("Errore inizializzazione sensore distanza")
                                distance_detector = None
                        # Distanza: distruggi se disabilitato ma esistente
                        elif not Config.DISTANCE_MONITORING_ENABLED and distance_detector:
                            distance_detector = None
                            logger.info("Rilevatore distanza disattivato")
                    
                    # Se GLOBAL_ENABLE è disattivato, assicurati che tutti i detector siano distrutti
                    elif not Config.GLOBAL_ENABLE:
                        if camera_detector:
                            camera_detector = None
                            logger.info("Rilevatore camera disattivato (global disable)")
                        
                        if audio_detector:
                            audio_detector.stop_audio_detection()
                            audio_detector = None
                            logger.info("Rilevatore audio disattivato (global disable)")
                        
                        if distance_detector:
                            distance_detector = None
                            logger.info("Rilevatore distanza disattivato (global disable)")
                
                # Esegui il monitoraggio solo se GLOBAL_ENABLE è attivato
                if Config.GLOBAL_ENABLE:
                    # Controllo camera solo se abilitato
                    if Config.CAMERA_MONITORING_ENABLED and camera_detector:
                        if current_time - last_motion_time > Config.INHIBIT_PERIOD:
                            if camera_detector.check_motion():
                                event_msg = "Movimento rilevato, cattura foto..."
                                logger.info(event_msg)
                                green_led.on()
                                time.sleep(0.1)
                                green_led.off()
                                
                                # Cattura una foto usando il photo manager
                                if photo_manager.capture_save_photo("camera_alert"):
                                    last_motion_time = current_time
                                    # Reset del rilevamento di movimento
                                    camera_detector.reset_detection()
                                    
                                    # Notifica cloud
                                    if cloud_manager:
                                        cloud_manager.notify_event("Motion", "Camera trigger")
                    
                    # Controllo distanza solo se abilitato
                    if Config.DISTANCE_MONITORING_ENABLED and distance_detector and distance_detector.distance_enabled:
                        if current_time - last_distance_time > Config.INHIBIT_PERIOD:
                            if distance_detector.check_distance():
                                event_msg = "Distanza variata, cattura foto..."
                                logger.info(event_msg)
                                green_led.on()
                                time.sleep(0.1)
                                green_led.off()
                                
                                # Cattura una foto nella cartella distance_alert
                                if photo_manager.capture_save_photo("distance_alert", "dist"):
                                    last_distance_time = current_time
                                    
                                    # Notifica cloud
                                    if cloud_manager:
                                        current_distance = distance_detector.read_distance()
                                        cloud_manager.notify_event("Distance", f"Distanza: {current_distance}mm")
                else:
                    # Lampeggia LED per indicare che il sistema è in standby
                    if int(time.time() * 2) % 10 == 0:
                        red_led.toggle()
                
                # Breve pausa per ridurre il carico CPU
                pyb.delay(100)
                
                # Lampeggia il LED blu ogni 30 cicli per indicare che il sistema è in esecuzione
                if int(time.time() * 10) % 30 == 0:
                    blue_led.toggle()
                
            except Exception as e:
                logger.error(f"Errore nel loop principale: {e}")
                time.sleep(1)
                
    except Exception as e:
        # Per errori fatali, stampa anche su console standard
        print(f"ERRORE FATALE: {e}")
        
        # Tenta di loggare l'errore anche nel cloud
        try:
            if 'cloud_manager' in locals() and cloud_manager and cloud_manager.is_connected:
                cloud_manager.update_status(f"ERRORE CRITICO: {e}")
        except:
            pass
            
        # Accendi LED rosso per segnalare errore
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