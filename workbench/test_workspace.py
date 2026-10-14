import importlib.util,tempfile,json,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('server',Path(__file__).with_name('workspace_server.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class WorkspaceTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'data').mkdir();self.page={'page_id':'p1','page_number':1,'source_sha256':'abc','html_sha256':'baseline','html':'original.html'}
  (self.root/'data/annotations.json').write_text(json.dumps({'pages':[self.page]}));self.client=m.create_app(self.root).test_client();self.html='<html><head><meta name="source-sha256" content="abc"><meta name="source-page" content="1"><meta name="source-version-sha256" content="baseline"></head><body><main data-page-id="p1">测试</main></body></html>'
  (self.root/'original.html').write_text(self.html)
 def tearDown(self):self.tmp.cleanup()
 def test_revision_conflict_keeps_original(self):
  r=self.client.post('/api/revisions/p1',json={'html':self.html,'base_sha256':'baseline'});self.assertEqual(r.status_code,201)
  r=self.client.post('/api/revisions/p1',json={'html':self.html+'x','base_sha256':'baseline'});self.assertEqual(r.status_code,409)
  state=self.client.get('/api/workspace').json;self.assertEqual(len(state['revisions']['p1']),1)
 def test_old_export_rejected_after_reopening_workspace(self):
  exported=self.client.get('/api/export/p1').get_data(as_text=True)
  first=self.client.post('/api/revisions/p1',json={'html':exported.replace('测试','第一次编辑')})
  self.assertEqual(first.status_code,201)
  # A new client reads current state; it must not relabel old bytes with current base.
  reopened=m.create_app(self.root).test_client()
  current=reopened.get('/api/workspace').json['revisions']['p1'][-1]['sha256']
  stale=reopened.post('/api/revisions/p1',json={'html':exported.replace('测试','旧文件编辑'),'base_sha256':current})
  self.assertEqual(stale.status_code,409)
  self.assertEqual(len(reopened.get('/api/workspace').json['revisions']['p1']),1)
  fresh=reopened.get('/api/export/p1').get_data(as_text=True)
  self.assertIn('content="'+current+'"',fresh)
  self.assertEqual(fresh.count('name="source-version-sha256"'),1)
  unchanged=reopened.post('/api/revisions/p1',json={'html':fresh})
  self.assertEqual(unchanged.status_code,200)
  self.assertTrue(unchanged.json['unchanged'])
  second=reopened.post('/api/revisions/p1',json={'html':fresh.replace('第一次编辑','第二次编辑')})
  self.assertEqual(second.status_code,201)
  self.assertEqual(second.json['parent_sha256'],current)
 def test_missing_version_or_forged_session_rejected(self):
  missing=self.html.replace('<meta name="source-version-sha256" content="baseline">','')
  self.assertEqual(self.client.post('/api/revisions/p1',json={'html':missing,'base_sha256':'baseline'}).status_code,400)
  forged=self.html.replace('</head>','<meta name="slide-library-session" content="forged"></head>')
  self.assertEqual(self.client.post('/api/revisions/p1',json={'html':forged}).status_code,400)
 def test_foreign_source_and_active_content_rejected(self):
  for html in [self.html.replace('abc','wrong'),self.html+'<script>alert(1)</script>',self.html+'<img src="https://example.com/x">',self.html+'<style>@import "evil";</style>']:
   self.assertEqual(self.client.post('/api/revisions/p1',json={'html':html,'base_sha256':'baseline'}).status_code,400)
 def test_collection_validation_and_persistence(self):
  self.assertEqual(self.client.post('/api/collection',json={'pages':['p1','p1']}).json['collection'],['p1'])
  self.assertEqual(self.client.post('/api/collection',json={'pages':['missing']}).status_code,400)
  self.assertEqual(self.client.get('/api/workspace').json['collection'],['p1'])
 def test_cross_origin_rejected(self):
  self.assertEqual(self.client.post('/api/collection',json={'pages':['p1']},headers={'Origin':'https://example.com'}).status_code,403)
if __name__=='__main__':unittest.main()
