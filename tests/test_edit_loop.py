import sys, tempfile, json, unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
from edit_loop import patch_page, create_app

class EditLoopTest(unittest.TestCase):
 def base(self):
  return {'atom_id':'synthetic','canvas_size':[320,180],'revision':1,'version_id':'v1','objects':[{'object_id':'o1','text':'Hello','layout':{'font':'Synthetic','size':12}}], 'html':'<span data-lp-object-id="o1" style="left:1cqw;top:2cqw;font-size:3cqw;color:#000000">Hello</span>'}
 def test_patch_preserves_identity_and_escapes_markup(self):
  source=self.base();changed=patch_page(source,[{'object_id':'o1','text':'<script>','font_size':24}])
  self.assertIn('&lt;script&gt;',changed['html']);self.assertIn('font-size:7.500000cqw',changed['html'])
  self.assertEqual(source['objects'][0]['text'],'Hello')
  with self.assertRaises(ValueError):patch_page(source,[{'object_id':'unknown','text':'bad'}])
 def test_subset_rebuilds_each_actual_font(self):
  source=self.base();source['objects'].append({'object_id':'o2','text':'Other','layout':{'font':'Second','size':12}})
  source['html']='@font-face{font-family:f0;src:url(data:font/woff2;base64,old0)}@font-face{font-family:f1;src:url(data:font/woff2;base64,old1)}'+source['html']+'<span data-lp-object-id="o2" style="left:1cqw;top:2cqw;font-size:3cqw;color:#000000">Other</span>'
  source['font_faces']={'Synthetic':{'path':'first','css_family':'f0'},'Second':{'path':'second','css_family':'f1'}}
  calls=[]
  def payload(path,text):calls.append((path,text));return ('new'+path,.8)
  with patch.dict(sys.modules,{'source_scene':SimpleNamespace(font_payload=payload)}):
   changed=patch_page(source,[{'object_id':'o2','text':'New glyphs'}])
  self.assertEqual(calls,[('first','Hello'),('second','New glyphs')])
  self.assertIn('base64,newsecond',changed['html'])
 def test_append_reload_conflict_and_origin(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'versions').mkdir();p=root/'versions/00000001.json';p.write_text(json.dumps(self.base()));old=p.read_bytes()
   client=create_app(root).test_client();kw={'base_url':'http://127.0.0.1:5320','headers':{'Origin':'http://127.0.0.1:5320'}}
   body={'base_version_id':'v1','operations':[{'object_id':'o1','text':'Changed'}]}
   self.assertEqual(client.post('/api/save',json=body,**kw).status_code,200)
   self.assertEqual(client.post('/api/save',json=body,**kw).status_code,409)
   self.assertEqual(client.get('/api/state',base_url=kw['base_url']).json['objects'][0]['text'],'Changed')
   self.assertEqual(p.read_bytes(),old)
   self.assertEqual(client.post('/api/save',json=body,base_url=kw['base_url'],headers={'Origin':'https://elsewhere.invalid'}).status_code,403)
if __name__=='__main__':unittest.main()
