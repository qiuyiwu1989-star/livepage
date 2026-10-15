"""Read-only preparation sources. Explicit credentials; no source-library writes."""
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen


def env_config(app, name):
    value = app.config.get(name) or os.environ.get(name)
    if value:
        return value
    filename = app.config.get('PREP_CONTEXT_ENV_FILE') or os.environ.get('PREP_CONTEXT_ENV_FILE')
    if filename:
        for line in Path(filename).read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, val = line.split('=', 1)
                if key.strip() == name:
                    return val.strip().strip('\"\'')
    return None


def terms(text):
    result = set(re.findall(r'[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}', text.lower()))
    for word in list(result):
        if len(word) > 2 and re.search('[\u4e00-\u9fff]', word):
            result.update(word[i:i+2] for i in range(len(word)-1))
    return result


def relevance(text, words):
    text = text.lower()
    return sum((len(w) if len(w) > 2 else 1) for w in words if w in text)


def source(sid, kind, title, text, **extra):
    return dict(source_id=sid, kind=kind, title=title, text=text,
                content_sha256=hashlib.sha256(text.encode()).hexdigest(), **extra)


def collect(app, root, intent):
    fixture = app.config.get('PREP_CONTEXT_PROVIDER')
    if callable(fixture):
        return fixture(intent)
    query_plan = []
    try:
        if app.extensions.get('prep_model_available', lambda:False)():
            planned,_ = app.extensions['prep_model_generate']({'intent':intent}, '你是备课资料检索规划器。只规划查询，不写课程。返回JSON：queries数组，4至6项，每项purpose、query。分别寻找讲者为什么关心主题的经历/动机、讲者自身实践、下一代与家庭或主题相关的具体实践、著作理论、听众情境。query是短词组，适合搜索真实记录的标题，不写操作要求，不假定存在事实，不用泛词堆叠。')
            query_plan = [q for q in planned.get('queries',[]) if isinstance(q,dict) and isinstance(q.get('query'),str) and 0<len(q['query'])<=100][:6]
    except Exception:
        pass
    if not query_plan:
        query_plan = [dict(purpose='主题',query=str(intent.get('topic',''))),dict(purpose='讲者动机与实践',query=str(intent.get('thoughts',''))[:200])]
    words = set().union(*(terms(q['query']) for q in query_plan))
    sources, coverage, books = [], [], []
    path = env_config(app, 'PREP_BOOKS_INDEX')
    public = env_config(app, 'PREP_BOOKS_CATALOG')
    try:
        if not path:
            raise ValueError('unconfigured')
        index = json.loads(Path(path).read_text())
        books = json.loads(Path(public).read_text()).get('items', []) if public else []
        candidates = []
        for book in index.get('books', []):
            for sec in book.get('sections', []):
                score = relevance(sec.get('text', '') + ' ' + sec.get('chapter', '') + ' ' + book.get('name', ''), words)
                if score:
                    candidates.append((score, book, sec))
        counts = {}
        for score, book, sec in sorted(candidates, key=lambda x: -x[0]):
            slug = book.get('slug') or book['id']
            if counts.get(slug, 0) >= 2:
                continue
            counts[slug] = counts.get(slug, 0) + 1
            sources.append(source(sec.get('sid') or 'book:'+slug+'#'+str(sec['n']), 'book', book.get('name', ''), sec.get('text', '')[:7000], chapter=sec.get('chapter'), heading=sec.get('heading'), url=sec.get('url'), author_status='authored_source_not_reverified', publication_status=book.get('status')))
            if sum(counts.values()) >= 10:
                break
        coverage.append(dict(kind='books', status='ready', total_books=len(index.get('books', [])), matched_sections=sum(counts.values())))
    except Exception:
        coverage.append(dict(kind='books', status='unavailable', message='著作正文索引未配置或暂不可读；没有用生成内容补齐。'))

    key = env_config(app, 'SHENNAO_API_KEY')
    try:
        if not key:
            raise ValueError('unconfigured')
        def remote(query):
            req = Request('https://shennao.zaowuyun.com/api/v1/transcripts'+query, headers={'Authorization':'Bearer '+key, 'Accept':'application/json'})
            with urlopen(req, timeout=20) as response:
                return json.load(response)
        cache = Path(root)/'data/prep-context-cache'
        cache.mkdir(parents=True, exist_ok=True)
        listing = cache/'transcript-list.json'
        import time
        if listing.exists() and time.time()-listing.stat().st_mtime < 1800:
            items = json.loads(listing.read_text())
        else:
            items, offset = [], 0
            while True:
                data = remote('?limit=100&offset='+str(offset))
                batch = data.get('transcripts', [])
                items.extend(batch)
                next_offset = data.get('next_offset')
                if next_offset is None or not batch or next_offset <= offset:
                    break
                offset = next_offset
            temporary = listing.with_suffix('.tmp')
            temporary.write_text(json.dumps(items, ensure_ascii=False)); temporary.replace(listing)
        selected = []
        selected_ids = set()
        # Cover each question before adding more results for a single broad topic.
        for query in query_plan:
            qw=terms(query['query'])
            ranked=sorted(items,key=lambda t:-relevance(t.get('title',''),qw))
            hit=next((t for t in ranked if t['id'] not in selected_ids and relevance(t.get('title',''),qw)>0),None)
            if hit:
                selected.append(hit);selected_ids.add(hit['id'])
        # Explicit prior reading anchors can supplement retrieval, without claiming it discovered them.
        for tid in intent.get('source_hints',[])[:4]:
            hit=next((t for t in items if t['id']==tid and tid not in selected_ids),None)
            if hit:selected.append(hit);selected_ids.add(tid)
        read_count = 0
        for item in selected:
            tid = item['id']
            if not re.fullmatch(r'[a-f0-9-]{36}', tid):
                continue
            filename = cache/(tid+'.json')
            # Re-fetch updated source versions; never label an older cache current.
            data = json.loads(filename.read_text()) if filename.exists() else None
            if not data or data.get('updated_at') != item.get('updated_at'):
                data = remote('?id='+tid+'&include_analyses=true')
                filename.write_text(json.dumps(data, ensure_ascii=False))
            raw = data.get('text','')
            blocks = []
            for m in re.finditer(r'[^\n]+(?:\n(?!\s*\n)[^\n]*)*', raw):
                body = m.group().strip()
                if len(body) < 70:
                    continue
                blocks.append((relevance(body, words) + (8 if re.match(r'^(邱懿武|qiuyiwu)\s', body) else 0), m.start(), body))
            chosen = sorted(blocks, reverse=True)[:4]
            # Read a motivation/turning-point passage as well as dense topic matches.
            turning = next((b for b in sorted(blocks,key=lambda x:x[1]) if re.match(r'^(邱懿武|qiuyiwu)\s',b[2]) and re.search(r'为什么.{0,12}(感兴趣|关注|教育)|我.{0,15}(开始|最大的区别|做了一个|上一个|一门课)',b[2]) and b[0]>0),None)
            if turning and turning not in chosen:chosen.append(turning)
            for score, start, body in chosen:
                if score == 0:
                    continue
                # Only an explicit speaker prefix is accepted, not a name mentioned in someone else's turn.
                first = body.split('\n',1)[0]
                attributed = bool(re.match(r'^(邱懿武|qiuyiwu)\s', first))
                stamp = re.search(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', first)
                sources.append(source('talk:'+tid+'@'+str(start), 'transcript', data.get('title',''), body[:4500], transcript_id=tid, character_offset=start, time_anchor=stamp.group() if stamp else None, speaker=first[:100], attribution='speaker_label_qiuyiwu_unverified_audio' if attributed else 'other_or_unknown_speaker', source_updated_at=data.get('updated_at'), url='https://shennao.zaowuyun.com/api/v1/transcripts?id='+tid, note='转写未听校；历史分析未作为本人原话。'))
            read_count += 1
        coverage.append(dict(kind='shennao', status='ready', indexed_records=len(items), read_records=read_count, note='按标题关键词检索后读取原文片段，不是全库语义理解。'))
    except Exception:
        coverage.append(dict(kind='shennao', status='unavailable', message='深脑暂不可读；未将缓存冒充本次成功读取。'))

    try:
        catalog_dir = Path(app.config.get('ASSEMBLY_CATALOG_DIR', Path(root).parent/'slide-library-migration/generated'))
        catalog = json.loads((catalog_dir/'catalog.json').read_text())
        ranked = []
        from atom_removal import deleted_ids
        removed = deleted_ids(Path(root))
        for p in catalog.get('pages', []):
            if p.get('atomic_id') in removed or (p.get('original_slide') or {}).get('is_blank'):
                continue
            ann = p.get('annotation') or {}
            text = str(ann.get('source_text') or '')
            score = relevance(p.get('title','')+' '+text, words)
            if score:
                ranked.append((score, p, text))
        for score, p, text in sorted(ranked, key=lambda x:-x[0])[:12]:
            sources.append(source('page:'+p['page_id'], 'slide', p.get('title',''), text[:2500], page_id=p['page_id'], deck_id=p.get('deck_id'), page_number=p.get('page_number'), url='atom-pages/page.html?page='+p['page_id'], note='源页提取文字，非讲者现场原话；不凭标题推断讲法。'))
        coverage.append(dict(kind='slides',status='ready',matched_pages=min(12,len(ranked))))
    except Exception:
        coverage.append(dict(kind='slides',status='unavailable',message='活页目录暂不可读。'))
    return dict(sources=sources, coverage=coverage, books=books, query_plan=query_plan)
