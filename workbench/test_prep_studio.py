import json
import tempfile
import time
import unittest
from pathlib import Path
from flask import Flask
from prep_agent_api import register_prep_agent
from prep_studio_api import register_prep_studio
from prep_context import collect

class StudioTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.app=Flask(__name__);register_prep_agent(self.app,self.root);register_prep_studio(self.app,self.root)
        self.app.config['PREP_CONTEXT_PROVIDER']=lambda i:dict(sources=[dict(source_id='book:synthetic#1',kind='book',text='Synthetic author statement',title='Synthetic book')],books=[],coverage=[dict(kind='books',status='ready')])
        self.app.config['PREP_AGENT_PROVIDER']=lambda c:self.result(c)
        self.client=self.app.test_client()
        self.doc=self.client.post('/api/prep/studio',json={'intent':{'topic':'Synthetic talk','audience':'Synthetic audience','thoughts':'Synthetic intention','duration_minutes':60}}).json
        self.pid=self.doc['preparation_id']
    def tearDown(self):self.tmp.cleanup()
    def result(self,ctx):
        if 'outline' in ctx:return dict(title='Script',sections=[dict(title='Part',minutes=60,script='Synthetic rehearsal text. '*8,source_ids=['book:synthetic#1'])],rehearsal_notes=['Needs rehearsal'])
        if 'confirmed_text' in ctx:return dict(title='Outline',central_question='Question',sections=[dict(title='Part',minutes=60,purpose=ctx['confirmed_text'],transition='Next',source_ids=['book:synthetic#1'],page_ids=[],missing_material='New oral material',interaction='Discussion')],tradeoffs=[])
        return dict(why_this_talk='Why',speaker_position='Position',audience_tension='Tension',desired_change='Change',questions=[],boundaries=[],evidence=[dict(point='Synthetic point',kind='supported',source_ids=['book:synthetic#1'])])
    def latest(self):return self.client.get('/api/prep/studio/'+self.pid).json
    def generate(self,stage):
        self.doc=self.latest();r=self.client.post('/api/prep/studio/'+self.pid+'/generate',json={'base_revision':self.doc['revision'],'stage':stage})
        if r.status_code!=202:return r
        for _ in range(100):
            self.doc=self.latest()
            if self.doc['job']['status']!='running':return self.doc
            time.sleep(.01)
        self.fail('Background job did not finish')
    def confirm(self,text='Corrected human intent',confirm=True):
        self.doc=self.latest();return self.client.put('/api/prep/studio/'+self.pid+'/understanding',json={'base_revision':self.doc['revision'],'text':text,'confirm':confirm})
    def test_confirmation_gate_and_full_roundtrip(self):
        self.assertEqual(self.generate('outline').status_code,400)
        self.assertEqual(self.generate('understanding')['job']['status'],'succeeded')
        self.assertEqual(self.confirm().status_code,200)
        d=self.generate('outline');self.assertEqual(d['outline']['sections'][0]['purpose'],'Corrected human intent')
        d=self.generate('manuscript');self.assertIn('manuscript',d)
        self.assertIn('Synthetic rehearsal',self.client.get('/api/prep/studio/'+self.pid+'/export').text)
        d=self.confirm('Changed again',False).json;self.assertNotIn('outline',d);self.assertNotIn('manuscript',d);self.assertFalse(d['confirmed'])
        self.assertGreater(len(list((self.root/'data/preparations'/self.pid).glob('[0-9]*.json'))),5)
    def test_invalid_citations_never_saved(self):
        self.app.config['PREP_AGENT_PROVIDER']=lambda c:dict(self.result(c),evidence=[dict(point='Invented',kind='supported',source_ids=['unknown'])])
        d=self.generate('understanding');self.assertEqual(d['job']['status'],'failed');self.assertNotIn('understanding',d)
    def test_fake_quote_rejected(self):
        self.app.config['PREP_AGENT_PROVIDER']=lambda c:dict(self.result(c),evidence=[dict(point='Point',kind='supported',source_ids=['book:synthetic#1'],quote='Not in the source')])
        self.assertEqual(self.generate('understanding')['job']['status'],'failed')
    def test_stale_edits_do_not_overwrite(self):
        self.generate('understanding');self.confirm()
        r=self.client.put('/api/prep/studio/'+self.pid+'/understanding',json={'base_revision':1,'text':'stale','confirm':True})
        self.assertEqual(r.status_code,409);self.assertEqual(self.latest()['confirmed_text'],'Corrected human intent')
    def test_time_budget_adjustment_is_explicit(self):
        self.generate('understanding');self.confirm()
        original=self.result
        def bad(c):
            r=original(c);r['sections'][0]['minutes']=61;return r
        self.app.config['PREP_AGENT_PROVIDER']=bad
        d=self.generate('outline');self.assertEqual(d['job']['status'],'succeeded');self.assertEqual(d['outline']['sections'][0]['minutes'],60);self.assertEqual(d['outline']['timing_adjustment']['model_total_minutes'],61)
    def test_source_outage_not_fabricated(self):
        self.app.config['PREP_CONTEXT_PROVIDER']=lambda i:dict(sources=[],books=[],coverage=[dict(kind='shennao',status='unavailable')])
        d=self.generate('understanding');self.assertEqual(d['job']['status'],'failed');self.assertNotIn('understanding',d)
    def test_changed_intent_invalidates_prior_work(self):
        self.generate('understanding');self.confirm();self.generate('outline');self.generate('manuscript')
        d=self.latest();intent=dict(d['intent'],topic='Changed topic')
        r=self.client.put('/api/prep/studio/'+self.pid+'/intent',json={'base_revision':d['revision'],'intent':intent})
        self.assertEqual(r.status_code,200);self.assertNotIn('understanding',r.json);self.assertNotIn('manuscript',r.json);self.assertFalse(r.json['confirmed'])
    def test_unknown_speaker_cannot_become_author_evidence(self):
        self.app.config['PREP_CONTEXT_PROVIDER']=lambda i:dict(sources=[dict(source_id='book:synthetic#1',kind='transcript',attribution='other_or_unknown_speaker',text='Synthetic statement',title='Synthetic conversation')],books=[],coverage=[])
        self.assertEqual(self.generate('understanding')['job']['status'],'failed')
    def test_manuscript_edit_persists_without_confirming_author(self):
        self.generate('understanding');self.confirm();self.generate('outline');self.generate('manuscript')
        d=self.latest();m=d['manuscript'];m['sections'][0]['script']='Revised rehearsal text. '*8
        r=self.client.put('/api/prep/studio/'+self.pid+'/manuscript',json={'base_revision':d['revision'],'manuscript':m})
        self.assertEqual(r.status_code,200);self.assertEqual(self.latest()['manuscript_review'],'human_edited_pending')
        self.assertIn('Revised rehearsal',self.client.get('/api/prep/studio/'+self.pid+'/export').text)
    def test_assembly_requires_real_selected_pages(self):
        self.generate('understanding');self.confirm();self.generate('outline')
        d=self.latest();r=self.client.post('/api/prep/studio/'+self.pid+'/assemble',json={'base_revision':d['revision']})
        self.assertEqual(r.status_code,400);self.assertNotIn('assembly_id',self.latest())

    def test_refresh_invalidates_old_confirmed_content_even_when_new_job_fails(self):
        self.generate('understanding');self.confirm();self.generate('outline')
        self.app.config['PREP_CONTEXT_PROVIDER']=lambda i:dict(sources=[],books=[],coverage=[])
        d=self.generate('understanding');self.assertFalse(d['confirmed']);self.assertNotIn('understanding',d);self.assertNotIn('outline',d)
    def test_history_is_readable_without_overwriting_current(self):
        self.generate('understanding');self.confirm()
        revision=self.latest()['revision']
        old=self.client.get('/api/prep/studio/'+self.pid+'?revision=1').json
        self.assertEqual(old['revision'],1);self.assertEqual(self.latest()['revision'],revision)
        h=self.client.get('/api/prep/studio/'+self.pid+'/history').json['history'];self.assertEqual(h[-1]['revision'],1)

    def test_book_catalog_and_section_status(self):
        self.app.config.pop('PREP_CONTEXT_PROVIDER')
        index=self.root/'books.json';index.write_text(json.dumps({'books':[{'slug':'synthetic','name':'Synthetic','status':'online','sections':[{'sid':'book:synthetic#1','text':'education growth','chapter':'Test'}]}]}))
        self.app.config['PREP_BOOKS_INDEX']=str(index)
        c=collect(self.app,self.root,{'topic':'education'})
        self.assertEqual(c['sources'][0]['publication_status'],'online');self.assertEqual(c['coverage'][1]['status'],'unavailable')

if __name__=='__main__':unittest.main()
