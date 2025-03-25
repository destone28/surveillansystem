import sensor
import time
import mjpeg
import os
import gc
import pyb
import logger

# LED per debug
red_led = pyb.LED(1)
blue_led = pyb.LED(3)

class VideoManager:
    def __init__(self, config, file_manager):
        """
        Gestore dei video che si occupa di registrare e salvare video
        
        Args:
            config: Configurazione del sistema
            file_manager: Riferimento al gestore dei file
        """
        self.config = config
        self.file_manager = file_manager
        self.camera_enabled = False
        self.current_mode = None  # Nessuna modalità iniziale
        self.last_video_path = None  # Traccia dell'ultimo video salvato
        self.telegram_manager = None  # Sarà impostato dal main
        
        # Crea le directory per i video
        self.file_manager.ensure_directory("camera_videos")
        self.file_manager.ensure_directory("audio_videos")
        self.file_manager.ensure_directory("distance_videos")
        
        # Tentativo iniziale di inizializzazione della camera
        try:
            sensor.reset()
            self.camera_enabled = True
            logger.info("Camera disponibile per VideoManager")
        except Exception as e:
            logger.error(f"Errore inizializzazione camera nel VideoManager: {e}")
    
    def init_camera_for_video(self):
        """Inizializza la camera per registrazione video (RGB565)"""
        if not self.camera_enabled:
            logger.warning("Camera non disponibile per video")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)  # RGB565 per il video
            sensor.set_framesize(sensor.QVGA)    # QVGA (320x240) per video
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=1000)  # Attendi per stabilizzazione
            
            self.current_mode = "video"
            logger.info("Camera inizializzata per registrazione video")
            return True
        except Exception as e:
            logger.error(f"Errore camera video: {e}")
            return False
    
    def record_video(self, event_type, extra_info=None):
        """
        Registra un video e lo salva nella directory appropriata
        
        Args:
            event_type: Tipo di evento ("camera", "audio", "distance")
            extra_info: Informazione aggiuntiva da includere nel nome del file
            
        Returns:
            bool: True se il video è stato registrato e salvato, False altrimenti
        """
        if not self.camera_enabled:
            logger.warning("Camera non disponibile per video")
            return False
            
        # Memorizza la modalità corrente per ripristinarla dopo
        prev_mode = self.current_mode
        
        try:
            # Inizializza la camera per il video
            if not self.init_camera_for_video():
                return False
                
            # Forza il garbage collection prima di iniziare la registrazione
            gc.collect()
            
            # Determina la directory di salvataggio in base al tipo di evento
            if event_type == "camera":
                directory = "camera_videos"
            elif event_type == "audio":
                directory = "audio_videos"
            elif event_type == "distance":
                directory = "distance_videos"
            else:
                directory = "other_videos"
                
            # Assicura che la directory esista
            self.file_manager.ensure_directory(directory)
                
            # Generate filename with timestamp
            timestamp = int(time.time())
            
            if extra_info:
                filename = f"{directory}/video_{timestamp}_{extra_info}.mjpeg"
            else:
                filename = f"{directory}/video_{timestamp}.mjpeg"
                
            logger.info(f"Avvio registrazione video: {filename}")
            
            # Accendi il LED rosso durante la registrazione
            red_led.on()
            blue_led.on()  # Aggiunge LED blu per distinguere registrazione video
            
            # Crea l'oggetto Mjpeg
            video = mjpeg.Mjpeg(filename)
            
            # Registra il video per la durata configurata
            frames_to_record = self.config.VIDEO_DURATION * self.config.VIDEO_FPS
            
            clock = time.clock()  # Per tracciare FPS
            
            start_time = time.time()
            actual_frames = 0
            
            while time.time() - start_time < self.config.VIDEO_DURATION:
                if actual_frames >= frames_to_record:
                    break
                    
                clock.tick()
                img = sensor.snapshot()
                
                # Aggiungi timestamp nel video
                current_time = time.localtime()
                timestamp_text = f"{current_time[3]:02d}:{current_time[4]:02d}:{current_time[5]:02d}"
                img.draw_string(5, 5, timestamp_text, color=(255, 255, 255), scale=2)
                
                # Aggiungi etichetta del tipo di evento
                event_label = f"Evento: {event_type.upper()}"
                img.draw_string(5, sensor.height() - 20, event_label, color=(255, 255, 255), scale=2)
                
                # Scrivi il frame al video con la qualità specificata
                video.write(img, quality=self.config.VIDEO_QUALITY)
                actual_frames += 1
                
                # Se stiamo registrando più velocemente del FPS target, aggiungi un ritardo
                target_frame_time = 1.0 / self.config.VIDEO_FPS
                elapsed = clock.avg() / 1000.0  # convert to seconds
                
                if elapsed < target_frame_time:
                    delay = target_frame_time - elapsed
                    time.sleep(delay)
                    
                # Aggiornamento debug ogni 10 frame
                if actual_frames % 10 == 0:
                    logger.debug(f"Registrazione video: {actual_frames}/{frames_to_record} frame, FPS: {clock.fps()}", verbose=True)
                    
                    # Alterna LED blu per feedback visivo durante registrazione
                    if actual_frames % 20 == 0:
                        blue_led.toggle()
            
            # Chiudi il video
            video.close()
            
            # Spegni i LED
            red_led.off()
            blue_led.off()
            
            # Aggiorna il percorso dell'ultimo video
            self.last_video_path = filename
            logger.info(f"Video salvato: {self.last_video_path}, {actual_frames} frame")
            
            # Gestione dei file FIFO
            max_videos = 5  # Limite di default
            if hasattr(self.config, 'MAX_VIDEOS'):
                max_videos = self.config.MAX_VIDEOS
                
            self.file_manager.manage_files(directory, max_videos)
            
            return True
            
        except Exception as e:
            logger.error(f"Errore registrazione video: {e}")
            red_led.off()
            blue_led.off()
            return False
            
        finally:
            # Ripristina la modalità precedente della camera
            if prev_mode == "motion":
                # Ripristina la modalità per rilevamento movimento
                try:
                    sensor.reset()
                    sensor.set_pixformat(sensor.GRAYSCALE)
                    sensor.set_framesize(self.config.FRAME_SIZE)
                    sensor.set_vflip(False)
                    sensor.set_hmirror(True)
                    sensor.skip_frames(time=500)
                    self.current_mode = "motion"
                except Exception as e:
                    logger.error(f"Errore ripristino camera motion: {e}")
    
    def set_telegram_manager(self, telegram_manager):
        """Imposta il riferimento al telegram manager"""
        self.telegram_manager = telegram_manager
