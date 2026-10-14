"""Read-only catalog bridge: migration snapshots stay separate from original stores."""
from atom_removal import deleted_ids
from pathlib import Path
import json,copy
from urllib.parse import urlsplit
from flask import Blueprint,jsonify,request,send_from_directory
MIGRATION=Path(__file__).resolve().parent.parent/'slide-library-migration'
def register_library(app, root=None):
 root=Path(root) if root else Path(__file__).resolve().parent
 bp=Blueprint('unified_library',__name__);cache={'mtime':None,'data':None}
 atomic_cache={'mtime':None,'data':None}
 original_cache={}
 archive_cache={}
 title_cache={}
 def title_overlay(atom_id):
  path=root/'title-governance/audit.json'
  if not path.exists():return {}
  stamp=path.stat().st_mtime_ns
  if title_cache.get('stamp')!=stamp:title_cache.update(stamp=stamp,records={r['atom_id']:r for r in json.loads(path.read_text())['records']})
  row=title_cache['records'].get(atom_id,{})
  if row.get('visual_review')=='image_checked_by_codex':
   return {'knowledge_title':row.get('candidate_title'),'title_review_status':'human_pending','title_source':'image_checked_candidate'}
  visual=root/'title-governance/visual-results'/(str(atom_id)+'.json')
  if visual.exists():
   candidate=json.loads(visual.read_text())
   if candidate.get('status')=='visual_model_candidate':return {'knowledge_title':candidate['knowledge_title'],'title_review_status':'AI待确认','title_source':'visual_model_candidate'}
  return {}
 def archive_records():
  path=root/"atomdump/atomdump/atoms.json"
  if not path.exists():return {}
  stamp=path.stat().st_mtime_ns
  if archive_cache.get("stamp")!=stamp:
   data=json.loads(path.read_text())
   archive_cache.update(stamp=stamp,records={a["atom_id"]:a for a in data.get("atoms",[])})
  return archive_cache["records"]
 def originals():
  folder=MIGRATION.parent/'slide-library-original-structured/data';marker=folder/'slide-index.json'
  if not marker.exists():return {},{}
  stamp=marker.stat().st_mtime_ns
  if original_cache.get('stamp')!=stamp:
   records={p.stem:json.loads(p.read_text()) for p in (folder/'atom').glob('*.json')}
   f=folder/'slide-framework-links-v2.json'
   original_cache.update(stamp=stamp,records=records,frameworks=json.loads(f.read_text()) if f.exists() else {})
  gone=deleted_ids(root)
  return {k:v for k,v in original_cache['records'].items() if k not in gone},original_cache['frameworks']
 def source_atom(atom_id):
  records,_=originals();a=records.get(atom_id)
  if not a:return None
  return {'atom_id':atom_id,'title':a.get('title',''),'identity_status':'source_record_without_index_membership','occurrence_ids':[],'annotation':{'vlm_summary':a.get('vlm_summary',{})},'original_atom':a}
 def load_atomic():
  path=MIGRATION/'generated/atomic-catalog.json'
  if not path.exists():return None
  stamp=path.stat().st_mtime_ns
  if atomic_cache['mtime']!=stamp:
   data=json.loads(path.read_text())
   atomic_cache.update(mtime=stamp,data=data,occurrences={o['occurrence_id']:o for o in data['occurrences']},atoms={a['atom_id']:a for a in data['atoms']})
  data=dict(atomic_cache['data']);gone=deleted_ids(root);data['atoms']=[a for a in data['atoms'] if a['atom_id'] not in gone];data['occurrences']=[o for o in data['occurrences'] if o['atom_id'] not in gone];return data
 def load():
  path=MIGRATION/'generated/catalog.json'
  if not path.exists():return {'decks':[],'pages':[],'status':'migration_pending'}
  stamp=path.stat().st_mtime_ns
  if cache['mtime']!=stamp:cache.update(mtime=stamp,data=json.loads(path.read_text()))
  data=dict(cache['data']);gone=deleted_ids(root);data['pages']=[p for p in data['pages'] if p.get('atomic_id') not in gone];return data
 def query(p):
  return json.dumps({'title_overlay':title_overlay(p.get('atomic_id')),'page':{k:p.get(k) for k in ['title','page_id','legacy_ids','atomic_id','atom_id','annotation']},'archive':archive_records().get(p.get('atomic_id')),'original_detail':originals()[0].get(p.get('atomic_id')),'frameworks':originals()[1].get('by_atom',{}).get(p.get('atomic_id'))},ensure_ascii=False).casefold()
 def has_html(p):return p.get('html',{}).get('status') in {'local_exists','unverified_remote'}
 def view(p):
  p=copy.deepcopy(p)
  p.update(title_overlay(p.get('atomic_id')))
  if p.get('knowledge_title'):p['original_title']=p.get('title');p['title']=p['knowledge_title']
  p['original_source_url']=p.get('source_url')
  records,frameworks=originals() if p.get('atomic_id') else ({},{})
  original=records.get(p.get('atomic_id'))
  if original:
   p['original_atom_detail']=copy.deepcopy(original)
   p['annotation']['snapshot_vlm_summary']=p['annotation'].get('vlm_summary')
   p['annotation']['vlm_summary']=copy.deepcopy(original.get('vlm_summary') or p['annotation'].get('vlm_summary') or {})
   p['annotation']['vlm_source']='original standalone atom detail'
  archive=archive_records().get(p.get('atomic_id'))
  if archive:
   p['structured_archive']=copy.deepcopy(archive)
   annotation=p.setdefault('annotation',{})
   existing=annotation.get('vlm_summary') or {}
   supplemental=archive.get('vlm') or {}
   annotation['vlm_summary']={**{k:v for k,v in supplemental.items() if v is not None and v!='' and v!=[]},**{k:v for k,v in existing.items() if v is not None and v!='' and v!=[]}}
   annotation['archive_provenance']={'source':'atomdump/atomdump/atoms.json','review':'pending','policy':'original nonempty fields retained; archive supplements missing fields'}
  p['framework_links']=copy.deepcopy(frameworks.get('by_atom',{}).get(p.get('atomic_id'),{}).get('frameworks',[]))
  p['framework_source']=frameworks.get('_meta',{})
  for key,target in [('thumbnail','thumbnail_url'),('image','source_url'),('html',None)]:
   ref=p.get(key,{})
   if target and ref.get('url'):p[target]=ref['url']
   if ref.get('local_path'):
    try:url='/'+str(Path(ref['local_path']).resolve().relative_to(Path(__file__).resolve().parent));ref['url']=url
    except ValueError:continue
    if target:p[target]=url
  remote=p.get('image',{}).get('url') or ''
  parts=urlsplit(remote)
  if parts.hostname=='qiuyiwu.com' and parts.path.startswith('/uploads/slides-hd/'):
   filename=Path(parts.path).name; local=root/'assets/legacy-hd'/filename
   if local.is_file() and local.stat().st_size>0:
    p['image']['remote_url']=remote;p['image']['url']='/assets/legacy-hd/'+filename
    p['image']['status']='local_cached';p['source_url']=p['image']['url']
  from image_governance import source_override
  recovered=next((source_override(root,sid) for sid in p.get('legacy_ids',[]) if source_override(root,sid)),None)
  if recovered:
   p['source_image_override']=recovered
   p['source_url']=recovered['image_url']
   p['thumbnail_url']=recovered.get('thumbnail_url') or recovered['image_url']
  if p.get('atomic_id')=='atom-0410':p['annotation_warning']='旧AI白纸解读与恢复原图不符，待重标；不可作为已核验解释'
  p['has_html']=has_html(p);p['origin_kind']=p.get('source_kind');return p
 def projection(p):
  p=view(p);a=p.get('annotation',{});return {k:p.get(k) for k in ['page_id','deck_id','title','page_number','legacy_ids','thumbnail_url','source_url','processing','html','origin_kind']}|{'tags':a.get('tags',[]),'summary':a.get('summary',''),'reading_summary':(a.get('vlm_summary') or {}).get('topic') if isinstance(a.get('vlm_summary'),dict) else a.get('summary',''),'has_html':has_html(p)}
 def page_matches_stage(p,stage):
  if stage=='has-html':return has_html(p)
  if stage=='needs-html':return not has_html(p)
  if stage=='needs-annotation':return not (p.get('annotation',{}).get('source_text') or p.get('annotation',{}).get('summary'))
  return True
 def gallery_atom(atom,occurrences,source_records):
  """Project one established identity, keeping its source-selected page when available."""
  source=source_records.get(atom['atom_id']) or {}
  preferred=atom.get('representative_id') or source.get('representative_id')
  representative=next((p for p in occurrences if preferred in p.get('legacy_ids',[])),None) if preferred else None
  representative=representative or occurrences[0]
  vlm=source.get('vlm_summary') or atom.get('annotation',{}).get('vlm_summary') or {}
  page=projection(representative)
  from image_governance import representative_override
  image_override=representative_override(root,atom['atom_id'])
  if image_override:
   page['source_image_url']=page.get('source_url')
   page['source_url']=image_override['image_url']
   page['thumbnail_url']=image_override.get('thumbnail_url') or image_override['image_url'].replace('/uploads/slides-hd/','/assets/legacy-thumbs/')
   page['image_override']=image_override
  summary=vlm.get('topic') if isinstance(vlm,dict) else None
  summary=summary or atom.get('annotation',{}).get('summary') or page.get('reading_summary') or ''
  page.update(atom_id=atom['atom_id'],occurrence_count=len(atom.get('occurrence_ids',[])),reading_summary=summary)
  return {'atom_id':atom['atom_id'],'title':title_overlay(atom['atom_id']).get('knowledge_title') or atom.get('title') or page.get('title') or '',
          'identity_status':atom.get('identity_status'),'summary':summary,
          'occurrence_count':len(atom.get('occurrence_ids',[])),
          'representative_page':page,'detail_url':'/api/atoms/'+atom['atom_id']}
 @bp.get('/api/library/processing')
 def processing_summary():
  from processing_status import course_summary
  data=load()
  path=root/'data/processing-jobs.json'
  jobs=json.loads(path.read_text()).get('pages',{}) if path.exists() else {}
  return jsonify(courses=course_summary(data.get('decks',[]),data.get('pages',[]),jobs),
                 task_registry_available=path.exists())
 @bp.get('/api/library')
 def catalog():
  data=load();pages=data.get('pages',[]);q=request.args.get('q','').strip().casefold();deck=request.args.get('deck','');stage=request.args.get('stage','');mode=request.args.get('mode','pages')
  if mode not in {'pages','atoms'}:return jsonify(error='目录模式无效'),400
  from annotation_api import note_search_text
  note_text=note_search_text(root) if q else {}
  try:offset=max(0,int(request.args.get('offset','0')));limit=min(60,max(1,int(request.args.get('limit','24'))))
  except ValueError:return jsonify(error='分页参数无效'),400
  counts={'pages':len(pages),'decks':len(data.get('decks',[])),'html':sum(has_html(p) for p in pages),'source_atoms':len({p.get('atomic_id') for p in pages if p.get('identity_authority')=='original_library' and p.get('atomic_id')}),'provisional_pages':sum(p.get('identity_authority')!='original_library' for p in pages),'source_annotations':sum(bool(p.get('annotation',{}).get('vlm_summary')) for p in pages)}
  if mode=='pages':
   items=[p for p in pages if (not deck or p.get('deck_id')==deck) and page_matches_stage(p,stage) and (not q or all(term in (query(p)+' '+note_text.get(p['page_id'],'').casefold()) for term in q.split()))]
   return jsonify(mode=mode,total=len(items),offset=offset,limit=limit,pages=[projection(p) for p in items[offset:offset+limit]],decks=data.get('decks',[]),counts=counts,status=data.get('status','ready'))
  atomic=load_atomic()
  if atomic is None:return jsonify(error='原子目录尚未就绪'),503
  source_records,framework_data=originals()
  counts.update(atoms=len(atomic['atoms']),source_orphans=len(set(source_records)-set(atomic_cache['atoms'])))
  eligible={p['page_id']:p for p in pages if (not deck or p.get('deck_id')==deck) and page_matches_stage(p,stage)}
  by_atom={}
  for occurrence in atomic['occurrences']:
   page=eligible.get(occurrence['occurrence_id'])
   if page:by_atom.setdefault(occurrence['atom_id'],[]).append(page)
  terms=q.split();items=[]
  for atom in atomic['atoms']:
   occurrences=by_atom.get(atom['atom_id'])
   if not occurrences:continue
   if terms:
    searchable=json.dumps({'atom':atom,'archive':archive_records().get(atom['atom_id']),'standalone':source_records.get(atom['atom_id']),'frameworks':framework_data.get('by_atom',{}).get(atom['atom_id'])},ensure_ascii=False).casefold()
    page_text=' '.join(query(p)+' '+note_text.get(p['page_id'],'').casefold() for p in occurrences)
    if not all(term in searchable+' '+page_text for term in terms):continue
   items.append((atom,occurrences))
  batch=[gallery_atom(atom,occurrences,source_records) for atom,occurrences in items[offset:offset+limit]]
  return jsonify(mode=mode,total=len(items),offset=offset,limit=limit,atoms=batch,pages=[a['representative_page'] for a in batch],decks=data.get('decks',[]),counts=counts,status=data.get('status','ready'))
 @bp.get('/api/library/page/<page_id>')
 def detail(page_id):
  p=next((p for p in load().get('pages',[]) if p['page_id']==page_id),None)
  if not p:return jsonify(error='页面不存在'),404
  result=view(p)
  siblings=sorted([x for x in load().get('pages',[]) if x['deck_id']==p['deck_id']],key=lambda x:(x.get('page_number') or 0,x['page_id']))
  index=next(i for i,x in enumerate(siblings) if x['page_id']==page_id)
  result['navigation']={'previous':siblings[index-1]['page_id'] if index else None,'next':siblings[index+1]['page_id'] if index+1<len(siblings) else None,'position':index+1,'total':len(siblings)}
  return jsonify(result)
 @bp.get('/api/atoms')
 def search_atoms():
  data=load_atomic()
  if data is None:return jsonify(error='原子目录尚未就绪'),503
  try:offset=max(0,int(request.args.get('offset',0)));limit=min(100,max(1,int(request.args.get('limit',20))))
  except ValueError:return jsonify(error='分页参数无效'),400
  terms=request.args.get('q','').casefold().split();deck=request.args.get('deck','')
  from annotation_api import note_search_text
  note_text=note_search_text(root) if terms else {}
  allowed={o['atom_id'] for o in data['occurrences'] if not deck or o['deck_id']==deck}
  matches=[]
  source_records,framework_data=originals()
  all_atoms=data['atoms']+[source_atom(aid) for aid in source_records if aid not in atomic_cache['atoms']]
  if not deck:allowed.update(source_records)
  for atom in all_atoms:
   if atom['atom_id'] not in allowed:continue
   searchable=json.dumps({'atom':{k:atom.get(k) for k in ['atom_id','title','annotation','original_atom']},'archive':archive_records().get(atom['atom_id']),'standalone':source_records.get(atom['atom_id']),'frameworks':framework_data.get('by_atom',{}).get(atom['atom_id'])},ensure_ascii=False).casefold()
   searchable+=' '+json.dumps(title_overlay(atom['atom_id']),ensure_ascii=False).casefold()
   searchable+=' '+' '.join(note_text.get(pid,'').casefold() for pid in atom.get('occurrence_ids',[]))
   if all(t in searchable for t in terms):matches.append(atom)
  return jsonify(total=len(matches),offset=offset,limit=limit,search_mode='keyword_all_terms',atoms=[{'atom_id':a['atom_id'],'title':title_overlay(a['atom_id']).get('knowledge_title') or a['title'],'identity_status':a['identity_status'],'summary':a.get('annotation',{}).get('vlm_summary',{}).get('topic') if isinstance(a.get('annotation',{}).get('vlm_summary'),dict) else a.get('annotation',{}).get('summary'),'occurrence_count':len(a['occurrence_ids']),'detail_url':'/api/atoms/'+a['atom_id']} for a in matches[offset:offset+limit]])
 @bp.get('/api/atoms/<atom_id>')
 def atom_detail(atom_id):
  data=load_atomic()
  if data is None:return jsonify(error='原子目录尚未就绪'),503
  canonical=data.get('identity_aliases',{}).get(atom_id,atom_id)
  if canonical in deleted_ids(root):return jsonify(error='原子页已删除，可恢复'),410
  atom=atomic_cache['atoms'].get(canonical) or source_atom(canonical)
  if not atom:return jsonify(error='原子页不存在'),404
  occurrences=[o for o in data['occurrences'] if o['atom_id']==canonical]
  ids={o['occurrence_id'] for o in occurrences}
  if request.args.get('view')=='reader':
   archive=archive_records().get(canonical) or {}
   pages=[{'page_id':p['page_id'],'legacy_ids':p.get('legacy_ids',[]),'html':{k:p.get('html',{}).get(k) for k in ['status','url']}} for p in load()['pages'] if p['page_id'] in ids]
   return jsonify(canonical_id=canonical,structured_archive={'rep':archive.get('rep')},pages=pages)
  effective=view(next((p for p in load()['pages'] if p['page_id'] in ids),{'atomic_id':canonical,'annotation':atom.get('annotation',{})})).get('annotation',{}).get('vlm_summary',{})
  return jsonify(title_overlay=title_overlay(canonical),atom=atom,requested_id=atom_id,canonical_id=canonical,structured_archive=archive_records().get(canonical),original_atom_detail=originals()[0].get(canonical),effective_vlm_annotation=effective,framework_links=originals()[1].get('by_atom',{}).get(canonical,{}),framework_provenance=originals()[1].get('_meta',{}),
    occurrences=occurrences,pages=[view(p) for p in load()['pages'] if p['page_id'] in ids],
    interpretation_endpoints=[{'page_id':pid,'url':'/api/library/page/'+pid+'/notes'} for pid in sorted(ids)],
    semantics={'identity':'inherited source identity; not a new human approval','annotation':'original AI interpretations retain model and date; not speaker transcript','search':'keyword retrieval; semantic embeddings not yet implemented'})
 @bp.get('/library-data/<path:path>')
 def files(path):return send_from_directory(MIGRATION/'generated',path)
 @bp.get('/api/atoms/<atom_id>/title-review')
 def title_review(atom_id):
  path=root/'title-governance/audit.json'
  if not path.exists():return jsonify(error='标题复核尚未生成'),404
  data=json.loads(path.read_text())
  record=next((r for r in data['records'] if r['atom_id']==atom_id),None)
  if record is None:return jsonify(error='原子页不存在'),404
  return jsonify(record=record,semantics='candidate only; original title unchanged; human review pending')
 @bp.get('/api/library/structure')
 def structure():
  data=load_atomic()
  if data is None:return jsonify(status='pending'),503
  return jsonify(statistics=data.get('statistics',{}),annotation_dimensions=data.get('annotation_dimensions',[]),courses=data.get('courses',[]))
 @bp.get('/api/library/page/<page_id>/identity')
 def identity(page_id):
  data=load_atomic()
  if data is None:return jsonify(status='pending'),503
  occ=atomic_cache['occurrences'].get(page_id)
  if not occ:return jsonify(error='Page not found'),404
  atom=atomic_cache['atoms'][occ['atom_id']]
  related=[o for o in data['occurrences'] if o['atom_id']==atom['atom_id']]
  return jsonify(atom=atom,occurrence=occ,occurrences=related)
 app.register_blueprint(bp)
