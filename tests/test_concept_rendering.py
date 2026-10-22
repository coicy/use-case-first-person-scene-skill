"""WP-04: real image bytes, explicit paid opt-in, concept-only provenance."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.provider import ProviderError
from ucscene.design.planner import create_design_plan
from ucscene.design.system import create_design_system
from ucscene.design.continuity import apply_design_system
from ucscene.rendering import (make_render_packet, verify_render_packet,
    render_concepts, verify_generation_report, build_concept_gallery, verify_concept_gallery)

ROOT=Path(__file__).resolve().parents[1]


def tiny_png(path):
    from PIL import Image
    Image.new('RGB',(256,144),(22,43,59)).save(path)


class WP04ConceptRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=load_json(ROOT/'benchmarks/new-products/new-asset-studio.wp02.brief.json')
        cls.plan=create_design_plan(cls.brief,variants=2)

    def test_single_frame_contract_on_every_request(self):
        from ucscene.rendering.concept import SINGLE_FRAME_PREFIX, SINGLE_FRAME_SUFFIX
        for mode, variant in [('explore', None), ('draft', 'VAR-01')]:
            kwargs = {'variant_id': variant} if variant else {}
            packet = make_render_packet(self.plan, mode=mode, **kwargs)
            for item in packet['items']:
                self.assertTrue(item['prompt'].startswith(SINGLE_FRAME_PREFIX))
                self.assertTrue(item['prompt'].endswith(SINGLE_FRAME_SUFFIX))
                self.assertIn('NO montage', item['prompt'])
                self.assertIn('ONE USE-CASE STEP', item['prompt'])
                self.assertEqual(item['prompt_sha256'],__import__('hashlib').sha256(item['prompt'].encode()).hexdigest())
        tampered = deepcopy(make_render_packet(self.plan, mode='draft', variant_id='VAR-01'))
        tampered['items'][0]['prompt'] = tampered['items'][0]['prompt'].replace('NO montage','MAKE montage')
        tampered['items'][0]['prompt_sha256'] = __import__('hashlib').sha256(tampered['items'][0]['prompt'].encode()).hexdigest()
        tampered['packet_sha256'] = __import__('ucscene.design.planner', fromlist=['_json_hash'])._json_hash({k:v for k,v in tampered.items() if k!='packet_sha256'})
        with self.assertRaisesRegex(SceneError,'Single-frame'):
            verify_render_packet(tampered)

    def test_modes_and_provenance(self):
        explore=make_render_packet(self.plan,mode='explore')
        self.assertEqual(len(explore['items']),6)
        self.assertEqual(len({(x['variant_id'],x['scene_id']) for x in explore['items']}),6)
        self.assertEqual(explore['design_authority'],'proposal-unapproved')
        self.assertEqual(verify_render_packet(explore),explore)
        draft=make_render_packet(self.plan,mode='draft',variant_id='VAR-02')
        self.assertEqual(len(draft['items']),3)
        self.assertEqual(draft['items'][0]['variant_id'],'VAR-02')
        revised=make_render_packet(self.plan,mode='revise',variant_id='VAR-01',change_request='Improve contrast in asset previews')
        self.assertIn('TARGETED REVISION REQUEST',revised['items'][0]['prompt'])
        self.assertNotEqual(revised['items'][0]['prompt_sha256'],make_render_packet(self.plan,mode='draft',variant_id='VAR-01')['items'][0]['prompt_sha256'])
        self.assertNotEqual(revised['packet_sha256'],draft['packet_sha256'])

    def test_consistent_mode_preserves_approved_baseline(self):
        system=create_design_system(self.plan,'VAR-02',evidence_ref='CI-SYNTHETIC-APPROVAL',locked=True)
        consistent=apply_design_system(system,self.brief)
        packet=make_render_packet(consistent,mode='consistent',system=system,brief=self.brief)
        self.assertEqual(packet['design_system_sha256'],system['digest_sha256'])
        self.assertEqual(packet['design_system_revision'],1)
        self.assertTrue(all(x['variant_id']=='APPROVED-VAR-02' for x in packet['items']))
        with self.assertRaisesRegex(SceneError,'cannot select new'):make_render_packet(consistent,mode='consistent',system=system,brief=self.brief,variant_id='VAR-01')
        with self.assertRaises(SceneError):make_render_packet(consistent,mode='consistent',system=system,brief=self.brief,change_request='Change locked nav')
        with self.assertRaises(SceneError):make_render_packet(consistent,mode='draft',variant_id='VAR-01')

    def test_invalid_mode_and_user_intent(self):
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='explore',variant_id='VAR-01')
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='draft')
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='revise',variant_id='VAR-01')
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='draft',variant_id='VAR-01',change_request='bad')
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='draft',variant_id='VAR-01',step_ids=['BAD'])
        with self.assertRaises(SceneError):make_render_packet(self.plan,mode='draft',variant_id='VAR-01',step_ids=['STEP-001','STEP-001'])

    def test_digest_and_source_tamper(self):
        pack=make_render_packet(self.plan,mode='draft',variant_id='VAR-01')
        x=deepcopy(pack);x['items'][0]['prompt']+=' fake'
        with self.assertRaisesRegex(SceneError,'prompt digest'):verify_render_packet(x)
        x=deepcopy(pack);x['items'][0]['prompt_sha256']='0'*64
        with self.assertRaises(SceneError):verify_render_packet(x)
        x=deepcopy(pack);x['items'][0]['required_ui_text']=[]
        with self.assertRaisesRegex(SceneError,'integrity'):verify_render_packet(x)

    def test_preflight_dry_run_no_provider_calls(self):
        pack=make_render_packet(self.plan,mode='draft',variant_id='VAR-01')
        with TemporaryDirectory() as tmp:
            with patch('ucscene.rendering.concept.generate_openai_image',side_effect=AssertionError('paid call')):
                report=render_concepts(pack,tmp)
            self.assertEqual(report['status'],'pending')
            self.assertTrue(all(x['status']=='not_generated' for x in report['images']))
            self.assertEqual(verify_generation_report(pack,report,tmp)['image_integrity_verified'],0)
            self.assertTrue((Path(tmp)/'generation-report.json').is_file())

    def test_execute_requires_cap_and_api_key(self):
        pack=make_render_packet(self.plan,mode='explore')
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SceneError,'max-images'):render_concepts(pack,tmp,execute=True)
            with self.assertRaisesRegex(SceneError,'max-images'):render_concepts(pack,tmp,execute=True,max_images=5)
        one=make_render_packet(self.plan,mode='draft',variant_id='VAR-01',step_ids=['STEP-001'])
        with TemporaryDirectory() as tmp,patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            with self.assertRaisesRegex(ProviderError,'OPENAI_API_KEY'):render_concepts(one,tmp,execute=True,max_images=1)
            self.assertFalse((Path(tmp)/'generation-report.json').exists())

    def test_mocked_real_image_flow_hash_and_gallery(self):
        pack=make_render_packet(self.plan,mode='draft',variant_id='VAR-01')
        calls=[]
        def mock_generate(prompt,path,**opts):
            calls.append((prompt,opts))
            tiny_png(path)
            return {'path':path,'model':opts['model']}
        with TemporaryDirectory() as tmp:
            root=Path(tmp);images=root/'images'
            report=render_concepts(pack,images,execute=True,max_images=3,generate_fn=mock_generate)
            self.assertEqual(report['status'],'completed')
            self.assertEqual(len(calls),3)
            self.assertEqual(verify_generation_report(pack,report,images)['image_integrity_verified'],3)
            gallery=build_concept_gallery(pack,images,root/'gallery',generation_report=report)
            self.assertEqual(len(gallery['images']),3)
            self.assertTrue(all(x['prompt_matches_source'] is True for x in gallery['images']))
            self.assertEqual(verify_concept_gallery(root/'gallery/manifest.json')['image_integrity_verified'],3)
            self.assertIn('human-concept-review', (root/'gallery/index.html').read_text(encoding='utf-8'))
            (images/report['images'][0]['path']).write_bytes(b'broken')
            with self.assertRaises(SceneError):verify_generation_report(pack,report,images)

    def test_external_gallery_does_not_claim_cli_prompt(self):
        pack=make_render_packet(self.plan,mode='draft',variant_id='VAR-01',step_ids=['STEP-001'])
        item=pack['items'][0]
        with TemporaryDirectory() as tmp:
            root=Path(tmp);imgs=root/'imgs';imgs.mkdir()
            tiny_png(imgs/'external.png')
            pick={'samples':[{'variant_id':item['variant_id'],'scene_id':item['scene_id'],
                'image':'external.png','origin':'conversation-image-generation','notes':'cropped from illustration'}]}
            gallery=build_concept_gallery(pack,imgs,root/'gallery',selection=pick)
            self.assertEqual(gallery['images'][0]['prompt_matches_source'],'not_verified')
            self.assertIsNone(gallery['images'][0]['generation_prompt_sha256'])
            self.assertEqual(gallery['approval'],'pending-human-review')
            with self.assertRaisesRegex(SceneError,'cannot claim ucscene-cli'):
                pick['samples'][0]['origin']='ucscene-cli'
                build_concept_gallery(pack,imgs,root/'new',selection=pick)

    def test_external_gallery_rejects_path_traversal_and_forged_prompt(self):
        packet=make_render_packet(self.plan,mode='draft',variant_id='VAR-01',step_ids=['STEP-001']);item=packet['items'][0]
        with TemporaryDirectory() as tmp:
            p=Path(tmp);tiny_png(p/'outside.png');(p/'assets').mkdir()
            base={'variant_id':item['variant_id'],'scene_id':item['scene_id'],
                'origin':'external-image-model','image':'../outside.png'}
            with self.assertRaisesRegex(SceneError,'outside image root'):
                build_concept_gallery(packet,p/'assets',p/'gallery',selection={'samples':[base]})
            base['image']='exists.png';tiny_png(p/'assets/exists.png')
            base['generation_prompt_sha256']=item['prompt_sha256']
            with self.assertRaisesRegex(SceneError,'cannot be asserted'):
                build_concept_gallery(packet,p/'assets',p/'gallery',selection={'samples':[base]})

    def test_cli_offline_smoke_and_dry_run(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'plan.json';source.write_text(json.dumps(self.plan,ensure_ascii=False),encoding='utf-8')
            packet=p/'packet.json'
            self.assertEqual(run(['concept-packet',str(source),'--mode','explore','--step','STEP-001','--out',str(packet)]),0)
            self.assertEqual(len(load_json(packet)['items']),2)
            reportdir=p/'prepared'
            self.assertEqual(run(['concept-render',str(packet),'--out',str(reportdir)]),0)
            report=load_json(reportdir/'generation-report.json')
            self.assertEqual(report['status'],'pending')
            self.assertEqual(run(['concept-render',str(packet),'--execute','--out',str(p/'failed')]),2)

    def test_chain_and_reference_conflicts(self):
        pack=make_render_packet(self.plan,mode='explore')
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(SceneError,'mix competing'):render_concepts(pack,tmp,chain=True)
        draft=make_render_packet(self.plan,mode='draft',variant_id='VAR-01')
        with TemporaryDirectory() as tmp:
            p=Path(tmp);tiny_png(p/'ref.png')
            with self.assertRaisesRegex(SceneError,'Choose chain'):render_concepts(draft,p/'out',reference_image=p/'ref.png',chain=True)

if __name__=='__main__':unittest.main()
