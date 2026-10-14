"""Local single-page edit pilot. Agent jobs are dispatched through Harness by operator.
Stores immutable local versions; never writes source artifacts or production library.
"""
import argparse, copy, hashlib, html, json, math, os, re, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, request, send_file


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

def patch_page(state, operations):
    out=copy.deepcopy(state);document=out['html'];objects={x['object_id']:x for x in out['objects']}
    if not isinstance(operations,list) or not 1<=len(operations)<=100:raise ValueError('需要1至100项修改')
    for op in operations:
        if set(op)-{'object_id','text','font_size','color','x','y'}:raise ValueError('未知修改字段')
        obj=objects.get(op.get('object_id'))
        if obj is None:raise ValueError('未知文字对象')
        pattern=r'<span\b(?=[^>]*data-lp-object-id="'+re.escape(obj['object_id'])+r'")[^>]*>.*?</span>'
        matches=list(re.finditer(pattern,document,re.S))
        if len(matches)!=1:raise ValueError('对象与HTML映射不唯一')
        old=matches[0][0];tag,body=old.split('>',1);style=re.search(r'style="([^"]*)"',tag)[1]
        for key,css in [('font_size','font-size'),('x','left'),('y','top')]:
            if key in op:
                value=op[key]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('坐标/字号需要有限数字')
                if key=='font_size' and not 6<=value<=300:raise ValueError('字号须为6至300')
                if key!='font_size' and not -2000<=value<=4000:raise ValueError('坐标超出试跑范围')
                style=re.sub(r'(?<![\w-])'+css+r':[^;]+',css+':'+f'{value/out["canvas_size"][0]*100:.6f}cqw',style)
                obj[key]=value
        if 'color' in op:
            if not isinstance(op['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',op['color']):raise ValueError('颜色格式无效')
            style=re.sub(r'(?<![\w-])color:[^;]+','color:'+op['color'],style);obj['color']=op['color']
        if 'text' in op:
            if not isinstance(op['text'],str) or len(op['text'])>3000:raise ValueError('文字格式或长度无效')
            obj['text']=op['text'];body=html.escape(op['text'])+'</span>'
        tag=re.sub(r'style="[^"]*"',lambda _:'style="'+style+'"',tag)
        document=document[:matches[0].start()]+tag+'>'+body+document[matches[0].end():]
    for font_name, face in out.get('font_faces',{}).items():
        from source_scene import font_payload
        text=''.join(o['text'] for o in out['objects'] if o['layout']['font']==font_name)
        payload,_=font_payload(face['path'],text)
        family=face['css_family']
        document,count=re.subn(r'@font-face\{font-family:'+re.escape(family)+r';src:url\(data:font/woff2;base64,[^)]*\)',lambda _:'@font-face{font-family:'+family+';src:url(data:font/woff2;base64,'+payload+')',document)
        if count!=1:raise ValueError('字体映射不唯一')
    out['html']=document;out['html_sha256']=sha(document)
    return out


def create_app(root):
    root=Path(root).resolve();versions=root/'versions';jobs=root/'agent-jobs';jobs.mkdir(exist_ok=True,parents=True)
    app=Flask(__name__);app.config['MAX_CONTENT_LENGTH']=512*1024;lock=threading.Lock()
    def latest():return json.loads(sorted(versions.glob('*.json'))[-1].read_text())
    @app.before_request
    def local_only():
        if request.host not in {'127.0.0.1:5320','localhost:5320'}:return jsonify(error='Invalid local host'),403
        if request.method=='POST' and request.headers.get('Origin') not in {'http://127.0.0.1:5320','http://localhost:5320'}:return jsonify(error='Invalid origin'),403
    @app.errorhandler(ValueError)
    def invalid(e):return jsonify(error=str(e)),400
    @app.get('/')
    def home():return send_file(Path(__file__).with_name('edit-loop.html'))
    @app.get('/api/state')
    def state():
        value=latest();value['history']=[{'revision':x['revision'],'version_id':x['version_id'],'provenance':x.get('provenance')} for x in [json.loads(p.read_text()) for p in sorted(versions.glob('*.json'))]]
        return jsonify(value)
    @app.get('/preview/<int:revision>')
    def preview(revision):
        p=versions/f'{revision:08d}.json'
        if not p.exists():return '',404
        return app.response_class(json.loads(p.read_text())['html'],mimetype='text/html',headers={'Content-Security-Policy':"default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:; sandbox"})
    @app.post('/api/agent-jobs')
    def job():
        b=request.get_json();s=latest()
        if b.get('base_version_id')!=s['version_id']:return jsonify(error='基线已改变，请重新读取'),409
        intent=b.get('intent')
        if not isinstance(intent,str) or not 1<=len(intent)<=4000:raise ValueError('请输入修改意图')
        jid=uuid.uuid4().hex;payload={'job_id':jid,'base_version_id':s['version_id'],'atom_id':s['atom_id'],'intent':intent,'objects':s['objects'],'status':'pending_dispatch','created_at':stamp(),'output_contract':{'base_version_id':s['version_id'],'model':'MiMo-V2.6-Flash','operations':[{'object_id':'existing ID','text':'new text'}]}}
        (jobs/(jid+'.request.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2))
        return jsonify(job_id=jid,status='pending_dispatch')
    @app.get('/api/agent-jobs/<jid>')
    def result(jid):
        if not re.fullmatch('[0-9a-f]{32}',jid):raise ValueError('任务ID无效')
        p=jobs/(jid+'.proposal.json')
        return jsonify(json.loads(p.read_text()) if p.exists() else {'status':'pending_dispatch','job_id':jid})
    @app.post('/api/save')
    def save():
        b=request.get_json()
        with lock:
            s=latest()
            if b.get('base_version_id')!=s['version_id']:return jsonify(error='基线冲突，旧版本不会被覆盖'),409
            provenance={'kind':'workbench','intent':b.get('intent','工作台精调')}
            operations=b.get('operations')
            if b.get('job_id'):
                jid=b['job_id']
                if not re.fullmatch('[0-9a-f]{32}',jid):raise ValueError('任务ID无效')
                req=json.loads((jobs/(jid+'.request.json')).read_text());p=jobs/(jid+'.proposal.json')
                if not p.exists():raise ValueError('Agent尚未提交提案')
                proposal=json.loads(p.read_text())
                if req['base_version_id']!=s['version_id'] or proposal.get('base_version_id')!=s['version_id']:return jsonify(error='Agent提案基线过期'),409
                if proposal.get('model') not in {'MiMo-V2.6-Flash','Codex'}:raise ValueError('模型标识不符')
                operations=proposal['operations'];provenance={'kind':'agent_proposal','model':proposal['model'],'job_id':jid,'intent':req['intent'],'proposal_sha256':sha(p.read_text())}
            font_config=root/'font-faces.json'
            if font_config.exists():s['font_faces']=json.loads(font_config.read_text())
            changed=patch_page(s,operations);changed.update(revision=s['revision']+1,version_id=uuid.uuid4().hex,parent_version_id=s['version_id'],provenance=provenance,created_at=stamp(),human_review='pending')
            target=versions/f'{changed["revision"]:08d}.json';tmp=versions/('.'+uuid.uuid4().hex+'.tmp')
            try:
                with tmp.open('x') as stream:json.dump(changed,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
                os.link(tmp,target)
            finally:tmp.unlink(missing_ok=True)
            return jsonify(version_id=changed['version_id'],revision=changed['revision'])
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--store',required=True);args=parser.parse_args()
    create_app(args.store).run(host='127.0.0.1',port=5320,threaded=True)
