import hashlib,json,tempfile,unittest
from pathlib import Path
from center import create_app
class API:
 def get(self,path):return {'courses':[{'deck_id':'synthetic-course','title':'Synthetic','page_count':1}]}
class CenterTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.client=create_app(self.root,API()).test_client();self.client.set_cookie('mcp_center_csrf','test-csrf');self.headers={'Origin':'https://qiuyiwu.com','X-CSRF-Token':'test-csrf'}
 def tearDown(self):self.tmp.cleanup()
 def test_lifecycle_and_no_plaintext(self):
  r=self.client.post('/api/keys',json={'name':'Synthetic agent','allowed_decks':['synthetic-course'],'days':7},headers=self.headers)
  self.assertEqual(r.status_code,201);key=r.json['key'];cid=r.json['client_id'];data=json.loads((self.root/'clients.json').read_text());self.assertNotIn(key,json.dumps(data));self.assertEqual(data['clients'][0]['token_sha256'],hashlib.sha256(key.encode()).hexdigest());listed=self.client.get('/api/keys').get_json();self.assertNotIn('token_sha256',str(listed));self.assertNotIn(key,str(listed));self.assertEqual(self.client.post('/api/keys/'+cid+'/revoke',json={},headers=self.headers).status_code,200);self.assertTrue(json.loads((self.root/'clients.json').read_text())['clients'][0]['revoked'])
 def test_csrf_scope_and_no_unintegrated_issuance(self):
  self.assertEqual(self.client.post('/api/keys',json={}).status_code,403)
  self.assertEqual(self.client.post('/api/keys',json={'name':'X','allowed_decks':['unknown']},headers=self.headers).status_code,400)
  self.assertEqual(self.client.post('/api/keys',json={'service':'unknown'},headers=self.headers).status_code,400)
 def test_directory(self):
  r=self.client.post('/api/services',json={'name':'Synthetic','url':'https://example.com/mcp'},headers=self.headers);self.assertEqual(r.status_code,201);self.assertFalse(r.json['service']['key_management'])
 def test_no_cache(self):self.assertEqual(self.client.get('/api/services').headers['Cache-Control'],'no-store')
if __name__=='__main__':unittest.main()
