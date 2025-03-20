# Copyright (C) 2024 Salvatore Sanfilippo <antirez@gmail.com>
# All Rights Reserved
#
# This code is released under the BSD 2 clause license.
# See the LICENSE file for more information

import network, socket, ssl, time, uasyncio as asyncio, json

class TelegramBot:
    def __init__(self,token,callback):
        self.token = token
        self.callback = callback
        self.rbuf = bytearray(4096)
        self.rbuf_mv = memoryview(self.rbuf)
        self.rbuf_used = 0
        self.active = True # So we can stop the task with .stop()
        self.debug = False
        self.missed_write = None # Failed write payload. This is useful
                                 # in order to retransfer after reconnection.

        # Array of outgoing messages. Each entry is a hash with
        # chat_id and text fields.
        self.outgoing = []
        self.pending = False # Pending HTTP request, waiting for reply.
        self.reconnect = True # We need to reconnect the socket, either for
                              # the first time or after errors.
        self.offset = 0     # Next message ID offset.
        self.watchdog_timeout_ms = 120000 # 120 seconds max idle time (aumentato da 60s)
        self.reconnect_attempts = 0 # Contatore per tentativi di riconnessione
        
        # Dizionario per tenere traccia delle tastiere inviate
        self.last_keyboard_message_id = {}  # chat_id -> message_id

    # Stop the task handling the bot. This should be called before
    # destroying the object, in order to also terminate the task.
    def stop(self):
        self.active = False

    # Main telegram bot loop.
    # Sould be executed asynchronously, like with:
    # asyncio.create_task(bot.run())
    async def run(self):
        print("[telegram] Bot task started")
        while self.active:
            if self.reconnect:
                self.reconnect_attempts += 1
                if self.debug: print(f"[telegram] Tentativo di riconnessione #{self.reconnect_attempts}")
                
                # Reset degli stati interni
                self.rbuf_used = 0
                self.pending = False
                
                try:
                    # Chiudi eventuali socket precedenti
                    try:
                        if hasattr(self, 'socket'):
                            self.socket.close()
                    except:
                        pass
                    
                    # Reconnection (or first connection)
                    addr = socket.getaddrinfo("api.telegram.org", 443, socket.AF_INET)
                    addr = addr[0][-1]
                    self.socket = socket.socket(socket.AF_INET)
                    self.socket.connect(addr)
                    self.socket.setblocking(False)
                    self.ssl = ssl.wrap_socket(self.socket)
                    self.reconnect = False
                    self.pending = False
                    self.reconnect_attempts = 0  # Reset dopo connessione riuscita
                    print("[telegram] Riconnessione completata con successo")
                except Exception as e:
                    print(f"[telegram] Errore durante riconnessione: {e}")
                    self.reconnect = True
                    
                    # Attendi più a lungo dopo ogni tentativo fallito (max 10 secondi)
                    delay = min(self.reconnect_attempts * 0.5, 10)
                    await asyncio.sleep(delay)
                    continue

            # Aggiungi qui per debugging
            if self.debug and not self.pending:
                print("[telegram] Checking for updates...")
                
            self.send_api_requests()
            self.read_api_response()

            # Aggiungi qui per debugging
            if self.debug and self.pending:
                print(f"[telegram] Waiting for response, pending since {time.ticks_diff(time.ticks_ms(),self.pending_since)}ms")

            # Watchdog: if the connection is idle for a too long
            # time, force a reconnection.
            if self.pending and time.ticks_diff(time.ticks_ms(),self.pending_since) > self.watchdog_timeout_ms:
                print("[telegram] *** SOCKET WATCHDOG EXPIRED ***")
                self.reconnect = True
                self.pending = False  # Reset dello stato pending

            # If there are outgoing messages pending, wait less
            # to do I/O again.
            sleep_time = 0.1 if len(self.outgoing) > 0 else 1.0
            await asyncio.sleep(sleep_time)

    # Send HTTP requests to the server. If there are no special requests
    # to handle (like sendMessage) we just ask for updates with getUpdates.
    def send_api_requests(self):
        if self.pending: return # Request already in progress.
        request = None

        # Re-issue a pending write that failed for OS error
        # after a reconnection.
        if self.missed_write != None:
            request = self.missed_write
            self.missed_write = None

        # Issue sendMessage requests if we have pending
        # messages to deliver.
        elif len(self.outgoing) > 0:
            oldest = self.outgoing.pop()
            request = self.build_post_request("sendMessage",oldest)

        # Issue a new getUpdates request if there is not
        # some request still pending.
        else:
            # Limit the fetch to a single message since we are using
            # a fixed 4k buffer. Very large incoming messages will break
            # the reading loop: that's a trade off.
            request = "GET /bot"+self.token+"/getUpdates?offset="+str(self.offset)+"&timeout=0&allowed_udpates=message&limit=1 HTTP/1.1\r\nHost:api.telegram.org\r\n\r\n"

        # Write the request to the SSL socket.
        #
        # Here we assume that the output buffer has enough
        # space available, since this is sent either at startup
        # or when we already received a reply. In both the
        # situations the socket buffer should be empty and
        # this request should work without sending just part
        # of the request.
        if request != None:
            if self.debug: print("[telegram] Writing payload:",request)
            try:
                self.ssl.write(request)
                self.pending = True
                self.pending_since = time.ticks_ms()
            except Exception as e:
                print(f"[telegram] Errore scrittura socket: {e}")
                self.reconnect = True
                self.missed_write = request

    # Try to read the reply from the Telegram server. Process it
    # and if needed ivoke the callback registered by the user for
    # incoming messages.
    def read_api_response(self):
        try:
            # Don't use await to read from the SSL socket (it's not
            # supported). We put the socket in non blocking mode
            # anyway. It will return None if there is no data to read.
            nbytes = self.ssl.readinto(self.rbuf_mv[self.rbuf_used:],len(self.rbuf)-self.rbuf_used)
            if self.debug: print("bytes from SSL socket:",nbytes)
        except OSError as e:
            print(f"[telegram] OSError nella lettura socket: {e}")
            self.reconnect = True
            self.rbuf_used = 0  # Reset del buffer
            return
        except Exception as e:
            print(f"[telegram] Errore nella lettura socket: {e}")
            self.reconnect = True
            self.rbuf_used = 0
            return

        if nbytes != None:
            if nbytes == 0:
                print("[telegram] Socket chiuso dal server, riconnessione necessaria")
                self.reconnect = True
                self.rbuf_used = 0
                return
            else:
                self.rbuf_used += nbytes
                if self.debug: print(self.rbuf[:self.rbuf_used])

        # Check if we got a well-formed JSON message.
        self.process_api_response()

    # Funzione helper per trovare un JSON completo
    def find_complete_json(self, buffer):
        depth = 0
        escaped = False
        in_string = False
        
        for i, c in enumerate(buffer):
            char = chr(c)
            
            if escaped:
                escaped = False
                continue
                
            if char == '\\' and in_string:
                escaped = True
                continue
                
            if char == '"' and not escaped:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # Abbiamo trovato un JSON completo
                        return buffer[:i+1]
        
        return None  # JSON incompleto
        
    # Metodo per processare un update
    def process_update(self, entry):
        if "callback_query" in entry:
            self.process_callback_query(entry)
        elif "message" in entry:
            # Controlla se è una risposta a un messaggio con tastiera e salva l'ID del messaggio
            message_id = entry.get('message', {}).get('message_id')
            if message_id and 'reply_markup' in str(entry):
                chat_id = entry.get('message', {}).get('chat', {}).get('id')
                if chat_id:
                    self.last_keyboard_message_id[chat_id] = message_id
            
            self.process_message(entry)
        elif "channel_post" in entry:
            self.process_message(entry, is_channel=True)
            
    def process_callback_query(self, entry):
        callback_query = entry['callback_query']
        callback_data = callback_query.get('data')
        callback_id = callback_query.get('id')
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_id = message.get('message_id')
        sender_name = callback_query.get('from', {}).get('username')
        
        # Risposta per evitare l'attesa su Telegram
        try:
            self.answer_callback_query(callback_id)
        except:
            pass
        
        # Invia al callback
        if callback_data and chat_id:
            # Salva sempre il messaggio con tastiera più recente
            if message_id:
                self.last_keyboard_message_id[chat_id] = message_id
                
            self.callback(self, "callback_query", None, sender_name, 
                        chat_id, callback_data, entry)
            if self.debug: print(f"[telegram] Chiamata callback con callback_data: {callback_data}")
            
    def process_message(self, entry, is_channel=False):
        msg = entry['message'] if not is_channel else entry['channel_post']
        
        # Fill the fields depending on the message
        msg_type = None
        chat_name = None
        sender_name = None
        chat_id = None
        text = None

        try: msg_type = msg['chat']['type']
        except: pass
        try: chat_name = msg['chat']['title']
        except: pass
        try: sender_name = msg['from']['username']
        except: pass
        try: chat_id = msg['chat']['id']
        except: pass
        try: text = msg['text']
        except: pass

        # We don't care about join messages and other stuff.
        # We report just messages with some text content.
        if text != None:
            self.callback(self, msg_type, chat_name, sender_name, chat_id, text, entry)
            if self.debug: print(f"[telegram] Calling callback with text: {text}")

    # Check if there is a well-formed JSON reply in the reply buffer:
    # if so, parses it, marks the current request as no longer "pending"
    # and resets the buffer. If the JSON reply is an incoming message, the
    # user callback is invoked.
    def process_api_response(self):
        if self.rbuf_used > 0:
            if self.debug: print(f"[telegram] Processing buffer ({self.rbuf_used} bytes)")
            
            # Esamina l'intero buffer per trovare tutte le risposte JSON
            buffer = self.rbuf[:self.rbuf_used]
            processed = 0
            
            # Troviamo tutte le occorrenze di inizio JSON
            json_start_indices = []
            
            # Trova tutte le occorrenze di inizio JSON (ogni risposta ha un JSON)
            i = 0
            while i < len(buffer):
                idx = buffer.find(b'{', i)
                if idx == -1:
                    break
                json_start_indices.append(idx)
                i = idx + 1
            
            if not json_start_indices:
                return  # Nessun JSON trovato
                
            # Processa ogni potenziale risposta JSON
            for start_idx in json_start_indices:
                try:
                    # Decodifica dal punto di inizio fino alla fine del buffer
                    sub_buffer = buffer[start_idx:self.rbuf_used]
                    # Cerca la fine del JSON contando le parentesi graffe
                    json_str = self.find_complete_json(sub_buffer)
                    
                    if not json_str:
                        continue  # JSON incompleto, prova il prossimo
                    
                    decoded = self.decode_surrogate_pairs(json_str)
                    res = json.loads(decoded)
                    
                    # Risposta JSON valida trovata
                    self.pending = False
                    processed = start_idx + len(json_str)
                    
                    # Ignora l'errore 400 per le callback query scadute
                    if not res.get('ok', True) and "query is too old" in res.get('description', ''):
                        print("[telegram] Ignorato errore callback scaduta")
                        continue
                    
                    # Controlla se è una risposta a sendMessage (per salvare message_id delle tastiere)
                    if res.get('ok', False) and 'result' in res and isinstance(res['result'], dict):
                        result = res['result']
                        if 'message_id' in result and 'reply_markup' in str(result):
                            chat_id = result.get('chat', {}).get('id')
                            if chat_id:
                                self.last_keyboard_message_id[chat_id] = result['message_id']
                                if self.debug: print(f"[telegram] Salvato message_id tastiera: {result['message_id']}")
                    
                    # Processa i messaggi normali e le callback query
                    if 'result' in res:
                        if isinstance(res['result'], list) and len(res['result']) > 0:
                            # Aggiorna offset per i prossimi update
                            offset = res['result'][0]['update_id']
                            offset += 1
                            self.offset = offset
                            if self.debug: print("[telegram] New offset:", offset)
                            
                            # Processa la risposta
                            self.process_update(res['result'][0])
                        else:
                            if self.debug: print("[telegram] Risposta senza update o vuota")
                    else:
                        if self.debug: print("[telegram] Risposta senza campo 'result'")
                
                except ValueError:  # Usa ValueError invece di JSONDecodeError per MicroPython
                    if self.debug: print(f"[telegram] JSON incompleto all'indice {start_idx}")
                    continue
                except Exception as e:
                    print(f"[telegram] Errore processing JSON: {e}")
                    continue
            
            # Sposta i dati non processati all'inizio del buffer
            if processed > 0:
                remaining = self.rbuf_used - processed
                if remaining > 0:
                    # Sposta i byte rimanenti all'inizio del buffer
                    for i in range(remaining):
                        self.rbuf[i] = self.rbuf[processed + i]
                    self.rbuf_used = remaining
                else:
                    # Nessun byte rimanente
                    self.rbuf_used = 0

    # MicroPython seems to lack the urlencode module. We need very
    # little to kinda make it work.
    def quote(self,string):
        return ''.join(['%{:02X}'.format(c) if c < 33 or c > 126 or c in (37, 38, 43, 58, 61) else chr(c) for c in str(string).encode('utf-8')])

    # Turn the GET/POST parameters in the 'fields' hash into a string
    # in url encoded form a=1&b=2&... quoting just the value (the key
    # of the hash is assumed to be already url encoded or just a plain
    # string without special chars).
    def urlencode(self,fields):
        return "&".join([str(key)+"="+self.quote(value) for key,value in fields.items()])

    # Create a POST request with url-encoded parameters in the body.
    # Parameters are passed as a hash in 'fields'.
    def build_post_request(self,cmd,fields):
        params = self.urlencode(fields)
        headers = f"POST /bot{self.token}/{cmd} HTTP/1.1\r\nHost:api.telegram.org\r\nContent-Type:application/x-www-form-urlencoded\r\nContent-Length:{len(params)}\r\n\r\n"
        return headers+params

    # MicroPython JSON library does not handle surrogate UTF-16 pairs
    # generated by the Telegram API. We need to do it manually by scanning
    # the input bytearray and converting the surrogates to UTF-8.
    def decode_surrogate_pairs(self,ba):
        result = bytearray()
        i = 0
        while i < len(ba):
            if ba[i:i+2] == b'\\u' and i + 12 <= len(ba):
                if ba[i+2:i+4] in [b'd8', b'd9', b'da', b'db'] and ba[i+6:i+8] == b'\\u' and ba[i+8:i+10] in [b'dc', b'dd', b'de', b'df']:
                    # We found a surrogate pairs. Convert.
                    high = int(ba[i+2:i+6].decode(), 16)
                    low = int(ba[i+8:i+12].decode(), 16)
                    code_point = 0x10000 + (high - 0xD800) * 0x400 + (low - 0xDC00)
                    result.extend(chr(code_point).encode('utf-8'))
                    i += 12
                else:
                    result.append(ba[i])
                    i += 1
            else:
                result.append(ba[i])
                i += 1
        return result

    # Send a message via Telegram, to the specified chat_id and containing
    # the specified text. This function will just queue the item. The
    # actual sending will be performed in the main boot loop.
    #
    # If 'glue' is True, the new text will be glued to the old pending
    # message up to 2k, in order to reduce the API back-and-forth.
    def send(self,chat_id,text,glue=False):
        if glue and len(self.outgoing) > 0 and \
           len(self.outgoing[0]["text"])+len(text)+1 < 2048:
            self.outgoing[0]["text"] += "\n"
            self.outgoing[0]["text"] += text
            return
        self.outgoing = [{"chat_id":chat_id, "text":text}]+self.outgoing

    # Invia un messaggio con tastiera inline
    def send_with_keyboard(self, chat_id, text, keyboard_markup):
        """
        Invia un messaggio con tastiera inline, rimuovendo automaticamente
        la tastiera precedente se esiste
        """
        # Prima rimuovi l'ultima tastiera se esiste
        if chat_id in self.last_keyboard_message_id:
            try:
                last_message_id = self.last_keyboard_message_id[chat_id]
                # Rimuovi la tastiera
                self.edit_message_reply_markup(chat_id, last_message_id)
            except Exception as e:
                print(f"[telegram] Errore rimozione tastiera precedente: {e}")
        
        # Poi invia il nuovo messaggio con tastiera
        fields = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(keyboard_markup)
        }
        request = self.build_post_request("sendMessage", fields)
        try:
            self.ssl.write(request)
            self.pending = True
            self.pending_since = time.ticks_ms()
        except Exception as e:
            print(f"[telegram] Errore invio messaggio: {e}")
            self.reconnect = True
            self.missed_write = request
        
    # Modifica o rimuove la tastiera di un messaggio esistente
    def edit_message_reply_markup(self, chat_id, message_id, keyboard_markup=None):
        """Modifica o rimuove la tastiera di un messaggio esistente"""
        if keyboard_markup is None:
            keyboard_markup = {}  # tastiera vuota = rimuove la tastiera
            
        fields = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": json.dumps(keyboard_markup)
        }
        request = self.build_post_request("editMessageReplyMarkup", fields)
        try:
            self.ssl.write(request)
            self.pending = True
            self.pending_since = time.ticks_ms()
        except Exception as e:
            print(f"[telegram] Errore modifica tastiera: {e}")
            self.reconnect = True
            self.missed_write = request
            
    # Risponde a una callback query
    def answer_callback_query(self, callback_query_id, text=None):
        fields = {"callback_query_id": callback_query_id}
        if text:
            fields["text"] = text
        request = self.build_post_request("answerCallbackQuery", fields)
        try:
            self.ssl.write(request)
            self.pending = True
            self.pending_since = time.ticks_ms()
        except:
            self.reconnect = True
            self.missed_write = request

    # This is just a utility method that can be used in order to wait
    # for the WiFi network to be connected.
    def connect_wifi(self,ssid,password,timeout=30):
        self.sta_if = network.WLAN(network.STA_IF)
        self.sta_if.active(True)
        self.sta_if.connect(ssid,password)
        seconds = 0
        while not self.sta_if.isconnected():
            time.sleep(1)
            seconds += 1
            if seconds == timeout:
                raise Exception("Timedout connecting to WiFi network")
            pass
        print("[WiFi] Connected")