import time
from config import Config

# Global reference to the cloud manager (will be set during initialization)
cloud_manager = None

def set_cloud_manager(manager):
    """Sets the cloud manager for logging"""
    global cloud_manager
    cloud_manager = manager
    Config.set_cloud_manager(manager)

def log(message, level="INFO", cloud=True):
    """
    Centralized logging system
    
    Args:
        message: Message to log
        level: Log level (INFO, DEBUG, ERROR, WARNING)
        cloud: If True, sends the message to the cloud if available
    """
    # Always print errors and warnings
    if level in ["ERROR", "WARNING"] or Config.DEBUG:
        # Format the message with timestamp and level
        timestamp = time.localtime()
        time_str = f"{timestamp[3]:02d}:{timestamp[4]:02d}:{timestamp[5]:02d}"
        formatted_msg = f"[{time_str}][{level}] {message}"
        
        # Print to console
        print(formatted_msg)
        
        # Send to the cloud if requested and available
        if cloud and cloud_manager and Config.LOG_TO_CLOUD:
            try:
                if level == "ERROR":
                    cloud_manager.add_log_message(f"ERROR: {message}")
                else:
                    cloud_manager.add_log_message(message)
            except Exception as e:
                print(f"[ERROR] Unable to send log to the cloud: {e}")

def debug(message, verbose=False, cloud=False):
    """Debug log (only if DEBUG is enabled)"""
    if not verbose or (verbose and Config.VERBOSE_DEBUG):
        log(message, "DEBUG", cloud)

def info(message, cloud=True):
    """Informational log"""
    log(message, "INFO", cloud)

def warning(message, cloud=True):
    """Warning log"""
    log(message, "WARNING", cloud)

def error(message, cloud=True):
    """Error log"""
    log(message, "ERROR", cloud)