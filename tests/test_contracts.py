import unittest
from livepage import validate_segment

class AudioEvidenceTests(unittest.TestCase):
    def test_out_of_source_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_segment(dict(start_seconds=2,end_seconds=20),10)

    def test_inference_cannot_self_confirm(self):
        s=dict(start_seconds=1,end_seconds=3,alignment_method='semantic_candidate',alignment_status='confirmed')
        with self.assertRaises(ValueError): validate_segment(s,10)
        s['confirmation_ref']='synthetic-review-1'
        self.assertEqual(validate_segment(s,10),s)
