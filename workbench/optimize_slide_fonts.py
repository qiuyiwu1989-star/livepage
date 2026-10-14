"""Subset embedded fonts for a static slide; preserve source bytes and glyph design.
Usage: python optimize_slide_fonts.py original.html --out candidate.html
Never rewrites input. This is packaging validation, not visual acceptance.
"""
import argparse, base64, hashlib, io, json, re
from html.parser import HTMLParser
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.depth=0; self.text=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('style','script'): self.depth+=1
        for key,value in attrs:
            if key in ('aria-label','alt') and value: self.text.append(value)
    def handle_endtag(self, tag):
        if tag in ('style','script'): self.depth=max(0,self.depth-1)
    def handle_data(self, data):
        if not self.depth: self.text.append(data)

FONT=re.compile(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)')
def optimize(source):
    if re.search(r'<script\b|(?<![\w-])content\s*:',source,re.I):
        raise ValueError('Dynamic or CSS-generated text requires an explicit character manifest')
    parser=VisibleText();parser.feed(source)
    points=set(map(ord,''.join(parser.text)))
    records=[]
    def replace(match):
        raw=base64.b64decode(match[1],validate=True);font=TTFont(io.BytesIO(raw))
        cmap=font.getBestCmap() or {};covered=points & cmap.keys()
        before={cp:font['hmtx'][cmap[cp]] for cp in covered}
        options=subset.Options();options.layout_features=['*'];options.recalc_timestamp=False
        sub=subset.Subsetter(options=options);sub.populate(unicodes=covered);sub.subset(font);font.flavor='woff2'
        output=io.BytesIO();font.save(output);candidate=output.getvalue()
        check=TTFont(io.BytesIO(candidate));after=check.getBestCmap() or {}
        if any(cp not in after or check['hmtx'][after[cp]]!=metrics for cp,metrics in before.items()):
            raise ValueError('Subset changed character coverage or advance metrics')
        # Never enlarge an already small font.
        result=candidate if len(candidate)<len(raw) else raw
        records.append({'before':len(raw),'after':len(result),'characters':len(covered),'metrics_preserved':True})
        return 'data:font/woff2;base64,'+base64.b64encode(result).decode()
    output=FONT.sub(replace,source)
    return output,{'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'output_sha256':hashlib.sha256(output.encode()).hexdigest(),
                   'before_bytes':len(source.encode()),'after_bytes':len(output.encode()),'fonts':records,
                   'status':'packaging_checked_visual_review_pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.source.resolve()==a.out.resolve():p.error('Output must differ from immutable source')
    output,report=optimize(a.source.read_text());a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(output);a.out.with_suffix('.font-qa.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
