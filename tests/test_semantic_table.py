import sys,unittest
from pathlib import Path
from html.parser import HTMLParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
from semantic_table import render_table
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.cells=0
 def handle_starttag(self,t,a):
  if t in {'td','th'}:self.cells+=1;self.ids.append(dict(a)['data-lp-cell-id'])
class TableTest(unittest.TestCase):
 def doc(self):return {'atom_id':'synthetic','source_sha256':'a'*64,'title':'Compare','rows':[{'cells':[{'id':f'c{r}-{c}','text':f'value {r}-{c}'} for c in range(3)]} for r in range(3)]}
 def test_themes_preserve_every_cell_identity(self):
  a=Parse();a.feed(render_table(self.doc(),'source'));b=Parse();b.feed(render_table(self.doc(),'yongle'))
  self.assertEqual(a.cells,9);self.assertEqual(set(a.ids),set(b.ids));self.assertEqual(len(set(a.ids)),9)
 def test_markup_escape_and_static_fallback(self):
  d=self.doc();d['rows'][1]['cells'][1]['text']='<img onerror=bad>'
  h=render_table(d,'yongle');self.assertIn('&lt;img onerror=bad&gt;',h);self.assertIn('prefers-reduced-motion',h);self.assertNotIn('<body data-playing',h)
if __name__=='__main__':unittest.main()
