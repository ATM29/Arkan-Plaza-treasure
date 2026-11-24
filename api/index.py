"""Single Vercel Python function. Secrets remain server-side, never in HTML."""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import os, json, hmac, base64, binascii

STARTS=[0,2,4,6]
META='id,team,stop,note,status,feedback,updated'
class AppError(Exception):
    def __init__(self, status, message): self.status=status; self.message=message

def team_num(value):
    try:
        number=int(value)
        return number if 0<=number<4 else None
    except (ValueError,TypeError): return None

def db(path, method='GET', payload=None):
    root=os.environ.get('SUPABASE_URL','').strip().rstrip('/')
    key=os.environ.get('SUPABASE_SECRET_KEY','').strip()
    if not root.startswith('https://') or not key:
        raise AppError(503,'The database has not been configured. Check SUPABASE_URL and SUPABASE_SECRET_KEY in Vercel.')
    headers={'apikey':key,'Content-Type':'application/json','Accept':'application/json','User-Agent':'ArkanHuntServer/1.0'}
    # New sb_secret_ keys are sent as apikey, not as JWT Bearer tokens.
    if not key.startswith('sb_secret_'): headers['Authorization']='Bearer '+key
    data=json.dumps(payload).encode() if payload is not None else None
    request=Request(root+'/rest/v1/'+path,data=data,headers=headers,method=method)
    try:
        with urlopen(request,timeout=15) as response:
            raw=response.read()
            return json.loads(raw) if raw else None
    except HTTPError as e:
        try: details=json.loads(e.read().decode())
        except Exception: details={}
        # Expose only explicitly generated safe validation errors; never expose DB internals.
        msg=details.get('message','')
        if e.code in (400,409) and msg in ('Earlier challenge needs approval.','This challenge is already submitted.','Invalid submission.'):
            raise AppError(409,msg)
        raise AppError(503,'Database request failed. Check the setup guide, database schema and Vercel environment variables.')
    except (URLError,TimeoutError,OSError,ValueError):
        raise AppError(503,'Could not reach the database. Please try again.')

class handler(BaseHTTPRequestHandler):
    def send_data(self,code,data,content_type='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(code);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def authorized(self):
        pw=os.environ.get('HOST_PASSWORD','')
        auth=self.headers.get('Authorization','')
        return bool(pw) and auth.startswith('Bearer ') and hmac.compare_digest(auth[7:].encode(),pw.encode())
    def body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise AppError(400,'Invalid request size.')
        if not 0<length<=3_000_000: raise AppError(400,'Photo too large. Please choose a smaller image.')
        try: obj=json.loads(self.rfile.read(length))
        except (ValueError,UnicodeError): raise AppError(400,'Invalid request.')
        if not isinstance(obj,dict): raise AppError(400,'Invalid request.')
        return obj
    def parameters(self):
        q=parse_qs(urlsplit(self.path).query)
        return q, q.get('route',[''])[0]
    def do_GET(self):
        try:
            q,route=self.parameters()
            if route=='status':
                team=team_num(q.get('team',[''])[0])
                if team is None: raise AppError(400,'Invalid team.')
                rows=db('hunt_submissions?select='+META+'&team=eq.'+str(team))
                return self.send_data(200,{'submissions':rows})
            if route=='host-submissions':
                if not self.authorized(): raise AppError(401,'Incorrect host password.')
                rows=db('hunt_submissions?select='+META+'&order=updated.desc')
                return self.send_data(200,{'submissions':rows})
            if route=='photo':
                team=team_num(q.get('team',[''])[0])
                try: stop=int(q.get('stop',[''])[0])
                except ValueError: stop=-1
                if team is None or not 0<=stop<8: raise AppError(404,'Photo not found.')
                rows=db('hunt_submissions?select=image&team=eq.'+str(team)+'&stop=eq.'+str(stop)+'&limit=1')
                if not rows: raise AppError(404,'Photo not found.')
                return self.send_data(200,base64.b64decode(rows[0]['image']),'image/jpeg')
            raise AppError(404,'Not found.')
        except AppError as e: self.send_data(e.status,{'error':e.message})
        except Exception: self.send_data(500,{'error':'Something went wrong. Please try again.'})
    def do_POST(self):
        try:
            _,route=self.parameters()
            if route=='submit':
                d=self.body(); team=team_num(d.get('team'))
                try: stop=int(d.get('stop',-1))
                except (ValueError,TypeError): stop=-1
                note=d.get('note',''); image=d.get('image','')
                if team is None or not 0<=stop<8 or not isinstance(note,str) or not note.strip() or len(note)>1500 or not isinstance(image,str) or len(image)>2_200_000: raise AppError(400,'Invalid submission. Include a photo and a note of up to 1,500 characters.')
                try: raw=base64.b64decode(image,validate=True)
                except (ValueError,binascii.Error): raise AppError(400,'Invalid photo. Please try another image.')
                if len(raw)<20 or not raw.startswith(b'\xff\xd8\xff'): raise AppError(400,'Please choose a valid photo.')
                db('rpc/hunt_submit','POST',{'p_team':team,'p_stop':stop,'p_note':note.strip(),'p_image':image})
                return self.send_data(200,{'ok':True})
            if route=='host-review':
                if not self.authorized(): raise AppError(401,'Incorrect host password.')
                d=self.body()
                try: ident=int(d.get('id',0))
                except (ValueError,TypeError): ident=0
                decision=d.get('decision'); feedback=d.get('feedback','')
                if ident<1 or decision not in ('approved','rejected') or not isinstance(feedback,str) or len(feedback)>500: raise AppError(400,'Invalid review.')
                if decision=='rejected' and not feedback.strip(): raise AppError(400,'Please include a note explaining what to retry.')
                result=db('rpc/hunt_review','POST',{'p_id':ident,'p_decision':decision,'p_feedback':feedback.strip()})
                if not result: raise AppError(409,'This submission is no longer pending. Refresh the dashboard.')
                return self.send_data(200,{'ok':True})
            raise AppError(404,'Not found.')
        except AppError as e: self.send_data(e.status,{'error':e.message})
        except Exception: self.send_data(500,{'error':'Something went wrong. Please try again.'})
