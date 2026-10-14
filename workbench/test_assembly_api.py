import json
from pathlib import Path
import tempfile
import unittest
from flask import Flask
from assembly_api import register_assemblies


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'pilot'
        self.root.mkdir()
        self.catalog = Path(self.temp.name) / 'catalog'
        self.catalog.mkdir()
        self.pages = [{'page_id': 'old', 'title': 'Old source', 'source_url': 'https://example.com/detail',
                       'image': {'url': 'https://example.com/old.jpg'}, 'html': {'status': 'missing'}},
                      {'page_id': 'new', 'title': 'New PDF', 'image': {'local_path': str(self.root / 'images/new.png')},
                       'thumbnail': {'local_path': str(self.root / 'thumbs/new.jpg')},
                       'html': {'local_path': str(self.root / 'html/new.html')}}]
        self.write_catalog()
        self.app = Flask(__name__)
        self.app.config['ASSEMBLY_CATALOG_DIR'] = str(self.catalog)
        register_assemblies(self.app, self.root)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def write_catalog(self):
        (self.catalog / 'catalog.json').write_text(json.dumps({'pages': self.pages}))
        (self.catalog / 'atomic-catalog.json').write_text(json.dumps({'occurrences': [
            {'occurrence_id': p['page_id'], 'atom_id': 'atom-' + p['page_id'], 'version_id': 'v1-' + p['page_id']} for p in self.pages]}))

    def create(self):
        r = self.client.post('/api/assemblies', json={'title': 'Lesson', 'page_ids': ['old', 'new', 'old']})
        self.assertEqual(r.status_code, 201)
        return r.json

    def test_persistence_order_repetition_and_frozen_sources(self):
        doc = self.create()
        self.assertEqual([e['page_id'] for e in doc['entries']], ['old', 'new', 'old'])
        self.assertEqual(len({e['entry_id'] for e in doc['entries']}), 3)
        self.assertEqual(doc['entries'][1]['source_url'], '/images/new.png')
        self.assertEqual(doc['entries'][1]['html']['url'], '/html/new.html')
        self.pages[0]['title'] = 'Changed later'
        self.write_catalog()
        app = Flask('fresh')
        app.config['ASSEMBLY_CATALOG_DIR'] = str(self.catalog)
        register_assemblies(app, self.root)
        loaded = app.test_client().get('/api/assemblies/' + doc['assembly_id']).json
        self.assertEqual(loaded, doc)
        self.assertEqual(self.client.get('/api/assemblies').json['assemblies'][0]['page_count'], 3)
        updated = self.client.put('/api/assemblies/' + doc['assembly_id'], json={
            'title': 'Reordered', 'page_ids': ['new', 'old'], 'base_revision': 1}).json
        self.assertEqual(updated['entries'][1]['title'], 'Old source')
        self.assertEqual(updated['entries'][1]['entry_id'], doc['entries'][0]['entry_id'])

    def test_conflict_restore_and_immutable_history(self):
        doc = self.create()
        url = '/api/assemblies/' + doc['assembly_id']
        path = self.root / 'data/assemblies' / doc['assembly_id'] / '00000001.json'
        original = path.read_bytes()
        body = {'title': 'Updated', 'page_ids': ['new'], 'base_revision': 1}
        self.assertEqual(self.client.put(url, json=body).status_code, 200)
        self.assertEqual(self.client.put(url, json=body).status_code, 409)
        self.assertEqual(self.client.post(url + '/restore', json={'revision': 1, 'base_revision': 1}).status_code, 409)
        restored = self.client.post(url + '/restore', json={'revision': 1, 'base_revision': 2}).json
        self.assertEqual(restored['revision'], 3)
        self.assertEqual(restored['entries'], doc['entries'])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(self.client.get(url + '/history').json['history']), 3)

    def test_validation_and_corrupt_store_no_overwrite(self):
        self.assertEqual(self.client.post('/api/assemblies', json={'title': 'Bad', 'page_ids': ['missing']}).status_code, 400)
        self.assertEqual(self.client.post('/api/assemblies', json={'title': 'Bad', 'page_ids': [], 'surprise': 1}).status_code, 400)
        doc = self.create()
        url = '/api/assemblies/' + doc['assembly_id']
        for value in (None, True, '1', 1.5):
            self.assertEqual(self.client.put(url, json={'title': 'Bad', 'page_ids': [], 'base_revision': value}).status_code, 400)
        path = self.root / 'data/assemblies' / doc['assembly_id'] / '00000001.json'
        path.write_text('broken data')
        self.assertEqual(self.client.put(url, json={'title': 'No overwrite', 'page_ids': [], 'base_revision': 1}).status_code, 400)
        self.assertEqual(path.read_text(), 'broken data')

    def test_actual_legacy_catalog_supported(self):
        actual = Path(__file__).resolve().parent.parent / 'slide-library-migration/generated'
        if not (actual / 'catalog.json').exists():
            self.skipTest('Actual migration catalog not present')
        pages = json.loads((actual / 'catalog.json').read_text())['pages']
        ids = [p['page_id'] for p in pages]
        self.assertGreaterEqual(len(ids), 2274)
        app = Flask('real_catalog')
        app.config['ASSEMBLY_CATALOG_DIR'] = str(actual)
        register_assemblies(app, self.root)
        r = app.test_client().post('/api/assemblies', json={'title': 'All sources', 'page_ids': ids})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.json['entries']), len(ids))
        self.assertTrue(all(e['version_id'] and e['atom_id'] for e in r.json['entries']))


if __name__ == '__main__':
    unittest.main()
