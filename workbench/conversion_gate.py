"""Blocking checks for candidates; never assigns human acceptance."""
import re

def inspect_slide(slide):
    issues=[]
    def visit(value,path='root'):
        if isinstance(value,dict):
            if value.get('type') in ('image','qr') and not value.get('src'):
                issues.append({'code':'missing_asset','path':path})
            for k,v in value.items():
                if k in ('text','lines','head','body'):
                    text=' '.join(map(str,v)) if isinstance(v,list) else str(v)
                    if any(0xe000<=ord(c)<=0xf8ff or c=='\ufffd' for c in text):issues.append({'code':'suspect_text','path':path+'.'+k})
                if k=='text_conf' and isinstance(v,(float,int)) and v<.8:issues.append({'code':'low_text_confidence','path':path})
                visit(v,path+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,f'{path}[{i}]')
    visit(slide)
    c=slide.get('confidence') or {}
    if c.get('text',1)<.8:issues.append({'code':'low_page_text_confidence','path':'confidence.text'})
    return {'status':'blocked' if issues else 'visual_review_pending','issues':issues,'human_review':'pending'}
