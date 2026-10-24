"""WP-06: original product semantic scene-graph -> SVG, failure gates."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import xml.etree.ElementTree as ET

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.scenegraph import (compile_scene_graph, validate_scene_graph,
                                render_scene_graph, verify_scene_svgs)

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'benchmarks/new-products/scenegraph'

class SemanticSceneGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures={}
        for product in ('new-asset-studio','new-hamlet-builder'):
            plan=load_json(FIXTURES/(product+'.plan.json'))
            spec=load_json(FIXTURES/(product+'.spec.json'))
            cls.fixtures[product]=(plan,spec,compile_scene_graph(plan,spec))

    def test_json_schema(self):
        from jsonschema import Draft202012Validator
        schema=load_json(ROOT/'schemas/scene-graph.schema.json')
        Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema)
        for plan,spec,graph in self.fixtures.values():
            self.assertEqual(list(validator.iter_errors(graph)),[])

    def test_both_products_six_steps(self):
        for name,(plan,spec,graph) in self.fixtures.items():
            self.assertEqual(len(graph['scenes']),3)
            self.assertEqual(graph['product_id'],name)
            self.assertEqual(graph['authority'],'proposed')
            self.assertEqual(len(graph['graph_sha256']),64)
            self.assertIs(validate_scene_graph(graph,plan=plan),graph)

    def test_source_brief_and_design_binding(self):
        first=self.fixtures['new-asset-studio']
        other=self.fixtures['new-hamlet-builder']
        with self.assertRaisesRegex(SceneError,'product identity'):
            compile_scene_graph(first[0],other[1])
        broken=copy.deepcopy(first[1]);broken['layout']='unapproved random layout'
        with self.assertRaisesRegex(SceneError,'layout contradicts'):
            compile_scene_graph(first[0],broken)
        broken=copy.deepcopy(first[1]);broken['authority']='approved'
        with self.assertRaisesRegex(SceneError,'self-approve'):
            compile_scene_graph(first[0],broken)
        with self.assertRaisesRegex(SceneError,'different source plan'):
            validate_scene_graph(first[2],plan=other[0])

    def test_regions_cannot_drift(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        next(x for x in broken['regions'] if x['id']=='inspector')['rect'][0]-=10
        with self.assertRaisesRegex(SceneError,'overlap|topology'):
            compile_scene_graph(plan,broken)

    def test_data_binding_wrong_object_fails(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        next(x for x in broken['elements'] if x['id']=='workers')['binding']='object.warehouse-01.workers'
        with self.assertRaisesRegex(SceneError,'Bound element references an unknown object'):
            compile_scene_graph(plan,broken)

    def test_existing_but_wrong_object_binding_fails(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        broken['objects'].append({'id':'warehouse-01','type':'warehouse','label':'仓库'})
        broken['scenes'][0]['values']['object.warehouse-01.workers']=7
        broken['scenes'][1]['values']['object.warehouse-01.workers']=7
        broken['scenes'][2]['values']['object.warehouse-01.workers']=7
        e=next(x for x in broken['elements'] if x['id']=='workers')
        e['binding']='object.warehouse-01.workers'
        with self.assertRaisesRegex(SceneError,'different domain object'):
            compile_scene_graph(plan,broken)

    def test_wrong_selected_object_fails(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        broken['scenes'][1]['selected_object_id']='warehouse-01'
        with self.assertRaisesRegex(SceneError,'Selected domain object'):
            compile_scene_graph(plan,broken)

    def test_wrong_effect_state_transition_fails(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        broken['scenes'][2]['values']['object.farm-01.workers']=6
        with self.assertRaisesRegex(SceneError,'State transition'):
            compile_scene_graph(plan,broken)

    def test_functional_error_success_instead_failure_fails(self):
        plan,spec,_=self.fixtures['new-asset-studio']
        broken=copy.deepcopy(spec)
        broken['scenes'][2]['values']['ui.notice']='保存成功'
        with self.assertRaisesRegex(SceneError,'State transition'):
            compile_scene_graph(plan,broken)

    def test_exact_required_evidence_missing_fails(self):
        plan,spec,_=self.fixtures['new-asset-studio']
        broken=copy.deepcopy(spec)
        broken['scenes'][0]['visible_elements'].remove('filter-control')
        with self.assertRaisesRegex(SceneError,'Visible evidence missing'):
            compile_scene_graph(plan,broken)

    def test_required_ui_text_missing_fails(self):
        plan,spec,_=self.fixtures['new-asset-studio']
        broken=copy.deepcopy(spec)
        next(x for x in broken['elements'] if x['id']=='save-failed')['label']='发生错误'
        broken['scenes'][2]['values']['ui.notice']='发生错误'
        broken['actions'][1]['effects']['ui.notice']['value']='发生错误'
        with self.assertRaisesRegex(SceneError,'Exact required UI text'):
            compile_scene_graph(plan,broken)

    def test_state_change_without_action_fails(self):
        plan,spec,_=self.fixtures['new-hamlet-builder']
        broken=copy.deepcopy(spec)
        broken['scenes'][1]['event_id']=None
        with self.assertRaisesRegex(SceneError,'State changed with no recorded action'):
            compile_scene_graph(plan,broken)

    def test_svg_round_trip_binds_data_and_identity(self):
        plan,spec,graph=self.fixtures['new-hamlet-builder']
        with TemporaryDirectory() as tmp:
            manifest=render_scene_graph(graph,Path(tmp)/'render',plan=plan)
            result=verify_scene_svgs(graph,Path(tmp)/'render/manifest.json')
            self.assertEqual(result['svgs_verified'],3)
            self.assertEqual(len(manifest['images']),3)
            root=ET.parse(Path(tmp)/'render/STEP-003.svg').getroot()
            self.assertEqual(root.attrib['data-graph-sha256'],graph['graph_sha256'])
            values={x.attrib['id']:x.attrib for x in root if 'id' in x.attrib}
            self.assertEqual(values['workers']['data-display-value'],'3')
            self.assertEqual(values['selected-farm']['data-object-id'],'farm-01')
            self.assertEqual(values['production']['data-display-value'],'6')
            self.assertEqual(values['assign-button']['data-action'],'assign-worker')
            layouts=[]
            for i in range(1,4):
                r=ET.parse(Path(tmp)/f'render/STEP-00{i}.svg').getroot()
                layouts.append({x.attrib['id']:x.attrib['data-rect'] for x in r if 'id' in x.attrib})
            self.assertEqual(layouts[0]['world'],layouts[1]['world'])
            self.assertEqual(layouts[1]['world'],layouts[2]['world'])
            self.assertEqual(layouts[0]['selected-farm'],layouts[2]['selected-farm'])

    def test_rendered_svg_tampering_detected(self):
        graph=self.fixtures['new-asset-studio'][2]
        with TemporaryDirectory() as tmp:
            render_scene_graph(graph,Path(tmp)/'render')
            p=Path(tmp)/'render/STEP-003.svg'
            p.write_bytes(p.read_bytes().replace('保存失败'.encode(),'保存成功'.encode()))
            with self.assertRaisesRegex(SceneError,'SVG image content changed'):
                verify_scene_svgs(graph,Path(tmp)/'render/manifest.json')

    def test_hash_integrity_catches_graph_change(self):
        graph=copy.deepcopy(self.fixtures['new-hamlet-builder'][2])
        graph['scenes'][2]['values']['object.farm-01.workers']=99
        with self.assertRaisesRegex(SceneError,'digest mismatch'):
            validate_scene_graph(graph)

    def test_svg_is_safe_and_no_remote_resources(self):
        graph=self.fixtures['new-asset-studio'][2]
        with TemporaryDirectory() as tmp:
            render_scene_graph(graph,Path(tmp)/'render')
            for p in Path(tmp,'render').glob('*.svg'):
                txt=p.read_text('utf-8')
                for token in ('<script','foreignObject','xlink:href','url(http','onload=', '<iframe'):
                    self.assertNotIn(token,txt)

    def test_cli_commands_end_to_end(self):
        plan,spec,_=self.fixtures['new-asset-studio']
        with TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            p=tmp/'plan.json';p.write_text(json.dumps(plan,ensure_ascii=False))
            s=tmp/'spec.json';s.write_text(json.dumps(spec,ensure_ascii=False))
            graph=tmp/'graph.json';render=tmp/'renders'
            self.assertEqual(run(['scene-compile',str(p),'--spec',str(s),'--out',str(graph)]),0)
            self.assertEqual(run(['scene-verify',str(graph),'--plan',str(p)]),0)
            self.assertEqual(run(['svg-render',str(graph),'--plan',str(p),'--out-dir',str(render)]),0)
            self.assertEqual(run(['svg-verify',str(graph),'--manifest',str(render/'manifest.json')]),0)
            self.assertEqual(len(list(render.glob('*.svg'))),3)

if __name__=='__main__':unittest.main()
