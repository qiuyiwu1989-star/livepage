import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workbench'))
from html_versions import HtmlVersions, VersionConflict, inspect, digest

HTML = '''<table data-lp-table-id="table"><tr><th data-lp-cell-id="a">A</th><th data-lp-cell-id="b">B</th></tr><tr><td data-lp-cell-id="c"><span>C</span></td><td data-lp-cell-id="d">D</td></tr></table>'''
CONTENT = {'atom_id': 'synthetic', 'source_sha256': 'a'*64, 'rows': [{'cells': [{'id': c, 'text': c} for c in 'ab']}, {'cells': [{'id': c, 'text': c} for c in 'cd']}]}

class HtmlVersionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = HtmlVersions(self.tmp.name)
        self.base = self.store.append('synthetic', HTML, None, {'actor': 'codex'}, CONTENT)

    def test_docs_return_reread_and_old_pin(self):
        changed = HTML.replace('>D</td>', '>New &amp; true</td>')
        result = self.store.append('synthetic', changed, self.base['version_id'], {'actor': 'docs'})
        reopened = HtmlVersions(self.tmp.name).get('synthetic')
        self.assertEqual(reopened['version_id'], result['version_id'])
        self.assertEqual(reopened['html'], changed)
        self.assertEqual(reopened['cells'][-1]['text'], 'New & true')
        self.assertEqual(self.store.get('synthetic', self.base['version_id'])['html'], HTML)
        self.assertEqual(result['source_content'], CONTENT)

    def test_agent_and_manual_share_base_conflict(self):
        second = self.store.patch_cells('synthetic', self.base['version_id'], [{'cell_id': 'c', 'text': '<New>'}], 'change C')
        self.assertIn('&lt;New&gt;', second['html'])
        self.assertIn('>D</td>', second['html'])
        with self.assertRaises(VersionConflict):
            self.store.append('synthetic', HTML, self.base['version_id'], {'actor': 'docs'})
        self.assertEqual(len(self.store.history('synthetic')), 2)

    def test_inserted_and_removed_cells_keep_source_provenance(self):
        changed = HTML.replace('data-lp-cell-id="d"', 'data-lp-cell-id="new"')
        result = self.store.append('synthetic', changed, self.base['version_id'], {'actor':'docs'})
        self.assertEqual(result['removed_source_cell_ids'], ['d'])
        self.assertIsNone(result['cells'][-1]['source_cell_id'])
        self.assertEqual(result['source_content'], CONTENT)

    def test_rejects_raster_duplicate_and_identity_change(self):
        for bad in [HTML.replace('>D</td>', '><img src="x"></td>'), HTML.replace('cell-id="d"','cell-id="c"'), HTML.replace('table-id="table"','table-id="other"')]:
            with self.assertRaises(ValueError):
                self.store.append('synthetic', bad, self.base['version_id'], {'actor':'docs'})
        self.assertEqual(len(self.store.history('synthetic')), 1)

    def test_stored_hash_corruption_is_detected(self):
        path = Path(self.tmp.name)/'synthetic'/'00000001.json'
        path.write_text(path.read_text().replace('"html_sha256": "', '"html_sha256": "0'))
        with self.assertRaises(ValueError): self.store.get('synthetic')

    def test_two_writers_cannot_publish_same_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        barrier = Barrier(2)
        def save():
            barrier.wait()
            try:
                HtmlVersions(self.tmp.name).append('synthetic', HTML, self.base['version_id'], {'actor':'docs'})
                return 'saved'
            except VersionConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: save(), range(2)))
        self.assertEqual(sorted(results), ['conflict', 'saved'])
        self.assertEqual(len(self.store.history('synthetic')), 2)

    def test_malformed_ranges_never_enter_store(self):
        bad = [HTML.replace('<span>C</span></td>', '<span>C</span>'),
               HTML.replace('>D</td>', '/>'),
               HTML.replace('data-lp-cell-id="d"', 'data-lp-cell-id="d" data-lp-cell-id="e"')]
        for source in bad:
            with self.assertRaises(ValueError): inspect(source)
