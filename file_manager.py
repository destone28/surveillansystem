import os
import time
import pyb
import logger

def debug_print(msg):
    print(msg)

class FileManager:
    def __init__(self):
        # Ensures that the necessary folders exist
        self.ensure_directory("camera_alert")
        self.ensure_directory("audio_alert")
        self.ensure_directory("distance_alert")
        self.ensure_directory("telegram_request")
        self.ensure_directory("camera_videos")
        self.ensure_directory("audio_videos")
        self.ensure_directory("distance_videos")
        self.ensure_directory("other_videos")


    def ensure_directory(self, directory):
        """Ensures that a directory exists"""
        try:
            try:
                os.stat(directory)
                debug_print(f"Folder {directory} exists")
            except OSError:
                os.mkdir(directory)
                debug_print(f"Folder {directory} created")
                self.sync_filesystem()  # Sync after creation
        except Exception as e:
            debug_print(f"Error creating folder {directory}: {e}")

    def manage_files(self, directory, max_files):
        """Manages files in the specified directory (FIFO)"""
        try:
            # Get the list of files in the folder
            files = os.listdir(directory)

            # Filter only jpg files
            jpg_files = [f for f in files if f.endswith('.jpg')]

            # Print information about the files
            debug_print(f"Files in {directory}: {len(jpg_files)}")

            # If the number of files is greater than or equal to the maximum, delete the oldest ones
            if len(jpg_files) >= max_files:
                # Get file information to sort them by date
                file_info = []
                for filename in jpg_files:
                    full_path = f"{directory}/{filename}"
                    try:
                        stat = os.stat(full_path)
                        file_info.append((full_path, stat[8]))  # stat[8] is mtime
                    except:
                        debug_print(f"Unable to get stat for {filename}")

                # Sort files by creation date (oldest to newest)
                file_info.sort(key=lambda x: x[1])

                # Delete the oldest files until we are below the limit
                while len(file_info) >= max_files:
                    oldest_file = file_info.pop(0)[0]
                    debug_print(f"Deleting oldest file: {oldest_file}")
                    try:
                        os.remove(oldest_file)
                    except Exception as e:
                        debug_print(f"Error deleting {oldest_file}: {e}")
                
                # Sync the filesystem after deletions
                self.sync_filesystem()
        except Exception as e:
            debug_print(f"Error managing files in {directory}: {e}")
    
    def save_image(self, img, filename, quality=90):
        """Saves an image with proper flush"""
        try:
            debug_print(f"Saving image: {filename}")
            
            # Direct method: save the image directly to the file
            img.save(filename, quality=quality)
            
            # Sync the filesystem after saving
            self.sync_filesystem()
            debug_print(f"Image successfully saved: {filename}")
            return True
        except Exception as e:
            debug_print(f"Error saving image {filename}: {e}")
            return False
    
    def sync_filesystem(self):
        """Syncs the filesystem to ensure files are written to flash"""
        try:
            # Force a filesystem sync
            os.sync()
            logger.debug("Filesystem synced", verbose=True)
            return True
        except Exception as e:
            logger.error(f"Error syncing filesystem: {e}")
            return False