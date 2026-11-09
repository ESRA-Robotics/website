#!/usr/bin/env python3
"""Optional ESRA events API. Python 3.11+, SQLite, no third-party dependencies.
Run behind an HTTPS reverse proxy in production; see backend/README.md.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from functools import partial
from hashlib import sha256
import hmac
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import smtplib
import sqlite3
import ssl
import time
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'events/catalog.json').read_text())
TYPES = CATALOG['types']
CONSENT_VERSION = 'events-newsletter-2026-11-09'

class Invalid(ValueError):
    pass

class Service:
    def __init__(self, db, secret, site, reviewers=(), delivery=False, sender=''):
        if len(secret) < 32:
            raise Invalid('ESRA_SECRET must contain at least 32 characters')
        self.db, self.secret, self.site = str(db), secret.encode(), site.rstrip('/')
        self.reviewers, self.delivery, self.sender = tuple(reviewers), delivery, sender
        self.origins = {self.site}
        if sender: self.email(parseaddr(sender)[1])
        if delivery and (not sender or not self.reviewers):
            raise Invalid('Enabled delivery requires a sender and trusted reviewers')
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL')
            c.executescript('''
            CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, payload TEXT NOT NULL,
              contact TEXT NOT NULL, status TEXT NOT NULL, submitted REAL NOT NULL,
              reviewer TEXT, reviewed REAL);
            CREATE TABLE IF NOT EXISTS subscribers(email TEXT PRIMARY KEY, prefs TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 0, consent TEXT NOT NULL, created REAL NOT NULL,
              confirmed REAL, revision TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, recipient TEXT NOT NULL,
              subject TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
              created REAL NOT NULL, sent REAL);
            CREATE TABLE IF NOT EXISTS limits(key TEXT PRIMARY KEY, count INTEGER, expires REAL);
            ''')
            # Serialise migration discovery when multiple WSGI workers start together.
            c.execute('BEGIN IMMEDIATE')
            # Additive migration: existing submissions and queues are preserved.
            columns={r['name'] for r in c.execute('PRAGMA table_info(events)')}
            for name in ('start_at','end_at'):
                if name not in columns:c.execute(f'ALTER TABLE events ADD COLUMN {name} REAL')
            while True:
                legacy=c.execute('SELECT id,payload FROM events WHERE start_at IS NULL LIMIT 200').fetchall()
                if not legacy:break
                for row in legacy:
                    event=json.loads(row['payload'])
                    c.execute('UPDATE events SET start_at=?,end_at=? WHERE id=?',
                              (datetime.fromisoformat(event['start']).timestamp(),datetime.fromisoformat(event['end']).timestamp(),row['id']))
            c.executescript('''
            CREATE INDEX IF NOT EXISTS events_by_start ON events(status,start_at,id);
            CREATE INDEX IF NOT EXISTS events_by_end ON events(status,end_at);
            CREATE INDEX IF NOT EXISTS events_by_type ON events(status,json_extract(payload,'$.type'),start_at,id);
            CREATE INDEX IF NOT EXISTS outbox_pending ON outbox(state,created,id);
            CREATE INDEX IF NOT EXISTS subscribers_active ON subscribers(active,email);
            CREATE INDEX IF NOT EXISTS limits_expiry ON limits(expires);
            ''')
        Path(self.db).chmod(0o600)
    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout=15000')
        c.create_function('casefold',1,lambda value: str(value).casefold(),deterministic=True)
        try:
            with c:
                yield c
        finally:
            c.close()
    def token(self, kind, identity, days=7, revision=''):
        data = json.dumps([kind, identity, int(time.time()+days*86400), revision], separators=(',', ':')).encode()
        payload = base64.urlsafe_b64encode(data).decode().rstrip('=')
        signature = hmac.new(self.secret, payload.encode(), sha256).hexdigest()
        return payload + '.' + signature
    def verify(self, token, kind):
        try:
            payload, sig = token.split('.')
            expected = hmac.new(self.secret, payload.encode(), sha256).hexdigest()
            if not hmac.compare_digest(sig, expected): raise Invalid('Invalid link')
            scope, identity, expiry, revision = json.loads(base64.urlsafe_b64decode(payload + '='*(-len(payload)%4)))
            if scope != kind or expiry < time.time(): raise Invalid('Expired or invalid link')
            return identity, revision
        except (ValueError, TypeError, KeyError) as e:
            raise Invalid('Expired or invalid link') from e
    def limit(self, identity, scope, maximum):
        # Store a hash of the direct peer address, never trust arbitrary proxy headers.
        key = hmac.new(self.secret, (scope+identity).encode(), sha256).hexdigest()
        with self.connect() as c:
            c.execute('DELETE FROM limits WHERE expires < ?', (time.time(),))
            c.execute('INSERT INTO limits VALUES(?,0,?) ON CONFLICT DO NOTHING', (key,time.time()+3600))
            c.execute('UPDATE limits SET count=count+1 WHERE key=?', (key,))
            count = c.execute('SELECT count FROM limits WHERE key=?',(key,)).fetchone()[0]
        if count > maximum: raise Invalid('Too many requests. Please try again later.')
    @staticmethod
    def email(value):
        value = str(value).strip().lower()
        if len(value)>254 or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value):
            raise Invalid('Enter a valid email address')
        return value
    @staticmethod
    def text(data, name, minimum=1, maximum=500):
        value = str(data.get(name, '')).strip()
        if not minimum <= len(value) <= maximum: raise Invalid(f'Check {name} ({minimum}–{maximum} characters)')
        return value
    @staticmethod
    def prefs(data):
        types = data.get('types', [])
        origin = data.get('origin', 'all')
        club = str(data.get('club', '')).strip()[:100]
        if not isinstance(types,list) or not types or any(t not in TYPES for t in types) or origin not in ('all','original','community'):
            raise Invalid('Select at least one supported event type')
        return {'types': sorted(set(types)), 'origin': origin, 'club': club}
    def queue(self, c, key, recipient, subject, body):
        c.execute('INSERT INTO outbox(id,recipient,subject,body,created) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING',
                  (key,recipient,subject,body,time.time()))
    def email_html(self, title, body, actions):
        buttons = ''.join(f'<a href="{escape(url, quote=True)}" style="display:inline-block;padding:14px 20px;margin:8px 8px 8px 0;background:#fff0b5;color:#222;text-decoration:none;border:1px solid #222">{escape(label)}</a>' for label,url in actions)
        return f'<!doctype html><html lang="en"><meta charset="utf-8"><body style="margin:0;background:#f3f4f1;color:#222;font-family:Arial,sans-serif"><div style="max-width:640px;margin:auto;padding:32px"><p style="font-family:monospace">ESRA / EUROPEAN STUDENT ROBOTICS</p><hr><h1>{escape(title)}</h1>{body}<p>{buttons}</p><hr><p><a href="{escape(self.site)}/events/">Open ESRA Events</a></p></div></body></html>'
    def submit(self, data):
        if not self.reviewers: raise Invalid('Event submissions are not configured yet')
        if data.get('website'): raise Invalid('Invalid submission') # honeypot
        if data.get('rules') is not True: raise Invalid('Please accept the event submission rules')
        payload = {k:self.text(data,k,1,160) for k in ('title','organiser','location')}
        if any(re.search(r'[\x00-\x1f\x7f]',v) for v in payload.values()): raise Invalid('Use plain text for event name, organiser and location')
        payload['description'] = self.text(data,'description',40,4000)
        payload['relevance'] = self.text(data,'relevance',30,1500)
        payload['type'] = data.get('type')
        if payload['type'] not in TYPES: raise Invalid('Choose an event type')
        url = self.text(data,'url',1,1000)
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise Invalid('Use a public HTTPS registration link')
        payload['url'] = url
        try:
            start = datetime.fromisoformat(str(data['start']))
            end = datetime.fromisoformat(str(data['end']))
            if not start.tzinfo or not end.tzinfo or end<start or end-start>timedelta(days=365): raise ValueError()
        except (ValueError, KeyError): raise Invalid('Enter valid dates with a timezone; end must follow start')
        payload.update(start=start.isoformat(),end=end.isoformat(),original=False)
        contact = self.email(data.get('email',''))
        event_id = secrets.token_urlsafe(18)
        payload['id'] = event_id
        with self.connect() as c:
            c.execute('INSERT INTO events(id,payload,contact,status,submitted,reviewer,reviewed,start_at,end_at) VALUES(?,?,?,?,?,?,?,?,?)',(event_id,json.dumps(payload),contact,'pending',time.time(),None,None,start.timestamp(),end.timestamp()))
            for reviewer in self.reviewers:
                token = self.token('review', [event_id,reviewer])
                base = self.site + '/events/review/#token=' + token
                body = '<p>A community organiser requests publication. Check ESRA relevance, organiser identity, dates, location, costs and registration details.</p>'
                body += ''.join(f'<p><b>{escape(k.title())}:</b> {escape(str(v))}</p>' for k,v in payload.items() if k not in ('id','original'))
                body += '<p>Accept and decline open a secure confirmation page. Opening a link alone does not change the event. Link expires in seven days.</p>'
                html = self.email_html('Review an event', body,[('Accept',base+'&action=accept'),('Decline',base+'&action=decline'),('Open review',base)])
                self.queue(c,'review:'+event_id+':'+reviewer,reviewer,'ESRA event review: '+payload['title'],html)
        return {'id':event_id,'message':'Submitted for ESRA review. Your event is not public yet.'}
    def review(self, token, action=None):
        (event_id,reviewer),_ = self.verify(token,'review')
        if reviewer not in self.reviewers: raise Invalid('Reviewer is no longer authorised')
        with self.connect() as c:
            row = c.execute('SELECT * FROM events WHERE id=?',(event_id,)).fetchone()
            if not row: raise Invalid('Event not found')
            if action:
                if action not in ('accept','decline'): raise Invalid('Choose accept or decline')
                status = 'approved' if action=='accept' else 'declined'
                changed = c.execute('UPDATE events SET status=?,reviewer=?,reviewed=? WHERE id=? AND status=?',
                                    (status,reviewer,time.time(),event_id,'pending')).rowcount
                if not changed: raise Invalid('This submission has already been reviewed')
                return {'message':'Event accepted and published.' if action=='accept' else 'Event declined.'}
            return {'event':json.loads(row['payload']),'status':row['status'],'contact':row['contact']}
    @staticmethod
    def public_event(event):
        fields=('id','title','organiser','location','type','start','end','description','original','url')
        return {key:event[key] for key in fields if key in event}
    def events(self, active_only=False):
        sql="SELECT payload FROM events WHERE status='approved'"
        values=[]
        if active_only:sql+=' AND end_at>=?';values.append(time.time())
        with self.connect() as c:entries=[json.loads(r[0]) for r in c.execute(sql+' ORDER BY submitted DESC',values)]
        originals=[e for e in CATALOG['events'] if not active_only or datetime.fromisoformat(e['end']).timestamp()>=time.time()]
        return [self.public_event(e) for e in originals+entries]
    def event_page(self, query):
        """Indexed, bounded public listing. Originals are independent of community pagination."""
        def one(key, default):return query.get(key,[default])[0]
        try:limit=int(one('limit','25'))
        except (ValueError,TypeError):raise Invalid('Invalid page size')
        if not 1<=limit<=100:raise Invalid('Page size must be 1–100')
        period=one('period','upcoming');origin=one('origin','all')
        types=query.get('type',TYPES);club=one('club','').strip()[:100]
        if period not in ('upcoming','current','past') or origin not in ('all','original','community') or any(t not in TYPES for t in types):raise Invalid('Invalid event filters')
        now=datetime.now(timezone.utc);stamp=now.timestamp()
        clauses=["status='approved'"];values=[]
        if period=='upcoming':clauses.append('start_at>?');values.append(stamp)
        elif period=='current':clauses.append('start_at<=? AND end_at>=?');values.extend([stamp,stamp])
        else:clauses.append('end_at<?');values.append(stamp)
        clauses.append("json_extract(payload,'$.type') IN ("+','.join('?' for _ in types)+')');values.extend(types)
        if origin=='original':clauses.append('0') # Original status is reserved for the curated catalogue.
        if club:clauses.append("instr(casefold(json_extract(payload,'$.organiser')),?)>0");values.append(club.casefold())
        cursor=one('cursor','')
        if cursor:
            try:
                point=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
                if not isinstance(point,list) or len(point)!=2 or not isinstance(point[0],(int,float)) or not isinstance(point[1],str):raise ValueError()
            except (ValueError,TypeError):raise Invalid('Invalid cursor')
            clauses.append('(start_at,id) '+('<' if period=='past' else '>')+' (?,?)');values.extend(point)
        direction='DESC' if period=='past' else 'ASC'
        sql='SELECT id,payload,start_at FROM events WHERE '+' AND '.join(clauses)+f' ORDER BY start_at {direction},id {direction} LIMIT ?'
        with self.connect() as c:rows=c.execute(sql,values+[limit+1]).fetchall()
        more=len(rows)>limit;rows=rows[:limit]
        next_cursor=None
        if more:
            last=rows[-1];next_cursor=base64.urlsafe_b64encode(json.dumps([last['start_at'],last['id']]).encode()).decode().rstrip('=')
        def selected(e):
            start=datetime.fromisoformat(e['start']);end=datetime.fromisoformat(e['end'])
            time_match=start>now if period=='upcoming' else start<=now<=end if period=='current' else end<now
            return time_match and e['type'] in types and origin!='community' and (not club or club.casefold() in e['organiser'].casefold())
        public=[self.public_event(json.loads(r['payload'])) for r in rows]
        return {'events':public,'featured':[e for e in CATALOG['events'] if selected(e)],'next_cursor':next_cursor}
    def subscribe(self,data):
        if data.get('consent') is not True: raise Invalid('Please consent to the selected event newsletter')
        email, prefs = self.email(data.get('email','')), self.prefs(data)
        self.limit(email,'confirmation-email',3)
        revision = secrets.token_urlsafe(18)
        # Do not change existing preferences until the new request is confirmed.
        token = self.token('confirm',[email,prefs],2,revision)
        with self.connect() as c:
            row = c.execute('SELECT * FROM subscribers WHERE email=?',(email,)).fetchone()
            if not row:
                c.execute('INSERT INTO subscribers VALUES(?,?,0,?,?,NULL,?)',(email,json.dumps(prefs),CONSENT_VERSION,time.time(),revision))
            else:
                c.execute('UPDATE subscribers SET revision=? WHERE email=?',(revision,email))
            url = self.site+'/events/preferences/#token='+token+'&mode=confirm'
            html = self.email_html('Confirm your event preferences','<p>Confirm your email to receive ESRA event updates for the topics you selected. If you did not request this, ignore this email.</p><p>'+escape(', '.join(prefs['types']))+'</p>',[('Confirm subscription',url)])
            self.queue(c,'confirm:'+revision,email,'Confirm your ESRA event subscription',html)
        return {'message':'Request saved. Check your email for a confirmation link once email delivery is active.'}
    def confirm(self,token):
        (email,prefs),revision = self.verify(token,'confirm')
        with self.connect() as c:
            changed = c.execute('UPDATE subscribers SET active=1,prefs=?,confirmed=?,consent=?,revision=? WHERE email=? AND revision=?',
                 (json.dumps(prefs),time.time(),CONSENT_VERSION,secrets.token_urlsafe(18),email,revision)).rowcount
            if not changed: raise Invalid('This confirmation has expired or was already used')
        return {'message':'Subscription confirmed. You can now manage your preferences.', 'token':self.token('manage',email,90)}
    def manage(self,token,data=None):
        email,_ = self.verify(token,'manage')
        with self.connect() as c:
            row = c.execute('SELECT * FROM subscribers WHERE email=?',(email,)).fetchone()
            if not row: raise Invalid('Subscription not found')
            if data is not None:
                if data.get('unsubscribe') is True:
                    c.execute('DELETE FROM subscribers WHERE email=?',(email,))
                    c.execute("DELETE FROM outbox WHERE recipient=? AND state='pending'",(email,))
                    return {'message':'Unsubscribed. Your subscription details have been removed.'}
                prefs = self.prefs(data)
                c.execute('UPDATE subscribers SET prefs=? WHERE email=?',(json.dumps(prefs),email))
                return {'message':'Preferences updated.'}
            return {'email':email,**json.loads(row['prefs']),'active':bool(row['active'])}
    @staticmethod
    def matches(event,prefs,now=None):
        now = now or datetime.now(timezone.utc)
        return (datetime.fromisoformat(event['end'])>=now and event['type'] in prefs['types']
                and (prefs['origin']=='all' or event['original']==(prefs['origin']=='original'))
                and (not prefs['club'] or prefs['club'].casefold() in event['organiser'].casefold()))
    def digest(self,period):
        if not re.fullmatch(r'\d{4}-W\d{2}',period): raise Invalid('Use an ISO week such as 2027-W02')
        events = self.events(active_only=True)
        after=''
        while True:
            with self.connect() as c:
                subscribers=c.execute('SELECT * FROM subscribers WHERE active=1 AND email>? ORDER BY email LIMIT 200',(after,)).fetchall()
            if not subscribers:break
            after=subscribers[-1]['email']
            for row in subscribers:
                selected = [e for e in events if self.matches(e,json.loads(row['prefs']))]
                if not selected: continue
                manage = self.site+'/events/preferences/#token='+self.token('manage',row['email'],90)
                body = '<p>Your selected European robotics events.</p>'
                for e in selected:
                    url = e['url'] if e['url'].startswith('https://') else self.site+e['url']
                    body += f'<h2>{escape(e["title"])}</h2><p>{escape(e["organiser"])} · {escape(e["location"])} · {escape(e["type"])}</p><p>{escape(e["start"][:10])} – {escape(e["end"][:10])}</p><p><a href="{escape(url,quote=True)}">View event</a></p>'
                html = self.email_html('Your robotics week',body,[('Manage preferences',manage),('Unsubscribe',manage+'&action=unsubscribe')])
                with self.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    # Do not requeue a subscriber removed/changed while the batch was rendered.
                    current=c.execute('SELECT prefs FROM subscribers WHERE email=? AND active=1',(row['email'],)).fetchone()
                    if current and current['prefs']==row['prefs']:
                        self.queue(c,'digest:'+period+':'+row['email'],row['email'],'ESRA events · '+period,html)
    def prune(self):
        with self.connect() as c:
            c.execute("DELETE FROM events WHERE status IN ('pending','declined') AND submitted<?",(time.time()-90*86400,))
            c.execute('DELETE FROM subscribers WHERE active=0 AND created<?',(time.time()-7*86400,))
            c.execute('DELETE FROM outbox WHERE created<?',(time.time()-30*86400,))
            c.execute('DELETE FROM limits WHERE expires<?',(time.time(),))
    def stats(self):
        with self.connect() as c:
            return {'events':dict(c.execute('SELECT status,count(*) FROM events GROUP BY status').fetchall()),
                    'mail':dict(c.execute('SELECT state,count(*) FROM outbox GROUP BY state').fetchall()),
                    'active_subscriptions':c.execute('SELECT count(*) FROM subscribers WHERE active=1').fetchone()[0]}
    def claim_message(self):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute("SELECT * FROM outbox WHERE state='pending' ORDER BY created,id LIMIT 1").fetchone()
            if row:c.execute("UPDATE outbox SET state='claimed' WHERE id=? AND state='pending'",(row['id'],))
            return row
    def deliver(self, batch_size=50):
        if not self.delivery: raise Invalid('Delivery disabled; no emails sent')
        if not 1<=batch_size<=500:raise Invalid('Delivery batch must be 1–500')
        host = os.environ.get('SMTP_HOST','')
        if not host: raise Invalid('Configure SMTP_HOST before enabling delivery')
        sent=0
        for _ in range(batch_size):
            row=self.claim_message()
            if not row:break
            try:
                msg=EmailMessage();msg['From']=self.sender;msg['To']=row['recipient'];msg['Subject']=row['subject']
                msg['Message-ID']='<'+sha256(row['id'].encode()).hexdigest()+'@'+parseaddr(self.sender)[1].split('@')[-1]+'>'
                msg.set_content('Open the HTML version of this ESRA message to review the details and links.')
                msg.add_alternative(row['body'],subtype='html')
                with smtplib.SMTP(host,int(os.environ.get('SMTP_PORT','587')),timeout=20) as smtp:
                    smtp.starttls(context=ssl.create_default_context())
                    if os.environ.get('SMTP_USER'):smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
                    smtp.send_message(msg)
                with self.connect() as c:c.execute("UPDATE outbox SET state='sent',sent=? WHERE id=?",(time.time(),row['id']))
                sent+=1
            except Exception:
                # A remote server may have accepted the email before disconnecting.
                # Hold only this message, never automatically retry ambiguous delivery.
                with self.connect() as c:c.execute("UPDATE outbox SET state='uncertain' WHERE id=?",(row['id'],))
                continue
        return sent

class Handler(SimpleHTTPRequestHandler):
    server_version = 'ESRA'
    def log_message(self,*args): pass # Tokens, contact details and request bodies never enter access logs.
    def end_headers(self):
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        if self.headers.get('Origin') in self.app.origins:
            self.send_header('Access-Control-Allow-Origin',self.headers['Origin'])
            self.send_header('Vary','Origin')
        super().end_headers()
    @property
    def app(self): return self.server.app
    def reply(self,data,status=200):
        raw=json.dumps(data).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def auth(self):
        auth=self.headers.get('Authorization','')
        if not auth.startswith('Bearer '): raise Invalid('Open the secure link from your email')
        return auth[7:]
    def do_GET(self):
        path=urlsplit(self.path).path
        try:
            if path=='/api/health': return self.reply({'ready':bool(self.app.reviewers),'delivery':self.app.delivery})
            if path=='/api/events': return self.reply(self.app.event_page(parse_qs(urlsplit(self.path).query)))
            if path=='/api/review': return self.reply(self.app.review(self.auth()))
            if path=='/api/preferences': return self.reply(self.app.manage(self.auth()))
            # Never expose the repository, private DB, backend files or directory listings.
            if path.startswith('/api/'): return self.reply({'error':'Not found'},404)
            decoded_path = self.translate_path(path)
            target=Path(decoded_path).resolve()
            if not target.is_relative_to(ROOT): return self.send_error(404)
            rel=target.relative_to(ROOT)
            if any(part.startswith('.') for part in rel.parts) or not (str(rel) in ('.','index.html','404.html') or (rel.parts and rel.parts[0] in ('assets','events','imprint'))):
                return self.send_error(404)
            if target.is_dir() and not (target/'index.html').exists(): return self.send_error(404)
            return super().do_GET()
        except Invalid as e: self.reply({'error':str(e)},400)
    def do_OPTIONS(self):
        if self.headers.get('Origin') not in self.app.origins: return self.reply({'error':'Origin not allowed'},403)
        self.send_response(204)
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization')
        self.end_headers()
    def do_HEAD(self):
        self.send_error(405) # Do not fall through to the broad static-file handler.
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin not in self.app.origins: return self.reply({'error':'Origin not allowed'},403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise Invalid('Use JSON')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=20000: raise Invalid('Request too large or empty')
            data=json.loads(self.rfile.read(length)); path=urlsplit(self.path).path
            if not isinstance(data,dict): raise Invalid('Invalid request')
            if path in ('/api/submissions','/api/subscribe'):
                self.app.limit(self.client_address[0],path,10)
            if path=='/api/submissions': result=self.app.submit(data)
            elif path=='/api/subscribe': result=self.app.subscribe(data)
            elif path=='/api/review': result=self.app.review(self.auth(),data.get('action'))
            elif path=='/api/confirm': result=self.app.confirm(self.auth())
            elif path=='/api/preferences': result=self.app.manage(self.auth(),data)
            else: return self.reply({'error':'Not found'},404)
            self.reply(result)
        except (Invalid, ValueError, json.JSONDecodeError) as e: self.reply({'error':str(e)},400)
        except Exception: self.reply({'error':'Request could not be saved. Please try again.'},500)

def configured_service():
    # Optional local configuration is excluded from Git and from all public exports.
    env=ROOT/'backend/.env.local'
    if env.exists():
        for line in env.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key,value=line.split('=',1);os.environ.setdefault(key,value)
    db=Path(os.environ.get('ESRA_DB',str(ROOT/'backend/private/events.sqlite3')))
    db.parent.mkdir(parents=True,exist_ok=True)
    app = Service(db,os.environ.get('ESRA_SECRET',''),os.environ.get('ESRA_SITE','http://127.0.0.1:8000'),
                   [Service.email(x) for x in os.environ.get('REVIEWER_EMAILS','').split(',') if x.strip()],
                   os.environ.get('EMAIL_DELIVERY')=='enabled',os.environ.get('EMAIL_FROM',''))
    for origin in os.environ.get('ESRA_ORIGINS','').split(','):
        if origin.strip(): app.origins.add(origin.strip().rstrip('/'))
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['serve','prepare-digest','deliver','prune','stats'])
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--batch-size',type=int,default=50)
    parser.add_argument('--period',default=datetime.now(timezone.utc).strftime('%G-W%V'))
    args=parser.parse_args();app=configured_service()
    if args.command=='prepare-digest': app.digest(args.period)
    elif args.command=='deliver': print(json.dumps({'sent':app.deliver(args.batch_size)}))
    elif args.command=='prune': app.prune()
    elif args.command=='stats': print(json.dumps(app.stats()))
    else:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(ROOT)))
        server.app=app; print(f'ESRA local service: http://127.0.0.1:{args.port}',flush=True)
        server.serve_forever()
