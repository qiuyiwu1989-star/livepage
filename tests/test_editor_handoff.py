import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workbench'))
from editor_handoff import build_handoff, build_deck, digest

class HandoffTest(unittest.TestCase):
    def scene(self):
        return {'atom_id':'synthetic','source_sha256':'a'*64,'pdf_page':0,'size':[320,180],
                'text':[{'text':'Hello','bbox':[1,2,40,20],'origin':[1,15],'font':'Synthetic','size':12,'color':0}]}
    def test_id_and_html_bound_to_base(self):
        scene=self.scene();html='<span data-block="0">Hello</span>'
        a,ha=build_handoff(scene,html,'v1');b,hb=build_handoff(scene,html,'v1')
        self.assertEqual(a,b);self.assertEqual(a['html_sha256'],digest(ha))
        self.assertIn(a['objects'][0]['object_id'],ha)
        self.assertNotIn('object_id',scene['text'][0])
    def test_rejects_raster_or_missing_dom(self):
        scene=self.scene();scene['text'][0]['source_raster']={'png':'synthetic'}
        with self.assertRaises(ValueError):build_handoff(scene,'','v1')
        with self.assertRaises(ValueError):build_handoff(self.scene(),'<p/>','v1')
    def test_deck_retains_repeat_occurrences_and_versions(self):
        rows=[{'entry_id':'e1','atom_id':'same','page_version_id':'v1'},
              {'entry_id':'e2','atom_id':'same','page_version_id':'v2'}]
        deck=build_deck('d1',rows)
        self.assertEqual([x['position'] for x in deck['entries']],[0,1])
        self.assertNotIn('position',rows[0])
        with self.assertRaises(ValueError):build_deck('d1',[rows[0],rows[0]])
if __name__=='__main__':unittest.main()
