import base64,unittest
from bridge import Bridge,API
class FakeAPI:
    def get(self,path):
        if path.startswith('/api/prep/courses'):return {'courses':[{'deck_id':'allowed','title':'A'},{'deck_id':'secret','title':'S'}]}
        if path.startswith('/api/library?'):return {'total':1,'pages':[{'page_id':'p','deck_id':'allowed','title':'A'}]}
        return {'page_id':'p','deck_id':'secret' if path.endswith('secret') else 'allowed','annotation':{'source_text':'original','summary':'AI summary'},'image':{'url':'/images/p.jpg','status':'local_exists'},'navigation':{}}
    def fetch(self,path):return b'image','image/jpeg'
class BridgeTests(unittest.TestCase):
    def setUp(self):self.b=Bridge(FakeAPI(),['allowed'])
    def test_scoped_collections(self):self.assertEqual(len(self.b.list_collections()),1)
    def test_direct_access_denied(self):
        with self.assertRaises(ValueError):self.b.read_content('secret')
    def test_search_denied(self):
        with self.assertRaises(ValueError):self.b.search_content(collection_id='secret')
    def test_permission_and_semantics(self):
        r=self.b.read_content('p');self.assertEqual(r['slide_text'],'original');self.assertIsNone(r['speaker_quote']);self.assertIn('unknown',r['usage_permission'])
    def test_download_opt_in(self):
        with self.assertRaises(ValueError):self.b.get_asset('p','image')
        self.b.asset_download=True;self.assertEqual(base64.b64decode(self.b.get_asset('p','image')['data_base64']),b'image')
    def test_local_api_only(self):
        for url in ['https://example.com','http://127.0.0.1@evil.com','file:///tmp/x']:
            with self.assertRaises(ValueError):API(url)
    def test_explicit_scope(self):
        with self.assertRaises(ValueError):Bridge(FakeAPI(),[])
if __name__=='__main__':unittest.main()
