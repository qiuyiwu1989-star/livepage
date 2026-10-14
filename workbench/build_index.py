#!/usr/bin/env python3
"""Build the atom gallery index page (search + filter by framework/status)."""
import json, html
from framework_labels import normalize
from image_governance import representative_override
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "atom-pages"
idx = json.loads((OUT / "index.json").read_text(encoding="utf-8"))
atoms = idx["atoms"]

def esc(s): return html.escape(str(s), quote=True)

# Facets normalize naming only; original model wording stays in each record.
frames = {}
for a in atoms:
    labels,state=normalize(a.get('frame'))
    a['framework_labels']=labels;a['framework_label_status']=state
    for label in labels:frames[label]=frames.get(label,0)+1
    if state in ('pending','unassigned'):
        label='待核验关联' if state=='pending' else '未标注框架'
        frames[label]=frames.get(label,0)+1
frame_opts = ''.join(f'<option value="{esc(k)}">{esc(k)} ({v})</option>' for k,v in sorted(frames.items(),key=lambda x:-x[1]))

PAGE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>活页库 · 活页 LivePage</title>
<link rel="stylesheet" href="../assets/editor-fonts.css"><style>
:root{--paper:#faf8f3;--ink:#221e1a;--ink2:#57524a;--ink3:#8a8377;--line:#e0d9cb;--card:#fffefb;--accent:#8e4231;--accent-soft:#f4e7e2;--green:#2f6b4f;--green-soft:#e7f0ea;--serif:"QiuSerif","Noto Serif SC","Songti SC",Georgia,serif;--sans:"QiuSans","Noto Sans SC",-apple-system,"PingFang SC",sans-serif;--mono:"JetBrains Mono",Menlo,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.7}
.wrap{max-width:1320px;margin:0 auto;padding:40px 32px 90px}
.eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--accent);margin:0 0 12px}
h1{font-family:var(--serif);font-size:clamp(1.8rem,4vw,2.6rem);font-weight:600;margin:0 0 10px;line-height:1.25}
.lead{font-family:var(--serif);font-size:1.1rem;color:var(--ink2);max-width:44em;margin:0 0 8px}
.stats{display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 26px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:13px;padding:12px 18px;min-width:120px}
.stat .n{font-family:var(--serif);font-style:italic;font-size:1.7rem;color:var(--accent);line-height:1}
.stat .l{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);margin-top:4px}
.controls{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:12px;margin:0 0 26px;align-items:center}
@media(max-width:820px){.controls{grid-template-columns:1fr}}
.controls input,.controls select{width:100%;border:1.5px solid var(--line);border-radius:11px;padding:12px 15px;font-family:var(--sans);font-size:.95rem;background:var(--card);color:var(--ink)}
.controls input:focus,.controls select:focus{outline:none;border-color:var(--accent)}
.count{font-family:var(--mono);font-size:11.5px;color:var(--ink3);letter-spacing:.05em;white-space:nowrap}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:15px;overflow:hidden;text-decoration:none;color:inherit;transition:.15s;display:flex;flex-direction:column}
.card:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 14px 34px rgba(50,40,30,.08)}
.card .ph{aspect-ratio:16/9;background:#f4f4ec;overflow:hidden}
.card .ph img:not([src]){opacity:0}.card .ph img{width:100%;height:100%;object-fit:contain;display:block}
.card .cb{padding:14px 16px;flex:1}
.card .aid{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--accent);margin-bottom:5px}
.card .t{font-family:var(--serif);font-size:1.02rem;line-height:1.5;font-weight:500;margin:0 0 8px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .meta{display:flex;flex-wrap:wrap;gap:6px;font-family:var(--mono);font-size:10px;color:var(--ink3)}
.card .meta .chip{background:#f2efe7;border-radius:20px;padding:2px 9px}
.card .meta .chip.hot{background:var(--accent-soft);color:var(--accent)}
.empty-note{font-family:var(--mono);font-size:12px;color:var(--ink3);padding:40px 0;text-align:center}
footer{margin-top:60px;padding-top:22px;border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;color:var(--ink3);line-height:2}
.course-shortcuts{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0 28px}.course-shortcuts a{display:flex;align-items:center;gap:10px;padding:10px 15px;background:var(--card);border:1px solid var(--line);border-radius:12px;text-decoration:none;color:var(--ink2);font-family:var(--sans);font-size:14px}.course-shortcuts a[aria-current=page]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}.course-shortcuts small{font-size:12px;color:var(--ink3)}.stats{display:none}
.image-problem{display:flex;align-items:center;justify-content:center;width:100%;height:100%;background:var(--paper);color:var(--ink3);font:13px var(--sans);padding:16px;text-align:center}.title-candidate{font:11px var(--sans);color:var(--ink3)}.aid:empty{display:none}
.library-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.prep-entry{font:14px var(--sans);padding:12px 18px;border:1px solid var(--line);border-radius:999px;text-decoration:none;color:var(--accent);white-space:nowrap}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">活页 LivePage</div><nav class="course-shortcuts" aria-label="工作区"><a href="index.html">活页库</a><a href="../assembly.html">我的备课</a><a href="../library.html?processing=1">导入与处理</a></nav>
  <div class="library-heading"><h1>活页库</h1><a class="prep-entry" href="../assembly.html">备课工作区 →</a></div>
  <p class="lead">按熟悉的课程找内容，再把需要的页面加入备课。</p>

  <nav class="course-shortcuts" aria-label="按课程浏览" id="courses">正在读取课程…</nav><p id="processing-summary" class="lead" role="status">正在核对处理进度…</p>
  <div class="stats">
    <div class="stat"><div class="n">__TOTAL__</div><div class="l">原子页</div></div>
    <div class="stat"><div class="n">__FRAMES__</div><div class="l">框架覆盖</div></div>
    <div class="stat"><div class="n">__CLAIMS__</div><div class="l">有主张</div></div>
    <div class="stat"><div class="n">__TEXTS__</div><div class="l">有原文</div></div>
    <div class="stat"><div class="n">2228</div><div class="l">高清图 · COS</div></div>
  </div>

  <div class="controls">
    <input id="q" type="search" placeholder="搜索标题 / 主题 / section / 框架…" autocomplete="off">
    <select id="ff"><option value="">框架关联（AI 候选）</option>__FRAME_OPTS__</select>
    <select id="st">
      <option value="">全部状态</option>
      <option value="claims">有核心主张</option>
      <option value="texts">有原文</option>
      <option value="multi">多次复用</option>
      <option value="blank">空白页</option>
    </select>
    <select id="html-filter" aria-label="HTML 转换状态"><option value="">全部格式</option><option value="available">已有 HTML 草稿</option><option value="pending">HTML 待验收</option><option value="recorded">清单标记已比对</option><option value="missing">尚无 HTML 记录</option></select>
    <span class="count" id="cnt">__TOTAL__ / __TOTAL__</span>
  </div>

  <div class="grid" id="grid"></div>
  <button id="load-more" type="button" style="display:block;margin:24px auto;padding:10px 24px;border:1px solid var(--line);border-radius:24px;background:var(--card);color:var(--ink);font:inherit;cursor:pointer" hidden>加载更多</button>
  <div id="load-sentinel" aria-hidden="true" style="height:1px"></div>
  <p id="load-progress" role="status" aria-live="polite" style="text-align:center;color:var(--ink3);font-size:13px"></p>
  <div class="empty-note" id="nores" hidden>没有匹配的知识单元</div>

  <footer>
    数据：生产 slide-library（1443 去重原子）· 卡片用缩略图（懒加载）· 详情页用高清原图 · 未对外发布 · noindex<br>
    每个卡片 = 一个独立生命周期档案页：①身份 ②表达 ③证据 ④讲述 ⑤复用 ⑥演化
  </footer>
</div>

<script>
const HTML_RECORDS = __HTML_RECORDS__;
const DATA = __DATA__;
const PREVIEWS = __PREVIEWS__;
const TITLE_OVERLAY = __TITLES__;
function applyTitle(a){const t=TITLE_OVERLAY[a.atom_id];if(t?.knowledge_title){a.original_title=a.original_title||a.title;a.title=t.knowledge_title;a.title_candidate=t.human_review!=='confirmed';}return a;}
DATA.forEach(applyTitle);
function previewImage(a){const sid=(a.hd||'').split('/').pop().replace(/\.jpg$/,'');const p=PREVIEWS[a.hd]||PREVIEWS[sid];const v=p?.variants||[];return {src:v[0]?.url||a.hd,srcset:v.map(x=>x.url+' '+x.width+'w').join(',')};}
const grid = document.getElementById('grid');
const cnt = document.getElementById('cnt');
const nores = document.getElementById('nores');
const q = document.getElementById('q');
const ff = document.getElementById('ff');
const st = document.getElementById('st');
const htmlFilter=document.getElementById('html-filter');
htmlFilter.value=new URLSearchParams(location.search).get('html')||'';
function htmlRecord(a){return HTML_RECORDS[a.atom_id]||a.html_record;}
function card(a){
  const conversion=htmlRecord(a);
  const destination=(a.detail_url||a.atom_id+'.html'+(a.occurrence_id?'?slide='+encodeURIComponent(a.occurrence_id):''));
  const preview=previewImage(a);
  const imageId=(a.hd||'').split('/').pop().replace(/\.jpg$/,'');
  const health=window.imageHealth;const white=health?.white.includes(imageId),black=health?.black.includes(imageId);
  const img = white||black ? '<div class="image-problem">'+(white?'源图片为空白 · 待恢复':'源图片为纯黑 · 待核验')+'</div>' : a.hd
    ? '<img data-src="'+esc(preview.src||'')+'" data-srcset="'+esc(preview.srcset)+'" sizes="(max-width:700px) 90vw, (max-width:1100px) 45vw, 430px" alt="'+esc(a.title)+'" loading="lazy" decoding="async">'
    : '<div style="display:flex;align-items:center;justify-content:center;height:100%;font-family:var(--mono);font-size:11px;color:#8a8377">无图</div>';
  return '<a class="card" href="'+esc(destination)+'"'+'>'
    + '<div class="ph">'+img+'</div>'
    + '<div class="cb">'
    + '<div class="aid">'+(a.page_number?'第 '+a.page_number+' 页':'')+'</div>'
    + '<p class="t">'+esc(a.title)+'</p>'+ (a.title_candidate?'<small class="title-candidate">知识标题候选 · 待确认</small>':'')
    + (conversion?'<small class="title-candidate">HTML 草稿 · '+(conversion.verified==='pixel-compare'?'清单标记已比对':'待验收')+'</small>':'')
    + '<div class="meta">'
    + '<span class="chip hot">'+esc((a.framework_labels||[]).join(' · ')||(a.framework_label_status==='pending'?'关联待核验':'未标注'))+'</span>'
    + '<span class="chip">'+esc(a.deck||'—')+'</span>'
    + '<span class="chip">×'+(a.uses||1)+'</span>'
    + (a.claimcount>0?'<span class="chip">'+a.claimcount+'主张</span>':'')
    + (a.is_blank?'<span class="chip">空白</span>':'')
    + '</div></div></a>';
}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
const PAGE_SIZE=24;
let filtered=[];
let shown=0;
const moreButton=document.getElementById('load-more');
function loadThumbnail(img){if(img.dataset.srcset)img.srcset=img.dataset.srcset;img.src=img.dataset.src;img.removeAttribute('data-src');img.removeAttribute('data-srcset');}
const thumbnailObserver=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{for(const item of entries){if(item.isIntersecting){loadThumbnail(item.target);thumbnailObserver.unobserve(item.target);}}},{rootMargin:'200px 0px'}):null;
function observeThumbnails(){grid.querySelectorAll('img[data-src]').forEach(img=>{if(thumbnailObserver)thumbnailObserver.observe(img);else loadThumbnail(img);});}
const sentinel=document.getElementById('load-sentinel');
const loadProgress=document.getElementById('load-progress');
let batchFrame=null;
function scheduleBatch(){if(batchFrame!==null||shown>=filtered.length)return;batchFrame=requestAnimationFrame(()=>{batchFrame=null;appendMore();});}
const batchObserver=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))scheduleBatch();},{rootMargin:'400px 0px'}):null;
if(batchObserver)batchObserver.observe(sentinel);
else window.addEventListener('scroll',onScroll,{passive:true});
moreButton.onclick=()=>appendMore();

