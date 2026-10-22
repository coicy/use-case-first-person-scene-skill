"""Mocked vision output verifies contract; never calls a real paid model."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucscene.core import SceneError, load_json
from ucscene.design.planner import create_design_plan
from ucscene.provider import ProviderError
from ucscene.rendering.concept import make_render_packet
from ucscene.rendering.audit import audit_concept_image

ROOT=Path(__file__).resolve().parents[1]

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=load_json(ROOT/'benchmarks/new-products/new-asset-studio.wp02.brief.json')
        cls.packet=make_render_packet(create_design_plan(cls.brief,variants=2),mode='draft',variant_id='VAR-01',step_ids=['STEP-001'])
        cls.item=cls.packet['items'][0]

    def _review(self, composition='single-frame', count=1, chrome=False, software='pass'):
        return {'composition':composition,'software_only':software,'distinct_screens':count,
                'external_presentation_chrome':chrome,'composition_reason':'looked at panel edges',
                'software_only_reason':'only UI','step_evidence':[
                    {'requirement':e,'status':'pass','reason':'visible'} for e in self.item['required_evidence']],
                'recommended_fixes':[]}

    def _run(self, result):
        with TemporaryDirectory() as tmp:
            file=Path(tmp)/'image.png'
            from PIL import Image
            Image.new('RGB',(256,144)).save(file)
            return audit_concept_image(self.packet,file,variant_id='VAR-01',scene_id=self.item['scene_id'],review_fn=lambda *args,**kwargs:result)

    def test_one_full_bleed_ui_is_advisory_only(self):
        report=self._run(self._review())
        self.assertEqual(report['visual_gate'],'advisory-pass')
        self.assertEqual(report['human_design_approval'],'not_checked')
        self.assertEqual(len(report['image_sha256']),64)

    def test_collage_is_not_approved(self):
        report=self._run(self._review('multi-frame-board',6,True))
        self.assertEqual(report['visual_gate'],'needs-human-review')

    def test_uncertain_is_not_passed(self):
        report=self._run(self._review('uncertain'))
        self.assertEqual(report['visual_gate'],'needs-human-review')

    def test_inconsistent_single_frame_rejected(self):
        with self.assertRaisesRegex(ProviderError,'Inconsistent'):
            self._run(self._review('single-frame',3,True))

    def test_wrong_evidence_is_rejected(self):
        review=self._review()
        review['step_evidence']=[{'requirement':'fabricated','status':'pass','reason':''}]
        with self.assertRaises(ProviderError):self._run(review)

    def test_unknown_scene_rejected_before_vision(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SceneError,'unique existing'):
                audit_concept_image(self.packet,Path(tmp)/'none.png',variant_id='VAR-01',scene_id='nonexistent',review_fn=lambda *_a,**_k:None)

    def test_no_api_key_is_not_a_false_pass(self):
        with TemporaryDirectory() as tmp,patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            from PIL import Image
            pic=Path(tmp)/'image.png';Image.new('RGB',(256,144)).save(pic)
            with self.assertRaisesRegex(ProviderError,'OPENAI_API_KEY'):
                audit_concept_image(self.packet,pic,variant_id='VAR-01',scene_id=self.item['scene_id'])

if __name__=='__main__':unittest.main()
