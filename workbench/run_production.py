import os
from pathlib import Path
from workspace_server import create_app
from flask import request
app=create_app(Path(__file__).parent)
# Explicit public origins; never trust client-supplied forwarded headers.
app.config['TRUSTED_WRITE_ORIGINS']=tuple(x.strip() for x in os.environ.get('LIVEPAGE_WRITE_ORIGINS','https://qiuyiwu.com').split(',') if x.strip())
def urls(v):
 if isinstance(v,dict):return {k:urls(x) for k,x in v.items()}
 if isinstance(v,list):return [urls(x) for x in v]
 if isinstance(v,str) and v.startswith('/') and not v.startswith('//') and not v.startswith('/admin/livepage/'):
  return '/admin/livepage'+v
 return v
@app.after_request
def scope_response(response):
 if response.is_json and not response.direct_passthrough:
  payload=response.get_json(silent=True)
  if payload is not None:response.set_data(app.json.dumps(urls(payload)))
 if response.headers.get('Location','').startswith('/'):
  response.headers['Location']='/admin/livepage'+response.headers['Location']
 return response
@app.before_request
def private_paths():
 if request.path.endswith(('.env','.pem','.key','.py')) or request.path.startswith(('/data/assemblies/','/data/prep-proposals/','/workspace/')):return '',404
