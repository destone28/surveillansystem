import network
import time
from arduino_iot_cloud import ArduinoCloudClient
from secrets import WIFI_SSID, WIFI_PASS, DEVICE_ID, SECRET_KEY
import logger

class CloudManager:
    def __init__(self, config):
        """
        Gestisce la connessione con Arduino IoT Cloud e sincronizza le variabili.
        
        Args:
            config: Oggetto di configurazione del sistema
        """
        self.config = config
        self.client = None
        self.wifi = None
        self.is_connected = False
        self.last_connection_check = 0
        self.connection_check_interval = 5  # Ridotto per maggiore reattività
        
        # Imposta il riferimento al cloud manager per il logging
        logger.set_cloud_manager(self)
        
    def connect_wifi(self):
        """Connette il dispositivo alla rete WiFi"""
        try:
            logger.info("Connessione WiFi...", cloud=False)
            self.wifi = network.WLAN(network.STA_IF)
            self.wifi.active(True)
            
            if not self.wifi.isconnected():
                self.wifi.connect(WIFI_SSID, WIFI_PASS)
                
                # Attendi connessione con timeout
                start_time = time.time()
                while not self.wifi.isconnected():
                    if time.time() - start_time > 20:  # Timeout di 20 secondi
                        logger.error("Timeout connessione WiFi")
                        return False
                    time.sleep(0.5)
                    
            logger.info(f"WiFi connesso: {self.wifi.ifconfig()}", cloud=False)
            return True
        except Exception as e:
            logger.error(f"Errore connessione WiFi: {e}")
            return False
            
    def init_cloud(self):
        """Inizializza la connessione ad Arduino IoT Cloud"""
        try:
            logger.info("Inizializzazione Arduino IoT Cloud...", cloud=False)
            
            # Crea il client Arduino Cloud in modalità sincrona
            self.client = ArduinoCloudClient(
                device_id=DEVICE_ID,
                username=DEVICE_ID,
                password=SECRET_KEY,
                sync_mode=True  # Usa modalità sincrona invece di quella asincrona
            )
            
            # Registra le variabili con callback
            self._register_variables()
            
            logger.info("Arduino IoT Cloud inizializzato", cloud=False)
            return True
        except Exception as e:
            logger.error(f"Errore inizializzazione cloud: {e}")
            return False
            
    def _register_variables(self):
        """Registra le variabili e i callback per Arduino IoT Cloud"""
        try:
            # Variabile di attivazione globale - Verifica che il tipo Bool sia corretto
            self.client.register("global_enable", value=self.config.GLOBAL_ENABLE, 
                               on_write=self._on_global_enable_change)
            
            # Variabili di controllo monitoraggio
            self.client.register("audio_monitoring", value=self.config.AUDIO_MONITORING_ENABLED, 
                               on_write=self._on_audio_monitoring_change)
            self.client.register("camera_monitoring", value=self.config.CAMERA_MONITORING_ENABLED, 
                               on_write=self._on_camera_monitoring_change)
            self.client.register("distance_monitoring", value=self.config.DISTANCE_MONITORING_ENABLED, 
                               on_write=self._on_distance_monitoring_change)
            
            # Parametri di rilevamento
            self.client.register("sound_threshold", value=self.config.SOUND_THRESHOLD, 
                               on_write=self._on_sound_threshold_change)
            self.client.register("motion_threshold", value=self.config.MOTION_THRESHOLD, 
                               on_write=self._on_motion_threshold_change)
            self.client.register("distance_threshold", value=self.config.DISTANCE_THRESHOLD, 
                               on_write=self._on_distance_threshold_change)
            
            # Parametri del video
            self.client.register("video_duration", value=self.config.VIDEO_DURATION, 
                               on_write=self._on_video_duration_change)
            self.client.register("video_fps", value=self.config.VIDEO_FPS, 
                               on_write=self._on_video_fps_change)
            self.client.register("video_quality", value=self.config.VIDEO_QUALITY, 
                               on_write=self._on_video_quality_change)
            
            # Parametri generali
            self.client.register("inhibit_period", value=self.config.INHIBIT_PERIOD, 
                               on_write=self._on_inhibit_period_change)
            
            # Variabili di status e notifiche
            self.client.register("system_status", value="Inizializzazione...")
            self.client.register("last_event", value="Nessun evento")
            self.client.register("last_event_time", value="")  # Stringa vuota invece di 0
            self.client.register("log_messages", value="")
            self.client.register("current_video", value="")
            self.client.register("event_type", value="")
            self.client.register("video_list", value="[]")
            
            logger.info("Variabili cloud registrate", cloud=False)
            return True
        except Exception as e:
            logger.error(f"Errore registrazione variabili: {e}")
            return False
    
    def sync_from_cloud(self):
        """Sincronizza lo stato dalle variabili cloud alla configurazione locale"""
        if not self.is_connected or not self.client:
            return False
            
        try:
            logger.info("Sincronizzazione stato dal cloud...", cloud=False)
            
            # Leggi le variabili dal cloud e aggiorna la configurazione locale
            try:
                # Prima richiedi un aggiornamento dal cloud
                self.client.update()
                
                # Leggi lo stato dell'interruttore globale
                cloud_global_enable = self.client["global_enable"]
                self.config.GLOBAL_ENABLE = cloud_global_enable
                
                # Leggi gli stati dei singoli interruttori
                cloud_camera_monitoring = self.client["camera_monitoring"] 
                cloud_audio_monitoring = self.client["audio_monitoring"]
                cloud_distance_monitoring = self.client["distance_monitoring"]
                
                # Aggiorna la configurazione locale
                self.config.CAMERA_MONITORING_ENABLED = cloud_camera_monitoring
                self.config.AUDIO_MONITORING_ENABLED = cloud_audio_monitoring
                self.config.DISTANCE_MONITORING_ENABLED = cloud_distance_monitoring
                
                # Aggiorna tutte le altre impostazioni
                self.config.SOUND_THRESHOLD = self.client["sound_threshold"]
                self.config.MOTION_THRESHOLD = self.client["motion_threshold"]
                self.config.DISTANCE_THRESHOLD = self.client["distance_threshold"]
                self.config.VIDEO_DURATION = self.client["video_duration"]
                self.config.VIDEO_FPS = self.client["video_fps"]
                self.config.VIDEO_QUALITY = self.client["video_quality"]
                self.config.INHIBIT_PERIOD = self.client["inhibit_period"]
                
                logger.info(f"Stato sincronizzato dal cloud: Global={cloud_global_enable}, Camera={cloud_camera_monitoring}, Audio={cloud_audio_monitoring}, Distance={cloud_distance_monitoring}")
                return True
            
            except Exception as e:
                logger.error(f"Errore lettura variabili cloud: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Errore sincronizzazione dal cloud: {e}")
            return False
    
    def sync_to_cloud(self):
        """Sincronizza lo stato dalla configurazione locale alle variabili cloud"""
        if not self.is_connected or not self.client:
            return False
            
        try:
            logger.info("Sincronizzazione stato al cloud...", cloud=False)
            
            # Aggiorna le variabili cloud con i valori della configurazione locale
            try:
                self.client["global_enable"] = self.config.GLOBAL_ENABLE
                self.client["camera_monitoring"] = self.config.CAMERA_MONITORING_ENABLED
                self.client["audio_monitoring"] = self.config.AUDIO_MONITORING_ENABLED
                self.client["distance_monitoring"] = self.config.DISTANCE_MONITORING_ENABLED
                self.client["sound_threshold"] = self.config.SOUND_THRESHOLD
                self.client["motion_threshold"] = self.config.MOTION_THRESHOLD
                self.client["distance_threshold"] = self.config.DISTANCE_THRESHOLD
                self.client["video_duration"] = self.config.VIDEO_DURATION
                self.client["video_fps"] = self.config.VIDEO_FPS
                self.client["video_quality"] = self.config.VIDEO_QUALITY
                self.client["inhibit_period"] = self.config.INHIBIT_PERIOD
                
                # Aggiorna lo stato del sistema
                status_msg = f"Sistema {'attivo' if self.config.GLOBAL_ENABLE else 'disattivato'} | Camera: {'ON' if self.config.CAMERA_MONITORING_ENABLED else 'OFF'} | Audio: {'ON' if self.config.AUDIO_MONITORING_ENABLED else 'OFF'} | Distance: {'ON' if self.config.DISTANCE_MONITORING_ENABLED else 'OFF'}"
                self.client["system_status"] = status_msg
                
                # Forza update per sincronizzazione
                self.client.update()
                
                logger.info(f"Stato sincronizzato al cloud")
                return True
                
            except Exception as e:
                logger.error(f"Errore scrittura variabili cloud: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Errore sincronizzazione al cloud: {e}")
            return False
    
    # I callback delle variabili restano invariati ma aggiorniamo i log
    def _on_camera_monitoring_change(self, client, value):
        self.config.CAMERA_MONITORING_ENABLED = value
        logger.info(f"Camera monitoring {'attivato' if value else 'disattivato'}")
        client["system_status"] = f"Camera monitoring {'attivato' if value else 'disattivato'}"
        client.update()  # Aggiornamento necessario in modalità sincrona
        
        # Sincronizza lo stato completo nel cloud
        self.sync_to_cloud()
        
    def _on_audio_monitoring_change(self, client, value):
        self.config.AUDIO_MONITORING_ENABLED = value
        logger.info(f"Audio monitoring {'attivato' if value else 'disattivato'}")
        client["system_status"] = f"Audio monitoring {'attivato' if value else 'disattivato'}"
        client.update()  # Aggiornamento necessario in modalità sincrona
        
        # Sincronizza lo stato completo nel cloud
        self.sync_to_cloud()
        
    def _on_distance_monitoring_change(self, client, value):
        self.config.DISTANCE_MONITORING_ENABLED = value
        logger.info(f"Distance monitoring {'attivato' if value else 'disattivato'}")
        client["system_status"] = f"Distance monitoring {'attivato' if value else 'disattivato'}"
        client.update()  # Aggiornamento necessario in modalità sincrona
        
        # Sincronizza lo stato completo nel cloud
        self.sync_to_cloud()
        
    def _on_sound_threshold_change(self, client, value):
        self.config.SOUND_THRESHOLD = value
        logger.info(f"Sound threshold cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
        
    def _on_motion_threshold_change(self, client, value):
        self.config.MOTION_THRESHOLD = value
        logger.info(f"Motion threshold cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
        
    def _on_distance_threshold_change(self, client, value):
        self.config.DISTANCE_THRESHOLD = value
        logger.info(f"Distance threshold cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
        
    def _on_inhibit_period_change(self, client, value):
        self.config.INHIBIT_PERIOD = value
        logger.info(f"Inhibit period cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona

    def _on_global_enable_change(self, client, value):
        """Callback quando l'interruttore globale cambia stato"""
        self.config.GLOBAL_ENABLE = value
        status_msg = f"Sistema {'attivato' if value else 'disattivato'} globalmente"
        logger.info(status_msg)
        client["system_status"] = status_msg
        
        # Se disabilitato globalmente, assicuriamoci che tutti i sensori siano disattivati
        if not value:
            self.config.CAMERA_MONITORING_ENABLED = False
            self.config.AUDIO_MONITORING_ENABLED = False
            self.config.DISTANCE_MONITORING_ENABLED = False
            client["camera_monitoring"] = False
            client["audio_monitoring"] = False
            client["distance_monitoring"] = False
        
        # Update necessario in modalità sincrona
        client.update()
        
        # Sincronizza lo stato completo nel cloud
        self.sync_to_cloud()

    def _on_video_duration_change(self, client, value):
        """Callback quando la durata del video cambia"""
        self.config.VIDEO_DURATION = value
        logger.info(f"Video duration cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
        
    def _on_video_fps_change(self, client, value):
        """Callback quando gli FPS del video cambiano"""
        self.config.VIDEO_FPS = value
        logger.info(f"Video FPS cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
        
    def _on_video_quality_change(self, client, value):
        """Callback quando la qualità del video cambia"""
        self.config.VIDEO_QUALITY = value
        logger.info(f"Video quality cambiato a {value}")
        client.update()  # Aggiornamento necessario in modalità sincrona
    
    def start(self):
        """Avvia la connessione al cloud"""
        try:
            if self.client:
                # In modalità sincrona, start() connette ma update() deve essere chiamato periodicamente
                try:
                    self.client.start()
                    self.is_connected = True
                    logger.info("Connessione Arduino IoT Cloud avviata")
                    
                    # Esegui immediatamente un update per sincronizzare lo stato
                    self.client.update()
                    
                    # Sincronizza lo stato dal cloud alla configurazione locale
                    time.sleep(0.5)  # Piccola pausa per assicurarsi che i dati arrivino
                    self.sync_from_cloud()
                    
                    self.update_status("Sistema connesso e online")
                    return True
                except Exception as e:
                    logger.error(f"Errore durante avvio client cloud: {str(e)}")
                    # Tentativo alternativo di connessione
                    logger.info("Tentativo alternativo di connessione cloud...")
                    time.sleep(1)
                    self.client.update()
                    self.is_connected = True
                    
                    # Sincronizza lo stato dal cloud alla configurazione locale
                    self.sync_from_cloud()
                    return True
            return False
        except Exception as e:
            logger.error(f"Errore avvio connessione cloud: {e}")
            return False
    
    def check_connection(self):
        """Verifica lo stato della connessione e tenta riconnessione se necessario"""
        current_time = time.time()
        
        # Chiamata aggiuntiva per modalità sincrona
        if self.is_connected and self.client:
            try:
                self.client.update()
            except Exception as e:
                logger.debug(f"Errore update client cloud: {e}", verbose=True)
        
        # Il resto della logica rimane invariato
        if current_time - self.last_connection_check < self.connection_check_interval:
            return self.is_connected
            
        self.last_connection_check = current_time
        
        # Controlla la connessione WiFi
        if self.wifi and not self.wifi.isconnected():
            logger.warning("WiFi disconnesso, tentativo di riconnessione...")
            try:
                self.wifi.connect(WIFI_SSID, WIFI_PASS)
                time.sleep(5)
                
                if self.wifi.isconnected():
                    logger.info("WiFi riconnesso")
                else:
                    logger.error("Riconnessione WiFi fallita")
                    self.is_connected = False
            except Exception as e:
                logger.error(f"Errore riconnessione: {e}")
                self.is_connected = False
        
        # Update client aggiuntivo per modalità sincrona
        if self.is_connected and self.client:
            try:
                logger.debug("Aggiornamento stato cloud...", verbose=True)
                self.client.update()
            except Exception as e:
                logger.error(f"Errore update client cloud: {e}")
                self.is_connected = False
        
        return self.is_connected
    
    def update_status(self, status):
        """Aggiorna lo stato del sistema sul cloud"""
        if self.client and self.is_connected:
            try:
                self.client["system_status"] = status
                # In modalità sincrona, necessario update() dopo ogni modifica
                self.client.update()
                return True
            except Exception as e:
                logger.error(f"Errore aggiornamento stato: {e}")
                return False
        return False
    
    def add_log_message(self, message):
        """Aggiunge un messaggio al log del cloud"""
        if self.client and self.is_connected:
            try:
                timestamp = time.localtime()
                formatted_time = f"{timestamp[0]}-{timestamp[1]:02d}-{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
                log_entry = f"[{formatted_time}] {message}"
                
                # Aggiunge il messaggio alla fine del log esistente
                current_log = self.client["log_messages"]
                if current_log:
                    # Mantieni solo le ultime 10 righe
                    log_lines = current_log.split("\n")
                    if len(log_lines) > 10:
                        log_lines = log_lines[-10:]
                    log_lines.append(log_entry)
                    self.client["log_messages"] = "\n".join(log_lines)
                else:
                    self.client["log_messages"] = log_entry
                
                # Update necessario in modalità sincrona
                self.client.update()
                return True
            except Exception as e:
                logger.debug(f"Errore aggiunta log: {e}", verbose=True)
                return False
        return False
    
    def notify_event(self, event_type, details=""):
        """Notifica un evento sul cloud"""
        if self.client and self.is_connected:
            try:
                timestamp = time.localtime()
                formatted_time = f"{timestamp[0]}-{timestamp[1]:02d}-{timestamp[2]:02d} {timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
                
                self.client["last_event"] = f"{event_type} {details}"
                self.client["last_event_time"] = formatted_time
                self.client["event_type"] = event_type
                
                # Aggiungi anche al log
                self.add_log_message(f"Evento: {event_type} {details}")
                
                # Update necessario in modalità sincrona
                self.client.update()
                return True
            except Exception as e:
                logger.error(f"Errore notifica evento: {e}")
                return False
        return False