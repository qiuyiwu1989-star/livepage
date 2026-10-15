"""User lesson assemblies. Immutable revision snapshots never modify source pages."""
from collections import defaultdict, deque
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import uuid
from flask import Blueprint, jsonify, request

_LOCK = threading.RLock()
_ID = re.compile(r'^assembly-[a-f0-9]{32}$')


def register_assemblies(app, root):
    root = Path(root).resolve()
    storage = root / 'data' / 'assemblies'
    migration = Path(app.config.get('ASSEMBLY_CATALOG_DIR', root.parent / 'slide-library-migration' / 'generated'))
    bp = Blueprint('assemblies', __name__)

    def folder(aid):
        if not _ID.fullmatch(aid):
            raise LookupError('课件不存在')
        return storage / aid

    def revisions(aid):
        return sorted(folder(aid).glob('[0-9]*.json'))

    def current(aid):
        paths = revisions(aid)
        if not paths:
            raise LookupError('课件不存在')
        return json.loads(paths[-1].read_text())

    def payload():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            raise ValueError('需要 JSON 对象')
        return body

    def fields(body):
        if set(body) - {'title', 'course_title', 'page_ids', 'entries', 'base_revision'}:
            raise ValueError('包含未知字段')
        title = body.get('title')
        course = body.get('course_title', '')
        ids = body.get('page_ids')
        if 'entries' in body:
            if 'page_ids' in body or not isinstance(body['entries'], list):
                raise ValueError('entries 与 page_ids 只能提供一种')
            ids = [e.get('page_id') if isinstance(e, dict) else None for e in body['entries']]
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError('课件名称须为 1 至 200 字')
        if not isinstance(course, str) or len(course) > 200:
            raise ValueError('课程名称不能超过 200 字')
        if not isinstance(ids, list) or len(ids) > 3000 or any(not isinstance(x, str) for x in ids):
            raise ValueError('page_ids 须为最多 3000 个页面编号的列表')
        return title.strip(), course.strip(), ids

    def cas(body, old):
        value = body.get('base_revision')
        if type(value) is not int:
            raise ValueError('必须提供 base_revision')
        if value != old['revision']:
            return jsonify(error='课件已更新，请重新载入后保存', current_revision=old['revision']), 409

    def ref(value):
        value = deepcopy(value or {})
        if value.get('local_path'):
            try:
                value['url'] = '/' + Path(value['local_path']).resolve().relative_to(root).as_posix()
            except ValueError:
                pass
        return value

    def entries(ids, previous=()):
        catalog = json.loads((migration / 'catalog.json').read_text())
        atomic = json.loads((migration / 'atomic-catalog.json').read_text())
        pages = {p['page_id']: p for p in catalog['pages']}
        identities = {p['occurrence_id']: p for p in atomic['occurrences']}
        kept = defaultdict(deque)
        for entry in previous:
            kept[entry['page_id']].append(entry)
        result = []
        for position, page_id in enumerate(ids, 1):
            if kept[page_id]:
                entry = deepcopy(kept[page_id].popleft())
            else:
                if page_id not in pages or page_id not in identities:
                    raise ValueError('页面不存在或身份未就绪：' + page_id)
                p, identity = pages[page_id], identities[page_id]
                from atom_removal import deleted_ids
                if identity['atom_id'] in deleted_ids(root):
                    raise ValueError('原子页已删除，不能新增：' + page_id)
                entry = {key: deepcopy(p.get(key)) for key in ('title', 'deck_id', 'legacy_ids', 'source_url', 'thumbnail_url', 'provenance')}
                entry.update(entry_id='entry-' + uuid.uuid4().hex, page_id=page_id,
                             atom_id=identity['atom_id'], version_id=identity['version_id'],
                             image=ref(p.get('image')), thumbnail=ref(p.get('thumbnail')), html=ref(p.get('html')))
                entry['original_source_url'] = entry.get('source_url')
                entry['source_url'] = entry['image'].get('url') or entry.get('source_url')
                entry['thumbnail_url'] = entry['thumbnail'].get('url') or entry.get('thumbnail_url')
            entry['position'] = position
            result.append(entry)
        return result

    def edited_entries(body, previous=()):
        if 'entries' not in body:
            return entries(body['page_ids'], previous)
        old = {e['entry_id']: e for e in previous}
        seen = set()
        result = []
        fresh_ids = [item['page_id'] for item in body['entries'] if not item.get('entry_id')]
        fresh = iter(entries(fresh_ids) if fresh_ids else [])
        for item in body['entries']:
            if set(item) - {'entry_id', 'page_id', 'chapter', 'notes'}:
                raise ValueError('页面引用包含未知字段')
            eid = item.get('entry_id')
            if eid:
                if eid not in old or eid in seen or old[eid]['page_id'] != item['page_id']:
                    raise ValueError('页面引用身份无效或重复')
                entry = deepcopy(old[eid])
                seen.add(eid)
            else:
                entry = next(fresh)
            for key, limit in (('chapter', 200), ('notes', 20000)):
                value = item.get(key, entry.get(key, ''))
                if not isinstance(value, str) or len(value) > limit:
                    raise ValueError(key + ' 格式无效或过长')
                entry[key] = value
            entry['position'] = len(result) + 1
            result.append(entry)
        return result

    def save(doc):
        directory = folder(doc['assembly_id'])
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / ('%08d.json' % doc['revision'])
        temporary = directory / ('.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('x') as stream:
                json.dump(doc, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic publish with exclusive destination: history can never be overwritten.
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return doc

    def summary(doc):
        return {k: doc[k] for k in ('assembly_id', 'title', 'course_title', 'revision', 'created_at', 'updated_at')} | {'page_count': len(doc['entries']), 'kind': doc.get('kind', 'lesson'), 'source_deck_id': doc.get('source_deck_id'), 'parent_assembly_id': doc.get('parent_assembly_id')}

    def stamp():
        return datetime.now(timezone.utc).isoformat()

    @bp.errorhandler(ValueError)
    def bad_request(exc):
        return jsonify(error=str(exc)), 400

    @bp.errorhandler(LookupError)
    def not_found(exc):
        return jsonify(error=str(exc)), 404

    @bp.get('/api/assemblies')
    def listing():
        with _LOCK:
            docs = [summary(current(p.name)) for p in storage.glob('assembly-*') if p.is_dir() and _ID.fullmatch(p.name) and revisions(p.name)]
        return jsonify(assemblies=sorted(docs, key=lambda x: x['updated_at'], reverse=True))

    def create_document(body):
        title, course, ids = fields(body)
        with _LOCK:
            now = stamp()
            doc = save(dict(assembly_id='assembly-' + uuid.uuid4().hex, title=title, course_title=course,
                            revision=1, entries=edited_entries(body), created_at=now, updated_at=now))
        return doc

    app.extensions['assembly_create'] = create_document

    @bp.post('/api/assemblies')
    def create():
        return jsonify(create_document(payload())), 201

    @bp.get('/api/assemblies/<aid>')
    def detail(aid):
        with _LOCK:
            return jsonify(current(aid))

    @bp.put('/api/assemblies/<aid>')
    def update(aid):
        body = payload()
        title, course, ids = fields(body)
        with _LOCK:
            old = current(aid)
            conflict = cas(body, old)
            if conflict:
                return conflict
            doc = deepcopy(old)
            doc.update(title=title, course_title=course, entries=edited_entries(body, old['entries']), revision=old['revision'] + 1, updated_at=stamp())
            doc.pop('restored_from_revision', None)
            return jsonify(save(doc))

    @bp.get('/api/assemblies/<aid>/history')
    def history(aid):
        with _LOCK:
            current(aid)
            return jsonify(history=[summary(json.loads(p.read_text())) for p in reversed(revisions(aid))])

    @bp.post('/api/assemblies/<aid>/restore')
    def restore(aid):
        body = payload()
        with _LOCK:
            old = current(aid)
            conflict = cas(body, old)
            if conflict:
                return conflict
            if set(body) - {'revision', 'base_revision'}:
                raise ValueError('包含未知字段')
            revision = body.get('revision')
            if type(revision) is not int or not 1 <= revision <= old['revision']:
                raise ValueError('恢复版本无效')
            path = folder(aid) / ('%08d.json' % revision)
            if not path.exists():
                raise ValueError('恢复版本不存在')
            doc = json.loads(path.read_text())
            doc.update(revision=old['revision'] + 1, updated_at=stamp(), restored_from_revision=revision)
            return jsonify(save(doc))

    app.extensions['prep_assembly_store'] = dict(current=current, save=save, entries=entries, summary=summary, stamp=stamp, lock=_LOCK, storage=storage, migration=migration)
    app.register_blueprint(bp)
