"""Run with python3 -m unittest discover -s backend -p 'test_*.py'. No emails sent."""
from datetime import datetime, timezone
from functools import partial
from http.server import ThreadingHTTPServer
import http.client
import json
import secrets
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from service import Service, Invalid, Handler, ROOT

class EventsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=Service(self.tmp.name+'/events.sqlite3',secrets.token_urlsafe(40),'http://127.0.0.1:8000',['reviewer@example.org'])
        self.event={'title':'Student robotics workshop','organiser':'Example Club','location':'Munich, Germany','type':'Workshops',
          'description':'A hands-on robotics workshop for students. Free entry, in English.','relevance':'A technical exchange for European student robotics clubs.',
          'start':'2027-02-01T10:00:00+01:00','end':'2027-02-01T18:00:00+01:00','email':'organiser@example.org','url':'https://example.org/event','rules':True}
        self.prefs={'email':'reader@example.org','types':['Workshops'],'origin':'community','club':'Example','consent':True}
    def tearDown(self): self.tmp.cleanup()
    def token_from_mail(self,kind):
        with self.app.connect() as c: body=c.execute('SELECT body FROM outbox WHERE id LIKE ? ORDER BY created DESC',(kind+'%',)).fetchone()[0]
        import re
        return re.search(r'#token=([^"&]+)',body)[1]
    def test_moderation_publication_and_replay(self):
        event_id=self.app.submit({**self.event,'original':True})['id']
        self.assertEqual(len(self.app.events()),1)
        token=self.token_from_mail('review:')
        # GET only reads; email scanners cannot publish.
        self.assertEqual(self.app.review(token)['status'],'pending')
        self.assertEqual(len(self.app.events()),1)
        self.app.review(token,'accept')
        public=self.app.events()[1]
        self.assertEqual(public['id'],event_id);self.assertFalse(public['original'])
        self.assertNotIn('contact',public);self.assertNotIn('email',public);self.assertNotIn('relevance',public)
        with self.assertRaises(Invalid): self.app.review(token,'decline')
    def test_decline_and_revoked_reviewer(self):
        self.app.submit(self.event);token=self.token_from_mail('review:')
        self.app.review(token,'decline');self.assertEqual(len(self.app.events()),1)
        self.app.reviewers=()
        with self.assertRaises(Invalid):self.app.review(token)
    def test_scope_expiry_and_tampering(self):
        with self.assertRaises(Invalid):self.app.review(self.app.token('manage','x'))
        with self.assertRaises(Invalid):self.app.review(self.app.token('review',['x','reviewer@example.org'],-1))
        token=self.app.token('review',['x','reviewer@example.org'])
        with self.assertRaises(Invalid):self.app.review(token+'0')
    def test_validation_and_html_escaping(self):
        for override in ({'url':'javascript:alert(1)'},{'rules':False},{'start':'2027-02-01T10:00:00'},{'end':'2026-01-01T00:00:00+00:00'},{'type':'Spam'},{'title':'Event\nBcc: victim@example.org'}):
            with self.subTest(override=override),self.assertRaises(Invalid):self.app.submit({**self.event,**override})
        self.app.submit({**self.event,'title':'<script>alert(1)</script>'})
        with self.app.connect() as c: html=c.execute('SELECT body FROM outbox').fetchone()[0]
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
    def test_confirmation_preferences_digest_and_unsubscribe(self):
        self.app.submit(self.event);self.app.review(self.token_from_mail('review:'),'accept')
        self.app.subscribe(self.prefs);confirmation=self.token_from_mail('confirm:')
        self.app.digest('2027-W01')
        with self.app.connect() as c:self.assertEqual(c.execute("SELECT count(*) FROM outbox WHERE id LIKE 'digest:%'").fetchone()[0],0)
        manage=self.app.confirm(confirmation)['token']
        with self.assertRaises(Invalid): self.app.confirm(confirmation)
        self.assertEqual(self.app.manage(manage)['types'],['Workshops'])
        self.app.digest('2027-W01');self.app.digest('2027-W01')
        with self.app.connect() as c:
            rows=c.execute("SELECT body FROM outbox WHERE id LIKE 'digest:%'").fetchall()
            self.assertEqual(len(rows),1);self.assertIn('Student robotics workshop',rows[0][0]);self.assertNotIn('China Trip',rows[0][0])
        self.app.manage(manage,{'types':['Trips'],'origin':'original','club':''})
        self.app.digest('2027-W02')
        with self.app.connect() as c:self.assertIn('China Trip',c.execute("SELECT body FROM outbox WHERE id LIKE 'digest:2027-W02:%'").fetchone()[0])
        self.app.manage(manage,{'unsubscribe':True})
        with self.app.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM subscribers').fetchone()[0],0)
            self.assertEqual(c.execute("SELECT count(*) FROM outbox WHERE recipient='reader@example.org' AND state='pending'").fetchone()[0],0)
    def test_filter_boundaries_and_origin(self):
        event={**self.event,'original':False};prefs={'types':['Workshops'],'origin':'community','club':'example'}
        self.assertTrue(self.app.matches(event,prefs,datetime(2027,2,1,12,tzinfo=timezone.utc)))
        self.assertFalse(self.app.matches(event,prefs,datetime(2027,2,2,tzinfo=timezone.utc)))
        self.assertFalse(self.app.matches(event,{**prefs,'origin':'original'},datetime(2027,1,1,tzinfo=timezone.utc)))
    def test_rate_limit_and_disabled_delivery(self):
        for _ in range(3):self.app.subscribe(self.prefs)
        with self.assertRaises(Invalid):self.app.subscribe(self.prefs)
        with patch('smtplib.SMTP') as smtp:
            with self.assertRaises(Invalid):self.app.deliver()
            smtp.assert_not_called()
    def test_wsgi_public_boundary_and_origin(self):
        import io
        import wsgi
        wsgi._service=self.app
        def call(method,path,origin='',payload=None):
            raw=json.dumps(payload or {}).encode();captured={}
            env={'REQUEST_METHOD':method,'PATH_INFO':path,'HTTP_ORIGIN':origin,
                 'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),
                 'REMOTE_ADDR':'127.0.0.1','wsgi.input':io.BytesIO(raw)}
            def start(status,headers):captured.update(status=status,headers=dict(headers))
            result=json.loads(b''.join(wsgi.application(env,start)))
            return captured,result
        self.assertEqual(call('GET','/backend/private/events.sqlite3')[0]['status'],'404 Not Found')
        self.assertEqual(call('POST','/api/submissions','https://evil.example',self.event)[0]['status'],'403 Forbidden')
        response,_=call('OPTIONS','/api/submissions',self.app.site)
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'],self.app.site)
        response,result=call('POST','/api/submissions',self.app.site,self.event)
        self.assertEqual(response['status'],'200 OK');self.assertIn('id',result)
    def test_dispatch_transport_is_explicit_and_idempotent(self):
        self.app.submit(self.event)
        self.app.delivery=True;self.app.sender='sender@example.org'
        with patch.dict('os.environ',{'SMTP_HOST':'smtp.example.org','SMTP_USER':'test','SMTP_PASSWORD':'test'}),patch('smtplib.SMTP') as transport:
            smtp=transport.return_value.__enter__.return_value
            self.app.deliver();self.app.deliver()
            smtp.starttls.assert_called_once();smtp.send_message.assert_called_once()
            message=smtp.send_message.call_args[0][0]
            self.assertEqual(message['To'],'reviewer@example.org')
        with self.app.connect() as c:self.assertEqual(c.execute('SELECT state FROM outbox').fetchone()[0],'sent')
    def publish(self,**overrides):
        event_id=self.app.submit({**self.event,**overrides})['id']
        self.app.review(self.app.token('review',[event_id,'reviewer@example.org']),'accept')
        return event_id
    def test_cursor_pages_filter_before_pagination_and_preserve_originals(self):
        ids={self.publish(title=f'Workshop {i}') for i in range(5)}
        query={'type':['Workshops'],'origin':['community'],'period':['upcoming'],'limit':['2']}
        seen=[]
        while True:
            page=self.app.event_page(query);seen.extend(e['id'] for e in page['events'])
            self.assertLessEqual(len(page['events']),2);self.assertEqual(page['featured'],[])
            if not page['next_cursor']:break
            query['cursor']=[page['next_cursor']]
        self.assertEqual(set(seen),ids);self.assertEqual(len(seen),len(ids))
        self.assertEqual(self.app.event_page({'club':['missing']})['events'],[])
        self.assertEqual(self.app.event_page({'origin':['original']})['featured'][0]['id'],'china-trip-2027')
        for bad in [{'limit':['0']},{'limit':['101']},{'cursor':['not-a-cursor']},{'type':['Spam']}]:
            with self.assertRaises(Invalid):self.app.event_page(bad)
    def test_concurrent_workers_claim_each_message_once(self):
        from concurrent.futures import ThreadPoolExecutor
        with self.app.connect() as c:
            for i in range(12):self.app.queue(c,f'worker-test:{i}','test@example.org','Test','<p>Test</p>')
        with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:self.app.claim_message(),range(16)))
        ids=[row['id'] for row in rows if row]
        self.assertEqual(len(ids),12);self.assertEqual(len(set(ids)),12)
    def test_failed_smtp_does_not_claim_or_block_entire_queue(self):
        with self.app.connect() as c:
            for i in range(3):self.app.queue(c,f'delivery:{i}','test@example.org','Test','<p>Test</p>')
        self.app.delivery=True;self.app.sender='sender@example.org'
        with patch.dict('os.environ',{'SMTP_HOST':'smtp.example.org'}),patch('smtplib.SMTP',side_effect=OSError('offline')):
            self.assertEqual(self.app.deliver(batch_size=1),0)
        with self.app.connect() as c:
            states=[r[0] for r in c.execute('SELECT state FROM outbox')]
        self.assertEqual(states.count('uncertain'),1);self.assertEqual(states.count('pending'),2)
    def test_existing_schema_migration_preserves_data(self):
        legacy=self.tmp.name+'/legacy.sqlite3'
        with sqlite3.connect(legacy) as c:
            c.execute('CREATE TABLE events(id TEXT PRIMARY KEY,payload TEXT,contact TEXT,status TEXT,submitted REAL,reviewer TEXT,reviewed REAL)')
            c.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',('old',json.dumps({**self.event,'id':'old','original':False}),'private@example.org','approved',1,None,None))
        upgraded=Service(legacy,secrets.token_urlsafe(40),self.app.site)
        public=upgraded.event_page({'type':['Workshops']})['events'][0]
        self.assertEqual(public['id'],'old');self.assertNotIn('email',public);self.assertNotIn('relevance',public)
        with upgraded.connect() as c:
            self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0],'wal')
            self.assertIsNotNone(c.execute('SELECT start_at FROM events').fetchone()[0])
    def test_digest_crosses_subscriber_batches_without_loss_or_duplicates(self):
        self.publish()
        with self.app.connect() as c:
            for i in range(205):
                c.execute('INSERT INTO subscribers VALUES(?,?,1,?,?,?,?)',
                          (f'batch{i:03d}@example.org',json.dumps({'types':['Workshops'],'origin':'community','club':''}),'test-consent',1,1,'revision'))
        self.app.digest('2027-W03');self.app.digest('2027-W03')
        with self.app.connect() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM outbox WHERE id LIKE 'digest:%'").fetchone()[0],205)
    def test_multiple_service_workers_can_initialise_the_same_store(self):
        from concurrent.futures import ThreadPoolExecutor
        shared=self.tmp.name+'/shared.sqlite3'
        def start(_):return Service(shared,'shared-test-secret-12345678901234567890',self.app.site)
        with ThreadPoolExecutor(max_workers=4) as pool:workers=list(pool.map(start,range(4)))
        self.assertEqual(len(workers),4)
        self.assertEqual(workers[0].event_page({})['events'],[])
    def test_api_origin_and_private_files(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)));server.app=self.app
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def call(method,path,body=None,headers=None):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port)
            c.request(method,path,body,headers or {});r=c.getresponse();result=(r.status,r.read());c.close();return result
        try:
            status,_=call('POST','/api/submissions',json.dumps(self.event),{'Origin':'https://evil.example','Content-Type':'application/json'})
            self.assertEqual(status,403)
            for path in ['/backend/.env.local','/backend/private/events.sqlite3','/events/../backend/private/events.sqlite3','/.git/config','/events/%2e%2e/backend/service.py']:
                self.assertEqual(call('GET',path)[0],404,path)
            self.assertEqual(call('GET','/api/events')[0],200)
            self.assertEqual(call('HEAD','/backend/.env.local')[0],405)
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
