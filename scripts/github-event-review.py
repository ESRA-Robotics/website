#!/usr/bin/env python3
"""GitHub Actions entry point. Only trusted repository collaborators can prepare updates."""
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote
from verify_event_access import verify_issue

ROOT=Path(__file__).resolve().parents[1]
def run(*args,**kwargs):return subprocess.run(args,cwd=ROOT,text=True,check=True,**kwargs)
def api(path,method='GET',data=None):
    args=['gh','api','--method',method,path]
    if data is not None:args+=['--input','-']
    return json.loads(run(*args,input=json.dumps(data) if data is not None else None,capture_output=True).stdout)

def main():
    repo=os.environ['GITHUB_REPOSITORY'];actor=os.environ['GITHUB_ACTOR']
    permission=api(f'repos/{repo}/collaborators/{quote(actor,safe="")}/permission')['permission']
    if permission not in ('write','maintain','admin'):raise SystemExit('A repository maintainer must run event review')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch':
        number=int(event['inputs']['issue_number']);decision=event['inputs']['decision']
    else:
        number=int(event['issue']['number']);decision={'event:reviewed':'prepare','event:declined':'decline'}.get(event['label']['name'])
    if number<=0 or decision not in ('prepare','decline'):raise SystemExit('Invalid review request')
    issue=api(f'repos/{repo}/issues/{number}')
    if not issue.get('title','').startswith('[Event] ') or issue.get('pull_request'):raise SystemExit('Not an event submission issue')
    if decision=='decline':
        api(f'repos/{repo}/issues/{number}','PATCH',{'state':'closed','state_reason':'not_planned'})
        print('Submission declined on GitHub. No website content changed.');return
    if issue.get('state')!='open':raise SystemExit('Reopen the issue before preparing a new event update')
    verify_issue(issue.get('body'),os.environ.get('EVENT_SUBMISSION_SECRET',''))
    path=Path(os.environ['RUNNER_TEMP'])/'event-issue.json';path.write_text(json.dumps(issue))
    run('python3','scripts/prepare-event-review.py',str(path))
    run('python3','scripts/check.py')
    branch=f'events/submission-{number}'
    exists=run('git','ls-remote','--heads','origin',branch,capture_output=True).stdout.strip()
    if exists:raise SystemExit('A review branch already exists; inspect it rather than overwriting it')
    run('git','switch','-c',branch)
    run('git','config','user.name','ESRA event review')
    run('git','config','user.email','github-actions[bot]@users.noreply.github.com')
    run('git','add','events/catalog.json','events/feeds')
    run('git','commit','-m',f'Prepare community event from issue #{number}')
    run('git','push','origin',branch)
    body=Path(os.environ['RUNNER_TEMP'])/'event-pr-body.txt'
    body.write_text(f'Review the submitted organiser, location, dates, public URL and ESRA relevance before merging.\n\nThis updates only the static event catalogue and feeds. Merging publishes through the existing main-branch GitHub Pages setup.\n\nCloses #{number}\n')
    run('gh','pr','create','--draft','--base',event['repository']['default_branch'],'--head',branch,'--title',f'Review event submission #{number}','--body-file',str(body))

if __name__=='__main__':main()
