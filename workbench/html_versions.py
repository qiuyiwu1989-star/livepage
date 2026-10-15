"""Append-only local editable HTML representations. No production writes."""
import copy
import fcntl
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import uuid
from datetime import datetime, timezone


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class Cells(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.lines = [0]
        for match in re.finditer('\n', source):
            self.lines.append(match.end())
        self.cells = {}
        self.active = None
        self.table = None
        self.table_count = 0
        self.table_id = None
        self.rows = []
        self.in_row = False
        self.feed(source)
        self.close()
        if self.active or self.table or self.in_row or not self.rows or len({len(r) for r in self.rows}) != 1:
            raise ValueError('Incomplete or non-rectangular table')
        if len(self.rows) < 2 or len(self.rows[0]) < 2:
            raise ValueError('Table needs header and body')

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if len(data) != len(attrs):
            raise ValueError("Duplicate HTML attributes")
        if tag == 'table':
            if self.table or self.table_count:
                raise ValueError('Exactly one semantic table required')
            self.table = data.get('data-lp-table-id')
            self.table_count += 1
            self.table_id = self.table
            if not self.table:
                raise ValueError('Stable table identity required')
        if self.table and tag == 'tr':
            if self.in_row:
                raise ValueError('Nested rows are invalid')
            self.in_row = True
            self.rows.append([])
            if len(self.rows) > 100:
                raise ValueError('Table exceeds 100 rows')
        if tag in ('th', 'td'):
            cid = data.get('data-lp-cell-id')
            if not self.table or self.active or not self.in_row or not cid or cid in self.cells or len(cid) > 200:
                raise ValueError('Invalid or duplicate cell identity')
            if data.get('rowspan', '1') != '1' or data.get('colspan', '1') != '1':
                raise ValueError('Spanning cells are not supported yet')
            self.active = cid
            self.rows[-1].append(cid)
            if len(self.rows[-1]) > 50:
                raise ValueError('Table exceeds 50 columns')
            self.cells[cid] = {'id': cid, 'text': '', 'tag': tag,
                               'content_start': self.source_offset() + len(self.get_starttag_text())}
        if self.active and tag == 'br':
            self.cells[self.active]['text'] += '\n'
        if self.active and tag in ('img', 'svg', 'script', 'style', 'canvas'):
            raise ValueError('Editable cell must contain text, not raster or executable content')

    def handle_startendtag(self, tag, attrs):
        if tag in ('table', 'tr', 'td', 'th'):
            raise ValueError('Table tags must have explicit closing tags')
        super().handle_startendtag(tag, attrs)

    def handle_data(self, data):
        if self.active:
            self.cells[self.active]['text'] += data

    def handle_endtag(self, tag):
        if tag in ('th', 'td'):
            if not self.active or self.cells[self.active]['tag'] != tag:
                raise ValueError('Malformed cell')
            self.cells[self.active]['content_end'] = self.source_offset()
            self.active = None
        if tag == 'tr':
            if not self.in_row or self.active:
                raise ValueError('Malformed row')
            self.in_row = False
        if tag == 'table':
            if self.active or self.in_row:
                raise ValueError('Malformed table')
            self.table = None


def inspect(source):
    if not isinstance(source, str) or len(source.encode()) > 5 * 1024 * 1024:
        raise ValueError('HTML must be UTF-8, at most 5 MiB')
    return Cells(source)


class VersionConflict(ValueError):
    pass


class HtmlVersions:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _folder(self, atom_id):
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}', atom_id):
            raise ValueError('Invalid atom identity')
        path = self.root / atom_id
        path.mkdir(exist_ok=True)
        return path

    def _read(self, path):
        doc = json.loads(path.read_text())
        if digest(doc['html']) != doc['html_sha256']:
            raise ValueError('Stored HTML hash mismatch')
        return doc

    def history(self, atom_id):
        return [self._read(p) for p in sorted(self._folder(atom_id).glob('[0-9]*.json'))]

    def get(self, atom_id, version_id=None):
        versions = self.history(atom_id)
        if not versions:
            raise FileNotFoundError(atom_id)
        if version_id is None:
            return versions[-1]
        for doc in versions:
            if doc['version_id'] == version_id:
                return doc
        raise FileNotFoundError(version_id)

    def append(self, atom_id, source, base_version_id, provenance, content=None):
        parsed = inspect(source)
        if not isinstance(provenance, dict) or provenance.get('actor') not in ('codex', 'mimo', 'docs'):
            raise ValueError('Explicit actor provenance required')
        folder = self._folder(atom_id)
        with (folder / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            history = self.history(atom_id)
            parent = history[-1] if history else None
            if base_version_id != (parent['version_id'] if parent else None):
                raise VersionConflict('Base version changed; reread before saving')
            if parent:
                content = parent['source_content']
                if parsed.table_id != parent['table_id']:
                    raise ValueError('Table identity changed')
            elif not content or content.get('atom_id') != atom_id or not re.fullmatch('[0-9a-f]{64}', content.get('source_sha256', '')):
                raise ValueError('Traceable source content required for initial version')
            known = {c['id']: c for r in content['rows'] for c in r['cells']}
            if not parent and set(known) != set(parsed.cells):
                raise ValueError('Initial cells must match source content')
            current = [{**copy.deepcopy(c), 'source_cell_id': cid if cid in known else None,
                        'human_review': 'pending'} for cid, c in parsed.cells.items()]
            doc = {'schema': 'livepage-html-version/0.1', 'atom_id': atom_id,
                   'version_id': uuid.uuid4().hex, 'revision': len(history) + 1,
                   'parent_version_id': parent['version_id'] if parent else None,
                   'table_id': parsed.table_id,
                   'source_sha256': content['source_sha256'], 'source_content': copy.deepcopy(content),
                   'html': source, 'html_sha256': digest(source), 'cells': current,
                   'display_rows': parsed.rows, 'removed_source_cell_ids': sorted(set(known) - set(parsed.cells)),
                   'provenance': provenance, 'human_review': 'pending',
                   'created_at': datetime.now(timezone.utc).isoformat()}
            payload = json.dumps(doc, ensure_ascii=False, indent=2).encode()
            path = folder / f'{doc["revision"]:08d}.json'
            temporary = folder / ('.' + uuid.uuid4().hex + '.tmp')
            with temporary.open('xb') as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, path)  # Publish a complete immutable record atomically.
            finally:
                temporary.unlink()
            directory = os.open(folder, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            return doc

    def patch_cells(self, atom_id, base_version_id, operations, intent, actor='codex'):
        doc = self.get(atom_id, base_version_id)
        source = doc['html']
        parsed = inspect(source)
        if not isinstance(operations, list) or not 1 <= len(operations) <= 100:
            raise ValueError('One to 100 object operations required')
        patches, seen = [], set()
        for op in operations:
            cid = op.get('cell_id')
            if set(op) != {'cell_id', 'text'} or cid not in parsed.cells or cid in seen or not isinstance(op['text'], str) or len(op['text']) > 3000:
                raise ValueError('Invalid cell operation')
            seen.add(cid)
            cell = parsed.cells[cid]
            patches.append((cell['content_start'], cell['content_end'], html.escape(op['text'])))
        for start, end, replacement in sorted(patches, reverse=True):
            source = source[:start] + replacement + source[end:]
        return self.append(atom_id, source, base_version_id,
                           {'actor': actor, 'intent': intent, 'operations': operations})
