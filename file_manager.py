import os
import time

def debug_print(msg):
    print(msg)

class FileManager:
    def __init__(self):
        # Assicura che le cartelle necessarie esistano
        self.ensure_directory("camera_alert")
        self.ensure_directory("audio_alert")

    def ensure_directory(self, directory):
        """Assicura che una directory esista"""
        try:
            # Verifica se la cartella esiste
            try:
                os.stat(directory)
                debug_print(f"Cartella {directory} esistente")
            except OSError:
                # La cartella non esiste, creala
                os.mkdir(directory)
                debug_print(f"Cartella {directory} creata")
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
                        # Usa la data di creazione come criterio di ordinamento
                        file_info.append((full_path, stat[8]))  # stat[8] è mtime
                    except:
                        debug_print(f"Impossibile ottenere stat per {filename}")

                # Ordina i file per data di creazione (dal più vecchio al più recente)
                file_info.sort(key=lambda x: x[1])

                # Elimina i file più vecchi fino a quando non siamo sotto il limite
                while len(file_info) >= max_files:
                    oldest_file = file_info.pop(0)[0]  # Prendi il file più vecchio
                    debug_print(f"Eliminazione file più vecchio: {oldest_file}")
                    try:
                        os.remove(oldest_file)
                    except Exception as e:
                        debug_print(f"Errore eliminazione {oldest_file}: {e}")
        except Exception as e:
            debug_print(f"Errore nella gestione dei file in {directory}: {e}")
