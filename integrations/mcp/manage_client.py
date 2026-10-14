"""Owner-only client provisioning. Never prints a key; writes a 0600 secret file."""
import argparse,hashlib,json,os,secrets,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--registry',type=Path,required=True);p.add_argument('--client',required=True);p.add_argument('--deck',action='append',default=[]);p.add_argument('--secret-file',type=Path);p.add_argument('--revoke',action='store_true');p.add_argument('--days',type=int,default=30);a=p.parse_args()
d=json.loads(a.registry.read_text()) if a.registry.exists() else {'clients':[]}
rows=d['clients'];rows[:]=[c for c in rows if c['client_id']!=a.client]
if not a.revoke:
 if not a.deck or len(a.deck)>20 or not a.secret_file or not 1<=a.days<=90:p.error('Supply 1-20 decks, secret file and 1-90 days')
 key=secrets.token_urlsafe(48);a.secret_file.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(a.secret_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:f.write(key+'\n')
 rows.append({'client_id':a.client,'token_sha256':hashlib.sha256(key.encode()).hexdigest(),'allowed_decks':a.deck,'asset_download':True,'expires_at':int(time.time()+a.days*86400)})
a.registry.parent.mkdir(parents=True,exist_ok=True);tmp=a.registry.with_suffix('.tmp');tmp.write_text(json.dumps(d));tmp.chmod(0o600);tmp.replace(a.registry)
print('Client revoked' if a.revoke else 'Client created; secret saved privately')
