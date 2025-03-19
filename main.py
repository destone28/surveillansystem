import time
import pyb
import gc
import os
import uasyncio as asyncio

import secrets_keys
from config import Config
import logger
from camera_detector import CameraDetector
from audio_detector import AudioDetector
from distance_detector import DistanceDetector
from file_manager import FileManager
from photo_manager import PhotoManager
from cloud_manager import CloudManager
from telegram import TelegramBot  # Libreria diretta Telegram

# LED per feedback visivo
red_led = pyb.LED(1)
green_led = pyb.LED(2)
blue_led = pyb.LED(3)

# Variabili globali
camera_detector = None
audio_detector = None
distance_detector = None
cloud_manager = None
photo_manager = None
file_manager = None
telegram_bot = None
loop = None

# Variabili di controllo ciclo
last_motion_time = 0
last_distance_time = 0
last_sync_time = 0
last_check_state_time = 0
last_cloud_sync_time = 0
last_distance_recalibration = 0
main_interval = 100  # Intervallo in millisecondi per l'esecuzione del loop principale

# Callback per il bot Telegram
def telegram_callback(bot, msg_type, chat_name, sender_name, chat_id, text, entry):
    print(f"TELEGRAM: {msg_type}, {chat_name}, {sender_name}, {chat_id}, {text}")
    # Echo semplice come in example.py
    bot.send(chat_id, "Ehi! " + text)

    # Lampeggia LED per feedback
    green_led.on()
    pyb.delay(100)
    green_led.off()

    # Aggiunta semplice: comando /status mostra lo stato del sistema
    if text == "/status":
        status_msg = (
            f"Sistema: {'Attivo' if Config.GLOBAL_ENABLE else 'Disattivato'}\n"
            f"Camera: {'ON' if Config.CAMERA_MONITORING_ENABLED else 'OFF'}\n"
            f"Audio: {'ON' if Config.AUDIO_MONITORING_ENABLED else 'OFF'}\n"
            f"Distanza: {'ON' if Config.DISTANCE_MONITORING_ENABLED else 'OFF'}"
        )
        bot.send(chat_id, status_msg)

