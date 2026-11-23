#!/usr/bin/env python3
"""Arkan Christmas Hunt: standard-library web server and SQLite-backed host review."""
import os, json, base64, sqlite3, hmac, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'hunt.sqlite3'
PASSWORD = os.environ.get('HOST_PASSWORD', '')
if not PASSWORD:
    raise SystemExit('Set HOST_PASSWORD before starting the server. See README.md.')
STARTS = [0, 2, 4, 6]

def connect():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    return c
with connect() as c:
    c.execute('CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, team INTEGER NOT NULL, stop INTEGER NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL, feedback TEXT NOT NULL DEFAULT "", image BLOB NOT NULL, mime TEXT NOT NULL, updated INTEGER NOT NULL, UNIQUE(team, stop))')

def team_num(x):
    try:
        n = int(x)
        return n if 0 <= n < 4 else None
    except (ValueError, TypeError): return None

def clean_row(row):
    return {k: row[k] for k in ['id','team','stop','note','status','feedback','updated']}

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type='application/json; charset=utf-8'):
        data = json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body
        self.send_response(status); self.send_header('Content-Type', content_type); self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Cache-Control', 'no-store' if self.path.startswith('/api/') else 'public, max-age=60')
        self.end_headers(); self.wfile.write(data)
    def error_json(self, status, message): self.respond(status, {'error': message})
    def authorized(self):
        value = self.headers.get('Authorization', '')
        return value.startswith('Bearer ') and hmac.compare_digest(value[7:].encode(), PASSWORD.encode())
    def body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise ValueError('Invalid request size.')
        if length <= 0 or length > 8_000_000: raise ValueError('Request too large or empty. Please use a smaller image.')
        try: obj=json.loads(self.rfile.read(length))
        except Exception: raise ValueError('Invalid request.')
        if not isinstance(obj,dict): raise ValueError('Invalid request.')
        return obj
    def do_GET(self):
        u=urlsplit(self.path); path=u.path
        if path in ('/', '/index.html', '/hero.png'):
            name='hero.png' if path=='/hero.png' else 'index.html'
            try: self.respond(200, (ROOT/name).read_bytes(), 'image/png' if name.endswith('.png') else 'text/html; charset=utf-8')
            except OSError: self.error_json(404,'Not found.')
            return
        if path == '/api/status':
            team=team_num(parse_qs(u.query).get('team',[''])[0])
            if team is None: return self.error_json(400,'Invalid team.')
            with connect() as c: rows=c.execute('SELECT id,team,stop,note,status,feedback,updated FROM submissions WHERE team=?', (team,)).fetchall()
            return self.respond(200, {'submissions':[clean_row(r) for r in rows]})
        if path == '/api/host/submissions':
            if not self.authorized(): return self.error_json(401,'Incorrect host password.')
            with connect() as c: rows=c.execute('SELECT id,team,stop,note,status,feedback,updated FROM submissions ORDER BY CASE status WHEN "pending" THEN 0 ELSE 1 END, updated DESC').fetchall()
            return self.respond(200, {'submissions':[clean_row(r) for r in rows]})
        m=re.fullmatch(r'/api/photo/(\d+)/(\d+)', path)
        if m:
            team=team_num(m.group(1)); stop=team_num(m.group(2)) if False else int(m.group(2))
            if team is None or not 0 <= stop < 8: return self.error_json(404,'Not found.')
            with connect() as c: row=c.execute('SELECT image,mime FROM submissions WHERE team=? AND stop=?',(team,stop)).fetchone()
            if not row: return self.error_json(404,'Not found.')
            return self.respond(200,row['image'],row['mime'])
        self.error_json(404,'Not found.')
    def do_POST(self):
        path=urlsplit(self.path).path
        if path == '/api/submit':
            try:
                d=self.body(); team=team_num(d.get('team')); stop=int(d.get('stop',-1)); note=str(d.get('note','')).strip()
                if team is None or not 0 <= stop < 8: raise ValueError('Invalid team or stop.')
                if not note or len(note)>1500: raise ValueError('Please add a note of up to 1,500 characters.')
                image=base64.b64decode(d.get('image',''), validate=True)
                if len(image)>5_000_000 or len(image)<20: raise ValueError('Invalid image or photo is too large.')
                if image[:3]==b'\xff\xd8\xff': mime='image/jpeg'
                elif image[:8]==b'\x89PNG\r\n\x1a\n': mime='image/png'
                elif image[:4]==b'RIFF' and image[8:12]==b'WEBP': mime='image/webp'
                else: raise ValueError('Use a JPEG, PNG or WebP photo.')
                with connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    rows=c.execute('SELECT stop,status FROM submissions WHERE team=?',(team,)).fetchall(); states={r['stop']:r['status'] for r in rows}
                    route=[(STARTS[team]+i)%8 for i in range(8)]; pos=route.index(stop)
                    if any(states.get(x)!='approved' for x in route[:pos]): return self.error_json(409,'An earlier challenge still needs host approval.')
                    if states.get(stop) in ('pending','approved'): return self.error_json(409,'This challenge has already been submitted.')
                    c.execute('INSERT INTO submissions(team,stop,note,status,feedback,image,mime,updated) VALUES(?,?,?,"pending","",?,?,?) ON CONFLICT(team,stop) DO UPDATE SET note=excluded.note,status="pending",feedback="",image=excluded.image,mime=excluded.mime,updated=excluded.updated',(team,stop,note,image,mime,int(time.time())))
                return self.respond(200,{'ok':True})
            except (ValueError, TypeError) as e: return self.error_json(400,str(e) or 'Invalid request.')
        if path == '/api/host/review':
            if not self.authorized(): return self.error_json(401,'Incorrect host password.')
            try:
                d=self.body(); ident=int(d.get('id',0)); decision=d.get('decision'); feedback=str(d.get('feedback','')).strip()
                if decision not in ('approved','rejected') or len(feedback)>500: raise ValueError('Invalid review.')
                if decision=='rejected' and not feedback: raise ValueError('Please include a note explaining what to retry.')
                with connect() as c:
                    cur=c.execute('UPDATE submissions SET status=?,feedback=?,updated=? WHERE id=? AND status="pending"',(decision,feedback,int(time.time()),ident))
                    if not cur.rowcount: return self.error_json(409,'This submission is no longer pending. Refresh the dashboard.')
                return self.respond(200,{'ok':True})
            except (ValueError,TypeError) as e: return self.error_json(400,str(e))
        self.error_json(404,'Not found.')
    def log_message(self, format, *args):
        # Avoid logging passwords, query parameters, and submission content.
        print('%s %s' % (self.command, urlsplit(self.path).path), flush=True)

if __name__ == '__main__':
    port=int(os.environ.get('PORT','8000'))
    print('Arkan hunt server listening on port %s' % port, flush=True)
    ThreadingHTTPServer(('0.0.0.0',port), Handler).serve_forever()
