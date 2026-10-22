"""New acceptance gate: generated content must be exclusively inside software."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ucscene.core import SceneError, build_plan, load_json, review_plan, save_json, validate_use_case
from ucscene.vision import review_image
ROOT = Path(__file__).resolve().parents[1]

class SoftwareOnlyTests(unittest.TestCase):
    def setUp(self):
        self.case = load_json(ROOT/'benchmarks/famous-projects/cases/godot-mob-scene.json')

    def test_godot_editor_is_only_software_pixels(self):
        plan = build_plan(self.case)
        self.assertEqual(plan['anchor']['frame_scope'], 'software-only')
        self.assertEqual(plan['anchor']['viewpoint_mode'], 'application-ui')
        for s in plan['scenes']:
            self.assertIn('full-bleed', s['prompt'].lower())
            self.assertIn('FORBIDDEN OUT-OF-SOFTWARE', s['prompt'])
            self.assertNotIn('plausible partial hand', s['prompt'])
        self.assertEqual(review_plan(plan), [])

    def test_no_hardware_or_humans_in_required_visuals(self):
        case = load_json(ROOT/'examples/warehouse-scan.json')
        case['steps'][0]['visible_evidence'].append('握着扫码终端的手')
        with self.assertRaisesRegex(SceneError, 'outside-software'):
            validate_use_case(case)
        case = load_json(ROOT/'examples/warehouse-scan.json')
        case['environment']='从用户眼睛看向显示器'
        with self.assertRaisesRegex(SceneError, 'physical user/device'):
            validate_use_case(case)

    def test_old_modes_and_old_plans_refused(self):
        self.case['viewpoint_mode']='physical-user'
        with self.assertRaisesRegex(SceneError, 'Deprecated'):
            build_plan(self.case)
        self.case['viewpoint_mode']='application-ui'
        plan=build_plan(self.case)
        plan['format_version']='1.0'
        self.assertTrue(any('regenerate' in e for e in review_plan(plan)))

    def test_both_game_perspectives_preserved(self):
        cases=ROOT/'benchmarks/famous-projects/cases'
        open_ttd=build_plan(load_json(cases/'openttd-rail.json'))
        luanti=build_plan(load_json(cases/'luanti-mining.json'))
        self.assertIn('GAME CAMERA: isometric',open_ttd['scenes'][0]['prompt'])
        self.assertIn('GAME CAMERA: first-person',luanti['scenes'][0]['prompt'])
        self.assertTrue(all('CAMERA: DIRECT game output' in s['prompt'] for s in open_ttd['scenes']+luanti['scenes']))

    def test_visual_anchor_schema_matches_new_plan(self):
        schema=json.loads((ROOT/'schemas/visual-anchor.schema.json').read_text(encoding='utf-8'))
        plan=build_plan(self.case)
        required=schema['properties']['scene_anchor']['required']
        self.assertTrue(all(k in plan['anchor'] for k in required))
        self.assertEqual(plan['anchor']['frame_scope'],'software-only')

    def test_review_rejects_screen_on_desk_even_when_evidence_passes(self):
        scene=build_plan(self.case)['scenes'][0]
        findings={
            'point_of_view':'pass','pov_reason':'scene controls match',
            'software_only':'fail','outside_software_elements':['monitor','desk'],
            'evidence':[{'requirement':e,'status':'pass','reason':'yes'} for e in scene['evidence']],
            'continuity':'not_checked','continuity_reason':'no reference',
            'ui_text':'not_checked','ui_text_reason':'none',
            'unsupported_visual_claims':[],'suggested_fixes':['crop to app viewport'],
        }
        with tempfile.TemporaryDirectory() as d:
            png=Path(d)/'sample.png'
            png.write_bytes(b'fake mock-only bytes')
            with patch('ucscene.vision.structured_response',return_value=findings):
                self.assertFalse(review_image(scene,png)['passed'])

if __name__=='__main__': unittest.main()
