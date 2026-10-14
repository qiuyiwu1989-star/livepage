from pathlib import Path
import json,hashlib,argparse
from fontTools import subset
from fontTools.ttLib import TTFont
parser=argparse.ArgumentParser(description='Subset existing reader fonts without changing glyph design');parser.add_argument('--codepoints',type=Path,required=True);parser.add_argument('--font-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
points=json.loads(args.codepoints.read_text());out=args.output;out.mkdir(parents=True,exist_ok=True)
css=[]
for family,filebase in [('QiuSerif','SourceHanSerifCN'),('QiuSans','SourceHanSansCN')]:
 for weight,suffix in [(400,'Regular'),(700,'Bold')]:
  source=args.font_dir/(filebase+'-'+suffix+'.otf');font=TTFont(source)
  covered=sorted(set(points)&set(font.getBestCmap()))
  options=subset.Options();options.flavor='woff2';options.recalc_timestamp=False;options.layout_features=['*']
  sub=subset.Subsetter(options=options);sub.populate(unicodes=covered);sub.subset(font);font.flavor='woff2'
  digest=hashlib.sha256(bytes(source.read_bytes())+json.dumps(covered).encode()).hexdigest()[:12];name=f'{family}-{weight}-{digest}.woff2';font.save(out/name)
  ranges=','.join('U+'+format(c,'X') for c in covered)
  css.append(f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:normal;font-display:swap;src:url("fonts/{name}") format("woff2");unicode-range:{ranges};}}')
  print(family,weight,'bytes',source.stat().st_size,'->',(out/name).stat().st_size,flush=True)
(out/'subset-fonts.css').write_text('\n'.join(css))
