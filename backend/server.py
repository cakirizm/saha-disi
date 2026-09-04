from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
ROOT=Path(__file__).parent
os.chdir(ROOT)
print('Saha Dışı feed: http://127.0.0.1:8787/feed.json')
ThreadingHTTPServer(('0.0.0.0',8787),SimpleHTTPRequestHandler).serve_forever()
