"""LivePage-owned experimental envelope, not an OpenDesign API adapter."""
import copy
import hashlib
import re


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def build_handoff(scene, html, page_version_id):
    if not page_version_id or not scene.get('atom_id') or not scene.get('source_sha256'):
        raise ValueError('Explicit identity, source and version required')
    if any(b.get('source_raster') for b in scene['text']):
        raise ValueError('Raster text cannot enter editable handoff')
    objects = []
    for i, block in enumerate(scene['text']):
        object_id = 'text-' + digest(f"{scene['source_sha256']}:{scene['pdf_page']}:{i}")[:24]
        pattern = rf'data-block="{i}"(?=[\s>])'
        html, count = re.subn(pattern, lambda _: f'data-block="{i}" data-lp-object-id="{object_id}"', html)
        if count != 1:
            raise ValueError(f'Text block {i} must map to exactly one DOM object')
        objects.append({'object_id': object_id, 'type': 'text', 'source_block_index': i,
                        'text': block['text'], 'layout': {k: copy.deepcopy(block[k]) for k in ('bbox', 'origin', 'size', 'font', 'color')},
                        'correction': copy.deepcopy(block.get('correction')), 'human_review': 'pending'})
    envelope = {'schema': 'livepage-editor-handoff/0.1', 'atom_id': scene['atom_id'],
                'base_page_version_id': page_version_id, 'source_sha256': scene['source_sha256'],
                'pdf_page': scene['pdf_page'], 'canvas_size': scene['size'], 'objects': objects,
                'html_sha256': digest(html), 'human_review': 'pending',
                'limitations': ['External editor protocol unverified', 'Graphics remain one SVG layer',
                                'No editor save or version return connected', 'Font and visual review pending']}
    return envelope, html


def build_deck(deck_id, entries):
    """Ordered, version-pinned occurrences. Never deduplicate by atom identity."""
    if not deck_id or not entries:
        raise ValueError('Deck identity and entries required')
    seen = set()
    result = []
    for position, entry in enumerate(entries):
        if any(not entry.get(k) for k in ('entry_id', 'atom_id', 'page_version_id')):
            raise ValueError('Entry identity and pinned page version required')
        if entry['entry_id'] in seen:
            raise ValueError('Duplicate deck entry identity')
        seen.add(entry['entry_id'])
        result.append({**copy.deepcopy(entry), 'position': position})
    return {'schema': 'livepage-deck/0.1', 'deck_id': deck_id, 'entries': result, 'human_review': 'pending'}
