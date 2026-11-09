#!/usr/bin/env python3
"""Prepare a reviewed issue as a static catalogue update; never publish it directly."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from event_content import parse_submission

ROOT=Path(__file__).resolve().parents[1]

def prepare(root, issue):
    if issue.get('pull_request') or not str(issue.get('title','')).startswith('[Event] '):raise ValueError('Use an event submission issue')
    catalog_path=root/'events/catalog.json';catalog=json.loads(catalog_path.read_text())
    event=parse_submission(issue.get('body'),catalog['types'],issue['number'])
    if any(e['id']==event['id'] for e in catalog['events']):raise ValueError('This issue already has a published event; edit its existing listing instead')
    now=datetime.now(timezone.utc).isoformat()
    event['published']=now;catalog['updated']=now;catalog['events'].append(event)
    catalog_path.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n')
    return event

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('issue_file',type=Path);args=parser.parse_args()
    event=prepare(ROOT,json.loads(args.issue_file.read_text()))
    subprocess.run(['python3',str(ROOT/'scripts/build-event-feeds.py')],cwd=ROOT,check=True)
    print('Prepared catalogue and feeds for '+event['id'])
