import unittest
from prep_assembly import assembly_plan

class NarrativeAssemblyTests(unittest.TestCase):
    def doc(self):
        choices=[[],['p1','p2'],[],['p1'],['p3'],[]]
        return {'outline':{'sections':[{'title':'Part '+str(i),'minutes':10,'purpose':'Purpose','page_ids':ids,'source_ids':[]} for i,ids in enumerate(choices)]},'manuscript':{'sections':[{'script':'UNIQUE_SCRIPT_'+str(i),'stage_directions':'Cue'} for i in range(6)]}}
    def test_all_sections_survive_and_repeated_pages_are_explicit(self):
        items,review=assembly_plan(self.doc())
        self.assertEqual([e['page_id'] for e in items],['p1','p2','p3'])
        notes='\n'.join(e['notes'] for e in items)
        for i in range(6):self.assertEqual(notes.count('UNIQUE_SCRIPT_'+str(i)),1)
        self.assertEqual(len(review['section_cues']),6)
        self.assertEqual(review['omitted_repeats'],[{'page_id':'p1','section':'Part 3'}])
        self.assertIn('继续口述',items[1]['notes'])
    def test_deliberate_repeat_can_be_preserved(self):
        items,review=assembly_plan(self.doc(),deduplicate=False)
        self.assertEqual([e['page_id'] for e in items],['p1','p2','p1','p3'])
        self.assertEqual(review['omitted_repeats'],[])
    def test_no_slides_does_not_fabricate_a_page(self):
        d=self.doc()
        for s in d['outline']['sections']:s['page_ids']=[]
        with self.assertRaises(ValueError):assembly_plan(d)
    def test_long_oral_script_is_not_silently_cut(self):
        d=self.doc();d['manuscript']['sections'][0]['script']='x'*21000
        with self.assertRaisesRegex(ValueError,'不会静默截断'):assembly_plan(d)

if __name__=='__main__':unittest.main()
