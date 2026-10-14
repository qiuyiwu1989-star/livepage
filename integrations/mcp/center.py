"""Private MCP directory and key management. Must be mounted behind owner login."""
from pathlib import Path
from contextlib import contextmanager
import fcntl,hashlib,json,os,secrets,time,uuid
from urllib.parse import urlsplit
from flask import Flask,request,jsonify,make_response,send_from_directory
from bridge import API

def create_app(root=None,api=None):
 root=Path(root or os.environ.get('MCP_CENTER_STATE','/opt/livepage/state/mcp'));root.mkdir(parents=True,exist_ok=True)
 api=api or API('http://127.0.0.1:5298');app=Flask(__name__,static_folder=None);app.config['MAX_CONTENT_LENGTH']=65536
 services_file=root/'services.json'
 @contextmanager
 def lock():
  with (root/'center.lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX)
   try:yield
   finally:fcntl.flock(f,fcntl.LOCK_UN)
 def read(path,default):return json.loads(path.read_text()) if path.exists() else default
 def write(path,data):
  temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False));temp.chmod(0o600);temp.replace(path)
 def services():return read(services_file,{'services':[{'id':'livepage','name':'活页 LivePage','url':'https://qiuyiwu.com/mcp/livepage','description':'知识、课程与图片 / HTML 素材，只读接口','key_management':True}]})['services']
 def registry(sid):
  if sid not in ('all','livepage'):raise ValueError('此服务尚未接入中心密钥验证；只支持目录登记')
  return root/'clients.json'
 @app.before_request
 def protect():
  if request.host.split(':')[0] not in ('127.0.0.1','localhost'):return jsonify(error='仅允许受保护的反向代理访问'),403
  if request.method not in ('GET','HEAD','OPTIONS'):
   origin=request.headers.get('Origin');expected=request.headers.get('X-CSRF-Token','');cookie=request.cookies.get('mcp_center_csrf','')
   if origin!='https://qiuyiwu.com' or not cookie or not secrets.compare_digest(cookie,expected):return jsonify(error='请求验证失败，请刷新页面'),403
 @app.after_request
 def headers(r):
  r.headers['Cache-Control']='no-store';r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='same-origin'
  r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
  return r
 @app.errorhandler(ValueError)
 def invalid(e):return jsonify(error=str(e)),400
 @app.get('/')
 def home():return send_from_directory(Path(__file__).parent,'center.html')
 @app.get('/center.js')
 def js():return send_from_directory(Path(__file__).parent,'center.js')
 @app.get('/api/session')
 def session():
  token=secrets.token_urlsafe(32);r=jsonify(csrf=token);r.set_cookie('mcp_center_csrf',token,secure=True,httponly=True,samesite='Strict',path='/admin/mcp/');return r
 @app.get('/api/services')
 def list_services():return jsonify(services=[dict(s, integration='active' if s.get('key_management') else 'directory_only', permissions=['read','download'] if s.get('key_management') else []) for s in services()],gateway_url='https://qiuyiwu.com/mcp')
 @app.post('/api/services')
 def add_service():
  b=request.get_json(silent=True) or {};name=b.get('name','');url=b.get('url','');description=b.get('description','')
  if not isinstance(name,str) or not 1<=len(name.strip())<=80 or not isinstance(url,str) or len(url)>500 or not isinstance(description,str) or len(description)>500:raise ValueError('名称、地址或描述无效')
  u=urlsplit(url)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:raise ValueError('请填写不含凭据的 HTTPS MCP 地址')
  with lock():
   rows=services()
   if any(x['url']==url for x in rows):raise ValueError('该服务已登记')
   row={'id':'service-'+uuid.uuid4().hex,'name':name.strip(),'url':url,'description':description,'key_management':False};rows.append(row);write(services_file,{'services':rows})
  return jsonify(service=row),201
 @app.get('/api/collections')
 def collections():
  try:rows=api.get('/api/prep/courses').get('courses',[])
  except Exception:return jsonify(error='课程服务暂不可用'),503
  return jsonify(collections=[{'id':d['deck_id'],'name':d.get('title','课件'),'pages':d.get('page_count',0)} for d in rows])
 @app.get('/api/keys')
 def list_keys():
  sid=request.args.get('service','all');path=registry(sid);rows=read(path,{'clients':[]})['clients']
  rows=[dict(c,grants=c.get('grants',{'livepage':{'actions':['read']+(['download'] if c.get('asset_download') else []),'collections':c.get('allowed_decks',[])}})) for c in rows]
  if sid!='all':rows=[c for c in rows if sid in c['grants']]
  return jsonify(keys=[{k:c.get(k) for k in ['client_id','name','suffix','allowed_decks','asset_download','created_at','expires_at','revoked','grants']} for c in rows])
 @app.post('/api/keys')
 def create_key():
  b=request.get_json(silent=True) or {};sid=b.get('service','livepage');path=registry(sid);
  if sid=='all':raise ValueError('请选择已接入的应用，不能默认授权全站')
  name=b.get('name');decks=b.get('allowed_decks');days=b.get('days',30);download=b.get('asset_download',False)
  if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('备注请填写1–80字')
  if type(days) is not int or not 1<=days<=90 or type(download) is not bool:raise ValueError('有效期或下载权限无效')
  if not isinstance(decks,list) or not 1<=len(decks)<=20 or any(not isinstance(x,str) for x in decks):raise ValueError('请选择1–20份课程')
  known={c['deck_id'] for c in api.get('/api/prep/courses').get('courses',[])}
  if not set(decks)<=known:raise ValueError('课程已变化，请刷新后重选')
  key='mcp_'+secrets.token_urlsafe(40);now=int(time.time());row={'client_id':uuid.uuid4().hex,'name':name.strip(),'suffix':key[-6:],'token_sha256':hashlib.sha256(key.encode()).hexdigest(),'allowed_decks':list(dict.fromkeys(decks)),'asset_download':download,'created_at':now,'expires_at':now+days*86400,'revoked':False,'grants':{sid:{'actions':['read']+(['download'] if download else []),'collections':list(dict.fromkeys(decks))}}}
  with lock():
   data=read(path,{'clients':[]});data['clients'].append(row);write(path,data)
  return jsonify(key=key,client_id=row['client_id'],expires_at=row['expires_at']),201
 @app.post('/api/keys/<client_id>/revoke')
 def revoke(client_id):
  with lock():
   path=registry('all');data=read(path,{'clients':[]});row=next((c for c in data['clients'] if c['client_id']==client_id),None)
   if row is None:return jsonify(error='密钥不存在'),404
   row['revoked']=True;row['revoked_at']=int(time.time());write(path,data)
  return jsonify(ok=True)
 return app
app=create_app() if os.environ.get('MCP_CENTER_STATE') else None
