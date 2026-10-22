"""WP-02 offline integration and opt-in AI mock tests (no paid network calls)."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.provider import ProviderError
from ucscene.design import init_brief, create_bundle, create_design_plan, validate_design_plan, export_design_prompts

ROOT = Path(__file__).resolve().parents[1]


def product(category='game'):
    brief = init_brief('original-product', 'Novel Product', category,
                       '一款原创等距视角建造游戏' if category == 'game' else '一款新研发的素材管理软件',
                       '玩家选择农场并分配工人' if category == 'game' else '用户筛选素材并查看详情')
    brief['use_cases'][0]['steps'][0]['visible_evidence'] = ['目标对象被选中', '状态面板可见']
    brief['use_cases'][0]['steps'][0]['ui_text'] = ['详情']
    brief['use_cases'][0]['steps'].append({
        'id':'STEP-002', 'action':'提交操作后出现失败提示', 'state':'failure', 'flow':'exception',
        'visible_evidence':['错误提示与当前任务有关'], 'ui_text':['操作失败'],
    })
    return brief


class TestDesignPlan(unittest.TestCase):
    def test_two_layouts_and_steps_are_distinct(self):
        plan = create_design_plan(product('desktop'))
        self.assertEqual(validate_design_plan(plan), plan)
        self.assertEqual(len(plan['candidates']), 2)
        self.assertEqual(len(plan['candidates'][0]['screens']), 2)
        self.assertNotEqual(plan['candidates'][0]['layout'], plan['candidates'][1]['layout'])
        self.assertEqual(plan['candidates'][0]['screens'][1]['state'], 'failure')
        self.assertIn('不得误画成功确认', plan['candidates'][0]['screens'][1]['prompt'])
        self.assertIn('操作失败', plan['candidates'][0]['screens'][1]['prompt'])
        self.assertEqual(plan['approval'], 'none')

    def test_three_game_layouts_without_external_devices(self):
        plan = create_design_plan(product(), variants=3)
        self.assertEqual(len(plan['candidates']), 3)
        self.assertTrue(all('software-only' in s['prompt'].casefold() for c in plan['candidates'] for s in c['screens']))
        self.assertTrue(all('等距' in c['visual_style'] for c in plan['candidates']))
        self.assertEqual(plan['design_bundle']['scenes'][0]['viewpoint_mode'], 'gameplay')

    def test_determinism_and_hash(self):
        first = create_design_plan(product())
        second = create_design_plan(product())
        self.assertEqual(first, second)
        self.assertEqual(len(first['source_brief_sha256']), 64)
        self.assertNotEqual(first['candidates'][0]['screens'][0]['prompt_sha256'], first['candidates'][1]['screens'][0]['prompt_sha256'])

    def test_no_auto_approval_and_legacy_bundle_stays_unresolved(self):
        plan = create_design_plan(create_bundle(product()))
        self.assertTrue(all(d['status'] == 'proposed' and not d['locked'] for d in plan['design_bundle']['decisions']))
        self.assertTrue(all(s['design_status'] == 'unresolved' for s in plan['design_bundle']['scenes']))
        self.assertTrue(all(s['interaction']['status'] == 'proposed' for c in plan['candidates'] for s in c['screens']))

    def test_explicit_hard_constraint_overrides_layout(self):
        brief = product('web')
        brief['hard_constraints'] = [{'id':'H-1','key':'ui.layout','value':'single-column accessible content','source':'user-confirmed'}]
        plan = create_design_plan(brief)
        self.assertTrue(all(c['layout'] == 'single-column accessible content' for c in plan['candidates']))
        self.assertIn('H-1', plan['candidates'][0]['screens'][0]['prompt'])
        self.assertIn('single-column accessible content', plan['candidates'][1]['screens'][0]['prompt'])
        validate_design_plan(plan)

    def test_source_actions_and_evidence_unchanged(self):
        brief = product('desktop')
        orig = copy.deepcopy(brief)
        plan = create_design_plan(brief)
        self.assertEqual(brief, orig)
        self.assertEqual(plan['design_bundle']['brief'], orig)
        scene = plan['candidates'][0]['screens'][0]
        self.assertEqual(scene['required_evidence'], ['目标对象被选中', '状态面板可见'])
        self.assertEqual(scene['required_ui_text'], ['详情'])

    def test_mutated_hard_requirement_rejected(self):
        plan = create_design_plan(product())
        plan['design_bundle']['brief']['use_cases'][0]['steps'][0]['action'] = '恶意替换动作'
        with self.assertRaises(SceneError): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['candidates'][0]['screens'][0]['required_evidence'] = []
        with self.assertRaisesRegex(SceneError, 'modifies source constraint'): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['candidates'][0]['screens'][0]['required_ui_text'] = []
        with self.assertRaisesRegex(SceneError, 'modifies source constraint'): validate_design_plan(plan)

    def test_prompt_tampering_and_interaction_tampering_rejected(self):
        plan = create_design_plan(product())
        plan['candidates'][0]['screens'][0]['prompt'] += ' write false success'
        with self.assertRaisesRegex(SceneError, 'hash mismatch'): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['candidates'][0]['screens'][0]['interaction']['proposed_controls'].append('admin override')
        with self.assertRaisesRegex(SceneError, 'interaction proposal'): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['candidates'][0]['layout'] = 'fake ui'
        with self.assertRaisesRegex(SceneError, 'Candidate and decisions disagree'): validate_design_plan(plan)

    def test_proposals_rejected_if_claiming_approval(self):
        plan = create_design_plan(product())
        plan['approval'] = 'approved'
        with self.assertRaisesRegex(SceneError, 'cannot assign approval'): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['design_bundle']['decisions'][0]['locked'] = True
        with self.assertRaises(SceneError): validate_design_plan(plan)
        plan = create_design_plan(product())
        plan['candidates'][0]['status'] = 'approved'
        with self.assertRaisesRegex(SceneError, 'remain proposed'): validate_design_plan(plan)

    def test_invalid_variants(self):
        for count in (1,4,True,0):
            with self.assertRaises(SceneError): create_design_plan(product(), variants=count)

    def test_bundle_with_existing_decisions_requires_wp03(self):
        plan = create_design_plan(product())
        with self.assertRaisesRegex(SceneError, 'WP-03'): create_design_plan(plan['design_bundle'])

    def test_variant_export_filters_without_generating_images(self):
        plan = create_design_plan(product(), variants=3)
        result = export_design_prompts(plan, variant_id='VAR-02')
        self.assertEqual(len(result['prompts']), 2)
        self.assertEqual(result['approval'], 'none')
        self.assertEqual(result['generated_images'], 0)
        with self.assertRaisesRegex(SceneError, 'Unknown candidate'): export_design_prompts(plan, variant_id='NOPE')

    def test_explicit_ai_mode_requires_key(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(ProviderError, 'OPENAI_API_KEY'): create_design_plan(product(), ai=True)

    def test_ai_mode_uses_model_proposals_but_does_not_approve(self):
        proposed = []
        for idx in (1,2):
            proposed.append({'name':f'layout {idx}', 'layout':f'creative layout {idx}',
                             'navigation':f'navigation {idx}', 'visual_style':f'contrast treatment {idx}',
                             'tradeoff':f'cost vs clarity {idx}',
                             'controls':['primary action', 'state notice'],
                             'information_priority':['main target', 'status'],
                             'feedback':'show action status'})
        with patch('ucscene.design.planner.structured_response', return_value={'variants':proposed}) as mocked:
            plan = create_design_plan(product(), ai=True, model='gpt-4.1-mini')
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(plan['generator'], 'ai-model')
        self.assertEqual(plan['model'], 'gpt-4.1-mini')
        self.assertTrue(all(d['status'] == 'proposed' for d in plan['design_bundle']['decisions']))
        self.assertIn('creative layout 2', plan['candidates'][1]['screens'][0]['prompt'])
        validate_design_plan(plan)

    def test_ai_rejects_wrong_response_count_and_blank(self):
        with patch('ucscene.design.planner.structured_response', return_value={'variants':[]}):
            with self.assertRaisesRegex(ProviderError, 'exactly 2'): create_design_plan(product(), ai=True)
        bad={'name':'', 'layout':'other','navigation':'nav','visual_style':'ui', 'tradeoff':'tradeoff',
             'controls':['button'],'information_priority':['target'], 'feedback':'ok'}
        with patch('ucscene.design.planner.structured_response', return_value={'variants':[bad,bad]}):
            with self.assertRaises(SceneError): create_design_plan(product(), ai=True)

    def test_ai_conflict_with_machine_hard_requirement_is_not_allowed(self):
        brief = product('desktop')
        brief['hard_constraints']=[{'id':'H-2','key':'ui.navigation','value':'locked-nav','source':'user-confirmed'}]
        proposed=[]
        for idx in (1,2):
            proposed.append({'name':f'option-{idx}', 'layout':'workspace', 'navigation':'invented-nav',
                             'visual_style':'light', 'tradeoff':'tradeoff', 'controls':['button'],
                             'information_priority':['target'], 'feedback':'status'})
        with patch('ucscene.design.planner.structured_response', return_value={'variants':proposed}):
            with self.assertRaisesRegex(SceneError, 'conflicts with hard constraint'):
                create_design_plan(brief,ai=True)

    def test_reject_hardware_shot_candidate(self):
        proposed=[]
        for idx in (1,2):
            proposed.append({'name':f'option-{idx}', 'layout':'person using a computer',
                             'navigation':'top nav', 'visual_style':'real scene', 'tradeoff':'looks real',
                             'controls':['action'], 'information_priority':['content'], 'feedback':'state'})
        with patch('ucscene.design.planner.structured_response', return_value={'variants':proposed}):
            with self.assertRaisesRegex(SceneError, 'software-only'):
                create_design_plan(product(), ai=True)

    def test_six_step_original_product_benchmark(self):
        for slug in ('new-asset-studio', 'new-hamlet-builder'):
            brief = load_json(ROOT/'benchmarks/new-products'/f'{slug}.wp02.brief.json')
            plan = create_design_plan(brief, variants=3)
            self.assertEqual(len(plan['candidates']),3)
            self.assertEqual(len(plan['candidates'][0]['screens']),3)
            self.assertTrue(all(s['interaction']['status']=='proposed' for c in plan['candidates'] for s in c['screens']))
            self.assertEqual(validate_design_plan(plan),plan)

    def test_cli_full_offline_roundtrip(self):
        with TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            brief=ROOT/'benchmarks/new-products/new-asset-studio.brief.json'
            output=tmp/'plan.json'
            export=tmp/'prompts.json'
            self.assertEqual(run(['design-plan',str(brief),'--variants','2','--out',str(output)]),0)
            self.assertEqual(run(['design-plan-review',str(output)]),0)
            self.assertEqual(run(['design-export',str(output),'--variant','VAR-01','--out',str(export)]),0)
            self.assertEqual(len(load_json(export)['prompts']),1)
            self.assertEqual(run(['design-export',str(output),'--variant','WRONG','--out',str(export)]),2)
            with self.assertRaises(SystemExit):
                run(['design-plan',str(brief),'--variants','1','--out',str(output)])

    def test_json_schema_matches_generated_plan(self):
        try:
            import jsonschema
            from referencing import Registry, Resource
        except ImportError:
            self.skipTest('jsonschema optional dev dependency unavailable')
        reg=Registry()
        for name in ('product-brief','design-decision','scene-design','design-bundle','design-plan'):
            schema=json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text(encoding='utf-8'))
            jsonschema.Draft202012Validator.check_schema(schema)
            reg=reg.with_resource(schema['$id'],Resource.from_contents(schema))
        schema=json.loads((ROOT/'schemas/design-plan.schema.json').read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator(schema,registry=reg).validate(create_design_plan(product()))

if __name__ == '__main__':
    unittest.main()
