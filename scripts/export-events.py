#!/usr/bin/env python3
"""Optionally export the static events site for events.esrarobotics.eu.

The normal GitHub Pages site needs no build: /events/ works directly.
This helper only prepares a second Pages repository's deploy directory.
"""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path, help='A new, empty output directory')
args = parser.parse_args()
out = args.output.resolve()
if out.exists() and (not out.is_dir() or any(out.iterdir())):
    parser.error('Output must be absent or an empty directory; nothing will be overwritten.')
if out == ROOT or ROOT in out.parents:
    parser.error('Choose an output directory outside the source checkout.')
out.mkdir(parents=True, exist_ok=True)
shutil.copytree(ROOT / 'assets', out / 'assets')
shutil.copytree(ROOT / 'events', out / 'events')
for page in (out / 'events').rglob('*.html'):
    text = page.read_text()
    # Organisation and legal navigation always return to the main site.
    for href in ['/', '/#home', '/#whatwedo', '/#mission', '/#partners',
                 '/#partners-1', '/imprint/', '/imprint/#privacy']:
        text = text.replace(f'href="{href}"', f'href="https://esrarobotics.eu{href}"')
    page.write_text(text)
# Keep /events/ as an alias so the shared event links work on either host.
shutil.copyfile(out / 'events/index.html', out / 'index.html')
(out / 'CNAME').write_text('events.esrarobotics.eu\n')
(out / '.nojekyll').touch()
print(f'Exported events site to {out}')
print('Main-site CNAME was not changed. Configure a separate Pages site and DNS to deploy.')