function appendMore(){
  if(shown>=filtered.length) return;
  const next=filtered.slice(shown,shown+PAGE_SIZE).map(card).join('');
  grid.insertAdjacentHTML('beforeend',next);
  shown=Math.min(shown+PAGE_SIZE,filtered.length);
  observeThumbnails();moreButton.hidden=!!batchObserver||shown>=filtered.length;moreButton.textContent='加载更多 · 已显示 '+shown+' / '+filtered.length;
  loadProgress.textContent=shown<filtered.length?'已显示 '+shown+' / '+filtered.length+' · 下滑自动加载':(filtered.length?'已显示全部 '+shown+' 项':'');
  // If a batch does not fill the viewport, continue one batch per frame.
  if(batchObserver){batchObserver.unobserve(sentinel);if(shown<filtered.length)batchObserver.observe(sentinel);}
}
function render(){
  const term=(q.value||'').toLowerCase().trim();
  const fw=ff.value; const s=st.value;
  filtered=(window.coursePages||DATA).filter(function(a){
    const conversion=htmlRecord(a);const hs=htmlFilter.value;
    if(hs==='available'&&!conversion)return false;
    if(hs==='pending'&&(!conversion||conversion.verified==='pixel-compare'))return false;
    if(hs==='recorded'&&conversion?.verified!=='pixel-compare')return false;
    if(hs==='missing'&&conversion)return false;
    if(window.removedAtoms?.has(a.atom_id)) return false;
    if(window.topicAtoms && !window.topicAtoms.has(a.atom_id)) return false;
    if(fw && !(a.framework_labels||[]).includes(fw) && !(fw==='待核验关联'&&a.framework_label_status==='pending') && !(fw==='未标注框架'&&a.framework_label_status==='unassigned')) return false;
    if(s==='claims' && !(a.claimcount>0)) return false;
    if(s==='texts' && !(a.textcount>0)) return false;
    if(s==='multi' && !((a.uses||1)>1)) return false;
    if(s==='blank' && !a.is_blank) return false;
    if(!term) return true;
    return (a.title+' '+(a.topic||'')+' '+(a.section||'')+' '+(a.frame||'')+' '+a.atom_id).toLowerCase().indexOf(term)>=0;
  });
  if(batchFrame!==null){cancelAnimationFrame(batchFrame);batchFrame=null;}
  thumbnailObserver?.disconnect();grid.innerHTML=''; shown=0;
  appendMore();
  cnt.textContent=filtered.length+' / '+(window.coursePages||DATA).length+(window.coursePages?' 页':' 项内容');
  nores.hidden=filtered.length>0||window.courseLoading;
  if(window.courseLoading)cnt.textContent='正在读取课程… '+(window.coursePages||[]).length+' 页已加载';
}
let raf=null;
function onScroll(){
  if(raf) return;
  raf=requestAnimationFrame(function(){
    raf=null;
    if(shown>=filtered.length) return;
    const rect=grid.getBoundingClientRect();
    if(rect.bottom < window.innerHeight*2) appendMore();
  });
}
// Append bounded batches near the viewport; thumbnail loading remains independent.
q.addEventListener('input',render); ff.addEventListener('change',render); st.addEventListener('change',render);htmlFilter.addEventListener('change',()=>{const url=new URL(location.href);if(htmlFilter.value)url.searchParams.set('html',htmlFilter.value);else url.searchParams.delete('html');history.replaceState(null,'',url);render();});
fetch('/api/atom-removals').then(r=>r.json()).then(d=>{window.removedAtoms=new Set(d.deleted);render();}).catch(()=>{});
fetch('image-health.json').then(r=>r.json()).then(d=>{window.imageHealth=d;render();}).catch(()=>{});
const topic=new URLSearchParams(location.search).get('topic');
fetch('/api/library/processing').then(r=>{if(!r.ok)throw Error('处理状态读取失败');return r.json()}).then(d=>{
 const host=document.getElementById('courses');host.replaceChildren();
 const selected=new URLSearchParams(location.search).get('deck');
 const all=document.createElement('a');all.href='index.html';all.textContent='全部活页';if(!selected&&!topic)all.setAttribute('aria-current','page');host.append(all);
 for(const c of d.courses){const a=document.createElement('a');a.href='index.html?deck='+encodeURIComponent(c.deck_id);a.textContent=c.title+' · '+({keynote:'Keynote',pdf:'PDF',legacy:'历史课件'}[c.source_kind])+' · '+c.page_count+' 页';if(c.deck_id===selected)a.setAttribute('aria-current','page');host.append(a);}
 const rows=selected?d.courses.filter(c=>c.deck_id===selected):d.courses;
 const n=(stage,state)=>rows.reduce((sum,c)=>sum+(c.counts[stage][state]||0),0);
 document.getElementById('processing-summary').textContent='标注：'+n('annotation','pending')+' 页待处理，'+n('annotation','candidate')+' 页候选待确认，'+n('annotation','confirmed')+' 页已确认。HTML：'+n('html','pending')+' 页无草稿，'+n('html','draft')+' 页待验收，'+n('html','confirmed')+' 页已确认。任务：'+n('task','unregistered')+' 页未登记，'+n('task','queued')+' 页排队，'+n('task','running')+' 页处理中，'+n('task','failed')+' 页失败，'+n('task','blocked')+' 页受阻，'+n('task','succeeded')+' 页任务已执行（仍需验收）。'+(!d.task_registry_available?' 尚无任务登记表，不能确认是否已进入外部处理管道。':'');
}).catch(()=>{document.getElementById('courses').textContent='课程入口读取失败，请刷新重试。';document.getElementById('processing-summary').textContent='处理进度暂不可核验';});

