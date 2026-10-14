import json,tempfile,unittest
from pathlib import Path
from flask import Flask
from prep_agent_api import register_prep_agent
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name);self.a='assembly-'+'a'*32
  d=self.r/'data/assemblies'/self.a;d.mkdir(parents=True);(d/'00000001.json').write_text(json.dumps({'revision':1,'entries':[]}))
  c=self.r/'catalog';c.mkdir();(c/'catalog.json').write_text(json.dumps({'pages':[{'page_id':'p1','page_number':1}]}))
  self.app=Flask(__name__);self.app.config['ASSEMBLY_CATALOG_DIR']=str(c);register_prep_agent(self.app,self.r);self.client=self.app.test_client()
 def tearDown(self):self.t.cleanup()
 def body(self):return {'assembly_id':self.a,'base_revision':1,'intent':{'thoughts':'组织变革'}}
 def result(self,p='p1'):return {'title':'课','chapters':[{'title':'章','entries':[{'page_id':p,'minutes':5,'reason':'选页理由','speaker_notes':'建议'}]}]}
 def test_unavailable(self):self.assertEqual(self.client.post('/api/prep/proposals',json=self.body()).status_code,503)
 def test_saved_without_mutation(self):
  self.app.config['PREP_AGENT_PROVIDER']=lambda c:self.result();r=self.client.post('/api/prep/proposals',json=self.body());self.assertEqual(r.status_code,201);self.assertEqual(self.client.get('/api/prep/proposals/'+r.json['proposal_id']).json['status'],'pending');self.assertEqual(len(list((self.r/'data/assemblies'/self.a).glob('*.json'))),1)
 def test_hallucinated_id(self):
  self.app.config['PREP_AGENT_PROVIDER']=lambda c:self.result('fake');self.assertEqual(self.client.post('/api/prep/proposals',json=self.body()).status_code,502)
 def test_stale(self):
  self.app.config['PREP_AGENT_PROVIDER']=lambda c:self.result();b=self.body();b['base_revision']=0;self.assertEqual(self.client.post('/api/prep/proposals',json=b).status_code,409)
