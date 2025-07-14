def quote_plus(string):
    return quote(string, "+")

def quote(string, safe='/'):
    """Quote the query part of a URL."""
    table = {i: '%{:02X}'.format(i) for i in range(256)}
    
    # Don't quote already-quoted sequences.
    string = string.replace('%', '%25')
    
    # Don't quote these characters
    for c in safe:
        if c in table:
            table[ord(c)] = c
    
    # Don't quote characters in the ASCII range that don't need quoting
    for i in range(128):
        c = chr(i)
        if c.isalnum() or c in '-._~':
            table[i] = c
    
    result = ""
    for char in string:
        result += table[ord(char)]
    
    return result

def urlencode(query, doseq=False):
    """Encode a dictionary of key/value pairs into a query string."""
    if hasattr(query, "items"):
        query = query.items()
    
    result = []
    for k, v in query:
        if v is None:
            continue
        
        k = quote_plus(str(k))
        if isinstance(v, (list, tuple)) and doseq:
            for x in v:
                result.append(k + '=' + quote_plus(str(x)))
        else:
            result.append(k + '=' + quote_plus(str(v)))
    
    return '&'.join(result)
