import unittest,tempfile,json
from pathlib import Path
from flask import Flask
from workspace_tools import register_tools,read_store,title_override
class ToolsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);g=self.root/'generated';g.mkdir();self.source={'pages':[{'page_id':'p','atomic_id':'atom-0001','deck_id':'d','title':'original'}],'decks':[{'deck_id':'d'}]};(g/'catalog.json').write_text(json.dumps(self.source));self.app=Flask(__name__);self.app.config['ASSEMBLY_CATALOG_DIR']=str(g);register_tools(self.app,self.root);self.c=self.app.test_client()
 def tearDown(self):self.tmp.cleanup()
 def test_title_conflict_history_and_source_preserved(self):
  r=self.c.put('/api/library/titles/p',json={'title':'new','base_revision':0});self.assertEqual(r.status_code,200);self.assertEqual(title_override(self.root,'atom-0001')['title'],'new');self.assertEqual(self.c.put('/api/library/titles/p',json={'title':'stale','base_revision':0}).status_code,409);self.assertEqual(len(read_store(self.root)['title_history']),1);self.assertEqual(json.loads((self.root/'generated/catalog.json').read_text()),self.source)
 def test_blocked_job_is_idempotent_not_dispatched(self):
  body={'deck_id':'d','stage':'html'};r=self.c.post('/api/processing/tasks',json=body);self.assertEqual(r.status_code,201);self.assertEqual(r.json['job']['status'],'blocked');r=self.c.post('/api/processing/tasks',json=body);self.assertTrue(r.json['duplicate']);self.assertEqual(len(read_store(self.root)['jobs']),1)
 def test_invalid_input(self):
  self.assertEqual(self.c.put('/api/library/titles/no',json={'title':'x','base_revision':0}).status_code,404);self.assertEqual(self.c.post('/api/processing/tasks',json={'deck_id':'no','stage':'html'}).status_code,404)
