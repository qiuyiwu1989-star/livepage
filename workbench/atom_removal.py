"""Recoverable atom removal; source files remain available for recovery."""
import json,re,os,tempfile
from pathlib import Path
from threading import RLock
from datetime import datetime,timezone
from flask import request,jsonify
LOCK=RLock()
def deleted_ids(root):
 p=Path(root)/'workspace/deleted-atoms.json'
 return set(json.loads(p.read_text()).get('deleted',[])) if p.exists() else set()
def register_removal(app,root):
 root=Path(root)
 @app.get('/api/atom-removals')
 def atom_removal_state():return jsonify(deleted=sorted(deleted_ids(root)))
 @app.post('/api/atoms/<atom_id>/removal')
 def atom_removal_change(atom_id):
  if not re.fullmatch(r'atom-\d{4}',atom_id):return jsonify(error='原子页编号无效'),400
  source=json.loads((root/'atomdump/atomdump/atoms.json').read_text())
  if not any(a['atom_id']==atom_id for a in source['atoms']):return jsonify(error='原子页不存在'),404
  action=(request.get_json(silent=True) or {}).get('action')
  if action not in ('delete','restore'):return jsonify(error='操作无效'),400
  with LOCK:
   p=root/'workspace/deleted-atoms.json';p.parent.mkdir(exist_ok=True)
   data=json.loads(p.read_text()) if p.exists() else {'deleted':[],'history':[]}
   ids=set(data['deleted'])
   if action=='delete':ids.add(atom_id)
   else:ids.discard(atom_id)
   data['deleted']=sorted(ids);data['history'].append({'atom_id':atom_id,'action':action,'at':datetime.now(timezone.utc).isoformat()})
   fd,tmp=tempfile.mkstemp(dir=p.parent)
   with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
   os.replace(tmp,p)
  return jsonify(atom_id=atom_id,deleted=action=='delete')
