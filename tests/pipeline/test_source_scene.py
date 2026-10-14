import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'workbench'))
import pymupdf
from source_scene import extract_scene,render_scene,preserve_text_regions
from conversion_gate import inspect_slide

class SourceSceneTest(unittest.TestCase):
 def test_graphics_retained_text_is_separate(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.pdf';doc=pymupdf.open();page=doc.new_page(width=320,height=180)
   page.draw_bezier((10,100),(60,20),(110,150),(150,30),color=(1,0,0))
   page.insert_text((20,50),'Hello');doc.save(p)
   s=extract_scene(p,0)
   self.assertIn('<path',s['graphics_svg']);self.assertNotIn('<text',s['graphics_svg'])
   self.assertEqual(s['text'][0]['text'],'Hello');self.assertEqual(s['human_review'],'pending')
 def test_explicit_raster_fallback_keeps_provenance(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.pdf';doc=pymupdf.open();page=doc.new_page(width=320,height=180)
   page.insert_text((20,50),'Hello');doc.save(p)
   scene=extract_scene(p,0);preserve_text_regions(scene,p,[0],'Exact font unavailable')
   output=render_scene(scene,lambda _:self.fail('Fallback must not substitute fonts'))
   self.assertIn('data-editable="false"',output)
   self.assertEqual(scene['text'][0]['text'],'Hello')
   self.assertEqual(scene['text'][0]['source_raster']['source_sha256'],scene['source_sha256'])
 def test_bad_text_is_blocked_before_font_lookup(self):
  with self.assertRaises(ValueError):render_scene({'text':[{'text':'\ue123'}]},lambda _:None)
 def test_gate_never_accepts_and_catches_missing_image(self):
  d=inspect_slide({'blocks':[{'type':'image','src':None},{'type':'text','lines':['\ue123'],'text_conf':.3}]})
  self.assertEqual(d['status'],'blocked');self.assertEqual(d['human_review'],'pending')
  self.assertEqual(inspect_slide({'blocks':[]})['status'],'visual_review_pending')
if __name__=='__main__':unittest.main()
