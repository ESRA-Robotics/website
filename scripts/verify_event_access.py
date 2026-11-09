"""Check the mail gateway's ESRA-domain attestation before preparing a publication PR."""
import base64
from hashlib import sha256
import hmac
import json
import re
import time

def verify_issue(body,secret):
    if not secret or len(secret)<32:raise ValueError('Configure EVENT_SUBMISSION_SECRET before enabling organiser review')
    match=re.search(r'### ESRA verification\s+([A-Za-z0-9_.-]+)',body or '')
    if not match:raise ValueError('Submit using the verified ESRA organiser form')
    try:
        encoded,signature=match[1].split('.')
        actual=base64.urlsafe_b64decode(signature+'='*(-len(signature)%4))
        expected=hmac.new(secret.encode(),encoded.encode(),sha256).digest()
        if not hmac.compare_digest(actual,expected):raise ValueError()
        proof=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        details=re.search(r'### Event details\s+```json\s*\n(.*?)\n```',body,re.S)
        if proof['purpose']!='event-submission' or proof['domain']!='esrarobotics.eu' or proof['expires']<=time.time():raise ValueError()
        if not details or proof['event']!=json.loads(details[1]):raise ValueError()
    except (ValueError,KeyError,TypeError):raise ValueError('Missing, altered or expired ESRA verification')
    return True
