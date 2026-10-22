"""Offline, provenance-aware benchmark of *plans*, optionally paired with real image audits.

A passing structural benchmark is NOT an image-quality score. Paid generation and
model vision review are separate explicitly opt-in commands.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .core import SceneError, build_plan, load_json, review_plan, validate_use_case


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_case(base: Path, name: Any) -> tuple[dict[str, Any], Path]:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise SceneError("Suite case file must be a relative path")
    path = (base / name).resolve()
    if not path.is_relative_to(base):
        raise SceneError("Suite case file escapes benchmark root")
    return load_json(path), path


def _check_source(case: dict[str, Any], entry: dict[str, Any]) -> int:
    sources = entry.get("official_sources")
    if not isinstance(sources, list) or not sources:
        raise SceneError("Each benchmark case must document at least one public source")
    ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str) or not source["id"].strip():
            raise SceneError("Source must include a nonempty ID")
        if source["id"] in ids:
            raise SceneError("Duplicate official source ID")
        ids.add(source["id"])
        url = source.get("url")
        if not isinstance(url, str) or urlparse(url).scheme != "https" or not urlparse(url).netloc:
            raise SceneError("Official sources must have an HTTPS URL")
        if not isinstance(source.get("paraphrase"), str) or not source["paraphrase"].strip():
            raise SceneError("Official source requires a concise fact summary")
    count = 0
    for step in case["steps"]:
        refs = step.get("source_refs")
        if not isinstance(refs, list) or not refs or any(ref not in ids for ref in refs):
            raise SceneError(f"Untraceable source_refs in {case['id']} / {step['id']}")
        count += len(step["visible_evidence"])
    return count


def _read_audit(audit_dir: Path, images_dir: Path, scene: dict[str, Any]) -> dict[str, Any] | None:
    sid = scene["id"]
    # Scene identifiers deliberately cannot be used as arbitrary path fragments.
    filename = sid + ".json"
    if Path(filename).name != filename or "/" in filename or "\\" in filename or ".." in filename:
        raise SceneError(f"Unsafe scene id for audit filename: {sid!r}")
    audit_file = audit_dir / filename
    if not audit_file.exists():
        return None
    report = load_json(audit_file)
    if report.get("scene_id") != sid:
        raise SceneError(f"Audit scene ID mismatch: {filename}")
    if report.get("prompt_sha256") != scene["prompt_sha256"]:
        raise SceneError(f"Audit prompt hash mismatch: {filename}")
    if report.get("method") != "model-vision-advisory" or type(report.get("passed")) is not bool:
        raise SceneError(f"Invalid audit method or result: {filename}")
    image = images_dir / (sid + ".png")
    if not image.is_file():
        raise SceneError(f"Audit requires a matching real image: {image.name}")
    expected_hash = report.get("image_sha256")
    if not isinstance(expected_hash, str) or _sha(image.read_bytes()) != expected_hash:
        raise SceneError(f"Audit image hash mismatch: {filename}")
    return {"scene_id": sid, "passed": report["passed"], "audit_file": filename, "method": "model-vision-advisory"}


def run_benchmark(suite_path: str | Path, *, audits: str | Path | None = None, images: str | Path | None = None) -> dict[str, Any]:
    """Validate a documented benchmark suite and report structural coverage.

    Optional paired audit+image folders permit provenance-verified aggregation
    of *advisory* visual findings. No image is generated, and no paid API called.
    """
    if (audits is None) != (images is None):
        raise SceneError("--audits and --images must be supplied together")
    suite_file = Path(suite_path).resolve()
    root = suite_file.parent
    suite = load_json(suite_file)
    if suite.get("format_version") != "1.0" or not isinstance(suite.get("suite_id"), str):
        raise SceneError("Unknown benchmark suite version or ID")
    items = suite.get("cases")
    if not isinstance(items, list) or not items:
        raise SceneError("Benchmark suite must have at least one case")
    audit_root = Path(audits).resolve() if audits is not None else None
    image_root = Path(images).resolve() if images is not None else None
    all_ids: set[str] = set()
    results = []
    expected_scenes = expected_evidence = checked_scenes = 0
    checked_evidence = 0
    visual_passed = visual_failed = visual_missing = 0
    for entry in items:
        if not isinstance(entry, dict):
            raise SceneError("Suite entries must be objects")
        case, filepath = _read_case(root, entry.get("file"))
        validate_use_case(case)
        if case["id"] in all_ids:
            raise SceneError(f"Duplicate case ID: {case['id']}")
        all_ids.add(case["id"])
        if case.get("benchmark_context", {}).get("project") != entry.get("project"):
            raise SceneError(f"Case project metadata mismatch: {case['id']}")
        if case.get("viewpoint_mode", "application-ui") != entry.get("expected_camera"):
            raise SceneError(f"Case camera does not match benchmark scenario: {case['id']}")
        case_evidence = _check_source(case, entry)
        plan = build_plan(case)
        errors = review_plan(plan)
        if errors:
            raise SceneError(f"Plan quality gate failed for {case['id']}: {'; '.join(errors)}")
        if build_plan(case) != plan:
            raise SceneError(f"Non-deterministic output for {case['id']}")
        expected_scenes += len(case["steps"])
        expected_evidence += case_evidence
        checked_scenes += len(plan["scenes"])
        checked_evidence += sum(len(x["evidence"]) for x in plan["scenes"])
        visual_results = []
        if audit_root and image_root:
            for scene in plan["scenes"]:
                audit = _read_audit(audit_root, image_root, scene)
                if audit is None:
                    visual_missing += 1
                elif audit["passed"]:
                    visual_passed += 1
                    visual_results.append(audit)
                else:
                    visual_failed += 1
                    visual_results.append(audit)
        results.append({
            "case_id": case["id"], "project": entry["project"], "category": entry.get("category", "unknown"),
            "camera": plan["anchor"]["viewpoint_mode"], "case_sha256": _sha(filepath.read_bytes()),
            "source_urls": [x["url"] for x in entry["official_sources"]],
            "expected_scenes": len(case["steps"]), "planned_scenes": len(plan["scenes"]),
            "source_linked_steps": len(case["steps"]), "visible_evidence_items": case_evidence,
            "prompt_sha256": {scene["step_id"]: scene["prompt_sha256"] for scene in plan["scenes"]},
            "structural_status": "pass", "visual_audits": visual_results,
        })
    if audit_root:
        # Make extra audits visible errors rather than silently ignore unsupported tests.
        expected_files = {f"{sid}--{step}.json" for result, entry in zip(results, items)
                          for step in [s['id'] for s in _read_case(root, entry['file'])[0]['steps']]
                          for sid in [result['case_id']]}
        extras = {p.name for p in audit_root.glob("*.json")} - expected_files
        if extras:
            raise SceneError("Unexpected audit files: " + ", ".join(sorted(extras)))
    visual = (
        {"status": "not_evaluated", "total_scenes": expected_scenes, "note": "No images were generated or visually evaluated by this offline benchmark"}
        if audit_root is None else
        {"status": "complete" if visual_missing == 0 else "incomplete", "total_scenes": expected_scenes,
         "model_audit_passed": visual_passed, "model_audit_failed_or_uncertain": visual_failed,
         "missing_image_audits": visual_missing,
         "note": "Model reviews are advisory, not independently established image quality or user study scores"}
    )
    return {
        "suite_id": suite["suite_id"], "suite_sha256": _sha(suite_file.read_bytes()),
        "kind": "offline-plan-and-source-integrity", "cases": len(results),
        "planned_scenes": checked_scenes, "expected_scenes": expected_scenes,
        "checked_visible_evidence": checked_evidence, "expected_visible_evidence": expected_evidence,
        "source_traceability": "all steps reference curated official documentation",
        "static_pass": checked_scenes == expected_scenes and checked_evidence == expected_evidence,
        "visual_evaluation": visual, "results": results,
        "limitations": [
            "Static metrics do not measure the correctness of actual generated pixels, typography, pose, UI, or composition.",
            "Curated source references were checked by the project maintainer at benchmark authoring time; this command does not crawl sites or check their freshness.",
            "A model-generated visual audit is fallible; controlled comparative claims require actual images and independent human ratings.",
        ],
    }


def export_benchmark_plans(suite_path: str | Path, output_directory: str | Path) -> dict[str, Any]:
    """Export usable per-case scene plans; all cases preflight before first write."""
    suite_file = Path(suite_path).resolve()
    suite = load_json(suite_file)
    if suite.get("format_version") != "1.0" or not isinstance(suite.get("cases"), list) or not suite["cases"]:
        raise SceneError("Unknown or empty benchmark suite")
    plans: list[tuple[dict[str, Any], dict[str, Any]]] = []
    known_ids: set[str] = set()
    for entry in suite["cases"]:
        case, _ = _read_case(suite_file.parent, entry["file"])
        validate_use_case(case)
        _check_source(case, entry)
        case_id = case["id"]
        if case_id in known_ids or not case_id.replace("-", "").replace("_", "").isalnum():
            raise SceneError(f"Duplicate or unsafe benchmark case ID: {case_id}")
        known_ids.add(case_id)
        if case.get("viewpoint_mode", "application-ui") != entry.get("expected_camera"):
            raise SceneError(f"Camera mode mismatch: {case_id}")
        plan = build_plan(case)
        if review_plan(plan):
            raise SceneError(f"Invalid benchmark plan: {case_id}")
        plans.append((entry, plan))
    from .core import save_json
    output = Path(output_directory).resolve()
    index = {"format_version": "1.0", "suite_id": suite["suite_id"], "plans": []}
    for entry, plan in plans:
        name = plan["use_case_id"] + ".json"
        save_json(output / name, plan)
        index["plans"].append({"project": entry["project"], "case_id": plan["use_case_id"], "plan_file": name, "scenes": len(plan["scenes"]), "viewpoint_mode": plan["anchor"]["viewpoint_mode"]})
    save_json(output / "index.json", index)
    return index


def make_prompt_lock(report: dict[str, Any]) -> dict[str, Any]:
    """Store approved golden prompt digests, never produced image quality scores."""
    if not report.get("static_pass"):
        raise SceneError("Cannot lock a failed benchmark")
    return {
        "format_version": "1.0", "suite_id": report["suite_id"],
        "suite_sha256": report["suite_sha256"],
        "cases": {r["case_id"]: {"case_sha256": r["case_sha256"], "prompt_sha256": dict(r["prompt_sha256"])} for r in report["results"]},
    }


def verify_prompt_lock(report: dict[str, Any], lock_file: str | Path) -> None:
    expected = load_json(lock_file)
    actual = make_prompt_lock(report)
    if expected != actual:
        raise SceneError("Benchmark prompt lock mismatch. Review changes and explicitly recreate lock with 'benchmark-lock' if intended")
