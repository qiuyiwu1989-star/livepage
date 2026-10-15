"""Semantic table HTML renderer. Themes change presentation, never source identity."""
import html
import json


def validate_table(doc):
    rows=doc.get('rows',[])
    if len(rows)<2:raise ValueError('Header and body rows required')
    width=len(rows[0]['cells']);ids=[]
    if width<2:raise ValueError('Row header and value columns required')
    for row in rows:
        if len(row['cells'])!=width:raise ValueError('Ragged table')
        for cell in row['cells']:
            if not isinstance(cell.get('text'),str) or not cell.get('id'):raise ValueError('Cell identity/text required')
            ids.append(cell['id'])
    if len(set(ids))!=len(ids):raise ValueError('Duplicate cell identity')
    return rows


def render_table(doc,theme='source',font_css='',logo_svg='',font_map=None):
    rows=validate_table(doc)
    font_map=font_map or {}
    if theme not in {'source','yongle'}:raise ValueError('Unknown theme')
    def cell(c,tag,scope=None,step=None):
        attributes=f' data-lp-object-id="{html.escape(c["id"],quote=True)}" data-lp-cell-id="{html.escape(c["id"],quote=True)}"'
        if scope:attributes+=f' scope="{scope}"'
        if step is not None:attributes+=f' data-step="{step}"'
        content=html.escape(c['text'])
        if theme=='source' and c.get('runs'):
            content=''.join('<span style="font-family:'+html.escape(font_map.get(r['font'],'lp-sans'),quote=True)+';color:'+html.escape(r['color'],quote=True)+'">'+html.escape(r['text'])+'</span>' for r in c['runs'])
        return f'<{tag}{attributes}>{content}</{tag}>'
    if theme=='source':
        head=''.join(cell(c,'th','col') for c in rows[0]['cells'])
        body=''.join('<tr>'+''.join(cell(c,'th' if i==0 else 'td','row' if i==0 else None) for i,c in enumerate(row['cells']))+'</tr>' for row in rows[1:])
    else:
        head=cell(rows[0]['cells'][0],'th','col')+''.join(cell(row['cells'][0],'th','col',i) for i,row in enumerate(rows[1:],1))
        body=''.join('<tr>'+cell(rows[0]['cells'][i],'th','row')+''.join(cell(row['cells'][i],'td',step=j) for j,row in enumerate(rows[1:],1))+'</tr>' for i in range(1,len(rows[0]['cells'])))
    metadata={'schema':'livepage-html-table/0.1','atom_id':doc['atom_id'],'source_sha256':doc['source_sha256'],'theme':theme,'human_review':'pending'}
    common='''*{box-sizing:border-box}html,body{margin:0;background:#202636}.slide{position:relative;width:100vw;aspect-ratio:16/9;container-type:inline-size;overflow:hidden;font-family:lp-sans,"PingFang SC",sans-serif}h1{margin:0;font-weight:700}table{table-layout:fixed;border-collapse:collapse}th,td{overflow-wrap:anywhere;vertical-align:middle;text-align:center}th{font-weight:700}button{font:inherit;cursor:pointer}.controls{display:flex;align-items:center;justify-content:center;gap:12px;padding:14px;color:#fff;font:14px system-ui}.controls button{padding:8px 14px;border:1px solid #74684b;border-radius:22px;background:#17213e;color:#f6e8c7}body:not([data-playing]) [data-step]{opacity:1}.controls[hidden]{display:none}@media print{html,body{background:white}.controls{display:none}[data-step]{opacity:1!important;transform:none!important}.slide{break-inside:avoid}}@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}[data-step]{opacity:1!important}}'''
    source='''.slide{background:#eaf4f6;color:#000}h1{position:absolute;left:4.58%;top:7.2%;font-size:2.6cqw;color:#100735}table{position:absolute;left:5.94%;top:18.05%;width:88.12%;height:68.52%;font-size:1.5625cqw;line-height:1.4}th,td{padding:.55cqw;border-right:1px dotted #444;border-bottom:1px dotted #444}tr>*:last-child{border-right:0}tbody tr:last-child>*{border-bottom:0}thead{height:16.5%}tbody tr:nth-child(1),tbody tr:nth-child(2){height:29.7%}tbody tr:last-child td:nth-child(3),tbody tr:last-child td:nth-child(6){color:#7234f4;font-weight:700}.logo{position:absolute;right:3.5%;top:3%;width:9.5%;height:8%}'''
    yongle='''.slide{--night:#050B22;--paper:#F4EFE3;--gold:#D4A858;--blue:#8FAAD5;background:linear-gradient(125deg,var(--night),#0E1F4D);color:var(--paper);padding:4.5cqw 6cqw}.eyebrow{font-size:.85cqw;letter-spacing:.18em;color:var(--gold);margin:0 0 1.25cqw}h1{font-weight:500;font-size:2.7cqw;line-height:1.15;margin-bottom:2.4cqw}table{width:100%;font-size:1.3cqw;line-height:1.35}thead th{color:var(--gold);font-size:1.55cqw;padding:1cqw .9cqw;border-bottom:2px solid #d4a85888}thead th:first-child,tbody th{width:16%;text-align:left}tbody th{color:var(--blue);font-weight:500}td,tbody th{padding:.68cqw .9cqw;border-bottom:1px solid #ffffff20}td{width:28%}tbody tr:last-child>*{border-bottom:0}[data-step]{transition:opacity .45s ease,background .45s ease}body[data-playing] [data-step]:not(.revealed){opacity:0}body[data-playing] [data-step].current{background:#d4a85812}.theme-note{position:absolute;right:6cqw;bottom:1.3cqw;color:#8faad5;font-size:.7cqw}'''
    logo=f'<div class="logo">{logo_svg}</div>' if theme=='source' else ''
    eyebrow='<p class="eyebrow">COMPARISON · 三种公司形态</p>' if theme=='yongle' else ''
    title=html.escape(doc['title']);controls=''
    if theme=='yongle':controls='''<div class="controls"><button id="start">分步呈现</button><button id="back" disabled>←</button><span id="count">完整对照</span><button id="next" disabled>→</button><button id="all">展示全部</button></div><script>(()=>{let step=0;const body=document.body,els=[...document.querySelectorAll('[data-step]')],$=id=>document.getElementById(id);function update(n){step=Math.max(0,Math.min(3,n));for(const el of els){el.classList.toggle('revealed',Number(el.dataset.step)<=step);el.classList.toggle('current',Number(el.dataset.step)===step)}$('count').textContent=step+' / 3';$('back').disabled=step===0;$('next').disabled=step===3}$('start').onclick=()=>{body.dataset.playing='true';update(1)};$('back').onclick=()=>update(step-1);$('next').onclick=()=>update(step+1);$('all').onclick=()=>{delete body.dataset.playing;$('count').textContent='完整对照';$('back').disabled=true;$('next').disabled=true};document.addEventListener('keydown',e=>{if(!body.dataset.playing||e.target.closest('input,textarea,select,button,[contenteditable]')||getSelection()?.toString())return;if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();update(step+1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();update(step-1)}if(e.key==='Escape')$('all').click()})})()</script>'''
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+font_css+common+(source if theme=='source' else yongle)+'</style></head><body><section class="slide" data-slide="'+html.escape(doc['atom_id'])+'">'+logo+eyebrow+'<h1 data-lp-object-id="'+doc['atom_id']+'-title">'+title+'</h1><table data-lp-table-id="'+doc['atom_id']+'-table"><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table></section>'+controls+'<script type="application/json" id="lp-provenance">'+json.dumps(metadata,ensure_ascii=False).replace('</','<\\/')+'</script></body></html>'
