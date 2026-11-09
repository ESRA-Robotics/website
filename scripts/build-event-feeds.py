#!/usr/bin/env python3
"""Render committed static RSS/calendar subscriptions. Optional maintenance, no site build."""
import argparse
from datetime import datetime, timezone
from email.utils import format_datetime
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urljoin
from xml.etree.ElementTree import Element, SubElement, tostring

ROOT=Path(__file__).resolve().parents[1]
BASE='https://esrarobotics.eu'

def slug(value):return value.lower().replace(' ','-')
def calendar(events):
    def esc(value):return str(value).replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
    def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ESRA//European Robotics Events//EN','CALSCALE:GREGORIAN']
    for e in events:
        lines+=['BEGIN:VEVENT','UID:'+esc(e['id'])+'@esrarobotics.eu','DTSTAMP:'+stamp(e.get('published','2026-11-09T00:00:00Z')),
                'DTSTART:'+stamp(e['start']),'DTEND:'+stamp(e['end']),'SUMMARY:'+esc(e['title']),
                'LOCATION:'+esc(e['location']),'DESCRIPTION:'+esc(e['organiser']+' · '+e['description']),
                'URL:'+urljoin(BASE,e['url']),'END:VEVENT']
    lines.append('END:VCALENDAR')
    folded=[]
    for line in lines:
        part=''
        for char in line:
            if len((part+char).encode())>75:folded.append(part);part=' '
            part+=char
        folded.append(part)
    return '\r\n'.join(folded)+'\r\n'

def outputs(catalog):
    files={};index={'topics':[],'clubs':[],'networks':{}}
    updated=catalog.get('updated','2026-11-09T00:00:00Z')
    def write(key,title,events):
        channel=Element('channel')
        for tag,value in [('title',title),('link',BASE+'/events/'),('description','Approved European student robotics events.'),('lastBuildDate',format_datetime(datetime.fromisoformat(updated.replace('Z','+00:00')).astimezone(timezone.utc)))]:SubElement(channel,tag).text=value
        for e in sorted(events,key=lambda e:e.get('published',updated),reverse=True)[:100]:
            item=SubElement(channel,'item')
            for tag,value in [('title',e['title']),('link',urljoin(BASE,e['url'])),('description',e['organiser']+' · '+e['location']+' · '+e['start']+' — '+e['description']),('pubDate',format_datetime(datetime.fromisoformat(e.get('published',updated).replace('Z','+00:00')).astimezone(timezone.utc)))]:SubElement(item,tag).text=value
            SubElement(item,'guid',isPermaLink='false').text=e['id']
        root=Element('rss',version='2.0');root.append(channel)
        files[key+'.xml']=tostring(root,encoding='unicode',xml_declaration=True)+'\n'
        files[key+'.ics']=calendar(events)
        return {'rss':'/events/feeds/'+key+'.xml','calendar':'/events/feeds/'+key+'.ics'}
    for origin in ('all','original','community'):
        selected=[e for e in catalog['events'] if origin=='all' or e['original']==(origin=='original')]
        index['networks'][origin]=write('all' if origin=='all' else 'all-'+origin,'ESRA · '+origin+' network events',selected)
    index['all']=index['networks']['all']
    for type in catalog['types']:
        for origin in ('all','original','community'):
            events=[e for e in catalog['events'] if e['type']==type and (origin=='all' or e['original']==(origin=='original'))]
            index['topics'].append({'type':type,'origin':origin,**write(slug(type)+'-'+origin,'ESRA · '+type+' · '+origin,events)})
    for club in sorted({e['organiser'] for e in catalog['events']} | set(catalog.get('_club_names',[]))):
        key='club-'+sha256(club.encode()).hexdigest()[:16]
        index['clubs'].append({'name':club,**write(key,'ESRA network · '+club,[e for e in catalog['events'] if e['organiser']==club])})
    files['index.json']=json.dumps(index,indent=2,ensure_ascii=False)+'\n'
    return files

def build(root=ROOT,check=False):
    target=root/'events/feeds';catalog=json.loads((root/'events/catalog.json').read_text())
    if (target/'index.json').exists():
        catalog['_club_names']=[e['name'] for e in json.loads((target/'index.json').read_text()).get('clubs',[])]
    generated=outputs(catalog)
    if not check:target.mkdir(exist_ok=True)
    for name,content in generated.items():
        path=target/name
        if check:
            if not path.exists() or path.read_bytes()!=content.encode():raise ValueError('Stale feed: '+name)
        else:path.write_bytes(content.encode())
    # Preserve old club URLs as empty feeds rather than 404ing existing subscriptions.
    return generated

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    build(check=args.check);print('Static event feeds verified' if args.check else 'Static event feeds rendered')
