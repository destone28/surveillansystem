# Wrapper per json
try:
    from json import loads, dumps
except ImportError:
    # Fallback
    import json
    loads = json.loads
    dumps = json.dumps
