import sensor
import time
import pyb

# LED per feedback visivo
red_led = pyb.LED(1)

def debug_print(msg):
    print(msg)

class PhotoManager:
    def __init__(self, config, file_manager):
        """
        Gestore delle foto che si occupa di catturare e salvare immagini
        
        Args:
            config: Configurazione del sistema
            file_manager: Riferimento al gestore dei file
        """
        self.config = config
        self.file_manager = file_manager
        self.camera_enabled = False
        self.current_mode = None  # Nessuna modalità iniziale
        self.last_photo_path = None  # Traccia dell'ultima foto salvata
        
        # Tentativo iniziale di inizializzazione della camera
        try:
            sensor.reset()
            self.camera_enabled = True
            debug_print("Camera disponibile per il PhotoManager")
        except Exception as e:
            debug_print(f"Errore inizializzazione camera nel PhotoManager: {e}")
    
    def init_camera_for_motion(self):
        """Inizializza la camera per il rilevamento del movimento (grayscale)"""
        if not self.camera_enabled:
            debug_print("Camera non disponibile")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.GRAYSCALE)  # Usa scala di grigi per il motion detection
            sensor.set_framesize(self.config.FRAME_SIZE)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=2000)
            
            self.current_mode = "motion"
            debug_print("Camera inizializzata per motion detection")
            debug_print(f"Dimensione immagine: {sensor.width()}x{sensor.height()}")
            return True
        except Exception as e:
            debug_print(f"Errore camera motion: {e}")
            return False
    
    def init_camera_for_photo(self):
        """Inizializza la camera per scattare foto (RGB)"""
        if not self.camera_enabled:
            debug_print("Camera non disponibile")
            return False
            
        try:
            sensor.reset()
            sensor.set_pixformat(sensor.RGB565)
            sensor.set_framesize(self.config.PHOTO_SIZE)
            sensor.set_vflip(False)
            sensor.set_hmirror(True)
            sensor.skip_frames(time=100)
            
            self.current_mode = "photo"
            debug_print("Camera inizializzata per foto")
            return True
        except Exception as e:
            debug_print(f"Errore camera photo: {e}")
            return False
    
    def capture_save_photo(self, directory, prefix=None, extra_info=None):
        """
        Cattura una foto e la salva nella directory specificata
        
        Args:
            directory: La directory dove salvare l'immagine
            prefix: Prefisso opzionale per il nome del file (default: 'img')
            extra_info: Informazione aggiuntiva da includere nel nome del file
            
        Returns:
            bool: True se la foto è stata catturata e salvata, False altrimenti
        """
        if not self.camera_enabled:
            debug_print("Camera non disponibile per foto")
            return False
            
        # Passa alla modalità foto se necessario
        if self.current_mode != "photo":
            if not self.init_camera_for_photo():
                return False
        
        try:
            # Accendi il LED rosso durante la cattura
            red_led.on()
            
            # Cattura l'immagine
            img = sensor.snapshot()
            
            # Genera nome file con timestamp
            timestamp = int(time.time())
            
            # Prefisso predefinito se non fornito
            if not prefix:
                prefix = "img"
                
            # Formato del nome file
            if extra_info:
                filename = f"{directory}/{prefix}_{timestamp}_{extra_info}.jpg"
            else:
                filename = f"{directory}/{prefix}_{timestamp}.jpg"
            
            # Salva l'immagine
            success = self.file_manager.save_image(img, filename, self.config.PHOTO_QUALITY)
            
            # Salva il percorso dell'ultima foto per riferimento
            if success:
                self.last_photo_path = filename
                debug_print(f"Ultimo percorso foto aggiornato: {self.last_photo_path}")
                
                # Gestisci la logica FIFO
                self.file_manager.manage_files(directory, self.config.MAX_IMAGES)
            
            # Spegni il LED rosso
            red_led.off()
            
            return success
        except Exception as e:
            debug_print(f"Errore nella cattura della foto: {e}")
            red_led.off()
            return False
        finally:
            # In ogni caso, tenta di ripristinare la camera alla modalità di rilevamento
            # se era in quella modalità prima
            if self.current_mode == "photo" and getattr(self, 'previous_mode', None) == "motion":
                self.init_camera_for_motion()