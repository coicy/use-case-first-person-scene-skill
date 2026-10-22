"""Offline smoke and regression tests for real-project documentation benchmarks."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ucscene.benchmark import (
    _read_audit, export_benchmark_plans, make_prompt_lock, run_benchmark,
    verify_prompt_lock,
)
from ucscene.cli import run
from ucscene.core import SceneError, build_plan, load_json, save_json, validate_use_case

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'benchmarks' / 'famous-projects' / 'suite.json'
LOCK = ROOT / 'benchmarks' / 'famous-projects' / 'prompt-lock.json'

class TestOfficialBenchmarks(unittest.TestCase):
    def test_golden_suite_all_cases_and_counts(self):
        report = run_benchmark(SUITE)
        self.assertEqual(report['cases'], 6)
        self.assertEqual(report['planned_scenes'], 18)
        self.assertEqual(report['checked_visible_evidence'], 36)
        self.assertTrue(report['static_pass'])
        self.assertEqual(report['visual_evaluation']['status'], 'not_evaluated')
        verify_prompt_lock(report, LOCK)
        self.assertEqual(make_prompt_lock(report), load_json(LOCK))

    def test_physical_game_does_not_invent_first_person_game_world(self):
        case = load_json(SUITE.parent / 'cases' / 'openttd-rail.json')
        p = build_plan(case)
        for scene in p['scenes']:
            self.assertIn('POV MODE: physical-user', scene['prompt'])
            self.assertIn('isometric/top-down/2D', scene['prompt'])
            self.assertIn('OpenTTD', scene['prompt'])
        self.assertEqual(p['anchor']['viewpoint_mode'], 'physical-user')

    def test_avatar_game_has_no_external_monitor(self):
        case = load_json(SUITE.parent / 'cases' / 'luanti-mining.json')
        p = build_plan(case)
        for scene in p['scenes']:
            self.assertIn('POV MODE: avatar-eyes', scene['prompt'])
            self.assertIn('No monitor', scene['prompt'])
        self.assertEqual(p['anchor']['viewpoint_mode'], 'avatar-eyes')

    def test_legacy_use_cases_keep_physical_viewpoint(self):
        case = load_json(ROOT / 'examples' / 'warehouse-scan.json')
        self.assertEqual(build_plan(case)['anchor']['viewpoint_mode'], 'physical-user')

    def test_reject_unknown_viewpoint(self):
        case = load_json(SUITE.parent / 'cases' / 'openttd-rail.json')
        case['viewpoint_mode'] = 'magic-flying-camera'
        with self.assertRaises(SceneError):
            validate_use_case(case)

    def test_reject_physical_monitor_with_avatar_eye_mode(self):
        case = load_json(SUITE.parent / 'cases' / 'luanti-mining.json')
        case['device'] = 'computer monitor'
        with self.assertRaises(SceneError):
            validate_use_case(case)

    def test_export_plans_and_cli(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'plans'
            self.assertEqual(run(['benchmark-export', str(SUITE), '--out-dir', str(out)]), 0)
            index = load_json(out / 'index.json')
            self.assertEqual(len(index['plans']), 6)
            self.assertEqual(len(load_json(out / 'BENCH-VSCODE-DEBUG.json')['scenes']), 3)
            self.assertEqual(run(['review', str(out / 'BENCH-LUANTI-MINE.json')]), 0)

    def test_report_and_lock_cli(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'report.json'
            lock = Path(tmp) / 'golden.json'
            self.assertEqual(run(['benchmark-lock', str(SUITE), '--out', str(lock)]), 0)
            self.assertEqual(run(['benchmark', str(SUITE), '--lock', str(lock), '--out', str(out)]), 0)
            self.assertTrue(load_json(out)['static_pass'])

    def test_lock_detects_unreviewed_change(self):
        report = run_benchmark(SUITE)
        with TemporaryDirectory() as tmp:
            lock = Path(tmp) / 'lock.json'
            bad = make_prompt_lock(report)
            bad['cases']['BENCH-OPENTTD-RAIL']['prompt_sha256']['01-toolbar'] = '0'*64
            save_json(lock, bad)
            with self.assertRaisesRegex(SceneError, 'lock mismatch'):
                verify_prompt_lock(report, lock)

    def _minimal_suite(self, tmp: Path):
        suite = load_json(SUITE)
        suite['cases'] = [suite['cases'][0]]
        case = load_json(SUITE.parent / suite['cases'][0]['file'])
        cases = tmp / 'cases'
        cases.mkdir()
        save_json(cases / 'case.json', case)
        suite['cases'][0]['file'] = 'cases/case.json'
        save_json(tmp / 'suite.json', suite)
        return tmp / 'suite.json', cases / 'case.json'

    def test_source_traceability_rejects_missing_ref(self):
        with TemporaryDirectory() as temp:
            path = Path(temp)
            suite, file = self._minimal_suite(path)
            case = load_json(file)
            case['steps'][1]['source_refs'] = ['FAKE-OFFICIAL-URL']
            save_json(file, case)
            with self.assertRaisesRegex(SceneError, 'Untraceable source_refs'):
                run_benchmark(suite)

    def test_manifest_case_path_cannot_escape_suite(self):
        with TemporaryDirectory() as temp:
            path = Path(temp)
            suite, file = self._minimal_suite(path)
            data = load_json(suite)
            data['cases'][0]['file'] = '../escape.json'
            save_json(suite, data)
            with self.assertRaisesRegex(SceneError, 'escapes benchmark root'):
                run_benchmark(suite)

    def test_mismatched_camera_fails_even_if_use_case_valid(self):
        with TemporaryDirectory() as temp:
            suite, file = self._minimal_suite(Path(temp))
            case = load_json(file)
            case['viewpoint_mode'] = 'avatar-eyes'
            case['device'] = 'gameplay viewport'
            save_json(file, case)
            with self.assertRaisesRegex(SceneError, 'camera does not match'):
                run_benchmark(suite)

    def test_audit_requires_paired_images_and_reports_missing(self):
        with TemporaryDirectory() as temp:
            suite, _ = self._minimal_suite(Path(temp))
            with self.assertRaisesRegex(SceneError, 'together'):
                run_benchmark(suite, audits=Path(temp))
            (Path(temp) / 'audits').mkdir()
            (Path(temp) / 'images').mkdir()
            report = run_benchmark(suite, audits=Path(temp)/'audits', images=Path(temp)/'images')
            self.assertEqual(report['visual_evaluation']['missing_image_audits'], 3)
            self.assertEqual(report['visual_evaluation']['status'], 'incomplete')

    def test_audit_image_and_prompt_must_match(self):
        with TemporaryDirectory() as temp:
            suite, file = self._minimal_suite(Path(temp))
            p = build_plan(load_json(file))
            s = p['scenes'][0]
            audit_dir = Path(temp)/'audits'
            image_dir = Path(temp)/'images'
            audit_dir.mkdir(); image_dir.mkdir()
            image = image_dir / (s['id']+'.png')
            # Benchmark intentionally checks byte integrity without decoding pixels.
            image.write_bytes(b'fixture-bytes-only')
            audit = {'scene_id': s['id'], 'method': 'model-vision-advisory',
                     'passed': True, 'prompt_sha256': s['prompt_sha256'],
                     'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest()}
            save_json(audit_dir/(s['id']+'.json'), audit)
            report = run_benchmark(suite, audits=audit_dir, images=image_dir)
            self.assertEqual(report['visual_evaluation']['model_audit_passed'], 1)
            self.assertEqual(report['visual_evaluation']['missing_image_audits'], 2)
            image.write_bytes(b'tampered')
            with self.assertRaisesRegex(SceneError, 'image hash mismatch'):
                run_benchmark(suite, audits=audit_dir, images=image_dir)
            image.write_bytes(b'fixture-bytes-only')
            audit['prompt_sha256'] = '1'*64
            save_json(audit_dir/(s['id']+'.json'), audit)
            with self.assertRaisesRegex(SceneError, 'prompt hash mismatch'):
                run_benchmark(suite, audits=audit_dir, images=image_dir)

    def test_unexpected_audit_file_rejected(self):
        with TemporaryDirectory() as temp:
            suite, _ = self._minimal_suite(Path(temp))
            audits = Path(temp) / 'audits'
            audits.mkdir()
            (Path(temp)/'images').mkdir()
            save_json(audits/'unrelated.json', {'passed': True})
            with self.assertRaisesRegex(SceneError, 'Unexpected audit'):
                run_benchmark(suite, audits=audits, images=Path(temp)/'images')

if __name__ == '__main__':
    unittest.main()
