"""Scoped read-only adapter over LivePage's existing business API."""
import base64, hashlib, json
from urllib.parse import urlsplit, urlencode, quote
from urllib.request import build_opener, HTTPRedirectHandler, Request

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Upstream redirect rejected; verify the API/tunnel')

class API:
    def __init__(self, base):
        u=urlsplit(base)
        if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or u.username or u.password or u.query or u.fragment:
            raise ValueError('Use a trusted loopback LivePage API or SSH tunnel')
        self.base=base.rstrip('/');self.opener=build_opener(NoRedirect)
    def fetch(self,path,limit=2_000_000):
        if not path.startswith('/') or path.startswith('//') or '..' in path:
            raise ValueError('Invalid API path')
        try:
            with self.opener.open(Request(self.base+path),timeout=15) as response:
                raw=response.read(limit+1);mime=response.headers.get_content_type()
        except Exception:
            raise ValueError('LivePage request failed; verify service, tunnel, resource and scope') from None
        if len(raw)>limit:raise ValueError('Response exceeds size limit')
        return raw,mime
    def get(self,path):
        raw,mime=self.fetch(path,8_000_000)
        if mime!='application/json':raise ValueError('API did not return JSON')
        return json.loads(raw)

class Bridge:
    def __init__(self,api,decks,asset_download=False):
        if not decks or len(decks)>20 or any(not isinstance(d,str) or not d for d in decks):raise ValueError('Explicit allowed_decks is required')
        self.api=api;self.decks=set(decks);self.asset_download=asset_download
    def _deck(self,deck):
        if deck not in self.decks:raise ValueError('Collection is outside this connection scope')
    def page(self,page_id):
        p=self.api.get('/api/library/page/'+quote(page_id,safe=''))
        self._deck(p.get('deck_id'));return p
    def list_collections(self):
        d=self.api.get('/api/prep/courses')
        return [{'collection_id':c['deck_id'],'title':c.get('title'),'page_count':c.get('page_count')} for c in d.get('courses',[]) if c['deck_id'] in self.decks]
    def search_content(self,query='',collection_id='',offset=0,limit=12):
        if offset<0 or not 1<=limit<=50 or len(query)>500:raise ValueError('Invalid search bounds')
        if collection_id:self._deck(collection_id)
        # A cursor is an offset within each permitted collection, not a global ranking.
        out=[];totals={}
        for deck in sorted([collection_id] if collection_id else self.decks):
            d=self.api.get('/api/library?'+urlencode({'deck':deck,'q':query,'offset':offset,'limit':limit}))
            totals[deck]=d.get('total',0)
            for p in d.get('pages',[]):
                if p.get('deck_id')!=deck:continue
                out.append({'content_id':p['page_id'],'collection_id':deck,'title':p.get('title'),
                            'snippet':str(p.get('reading_summary') or p.get('summary') or '')[:350],
                            'page_number':p.get('page_number'),'has_html':bool(p.get('has_html'))})
        return {'items':out,'totals_by_collection':totals,'offset_per_collection':offset,'limit_per_collection':limit,
                'retrieval':'keyword_all_terms; not semantic ranking','next_offsets':{d:offset+limit for d,n in totals.items() if offset+limit<n}}
    def read_content(self,content_id):
        p=self.page(content_id);a=p.get('annotation') or {}
        return {'content_id':p['page_id'],'atom_id':p.get('atomic_id') or p.get('atom_id'),'title':p.get('title'),
                'source':{'collection_id':p['deck_id'],'page_number':p.get('page_number'),
                          'image_sha256':(p.get('image') or {}).get('sha256'),'html_sha256':(p.get('html') or {}).get('sha256')},
                'slide_text':a.get('source_text',''),'ai_interpretation':a.get('vlm_summary') or a.get('ai_summary') or a.get('summary'),
                'review_status':p.get('human_review','pending'),'processing':p.get('processing',{}),
                'usage_permission':'unknown; access does not imply publication rights','speaker_quote':None}
    def read_context(self,content_id):
        p=self.page(content_id);n=p.get('navigation') or {}
        # Never return a neighboring ID before checking its collection scope.
        neighbors={}
        for key in ('previous','next'):
            if n.get(key):
                v=self.page(n[key]);neighbors[key]={'content_id':v['page_id'],'title':v.get('title'),'page_number':v.get('page_number')}
        return {'content_id':p['page_id'],'collection_id':p['deck_id'],'position':n.get('position'),'total':n.get('total'),'neighbors':neighbors}
    def list_assets(self,content_id):
        p=self.page(content_id);items=[]
        for kind in ('thumbnail','image','html'):
            ref=p.get(kind) or {}
            if ref.get('url') and ref.get('status') in ('local_exists','unverified_remote'):
                items.append({'kind':kind,'sha256':ref.get('sha256'),'availability':ref.get('status'),
                              'validation_status':ref.get('validation_status','unknown'),
                              'uri':'livepage://asset/'+quote(content_id,safe='')+'/'+kind})
        return {'content_id':content_id,'assets':items,'download_enabled':self.asset_download,'publication_permission':'unknown'}
    def get_asset(self,content_id,kind):
        if not self.asset_download:raise ValueError('Asset download is disabled for this connection')
        if kind not in ('thumbnail','image','html'):raise ValueError('Unsupported asset kind')
        p=self.page(content_id);ref=p.get(kind) or {};path=ref.get('url','')
        # The API cannot turn this adapter into a filesystem or arbitrary URL reader.
        if path.startswith('/admin/livepage/'):path=path[len('/admin/livepage'):]
        if '%' in path:raise ValueError('Encoded asset paths are not supported')
        if not path.startswith(('/images/','/thumbs/','/slides/','/assets/','/imports/')) or path.startswith('//') or '..' in path or '?' in path or '#' in path:
            raise ValueError('Asset path is not a permitted local media path')
        raw,mime=self.api.fetch(path)
        if mime not in ('image/jpeg','image/png','image/webp','text/html'):raise ValueError('Unsupported media type')
        digest=hashlib.sha256(raw).hexdigest()
        if ref.get('sha256') and digest!=ref['sha256']:raise ValueError('Asset changed; refresh source version before use')
        return {'content_id':content_id,'kind':kind,'mime_type':mime,'sha256':digest,'bytes':len(raw),
                'data_base64':base64.b64encode(raw).decode(),'publication_permission':'unknown'}
