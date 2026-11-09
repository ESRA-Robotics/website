"""Production API entry point. Serve with a production WSGI host; no static files."""
import json
import os
from urllib.parse import parse_qs
from service import configured_service, Invalid

_service = None

def application(environ, start_response):
    global _service
    if _service is None: _service = configured_service()
    app = _service
    origin = environ.get('HTTP_ORIGIN','')
    headers=[('Content-Type','application/json'),('Cache-Control','no-store'),('Referrer-Policy','no-referrer'),('X-Content-Type-Options','nosniff')]
    if origin in app.origins:
        headers += [('Access-Control-Allow-Origin',origin),('Vary','Origin')]
    def reply(status,data):
        body=json.dumps(data).encode();start_response(status,headers+[('Content-Length',str(len(body)))])
        return [body]
    try:
        method,path=environ['REQUEST_METHOD'],environ.get('PATH_INFO','')
        auth=environ.get('HTTP_AUTHORIZATION','')
        token=auth[7:] if auth.startswith('Bearer ') else ''
        if method=='OPTIONS':
            if origin not in app.origins:return reply('403 Forbidden',{'error':'Origin not allowed'})
            headers.extend([('Access-Control-Allow-Methods','GET, POST, OPTIONS'),('Access-Control-Allow-Headers','Content-Type, Authorization')])
            return reply('200 OK',{})
        if method=='GET':
            if path=='/api/health':result={'ready':bool(app.reviewers),'delivery':app.delivery}
            elif path=='/api/events':result=app.event_page(parse_qs(environ.get('QUERY_STRING','')))
            elif path=='/api/review':result=app.review(token)
            elif path=='/api/preferences':result=app.manage(token)
            else:return reply('404 Not Found',{'error':'Not found'})
        elif method=='POST':
            if origin not in app.origins:return reply('403 Forbidden',{'error':'Origin not allowed'})
            if environ.get('CONTENT_TYPE','').split(';')[0]!='application/json':raise Invalid('Use JSON')
            size=int(environ.get('CONTENT_LENGTH','0'))
            if not 0<size<=20000:raise Invalid('Request too large or empty')
            data=json.loads(environ['wsgi.input'].read(size))
            if not isinstance(data,dict):raise Invalid('Invalid request')
            peer=environ.get('REMOTE_ADDR','unknown')
            # Only enable behind a private, explicitly trusted reverse proxy.
            if os.environ.get('ESRA_TRUST_PROXY')=='1':peer=environ.get('HTTP_X_REAL_IP',peer)
            if path in ('/api/submissions','/api/subscribe'):app.limit(peer,path,10)
            if path=='/api/submissions':result=app.submit(data)
            elif path=='/api/subscribe':result=app.subscribe(data)
            elif path=='/api/review':
                if data.get('action') not in ('accept','decline'):raise Invalid('Choose accept or decline')
                result=app.review(token,data['action'])
            elif path=='/api/confirm':result=app.confirm(token)
            elif path=='/api/preferences':result=app.manage(token,data)
            else:return reply('404 Not Found',{'error':'Not found'})
        else:return reply('405 Method Not Allowed',{'error':'Method not allowed'})
        return reply('200 OK',result)
    except (Invalid,ValueError,TypeError):return reply('400 Bad Request',{'error':'Check your request or reopen the secure email link.'})
    except Exception:return reply('500 Internal Server Error',{'error':'Request could not be completed. Please try again.'})
