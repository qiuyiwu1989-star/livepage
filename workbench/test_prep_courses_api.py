import json
import unittest
from test_assembly_api import AssemblyTests
from prep_courses_api import register_prep_courses


class PrepCoursesTests(AssemblyTests):
    def setUp(self):
        super().setUp()
        for i, page in enumerate(self.pages):
            page.update(deck_id='course', page_number=2-i, atomic_id='atom-' + page['page_id'])
        self.write_catalog()
        path = self.catalog / 'catalog.json'
        data = json.loads(path.read_text())
        data['decks'] = [dict(deck_id='course', legacy_ids=['mba'], title='母课程', page_count=2)]
        path.write_text(json.dumps(data))
        register_prep_courses(self.app, self.root)

    def test_master_order_idempotence_derive_and_source_untouched(self):
        source = (self.catalog / 'catalog.json').read_bytes()
        response = self.client.post('/api/prep/courses/mba/master')
        self.assertEqual(response.status_code, 201)
        master = response.json
        self.assertEqual([e['page_id'] for e in master['entries']], ['new', 'old'])
        self.assertEqual(self.client.post('/api/prep/courses/course/master').json['assembly_id'], master['assembly_id'])
        self.assertEqual(self.client.get('/api/prep/courses').json['courses'][0]['master_assembly_id'], master['assembly_id'])
        derived = self.client.post('/api/prep/assemblies/' + master['assembly_id'] + '/derive', json={'title':'本次授课', 'base_revision':1})
        self.assertEqual(derived.status_code, 201)
        self.assertEqual(derived.json['parent_assembly_id'], master['assembly_id'])
        self.assertNotEqual(derived.json['entries'][0]['entry_id'], master['entries'][0]['entry_id'])
        self.assertEqual(source, (self.catalog / 'catalog.json').read_bytes())

    def test_duplicate_entry_notes_reorder_and_restore(self):
        doc = self.create()
        url = '/api/assemblies/' + doc['assembly_id']
        items = [{'entry_id':e['entry_id'], 'page_id':e['page_id'], 'chapter':'案例', 'notes':str(i)} for i,e in enumerate(doc['entries'])]
        response = self.client.put(url, json={'title':'重排', 'entries':list(reversed(items)), 'base_revision':1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([e['notes'] for e in response.json['entries']], ['2','1','0'])
        self.assertEqual(self.client.put(url, json={'title':'冲突', 'entries':items, 'base_revision':1}).status_code, 409)
        restored = self.client.post(url+'/restore', json={'revision':1,'base_revision':2}).json
        self.assertEqual(restored['revision'], 3)
        self.assertEqual(restored['entries'],doc['entries'])

    def test_deleted_new_reference_blocked_existing_history_kept(self):
        doc = self.create()
        workspace = self.root / 'workspace'
        workspace.mkdir()
        (workspace/'deleted-atoms.json').write_text(json.dumps({'deleted':['atom-old']}))
        self.assertEqual(self.client.post('/api/assemblies', json={'title':'Bad','page_ids':['old']}).status_code,400)
        items=[{'entry_id':e['entry_id'],'page_id':e['page_id']} for e in doc['entries']]
        self.assertEqual(self.client.put('/api/assemblies/'+doc['assembly_id'],json={'title':'Keep','entries':items,'base_revision':1}).status_code,200)
        derived=self.client.post('/api/prep/assemblies/'+doc['assembly_id']+'/derive',json={'title':'Clean','base_revision':2}).json
        self.assertEqual([e['page_id'] for e in derived['entries']],['new'])


if __name__ == '__main__':
    unittest.main()
