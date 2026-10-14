import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask
import library_api

class AtomAPI(unittest.TestCase):
 def test_canonical_search_alias_and_full_provenance(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);g=root/'generated';g.mkdir()
   pages=[{'page_id':i,'deck_id':'course','page_number':n,'title':'原页','annotation':{'vlm_summary':{'claims':['原始论点'],'model':'original-model'}},'image':{},'provenance':[{'source':'original'}]} for n,i in enumerate(['p1','p2'],1)]
   atom={'atom_id':'atom-original','title':'组织学习','identity_status':'original_library','occurrence_ids':['p1','p2'],'annotation':{'vlm_summary':{'topic':'隐性经验','claims':['原始论点'],'model':'original-model'}},'original_atom':{'unknown_original_field':'preserved'}}
   (g/'catalog.json').write_text(json.dumps({'pages':pages,'decks':[]}));(g/'atomic-catalog.json').write_text(json.dumps({'atoms':[atom],'identity_aliases':{'old-temp':'atom-original'},'occurrences':[{'occurrence_id':i,'atom_id':'atom-original','deck_id':'course'} for i in ['p1','p2']]}))
   app=Flask(__name__)
   with patch.object(library_api,'MIGRATION',root):
    library_api.register_library(app,root);c=app.test_client();r=c.get('/api/atoms?q=隐性经验').json
    self.assertEqual(r['total'],1);self.assertEqual(r['atoms'][0]['occurrence_count'],2)
    d=c.get('/api/atoms/old-temp').json;self.assertEqual(d['canonical_id'],'atom-original');self.assertEqual(d['atom'],atom);self.assertEqual(len(d['pages']),2);self.assertEqual(len(d['interpretation_endpoints']),2)
    reader=c.get('/api/atoms/old-temp?view=reader').json;self.assertEqual(reader['canonical_id'],'atom-original');self.assertEqual(len(reader['pages']),2);self.assertNotIn('atom',reader);self.assertNotIn('annotation',reader['pages'][0])
    self.assertEqual(c.get('/api/atoms/missing').status_code,404);self.assertEqual(c.get('/api/atoms?limit=bad').status_code,400)
    self.assertEqual(c.get('/api/library/page/p1').json['navigation']['next'],'p2')

 def test_gallery_groups_only_by_canonical_identity_and_keeps_source_orphans_unassigned(self):
  with tempfile.TemporaryDirectory() as folder:
   base=Path(folder);root=base/'migration';g=root/'generated';g.mkdir(parents=True)
   source=base/'slide-library-original-structured/data';(source/'atom').mkdir(parents=True)
   (source/'slide-index.json').write_text('{}')
   (source/'atom/a1.json').write_text(json.dumps({'title':'同名页','vlm_summary':{'topic':'独立标注主题','model':'source-model'},'representative_id':'legacy-2'}))
   (source/'atom/orphan.json').write_text(json.dumps({'title':'孤立原子','vlm_summary':{'topic':'未归属'}}))
   pages=[{'page_id':pid,'deck_id':deck,'page_number':number,'title':'同名页','legacy_ids':[legacy],
           'annotation':{'summary':'快照摘要','vlm_summary':{'topic':'快照主题'}},'image':{},'thumbnail':{},
           'html':{'status':html},'processing':{}} for pid,deck,number,legacy,html in
          [('p1','course-1',1,'legacy-1','missing'),('p2','course-2',2,'legacy-2','local_exists'),('p3','course-1',3,'legacy-3','missing')]]
   atoms=[{'atom_id':'a1','title':'同名页','identity_status':'original_library','occurrence_ids':['p1','p2'],
           'representative_id':'legacy-2','annotation':{'vlm_summary':{'topic':'快照主题'}}},
          {'atom_id':'a2','title':'同名页','identity_status':'provisional_per_occurrence','occurrence_ids':['p3'],'annotation':{}}]
   (g/'catalog.json').write_text(json.dumps({'pages':pages,'decks':[{'deck_id':'course-1'},{'deck_id':'course-2'}]}))
   (g/'atomic-catalog.json').write_text(json.dumps({'atoms':atoms,'occurrences':[
    {'occurrence_id':pid,'atom_id':aid,'deck_id':deck} for pid,aid,deck in
    [('p1','a1','course-1'),('p2','a1','course-2'),('p3','a2','course-1')]]}))
   notes=base/'workspace/annotations';notes.mkdir(parents=True)
   (notes/'human.json').write_text(json.dumps({'page_id':'p1','notes':[{'kind':'teaching_note','text':'人工讲述线索'}]}))
   app=Flask(__name__)
   with patch.object(library_api,'MIGRATION',root):
    library_api.register_library(app,base);c=app.test_client()
    gallery=c.get('/api/library?mode=atoms').json
    self.assertEqual(gallery['total'],2)  # Same title is not an identity relation.
    self.assertEqual(gallery['counts']['source_orphans'],1)
    self.assertEqual(gallery['atoms'][0]['representative_page']['page_id'],'p2')
    self.assertEqual(gallery['atoms'][0]['representative_page']['reading_summary'],'独立标注主题')
    self.assertEqual(gallery['atoms'][0]['occurrence_count'],2)
    self.assertEqual(c.get('/api/library?mode=atoms&deck=course-1').json['atoms'][0]['representative_page']['page_id'],'p1')
    self.assertEqual(c.get('/api/library?mode=atoms&stage=has-html').json['total'],1)
    self.assertEqual(c.get('/api/library?mode=atoms&q=独立标注主题').json['total'],1)
    self.assertEqual(c.get('/api/library?mode=atoms&q=legacy-3').json['atoms'][0]['atom_id'],'a2')
    self.assertEqual(c.get('/api/atoms?q=人工讲述线索').json['atoms'][0]['atom_id'],'a1')
    self.assertEqual(c.get('/api/library?mode=atoms&q=人工讲述线索').json['atoms'][0]['atom_id'],'a1')
    self.assertEqual(c.get('/api/atoms/orphan').json['occurrences'],[])
    self.assertEqual(c.get('/api/library').json['total'],3)
    self.assertEqual(c.get('/api/library?mode=invalid').status_code,400)
