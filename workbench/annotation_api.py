"""Append-only human interpretations; never overwrite imported source annotations."""
from datetime import datetime, timezone
import hashlib
import os
import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from uuid import uuid4

from flask import Blueprint, jsonify, request

_LOCK = RLock()
KINDS = {'explanation', 'example', 'teaching_note', 'question', 'source_correction'}
OPTIONAL = {'course_title': 500, 'session_title': 500, 'source_reference': 4000, 'timecode': 100}


def note_search_text(root):
    """Read supplementary search terms without changing source/catalog content.

    Unreadable histories are omitted here; the detail API explicitly reports their
    error. This helper never repairs or rewrites stored annotations.
    """
    result = {}
    with _LOCK:
        for path in (Path(root) / 'workspace/annotations').glob('*.json'):
            try:
                history = json.loads(path.read_text(encoding='utf-8'))
                page_id, notes = history['page_id'], history['notes']
                if not isinstance(page_id, str) or not isinstance(notes, list):
                    continue
                result[page_id] = ' '.join(
                    value for note in notes if isinstance(note, dict)
                    for key in ('text', 'kind', *OPTIONAL)
                    if isinstance((value := note.get(key)), str)
                )
            except (OSError, ValueError, KeyError, TypeError):
                continue
    return result


def register_annotations(app, root, catalog_path=None, atomic_catalog_path=None):
    root = Path(root)
    catalog_path = Path(catalog_path) if catalog_path else Path(os.environ.get('LIVEPAGE_CATALOG_ROOT', root.parent / 'slide-library-migration')) / 'generated/catalog.json'
    atomic_catalog_path = Path(atomic_catalog_path) if atomic_catalog_path else catalog_path.with_name('atomic-catalog.json')
    store = root / 'workspace/annotations'
    bp = Blueprint('page_annotations', __name__)

    def find_page(page_id):
        data = json.loads(catalog_path.read_text(encoding='utf-8'))
        return next((p for p in data.get('pages', []) if p.get('page_id') == page_id), None)

    def path_for(page_id):
        # Source identifiers are not filesystem paths, even for future imports.
        return store / (hashlib.sha256(page_id.encode()).hexdigest() + '.json')

    def atomic_refs(page_id):
        try:
            data = json.loads(atomic_catalog_path.read_text(encoding='utf-8'))
            matches = [row for row in data.get('occurrences', [])
                       if row.get('source_page_id') == page_id]
            if len(matches) != 1:
                return {}
            return {key: matches[0][key] for key in ('atom_id', 'version_id')
                    if isinstance(matches[0].get(key), str) and matches[0][key]}
        except (OSError, ValueError, TypeError, AttributeError):
            return {}

    def read_history(path, page_id):
        if not path.exists():
            return {'schema_version': 1, 'page_id': page_id, 'notes': []}
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('page_id') != page_id or not isinstance(data.get('notes'), list):
            raise ValueError('Annotation history is invalid')
        return data

    @bp.route('/api/library/page/<page_id>/notes', methods=['GET', 'POST'])
    def notes(page_id):
        try:
            page = find_page(page_id)
        except (OSError, ValueError, TypeError):
            return jsonify(error='课件目录暂不可用'), 503
        if page is None:
            return jsonify(error='页面不存在'), 404
        payload = None
        if request.method == 'POST':
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict):
                return jsonify(error='请提交 JSON 对象'), 400
            if set(payload) - ({'kind', 'text'} | set(OPTIONAL)):
                return jsonify(error='包含不支持的字段'), 400
            kind, text = payload.get('kind'), payload.get('text')
            if not isinstance(kind, str) or kind not in KINDS:
                return jsonify(error='标注类型无效'), 400
            if not isinstance(text, str) or not text.strip() or len(text) > 20000:
                return jsonify(error='标注内容需为 1 至 20000 字符'), 400
            for key, limit in OPTIONAL.items():
                if key in payload and (not isinstance(payload[key], str) or len(payload[key]) > limit):
                    return jsonify(error=f'{key} 格式或长度无效'), 400
        try:
            with _LOCK:
                path = path_for(page_id)
                history = read_history(path, page_id)
                if payload is None:
                    return jsonify(history)
                note = {
                    'id': str(uuid4()), 'created_at': datetime.now(timezone.utc).isoformat(),
                    'author': 'human', 'kind': payload['kind'], 'text': payload['text'].strip(),
                    'origin': 'human_note',
                    'scope': ('lecture_context' if payload['kind'] == 'teaching_note' or
                              any(payload.get(key, '').strip() for key in ('course_title', 'session_title', 'timecode'))
                              else 'page_interpretation'),
                    'page_id': page_id,
                    'source_context': {key: page.get(key) for key in
                                       ('deck_id', 'page_number', 'legacy_ids', 'source_kind')},
                }
                note['source_context'].update(atomic_refs(page_id))
                note.update({key: payload[key].strip() for key in OPTIONAL if key in payload})
                history['notes'].append(note)
                store.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=store, delete=False) as f:
                        temporary = f.name
                        json.dump(history, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(temporary, path)
                finally:
                    if temporary and os.path.exists(temporary):
                        os.unlink(temporary)
                return jsonify(note=note, count=len(history['notes'])), 201
        except (OSError, ValueError, TypeError, AttributeError):
            # A corrupt history is never silently reset or replaced.
            return jsonify(error='标注历史不可用，原文件已保留'), 503

    app.register_blueprint(bp)
