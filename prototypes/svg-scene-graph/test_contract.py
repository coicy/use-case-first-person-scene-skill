import copy, json, unittest
from pathlib import Path
from render import ContractError, validate, render, stablehash

ROOT=Path(__file__).parent
class SceneContractTests(unittest.TestCase):
    def setUp(self):self.doc=json.loads((ROOT/'scene-contract.json').read_text(encoding='utf-8'))
    def test_json_schema_draft202012(self):
        from jsonschema import Draft202012Validator
        schema=json.loads((ROOT/'scene-contract.schema.json').read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(self.doc)))
    def test_original_valid(self):validate(self.doc)
    def test_identical_stable_layout(self):
        out=[render(self.doc,s['id']).getroot() for s in self.doc['steps']]
        ids=['hud','world','inspector','selected-farm','worker-counter','production-counter','assign-button','commands']
        for id in ids:
            self.assertEqual(len({next(e.attrib['data-rect'] for e in scene if e.attrib.get('id')==id) for scene in out}),1)
    def test_changed_worker_count_fails(self):
        doc=copy.deepcopy(self.doc);doc['steps'][2]['objects']['farm-01']['workers']=1
        with self.assertRaisesRegex(ContractError,'state transition'):validate(doc)
    def test_wrong_selected_object_fails(self):
        doc=copy.deepcopy(self.doc);doc['steps'][1]['selected_object']='warehouse-01'
        with self.assertRaisesRegex(ContractError,'selected'):validate(doc)
    def test_wrong_data_binding_fails(self):
        doc=copy.deepcopy(self.doc);next(x for x in doc['design']['components'] if x['id']=='worker-counter')['bind']='objects.warehouse-01.workers'
        with self.assertRaisesRegex(ContractError,'bindings'):validate(doc)
    def test_missing_control_fails(self):
        doc=copy.deepcopy(self.doc);doc['design']['components']=[x for x in doc['design']['components'] if x['id']!='assign-button']
        with self.assertRaisesRegex(ContractError,'component'):validate(doc)
    def test_wrong_layout_topology_fails(self):
        doc=copy.deepcopy(self.doc);next(x for x in doc['design']['components'] if x['id']=='inspector')['rect']=[850,70,350,650]
        with self.assertRaisesRegex(ContractError,'adjacency'):validate(doc)
    def test_unapproved_must_remain_unapproved(self):
        doc=copy.deepcopy(self.doc);doc['authority']='approved'
        with self.assertRaisesRegex(ContractError,'approval'):validate(doc)
    def test_inspection_does_not_change_state(self):
        doc=copy.deepcopy(self.doc);doc['steps'][1]['objects']['farm-01']['workers']=3
        with self.assertRaisesRegex(ContractError,'Inspection changed'):validate(doc)
if __name__=='__main__':unittest.main()
