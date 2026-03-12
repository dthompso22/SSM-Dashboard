#!/usr/bin/env python3
"""Local helper server for the RA Dashboard Refresh button.

Listens on localhost:7474.  Run this once before clicking Refresh Data:
    python ra_helper.py          (or double-click Start-RAHelper.ps1)

The static dashboard calls POST /refresh, which runs Update-RAData.ps1
and returns the annotated data.  The site then pushes it to GitLab.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, re, subprocess
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 7474

# ── Annotation logic (mirrors build.py) ──────────────────────────────────────
def get_category(t):
    if t == 'Licensing Change': return 'licensing'
    if t == 'Special Update':  return 'su'
    return 'other'

def parse_prd_date(title):
    m = re.search(r'for PRD (?:on|by)\s+(\d{1,2})-(\d{1,2})-(\d{2,4})', title, re.IGNORECASE)
    if not m: return None
    mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yr < 100: yr += 2000
    try: return date(yr, mo, dy).isoformat()
    except ValueError: return None

def annotate(raw):
    result = []
    for ra in raw:
        r = dict(ra)
        r['cat'] = get_category(r['type'])
        r['prd_from_title'] = parse_prd_date(r['title']) if r['type'] == 'Special Update' else None
        result.append(r)
    return result

# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # suppress request logs

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path != '/refresh':
            self.send_json(404, {'error': 'Not found'})
            return
        try:
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File',
                 os.path.join(BASE, 'Update-RAData.ps1')],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                self.send_json(500, {'error': result.stderr or result.stdout})
                return
            with open(os.path.join(BASE, 'ra_data.json'), encoding='utf-8') as f:
                raw = json.load(f)
            data = annotate(raw)
            self.send_json(200, {'data': data, 'count': len(data)})
        except subprocess.TimeoutExpired:
            self.send_json(500, {'error': 'Update-RAData.ps1 timed out after 120s'})
        except Exception as e:
            self.send_json(500, {'error': str(e)})

if __name__ == '__main__':
    print(f'RA Helper running on http://localhost:{PORT}')
    print('Keep this window open while using the dashboard.')
    print('Press Ctrl+C to stop.\n')
    HTTPServer(('localhost', PORT), Handler).serve_forever()
