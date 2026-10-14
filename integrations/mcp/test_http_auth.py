import hashlib,json,tempfile,time,unittest
from pathlib import Path
from http_server import ClientAuth
from test_bridge import FakeAPI
class HTTPAuthTest(unittest.TestCase):
 def test_key_scope_expiry_revocation(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'clients.json';record={'client_id':'synthetic','token_sha256':hashlib.sha256(b'test-only-key').hexdigest(),'allowed_decks':['allowed'],'expires_at':time.time()+60}
   path.write_text(json.dumps({'clients':[record]}));auth=ClientAuth(None,path,FakeAPI())
   self.assertIsNone(auth.resolve(''));self.assertIsNone(auth.resolve('Bearer invalid'))
   b=auth.resolve('Bearer test-only-key');self.assertEqual(len(b.list_collections()),1)
   with self.assertRaises(ValueError):b.read_content('secret')
   record['expires_at']=0;path.write_text(json.dumps({'clients':[record]}));self.assertIsNone(auth.resolve('Bearer test-only-key'))
   record['expires_at']=time.time()+60;record['revoked']=True;path.write_text(json.dumps({'clients':[record]}));self.assertIsNone(auth.resolve('Bearer test-only-key'))
if __name__=='__main__':unittest.main()
