"""Deterministic scene plan generation from a structured software use case."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class SceneError(ValueError):
    """Invalid or unsupported scene source."""

DEFAULT_STYLE = "realistic documentary photography, truthful product concept visualization"
STYLE_PRESETS = {
    "realistic": DEFAULT_STYLE,
    "sketch": "clear grayscale UX concept sketch, minimal shading, legible silhouettes",
    "illustration": "restrained editorial illustration, coherent perspective and spatial relationships",
    "ui-focused": "realistic first-person device view, screen is dominant and sharp, restrained surroundings",
}
MANDATORY = ("id", "title", "actor", "goal", "environment", "device", "steps")
VIEWPOINT_MODES = {
    "physical-user": "True first-person eye-level view of the real user operating a physical device; the application or game is visible on its real display, not an imagined walkable virtual world.",
    "avatar-eyes": "True in-game first-person view from the controlled avatar's eyes, looking directly into the playable virtual world; do not show a physical computer, screen bezel, keyboard, desk, or an external observer.",
}


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SceneError(f"{name} must be a non-empty string")
    return value.strip()

def validate_use_case(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise SceneError("Use case must be an object")
    if isinstance(data.get("extraction"), dict) and data["extraction"].get("ready") is False:
        raise SceneError("Extracted draft is not ready: " + "; ".join(data["extraction"].get("issues", [])))
    for key in MANDATORY:
        if key not in data:
            raise SceneError(f"Missing field: {key}")
    for key in ("id", "title", "actor", "goal", "environment", "device"):
        _require_str(data[key], key)
    mode = data.get("viewpoint_mode", "physical-user")
    if mode not in VIEWPOINT_MODES:
        raise SceneError(f"Unsupported viewpoint_mode: {mode!r}")
    if mode == "avatar-eyes" and data.get("device", "").strip().casefold() in {"pc", "laptop", "desktop monitor", "computer monitor", "手机", "电脑显示器"}:
        raise SceneError("avatar-eyes mode requires an in-game viewport, not a physical monitor device")
    if data.get("style", "realistic") not in STYLE_PRESETS:
        raise SceneError(f"style must be one of: {', '.join(STYLE_PRESETS)}")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise SceneError("steps must be a non-empty list")
    ids: set[str] = set()
    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            raise SceneError(f"steps[{i}] must be an object")
        for key in ("id", "action", "visible_evidence"):
            if key not in step:
                raise SceneError(f"steps[{i}].{key} is required")
        sid = _require_str(step["id"], f"steps[{i}].id")
        _require_str(step["action"], f"steps[{i}].action")
        if sid in ids:
            raise SceneError(f"Duplicate step id: {sid}")
        ids.add(sid)
        evidence = step["visible_evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise SceneError(f"steps[{i}].visible_evidence must be non-empty")
        for j, e in enumerate(evidence):
            _require_str(e, f"steps[{i}].visible_evidence[{j}]")
        state = step.get("state", "in-progress")
        if state not in {"start", "in-progress", "waiting", "success", "failure"}:
            raise SceneError(f"steps[{i}].state unsupported: {state}")
        branch = step.get("branch", "main")
        if branch not in {"main", "alternative", "exception"}:
            raise SceneError(f"steps[{i}].branch unsupported: {branch}")
        if "ui_text" in step and (not isinstance(step["ui_text"], list) or any(not isinstance(v,str) for v in step["ui_text"])):
            raise SceneError(f"steps[{i}].ui_text must be a list of strings")
    if "constraints" in data:
        c = data["constraints"]
        if not isinstance(c, dict):
            raise SceneError("constraints must be an object")
        for key in ("must_show", "must_not_show"):
            if key in c and (not isinstance(c[key], list) or any(not isinstance(v,str) for v in c[key])):
                raise SceneError(f"constraints.{key} must be list of strings")
    return data

def make_scene_anchor(data: dict[str, Any]) -> dict[str, str]:
    c = data.get("constraints", {})
    return {
        "actor": data["actor"].strip(),
        "environment": data["environment"].strip(),
        "device": data["device"].strip(),
        "style": data.get("style", "realistic"),
        "viewpoint_mode": data.get("viewpoint_mode", "physical-user"),
        "viewpoint": VIEWPOINT_MODES[data.get("viewpoint_mode", "physical-user")],
        "continuity": str(c.get("continuity", "same physical environment, device, and visual style in all scenes")),
    }

def _prompt(case: dict[str, Any], step: dict[str, Any], anchor: dict[str, str]) -> str:
    evidence = "\n".join(f"- {v}" for v in step["visible_evidence"])
    constraints = case.get("constraints", {})
    must_show = constraints.get("must_show", [])
    must_not_show = constraints.get("must_not_show", [])
    exact = step.get("ui_text", [])
    avatar = anchor["viewpoint_mode"] == "avatar-eyes"
    camera_rule = (
        "CAMERA: In-game first-person avatar-eyes view. Look straight into the world through the controlled avatar's eyes. No monitor, no workstation, no HUD invented beyond documented evidence. No external view of the avatar."
        if avatar else
        "CAMERA: Physical user's first-person eyes looking at the real device display while operating it. A plausible partial hand may appear. The source application's original camera (isometric/top-down/2D) MUST REMAIN as seen on the screen; never transform the game's world into a fictional first-person 3D scene. No third-person photo of the user."
    )
    return "\n".join([
        "Create ONE authentic first-person use-case scene illustration, not a diagram or a third-person portrait.",
        camera_rule,
        f"POV MODE: {anchor['viewpoint_mode']}",
        f"ACTOR ROLE: {anchor['actor']}",
        f"TASK GOAL: {case['goal']}",
        f"ENVIRONMENT: {anchor['environment']}",
        f"INTERACTION DEVICE: {anchor['device']}",
        f"CURRENT STEP: {step['action']}",
        f"STEP STATE: {step.get('state', 'in-progress')}; FLOW: {step.get('branch', 'main')}",
        "REQUIRED VISIBLE EVIDENCE (each must be recognizable):\n" + evidence,
        "ADDITIONAL MUST-SHOW: " + ("; ".join(must_show) if must_show else "none"),
        "FORBIDDEN: " + "; ".join(["third-person view", "full-body user", "unrelated decorative activity", "invented system behavior", *(["monitor frame", "desk", "real-world hands holding a controller"] if avatar else []), *must_not_show]),
        "SCENE ANCHOR (do not change across this use case): " + anchor["continuity"],
        "VISUAL STYLE: " + STYLE_PRESETS[anchor["style"]],
        "VISIBLE UI TEXT: " + ("; ".join(exact) if exact else "use minimal generic UI labels, avoid invented product claims"),
        "IMPORTANT: Image generation may not reproduce text perfectly; keep critical exact words in a separate post-production UI overlay, not as proof of functional correctness.",
        "EVIDENCE POLICY: Only the provided use-case evidence and explicitly supplied references are product facts. Camera framing and background are visualization assumptions, not product requirements.",
        "FOCUS: Tell the story of this exact action and its current state, with clear environmental context, plausible posture, consistent scale and camera geometry. Do not invent additional screens, permissions, actors, outcomes, or actions.",
    ])

def build_plan(data: dict[str, Any], step_ids: list[str] | None = None) -> dict[str, Any]:
    case = validate_use_case(data)
    choices = set(step_ids or [])
    ids = {s["id"] for s in case["steps"]}
    if choices - ids:
        raise SceneError("Unknown step(s): " + ", ".join(sorted(choices - ids)))
    anchor = make_scene_anchor(case)
    scenes = []
    for index, step in enumerate(case["steps"]):
        if choices and step["id"] not in choices:
            continue
        prompt = _prompt(case, step, anchor)
        scenes.append({
            "id": f"{case['id']}--{step['id']}",
            "index": index,
            "step_id": step["id"],
            "action": step["action"],
            "state": step.get("state", "in-progress"),
            "branch": step.get("branch", "main"),
            "evidence": step["visible_evidence"],
            "exact_ui_text": step.get("ui_text", []),
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
    return {
        "format_version": "1.0",
        "use_case_id": case["id"],
        "title": case["title"],
        "source": "structured-use-case",
        "anchor": anchor,
        "scenes": scenes,
        "caveats": ["Visual evidence is planned, not yet image-verified", "Image model output is nondeterministic", "Exact UI lettering requires external overlay or manual review"],
    }

def review_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.get("scenes"), list) or not plan["scenes"]:
        errors.append("No scenes")
    seen: set[str] = set()
    anchor = plan.get("anchor")
    if not isinstance(anchor, dict) or anchor.get("viewpoint_mode", "physical-user") not in VIEWPOINT_MODES:
        errors.append("Invalid or missing viewpoint anchor")
    for scene in plan.get("scenes", []):
        sid = scene.get("id", "")
        if sid in seen:
            errors.append(f"Duplicate scene ID: {sid}")
        seen.add(sid)
        if not scene.get("evidence"):
            errors.append(f"Missing visual evidence: {sid}")
        prompt = scene.get("prompt", "")
        for required in ("first-person", "CAMERA:", "POV MODE:", "REQUIRED VISIBLE EVIDENCE", "SCENE ANCHOR"):
            if required not in prompt:
                errors.append(f"Missing prompt constraint {required}: {sid}")
        if anchor and f"POV MODE: {anchor.get('viewpoint_mode', 'physical-user')}" not in prompt:
            errors.append(f"Scene viewpoint mismatch: {sid}")
        if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != scene.get("prompt_sha256"):
            errors.append(f"Prompt hash mismatch: {sid}")
    return errors

def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise SceneError(f"Invalid JSON: {e}") from e

def save_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
