import time
from vl53l1x import VL53L1X
from machine import I2C
import pyb
import logger

class DistanceDetector:
    def __init__(self, config):
        self.config = config
        self.tof = None
        self.base_distance = None
        self.distance_enabled = False
        self.last_distances = []  # Buffer per media mobile
        self.debug_counter = 0
        
        self.init_distance_sensor()
        
    def init_distance_sensor(self):
        """Inizializza il sensore di distanza ToF VL53L1X"""
        logger.info("Inizializzazione sensore distanza ToF...")
        
        try:
            # Inizializza l'I2C
            i2c = I2C(2)
            time.sleep(0.1)  # Breve pausa dopo inizializzazione I2C
            
            # Inizializza il sensore
            self.tof = VL53L1X(i2c)
            time.sleep(0.5)  # Pausa per stabilizzazione
            
            # Imposta la modalità di misurazione a lungo raggio
            if hasattr(self.tof, 'set_measurement_timing_budget'):
                self.tof.set_measurement_timing_budget(50000)  # Usa 50ms per maggiore precisione
            
            # Calibrazione iniziale: letture multiple
            self.calibrate_distance()
            
            if self.base_distance > 0:
                self.distance_enabled = True
                logger.info(f"Sensore ToF inizializzato: {self.base_distance}mm")
            else:
                logger.error("Errore lettura distanza iniziale dal sensore ToF")
        except Exception as e:
            logger.error(f"Errore inizializzazione sensore ToF: {e}")
            
    def calibrate_distance(self):
        """Calibra la distanza base con media di multiple letture"""
        readings = []
        valid_readings = 0
        
        # Effettua 5 letture per una calibrazione stabile
        for i in range(5):
            dist = self.read_distance_raw()
            if dist > 0:
                readings.append(dist)
                valid_readings += 1
            time.sleep(0.1)
        
        # Calcola la media delle letture valide
        if valid_readings > 0:
            self.base_distance = sum(readings) / valid_readings
            self.last_distances = [self.base_distance] * 3  # Inizializza buffer
            logger.info(f"Distanza base calibrata: {self.base_distance:.1f}mm ({valid_readings} letture)")
        else:
            self.base_distance = 0
            logger.error("Calibrazione fallita: nessuna lettura valida")
            
    def read_distance_raw(self):
        """Legge la distanza grezza dal sensore ToF"""
        try:
            if self.tof:
                # La funzione read() restituisce la distanza in millimetri
                distance = self.tof.read()
                return distance
            return 0
        except Exception as e:
            logger.debug(f"Errore lettura grezza distanza ToF: {e}", verbose=True)
            return 0
            
    def read_distance(self):
        """Legge la distanza filtrata dal sensore ToF"""
        raw_distance = self.read_distance_raw()
        
        if raw_distance <= 0:
            return 0
            
        # Aggiungi al buffer e mantieni solo gli ultimi 3 valori
        self.last_distances.append(raw_distance)
        if len(self.last_distances) > 3:
            self.last_distances.pop(0)
            
        # Calcola la media per ridurre il rumore
        avg_distance = sum(self.last_distances) / len(self.last_distances)
        return avg_distance
            
    def check_distance(self):
        """Verifica se la distanza attuale supera la soglia"""
        if not self.distance_enabled:
            return False
            
        try:
            # Aumenta il contatore di debug
            self.debug_counter += 1
            
            # Log periodico ogni 20 check
            if self.debug_counter % 20 == 0:
                logger.debug(f"Distance check attivo, soglia: {self.config.DISTANCE_THRESHOLD}mm", verbose=True)
            
            current_distance = self.read_distance()
            if current_distance <= 0:  # Lettura non valida
                return False
                
            diff = abs(current_distance - self.base_distance)
            
            # Log più frequente per debug
            if self.debug_counter % 10 == 0:
                logger.debug(f"Distanza attuale: {current_distance:.1f}mm, base: {self.base_distance:.1f}mm, diff: {diff:.1f}mm", verbose=True)
            
            if diff > self.config.DISTANCE_THRESHOLD:
                logger.info(f"Alert! Distanza cambiata: {current_distance:.1f}mm (diff: {diff:.1f}mm)")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore verifica distanza: {e}")
            return False
            
    def recalibrate(self):
        """Ricalibra la distanza base"""
        try:
            logger.info("Ricalibrazione sensore distanza...")
            self.calibrate_distance()
            return self.base_distance > 0
        except Exception as e:
            logger.error(f"Errore ricalibrazione ToF: {e}")
            return False