"""Host-native image routing declaration tests. All offline."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ucscene.cli import run
from ucscene.core import SceneError, load_json
from ucscene.design.planner import create_design_plan
from ucscene.rendering.concept import make_render_packet
from ucscene.rendering.host_guard import preflight_host_agent, verify_host_preflight

ROOT = Path(__file__).resolve().parents[1]


class HostAgentPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = load_json(ROOT / 'benchmarks/new-products/new-hamlet-builder.wp02.brief.json')
        plan = create_design_plan(source, variants=2)
        cls.packet = make_render_packet(plan, mode='draft', variant_id='VAR-01',
                                        step_ids=['STEP-001'])

    def capabilities(self):
        return {
            'format_version': '1.0', 'tool_id': 'test-native-tool',
            'explicit_prompt_supported': True,
            'one_image_per_call': True,
            'prompt_isolation_supported': True,
            'png_output_available': True,
            'submitted_prompt_record_available': False,
        }

    def test_eligible_route_retains_exact_product_and_step(self):
        c = self.capabilities()
        r = preflight_host_agent(self.packet, c)
        self.assertEqual(r['route'], 'host-native-eligible')
        self.assertEqual(r['product_id'], 'new-hamlet-builder')
        self.assertEqual([x['step_id'] for x in r['tasks']], ['STEP-001'])
        self.assertEqual(r['images_generated'], 0)
        self.assertFalse(r['external_api_fallback_authorized'])
        self.assertEqual(r['submitted_prompt_trace'], 'not-available')
        verify_host_preflight(self.packet, c, r)

    def test_no_explicit_prompt_blocks(self):
        c = self.capabilities()
        c['explicit_prompt_supported'] = False
        r = preflight_host_agent(self.packet, c)
        self.assertEqual(r['route'], 'host-native-blocked')
        self.assertIn('explicit_prompt_supported', r['blocked_reasons'])

    def test_no_isolation_blocks(self):
        c = self.capabilities()
        c['prompt_isolation_supported'] = False
        self.assertEqual(preflight_host_agent(self.packet, c)['route'], 'host-native-blocked')

    def test_no_png_blocks(self):
        c = self.capabilities()
        c['png_output_available'] = False
        self.assertEqual(preflight_host_agent(self.packet, c)['route'], 'host-native-blocked')

    def test_no_single_image_control_blocks(self):
        c = self.capabilities()
        c['one_image_per_call'] = False
        self.assertEqual(preflight_host_agent(self.packet, c)['route'], 'host-native-blocked')

    def test_bad_boolean_does_not_count_as_true(self):
        c = self.capabilities()
        c['explicit_prompt_supported'] = 1
        with self.assertRaises(SceneError):
            preflight_host_agent(self.packet, c)

    def test_missing_flag_fails_closed(self):
        c = self.capabilities()
        del c['prompt_isolation_supported']
        with self.assertRaises(SceneError):
            preflight_host_agent(self.packet, c)

    def test_cross_packet_report_tampering_is_rejected(self):
        c = self.capabilities()
        r = preflight_host_agent(self.packet, c)
        r['tasks'][0]['scene_id'] = 'wrong'
        with self.assertRaises(SceneError):
            verify_host_preflight(self.packet, c, r)

    def test_cli_blocks_an_unrouteable_host(self):
        with TemporaryDirectory() as d:
            p = Path(d)
            (p / 'packet.json').write_text(json.dumps(self.packet), encoding='utf-8')
            c = self.capabilities()
            c['explicit_prompt_supported'] = False
            (p / 'caps.json').write_text(json.dumps(c), encoding='utf-8')
            self.assertEqual(run(['concept-agent-preflight', str(p / 'packet.json'),
                                  '--capabilities', str(p / 'caps.json'),
                                  '--out', str(p / 'result.json')]), 4)
            self.assertEqual(json.loads((p / 'result.json').read_text())['route'],
                             'host-native-blocked')

    def test_cli_eligible_host_still_does_not_generate(self):
        with TemporaryDirectory() as d:
            p = Path(d)
            (p / 'packet.json').write_text(json.dumps(self.packet), encoding='utf-8')
            (p / 'caps.json').write_text(json.dumps(self.capabilities()), encoding='utf-8')
            self.assertEqual(run(['concept-agent-preflight', str(p / 'packet.json'),
                                  '--capabilities', str(p / 'caps.json'),
                                  '--out', str(p / 'result.json')]), 0)
            self.assertEqual(json.loads((p / 'result.json').read_text())['images_generated'], 0)


if __name__ == '__main__':
    unittest.main()
