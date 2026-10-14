import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
import governance_api


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.generated = self.root / 'migration/generated'
        self.generated.mkdir(parents=True)
        self.patch = patch.object(governance_api, 'MIGRATION', self.root / 'migration')
        self.patch.start()
        self.data = {'decks': [{'deck_id': 'd', 'title': '课程'}], 'pages': [
            {'page_id': 'a', 'deck_id': 'd', 'title': '同页', 'page_number': 1,
             'source_kind': 'legacy_ui_inventory', 'annotation_completeness': 'ui_metadata_only',
             'html': {'status': 'missing'}, 'thumbnail_url': 'https://example.com/a.jpg'},
            {'page_id': 'b', 'deck_id': 'd', 'title': '同页', 'page_number': 2,
             'html': {'status': 'unverified_remote'}, 'thumbnail_url': 'javascript:alert(1)'},
            {'page_id': 'c', 'deck_id': 'd', 'title': '', 'html': {'status': 'local_exists'}},
            {'page_id': 'd', 'deck_id': 'd', 'title': '', 'html': {'status': 'missing'}},
        ]}
        self.write('catalog.json', self.data)
        self.write('atomic-catalog.json', {'atoms': [
            {'identity_status': 'provisional_per_occurrence', 'occurrence_ids': ['a']},
            {'identity_status': 'confirmed', 'occurrence_ids': ['b']},
            {'identity_status': 'provisional_per_occurrence', 'occurrence_ids': ['stale']},
        ]})
        app = Flask(__name__)
        governance_api.register_governance(app, self.root)
        self.client = app.test_client()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def write(self, name, data):
        (self.generated / name).write_text(json.dumps(data))

    def test_candidates_never_claim_identity_and_omit_self(self):
        result = self.client.get('/api/library/page/a/related').get_json()
        self.assertFalse(result['identity_confirmed'])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['pages'][0]['page_id'], 'b')
        self.assertEqual(result['pages'][0]['status'], 'unconfirmed')
        self.assertIsNone(result['pages'][0]['thumbnail_url'])
        self.assertEqual(self.client.get('/api/library/page/c/related').get_json()['total'], 0)
        self.assertEqual(self.client.get('/api/library/page/no/related').status_code, 404)

    def test_counts_and_missing_atomic_are_explicit(self):
        counts = self.client.get('/api/library/governance').get_json()['counts']
        self.assertEqual(counts, {'pages': 4, 'decks': 1, 'missing_old_annotations': 1,
                                 'pending_html': 2, 'provisional': 1, 'confirmed': 0, 'confirmed_occurrences': 0, 'candidate_groups': 1})
        (self.generated / 'atomic-catalog.json').unlink()
        result = self.client.get('/api/library/governance').get_json()
        self.assertIsNone(result['counts']['provisional'])
        self.assertEqual(result['status'], 'atomic_pending')

    def test_cache_refreshes_without_mutating_sources(self):
        before = {p.name: p.read_bytes() for p in self.generated.iterdir()}
        self.client.get('/api/library/governance')
        self.client.get('/api/library/page/a/related')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.generated.iterdir()})
        new = copy.deepcopy(self.data)
        new['pages'][1]['title'] = '修改后的标题'
        self.write('catalog.json', new)
        self.assertEqual(self.client.get('/api/library/page/a/related').get_json()['total'], 0)
        self.assertEqual(self.client.get('/api/library/governance').get_json()['counts']['candidate_groups'], 0)

    def test_local_paths_are_contained_and_urls_safe(self):
        self.data['pages'][1]['thumbnail'] = {'local_path': str(self.root / 'thumbs/中文.jpg')}
        self.write('catalog.json', self.data)
        result = self.client.get('/api/library/page/a/related').get_json()['pages'][0]
        self.assertEqual(result['thumbnail_url'], '/thumbs/%E4%B8%AD%E6%96%87.jpg')
        self.data['pages'][1]['thumbnail']['local_path'] = '/private/not-a-public-asset'
        self.data['pages'][1]['thumbnail_url'] = 'https://user:password@example.com/a.jpg'
        self.write('catalog.json', self.data)
        self.assertIsNone(self.client.get('/api/library/page/a/related').get_json()['pages'][0]['thumbnail_url'])

    def test_original_identity_groups_different_titles_without_merging_candidates(self):
        self.write('atomic-catalog.json', {'atoms': [
            {'atom_id': 'atom-0751', 'identity_status': 'original_library', 'occurrence_ids': ['a', 'c']},
            {'atom_id': 'other', 'identity_status': 'original_library', 'occurrence_ids': ['b']},
        ]})
        result = self.client.get('/api/library/page/a/related').get_json()
        self.assertTrue(result['identity_confirmed'])
        self.assertEqual([p['page_id'] for p in result['same_atom']], ['c'])
        self.assertEqual([p['page_id'] for p in result['candidates']], ['b'])
        self.assertEqual(result['same_atom'][0]['reason'], 'source_atom_mapping')
        counts = self.client.get('/api/library/governance').get_json()['counts']
        self.assertEqual(counts['confirmed'], 2)
        self.assertEqual(counts['confirmed_occurrences'], 3)
        self.write('atomic-catalog.json', {'atoms': [
            {'atom_id': 'atom-0751', 'identity_status': 'original_library', 'occurrence_ids': ['a', 'b', 'c']},
        ]})
        self.assertEqual(self.client.get('/api/library/governance').get_json()['counts']['candidate_groups'], 0)
        self.assertEqual(self.client.get('/api/library/page/a/related').get_json()['candidates'], [])

    def test_missing_catalog_is_not_empty_success(self):
        (self.generated / 'catalog.json').unlink()
        self.assertEqual(self.client.get('/api/library/governance').status_code, 503)
        self.assertEqual(self.client.get('/api/library/page/a/related').status_code, 503)
        self.assertEqual(self.client.post('/api/library/governance').status_code, 405)


if __name__ == '__main__':
    unittest.main()
