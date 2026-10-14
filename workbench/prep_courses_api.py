"""Mother-course lifecycle over the existing immutable assembly store."""
from copy import deepcopy
import json
import uuid
from flask import Blueprint, jsonify, request
from atom_removal import deleted_ids


def register_prep_courses(app, root):
    store = app.extensions['prep_assembly_store']
    bp = Blueprint('prep_courses', __name__)

    def catalog():
        return json.loads((store['migration'] / 'catalog.json').read_text())

    def masters():
        docs = []
        for directory in store['storage'].glob('assembly-*'):
            if directory.is_dir():
                try:
                    doc = store['current'](directory.name)
                except LookupError:
                    continue
                if doc.get('kind') == 'master':
                    docs.append(doc)
        return docs

    @bp.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(error=str(exc)), 400

    @bp.errorhandler(LookupError)
    def missing(exc):
        return jsonify(error=str(exc)), 404

    @bp.get('/api/prep/courses')
    def listing():
        with store['lock']:
            existing = {d['source_deck_id']: d['assembly_id'] for d in masters()}
            courses = [dict(d, master_assembly_id=existing.get(d['deck_id'])) for d in catalog().get('decks', [])]
        return jsonify(courses=courses)

    @bp.post('/api/prep/courses/<deck_id>/master')
    def initialize(deck_id):
        with store['lock']:
            for doc in masters():
                if doc.get('source_deck_id') == deck_id:
                    return jsonify(doc)
            source = catalog()
            deck = next((d for d in source.get('decks', []) if d['deck_id'] == deck_id or deck_id in d.get('legacy_ids', [])), None)
            if not deck:
                raise LookupError('原课程不存在')
            # Resolve aliases before the idempotence check.
            for doc in masters():
                if doc.get('source_deck_id') == deck['deck_id']:
                    return jsonify(doc)
            removed = deleted_ids(root)
            pages = sorted((p for p in source['pages'] if p.get('deck_id') == deck['deck_id'] and p.get('atomic_id') not in removed), key=lambda p: p.get('page_number', 0))
            now = store['stamp']()
            doc = dict(assembly_id='assembly-' + uuid.uuid4().hex, kind='master', source_deck_id=deck['deck_id'], title=deck['title'], course_title=deck['title'], revision=1, created_at=now, updated_at=now, entries=store['entries']([p['page_id'] for p in pages]))
            return jsonify(store['save'](doc)), 201

    @bp.post('/api/prep/assemblies/<aid>/derive')
    def derive(aid):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or set(body) - {'title', 'base_revision'}:
            raise ValueError('需要 title 和 base_revision')
        title = body.get('title')
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError('课件名称须为 1 至 200 字')
        with store['lock']:
            old = store['current'](aid)
            if type(body.get('base_revision')) is not int:
                raise ValueError('必须提供 base_revision')
            if body['base_revision'] != old['revision']:
                return jsonify(error='课程已更新，请重新载入', current_revision=old['revision']), 409
            doc = deepcopy(old)
            now = store['stamp']()
            removed = deleted_ids(root)
            doc['entries'] = [e for e in doc['entries'] if e.get('atom_id') not in removed]
            for i, entry in enumerate(doc['entries'], 1):
                entry.update(entry_id='entry-' + uuid.uuid4().hex, position=i)
            doc.update(assembly_id='assembly-' + uuid.uuid4().hex, kind='lesson', title=title.strip(), revision=1, created_at=now, updated_at=now, parent_assembly_id=aid, parent_revision=old['revision'])
            doc.pop('restored_from_revision', None)
            return jsonify(store['save'](doc)), 201

    app.register_blueprint(bp)
