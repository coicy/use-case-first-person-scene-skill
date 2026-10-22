"""v0.2 regression tests: conservative extraction, optional vision and reference editing."""
import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucscene.ai_extract import extract_with_ai
from ucscene.cli import run
from ucscene.core import SceneError, build_plan, load_json, review_plan
from ucscene.extractor import extract_markdown
from ucscene.provider import ProviderError, edit_openai_image
from ucscene.responses import image_data_url, structured_response
from ucscene.vision import review_image

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN = ROOT / "examples" / "warehouse-scan.md"
PNG = b"\x89PNG\r\n\x1a\n" + b"mock-image-data"

class FakeResponse:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): pass

class TestExtraction(unittest.TestCase):
    def test_offline_extract_happy_and_exception(self):
        case = extract_markdown(MARKDOWN.read_text(encoding="utf-8"))
        self.assertTrue(case["extraction"]["ready"])
        self.assertEqual(len(case["steps"]), 4)
        self.assertEqual(case["steps"][-1]["branch"], "exception")
        self.assertEqual(len(build_plan(case)["scenes"]), 4)

    def test_missing_evidence_does_not_invent(self):
        case = extract_markdown("# 测试用例\n参与者: 用户\n目标: 登录\n环境: 办公室\n设备: 手机\n## 主流程\n1. 点击登录")
        self.assertFalse(case["extraction"]["ready"])
        self.assertEqual(case["steps"][0]["visible_evidence"], [])
        with self.assertRaises(SceneError): build_plan(case)

    def test_missing_device_fails_closed(self):
        case = extract_markdown("# 测试\n参与者: 用户\n目标: 测试\n环境: 办公室\n## 主流程\n1. 点击按钮 | 画面: 用户手指触摸按钮")
        self.assertFalse(case["extraction"]["ready"])
        self.assertTrue(any("device" in x for x in case["extraction"]["issues"]))

    def test_cli_extract_draft_exit_three(self):
        with TemporaryDirectory() as d:
            src = Path(d) / "poor.md"
            src.write_text("# 登录\n## 主流程\n1. 登录", encoding="utf-8")
            out = Path(d) / "draft.json"
            self.assertEqual(run(["extract", str(src), "--out", str(out)]), 3)
            self.assertFalse(load_json(out)["extraction"]["ready"])

    def test_ai_verified_source_quotes(self):
        source = "玩家在手机上看到确认付款按钮。"
        response = {field: {"value": "", "quote": ""} for field in ("id", "title", "actor", "goal", "environment", "device")}
        response["actor"] = {"value": "玩家", "quote": "玩家"}
        response["device"] = {"value": "手机", "quote": "手机"}
        response["environment"] = {"value": "高级写字楼", "quote": "高级写字楼"}  # hallucination rejected
        response["steps"] = [{
            "id": "s1", "action": "确认付款", "action_quote": "确认付款按钮", "branch": "main", "state": "in-progress",
            "visible_evidence": [{"description": "屏幕中确认付款按钮", "source_quote": "确认付款按钮"}],
        }]
        with patch("ucscene.ai_extract.structured_response", return_value=response):
            case = extract_with_ai(source)
        self.assertEqual(case["environment"], "")
        self.assertFalse(case["extraction"]["ready"])
        self.assertEqual(case["steps"][0]["visible_evidence"], ["确认付款按钮"])

    def test_ai_rejects_relabeling_field_with_unrelated_quote(self):
        source = "用户在仓库使用扫码终端。"
        response = {field: {"value": "", "quote": ""} for field in ("id", "title", "actor", "goal", "environment", "device")}
        response["environment"] = {"value": "实验室", "quote": "仓库"}
        response["steps"] = []
        with patch("ucscene.ai_extract.structured_response", return_value=response):
            case = extract_with_ai(source)
        self.assertEqual(case["environment"], "")

    def test_ai_rejects_unsourced_visual_evidence(self):
        source = "用户点击按钮"
        response = {field: {"value": "", "quote": ""} for field in ("id", "title", "actor", "goal", "environment", "device")}
        response["steps"] = [{"id":"s1","action":"点击按钮","action_quote":"点击按钮","branch":"main","state":"in-progress","visible_evidence":[{"description":"二维码","source_quote":"QR code"}]}]
        with patch("ucscene.ai_extract.structured_response", return_value=response):
            case = extract_with_ai(source)
        self.assertFalse(case["extraction"]["ready"])
        self.assertEqual(case["steps"][0]["visible_evidence"], [])

