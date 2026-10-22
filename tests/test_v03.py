"""Offline regression tests for verified visual anchors and perspective UI overlay."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucscene.anchors import create_anchor, verify_anchor
from ucscene.cli import run
from ucscene.composite import compose_ui, compose_batch, load_quad
from ucscene.core import SceneError, build_plan, load_json, save_json
from ucscene.imaging import inspect_image

ROOT = Path(__file__).resolve().parents[1]

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None


@unittest.skipUnless(Image is not None, 'Install the [ui] extra to run v0.3 image tests')
class ImageOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = build_plan(load_json(ROOT / 'examples' / 'warehouse-scan.json'))
        self.plan_path = self.root / 'plan.json'
        save_json(self.plan_path, self.plan)
        self.scene = self.root / 'scene.png'
        self.ui = self.root / 'ui.png'
        Image.new('RGB', (400, 240), (25, 40, 60)).save(self.scene)
        Image.new('RGB', (180, 120), (245, 230, 20)).save(self.ui)
        self.quad = self.root / 'quad.json'
        save_json(self.quad, {'coordinate_system': 'normalized', 'points': [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]})

    def test_anchor_manifest_verifies_digest_and_case(self):
        m = self.root / 'assets' / 'anchor.json'
        asset = create_anchor(self.plan, self.scene, m, approved=True, note='human-verified warehouse')
        verified, path = verify_anchor(m, plan=self.plan, require_approved=True)
        self.assertEqual(path, self.scene.resolve())
        self.assertEqual(verified['reference_sha256'], asset['reference_sha256'])
        self.assertFalse(Path(asset['reference_image']).is_absolute())

    def test_anchor_requires_operator_approval(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m)
        with self.assertRaisesRegex(SceneError, 'explicitly approved'):
            verify_anchor(m, plan=self.plan, require_approved=True)
        self.assertFalse(verify_anchor(m)[0]['approved_by_operator'])

    def test_anchor_mutation_rejected(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m, approved=True)
        Image.new('RGB', (400, 240), (25, 42, 60)).save(self.scene)
        with self.assertRaisesRegex(SceneError, 'hash mismatch'):
            verify_anchor(m)

    def test_anchor_plan_mismatch_rejected(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m, approved=True)
        modified = dict(self.plan, anchor=dict(self.plan['anchor'], device='new device'))
        with self.assertRaisesRegex(SceneError, 'Scene anchor changed'):
            verify_anchor(m, plan=modified)

    def test_anchor_wrong_case_rejected(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m, approved=True)
        modified = dict(self.plan, use_case_id='ANOTHER-CASE')
        with self.assertRaisesRegex(SceneError, 'different use case'):
            verify_anchor(m, plan=modified)

    def test_anchor_manifest_cannot_overwrite_image(self):
        with self.assertRaisesRegex(SceneError, 'must not overwrite'):
            create_anchor(self.plan, self.scene, self.scene)
        inspect_image(self.scene)

    def test_anchor_rejects_nonimage_input(self):
        src = self.root / 'not-an-image.png'
        src.write_text('not png', encoding='utf-8')
        with self.assertRaises(SceneError):
            create_anchor(self.plan, src, self.root / 'anchor.json')

    def test_compat_generate_preflights_anchor_before_any_network(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m, approved=False)
        with patch('ucscene.cli.edit_openai_image') as edit, patch('ucscene.cli.generate_openai_image') as generate:
            self.assertEqual(run(['generate', str(self.plan_path), '--anchor', str(m), '--out', str(self.root / 'out')]), 2)
            edit.assert_not_called()
            generate.assert_not_called()

    def test_generate_uses_single_manifest_reference_across_steps(self):
        m = self.root / 'anchor.json'
        create_anchor(self.plan, self.scene, m, approved=True)
        out = self.root / 'out'
        with patch('ucscene.cli.edit_openai_image', side_effect=lambda prompt, ref, path, **kwargs: {'path': str(path), 'reference_image': str(ref), 'bytes': 42}) as edit, patch('ucscene.cli.generate_openai_image') as generate:
            self.assertEqual(run(['generate', str(self.plan_path), '--anchor', str(m), '--out', str(out)]), 0)
            self.assertEqual(edit.call_count, len(self.plan['scenes']))
            self.assertEqual({call.args[1] for call in edit.call_args_list}, {str(self.scene.resolve())})
            generate.assert_not_called()
        report = load_json(out / 'generation-report.json')
        self.assertEqual(report['continuity_mode'], 'verified-manifest-anchor')
        self.assertEqual(report['anchor_reference_sha256'], inspect_image(self.scene)['sha256'])

    def test_composite_rectangle_is_actual_source_image(self):
        output = self.root / 'composed.png'
        report = compose_ui(self.scene, self.ui, self.quad, output)
        self.assertEqual(report['method'], 'offline-perspective-overlay')
        self.assertEqual(report['ui_sha256'], inspect_image(self.ui)['sha256'])
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((200, 120)), (245, 230, 20))
            self.assertEqual(image.getpixel((5, 5)), (25, 40, 60))
            self.assertEqual(image.getpixel((399, 239)), (25, 40, 60))

    def test_composite_output_does_not_clobber_input(self):
        original = self.scene.read_bytes()
        with self.assertRaisesRegex(SceneError, 'must not overwrite'):
            compose_ui(self.scene, self.ui, self.quad, self.scene)
        self.assertEqual(self.scene.read_bytes(), original)

    def test_composite_skewed_quad(self):
        save_json(self.quad, {'coordinate_system': 'normalized', 'points': [[0.25, 0.12], [0.72, 0.25], [0.8, 0.9], [0.12, 0.78]]})
        output = self.root / 'skewed.png'
        compose_ui(self.scene, self.ui, self.quad, output)
        with Image.open(output) as image:
            center = image.getpixel((192, 120))
            self.assertEqual(center, (245, 230, 20))
            self.assertEqual(image.getpixel((390, 20)), (25, 40, 60))

    def test_composite_transparent_ui_keeps_background(self):
        ui = Image.new('RGBA', (180, 120), (245, 230, 20, 255))
        ImageDraw.Draw(ui).rectangle((60, 40, 120, 80), fill=(0, 0, 0, 0))
        ui.save(self.ui)
        output = self.root / 'alpha.png'
        compose_ui(self.scene, self.ui, self.quad, output)
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((200, 120)), (25, 40, 60))

    def test_composite_cli_and_report(self):
        target = self.root / 'out.png'
        report = self.root / 'report.json'
        self.assertEqual(run(['compose-ui', '--scene', str(self.scene), '--ui', str(self.ui), '--quad', str(self.quad), '--out', str(target), '--report', str(report)]), 0)
        self.assertEqual(load_json(report)['output_sha256'], inspect_image(target)['sha256'])

    def test_invalid_quad_rejected(self):
        for points in [
            [[0.1, 0.1], [0.9, 0.9], [0.9, 0.1], [0.1, 0.9]], # bow tie
            [[0.1, 0.1], [0.8, 0.1], [0.8, 0.1], [0.1, 0.8]], # degenerate
            [[-0.1, 0.1], [0.8, 0.1], [0.8, 0.8], [0.1, 0.8]], # out of range
            [[0.1, 0.1], [0.8, 0.1], [0.8, 0.8]], # missing corner
        ]:
            save_json(self.quad, {'coordinate_system': 'normalized', 'points': points})
            with self.subTest(points=points), self.assertRaises(SceneError):
                load_quad(self.quad)

    def test_invalid_quads_do_not_create_output(self):
        save_json(self.quad, {'coordinate_system': 'normalized', 'points': [[0.1, 0.1]]*4})
        output = self.root / 'out.png'
        with self.assertRaises(SceneError):
            compose_ui(self.scene, self.ui, self.quad, output)
        self.assertFalse(output.exists())

    def test_compose_batch_one_mapped_step_and_manifest(self):
        images = self.root / 'generated'
        images.mkdir()
        (images / 'UC-WH-001--02-scan.png').write_bytes(self.scene.read_bytes())
        mapping = self.root / 'mapping.json'
        save_json(mapping, {'format_version': '1.0', 'screens': {'02-scan': {'ui': 'ui.png', 'quad': 'quad.json'}}})
        out = self.root / 'composited'
        report = compose_batch(self.plan, images, mapping, out)
        self.assertEqual(len(report['items']), 1)
        self.assertIn('03-fail', report['unmapped_step_ids'])
        self.assertTrue((out / 'UC-WH-001--02-scan-ui.png').is_file())
        self.assertTrue((out / 'composition-report.json').is_file())

    def test_compose_batch_invalid_mapping_does_not_partially_write(self):
        images = self.root / 'generated'
        images.mkdir()
        (images / 'UC-WH-001--02-scan.png').write_bytes(self.scene.read_bytes())
        mapping = self.root / 'mapping.json'
        save_json(mapping, {'format_version': '1.0', 'screens': {'02-scan': {'ui': 'ui.png', 'quad': 'quad.json'}, '03-fail': {'ui': 'missing.png', 'quad': 'quad.json'}}})
        out = self.root / 'composited'
        with self.assertRaises(FileNotFoundError):
            compose_batch(self.plan, images, mapping, out)
        self.assertFalse(out.exists())

    def test_compose_batch_rejects_unknown_steps(self):
        mapping = self.root / 'mapping.json'
        save_json(mapping, {'format_version': '1.0', 'screens': {'fake': {'ui': 'ui.png', 'quad': 'quad.json'}}})
        with self.assertRaisesRegex(SceneError, 'unknown step'):
            compose_batch(self.plan, self.root, mapping, self.root / 'newdir')

    def test_compose_batch_strict_missing_mapping(self):
        mapping = self.root / 'mapping.json'
        save_json(mapping, {'format_version': '1.0', 'screens': {'02-scan': {'ui': 'ui.png', 'quad': 'quad.json'}}})
        with self.assertRaisesRegex(SceneError, 'Missing UI screenshot'):
            compose_batch(self.plan, self.root, mapping, self.root / 'newdir', strict=True)

    def test_compose_batch_cli(self):
        images = self.root / 'generated'
        images.mkdir()
        (images / 'UC-WH-001--02-scan.png').write_bytes(self.scene.read_bytes())
        mapping = self.root / 'mapping.json'
        save_json(mapping, {'format_version': '1.0', 'screens': {'02-scan': {'ui': 'ui.png', 'quad': 'quad.json'}}})
        self.assertEqual(run(['compose-batch', str(self.plan_path), '--images', str(images), '--map', str(mapping), '--out', str(self.root / 'results')]), 0)
        self.assertTrue((self.root / 'results' / 'composition-report.json').exists())

    def test_anchor_cli_smoke(self):
        m = self.root / 'anchor.json'
        self.assertEqual(run(['anchor-create', str(self.plan_path), '--image', str(self.scene), '--out', str(m), '--approved']), 0)
        self.assertEqual(run(['anchor-verify', str(m), '--plan', str(self.plan_path), '--require-approved']), 0)


if __name__ == '__main__':
    unittest.main()
