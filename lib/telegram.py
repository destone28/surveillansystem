# Copyright (C) 2024 Salvatore Sanfilippo <antirez@gmail.com>
# All Rights Reserved
#
# This code is released under the BSD 2 clause license.
# See the LICENSE file for more information

import network, socket, ssl, time, uasyncio as asyncio, json, os, gc

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
        self.watchdog_timeout_ms = 60000 # 60 seconds max idle time.
        self.max_image_size = 50000  # Limita la dimensione dell'immagine (circa 50KB)

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
                if self.debug: print("[telegram] Reconnecting socket.")
                # Reconnection (or first connection)
                try:
                    addr = socket.getaddrinfo("api.telegram.org", 443, socket.AF_INET)
                    addr = addr[0][-1]
                    self.socket = socket.socket(socket.AF_INET)
                    self.socket.connect(addr)
                    self.socket.setblocking(False)
                    self.ssl = ssl.wrap_socket(self.socket)
                    self.reconnect = False
                    self.pending = False
                except Exception as e:
                    print(f"[telegram] Reconnection error: {e}")
                    self.reconnect = True
                    await asyncio.sleep(5)  # Wait before retrying

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
                self.reconnect = True
                print("[telegram] *** SOCKET WATCHDOG EXPIRED ***")

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
            oldest = self.outgoing.pop(0)  # Use FIFO order for messages
            request = self.build_post_request("sendMessage", oldest)

        # Issue a new getUpdates request if there is not
        # some request still pending.
        else:
            # Limit the fetch to a single message since we are using
            # a fixed 4k buffer. Very large incoming messages will break
            # the reading loop: that's a trade off.
            request = "GET /bot"+self.token+"/getUpdates?offset="+str(self.offset)+"&timeout=0&allowed_udpates=message&limit=1 HTTP/1.1\r\nHost:api.telegram.org\r\n\r\n"

        # Write the request to the SSL socket.
        if request != None:
            if self.debug: print("[telegram] Writing payload:", request[:100] + "..." if len(request) > 100 else request)
            try:
                if isinstance(request, str):
                    self.ssl.write(request)
                else:
                    # If it's bytes, write directly
                    self.ssl.write(request)
                self.pending = True
                self.pending_since = time.ticks_ms()
            except Exception as e:
                print(f"[telegram] Error writing request: {e}")
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
            nbytes = self.ssl.readinto(self.rbuf_mv[self.rbuf_used:], len(self.rbuf)-self.rbuf_used)
            if self.debug: print("bytes from SSL socket:", nbytes)
        except Exception as e:
            print(f"[telegram] Socket read error: {e}")
            self.reconnect = True
            return

        if nbytes != None:
            if nbytes == 0:
                self.reconnect = True
                return
            else:
                self.rbuf_used += nbytes
                if self.debug and self.rbuf_used < 100:
                    print(self.rbuf[:self.rbuf_used])

        # Check if we got a well-formed JSON message.
        self.process_api_response()

    # Check if there is a well-formed JSON reply in the reply buffer:
    # if so, parses it, marks the current request as no longer "pending"
    # and resets the buffer. If the JSON reply is an incoming message, the
    # user callback is invoked.
    def process_api_response(self):
        if self.rbuf_used > 0:
            if self.debug: print(f"[telegram] Processing response buffer ({self.rbuf_used} bytes)")
            # Discard the HTTP request header by looking for the
            # start of the json message.
            start_idx = self.rbuf.find(b"{")
            if start_idx != -1:
                # It is possible that we read a non complete reply
                # from the socket. In such case the JSON message
                # will be broken and will produce a ValueError.
                try:
                    mybuf = self.decode_surrogate_pairs(self.rbuf[start_idx:self.rbuf_used])
                    res = json.loads(mybuf)
                    if res != False:
                        if self.debug: print(f"[telegram] Valid JSON response: {res}")
                except ValueError:
                    res = False
                if res != False:
                    self.pending = False
                    if 'result' not in res:
                        # Probably an error response from a sendPhoto or sendMessage request
                        if self.debug: print(f"[telegram] Error response: {res}")
                    elif len(res['result']) == 0:
                        # Empty result set. Try again.
                        if self.debug: print("No more messages.")
                    elif not isinstance(res['result'], list):
                        # This is the reply to SendMessage or other
                        # non getUpdates related API calls? Discard it.
                        if self.debug: print("Got reply from sendMessage/sendPhoto")
                    else:
                        # Update the last message ID we get so we
                        # will get only next ones.
                        offset = res['result'][0]['update_id']
                        offset += 1
                        self.offset = offset
                        if self.debug: print("New offset:", offset)

                        # Process the received message.
                        entry = res['result'][0]
                        if "message" in entry:
                            msg = entry['message']
                        elif "channel_post" in entry:
                            msg = entry['channel_post']

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
                    self.rbuf_used = 0

    # MicroPython seems to lack the urlencode module. We need very
    # little to kinda make it work.
    def quote(self, string):
        return ''.join(['%{:02X}'.format(c) if c < 33 or c > 126 or c in (37, 38, 43, 58, 61) else chr(c) for c in str(string).encode('utf-8')])

    # Turn the GET/POST parameters in the 'fields' hash into a string
    # in url encoded form a=1&b=2&... quoting just the value (the key
    # of the hash is assumed to be already url encoded or just a plain
    # string without special chars).
    def urlencode(self, fields):
        return "&".join([str(key)+"="+self.quote(value) for key, value in fields.items()])

    # Create a POST request with url-encoded parameters in the body.
    # Parameters are passed as a hash in 'fields'.
    def build_post_request(self, cmd, fields):
        params = self.urlencode(fields)
        headers = f"POST /bot{self.token}/{cmd} HTTP/1.1\r\nHost:api.telegram.org\r\nContent-Type:application/x-www-form-urlencoded\r\nContent-Length:{len(params)}\r\n\r\n"
        return headers+params

    # MicroPython JSON library does not handle surrogate UTF-16 pairs
    # generated by the Telegram API. We need to do it manually by scanning
    # the input bytearray and converting the surrogates to UTF-8.
    def decode_surrogate_pairs(self, ba):
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
    def send(self, chat_id, text, glue=False):
        if glue and len(self.outgoing) > 0 and \
           len(self.outgoing[0]["text"])+len(text)+1 < 2048:
            self.outgoing[0]["text"] += "\n"
            self.outgoing[0]["text"] += text
            return
        self.outgoing.append({"chat_id": chat_id, "text": text})

    # Implementazione completamente semplificata per inviare una foto
    # Questa versione è basata sull'esempio esatto del PDF
    def send_photo(self, chat_id, photo_path, caption=None):
        try:
            # Check if file exists and get its size
            try:
                stats = os.stat(photo_path)
                file_size = stats[6]  # Size in bytes

                if file_size > self.max_image_size:
                    # File is too large
                    self.send(chat_id, f"📷 Foto scattata! Dimensione {file_size/1024:.1f}KB (troppo grande per l'invio diretto)")
                    return False
            except OSError:
                self.send(chat_id, f"⚠️ Errore: impossibile trovare il file '{photo_path}'")
                return False

            # Forza il garbage collection prima di iniziare
            gc.collect()

            print(f"[telegram] Sending photo {photo_path} ({file_size} bytes) to {chat_id}")

            # Leggiamo la foto in memoria
            try:
                with open(photo_path, 'rb') as f:
                    photo_data = f.read()
            except Exception as e:
                print(f"[telegram] Error reading photo file: {e}")
                self.send(chat_id, f"⚠️ Errore lettura file: {e}")
                return False

            # Inviamo la foto usando la normale richiesta POST con URL param "chat_id"
            # e il campo "document" contenente il file - approccio semplificato come da PDF
            try:
                # Creiamo una nuova connessione dedicata
                addr = socket.getaddrinfo("api.telegram.org", 443, socket.AF_INET)
                addr = addr[0][-1]
                sock = socket.socket(socket.AF_INET)
                sock.connect(addr)
                sock.setblocking(True)  # Modalità bloccante
                ssl_sock = ssl.wrap_socket(sock)

                # Semplice boundary statico
                boundary = "----WebKitFormBoundaryNiclaVision"

                # Contenuto del form
                form_data = bytearray()

                # Campo chat_id
                form_data.extend(f"--{boundary}\r\n".encode())
                form_data.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())

                # Campo caption se presente
                if caption:
                    form_data.extend(f"--{boundary}\r\n".encode())
                    form_data.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())

                # Campo "document" con il file
                form_data.extend(f"--{boundary}\r\n".encode())
                form_data.extend(f'Content-Disposition: form-data; name="document"; filename="photo.jpg"\r\n'.encode())
                form_data.extend(f'Content-Type: image/jpeg\r\n\r\n'.encode())

                # Aggiungi il contenuto del file
                end_boundary = f"\r\n--{boundary}--\r\n".encode()

                # Calcola la lunghezza totale
                total_length = len(form_data) + len(photo_data) + len(end_boundary)

                # Creiamo l'header HTTP
                header = f"POST /bot{self.token}/sendDocument HTTP/1.1\r\n"
                header += "Host: api.telegram.org\r\n"
                header += f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
                header += f"Content-Length: {total_length}\r\n"
                header += "Connection: close\r\n\r\n"

                # Invia l'header
                ssl_sock.write(header.encode())

                # Invia la prima parte del form
                ssl_sock.write(form_data)

                # Invia il contenuto del file
                ssl_sock.write(photo_data)

                # Invia la parte finale
                ssl_sock.write(end_boundary)

                # Leggi la risposta
                response = bytearray(1024)
                bytes_read = ssl_sock.readinto(response)
                response_text = response[:bytes_read].decode('utf-8', 'ignore')

                # Chiudi il socket
                ssl_sock.close()
                sock.close()

                # Controlla se la risposta è positiva
                if "HTTP/1.1 200" in response_text:
                    print("[telegram] Photo sent successfully!")
                    return True
                else:
                    # Cerca più informazioni sull'errore nella risposta
                    error_info = response_text.split("\r\n\r\n")[-1] if "\r\n\r\n" in response_text else response_text
                    print(f"[telegram] Error response: {error_info[:200]}")
                    self.send(chat_id, f"⚠️ Errore invio foto. Riprova più tardi.")
                    return False

            except Exception as e:
                print(f"[telegram] Error in send_photo transaction: {e}")
                self.send(chat_id, f"⚠️ Errore invio: {e}")
                return False

        except Exception as e:
            print(f"[telegram] Error in send_photo: {e}")
            self.send(chat_id, f"⚠️ Errore generico: {e}")
            return False

    def send_video(self, chat_id, video_path, caption=None):
        """
        Invia un video tramite Telegram usando un approccio a blocchi per risparmiare memoria

        Args:
            chat_id: ID della chat
            video_path: Percorso del file video
            caption: Descrizione opzionale

        Returns:
            bool: True se il video è stato inviato, False altrimenti
        """
        try:
            # Verifica se il file esiste e ottieni la sua dimensione
            try:
                stats = os.stat(video_path)
                file_size = stats[6]  # Dimensione in byte

                # Utilizziamo un valore hardcoded
                max_video_size = 10000000  # 10MB (soglia ragionevole per Telegram)

                if file_size > max_video_size:
                    # File troppo grande
                    self.send(chat_id, f"🎥 Video registrato! Dimensione {file_size/1024/1024:.1f}MB (troppo grande per l'invio diretto)")
                    return False
            except OSError:
                self.send(chat_id, f"⚠️ Errore: impossibile trovare il file '{video_path}'")
                return False

            # Forza il garbage collection prima di iniziare
            gc.collect()

            print(f"[telegram] Sending video {video_path} ({file_size} bytes) to {chat_id}")

            # Invia il video usando la normale richiesta POST con URL param "chat_id"
            # e il campo "document" contenente il file
            try:
                # Crea una nuova connessione dedicata
                addr = socket.getaddrinfo("api.telegram.org", 443, socket.AF_INET)
                addr = addr[0][-1]
                sock = socket.socket(socket.AF_INET)
                sock.connect(addr)
                sock.setblocking(True)  # Modalità bloccante
                ssl_sock = ssl.wrap_socket(sock)

                # Semplice boundary statico
                boundary = "----WebKitFormBoundaryNiclaVision"

                # Contenuto del form
                form_data = bytearray()

                # Campo chat_id
                form_data.extend(f"--{boundary}\r\n".encode())
                form_data.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())

                # Campo caption se presente
                if caption:
                    form_data.extend(f"--{boundary}\r\n".encode())
                    form_data.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())

                # Campo "document" con il file
                form_data.extend(f"--{boundary}\r\n".encode())
                form_data.extend(f'Content-Disposition: form-data; name="document"; filename="video.mjpeg"\r\n'.encode())
                form_data.extend(f'Content-Type: video/mjpeg\r\n\r\n'.encode())

                # Fine del form (da aggiungere dopo il contenuto del file)
                end_boundary = f"\r\n--{boundary}--\r\n".encode()

                # Calcola la lunghezza totale
                total_length = len(form_data) + file_size + len(end_boundary)

                # Crea l'header HTTP
                header = f"POST /bot{self.token}/sendDocument HTTP/1.1\r\n"
                header += "Host: api.telegram.org\r\n"
                header += f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
                header += f"Content-Length: {total_length}\r\n"
                header += "Connection: close\r\n\r\n"

                # Invia l'header
                ssl_sock.write(header.encode())

                # Invia la prima parte del form
                ssl_sock.write(form_data)

                # Leggi e invia il file a blocchi per risparmiare memoria
                chunk_size = 4096  # dimensione del blocco (4KB)
                sent_bytes = 0

                try:
                    with open(video_path, 'rb') as f:
                        while True:
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            ssl_sock.write(chunk)
                            sent_bytes += len(chunk)
                            # Feedback su stdout ogni 20KB
                            if sent_bytes % 20480 == 0:
                                print(f"[telegram] Inviati {sent_bytes/1024:.1f}KB/{file_size/1024:.1f}KB")
                            # Libera memoria
                            del chunk
                            gc.collect()
                except Exception as e:
                    print(f"[telegram] Error durante l'invio dei dati video: {e}")
                    ssl_sock.close()
                    sock.close()
                    self.send(chat_id, f"⚠️ Errore durante l'invio del video: {e}")
                    return False

                # Invia la parte finale
                ssl_sock.write(end_boundary)

                # Leggi la risposta
                response = bytearray(1024)
                bytes_read = ssl_sock.readinto(response)
                response_text = response[:bytes_read].decode('utf-8', 'ignore')

                # Chiudi il socket
                ssl_sock.close()
                sock.close()

                # Controlla se la risposta è positiva
                if "HTTP/1.1 200" in response_text:
                    print("[telegram] Video sent successfully!")
                    return True
                else:
                    # Cerca più informazioni sull'errore nella risposta
                    error_info = response_text.split("\r\n\r\n")[-1] if "\r\n\r\n" in response_text else response_text
                    print(f"[telegram] Error response: {error_info[:200]}")
                    self.send(chat_id, f"⚠️ Errore invio video. Riprova più tardi.")
                    return False

            except Exception as e:
                print(f"[telegram] Error in send_video transaction: {e}")
                self.send(chat_id, f"⚠️ Errore invio video: {e}")
                return False

        except Exception as e:
            print(f"[telegram] Error in send_video: {e}")
            self.send(chat_id, f"⚠️ Errore generico invio video: {e}")
            return False

    # This is just a utility method that can be used in order to wait
    # for the WiFi network to be connected.
    def connect_wifi(self, ssid, password, timeout=30):
        self.sta_if = network.WLAN(network.STA_IF)
        self.sta_if.active(True)
        self.sta_if.connect(ssid, password)
        seconds = 0
        while not self.sta_if.isconnected():
            time.sleep(1)
            seconds += 1
            if seconds == timeout:
                raise Exception("Timedout connecting to WiFi network")
            pass
        print("[WiFi] Connected")