if(topic&&!new URLSearchParams(location.search).has('deck')){fetch('deck-context.json').then(r=>r.json()).then(rows=>{const selected=rows.filter(r=>r.deck===topic);window.topicAtoms=new Set(selected.map(r=>r.atom_id));const byId=new Map(DATA.map(a=>[a.atom_id,a]));window.coursePages=selected.sort((a,b)=>Number(a.page)-Number(b.page)).filter(row=>byId.has(row.atom_id)).map(row=>({...byId.get(row.atom_id),occurrence_id:row.id,page_number:row.page,deck:row.deck_name,hd:'../assets/legacy-thumbs/'+row.id+'.jpg'})).map(applyTitle);const h=document.querySelector('h1');if(h)h.textContent=selected[0]?.deck_name||'主题总览';render();}).catch(()=>{cnt.textContent='主题读取失败，请刷新重试';});}
fetch('/api/prep/courses').then(r=>{if(!r.ok)throw Error('课件读取失败');return r.json()}).then(d=>{const courses=(d.courses||[]).filter(c=>!c.deck_id.startsWith('legacy-'));if(!topic&&!new URLSearchParams(location.search).has('deck')){(async()=>{for(const c of courses){for(let offset=0;;offset+=60){const response=await fetch('/api/library?deck='+encodeURIComponent(c.deck_id)+'&limit=60&offset='+offset);if(!response.ok)throw Error('导入课件读取失败');const data=await response.json();DATA.push(...data.pages.map(p=>({atom_id:p.page_id,title:p.title,deck:c.title,page_number:p.page_number,hd:p.thumbnail_url||p.source_url,textcount:1,framework_labels:[],detail_url:'page.html?page='+encodeURIComponent(p.page_id)})));if(offset+data.pages.length>=data.total)break;}}render();})().catch(()=>{cnt.textContent+=' · 新导入内容读取失败，请刷新';});}}).catch(()=>{});
const sourceDeck=new URLSearchParams(location.search).get('deck');
if(sourceDeck){window.courseLoading=true;window.coursePages=[];document.getElementById('cnt').textContent='正在读取课程…';(async()=>{let rows=[],meta;for(let offset=0;;offset+=60){const response=await fetch('/api/library?deck='+encodeURIComponent(sourceDeck)+'&limit=60&offset='+offset);if(!response.ok)throw Error('读取失败');const data=await response.json();meta=data.decks.find(d=>d.deck_id===sourceDeck);rows.push(...data.pages);window.coursePages=rows.map(p=>({atom_id:p.page_id,title:p.title,deck:meta?.title,page_number:p.page_number,hd:p.thumbnail_url||p.source_url,textcount:1,framework_labels:[],detail_url:'page.html?page='+encodeURIComponent(p.page_id)}));render();if(rows.length>=data.total)break;}window.topicAtoms=null;window.coursePages=rows.sort((a,b)=>a.page_number-b.page_number).map(p=>({atom_id:p.page_id,title:p.title,deck:meta?.title,page_number:p.page_number,hd:p.thumbnail_url||p.source_url,textcount:1,framework_labels:[],detail_url:'page.html?page='+encodeURIComponent(p.page_id)}));window.courseLoading=false;document.querySelector('h1').textContent=meta?.title||'课程';document.querySelector('.lead').textContent=(sourceDeck.startsWith('keynote-')?'Keynote 原始导入':'历史来源版本')+' · '+rows.length+' 页 · 按原始顺序浏览，标注待核验';render();})().catch(()=>{window.courseLoading=false;cnt.textContent='课程读取失败，请刷新重试';});}
render();
</script>
</body>
</html>
'''
total = len(atoms)
frames_n = len([k for k in frames if k and k != "—"])
claims_n = sum(1 for a in atoms if a["claimcount"] > 0)
texts_n = sum(1 for a in atoms if a["textcount"] > 0)
# enrich atoms with hd + search fields for client
for a in atoms:
    # hd url for cards: reconstruct from cos map via hdfile isn't stored; use empty -> card shows fallback unless we add.
    pass
# Card images: use the small public thumbnails (/uploads/slides/, ~8.5KB),
# not the HD files (~307KB). 1443 HD files would be ~440MB on first load;
# thumbnails are ~12MB total. The detail page still uses the HD image.
atomsfull = json.loads((ROOT / "atomdump" / "atomdump" / "atoms.json").read_text(encoding="utf-8"))["atoms"]
thumb_by_id = {}
hd_by_id = {}
for a in atomsfull:
    aid = a.get("atom_id")
    hd = a.get("hd_thumb") or ""
    # derive slide id from hd path (/uploads/slides-hd/mba-229.jpg -> mba-229)
    sid = hd.rsplit("/", 1)[-1].rsplit(".", 1)[0] if hd else (a.get("rep") or "")
    override = representative_override(ROOT, aid)
    if override: sid = override["display_slide_id"]
    thumb_by_id[aid] = (override.get("thumbnail_url") if override else None) or (("../assets/legacy-thumbs/" + sid + ".jpg") if sid else "")
    hd_by_id[aid] = hd if hd.startswith("/uploads/") else (("/uploads/slides-hd/" + sid + ".jpg") if sid else "")
for a in atoms:
    a["hd"] = thumb_by_id.get(a["atom_id"], "")   # cards show thumbnail
# Trim fields the gallery never renders, to keep the embedded JSON small.
KEEP = {"atom_id","title","frame","deck","uses","claimcount","textcount","is_blank","topic","hd","section","framework_labels","framework_label_status"}
atoms = [{k: v for k, v in a.items() if k in KEEP} for a in atoms]
data_js = json.dumps(atoms, ensure_ascii=False, separators=(",", ":"))
page = (PAGE
    .replace("__TOTAL__", str(total))
    .replace("__FRAMES__", str(frames_n))
    .replace("__CLAIMS__", str(claims_n))
    .replace("__TEXTS__", str(texts_n))
    .replace("__FRAME_OPTS__", frame_opts)
    .replace("__DATA__", data_js)
    .replace("__HTML_RECORDS__", json.dumps(json.loads((ROOT / "data/html-conversions.json").read_text())["records"],ensure_ascii=False,separators=(",",":")))
    .replace("__PREVIEWS__", json.dumps(json.loads((OUT / 'preview-images.json').read_text()),ensure_ascii=False,separators=(',',':')))
    .replace("__TITLES__", json.dumps(json.loads((ROOT / 'title-governance/knowledge-title-overlay.json').read_text()).get('titles',{}),ensure_ascii=False,separators=(',',':'))))
(OUT / "index.html").write_text(page, encoding="utf-8")
print("index.html written", len(page), "bytes;", total, "atoms;", frames_n, "frames")
