"""WP-03 approval, frozen baseline, and future use case consistency tests."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.design import init_brief
from ucscene.design.planner import create_design_plan
from ucscene.design.system import create_design_system, revise_design_system, validate_design_system, compare_design_system
from ucscene.design.continuity import apply_design_system, validate_consistent_plan

ROOT = Path(__file__).resolve().parents[1]


def example_brief(category='desktop'):
    brief = init_brief('original-artist', 'Original Artist', category,
                       '原创游戏资产管理工具' if category != 'game' else '原创策略建设游戏',
                       '搜索并打开资源' if category != 'game' else '选择农场并查看生产状态')
    brief['use_cases'][0]['steps'][0]['visible_evidence'] = ['选中对象高亮']
    brief['use_cases'][0]['steps'][0]['ui_text'] = ['查看详情']
    return brief


def new_steps(brief):
    b = deepcopy(brief)
    b['use_cases'].append({
        'id': 'UC-002', 'title': '更新详情', 'actor': '用户', 'goal': '保存修改结果',
        'steps': [
            {'id': 'STEP-001', 'action': '编辑对象详情', 'state': 'in-progress', 'flow': 'main',
             'visible_evidence': ['编辑区域可见'], 'ui_text': ['编辑']},
            {'id': 'STEP-002', 'action': '保存失败显示错误信息', 'state': 'failure', 'flow': 'exception',
             'visible_evidence': ['操作失败状态明显'], 'ui_text': ['保存失败']},
        ],
    })
    return b


class TestDesignSystem(unittest.TestCase):
    def setUp(self):
        self.brief = example_brief()
        self.plan = create_design_plan(self.brief, variants=3)

    def approve(self, variant='VAR-02', locked=True):
        return create_design_system(self.plan, variant, evidence_ref='CHAT-USER-APPROVAL-001', locked=locked)

    def test_approve_exact_variant_no_auto_selection(self):
        system = self.approve()
        self.assertEqual(validate_design_system(system, plan=self.plan), system)
        self.assertEqual(system['approved_design']['layout'], self.plan['candidates'][1]['layout'])
        self.assertEqual(system['selected_variant_id'], 'VAR-02')
        self.assertTrue(system['locked'])
        self.assertTrue(all(x['status'] == 'approved' and x['locked'] for x in system['approved_decisions']))
        self.assertTrue(all(d['status'] == 'proposed' for d in self.plan['design_bundle']['decisions']))
        self.assertEqual(system['approval']['by'], 'user')

    def test_no_evidence_rejected(self):
        with self.assertRaisesRegex(SceneError, 'evidence_ref'):
            create_design_system(self.plan, 'VAR-01', evidence_ref='')

    def test_unknown_variant_rejected(self):
        with self.assertRaisesRegex(SceneError, 'Unknown'):
            self.approve('VAR-99')

    def test_design_hash_tampering_rejected(self):
        system = self.approve()
        system['approved_design']['navigation'] = 'tampered'
        with self.assertRaises(SceneError): validate_design_system(system)

    def test_decision_status_tampering_rejected(self):
        system = self.approve()
        system['approved_decisions'][0]['status'] = 'proposed'
        with self.assertRaises(SceneError): validate_design_system(system)

    def test_original_source_plan_tampering_rejected(self):
        system = self.approve()
        changed = deepcopy(self.plan)
        changed['warning'] += 'tampered'
        with self.assertRaisesRegex(SceneError, 'source plan changed'):
            validate_design_system(system, plan=changed)

    def test_locked_baseline_cannot_be_revised_without_override(self):
        system = self.approve()
        with self.assertRaisesRegex(SceneError, 'locked'):
            revise_design_system(system, 'ui.layout', 'New layout', evidence_ref='USER-EDIT-001')
        self.assertEqual(system['revision'], 1)

    def test_explicit_locked_override_preserves_lock(self):
        system = self.approve()
        revised = revise_design_system(system, 'ui.layout', 'New approved layout',
                                        evidence_ref='USER-EDIT-001', override_lock=True)
        self.assertEqual(validate_design_system(revised)['revision'], 2)
        self.assertTrue(revised['locked'])
        self.assertEqual(revised['history'][-1]['previous_sha256'], system['digest_sha256'])
        self.assertEqual(revised['history'][-1]['action'], 'revise-locked')
        self.assertNotEqual(revised['digest_sha256'], system['digest_sha256'])
        self.assertNotEqual(revised['approved_design']['layout'], system['approved_design']['layout'])
        self.assertEqual(revised['approved_design']['navigation'], system['approved_design']['navigation'])

    def test_diff_detects_changed_frozen_baseline(self):
        old = self.approve()
        new = revise_design_system(old, 'ui.layout', 'Revised approved layout',
                                   evidence_ref='USER-EDIT-002', override_lock=True)
        report = compare_design_system(old, new)
        self.assertEqual(report['changes'][0]['key'], 'ui.layout')
        self.assertTrue(report['requires_scene_review'])
        with self.assertRaisesRegex(SceneError, 'consecutive'):
            compare_design_system(old, old)

    def test_unlocked_revise_has_revision_chain(self):
        system = self.approve(locked=False)
        second = revise_design_system(system, 'ui.visual_style', 'Softer contrast', evidence_ref='USER-002')
        third = revise_design_system(second, 'ui.navigation', 'Simple nav', evidence_ref='USER-003')
        self.assertEqual(third['revision'], 3)
        self.assertEqual(len(third['history']), 3)
        self.assertEqual(third['history'][-1]['previous_sha256'], second['digest_sha256'])
        self.assertTrue(all(d['status'] == 'approved' and not d['locked'] for d in third['approved_decisions']))
        validate_design_system(third)

    def test_same_value_change_rejected(self):
        system = self.approve(locked=False)
        with self.assertRaisesRegex(SceneError, 'no change'):
            revise_design_system(system, 'ui.layout', system['approved_design']['layout'], evidence_ref='USER-003')

    def test_hard_constraint_prevents_revision(self):
        brief = example_brief()
        brief['hard_constraints'] = [{'id':'H1','key':'ui.layout','value':'one-column','source':'user-confirmed'}]
        plan = create_design_plan(brief)
        system = create_design_system(plan, 'VAR-01', evidence_ref='APPROVAL', locked=True)
        with self.assertRaisesRegex(SceneError, 'hard constraint'):
            revise_design_system(system, 'ui.layout', 'different', evidence_ref='APPROVAL2', override_lock=True)
        with self.assertRaisesRegex(SceneError, 'hard constraint'):
            apply_design_system(system, {**brief, 'hard_constraints': []})

    def test_consistent_new_use_case_preserves_approved_design(self):
        system = self.approve()
        future_brief = new_steps(self.brief)
        applied = apply_design_system(system, future_brief)
        self.assertEqual(validate_consistent_plan(applied, system=system, brief=future_brief), applied)
        self.assertEqual(len(applied['scenes']), 3)
        self.assertEqual(applied['approved_layout'], system['approved_design']['layout'])
        self.assertTrue(all('APPROVED UI LAYOUT: ' + system['approved_design']['layout'] in s['prompt'] for s in applied['scenes']))
        self.assertTrue(all(s['design_status'] == 'approved-baseline' for s in applied['scenes']))
        self.assertEqual(applied['scenes'][-1]['state'], 'failure')
        self.assertIn('保存失败', applied['scenes'][-1]['prompt'])
        self.assertEqual(applied['generated_images'], 0)

    def test_apply_does_not_require_original_brief_hash(self):
        system = self.approve()
        future_brief = new_steps(self.brief)
        self.assertNotEqual(system['source_brief_sha256'], apply_design_system(system, future_brief)['source_brief_sha256'])

    def test_wrong_product_and_conflicting_new_constraint_rejected(self):
        system = self.approve()
        wrong = example_brief()
        wrong['product_id'] = 'someone-else'
        with self.assertRaisesRegex(SceneError, 'different product'):
            apply_design_system(system, wrong)
        changed = new_steps(self.brief)
        changed['hard_constraints'] = [{'id':'H2','key':'ui.layout','value':'something else','source':'user-confirmed'}]
        with self.assertRaisesRegex(SceneError, 'contradicts'):
            apply_design_system(system, changed)

    def test_applied_plan_cannot_hide_source_evidence_or_change_prompt(self):
        system = self.approve()
        applied = apply_design_system(system, self.brief)
        applied['scenes'][0]['required_evidence'] = []
        with self.assertRaisesRegex(SceneError, 'diverge'):
            validate_consistent_plan(applied, system=system, brief=self.brief)
        applied = apply_design_system(system, self.brief)
        applied['scenes'][0]['prompt'] += 'Change UI style illegally'
        with self.assertRaisesRegex(SceneError, 'diverge'):
            validate_consistent_plan(applied, system=system, brief=self.brief)

    def test_game_camera_is_not_real_world_operator(self):
        game = example_brief('game')
        system = create_design_system(create_design_plan(game), 'VAR-01', evidence_ref='APPROVAL')
        scene = apply_design_system(system, game)['scenes'][0]
        self.assertIn('software-only', scene['prompt'])
        self.assertIn('in-game', scene['prompt']) if 'in-game' in scene['prompt'] else self.assertIn('application or game output', scene['prompt'])

    def test_cli_approval_and_application(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp)
            plan_path = p/'plan.json';plan_path.write_text(json.dumps(self.plan,ensure_ascii=False),encoding='utf-8')
            sys_path = p/'system.json';draft_path = p/'consistent.json';brief_path=p/'brief.json'
            brief_path.write_text(json.dumps(new_steps(self.brief),ensure_ascii=False),encoding='utf-8')
            self.assertEqual(run(['design-system-create', str(plan_path), '--variant','VAR-02',
                                  '--approve','--evidence-ref','USER-APPROVAL-001','--lock','--out',str(sys_path)]),0)
            self.assertEqual(run(['design-system-review',str(sys_path),'--plan',str(plan_path)]),0)
            self.assertEqual(run(['design-apply',str(sys_path),str(brief_path),'--out',str(draft_path)]),0)
            self.assertEqual(run(['design-apply-review',str(draft_path),'--system',str(sys_path),'--brief',str(brief_path)]),0)
            self.assertEqual(len(load_json(draft_path)['scenes']),3)
            revised_path = p/'revised.json'
            self.assertEqual(run(['design-system-revise',str(sys_path),'--key','ui.layout','--value','Refined layout',
                                  '--approve','--evidence-ref','USER-APPROVAL-002','--override-lock','--out',str(revised_path)]),0)
            self.assertEqual(load_json(revised_path)['revision'],2)
            self.assertEqual(run(['design-apply-review',str(draft_path),'--system',str(revised_path),'--brief',str(brief_path)]),2)

    def test_schemas_are_valid_and_accept_actual_output(self):
        import jsonschema
        schemas = ['design-system.schema.json', 'consistent-scene-plan.schema.json']
        for name in schemas:
            schema = json.loads((ROOT/'schemas'/name).read_text(encoding='utf-8'))
            jsonschema.Draft202012Validator.check_schema(schema)
        system = self.approve()
        plan = apply_design_system(system, self.brief)
        jsonschema.validate(system, json.loads((ROOT/'schemas'/schemas[0]).read_text(encoding='utf-8')))
        jsonschema.validate(plan, json.loads((ROOT/'schemas'/schemas[1]).read_text(encoding='utf-8')))

if __name__ == '__main__':
    unittest.main()
