"""Source-first PDF scene candidate: retain graphics paths/images; text stays HTML.
Inputs are explicit, outputs immutable per run. No personal paths in the module.
"""
import base64,hashlib,html,io,json,re,xml.etree.ElementTree as ET
from pathlib import Path
import pymupdf
from fontTools import subset
from fontTools.ttLib import TTFont
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def font_payload(path,text):
    font=TTFont(path);cmap=font.getBestCmap();points=set(map(ord,text));missing=points-set(cmap)
    # Whitespace may have no glyph; all actual visible characters must be covered.
    missing={x for x in missing if not chr(x).isspace()}
    if missing:raise ValueError('Font missing codepoints: '+str(sorted(missing)))
    units=font['head'].unitsPerEm
    baseline=.5+(font['hhea'].ascent+font['hhea'].descent)/(2*units)
    options=subset.Options();options.layout_features=['*'];options.recalc_timestamp=False
    sub=subset.Subsetter(options=options);sub.populate(unicodes=points);sub.subset(font);font.flavor='woff2'
    out=io.BytesIO();font.save(out)
    return base64.b64encode(out.getvalue()).decode(),baseline


def extract_scene(pdf,page_index,decode=None):
    doc=pymupdf.open(pdf);page=doc[page_index];w,h=page.rect.width,page.rect.height
    svg=ET.fromstring(page.get_svg_image(text_as_path=False))
    # Keep PDF paths rather than replacing their bounding boxes with rectangles.
    for parent in list(svg.iter()):
        for child in list(parent):
            if child.tag.rsplit('}',1)[-1]=='text':parent.remove(child)
    spans=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            for span in line['spans']:
                if not span['text'].strip():continue
                if line.get('dir')!=(1.0,0.0):raise ValueError('Rotated text requires explicit handling')
                x0,y0,x1,y1=span['bbox']
                if x1<=0 or y1<=0 or x0>=w or y0>=h:continue
                t=decode(span['text'],span['font']) if decode else span['text']
                spans.append({'text':t,'font':span['font'],'size':span['size'],'color':span['color'],
                              'origin':list(span['origin']),'bbox':list(span['bbox']),'role':'unassigned'})
    return {'schema':'source-scene/0.1','size':[w,h],'source_sha256':hashlib.sha256(Path(pdf).read_bytes()).hexdigest(),
            'pdf_page':page_index,'graphics_svg':ET.tostring(svg,encoding='unicode'),'text':spans,
            'limitations':['semantic grouping pending','text composited above graphics; layering needs review'],
            'human_review':'pending'}


def preserve_text_regions(scene, pdf, indices, reason):
    """Explicit source-raster fallback; retain decoded text and mark non-editable."""
    doc=pymupdf.open(pdf)
    try:
        page=doc[scene['pdf_page']]
        for i in indices:
            block=scene['text'][i]
            rect=pymupdf.Rect(block['bbox']) & page.rect
            if rect.is_empty:raise ValueError('Empty text fallback region')
            pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=rect,alpha=True)
            block['source_raster']={'png':base64.b64encode(pix.tobytes('png')).decode(),
                'bbox':list(rect),'reason':reason,'editable':False,
                'source_sha256':scene['source_sha256'],'review_status':'pending'}
    finally:doc.close()
    scene['limitations'].append('Some text regions retain source raster; not editable')


def render_scene(scene,font_resolver):
    fonts={};groups={}
    for b in scene['text']:
        if b.get('source_raster'):continue
        if any(0xe000<=ord(c)<=0xf8ff or 0xac00<=ord(c)<=0xd7ff or c=='\ufffd' for c in b['text']):
            raise ValueError('Suspect decoded text requires a source-linked correction')
    for b in scene['text']:
        if not b.get('source_raster'):groups.setdefault(b['font'],[]).append(b['text'])
    css=[]
    for i,(name,parts) in enumerate(groups.items()):
        payload,baseline=font_payload(font_resolver(name),''.join(parts));fonts[name]=(f'f{i}',baseline)
        css.append(f'@font-face{{font-family:f{i};src:url(data:font/woff2;base64,{payload}) format("woff2");font-display:block}}')
    w,h=scene['size'];cq=lambda v:f'{v/w*100:.6f}cqw'
    blocks=[]
    for i,b in enumerate(scene['text']):
        if b.get('source_raster'):
            r=b['source_raster'];x0,y0,x1,y1=r['bbox']
            blocks.append(f'<img data-block="{i}" data-editable="false" title="Source text region; editing pending" alt="{html.escape(b["text"],quote=True)}" style="position:absolute;left:{cq(x0)};top:{cq(y0)};width:{cq(x1-x0)};height:{cq(y1-y0)}" src="data:image/png;base64,{r["png"]}">')
            continue
        family,baseline=fonts[b['font']];x,y=b['origin'];size=b['size']
        blocks.append(f'<span class="text" data-block="{i}" style="left:{cq(x)};top:{cq(y-baseline*size)};font-family:{family};font-size:{cq(size)};color:#{b["color"]:06x}">{html.escape(b["text"])}</span>')
    svg=scene['graphics_svg'];svg=re.sub(r'<(?:ns\d+:)?svg\b',lambda m:m[0]+' class="graphics"',svg,count=1)
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>'+''.join(css)+f'html,body{{margin:0;background:#ddd}}.slide{{position:relative;width:100vw;aspect-ratio:{w}/{h};container-type:inline-size;overflow:hidden}}.graphics{{position:absolute;width:100%;height:100%;inset:0}}.text{{position:absolute;white-space:pre;line-height:1;font-synthesis:none}}</style><article class="slide">'+svg+''.join(blocks)+'</article></html>'
