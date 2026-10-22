"""Human visual benchmark: only verified real image bytes enter scores."""
from __future__ import annotations
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from ucscene.benchmark_human import MODES, rating_template, score_human_packet
from ucscene.cli import run
from ucscene.core import SceneError, load_json, save_json

SUITE = Path(__file__).resolve().parents[1] / 'benchmarks/famous-projects/suite.json'

class HumanRatingTests(unittest.TestCase):
    def test_empty_template_does_not_fabricate_scores(self):
        data = rating_template(SUITE)
        self.assertEqual(len(data['ratings']), 54)
        self.assertEqual(len({x['scene_id'] for x in data['ratings']}), 18)
        self.assertEqual({x['mode'] for x in data['ratings']}, set(MODES))
        with TemporaryDirectory() as temp:
            save_json(Path(temp) / 'packet.json', data)
            result = score_human_packet(SUITE, Path(temp)/'packet.json', temp)
            self.assertEqual(result['scored_reviews'], 0)
            self.assertFalse(result['coverage_complete'])
            self.assertFalse(result['comparison_ready'])
            self.assertTrue(all(x['strict_pass_rate'] is None for x in result['per_mode'].values()))

    def create_real_sample(self, folder: Path, mode: str, row: dict, *, score: int = 2) -> None:
        file = folder / mode / (row['scene_id'] + '.png')
        file.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (40, 40), (42, 66, 89)).save(file)
        row['rater_id'] = 'human-test'
        row['image_sha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        row['ratings'] = {'point_of_view': score, 'visible_evidence': score, 'app_fidelity': score, 'continuity': score}
        row['unsupported_product_features'] = False

    def test_actual_image_required_and_hash_bound(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            data = rating_template(SUITE)
            row = data['ratings'][0]
            self.create_real_sample(base, row['mode'], row)
            file = base / 'scores.json'
            save_json(file, data)
            result = score_human_packet(SUITE, file, base)
            self.assertEqual(result['scored_reviews'], 1)
            self.assertEqual(result['per_mode']['prompt-only']['strict_passes'], 1)
            self.assertEqual(result['per_mode']['prompt-only']['missing_from_single_rater_baseline'], 17)
            source = base / row['image_path']
            Image.new('RGB', (40,40), (255, 1, 2)).save(source)
            with self.assertRaisesRegex(SceneError, 'digest mismatch'):
                score_human_packet(SUITE, file, base)

    def test_unknown_scene_and_duplicate_rater_rejected(self):
        with TemporaryDirectory() as temp:
            base=Path(temp)
            data=rating_template(SUITE)
            row=data['ratings'][0]
            self.create_real_sample(base,row['mode'],row)
            data['ratings'].append(row.copy())
            file=base/'scores.json'
            save_json(file,data)
            with self.assertRaisesRegex(SceneError,'Duplicate rater'):
                score_human_packet(SUITE,file,base)
            data['ratings'][-1]['scene_id']='unregistered'
            save_json(file,data)
            with self.assertRaisesRegex(SceneError,'Unknown or invalid scene'):
                score_human_packet(SUITE,file,base)

    def test_partial_or_uncertain_is_not_strict_pass(self):
        with TemporaryDirectory() as temp:
            base=Path(temp)
            data=rating_template(SUITE)
            row=data['ratings'][0]
            self.create_real_sample(base,row['mode'],row,score=1)
            file=base/'scores.json';save_json(file,data)
            result=score_human_packet(SUITE,file,base)
            self.assertEqual(result['per_mode'][row['mode']]['strict_pass_rate'],0)

    def test_pairing_uses_identical_scene_and_rater(self):
        with TemporaryDirectory() as temp:
            base=Path(temp)
            data=rating_template(SUITE)
            rows=data['ratings'][:3]
            for row in rows:self.create_real_sample(base,row['mode'],row)
            rows[1]['ratings']['app_fidelity']=0
            file=base/'scores.json';save_json(file,data)
            result=score_human_packet(SUITE,file,base)
            self.assertEqual(result['fully_paired_scene_rater_groups'],1)
            self.assertEqual(result['paired_strict_passes'],{'prompt-only':1,'fixed-reference':0,'sequential-chain':1})
            self.assertFalse(result['comparison_ready'])

    def test_multiple_reviewers_still_allow_complete_comparison(self):
        """Extra paired raters must not turn a complete comparison into incomplete."""
        with TemporaryDirectory() as temp:
            base = Path(temp)
            data = rating_template(SUITE)
            for row in data['ratings']:
                self.create_real_sample(base, row['mode'], row)
            additional = []
            for row in data['ratings'][:3]:
                clone = dict(row)
                clone['rater_id'] = 'independent-reviewer-2'
                additional.append(clone)
            data['ratings'].extend(additional)
            packet = base / 'scores.json'
            save_json(packet, data)
            result = score_human_packet(SUITE, packet, base)
            self.assertEqual(result['fully_paired_scene_rater_groups'], 19)
            self.assertTrue(result['comparison_ready'])
            self.assertTrue(result['coverage_complete'])
            self.assertEqual(result['scored_reviews'], 57)

    def test_reject_forged_claim_with_no_real_image(self):
        with TemporaryDirectory() as temp:
            base=Path(temp);data=rating_template(SUITE);row=data['ratings'][0]
            row.update({'rater_id':'fake','image_sha256':'0'*64,'unsupported_product_features':False})
            row['ratings']={key:2 for key in row['ratings']}
            file=base/'scores.json';save_json(file,data)
            with self.assertRaises(FileNotFoundError):
                score_human_packet(SUITE,file,base)

    def test_cli_template_and_empty_report(self):
        with TemporaryDirectory() as temp:
            base=Path(temp);packet=base/'ratings.json';result=base/'score.json'
            self.assertEqual(run(['benchmark-rating-template',str(SUITE),'--out',str(packet)]),0)
            self.assertEqual(run(['benchmark-score',str(SUITE),'--packet',str(packet),'--images',str(base),'--out',str(result)]),0)
            self.assertIsNone(load_json(result)['per_mode']['prompt-only']['strict_pass_rate'])

if __name__ == '__main__':
    unittest.main()
