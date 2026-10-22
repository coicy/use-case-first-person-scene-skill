import base64
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from ucscene.core import SceneError, build_plan, load_json, review_plan, save_json, validate_use_case
from ucscene.cli import run
from ucscene.provider import ProviderError, generate_openai_image

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "warehouse-scan.json"

class TestScenePlanner(unittest.TestCase):
    def setUp(self):
        self.case = load_json(EXAMPLE)

    def test_example_valid(self):
        self.assertEqual(len(validate_use_case(self.case)["steps"]), 4)

    def test_plan_deterministic(self):
        a = build_plan(self.case)
        self.assertEqual(a, build_plan(self.case))
        self.assertEqual(review_plan(a), [])
        self.assertEqual(len(a["scenes"]), 4)
        self.assertEqual(len({s["prompt_sha256"] for s in a["scenes"]}), 4)

    def test_anchor_stable(self):
        plan = build_plan(self.case)
        self.assertTrue(all(plan["anchor"]["environment"] in s["prompt"] for s in plan["scenes"]))

    def test_select_one_step(self):
        plan = build_plan(self.case, ["03-fail"])
        self.assertEqual(plan["scenes"][0]["branch"], "exception")
        self.assertEqual(len(plan["scenes"]), 1)

    def test_unknown_step_fails(self):
        with self.assertRaises(SceneError):
            build_plan(self.case, ["missing"])

    def test_missing_evidence_fails(self):
        self.case["steps"][0]["visible_evidence"] = []
        with self.assertRaises(SceneError):
            validate_use_case(self.case)

    def test_duplicate_ids_fail(self):
        self.case["steps"][1]["id"] = self.case["steps"][0]["id"]
        with self.assertRaises(SceneError):
            validate_use_case(self.case)

    def test_tamper_hash_detected(self):
        plan = build_plan(self.case)
        plan["scenes"][0]["prompt"] += " altered"
        self.assertTrue(any("hash mismatch" in s for s in review_plan(plan)))

    def test_roundtrip_and_cli(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            self.assertEqual(run(["plan", str(EXAMPLE), "--out", str(p)]), 0)
            self.assertEqual(run(["review", str(p)]), 0)
            self.assertEqual(len(load_json(p)["scenes"]), 4)

    def test_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ProviderError):
                generate_openai_image("test", "unused.png")

    def test_provider_mock(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args): return b""
        fake = FakeResponse()
        image = b"\x89PNG\r\n\x1a\nmock"
        with TemporaryDirectory() as d, patch("urllib.request.urlopen", return_value=fake), patch("json.load", return_value={"data":[{"b64_json":base64.b64encode(image).decode()}]}):
            p = Path(d) / "test.png"
            report = generate_openai_image("scene", p, api_key="test-key")
            self.assertEqual(p.read_bytes(), image)
            self.assertFalse(report["verified_image_content"])

if __name__ == "__main__":
    unittest.main()