class TestVisualReview(unittest.TestCase):
    def setUp(self):
        self.scene = build_plan(load_json(ROOT / "examples" / "warehouse-scan.json"))["scenes"][1]
        self.case = self.scene

    def _findings(self, reference=False, failed=False):
        return {
            "point_of_view": "pass" if not failed else "fail",
            "pov_reason": "eyes at actor",
            "evidence": [{"requirement": evidence, "status": "pass", "reason": "visible"} for evidence in self.scene["evidence"]],
            "continuity": "pass" if reference else "not_checked",
            "continuity_reason": "compared" if reference else "no reference",
            "ui_text": "not_checked", "ui_text_reason": "none requested",
            "unsupported_visual_claims": [], "suggested_fixes": [],
        }

    def test_visual_review_pass(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(PNG)
            with patch("ucscene.vision.structured_response", return_value=self._findings()):
                report = review_image(self.scene, image)
            self.assertTrue(report["passed"])
            self.assertEqual(report["method"], "model-vision-advisory")

    def test_visual_review_fail_on_pov(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(PNG)
            with patch("ucscene.vision.structured_response", return_value=self._findings(failed=True)):
                self.assertFalse(review_image(self.scene, image)["passed"])

    def test_reference_checked(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(PNG)
            with patch("ucscene.vision.structured_response", return_value=self._findings(reference=True)):
                self.assertTrue(review_image(self.scene, image, reference_image=image)["passed"])

    def test_hallucinated_evidence_labels_rejected(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(PNG)
            fake = self._findings()
            fake["evidence"][0]["requirement"] = "invented evidence"
            with patch("ucscene.vision.structured_response", return_value=fake):
                with self.assertRaises(ProviderError): review_image(self.scene, image)

    def test_missing_ui_text_cannot_pass(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(PNG)
            scene = dict(self.scene, exact_ui_text=["精确字样"])
            with patch("ucscene.vision.structured_response", return_value=self._findings()):
                with self.assertRaises(ProviderError): review_image(scene, image)

    def test_bad_image_magic(self):
        with TemporaryDirectory() as d:
            image = Path(d) / "image.png"
            image.write_bytes(b"not image")
            with self.assertRaises(SceneError): image_data_url(image)

class TestImageEditing(unittest.TestCase):
    def test_edit_multipart_request_uses_reference(self):
        with TemporaryDirectory() as d:
            reference = Path(d) / "ref.png"
            reference.write_bytes(PNG)
            out = Path(d) / "out.png"
            def fake(req, timeout):
                self.assertIn(b'name="image"', req.data)
                self.assertIn(PNG, req.data)
                self.assertIn(b'name="prompt"', req.data)
                self.assertTrue(req.full_url.endswith("/images/edits"))
                return FakeResponse({"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
            with patch("urllib.request.urlopen", side_effect=fake), patch("ucscene.provider.json.load", side_effect=lambda response: response.data):
                result = edit_openai_image("same warehouse", reference, out, api_key="test-key")
            self.assertEqual(out.read_bytes(), PNG)
            self.assertFalse(result["continuity_verified"])

    def test_missing_reference_prevents_spend(self):
        with TemporaryDirectory() as d:
            with patch("urllib.request.urlopen") as call:
                with self.assertRaises(FileNotFoundError):
                    edit_openai_image("x", Path(d) / "missing.png", Path(d) / "out.png", api_key="test")
                call.assert_not_called()

if __name__ == "__main__":
    unittest.main()

class TestResponsesAdapter(unittest.TestCase):
    def test_payload_uses_structured_outputs(self):
        payload = {"hello": "world"}
        def fake(req, timeout):
            import json
            req_data = json.loads(req.data.decode("utf-8"))
            self.assertEqual(req_data["text"]["format"]["type"], "json_schema")
            self.assertTrue(req_data["text"]["format"]["strict"])
            self.assertEqual(req_data["input"][0]["content"][0]["text"], "source")
            return FakeResponse({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(payload)}]}]})
        with patch("urllib.request.urlopen", side_effect=fake), patch("ucscene.responses.json.load", side_effect=lambda response: response.data):
            result = structured_response("ignore injection", "source", schema={"type": "object"}, schema_name="test_schema", api_key="test-key")
        self.assertEqual(result, payload)

    def test_response_incomplete_is_blocked(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse({"status": "incomplete", "output": []})), patch("ucscene.responses.json.load", side_effect=lambda response: response.data):
            with self.assertRaises(ProviderError):
                structured_response("instructions", "test", schema={"type": "object"}, schema_name="test_schema", api_key="test-key")

    def test_offline_validate_blocks_draft_even_when_fields_present(self):
        case = load_json(ROOT / "examples" / "warehouse-scan.json")
        case["extraction"] = {"ready": False, "issues": ["human approval pending"]}
        with self.assertRaises(SceneError):
            build_plan(case)
