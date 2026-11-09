#!/usr/bin/env python3
"""Keep standalone event-page headers/footers consistent; no build is required.
Edit templates/events/*.html, run this helper, and commit the resulting HTML.
Use --check in CI to detect drift without writing files.
"""
import argparse
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check',action='store_true')
args=parser.parse_args()
changed=[]
for page in sorted((ROOT/'events').rglob('index.html')):
    text=page.read_text();original=text
    for part in ('header','footer'):
        template=(ROOT/'templates/events'/f'{part}.html').read_text().rstrip('\n')
        template=template.replace('{{events_current}}',' aria-current="page"' if page==ROOT/'events/index.html' else '')
        pattern=re.compile(r'    <'+part+r'\b.*?</'+part+'>',re.S)
        text,count=pattern.subn(lambda _:template,text)
        if count!=1:raise SystemExit(f'Expected one {part} in {page.relative_to(ROOT)}')
    if original!=text:
        changed.append(str(page.relative_to(ROOT)))
        if not args.check:page.write_text(text)
if args.check and changed:raise SystemExit('Event shell drift: '+', '.join(changed))
print(('Checked' if args.check else 'Updated')+' event page shells'+(': '+', '.join(changed) if changed else ': consistent'))
