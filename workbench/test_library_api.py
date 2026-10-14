import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from flask import Flask
import library_api
from annotation_api import register_annotations


class LibraryIntegrationTest(unittest.TestCase):
 def test_source_image_and_supplementary_search(self):
  with tempfile.TemporaryDirectory() as folder:
   base=Path(folder);root=base/'pilot';root.mkdir();migration=base/'slide-library-migration';generated=migration/'generated';generated.mkdir(parents=True)
   page={'page_id':'old-1','deck_id':'deck-1','title':'Original','source_url':'https://example.com/slide.html?id=1','image':{'url':'https://example.com/image.jpg'},'thumbnail':{'url':'https://example.com/thumb.jpg'},'annotation':{},'html':{}}
   (generated/'catalog.json').write_text(json.dumps({'pages':[page],'decks':[{'deck_id':'deck-1','title':'Deck'}]}))
   app=Flask(__name__)
   with patch.object(library_api,'MIGRATION',migration):
    library_api.register_library(app,root);register_annotations(app,root);client=app.test_client()
    result=client.get('/api/library/page/old-1').json
    self.assertEqual(result['source_url'],'https://example.com/image.jpg')
    self.assertEqual(result['original_source_url'],page['source_url'])
    self.assertEqual(client.get('/api/library?q=classroom-evidence').json['total'],0)
    self.assertEqual(client.post('/api/library/page/old-1/notes',json={'kind':'teaching_note','text':'classroom-evidence'}).status_code,201)
    self.assertEqual(client.get('/api/library?q=classroom-evidence').json['total'],1)
    self.assertEqual(json.loads((generated/'catalog.json').read_text())['pages'][0],page)

 def test_archive_supplements_without_overwriting_source(self):
  with tempfile.TemporaryDirectory() as folder:
   base=Path(folder);root=base/'pilot';archive=root/'atomdump/atomdump';archive.mkdir(parents=True)
   migration=base/'migration';generated=migration/'generated';generated.mkdir(parents=True)
   page={'page_id':'p1','atomic_id':'atom-1','deck_id':'d1','title':'Page','annotation':{'vlm_summary':{'topic':'Original topic','claims':[]}},'html':{}}
   (generated/'catalog.json').write_text(json.dumps({'pages':[page],'decks':[]}))
   path=archive/'atoms.json'
   path.write_text(json.dumps({'atoms':[{'atom_id':'atom-1','vlm':{'topic':'Replacement','claims':['unique-archive-claim'],'has_chart':False}}]}))
   app=Flask(__name__)
   with patch.object(library_api,'MIGRATION',migration):
    library_api.register_library(app,root);client=app.test_client()
    result=client.get('/api/library/page/p1').json
    self.assertEqual(result['annotation']['vlm_summary']['topic'],'Original topic')
    self.assertEqual(result['annotation']['vlm_summary']['claims'],['unique-archive-claim'])
    self.assertIs(result['annotation']['vlm_summary']['has_chart'],False)
    self.assertEqual(client.get('/api/library?q=unique-archive-claim').json['total'],1)
    self.assertEqual(json.loads((generated/'catalog.json').read_text())['pages'][0],page)
    path.write_text(json.dumps({'atoms':[]}))
    self.assertNotIn('structured_archive',client.get('/api/library/page/p1').json)


if __name__=='__main__':unittest.main()
