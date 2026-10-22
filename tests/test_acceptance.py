import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
from ucscene.acceptance import create_gallery, verify_gallery
from ucscene.cli import run
from ucscene.core import SceneError

SUITE = Path(__file__).resolve().parents[1] / 'benchmarks/famous-projects/suite.json'


class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / 'src'
        self.src.mkdir()
        self.image = self.src / 'test.png'
        Image.new('RGB', (320, 180), (40, 65, 92)).save(self.image)
        self.selection = self.root / 'selection.json'
        self.item = {
            'scene_id': 'BENCH-GODOT-MOB--03-gravity',
            'image': 'test.png',
            'origin': 'conversation-image-generation',
            'notes': 'Example. Need independent visual inspection.',
        }
        self.out = self.root / 'gallery'

    def select(self, items=None):
        self.selection.write_text(json.dumps({'samples': items or [self.item]}), encoding='utf8')

    def test_create_uses_real_sha_and_no_claim_of_success(self):
        self.select()
        report = create_gallery(SUITE, self.selection, self.src, self.out)
        self.assertEqual(report['visual_verdict'], 'user_review_pending')
        self.assertEqual(report['selected_samples'], 1)
        self.assertTrue(report['partial_selection'])
        self.assertTrue((self.out / 'index.html').exists())
        self.assertEqual(verify_gallery(self.out / 'manifest.json')['image_integrity_verified'], 1)
        self.assertIn('导出用户验收意见', (self.out / 'index.html').read_text())
        self.assertEqual(report['samples'][0]['origin'], 'conversation-image-generation')

    def test_detects_tampered_image(self):
        self.select()
        report = create_gallery(SUITE, self.selection, self.src, self.out)
        p = self.out / report['samples'][0]['image']
        Image.new('RGB', (320, 180), (80, 0, 0)).save(p)
        with self.assertRaisesRegex(SceneError, 'changed'):
            verify_gallery(self.out / 'manifest.json')

    def test_wrong_case_is_rejected(self):
        self.select([{**self.item, 'scene_id': 'FAKE--03-gravity'}])
        with self.assertRaisesRegex(SceneError, 'Unknown scene'):
            create_gallery(SUITE, self.selection, self.src, self.out)

    def test_duplicate_scene_is_rejected(self):
        self.select([self.item, self.item])
        with self.assertRaisesRegex(SceneError, 'Duplicate'):
            create_gallery(SUITE, self.selection, self.src, self.out)

    def test_missing_origin_is_rejected(self):
        self.select([{k: v for k, v in self.item.items() if k != 'origin'}])
        with self.assertRaisesRegex(SceneError, 'origin'):
            create_gallery(SUITE, self.selection, self.src, self.out)

    def test_origin_does_not_imply_prompt_used(self):
        self.select()
        result = create_gallery(SUITE, self.selection, self.src, self.out)
        self.assertEqual(result["samples"][0]["generation_prompt_match"], "not_verified")
        self.assertIsNone(result["samples"][0]["generation_prompt_sha256"])

    def test_cli_origin_requires_verified_prompt_digest(self):
        self.select([{**self.item, "origin": "ucscene-cli"}])
        with self.assertRaisesRegex(SceneError, "matching generation_prompt"):
            create_gallery(SUITE, self.selection, self.src, self.out)

    def test_path_traversal_is_rejected(self):
        self.select([{**self.item, 'image': '../other.png'}])
        with self.assertRaisesRegex(SceneError, 'traverse'):
            create_gallery(SUITE, self.selection, self.src, self.out)

    def test_html_escapes_untrusted_notes(self):
        self.select([{**self.item, 'notes': '<script>alert("oops")</script>'}])
        create_gallery(SUITE, self.selection, self.src, self.out)
        text = (self.out / 'index.html').read_text()
        self.assertIn('&lt;script&gt;alert(', text)
        self.assertNotIn('<script>alert(', text)

    def test_output_cannot_be_inside_source(self):
        self.select()
        with self.assertRaisesRegex(SceneError, 'Output directory'):
            create_gallery(SUITE, self.selection, self.src, self.src / 'out')

    def test_cli_round_trip(self):
        self.select()
        self.assertEqual(run(['acceptance-gallery', str(SUITE), '--selection', str(self.selection), '--images', str(self.src), '--out-dir', str(self.out)]), 0)
        self.assertEqual(run(['acceptance-verify', str(self.out / 'manifest.json')]), 0)


if __name__ == '__main__':
    unittest.main()

class StateCarryForwardTests(unittest.TestCase):
    def test_prior_fact_applies_even_when_only_later_scene_selected(self):
        from ucscene.core import build_plan, load_json
        fixture = SUITE.parent / 'cases/godot-mob-scene.json'
        case = load_json(fixture)
        planned = build_plan(case, ['03-gravity'])
        self.assertEqual(len(planned['scenes']), 1)
        p = planned['scenes'][0]['prompt']
        self.assertIn('RigidBody2D', p)
        self.assertIn('CharacterBody2D', p)
        self.assertIn('VisibleOnScreenNotifier2D', p)
        self.assertEqual(len(planned['scenes'][0]['persistent_facts']), 2)

    def test_prior_fact_cannot_be_injected_as_physical_camera(self):
        from ucscene.core import validate_use_case, load_json
        fixture = SUITE.parent / 'cases/godot-mob-scene.json'
        case = load_json(fixture)
        case['steps'][0]['carry_forward'] = ['显示器边框必须可见']
        with self.assertRaises(SceneError):
            validate_use_case(case)
