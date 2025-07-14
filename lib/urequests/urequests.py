import usocket
import ussl

class Response:
    def __init__(self, f, status_code, headers):
        self.raw = f
        self.status_code = status_code
        self.headers = headers
        self.content = b''
        
    def close(self):
        if self.raw:
            self.raw.close()
            self.raw = None
        
    def read(self, size=-1):
        if self.raw:
            return self.raw.read(size)
        else:
            return b''
            
    @property
    def text(self):
        if not self.content:
            try:
                self.content = self.raw.read()
            finally:
                self.close()
        return self.content.decode('utf-8')
        
    def json(self):
        import ujson
        return ujson.loads(self.text)

def request(method, url, json=None, data=None, headers=None, timeout=None):
    # Analisi dell'URL
    proto, _, host, path = url.split('/', 3)
    proto = proto[:-1]  # Rimuovi i due punti
    
    # Gestione porta
    if ':' in host:
        host, port = host.split(':')
        port = int(port)
    else:
        if proto == 'http':
            port = 80
        else:
            port = 443
    
    # Imposta header predefiniti
    if headers is None:
        headers = {}
    
    # Prepara i dati
    if json is not None:
        assert data is None, "Impossibile specificare sia json che data"
        import ujson
        data = ujson.dumps(json).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif data and isinstance(data, dict):
        import urlencode
        data = urlencode.urlencode(data).encode('utf-8')
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    
    if data:
        headers['Content-Length'] = str(len(data))
    
    # Crea la connessione socket
    s = usocket.socket()
    if timeout:
        s.settimeout(timeout)
    
    try:
        s.connect((host, port))
        
        # Wrappa con SSL se HTTPS - VERSIONE SEMPLIFICATA senza server_hostname
        if proto == 'https':
            try:
                # Prima prova con il parametro server_hostname
                s = ussl.wrap_socket(s, server_hostname=host)
            except TypeError:
                # Se fallisce, prova senza server_hostname
                try:
                    s = ussl.wrap_socket(s)
                except Exception as e:
                    raise Exception(f"Errore SSL: {e}")
        
        # Costruisci la richiesta
        s.write(f"{method} /{path} HTTP/1.1\r\n".encode())
        s.write(f"Host: {host}\r\n".encode())
        
        # Aggiungi headers
        for k, v in headers.items():
            s.write(f"{k}: {v}\r\n".encode())
        
        # Termina intestazione
        s.write(b"\r\n")
        
        # Invia il corpo se presente
        if data:
            s.write(data)
        
        # Leggi la risposta
        line = s.readline()
        status = int(line.split(b' ')[1])
        
        # Leggi headers
        headers = {}
        line = s.readline()
        while line and line != b'\r\n':
            key, value = line.decode().strip().split(':', 1)
            headers[key.lower()] = value.strip()
            line = s.readline()
        
        return Response(s, status, headers)
    
    except OSError as e:
        s.close()
        raise e

def head(url, **kw):
    return request("HEAD", url, **kw)

def get(url, **kw):
    return request("GET", url, **kw)

def post(url, **kw):
    return request("POST", url, **kw)

def put(url, **kw):
    return request("PUT", url, **kw)

def patch(url, **kw):
    return request("PATCH", url, **kw)

def delete(url, **kw):
    return request("DELETE", url, **kw)