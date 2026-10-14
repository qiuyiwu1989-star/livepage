"""Read-only migration quality and title candidates; candidates never imply identity."""
from collections import defaultdict
import os
import json
from pathlib import Path
from urllib.parse import quote, urlsplit

from flask import Blueprint, jsonify

MIGRATION = Path(os.environ.get('LIVEPAGE_CATALOG_ROOT',Path(__file__).resolve().parent.parent / 'slide-library-migration'))


def register_governance(app, root=None):
    root = Path(root or Path(__file__).resolve().parent).resolve()
    bp = Blueprint('library_governance', __name__)
    cache = {}

    def load(name):
        path = MIGRATION / 'generated' / name
        if not path.exists():
            cache.pop(name, None)
            return None
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        if name not in cache or cache[name][0] != stamp:
            cache[name] = (stamp, json.loads(path.read_text()))
        return cache[name][1]

    def title_groups(pages):
        groups = defaultdict(list)
        for page in pages:
            title = (page.get('title') or '').strip()
            if title:
                groups[title].append(page)
        return groups

    def identities(pages):
        known = {p['page_id'] for p in pages}
        confirmed = {}
        for atom in (load('atomic-catalog.json') or {}).get('atoms', []):
            if atom.get('identity_status') not in {'confirmed', 'original_library'} or not atom.get('atom_id'):
                continue
            for page_id in known.intersection(atom.get('occurrence_ids', [])):
                confirmed[page_id] = atom['atom_id']
        return confirmed

    def candidate_groups(pages, identity):
        return [group for group in title_groups(pages).values()
                if len({identity.get(p['page_id'], 'page:' + p['page_id']) for p in group}) > 1]

    def thumbnail(page):
        ref = page.get('thumbnail') or {}
        if ref.get('local_path'):
            try:
                relative = Path(ref['local_path']).resolve().relative_to(root)
                return '/' + quote(relative.as_posix(), safe='/')
            except ValueError:
                pass
        value = page.get('thumbnail_url') or ref.get('url') or ''
        try:
            parts = urlsplit(value)
            if parts.scheme in ('http', 'https') and parts.hostname and not parts.username and not parts.password:
                return value
            if value.startswith('/') and not value.startswith('//') and not parts.scheme and '\\' not in value:
                return value
        except ValueError:
            pass
        return None

    @bp.get('/api/library/page/<page_id>/related')
    def related(page_id):
        data = load('catalog.json')
        if data is None:
            return jsonify(error='目录尚未生成', status='pending'), 503
        pages = data.get('pages', [])
        page = next((p for p in pages if p['page_id'] == page_id), None)
        if page is None:
            return jsonify(error='页面不存在'), 404
        decks = {d['deck_id']: d.get('title', '') for d in data.get('decks', [])}
        identity = identities(pages)
        atom_id = identity.get(page_id)
        def item(p, confirmed=False):
            return {
                'page_id': p['page_id'], 'title': p.get('title', ''),
                'deck_id': p.get('deck_id'), 'deck_title': decks.get(p.get('deck_id'), ''),
                'page_number': p.get('page_number'), 'thumbnail_url': thumbnail(p),
                'atom_id': identity.get(p['page_id']),
                'reason': 'source_atom_mapping' if confirmed else 'exact_title',
                'status': 'source_confirmed' if confirmed else 'unconfirmed',
            }
        same_atom = [item(p, True) for p in pages if p['page_id'] != page_id
                     and atom_id and identity.get(p['page_id']) == atom_id]
        candidates = [item(p) for p in title_groups(pages).get((page.get('title') or '').strip(), [])
                      if p['page_id'] != page_id and not (atom_id and identity.get(p['page_id']) == atom_id)]
        return jsonify(page_id=page_id, atom_id=atom_id, same_atom=same_atom,
                       candidates=candidates, pages=candidates, total=len(same_atom) + len(candidates),
                       status='source_confirmed' if atom_id else 'unconfirmed',
                       identity_confirmed=bool(atom_id),
                       explanation='同一原子页来自原库明确映射；同标题候选另列，不自动合并。')

    @bp.get('/api/library/governance')
    def governance():
        data = load('catalog.json')
        if data is None:
            return jsonify(error='目录尚未生成', status='pending'), 503
        atomic = load('atomic-catalog.json')
        pages = data.get('pages', [])
        known_ids = {p['page_id'] for p in pages}
        atoms = (atomic or {}).get('atoms', [])
        provisional = sum(
            str(a.get('identity_status', '')).startswith('provisional')
            and bool(known_ids.intersection(a.get('occurrence_ids', []))) for a in atoms
        ) if atomic is not None else None
        confirmed = identities(pages)
        return jsonify(status='ready' if atomic is not None else 'atomic_pending', counts={
            'pages': len(pages), 'decks': len(data.get('decks', [])),
            'missing_old_annotations': sum(p.get('source_kind', '').startswith('legacy') and (
                p.get('annotation_completeness') == 'ui_metadata_only'
                or p.get('processing', {}).get('annotation') == 'pending_source_acquisition') for p in pages),
            'pending_html': sum(p.get('html', {}).get('status') not in {'local_exists', 'unverified_remote'} for p in pages),
            'provisional': provisional,
            'confirmed': len(set(confirmed.values())) if atomic is not None else None,
            'confirmed_occurrences': len(confirmed) if atomic is not None else None,
            'candidate_groups': len(candidate_groups(pages, confirmed)),
        }, semantics={
            'pages': '页面出现记录，不是去重后的原子页数',
            'pending_html': '尚未登记 HTML；已登记远程 HTML 仍需核验',
            'provisional': '暂定身份，不是已确认的独立原子页',
            'candidate_groups': '跨原子身份的同标题候选组，未自动合并',
            'confirmed': '原库明确映射的原子身份，不表示内容已人工审核',
            'confirmed_occurrences': '已接回原库原子身份的页面出现记录',
            'missing_old_annotations': '旧标注尚未接入，不表示原库没有标注',
        })

    app.register_blueprint(bp)
