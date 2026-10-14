"""Loopback-only slide workspace. Originals and generated pages are immutable.
Imported HTML is stored as a new revision; selecting it never marks human acceptance.
"""
from pathlib import Path
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4
import hashlib,json,os,re,tempfile
from html.parser import HTMLParser
from flask import Flask,request,jsonify,send_from_directory,Response,redirect
ROOT=Path(os.environ.get("LIVEPAGE_WORKSPACE_ROOT", Path(__file__).resolve().parent))
LIMIT=5*1024*1024
class HTMLCheck(HTMLParser):
 def __init__(self):super().__init__();self.errors=[];self.source=None;self.page=None;self.page_id=None;self.base=None;self.session=None;self.meta_counts={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in {'script','iframe','object','embed','base','form','link','audio','video'}:self.errors.append('不允许的 HTML 元素 '+tag)
  if tag=='meta':
   name=a.get('name');self.meta_counts[name]=self.meta_counts.get(name,0)+1
   if name=='source-version-sha256':self.base=a.get('content')
   if name=='slide-library-session':self.session=a.get('content')
   if a.get('http-equiv'):self.errors.append('不允许重定向或响应头')
   if a.get('name')=='source-sha256':self.source=a.get('content')
   if a.get('name')=='source-page':self.page=a.get('content')
  if 'data-page-id' in a:self.page_id=a['data-page-id']
  for k,v in a.items():
   if k.startswith('on') or k in {'srcdoc','srcset','action','formaction'}:self.errors.append('不允许主动内容')
   if k in {'src','href','xlink:href'} and v and not(v.startswith('#') or v.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,'))):self.errors.append('资源必须内嵌')
def strip_transport(text):
 return re.sub(r'<meta\b(?=[^>]*\bname=["\'](?:source-version-sha256|slide-library-session)["\'])[^>]*>', '', text, flags=re.I)
def check_html(text,page):
 if not isinstance(text,str) or not text.strip():raise ValueError('请选择非空UTF-8 HTML')
 if len(text.encode())>LIMIT:raise ValueError('HTML 超过 5 MiB')
 h=HTMLCheck();h.feed(text)
 if h.errors:raise ValueError(h.errors[0])
 if re.search(r'@import|expression\s*\(',text,re.I):raise ValueError('不允许外部 CSS 或表达式')
 for url in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)',text,re.I):
  if not url.startswith(('#','data:font/woff2;base64,','data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):raise ValueError('CSS 资源必须内嵌')
 if h.source!=page['source_sha256'] or h.page!=str(page['page_number']) or h.page_id!=page['page_id']:raise ValueError('原稿或页面标识不匹配；请从本页导出的 HTML 编辑')
 if any(h.meta_counts.get(k,0)!=1 for k in ['source-sha256','source-page','source-version-sha256']):raise ValueError('来源或版本凭据缺失或重复，请重新导出当前版本')
 if h.meta_counts.get('slide-library-session',0)>1:raise ValueError('会话凭据重复')
 return hashlib.sha256(strip_transport(text).encode()).hexdigest(),h
def create_app(root=ROOT):
 root=Path(root);store=root/'workspace';store.mkdir(exist_ok=True);lock=RLock()
 app=Flask(__name__,static_folder=None);app.config['ASSEMBLY_CATALOG_DIR']=str(Path(os.environ.get('LIVEPAGE_CATALOG_ROOT',root.parent/'slide-library-migration'))/'generated');app.config['MAX_CONTENT_LENGTH']=35*1024*1024
 def read():
  p=store/'state.json';return json.loads(p.read_text()) if p.exists() else {'collection':[],'revisions':{},'imports':[]}
 def write(state):
  fd,p=tempfile.mkstemp(dir=store,suffix='.json');
  with os.fdopen(fd,'w') as f:json.dump(state,f,ensure_ascii=False,indent=2)
  os.replace(p,store/'state.json')
 def pages():return {p['page_id']:p for p in json.loads((root/'data/annotations.json').read_text())['pages']}
 @app.before_request
 def local_only():
  if request.host.split(':')[0] not in ('127.0.0.1','localhost','[::1]'):return jsonify(error='仅允许本机访问'),403
  if request.method!='GET' and request.headers.get('Origin') not in (None,request.host_url.rstrip('/'),*app.config.get('TRUSTED_WRITE_ORIGINS',())):return jsonify(error='跨来源写入被拒绝'),403
 @app.after_request
 def headers(response):
  response.headers['X-Content-Type-Options']='nosniff'
  if request.path.startswith('/workspace/revisions/'):
   response.headers['Content-Security-Policy']="sandbox; default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'"
  return response
 @app.errorhandler(ValueError)
 def invalid(e):return jsonify(error=str(e)),400
 @app.get('/api/workspace')
 def state():return jsonify(read())
 @app.post('/api/collection')
 def collection():
  body=request.get_json();ids=body.get('pages',[])
  if not isinstance(ids,list) or len(ids)>500 or any(not isinstance(i,str) or i not in pages() for i in ids):raise ValueError('页面不存在')
  with lock:
   state=read();state['collection']=list(dict.fromkeys(ids));write(state)
  return jsonify(state)
 @app.post('/api/revisions/<page_id>')
 def revision(page_id):
  page=pages().get(page_id)
  if not page:raise ValueError('页面不存在')
  body=request.get_json();html=body.get('html','');sha,checked=check_html(html,page)
  with lock:
   state=read();history=state['revisions'].get(page_id,[]);current=history[-1]['sha256'] if history else page['html_sha256']
   if checked.base!=current or (body.get('base_sha256') is not None and body['base_sha256']!=checked.base):return jsonify(error='页面已有更新，请重新载入后再保存'),409
   if checked.session:
    ticket=state.get('handoffs',{}).get(checked.session)
    if not ticket or ticket['page_id']!=page_id or ticket['base_sha256']!=checked.base or ticket.get('consumed'):raise ValueError('交接票据无效或已使用')
   if sha==current:return jsonify(unchanged=True),200
   path=Path('workspace/revisions')/page_id/(uuid4().hex+'.html');(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_text(strip_transport(html))
   record={'id':path.stem,'path':str(path),'sha256':sha,'parent_sha256':current,'created_at':datetime.now(timezone.utc).isoformat(),'human_review':'pending','source_sha256':page['source_sha256']}
   if checked.session:state['handoffs'][checked.session]['consumed']=record['id']
   history.append(record);state['revisions'][page_id]=history;write(state)
  return jsonify(record),201
 @app.get('/api/export/<page_id>')
 def export_current(page_id):
  page=pages().get(page_id)
  if not page:raise ValueError('页面不存在')
  with lock:
   state=read();history=state['revisions'].get(page_id,[]);last=history[-1] if history else None
   source_path=last['path'] if last else page['html'];base=last['sha256'] if last else page['html_sha256']
   html=(root/source_path).read_text()
   # Stored bytes are immutable. The transport metadata is reissued on this copy only.
   html=strip_transport(html)
   session=uuid4().hex;ticket={'page_id':page_id,'base_sha256':base,'source_sha256':page['source_sha256'],'created_at':datetime.now(timezone.utc).isoformat()}
   state.setdefault('handoffs',{})[session]=ticket;write(state)
   meta='<meta name="source-version-sha256" content="'+base+'"><meta name="slide-library-session" content="'+session+'">'
   html=re.sub(r'(<head\b[^>]*>)',lambda match:match.group(0)+meta,html,count=1,flags=re.I)
   if not re.search(r'<head\b',html,re.I):raise ValueError('HTML缺少head，不能签发版本')
   if len(html.encode())>LIMIT:raise ValueError('添加来源凭据后HTML超过5 MiB')
  response=Response(html,content_type='text/html; charset=utf-8');response.headers['Content-Disposition']='attachment; filename="'+page_id+'-editable.html"';response.headers['Cache-Control']='no-store';return response
 @app.post('/api/import-pdf')
 def import_pdf():
  import pymupdf
  upload=request.files.get('file')
  if not upload:raise ValueError('请选择 PDF')
  data=upload.read();sha=hashlib.sha256(data).hexdigest()
  original=json.loads((root/'data/source-manifest.json').read_text())
  if sha==original['source_sha256']:return jsonify(duplicate=True,deck_id=sha,pages=original['page_count'])
  try:doc=pymupdf.open(stream=data,filetype='pdf')
  except Exception:raise ValueError('文件不是有效 PDF')
  if doc.needs_pass or not 0<len(doc)<=500:raise ValueError('请提供未加密、1–500 页 PDF')
  with lock:
   state=read()
   existing=next((x for x in state['imports'] if x['sha256']==sha),None)
   if existing:return jsonify(duplicate=True,**existing)
   folder=store/'imports'/sha;folder.mkdir(parents=True,exist_ok=True);(folder/'original.pdf').write_bytes(data)
   rec={'deck_id':sha,'sha256':sha,'name':Path(upload.filename or '课件.pdf').name,'pages':len(doc),'status':'archived_pending_annotation','source':str((folder/'original.pdf').relative_to(root)),'created_at':datetime.now(timezone.utc).isoformat()}
   state['imports'].append(rec);write(state)
  return jsonify(duplicate=False,**rec),201
 @app.get('/')
 def home():return send_from_directory(root,'index.html') if request.args.get('processing')=='1' or request.args.get('page') else redirect('/atom-pages/index.html')
 @app.get('/<path:path>')
 def assets(path):
  if path.endswith(('.py','.json.tmp')):return '',404
  return send_from_directory(root,path)
 from atom_removal import register_removal
 register_removal(app,root)
 from library_api import register_library
 register_library(app, root)
 @app.get('/uploads/slides-hd/<filename>')
 @app.get('/uploads/slides/<filename>')
 def archive_local_image(filename):
  from image_governance import source_override
  replacement=source_override(root,Path(filename).stem)
  if replacement:
   recovered=(root/replacement['image_url'].lstrip('/')).resolve()
   if root.resolve() in recovered.parents and recovered.is_file():return send_from_directory(recovered.parent,recovered.name)
  return send_from_directory(root/'assets/legacy-hd',filename)
 from annotation_api import register_annotations
 register_annotations(app, root)
 from assembly_api import register_assemblies
 register_assemblies(app, root)
 from prep_courses_api import register_prep_courses
 register_prep_courses(app, root)
 from prep_agent_api import register_prep_agent
 register_prep_agent(app, root)
 from governance_api import register_governance
 register_governance(app, root)
 return app
if __name__=='__main__':create_app().run(host='127.0.0.1',port=5198,debug=False)