# Task asincrono che esegue il loop principale
async def main_loop():
    global camera_detector, audio_detector, distance_detector
    global cloud_manager, last_motion_time, last_distance_time
    global last_sync_time, last_check_state_time, last_cloud_sync_time
    global last_distance_recalibration

    print("Avvio loop principale...")

    while True:
        try:
            current_time = time.time()

            # Controlla la connessione cloud
            if cloud_manager and cloud_manager.is_connected:
                cloud_manager.check_connection()

            # Sincronizzazione filesystem
            if current_time - last_sync_time > Config.FILESYSTEM_SYNC_INTERVAL:
                file_manager.sync_filesystem()
                last_sync_time = current_time

            # Sincronizzazione cloud
            if cloud_manager and cloud_manager.is_connected and (current_time - last_cloud_sync_time > Config.CLOUD_SYNC_INTERVAL):
                cloud_manager.sync_from_cloud()
                last_cloud_sync_time = current_time

            # Gestione inizializzazione detector
            if current_time - last_check_state_time > Config.DETECTOR_CHECK_INTERVAL:
                last_check_state_time = current_time

                # Gestione detector in base allo stato globale
                if Config.GLOBAL_ENABLE:
                    # Camera detector
                    if Config.CAMERA_MONITORING_ENABLED:
                        if not camera_detector:
                            photo_manager.init_camera_for_motion()
                            camera_detector = CameraDetector(Config)
                            logger.info("Rilevatore camera inizializzato (on-demand)")
                    else:
                        if camera_detector:
                            camera_detector = None
                            logger.info("Rilevatore camera disattivato")

                    # Audio detector
                    if Config.AUDIO_MONITORING_ENABLED:
                        if not audio_detector:
                            audio_detector = AudioDetector(Config, file_manager, photo_manager)
                            audio_detector.start_audio_detection()
                            if cloud_manager:
                                audio_detector.set_cloud_manager(cloud_manager)
                            logger.info("Rilevatore audio inizializzato e avviato (on-demand)")
                    else:
                        if audio_detector:
                            audio_detector.stop_audio_detection()
                            audio_detector = None
                            logger.info("Rilevatore audio disattivato")

                    # Distance detector
                    if Config.DISTANCE_MONITORING_ENABLED:
                        if not distance_detector:
                            distance_detector = DistanceDetector(Config)
                            if distance_detector.distance_enabled:
                                logger.info(f"Rilevatore distanza inizializzato (on-demand), distanza base: {distance_detector.base_distance:.1f}mm")
                            else:
                                logger.warning("Errore inizializzazione sensore distanza")
                                distance_detector = None
                        elif current_time - last_distance_recalibration > Config.DISTANCE_RECALIBRATION:
                            # Ricalibrare periodicamente il sensore di distanza
                            distance_detector.recalibrate()
                            last_distance_recalibration = current_time
                    else:
                        if distance_detector:
                            distance_detector = None
                            logger.info("Rilevatore distanza disattivato")
                else:
                    # Disattiva tutti i detector se GLOBAL_ENABLE è disattivato
                    if camera_detector:
                        camera_detector = None
                        logger.info("Rilevatore camera disattivato (global disable)")

                    if audio_detector:
                        audio_detector.stop_audio_detection()
                        audio_detector = None
                        logger.info("Rilevatore audio disattivato (global disable)")

                    if distance_detector:
                        distance_detector = None
                        logger.info("Rilevatore distanza disattivato (global disable)")

            # SEZIONE RILEVAMENTO EVENTI
            if Config.GLOBAL_ENABLE:
                # Rilevamento movimento camera
                if Config.CAMERA_MONITORING_ENABLED and camera_detector:
                    if current_time - last_motion_time > Config.INHIBIT_PERIOD:
                        if camera_detector.check_motion():
                            event_msg = "Movimento rilevato, cattura foto..."
                            logger.info(event_msg)
                            green_led.on()
                            time.sleep(0.1)
                            green_led.off()

                            # Cattura foto
                            if photo_manager.capture_save_photo("camera_alert"):
                                last_motion_time = current_time
                                # Reset rilevamento movimento
                                camera_detector.reset_detection()

                                # Notifica cloud
                                if cloud_manager:
                                    cloud_manager.notify_event("Motion", "Camera trigger")

                                # Notifica Telegram
                                if telegram_bot:
                                    try:
                                        for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                            if chat_id != "*":  # Ignora l'asterisco
                                                telegram_bot.send(chat_id, "🚨 Movimento rilevato!")
                                    except Exception as e:
                                        logger.error(f"Errore notifica Telegram: {e}")

                # Rilevamento variazione distanza
                if Config.DISTANCE_MONITORING_ENABLED and distance_detector and distance_detector.distance_enabled:
                    if current_time - last_distance_time > Config.INHIBIT_PERIOD:
                        if distance_detector.check_distance():
                            current_distance = distance_detector.read_distance()
                            event_msg = f"Distanza variata: {current_distance:.1f}mm, cattura foto..."
                            logger.info(event_msg)
                            green_led.on()
                            time.sleep(0.1)
                            green_led.off()

                            # Cattura foto
                            if photo_manager.capture_save_photo("distance_alert", "dist", int(current_distance)):
                                last_distance_time = current_time

                                # Notifica cloud
                                if cloud_manager:
                                    cloud_manager.notify_event("Distance", f"Distanza: {int(current_distance)}mm")

                                # Notifica Telegram
                                if telegram_bot:
                                    try:
                                        for chat_id in secrets_keys.TELEGRAM_AUTHORIZED_USERS:
                                            if chat_id != "*":  # Ignora l'asterisco
                                                telegram_bot.send(chat_id, f"📏 Variazione distanza: {int(current_distance)}mm")
                                    except Exception as e:
                                        logger.error(f"Errore notifica Telegram: {e}")
            else:
                # Sistema disabilitato
                if int(time.time() * 2) % 10 == 0:
                    red_led.toggle()

            # Indicazione attività sistema
            if int(time.time() * 10) % 30 == 0:
                blue_led.toggle()

        except Exception as e:
            logger.error(f"Errore nel loop principale: {e}")

        # Attendi per la prossima iterazione (in modo asincrono)
        await asyncio.sleep_ms(main_interval)

