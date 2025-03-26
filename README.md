# Nicla Vision Alert Detector

## Cos'è questo progetto

Il Nicla Vision Alert Detector è un sistema di videosorveglianza intelligente basato su Arduino Nicla Vision che sfrutta le capacità avanzate del dispositivo per monitorare l'ambiente circostante attraverso tre modalità di rilevamento:

1. **Monitoraggio tramite camera**: rileva movimenti nell'inquadratura e registra video quando viene identificato un cambiamento significativo
2. **Monitoraggio tramite microfono**: rileva suoni che superano una soglia configurabile e attiva la registrazione
3. **Monitoraggio tramite sensore di distanza**: identifica variazioni nella distanza rispetto a una baseline e attiva la registrazione

Il sistema è completamente integrabile con Arduino IoT Cloud, che permette di configurare parametri, abilitare/disabilitare funzionalità e monitorare lo stato del sistema da remoto. Inoltre, include un bot Telegram che invia notifiche, foto e video in tempo reale e permette di controllare il dispositivo tramite semplici comandi.

## A chi è rivolto

Questo sistema è ideale per:

- **Hobbisti e maker** che desiderano sperimentare con progetti avanzati di videosorveglianza
- **Appassionati di domotica** che vogliono integrare un sistema di monitoraggio personalizzabile
- **Sviluppatori** interessati all'esplorazione delle capacità di Arduino Nicla Vision
- **Piccole imprese** che necessitano di un sistema di sorveglianza economico ma flessibile
- **Studenti e educatori** nel campo della robotica e dell'IoT

## Come utilizza Arduino Nicla Vision

Il progetto sfrutta al massimo le capacità hardware dell'Arduino Nicla Vision:

- **Camera integrata**: per il rilevamento del movimento e la cattura di foto/video
- **Microfono**: per il rilevamento di suoni e rumori
- **Sensore Time-of-Flight (VL53L1X)**: per il rilevamento delle variazioni di distanza
- **Processore STM32H747**: per l'elaborazione delle immagini e l'esecuzione del codice MicroPython
- **Connettività WiFi**: per la comunicazione con Arduino IoT Cloud e l'invio di notifiche via Telegram
- **LED integrati**: per fornire feedback visivi sullo stato del sistema

## Guida all'installazione

### Prerequisiti

- Arduino Nicla Vision
- Account Arduino IoT Cloud
- Account Telegram e un bot Telegram creato tramite BotFather
- OpenMV IDE installato sul computer
- MicroPython installato su Arduino Nicla Vision (versione >= 1.2)
- Connessione WiFi

### 1. Installazione di Arduino Agent

