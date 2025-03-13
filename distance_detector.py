import time
from vl53l1x import VL53L1X
from machine import I2C
import pyb

def debug_print(msg):
    print(msg)

class DistanceDetector:
    def __init__(self, config):
        self.config = config
        self.tof = None
        self.base_distance = None
        self.distance_enabled = False

        self.init_distance_sensor()

    def init_distance_sensor(self):
        """Inizializza il sensore di distanza ToF VL53L1X"""
        debug_print("Inizializzazione sensore distanza ToF...")

        try:
            # Inizializza il sensore VL53L1X utilizzando I2C(2)
            self.tof = VL53L1X(I2C(2))

            # Leggi la distanza base al momento dell'inizializzazione
            self.base_distance = self.read_distance()

            if self.base_distance > 0:
                self.distance_enabled = True
                debug_print(f"Sensore ToF inizializzato: {self.base_distance}mm")
            else:
                debug_print("Errore lettura distanza iniziale dal sensore ToF")
        except Exception as e:
            debug_print(f"Errore inizializzazione sensore ToF: {e}")

    def read_distance(self):
        """Legge la distanza dal sensore ToF"""
        try:
            if self.tof:
                # La funzione read() restituisce la distanza in millimetri
                distance = self.tof.read()
                return distance
            return 0
        except Exception as e:
            debug_print(f"Errore lettura distanza ToF: {e}")
            return 0

    def check_distance(self):
        """Verifica se la distanza attuale supera la soglia"""
        if not self.distance_enabled:
            return False

        try:
            current_distance = self.read_distance()
            if current_distance <= 0:  # Lettura non valida
                return False

            diff = abs(current_distance - self.base_distance)

            if diff > self.config.DISTANCE_THRESHOLD:
                debug_print(f"Alert! Distanza cambiata: {current_distance}mm (diff: {diff}mm)")
                return True
            return False
        except Exception as e:
            debug_print(f"Errore verifica distanza: {e}")
            return False

    def recalibrate(self):
        """Ricalibra la distanza base"""
        try:
            new_base = self.read_distance()
            if new_base > 0:
                self.base_distance = new_base
                debug_print(f"Sensore ToF ricalibrato: {self.base_distance}mm")
                return True
            return False
        except Exception as e:
            debug_print(f"Errore ricalibrazione ToF: {e}")
            return False