def main():
    global camera_detector, audio_detector, distance_detector
    global cloud_manager, photo_manager, file_manager, telegram_bot, loop

    try:
        # Pulisci la memoria all'avvio
        gc.collect()

        # Inizializzazione del loop asincrono
        loop = asyncio.get_event_loop()

        # Inizializza il file manager (necessario per le operazioni di base)
        file_manager = FileManager()

        # Inizializza il cloud manager (prima degli altri per consentire la configurazione)
        if Config.CLOUD_ENABLED:
            cloud_manager = CloudManager(Config)

            # Connetti al WiFi
            if cloud_manager.connect_wifi():
                if cloud_manager.init_cloud():
                    try:
                        # Avvia la connessione cloud
                        cloud_manager.start()

                        # Sincronizza le impostazioni dal cloud
                        logger.info("Sincronizzazione iniziale dello stato dal cloud...")
                        for i in range(3):  # Alcuni tentativi di sincronizzazione
                            time.sleep(0.5)
                            if cloud_manager.sync_from_cloud():
                                logger.info("Sincronizzazione iniziale completata")
                                break

                    except Exception as e:
                        logger.error(f"Errore durante l'avvio del client cloud: {e}")

        # Inizializza il photo manager (gestore foto) comunque
        photo_manager = PhotoManager(Config, file_manager)

        # Segnala avvio con LED blu
        blue_led.on()
        time.sleep(1)
        blue_led.off()

        # Avvia il task del loop principale
        asyncio.create_task(main_loop())

        # Avvio del bot Telegram esattamente come in example.py
        if hasattr(Config, 'TELEGRAM_ENABLED') and Config.TELEGRAM_ENABLED:
            try:
                print("Inizializzazione bot Telegram...")
                telegram_bot = TelegramBot(secrets_keys.TELEGRAM_TOKEN, telegram_callback)
                telegram_bot.debug = False  # Attiva debug

                print("Connessione WiFi per Telegram...")
                try:
                    telegram_bot.connect_wifi(Config.WIFI_SSID, Config.WIFI_PASS)
                except Exception as e:
                    print(f"Errore WiFi (potrebbe essere già connesso): {e}")

                print("Avvio bot Telegram...")
                asyncio.create_task(telegram_bot.run())

                # Segnala avvio Telegram completo con LED
                for _ in range(3):
                    green_led.on()
                    time.sleep(0.1)
                    green_led.off()
                    time.sleep(0.1)

                print("Bot Telegram avviato!")
            except Exception as e:
                print(f"Errore inizializzazione Telegram: {e}")

        print("Sistema avviato, in attesa di messaggi...")

        # Esegui il loop forever come in example.py
        loop.run_forever()

    except Exception as e:
        # Per errori fatali, stampa anche su console standard
        print(f"ERRORE FATALE: {e}")

        # Tenta di loggare l'errore anche nel cloud
        try:
            if cloud_manager and cloud_manager.is_connected:
                cloud_manager.update_status(f"ERRORE CRITICO: {e}")
        except:
            pass

        # Accendi LED rosso per segnalare errore
        red_led.on()
    finally:
        # Assicurati di fermare lo streaming audio se il programma termina
        if audio_detector:
            try:
                audio_detector.stop_audio_detection()
            except:
                pass

        # Ferma il bot Telegram
        if telegram_bot:
            try:
                telegram_bot.stop()
            except:
                pass

if __name__ == "__main__":
    main()
