import os
import time
import pyb
import logger

def debug_print(msg):
    print(msg)

class FileManager:
    def __init__(self):
        # Assicura che le cartelle necessarie esistano
        self.ensure_directory("camera_alert")
        self.ensure_directory("audio_alert")
        self.ensure_directory("distance_alert")
        self.ensure_directory("telegram_request")  # Aggiunto per le foto richieste tramite Telegram


    def ensure_directory(self, directory):
        """Assicura che una directory esista"""
        try:
            try:
                os.stat(directory)
                debug_print(f"Cartella {directory} esistente")
            except OSError:
                os.mkdir(directory)
                debug_print(f"Cartella {directory} creata")
                self.sync_filesystem()  # Sincronizza dopo la creazione
        except Exception as e:
            debug_print(f"Errore nella creazione della cartella {directory}: {e}")

    def manage_files(self, directory, max_files):
        """Gestisce i file nella directory specificata (FIFO)"""
        try:
            # Ottiene la lista dei file nella cartella
            files = os.listdir(directory)

            # Filtra solo i file jpg
            jpg_files = [f for f in files if f.endswith('.jpg')]

            # Stampa le informazioni sui file
            debug_print(f"File in {directory}: {len(jpg_files)}")

            # Se il numero di file è maggiore o uguale al massimo, elimina i più vecchi
            if len(jpg_files) >= max_files:
                # Ottieni le informazioni sui file per ordinarli per data
                file_info = []
                for filename in jpg_files:
                    full_path = f"{directory}/{filename}"
                    try:
                        stat = os.stat(full_path)
                        file_info.append((full_path, stat[8]))  # stat[8] è mtime
                    except:
                        debug_print(f"Impossibile ottenere stat per {filename}")

                # Ordina i file per data di creazione (dal più vecchio al più recente)
                file_info.sort(key=lambda x: x[1])

                # Elimina i file più vecchi fino a quando non siamo sotto il limite
                while len(file_info) >= max_files:
                    oldest_file = file_info.pop(0)[0]
                    debug_print(f"Eliminazione file più vecchio: {oldest_file}")
                    try:
                        os.remove(oldest_file)
                    except Exception as e:
                        debug_print(f"Errore eliminazione {oldest_file}: {e}")
                
                # Sincronizza il filesystem dopo le eliminazioni
                self.sync_filesystem()
        except Exception as e:
            debug_print(f"Errore nella gestione dei file in {directory}: {e}")
    
    def save_image(self, img, filename, quality=90):
        """Salva un'immagine con flush corretto"""
        try:
            debug_print(f"Salvataggio immagine: {filename}")
            
            # Metodo diretto: salva l'immagine direttamente sul file
            img.save(filename, quality=quality)
            
            # Sincronizza il filesystem dopo il salvataggio
            self.sync_filesystem()
            debug_print(f"Immagine salvata con successo: {filename}")
            return True
        except Exception as e:
            debug_print(f"Errore salvataggio immagine {filename}: {e}")
            return False
    
    def sync_filesystem(self):
        """Sincronizza il filesystem per garantire che i file siano scritti su flash"""
        try:
            # Forza un sync del filesystem
            os.sync()
            logger.debug("Filesystem sincronizzato", verbose=True)
            return True
        except Exception as e:
            logger.error(f"Errore sincronizzazione filesystem: {e}")
            return False