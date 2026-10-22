"""Operator-labelled, provenance-checked image benchmark across generation modes.

Never infer image quality from prompt plan integrity or simulated provider calls.
No image APIs, network access, or rater scores are created by this module.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from pathlib import Path
from typing import Any

from .benchmark import run_benchmark
from .core import SceneError, load_json, save_json
from .imaging import inspect_image

MODES = ("prompt-only", "fixed-reference", "sequential-chain")
SCORE_FIELDS = ("point_of_view", "visible_evidence", "app_fidelity", "continuity")


def _scene_filename(scene_id: str) -> str:
    if (not scene_id or scene_id in {".", ".."} or "/" in scene_id or "\\" in scene_id
            or ".." in scene_id or any(ord(c) < 32 for c in scene_id)):
        raise SceneError(f"Unsafe scene id: {scene_id!r}")
    return scene_id + ".png"


def rating_template(suite_path: str | Path) -> dict[str, Any]:
    """Create an empty scoring packet, with never-fabricated human findings."""
    report = run_benchmark(suite_path)
    questions = []
    for result in report["results"]:
        for step_id, prompt_hash in result["prompt_sha256"].items():
            sid = result["case_id"] + "--" + step_id
            filename = _scene_filename(sid)
            for mode in MODES:
                questions.append({
                    "scene_id": sid,
                    "case_id": result["case_id"],
                    "project": result["project"],
                    "mode": mode,
                    "prompt_sha256": prompt_hash,
                    "image_path": f"{mode}/{filename}",
                    "image_sha256": None,
                    "rater_id": None,
                    "ratings": {field: None for field in SCORE_FIELDS},
                    "unsupported_product_features": None,
                    "notes": "",
                })
    return {
        "format_version": "1.0",
        "suite_id": report["suite_id"],
        "suite_sha256": report["suite_sha256"],
        "method": "independent-human-visual-review",
        "score_scale": {"0": "fails", "1": "partial-or-uncertain", "2": "fully-visible-and-correct"},
        "instructions": "Replace null fields only after inspecting the actual generated PNG. Use distinct rater IDs. Copy entries for additional independent raters; do not score ungenerated images.",
        "ratings": questions,
    }


def score_human_packet(suite_path: str | Path, packet_path: str | Path, images_dir: str | Path) -> dict[str, Any]:
    """Score only images actually inspected by humans with byte-bound labels.

    Report missing tasks explicitly; a missing score is never a failure/pass and
    does not enter a success-rate denominator. Paired comparison only uses
    scene/rater matches scored in all modes.
    """
    benchmark = run_benchmark(suite_path)
    packet = load_json(packet_path)
    template = rating_template(suite_path)
    if (packet.get("format_version") != "1.0" or packet.get("method") != template["method"]
            or packet.get("suite_id") != template["suite_id"]
            or packet.get("suite_sha256") != template["suite_sha256"]):
        raise SceneError("Human rating packet suite/version/provenance mismatch")
    rows = packet.get("ratings")
    if not isinstance(rows, list):
        raise SceneError("Human rating packet must contain a ratings list")
    expected = {(item["scene_id"], item["mode"]): item for item in template["ratings"]}
    scene_ids = {k[0] for k in expected}
    seen: set[tuple[str, str, str]] = set()
    results: list[dict[str, Any]] = []
    valid_image_count = 0
    for n, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SceneError(f"ratings[{n}] must be an object")
        sid, mode = row.get("scene_id"), row.get("mode")
        key = (sid, mode)
        if key not in expected:
            raise SceneError(f"Unknown or invalid scene/mode at ratings[{n}]")
        definition = expected[key]
        if row.get("case_id") != definition["case_id"] or row.get("prompt_sha256") != definition["prompt_sha256"]:
            raise SceneError(f"Ratings metadata/prompt mismatch: {sid} {mode}")
        if row.get("image_path") != definition["image_path"]:
            raise SceneError(f"Image path mismatch: {sid} {mode}")
        rating = row.get("ratings")
        if not isinstance(rating, dict) or set(rating) != set(SCORE_FIELDS):
            raise SceneError(f"Incorrect rating fields: {sid} {mode}")
        rater = row.get("rater_id")
        values = [rating[field] for field in SCORE_FIELDS]
        if rater is None and all(x is None for x in values) and row.get("image_sha256") is None and row.get("unsupported_product_features") is None:
            # An empty template row means not evaluated. Never count it as failed or passed.
            continue
        if not isinstance(rater, str) or not rater.strip() or len(rater) > 80:
            raise SceneError(f"Rater ID required for scored image: {sid} {mode}")
        ident = (sid, mode, rater)
        if ident in seen:
            raise SceneError(f"Duplicate rater/scene/mode: {ident}")
        seen.add(ident)
        if any(type(x) is not int or x not in (0, 1, 2) for x in values):
            raise SceneError(f"All 4 quality criteria require 0, 1, or 2: {sid} {mode}")
        if type(row.get("unsupported_product_features")) is not bool:
            raise SceneError(f"unsupported_product_features must be boolean: {sid} {mode}")
        expected_image_hash = row.get("image_sha256")
        if not isinstance(expected_image_hash, str) or len(expected_image_hash) != 64:
            raise SceneError(f"Image SHA256 required: {sid} {mode}")
        image_file = Path(images_dir).resolve() / mode / _scene_filename(sid)
        # Inspect actual image pixels/metadata (not arbitrary bytes) before accepting a score.
        inspect_image(image_file)
        actual_hash = hashlib.sha256(image_file.read_bytes()).hexdigest()
        if actual_hash != expected_image_hash:
            raise SceneError(f"Actual image digest mismatch: {sid} {mode}")
        valid_image_count += 1
        passed = all(x == 2 for x in values) and not row["unsupported_product_features"]
        results.append({"scene_id": sid, "mode": mode, "rater_id": rater, "scores": {k: rating[k] for k in SCORE_FIELDS}, "passed_strict": passed})
    counters = Counter(x["mode"] for x in results)
    successes = Counter(x["mode"] for x in results if x["passed_strict"])
    by_pair: dict[tuple[str, str], dict[str, bool]] = defaultdict(dict)
    for item in results:
        by_pair[(item["scene_id"], item["rater_id"])][item["mode"]] = item["passed_strict"]
    paired_groups = {key: values for key, values in by_pair.items() if set(values) == set(MODES)}
    paired = list(paired_groups.values())
    paired_scenes = {scene_id for scene_id, _rater_id in paired_groups}
    per_mode = {
        mode: {
            "scored_reviews": counters[mode], "strict_passes": successes[mode],
            "strict_pass_rate": successes[mode] / counters[mode] if counters[mode] else None,
            "missing_from_single_rater_baseline": len(scene_ids) - len({x["scene_id"] for x in results if x["mode"] == mode}),
        } for mode in MODES
    }
    return {
        "suite_id": benchmark["suite_id"], "suite_sha256": benchmark["suite_sha256"],
        "method": "independent-human-visual-review", "scored_reviews": len(results),
        "actual_image_verifications": valid_image_count,
        "expected_scene_mode_pairs": len(expected), "rated_scene_mode_pairs": len({(x["scene_id"],x["mode"]) for x in results}),
        "coverage_complete": all(per_mode[m]["missing_from_single_rater_baseline"] == 0 for m in MODES),
        "per_mode": per_mode, "fully_paired_scene_rater_groups": len(paired),
        "paired_strict_passes": {mode: sum(item[mode] for item in paired) for mode in MODES},
        "comparison_ready": paired_scenes == scene_ids and bool(scene_ids),
        "warning": "Independent manual image scores only. Do not claim statistical superiority without sufficient replicated trials and blinded raters.",
    }
