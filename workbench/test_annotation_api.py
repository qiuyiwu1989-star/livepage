import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from flask import Flask
from annotation_api import register_annotations, note_search_text


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps({'pages': [{'page_id': 'old-001', 'deck_id': 'course-a',
            'page_number': 1, 'legacy_ids': ['org-001'], 'source_kind': 'legacy_ui_inventory',
            'annotation': {'source_text': '不可改写的原文'}}]}), encoding='utf-8')
        self.original = self.catalog.read_bytes()
        self.atomic_catalog = self.root / 'atomic-catalog.json'
        self.app = self.make_app()
        self.url = '/api/library/page/old-001/notes'

    def make_app(self):
        app = Flask(__name__)
        register_annotations(app, self.root, self.catalog, self.atomic_catalog)
        return app

    def test_append_persist_and_trace(self):
        with self.app.test_client() as client:
            self.assertEqual(client.get(self.url).json['notes'], [])
            first = client.post(self.url, json={'kind': 'explanation', 'text': '这页的解读',
                'course_title': '组织变革', 'session_title': '第一讲',
                'source_reference': '录音 2026-10-07', 'timecode': '00:12:05'})
            self.assertEqual(first.status_code, 201)
            note = first.json['note']
            self.assertEqual(note['author'], 'human')
            self.assertEqual(note['origin'], 'human_note')
            self.assertEqual(note['scope'], 'lecture_context')
            self.assertNotIn('atom_id', note['source_context'])
            self.assertEqual(note['source_context']['legacy_ids'], ['org-001'])
            self.assertEqual(note['source_reference'], '录音 2026-10-07')
            self.assertEqual(client.post(self.url, json={'kind': 'source_correction', 'text': '待核对的数据'}).status_code, 201)
        with self.make_app().test_client() as client:
            history = client.get(self.url).json['notes']
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0], note)
            self.assertNotEqual(history[0]['id'], history[1]['id'])
            self.assertEqual(history[1]['scope'], 'page_interpretation')
        self.assertEqual(self.catalog.read_bytes(), self.original)
        search = note_search_text(self.root)
        self.assertIn('这页的解读', search['old-001'])
        self.assertIn('第一讲', search['old-001'])
        self.assertIn('00:12:05', search['old-001'])

    def test_invalid_inputs_never_write(self):
        with self.app.test_client() as client:
            for payload in [[], None, {'kind': [], 'text': 'x'}, {'kind': 'example', 'text': ' '},
                            {'kind': 'example', 'text': 'x' * 20001},
                            {'kind': 'example', 'text': 'x', 'author': 'ai'},
                            {'kind': 'example', 'text': 'x', 'timecode': 12}]:
                response = client.post(self.url, data=json.dumps(payload), content_type='application/json')
                self.assertEqual(response.status_code, 400, payload)
            self.assertEqual(client.post(self.url, data='{', content_type='application/json').status_code, 400)
            self.assertEqual(client.get('/api/library/page/missing/notes').status_code, 404)
            self.assertEqual(client.post('/api/library/page/missing/notes', json={'kind': 'question', 'text': 'x'}).status_code, 404)
        self.assertFalse((self.root / 'workspace').exists())

    def test_atomic_refs_are_frozen_at_creation(self):
        self.atomic_catalog.write_text(json.dumps({'occurrences': [
            {'source_page_id': 'old-001', 'atom_id': 'atom-first', 'version_id': 'version-first'}]}))
        with self.app.test_client() as client:
            first = client.post(self.url, json={'kind': 'explanation', 'text': '第一版解读'}).json['note']
            self.assertEqual(first['source_context']['atom_id'], 'atom-first')
            self.assertEqual(first['source_context']['version_id'], 'version-first')
            self.atomic_catalog.write_text(json.dumps({'occurrences': [
                {'source_page_id': 'old-001', 'atom_id': 'atom-second', 'version_id': 'version-second'}]}))
            second = client.post(self.url, json={'kind': 'teaching_note', 'text': '新版课堂解读'}).json['note']
            self.assertEqual(second['source_context']['version_id'], 'version-second')
            self.assertEqual(second['scope'], 'lecture_context')
            self.assertEqual(client.get(self.url).json['notes'][0], first)

    def test_corruption_preserved(self):
        with self.app.test_client() as client:
            client.post(self.url, json={'kind': 'question', 'text': '问题'})
            path = next((self.root / 'workspace/annotations').glob('*.json'))
            path.write_text('{broken', encoding='utf-8')
            self.assertEqual(client.get(self.url).status_code, 503)
            self.assertEqual(client.post(self.url, json={'kind': 'example', 'text': '例子'}).status_code, 503)
            self.assertEqual(path.read_text(), '{broken')
            self.assertEqual(note_search_text(self.root), {})

    def test_concurrent_append_across_app_instances(self):
        other = self.make_app()
        def append(i):
            with (self.app if i % 2 else other).test_client() as client:
                return client.post(self.url, json={'kind': 'teaching_note', 'text': str(i)}).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(list(pool.map(append, range(20))), [201] * 20)
        with self.app.test_client() as client:
            notes = client.get(self.url).json['notes']
            self.assertEqual({n['text'] for n in notes}, {str(i) for i in range(20)})
            self.assertEqual(len({n['id'] for n in notes}), 20)


if __name__ == '__main__':
    unittest.main()