- Segui i passaggi per installare l'Arduino Agent su Linux, Windows o macOS all'indirizzo: [https://support.arduino.cc/hc/en-us/articles/360014869820-Install-the-Arduino-Cloud-Agent](https://support.arduino.cc/hc/en-us/articles/360014869820-Install-the-Arduino-Cloud-Agent)

### 2. Installazione di OpenMV IDE

1. Scarica OpenMV IDE dal sito ufficiale: [https://openmv.io/pages/download](https://openmv.io/pages/download)
2. Installa l'IDE seguendo le istruzioni per il tuo sistema operativo
3. Avvia OpenMV IDE
4. Collega Arduino Nicla Vision al computer tramite USB
5. Nella barra degli strumenti, seleziona la porta seriale corretta per il tuo Arduino Nicla Vision
6. Se richiesto, installa il firmware MicroPython per Arduino Nicla Vision

### 3. Configurazione Arduino IoT Cloud

1. **Accedi al tuo account Arduino IoT Cloud** all'indirizzo [https://create.arduino.cc/iot](https://create.arduino.cc/iot)

2. **Crea una nuova Thing**:
   - Clicca su "Create Thing"
   - Assegna un nome alla tua Thing (ad esempio "NiclaVisionAlert")

3. **Associa il dispositivo**:
   - Nella sezione "Associated Devices" clicca su "Select Device"
   - Clicca su "Set Up New Device"
   - Seleziona "Manual Device" in fondo alla pagina e clicca "Continue"
   - Assegna un nome al tuo dispositivo e clicca "Continue"
   - **IMPORTANTE**: Salva il **Device ID** e il **Secret Key** che vengono generati, serviranno per connettere il dispositivo al cloud

4. **Crea le seguenti variabili** nella tua Thing:

   | Nome variabile | Tipo | Descrizione |
   |---------------|------|-------------|
   | global_enable | boolean | Attiva/disattiva tutto il sistema |
   | camera_monitoring | boolean | Attiva/disattiva il monitoraggio via camera |
   | audio_monitoring | boolean | Attiva/disattiva il monitoraggio via microfono |
   | distance_monitoring | boolean | Attiva/disattiva il monitoraggio via sensore di distanza |
   | sound_threshold | integer | Soglia per il rilevamento audio |
   | motion_threshold | float | Soglia per il rilevamento movimento |
   | distance_threshold | integer | Soglia per il rilevamento variazione distanza |
   | video_duration | integer | Durata dei video registrati (in secondi) |
   | video_fps | integer | Frequenza dei fotogrammi video |
   | video_quality | integer | Qualità dei video (1-100) |
   | inhibit_period | integer | Periodo minimo tra due rilevamenti (in secondi) |
   | system_status | string | Stato attuale del sistema |
   | last_event | string | Ultimo evento rilevato |
   | last_event_time | string | Orario dell'ultimo evento |
   | log_messages | string | Log del sistema |
   | record_video_enabled | boolean | Attiva/disattiva la registrazione video |
   | send_videos_telegram | boolean | Attiva/disattiva l'invio di video via Telegram |

5. **Crea un Dashboard**:
   - Vai alla sezione "Dashboards" e clicca "Create Dashboard"
   - Assegna un nome al dashboard (ad esempio "NiclaVision Control")
   - Aggiungi i seguenti widget associati alle variabili create:
     - Switch per: global_enable, camera_monitoring, audio_monitoring, distance_monitoring, record_video_enabled, send_videos_telegram
     - Slider per: sound_threshold, motion_threshold, distance_threshold, video_duration, video_fps, video_quality, inhibit_period
     - Text per: system_status, last_event, last_event_time, log_messages

### 4. Creazione del Bot Telegram

1. **Crea un nuovo bot su Telegram**:
   - Avvia una chat con BotFather (@BotFather) su Telegram
   - Invia il comando `/newbot`
   - Segui le istruzioni per dare un nome al tuo bot
   - Al termine, riceverai un **token** per l'API del bot. Salvalo, ti servirà per configurare il sistema

2. **Ottieni il tuo chat ID**:
   - Avvia una chat con IDBot (@myidbot) su Telegram
   - Invia il comando `/getid`
   - Il bot risponderà con il tuo **chat ID**. Salvalo, ti servirà per autorizzare il tuo account

### 5. Preparazione dei file sul dispositivo

1. **Verifica il file `secrets_keys.py`**:
   - Nel repository è fornito un file `secrets_keys.py` con informazioni generiche
   - Apri questo file con OpenMV IDE e modifica le informazioni con i tuoi dati personali:

   ```python
   # WiFi credentials
   WIFI_SSID = "Il_Tuo_SSID_WiFi"
   WIFI_PASS = "La_Tua_Password_WiFi"

   # Arduino IoT Cloud credentials
   DEVICE_ID = "il_tuo_device_id"  # Device ID fornito da Arduino IoT Cloud
   SECRET_KEY = "il_tuo_secret_key"  # Secret Key fornito da Arduino IoT Cloud

   # Telegram bot credentials
   TELEGRAM_TOKEN = "il_tuo_token_bot"  # Token fornito da BotFather
   TELEGRAM_AUTHORIZED_USERS = ["il_tuo_chat_id"]  # Lista di chat ID autorizzati
   # Puoi usare ["*"] per permettere a chiunque di usare il bot
   ```

2. **Installa la libreria Arduino IoT Cloud per MicroPython**:
   - Scarica la libreria Arduino IoT Cloud per MicroPython dal repository ufficiale: [https://github.com/arduino/arduino-iot-cloud-py](https://github.com/arduino/arduino-iot-cloud-py)
   - Collega il tuo Arduino Nicla Vision al computer
   - Apri OpenMV IDE
   - Usa lo strumento di gestione dei file di OpenMV per creare una cartella `lib` nel dispositivo (se non esiste già)
   - Copia tutti i file della libreria scaricata nella cartella `lib` del dispositivo

3. **Carica tutti i file Python sul dispositivo**:
   - Collega il tuo Arduino Nicla Vision al computer
   - Apri OpenMV IDE
   - Carica tutti i file forniti nel repository sul dispositivo tramite lo strumento di gestione dei file di OpenMV:
     - `main.py`
     - `config.py`
     - `camera_detector.py`
     - `audio_detector.py`
     - `distance_detector.py`
     - `video_manager.py`
     - `photo_manager.py`
     - `file_manager.py`
     - `cloud_manager.py`
     - `telegram.py`
     - `secrets_keys.py` (modificato con i tuoi dati)
   - Assicurati che tutti i file siano caricati nella directory principale del dispositivo

### 6. Avvio del sistema

1. **Riavvia il dispositivo**:
   - Premi il pulsante di reset su Arduino Nicla Vision o scollega e ricollega il dispositivo

2. **Verifica la connessione**:
   - Il sistema dovrebbe avviarsi automaticamente
   - I LED integrati forniranno feedback visivo sullo stato del sistema:
     - LED blu lampeggiante: sistema attivo
     - LED verde: operazione completata con successo
     - LED rosso: errore o allarme

3. **Test con Telegram**:
   - Avvia una chat con il tuo bot su Telegram
   - Invia il comando `/start`
   - Il bot dovrebbe rispondere con un messaggio di benvenuto
   - Invia il comando `/status` per verificare lo stato del sistema

## Esempi di utilizzo

### Controllo del sistema tramite Telegram

Il bot Telegram supporta i seguenti comandi:

#### Generici

- `/start` - Avvia il bot e mostra il messaggio di benvenuto
- `/status` - Mostra lo stato del sistema
- `/enable` - Abilita il monitoraggio globale
- `/disable` - Disabilita il monitoraggio globale
- `/camera_on` - Abilita il monitoraggio tramite camera
- `/camera_off` - Disabilita il monitoraggio tramite camera
- `/audio_on` - Abilita il monitoraggio tramite microfono
- `/audio_off` - Disabilita il monitoraggio tramite microfono
- `/distance_on` - Abilita il monitoraggio tramite sensore di distanza
- `/distance_off` - Disabilita il monitoraggio tramite sensore di distanza
- `/photo` - Scatta una foto istantanea
- `/photos_on` - Abilita l'invio automatico di foto
- `/photos_off` - Disabilita l'invio automatico di foto
- `/video` - Registra un video istantaneo
- `/videos_on` - Abilita la registrazione automatica di video
- `/videos_off` - Disabilita la registrazione automatica di video

#### Impostazioni soglie
- `/set_motion_threshold X` - Imposta soglia movimento (0.5-50)
- `/set_audio_threshold X` - Imposta soglia audio (500-20000)
- `/set_distance_threshold X` - Imposta soglia distanza (10-2000)

#### Impostazioni video
- `/set_video_duration X` - Imposta durata video in secondi (3-30)
- `/set_video_fps X` - Imposta frame per secondo (5-30)
- `/set_video_quality X` - Imposta qualità video (10-100)

#### Impostazioni foto
- `/set_photo_quality X` - Imposta qualità foto (10-100)
- `/set_telegram_photo_quality X` - Imposta qualità foto Telegram (10-100)

#### Altre impostazioni
- `/set_inhibit_period X` - Imposta periodo di inibizione in secondi (1-30)
- `/set_audio_gain X` - Imposta guadagno audio in dB (0-48)
- `/set_distance_recalibration X` - Imposta intervallo ricalibrazione distanza (60-3600)

#### Impostazioni archiviazione
- `/set_max_images X` - Imposta numero massimo immagini (5-100)
- `/set_max_videos X` - Imposta numero massimo video (2-20)
- `/set_max_telegram_photos X` - Imposta numero massimo foto Telegram (2-20)

#### Altre informazioni
- `/show_settings` - Mostra tutte le impostazioni attuali

### Configurazione tramite Arduino IoT Cloud

Puoi utilizzare il dashboard creato su Arduino IoT Cloud per:

1. **Attivare/disattivare le funzionalità di monitoraggio**:
   - Usa gli switch per attivare/disattivare il sistema globalmente o singole modalità

2. **Regolare i parametri di rilevamento**:
   - Modifica le soglie di rilevamento movimento, audio e distanza
   - Configura la durata dei video e la frequenza dei fotogrammi

3. **Monitorare lo stato del sistema**:
   - Visualizza lo stato attuale
   - Controlla l'ultimo evento rilevato
   - Leggi i messaggi di log

### Scenari di utilizzo

1. **Monitoraggio di una stanza**:
   - Posiziona Arduino Nicla Vision in un punto strategico
   - Attiva il monitoraggio tramite camera e audio
   - Ricevi notifiche, foto e video quando viene rilevato movimento o suono

2. **Monitoraggio di un oggetto di valore**:
   - Posiziona Arduino Nicla Vision di fronte all'oggetto
   - Attiva il monitoraggio tramite sensore di distanza
   - Ricevi notifiche quando qualcuno si avvicina all'oggetto

3. **Baby monitor avanzato**:
   - Posiziona Arduino Nicla Vision nella stanza del bambino
   - Attiva il monitoraggio audio con una soglia appropriata
   - Ricevi notifiche e immagini quando il bambino piange

## Possibili implementazioni

Ecco alcune idee per estendere e migliorare ulteriormente il progetto:

1. **Riconoscimento facciale**:
   - Implementare algoritmi di riconoscimento facciale per distinguere tra persone autorizzate e intrusi

2. **Riconoscimento oggetti**:
   - Utilizzare modelli di machine learning per identificare oggetti specifici nel campo visivo

3. **Analisi audio avanzata**:
   - Implementare il riconoscimento di suoni specifici (vetri rotti, allarmi, etc.)

4. **Integrazione con sistemi di domotica**:
   - Collegare il sistema a piattaforme come Home Assistant o Google Home

5. **Archiviazione cloud**:
   - Salvare foto e video su servizi di storage cloud come Google Drive o Dropbox

6. **Interfaccia web dedicata**:
   - Sviluppare un'interfaccia web dedicata per la gestione del sistema

7. **Supporto multi-camera**:
   - Espandere il sistema per supportare più dispositivi Nicla Vision in rete

8. **Analisi dei dati**:
   - Implementare funzionalità per analizzare i dati raccolti e generare statistiche

9. **Modalità a basso consumo**:
   - Ottimizzare il consumo energetico per un utilizzo a batteria più prolungato

10. **Autenticazione a due fattori**:
    - Implementare un sistema di autenticazione più sicuro per il controllo remoto

---

## Risoluzione dei problemi comuni

### Il dispositivo non si connette al WiFi

- Verifica che le credenziali WiFi in `secrets_keys.py` siano corrette
- Assicurati che la rete WiFi sia disponibile e stabile
- Riavvia il dispositivo

### Il dispositivo non si connette ad Arduino IoT Cloud

- Verifica che Device ID e Secret Key in `secrets_keys.py` siano corretti
- Controlla che la connessione WiFi funzioni correttamente
- Verifica che la Thing su Arduino IoT Cloud sia configurata correttamente

### Il bot Telegram non risponde

- Verifica che il token del bot in `secrets_keys.py` sia corretto
- Assicurati che il tuo chat ID sia incluso nella lista degli utenti autorizzati
- Controlla che la connessione WiFi funzioni correttamente

### Il rilevamento non funziona correttamente

- Regola le soglie di rilevamento tramite Arduino IoT Cloud o i comandi Telegram
- Assicurati che il dispositivo sia posizionato correttamente
- Verifica che la modalità di monitoraggio desiderata sia attivata

### La registrazione video fallisce

- Controlla lo spazio disponibile sulla memoria del dispositivo
- Diminuisci la durata o la qualità dei video
- Riavvia il dispositivo per liberare memoria

---

Per qualsiasi problema o domanda, puoi creare un issue nel repository GitHub del progetto o contattare Emilio (@destone28) <emilio.destratis@gmail.com>.
