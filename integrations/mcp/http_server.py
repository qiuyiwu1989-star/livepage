"""Streamable HTTP with independently revocable, collection-scoped client keys."""
import contextvars,hashlib,hmac,json,os,time
from pathlib import Path
from bridge import API,Bridge
from server import create_server
current=contextvars.ContextVar('livepage_client')
class ScopedBridge:
    def search_content(self,query:str='',collection_id:str='',offset:int=0,limit:int=12):return current.get().search_content(query,collection_id,offset,limit)
    def list_collections(self):return current.get().list_collections()
    def read_content(self,content_id:str):return current.get().read_content(content_id)
    def read_context(self,content_id:str):return current.get().read_context(content_id)
    def list_assets(self,content_id:str):return current.get().list_assets(content_id)
    def get_asset(self,content_id:str,kind:str):return current.get().get_asset(content_id,kind)

class ClientAuth:
    def __init__(self,app,registry,api):self.app=app;self.registry=Path(registry);self.api=api
    def resolve(self,authorization):
        if not authorization.startswith('Bearer '):return None
        digest=hashlib.sha256(authorization[7:].encode()).hexdigest()
        try:records=json.loads(self.registry.read_text()).get('clients',[])
        except (OSError,ValueError):return None
        for client in records:
            if hmac.compare_digest(digest,client.get('token_sha256','')) and not client.get('revoked') and client.get('expires_at',0)>time.time():
                return Bridge(self.api,client.get('allowed_decks',[]),client.get('asset_download') is True)
        return None
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        headers=dict(scope.get('headers',[]));auth=headers.get(b'authorization',b'').decode(errors='replace')
        bridge=self.resolve(auth)
        if bridge is None:
            await send({'type':'http.response.start','status':401,'headers':[(b'content-type',b'application/json'),(b'cache-control',b'no-store'),(b'www-authenticate',b'Bearer realm="LivePage"')]})
            await send({'type':'http.response.body','body':b'{"error":"Valid LivePage client key required"}'})
            return
        token=current.set(bridge)
        try:await self.app(scope,receive,send)
        finally:current.reset(token)

service=create_server(ScopedBridge(),stateless_http=True,json_response=True,
    transport_security=__import__('mcp.server.transport_security',fromlist=['TransportSecuritySettings']).TransportSecuritySettings(
        enable_dns_rebinding_protection=True,allowed_hosts=['127.0.0.1','localhost','127.0.0.1:*','localhost:*','qiuyiwu.com'],allowed_origins=['https://qiuyiwu.com']))
app=ClientAuth(service.streamable_http_app(),os.environ.get('LIVEPAGE_MCP_CLIENTS','/etc/livepage-mcp/clients.json'),API(os.environ.get('LIVEPAGE_API_BASE','http://127.0.0.1:5298')))
