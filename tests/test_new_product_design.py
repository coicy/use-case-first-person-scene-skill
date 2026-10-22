"""WP-01 contract tests; do not imply a running design/image model."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.design import (
    create_bundle, init_brief, migrate_legacy_case, scaffold_scenes,
    validate_design_bundle, validate_design_decision,
    validate_product_brief, validate_scene_design,
)

ROOT = Path(__file__).resolve().parents[1]


def new_brief(category='desktop'):
    return init_brief('new-inventory', 'Inventor', category,
                      '一款原创的素材管理工具，提供资源筛选和任务协作',
                      '筛选资源并查看条目详情')


def draft_decision(brief=None):
    return {
        'schema_version': '1.0', 'id': 'DD-001',
        'product_id': (brief or new_brief())['product_id'],
        'topic': 'navigation', 'proposal': 'Use a left sidebar',
        'rationale': 'Keeps filters visible', 'status': 'proposed',
        'locked': False, 'revision': 1, 'source': 'ai-proposal',
        'related_use_case_ids': ['UC-001'],
        'effects': [{'key': 'navigation.layout', 'value': 'sidebar'}],
    }


class TestNewProductModels(unittest.TestCase):
    def test_one_prompt_and_one_use_case_is_enough_without_existing_screenshot(self):
        brief = new_brief()
        self.assertEqual(validate_product_brief(brief), brief)
        self.assertEqual(brief['origin']['mode'], 'direct-prompt')
        self.assertNotIn('approved', json.dumps(brief))
        self.assertIn('visual style', brief['unknowns'])
        self.assertEqual(len(scaffold_scenes(brief)), 1)
        self.assertEqual(scaffold_scenes(brief)[0]['design_status'], 'unresolved')
        self.assertEqual(scaffold_scenes(brief)[0]['frame_scope'], 'software-only')

    def test_new_game_renders_gameplay_boundary(self):
        brief = new_brief('game')
        self.assertEqual(scaffold_scenes(brief)[0]['viewpoint_mode'], 'gameplay')

    def test_invalid_category_and_missing_required_field(self):
        b = new_brief()
        b['category'] = 'hardware'
        with self.assertRaises(SceneError): validate_product_brief(b)
        b = new_brief()
        b['use_cases'][0]['steps'] = []
        with self.assertRaises(SceneError): validate_product_brief(b)

    def test_duplicate_requirement_and_step_ids_rejected(self):
        b = new_brief()
        b['requirements'].append(copy.deepcopy(b['requirements'][0]))
        with self.assertRaisesRegex(SceneError, 'duplicate'): validate_product_brief(b)
        b = new_brief()
        b['use_cases'][0]['steps'].append(copy.deepcopy(b['use_cases'][0]['steps'][0]))
        with self.assertRaisesRegex(SceneError, 'duplicate'): validate_product_brief(b)

    def test_invalid_requirement_reference(self):
        b = new_brief()
        b['requirements'][0]['use_case_ids'] = ['nonexistent']
        with self.assertRaisesRegex(SceneError, 'unknown use case'): validate_product_brief(b)

    def test_duplicate_hard_constraints_detected(self):
        b = new_brief()
        b['hard_constraints'] = [
            {'id': 'C-A', 'key':'navigation.layout', 'value':'sidebar', 'source':'user-confirmed'},
            {'id': 'C-B', 'key':'navigation.layout', 'value':'top-tabs', 'source':'user-confirmed'},
        ]
        with self.assertRaisesRegex(SceneError, 'Contradictory'): validate_product_brief(b)

    def test_ai_proposal_is_not_automatically_approved(self):
        b = new_brief()
        d = draft_decision(b)
        validate_design_decision(d)
        packet = create_bundle(b)
        packet['decisions'] = [d]
        self.assertEqual(validate_design_bundle(packet), packet)
        d['status'] = 'approved'
        d['locked'] = True
        with self.assertRaisesRegex(SceneError, 'approval'): validate_design_decision(d)
        d['approval'] = {'by': 'user', 'evidence_ref': 'turn-44-approval'}
        self.assertEqual(validate_design_decision(d), d)
        d['locked'] = False
        d['status'] = 'proposed'
        with self.assertRaisesRegex(SceneError, 'cannot claim'): validate_design_decision(d)

    def test_approved_decisions_cannot_contradict_each_other(self):
        brief = new_brief()
        bundle = create_bundle(brief)
        left = draft_decision(brief)
        left.update(status='approved', locked=True, approval={'by':'user','evidence_ref':'review-A'})
        right = draft_decision(brief)
        right.update(id='DD-002', status='approved', locked=True,
                     effects=[{'key':'navigation.layout', 'value':'top-tabs'}],
                     approval={'by':'user','evidence_ref':'review-B'})
        bundle['decisions'] = [left, right]
        with self.assertRaisesRegex(SceneError, 'contradict each other'):
            validate_design_bundle(bundle)

    def test_reject_unknown_properties_and_incorrect_types(self):
        b = new_brief()
        b['approved'] = True
        with self.assertRaisesRegex(SceneError, 'unexpected fields'): validate_product_brief(b)
        d = draft_decision()
        d['locked'] = 1
        with self.assertRaisesRegex(SceneError, 'boolean'): validate_design_decision(d)
        d = draft_decision()
        d['revision'] = True
        with self.assertRaisesRegex(SceneError, 'positive integer'): validate_design_decision(d)

    def test_not_allowed_to_lock_unapproved(self):
        d = draft_decision()
        d['locked'] = True
        with self.assertRaisesRegex(SceneError, 'Only approved'): validate_design_decision(d)

    def test_explicit_hard_constraint_conflict_blocks_bundle(self):
        b = new_brief()
        b['hard_constraints'] = [{'id':'C-1', 'key':'navigation.layout', 'value':'top-tabs', 'source':'user-confirmed'}]
        packet = create_bundle(b)
        packet['decisions'].append(draft_decision(b))
        with self.assertRaisesRegex(SceneError, 'conflicts with confirmed hard constraints'): validate_design_bundle(packet)
        packet['decisions'][0]['effects'][0]['value'] = 'top-tabs'
        self.assertEqual(validate_design_bundle(packet), packet)

    def test_scene_cross_references_and_approval(self):
        b = new_brief()
        bundle = create_bundle(b)
        s = bundle['scenes'][0]
        s['requirement_ids'] = ['REQ-missing']
        with self.assertRaisesRegex(SceneError, 'unknown requirement'): validate_design_bundle(bundle)
        s['requirement_ids'] = ['REQ-001']
        s['design_status'] = 'approved'
        with self.assertRaisesRegex(SceneError, 'Approved scene'): validate_scene_design(s)
        s['design_decision_ids'] = ['DD-001']
        bundle['decisions'] = [draft_decision(b)]
        with self.assertRaisesRegex(SceneError, 'unapproved'): validate_design_bundle(bundle)
        bundle['decisions'][0].update(status='approved', locked=True,
                                      approval={'by':'user','evidence_ref':'review-turn-1'})
        self.assertEqual(validate_design_bundle(bundle), bundle)

    def test_rejected_decisions_cannot_drive_scenes(self):
        b = new_brief()
        packet = create_bundle(b)
        d = draft_decision(b)
        d.update(status='rejected', approval={'by':'user','evidence_ref':'review-turn-2'})
        packet['decisions'].append(d)
        packet['scenes'][0]['design_decision_ids'] = ['DD-001']
        with self.assertRaisesRegex(SceneError, 'rejected'): validate_design_bundle(packet)

    def test_approved_user_requirements_stay_intact(self):
        b = new_brief()
        b['use_cases'][0]['steps'][0]['visible_evidence'] = ['标签筛选器', '已过滤的结果']
        b['use_cases'][0]['steps'][0]['ui_text'] = ['筛选']
        bundle = create_bundle(b)
        bundle['scenes'][0]['visible_evidence'].pop()
        with self.assertRaisesRegex(SceneError, 'drops required visible evidence'):
            validate_design_bundle(bundle)
        bundle = create_bundle(b)
        bundle['scenes'][0]['expected_ui_text'] = []
        with self.assertRaisesRegex(SceneError, 'drops required UI text'):
            validate_design_bundle(bundle)
        bundle = create_bundle(b)
        bundle['scenes'][0]['action'] = '无关任务'
        with self.assertRaisesRegex(SceneError, 'overrides source use-case action'):
            validate_design_bundle(bundle)
        bundle = create_bundle(b)
        bundle['scenes'][0]['flow'] = 'exception'
        with self.assertRaisesRegex(SceneError, 'overrides source use-case flow'):
            validate_design_bundle(bundle)

    def test_scene_product_and_step_mismatch(self):
        b = new_brief()
        packet = create_bundle(b)
        packet['scenes'][0]['step_id'] = 'not-real'
        with self.assertRaisesRegex(SceneError, 'unknown step'): validate_design_bundle(packet)
        packet['scenes'][0]['step_id'] = 'STEP-001'
        packet['scenes'][0]['product_id'] = 'not-real'
        with self.assertRaisesRegex(SceneError, 'another product'): validate_design_bundle(packet)

    def test_legacy_migration_preserves_ids_and_does_not_claim_approval(self):
        old = load_json(ROOT / 'examples' / 'warehouse-scan.json')
        original = copy.deepcopy(old)
        new = migrate_legacy_case(old, product_id='warehouse-concept', name='Warehouse Console', category='web')
        self.assertEqual(old, original)
        self.assertEqual(new['use_cases'][0]['id'], old['id'])
        self.assertEqual([x['id'] for x in new['use_cases'][0]['steps']], [x['id'] for x in old['steps']])
        self.assertTrue(all(r['authority'] == 'review-required' for r in new['requirements']))
        self.assertTrue(all(r['source'] == 'legacy-case' for r in new['requirements']))
        self.assertNotIn('approved', json.dumps(new))
        self.assertEqual(new['use_cases'][0]['steps'][2]['flow'], 'exception')
        self.assertEqual(new['use_cases'][0]['steps'][2]['ui_text'], ['条码不匹配'])
        self.assertTrue(any('Legacy viewpoint_mode' in r['text'] for r in new['requirements']))
        validate_design_bundle(create_bundle(new))

    def test_migrated_case_invalid_unknown_category(self):
        old = load_json(ROOT / 'examples' / 'warehouse-scan.json')
        with self.assertRaises(SceneError):
            migrate_legacy_case(old, product_id='product', name='Product', category='unknown')

    def test_real_examples_and_cli_smoke(self):
        for slug in ('new-asset-studio', 'new-hamlet-builder'):
            b = load_json(ROOT / 'benchmarks' / 'new-products' / (slug + '.brief.json'))
            bundle = load_json(ROOT / 'benchmarks' / 'new-products' / (slug + '.bundle.json'))
            validate_product_brief(b)
            validate_design_bundle(bundle)
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            brief = tmp / 'brief.json'
            bundle = tmp / 'bundle.json'
            migration = tmp / 'legacy.json'
            self.assertEqual(run(['brief-init', '--product-id', 'idea-1', '--name', 'Project', '--category', 'web',
                                  '--prompt', '新软件，用于管理任务', '--use-case', '用户创建任务', '--out', str(brief)]),0)
            self.assertEqual(run(['design-validate', str(brief), '--kind', 'brief']),0)
            self.assertEqual(run(['design-scaffold', str(brief), '--out', str(bundle)]),0)
            self.assertEqual(run(['design-validate', str(bundle), '--kind', 'bundle']),0)
            self.assertEqual(run(['migrate-legacy', str(ROOT / 'examples' / 'warehouse-scan.json'),
                                  '--product-id','legacy-migrated','--name','Warehouse','--out',str(migration)]),0)
            self.assertEqual(run(['design-validate', str(migration), '--kind', 'brief']),0)
            self.assertEqual(run(['design-validate', str(bundle), '--kind', 'scene']),2)

    def test_schema_files_match_runtime_fixtures(self):
        try:
            import jsonschema
            from referencing import Registry, Resource
        except ImportError:
            self.skipTest('Install optional jsonschema dev dependency to validate exported contract schemas')
        registry = Registry()
        for filename in ('product-brief', 'design-decision', 'scene-design', 'design-bundle'):
            document = json.loads((ROOT / 'schemas' / (filename+'.schema.json')).read_text())
            jsonschema.Draft202012Validator.check_schema(document)
            registry = registry.with_resource(document['$id'], Resource.from_contents(document))
        base = ROOT / 'benchmarks' / 'new-products' / 'new-asset-studio'
        b = load_json(str(base)+'.brief.json')
        bundle = load_json(str(base)+'.bundle.json')
        schema = json.loads((ROOT / 'schemas' / 'design-bundle.schema.json').read_text())
        jsonschema.Draft202012Validator(schema, registry=registry).validate(bundle)
        schema = json.loads((ROOT / 'schemas' / 'product-brief.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(b)

if __name__ == '__main__': unittest.main()
