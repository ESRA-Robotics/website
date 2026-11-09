"""Offline tests: no issues, PRs, notifications or email are created."""
from datetime import datetime
from importlib.util import spec_from_file_location, module_from_spec
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree.ElementTree import fromstring
from event_content import parse_submission, ACK

def module(name):
    spec=spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=module_from_spec(spec);spec.loader.exec_module(m);return m
feeds=module('build-event-feeds');review=module('prepare-event-review')

class StaticEvents(unittest.TestCase):
    def setUp(self):
        self.event={'title':'Robotics workshop <2027>','organiser':'Example Club','location':'Munich, Germany','type':'Workshops','start':'2027-02-01T10:00:00+01:00','end':'2027-02-01T18:00:00+01:00','url':'https://example.org/event','description':'A workshop for European robotics students. Free entry and English language.','relevance':'A technical exchange for the European student robotics community.'}
        self.types=['Trips','Workshops']
    def body(self,event=None):return '### Event details\n\n```json\n'+json.dumps(event or self.event)+'\n```\n\n### Review acknowledgement\n\n'+ACK
    def test_untrusted_fields_cannot_publish_private_data_or_original_status(self):
        event=parse_submission(self.body({**self.event,'original':True,'email':'private@example.org','id':'china-trip-2027'}),self.types,42)
        self.assertFalse(event['original']);self.assertEqual(event['id'],'community-issue-42');self.assertNotIn('email',event);self.assertNotIn('relevance',event)
    def test_invalid_submissions_are_rejected(self):
        for override in [{'type':'Spam'},{'url':'javascript:alert(1)'},{'url':'https://example.org:invalid/'},{'description':'Bad control character '+chr(1)+' and enough text for a long description.'},{'url':'https://user:pass@example.org'},{'start':'2027-02-01T10:00:00'},{'end':'2026-01-01T10:00:00Z'},{'title':'Title\nBcc: victim@example.org'}]:
            with self.subTest(override=override),self.assertRaises(ValueError):parse_submission(self.body({**self.event,**override}),self.types,42)
        with self.assertRaises(ValueError):parse_submission(self.body().replace(ACK,''),self.types,42)
    def test_review_produces_only_catalogue_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'events').mkdir();path=root/'events/catalog.json';path.write_text(json.dumps({'types':self.types,'events':[]}))
            issue={'number':42,'title':'[Event] Workshop','body':self.body()}
            review.prepare(root,issue)
            self.assertEqual(len(json.loads(path.read_text())['events']),1)
            with self.assertRaises(ValueError):review.prepare(root,issue)
            self.assertEqual([p.name for p in root.iterdir()],['events'])
    def test_rss_is_escaped_and_topic_and_club_feeds_are_distinct(self):
        event=parse_submission(self.body(),self.types,42)
        catalog={'types':self.types,'events':[event]};files=feeds.outputs(catalog)
        root=fromstring(files['workshops-community.xml'])
        self.assertEqual(root.find('channel/item/title').text,self.event['title'])
        self.assertIsNone(fromstring(files['trips-all.xml']).find('channel/item'))
        self.assertIsNone(fromstring(files['workshops-original.xml']).find('channel/item'))
        index=json.loads(files['index.json']);self.assertEqual(index['clubs'][0]['name'],'Example Club')
    def test_calendar_escapes_and_folds_utf8_lines(self):
        event=parse_submission(self.body(),self.types,42);event['description']='é'*150+';line\nnext'
        calendar=feeds.calendar([event])
        self.assertTrue(all(len(line.encode())<=75 for line in calendar.split('\r\n')))
        self.assertIn('DTSTART:20270201T090000Z',calendar)
        self.assertIn('LOCATION:Munich\\, Germany',calendar)
    def test_retired_club_feed_urls_remain_valid_but_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'events').mkdir();path=root/'events/catalog.json'
            event=parse_submission(self.body(),self.types,42)
            path.write_text(json.dumps({'types':self.types,'events':[event]}));feeds.build(root)
            old=json.loads((root/'events/feeds/index.json').read_text())['clubs'][0]['rss'].split('/')[-1]
            path.write_text(json.dumps({'types':self.types,'events':[]}));feeds.build(root);feeds.build(root,check=True)
            self.assertIsNone(fromstring((root/'events/feeds'/old).read_text()).find('channel/item'))

if __name__=='__main__':unittest.main()
