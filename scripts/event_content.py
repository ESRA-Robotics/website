"""Validate untrusted issue content before it can enter the static catalogue."""
from datetime import datetime
import json
import re
from urllib.parse import urlsplit

FIELDS={'title':(1,160),'organiser':(1,160),'location':(1,160),
        'description':(40,4000),'relevance':(30,1500)}
ACK='I am authorised to submit this public event and agree to the ESRA event guidelines.'

def parse_submission(body, types, issue_number):
    if not isinstance(body,str) or len(body)>16000:raise ValueError('Submission is missing or too large')
    section=re.search(r'### Event details\s+```json\s*\n(.*?)\n```',body,re.S)
    if not section:raise ValueError('Use the website submission helper or the event issue form')
    if ACK not in body:raise ValueError('The submission acknowledgement is missing')
    data=json.loads(section[1])
    if not isinstance(data,dict):raise ValueError('Event details must be a JSON object')
    clean={}
    for field,(minimum,maximum) in FIELDS.items():
        value=data.get(field)
        if not isinstance(value,str) or not minimum<=len(value.strip())<=maximum:raise ValueError('Check '+field)
        clean[field]=value.strip().replace('\r\n','\n').replace('\r','\n')
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',clean[field]):raise ValueError('Invalid control character in '+field)
    for field in ('title','organiser','location'):
        if re.search(r'[\x00-\x1f\x7f]',clean[field]):raise ValueError('Use plain text for '+field)
    if data.get('type') not in types:raise ValueError('Unsupported event type')
    clean['type']=data['type']
    url=data.get('url','')
    if not isinstance(url,str) or len(url)>1000:raise ValueError('Check the event URL')
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or re.search(r'[\x00-\x20]',url):raise ValueError('Use a public HTTPS event URL')
    try:parsed.port
    except ValueError:raise ValueError('Invalid HTTPS event URL port')
    clean['url']=url
    try:
        start=datetime.fromisoformat(data['start']);end=datetime.fromisoformat(data['end'])
        if not start.tzinfo or not end.tzinfo or end<start or (end-start).days>365:raise ValueError()
    except (ValueError,KeyError,TypeError):raise ValueError('Use valid ISO dates with timezone offsets')
    clean.update(start=start.isoformat(),end=end.isoformat(),id=f'community-issue-{int(issue_number)}',original=False)
    # Relevance is moderation context, not public marketing copy.
    clean.pop('relevance')
    return clean
