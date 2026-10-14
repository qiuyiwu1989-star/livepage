import unittest
from processing_status import page_status, course_summary

class ProcessingStatusTest(unittest.TestCase):
    def test_import_is_not_job_or_annotation(self):
        p={'annotation':{'source_text':'text'},'processing':{'html':'keynote_deck_export_available'},'html':{'status':'missing'}}
        s=page_status(p)
        self.assertEqual((s['annotation'],s['html'],s['task']),('pending','pending','unregistered'))
    def test_draft_and_global_review_do_not_confirm(self):
        p={'annotation':{'vlm_summary':{'topic':'x'}},'html':{'status':'local_exists','verified':'pixel-compare'},'human_review':'confirmed'}
        self.assertFalse(page_status(p)['complete'])
        self.assertEqual(page_status(p,{'status':'succeeded'})['html'],'draft')
    def test_scoped_review_and_course_identity(self):
        p={'page_id':'p','deck_id':'a','annotation':{'summary':'x'},'html':{'status':'local_exists'},'stage_reviews':{s:{'status':'confirmed','evidence_ref':'review-1'} for s in ('annotation','html')}}
        d=course_summary([{'deck_id':'a','title':'same'},{'deck_id':'b','title':'same'}],[p],{'p':{'status':'running'}})
        self.assertEqual([x['page_count'] for x in d],[1,0])
        self.assertEqual(d[0]['complete'],1)
        self.assertEqual(d[0]['counts']['task'],{'running':1})
