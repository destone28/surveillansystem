import time
from config import Config

# Riferimento globale al cloud manager (verrà impostato durante l'inizializzazione)
cloud_manager = None

def set_cloud_manager(manager):
    """Imposta il cloud manager per il logging"""
    global cloud_manager
    cloud_manager = manager
    Config.set_cloud_manager(manager)

def log(message, level="INFO", cloud=True):
    """
    Sistema centralizzato di logging
    
    Args:
        message: Messaggio da loggare
        level: Livello di log (INFO, DEBUG, ERROR, WARNING)
        cloud: Se True, invia il messaggio anche al cloud se disponibile
    """
    # Stampa sempre gli errori e i warning
    if level in ["ERROR", "WARNING"] or Config.DEBUG:
        # Formatta il messaggio con timestamp e livello
        timestamp = time.localtime()
        time_str = f"{timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
        formatted_msg = f"[{time_str}][{level}] {message}"
        
        # Stampa su console
        print(formatted_msg)
        
        # Invia al cloud se richiesto e disponibile
        if cloud and cloud_manager and Config.LOG_TO_CLOUD:
            try:
                if level == "ERROR":
                    cloud_manager.add_log_message(f"ERRORE: {message}")
                else:
                    cloud_manager.add_log_message(message)
            except Exception as e:
                print(f"[ERROR] Impossibile inviare log al cloud: {e}")

def debug(message, verbose=False, cloud=False):
    """Log di debug (solo se DEBUG è abilitato)"""
    if not verbose or (verbose and Config.VERBOSE_DEBUG):
        log(message, "DEBUG", cloud)

def info(message, cloud=True):
    """Log informativo"""
    log(message, "INFO", cloud)

def warning(message, cloud=True):
    """Log di warning"""
    log(message, "WARNING", cloud)

def error(message, cloud=True):
    """Log di errore"""
    log(message, "ERROR", cloud)