"""Host Agent native image handoff never requires a standalone API key."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from PIL import Image
from ucscene.core import SceneError, load_json
from ucscene.design.planner import create_design_plan
from ucscene.rendering.concept import make_render_packet
from ucscene.rendering.agent import export_agent_handoff, verify_agent_handoff, import_agent_images, verify_agent_import
from ucscene.rendering.gallery import build_concept_gallery, verify_concept_gallery

ROOT=Path(__file__).resolve().parents[1]
class TestHostAgentNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        brief=load_json(ROOT/'benchmarks/new-products/new-asset-studio.wp02.brief.json')
        game=load_json(ROOT/'benchmarks/new-products/new-hamlet-builder.wp02.brief.json')
        cls.asset=make_render_packet(create_design_plan(brief,variants=2),mode='draft',variant_id='VAR-01')
        cls.game=make_render_packet(create_design_plan(game,variants=2),mode='draft',variant_id='VAR-01')
    def prepare(self,root):
        manifest=export_agent_handoff(self.asset,root/'tasks')
        (root/'images').mkdir()
        Image.new('RGB',(256,144)).save(root/'images/image.png')
        source=self.asset['items'][0]
        (root/'results.json').write_text(json.dumps({'images':[{
            'variant_id':source['variant_id'],'scene_id':source['scene_id'],
            'file':'image.png','tool':'native-agent-image-generator'}]}),encoding='utf-8')
        return root/'tasks/manifest.json'
    def test_keyless_export_per_step(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            manifest=verify_agent_handoff(self.asset,path)
            self.assertEqual(len(manifest['tasks']),3)
            for item,task in zip(self.asset['items'],manifest['tasks']):
                self.assertEqual((root/'tasks'/task['prompt_file']).read_text(),item['prompt'])
    def test_cross_product_handoff_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            with self.assertRaises(SceneError):verify_agent_handoff(self.game,path)
    def test_actual_png_import_and_gallery(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            result=import_agent_images(self.asset,path,root/'results.json',root/'images',root/'received')
            self.assertEqual(result['images'][0]['prompt_provenance'],'not_verified')
            self.assertEqual(verify_agent_import(self.asset,path,root/'received/manifest.json')['images_verified'],1)
            gallery=build_concept_gallery(self.asset,root/'received/images',root/'gallery',
                selection=load_json(root/'received/gallery-selection.json'))
            self.assertEqual(gallery['images'][0]['human_verdict'],'pending')
            verify_concept_gallery(root/'gallery/manifest.json')
    def test_tampered_prompt_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            task=load_json(path)['tasks'][0]
            (root/'tasks'/task['prompt_file']).write_text('wrong product')
            with self.assertRaises(SceneError):verify_agent_handoff(self.asset,path)
    def test_wrong_scene_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            m=load_json(root/'results.json');m['images'][0]['scene_id']='wrong-scene'
            (root/'results.json').write_text(json.dumps(m))
            with self.assertRaises(SceneError):import_agent_images(self.asset,path,root/'results.json',root/'images',root/'received')
    def test_changed_png_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp);path=self.prepare(root)
            import_agent_images(self.asset,path,root/'results.json',root/'images',root/'received')
            Image.new('RGB',(256,144),'red').save(root/'received/images/image-001.png')
            with self.assertRaises(SceneError):verify_agent_import(self.asset,path,root/'received/manifest.json')
if __name__=='__main__':unittest.main()
