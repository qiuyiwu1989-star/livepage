"""Persistent user titles and explicit local task requests; no implicit model execution."""
from pathlib import Path
from threading import RLock
from datetime import datetime, timezone
import json, os, tempfile, uuid
from flask import request, jsonify
LOCK=RLock()
def read_store(root):
 p=Path(root)/'data/workspace-tools.json'
 return json.loads(p.read_text()) if p.exists() else {'titles':{},'title_history':[],'jobs':[]}
def save(root,data):
 p=Path(root)/'data/workspace-tools.json';p.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=p.parent)
 with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
 os.replace(tmp,p)
def title_override(root,key):return read_store(root)['titles'].get(key)
def register_tools(app,root):
 root=Path(root)
 def catalog():
  p=Path(app.config['ASSEMBLY_CATALOG_DIR'])/'catalog.json'
  return json.loads(p.read_text())
 def now():return datetime.now(timezone.utc).isoformat()
 @app.get('/api/library/user-titles')
 def titles():
  values=read_store(root)['titles'];aliases=dict(values)
  if values:
   for page in catalog()['pages']:
    value=values.get(page.get('atomic_id') or page['page_id'])
    if value:aliases[page['page_id']]=value
  return jsonify(titles=aliases)
 @app.put('/api/library/titles/<identity>')
 def rename(identity):
  data=catalog();page=next((p for p in data['pages'] if identity in (p['page_id'],p.get('atomic_id'),p.get('atom_id'))),None)
  if not page:return jsonify(error='页面不存在'),404
  body=request.get_json(silent=True) or {};title=body.get('title');revision=body.get('base_revision')
  if not isinstance(title,str) or not 1<=len(title.strip())<=200:return jsonify(error='标题须为1至200字'),400
  key=page.get('atomic_id') or page['page_id']
  with LOCK:
   store=read_store(root);old=store['titles'].get(key,{})
   if type(revision) is not int or revision!=old.get('revision',0):return jsonify(error='标题已更新，请重新加载',current=old),409
   record={'title':title.strip(),'revision':revision+1,'at':now(),'source':'user_edit'}
   store['titles'][key]=record;store['title_history'].append({'identity':key,'previous':old,'new':record});save(root,store)
  return jsonify(identity=key,record=record)
 @app.get('/api/processing/tasks')
 def tasks():return jsonify(jobs=read_store(root)['jobs'],executor={'name':'DeepSeek harness / MiMo 2.6 Flash','connected':False},imports=(json.loads((root/'workspace/state.json').read_text()).get('imports',[]) if (root/'workspace/state.json').exists() else []))
 @app.post('/api/processing/tasks')
 def create_task():
  body=request.get_json(silent=True) or {};deck=body.get('deck_id');stage=body.get('stage')
  if stage not in ('annotation','html'):return jsonify(error='请选择标注或HTML转换'),400
  if not any(d['deck_id']==deck for d in catalog()['decks']):return jsonify(error='课件不存在'),404
  with LOCK:
   store=read_store(root);old=next((j for j in store['jobs'] if j['deck_id']==deck and j['stage']==stage and j['status']=='blocked'),None)
   if old:return jsonify(job=old,duplicate=True)
   job={'job_id':'job-'+uuid.uuid4().hex,'deck_id':deck,'stage':stage,'status':'blocked','reason':'尚未接通harness任务执行协议，已保存处理请求，未发送模型','created_at':now()}
   store['jobs'].append(job);save(root,store)
  return jsonify(job=job),201
