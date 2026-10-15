import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from flask import Flask
from prep_context import collect,atomic_json

class ContextFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.app=Flask(__name__)
        self.app.config['SHENNAO_API_KEY']='synthetic-test-key'
    def tearDown(self):self.tmp.cleanup()
    def test_outage_is_not_a_successful_source_read(self):
        with patch('prep_context.urlopen',side_effect=OSError('Synthetic outage')):
            d=collect(self.app,self.root,{'topic':'learning'})
        coverage=next(c for c in d['coverage'] if c['kind']=='shennao')
        self.assertEqual(coverage['status'],'unavailable');self.assertEqual(d['sources'],[])
    def test_cache_is_explicitly_labelled_as_cache(self):
        cache=self.root/'data/prep-context-cache';cache.mkdir(parents=True)
        tid='12345678-1234-1234-1234-123456789abc'
        atomic_json(cache/'transcript-list.json',[dict(id=tid,title='learning',updated_at='synthetic-version')])
        atomic_json(cache/(tid+'.json'),dict(id=tid,title='learning',updated_at='synthetic-version',text='qiuyiwu 00:01:00\n'+('Synthetic learning experience. '*8)))
        with patch('prep_context.urlopen',side_effect=AssertionError('No live connection expected')):
            d=collect(self.app,self.root,{'topic':'learning'})
        c=next(c for c in d['coverage'] if c['kind']=='shennao')
        self.assertEqual(c['status'],'ready');self.assertTrue(c['metadata_cached']);self.assertIn('缓存',c['note'])
        self.assertEqual(d['sources'][0]['attribution'],'speaker_label_qiuyiwu_unverified_audio')

if __name__=='__main__':unittest.main()
