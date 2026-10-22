"""Deterministic, software-content-only scene plans from structured use cases."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

class SceneError(ValueError):
    """Invalid or unsupported scene source."""

# The output canvas is the application's framebuffer/content, never a picture of a user.
FRAME_SCOPE = "software-only"
DEFAULT_VIEWPOINT_MODE = "application-ui"
DEFAULT_STYLE = "accurate application viewport concept rendering, no external physical setting"
STYLE_PRESETS = {
    "realistic": "high-fidelity in-software pixels and plausible runtime appearance; no photography of devices",
    "sketch": "low-fidelity wireframe of software-internal regions and controls, not paper or a desk",
    "illustration": "coherent stylized digital content entirely within the product's own viewport",
    "ui-focused": "legible full-bleed application UI or in-game HUD/viewport, accurate hierarchy and states",
}
MANDATORY = ("id", "title", "actor", "goal", "environment", "steps")
VIEWPOINT_MODES = {
    "application-ui": "The full canvas is the application's own UI or editor view; show only its digital panels, controls and content.",
    "gameplay": "The full canvas is the game's own rendered viewport and justified HUD; preserve the game's documented in-game camera.",
}
GAME_CAMERAS = {
    "documented": "preserve the camera/view expressly documented by the use case; never invent a new angle",
    "first-person": "player-character eye view within the game world (in-game hands permitted only if documented)",
    "isometric": "isometric camera looking onto the game world; never convert to character-eye or real-life perspective",
    "top-down": "top-down game camera; do not substitute character-eye perspective",
    "side-scrolling": "side-scrolling game viewport with original game camera",
    "third-person": "in-game third-person avatar view; the avatar is game content, not a real user",
}
DEPRECATED_MODES = {
    "physical-user": "application-ui (desktop software) or gameplay (games)",
    "avatar-eyes": "gameplay with game_camera=first-person",
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
    for key in ("id", "title", "actor", "goal", "environment"):
        _require_str(data[key], key)
    banned_outside = (
        "用户坐在电脑前", "开发者坐在电脑前", "从用户眼睛看向显示器", "显示器边框", "桌面上的键盘",
        "握着扫码终端的手", "扫描头对准实物", "拍摄使用软件的用户", "physical user's eyes", "over-the-shoulder photo",
    )
    if any(term in data["environment"].casefold() for term in banned_outside):
        raise SceneError("Environment describes a physical user/device shot; supply an IN-SOFTWARE context instead")
    if "device" in data and not isinstance(data["device"], str):
        raise SceneError("device is optional legacy source metadata, not a visual object")
    mode = data.get("viewpoint_mode", DEFAULT_VIEWPOINT_MODE)
    if mode in DEPRECATED_MODES:
        raise SceneError(f"Deprecated viewpoint_mode {mode!r}: choose {DEPRECATED_MODES[mode]}. No physical-user scenes are allowed")
    if mode not in VIEWPOINT_MODES:
        raise SceneError(f"Unsupported viewpoint_mode: {mode!r}")
    camera = data.get("game_camera", "documented")
    if camera not in GAME_CAMERAS:
        raise SceneError(f"Unsupported game_camera: {camera!r}")
    if mode == "application-ui" and camera != "documented":
        raise SceneError("game_camera is applicable only to gameplay mode")
    if data.get("frame_scope", FRAME_SCOPE) != FRAME_SCOPE:
        raise SceneError("frame_scope must be software-only; real-world operator/device scenes are out of scope")
    if data.get("style", "ui-focused") not in STYLE_PRESETS:
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
            if any(term in e.casefold() for term in banned_outside):
                raise SceneError(f"steps[{i}].visible_evidence[{j}] demands outside-software content")
        state = step.get("state", "in-progress")
        if state not in {"start", "in-progress", "waiting", "success", "failure"}:
            raise SceneError(f"steps[{i}].state unsupported: {state}")
        branch = step.get("branch", "main")
        if branch not in {"main", "alternative", "exception"}:
            raise SceneError(f"steps[{i}].branch unsupported: {branch}")
        if "ui_text" in step and (not isinstance(step["ui_text"], list) or any(not isinstance(v,str) for v in step["ui_text"])):
            raise SceneError(f"steps[{i}].ui_text must be a list of strings")
        if "carry_forward" in step:
            values = step["carry_forward"]
            if (not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values)):
                raise SceneError(f"steps[{i}].carry_forward must be a list of nonempty source-supported facts")
            if any(any(term in v.casefold() for term in banned_outside) for v in values):
                raise SceneError(f"steps[{i}].carry_forward contains outside-software content")
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
    mode = data.get("viewpoint_mode", DEFAULT_VIEWPOINT_MODE)
    return {
        "frame_scope": FRAME_SCOPE,
        "actor": data["actor"].strip(),  # metadata only: never visualize the user/operator
        "environment": data["environment"].strip(),  # virtual workspace / in-game context
        "viewpoint_mode": mode,
        "game_camera": data.get("game_camera", "documented"),
        "viewpoint": VIEWPOINT_MODES[mode],
        "style": data.get("style", "ui-focused"),
        "continuity": str(c.get("continuity", "same software layout, project/level and view across steps")),
    }


def _prompt(case: dict[str, Any], step: dict[str, Any], anchor: dict[str, str], prior_facts: list[str]) -> str:
    evidence = "\n".join(f"- {v}" for v in step["visible_evidence"])
    constraints = case.get("constraints", {})
    exact = step.get("ui_text", [])
    mode = anchor["viewpoint_mode"]
    camera_rule = (
        "CAMERA: DIRECT application/editor UI pixels, captured as if from the application's own viewport. "
        "No monitor body, device bezel or surroundings. Preserve genuine native editor/tool layout and controls."
        if mode == "application-ui" else
        "CAMERA: DIRECT game output pixels, from the documented in-game camera. "
        + GAME_CAMERAS[anchor["game_camera"]] + ". "
        "Keep its genuine perspective, game environment, interactions and warranted HUD. "
        "Never reinterpret the game as someone physically looking at a screen."
    )
    forbidden = [
        "real human operator or player outside the software", "hands on keyboard or mouse outside the game",
        "physical monitor", "screen bezel", "desk", "office", "room photographed around a device",
        "phone or controller held in real-world hands", "third-person photo of software usage",
        "marketing mockup", "explainer poster", "multi-panel storyboard", "unrelated decorative activity",
        "invented UI features or game mechanics", *constraints.get("must_not_show", []),
    ]
    return "\n".join([
        "Render ONE SOFTWARE-ONLY use-case frame. OUTPUT MUST BE FULL-BLEED SOFTWARE CONTENT, not a photograph or drawing of someone using software.",
        "FRAME SCOPE: software-only; no physical-world framing, users, operators, peripherals or hardware.",
        camera_rule,
        f"POV MODE: {mode}",
        f"GAME CAMERA: {anchor['game_camera']}",
        f"ACTOR ROLE (metadata; DO NOT DEPICT PERSON): {anchor['actor']}",
        f"TASK GOAL: {case['goal']}",
        f"IN-SOFTWARE CONTEXT: {anchor['environment']}",
        f"CURRENT STEP: {step['action']}",
        f"STEP STATE: {step.get('state', 'in-progress')}; FLOW: {step.get('branch', 'main')}",
        "REQUIRED VISIBLE EVIDENCE (each must be recognizable in software/game pixels):\n" + evidence,
        "PERSISTENT SOFTWARE STATE FROM EARLIER STEPS: " + ("; ".join(prior_facts) if prior_facts else "none established"),
        "ADDITIONAL MUST-SHOW: " + ("; ".join(constraints.get("must_show", [])) if constraints.get("must_show") else "none"),
        "FORBIDDEN OUT-OF-SOFTWARE ELEMENTS: " + "; ".join(forbidden),
        "SOFTWARE ANCHOR (unchanged across this use case): " + anchor["continuity"],
        "RENDERING STYLE: " + STYLE_PRESETS[anchor["style"]],
        "VERBATIM UI TEXT: " + ("; ".join(exact) if exact else "do not invent specific UI text"),
        "TEXT FIDELITY: When exact glyphs matter, use a verified in-app screenshot or pixel-accurate UI overlay. Rendered text alone cannot verify software behavior.",
        "EVIDENCE POLICY: The supplied use-case evidence and explicitly provided product references are the only accepted product facts. Never invent controls, characters, permissions, game rules, states, or outcomes.",
        "FOCUS: Show only what exists INSIDE the application/game at this use-case step. A real human user is never part of the image. In-game characters may appear when the software itself displays them.",
    ])

def build_plan(data: dict[str, Any], step_ids: list[str] | None = None) -> dict[str, Any]:
    case = validate_use_case(data)
    choices = set(step_ids or [])
    ids = {s["id"] for s in case["steps"]}
    if choices - ids:
        raise SceneError("Unknown step(s): " + ", ".join(sorted(choices - ids)))
    anchor = make_scene_anchor(case)
    scenes = []
    # Prior-step facts must be preserved even when only one later step is selected.
    carried_facts: list[str] = []
    for index, step in enumerate(case["steps"]):
        if choices and step["id"] not in choices:
            for fact in step.get("carry_forward", []):
                if fact not in carried_facts:
                    carried_facts.append(fact)
            continue
        prompt = _prompt(case, step, anchor, carried_facts)
        scenes.append({
            "id": f"{case['id']}--{step['id']}",
            "index": index,
            "step_id": step["id"],
            "action": step["action"],
            "state": step.get("state", "in-progress"),
            "branch": step.get("branch", "main"),
            "evidence": step["visible_evidence"],
            "persistent_facts": list(carried_facts),
            "exact_ui_text": step.get("ui_text", []),
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
        for fact in step.get("carry_forward", []):
            if fact not in carried_facts:
                carried_facts.append(fact)
    return {
        "format_version": "1.1",
        "use_case_id": case["id"],
        "title": case["title"],
        "source": "structured-use-case",
        "anchor": anchor,
        "scenes": scenes,
        "caveats": ["Visual evidence is planned, not yet image-verified", "Image model output is nondeterministic", "Exact UI lettering requires external overlay or manual review"],
    }

def review_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("format_version") != "1.1":
        errors.append("Plan is not software-only v1.1: regenerate using the updated use-case source")
    if not isinstance(plan.get("scenes"), list) or not plan["scenes"]:
        errors.append("No scenes")
    seen: set[str] = set()
    anchor = plan.get("anchor")
    if not isinstance(anchor, dict) or anchor.get("viewpoint_mode") not in VIEWPOINT_MODES or anchor.get("frame_scope") != FRAME_SCOPE:
        errors.append("Invalid or non-software-only view anchor")
    for scene in plan.get("scenes", []):
        sid = scene.get("id", "")
        if sid in seen:
            errors.append(f"Duplicate scene ID: {sid}")
        seen.add(sid)
        if not scene.get("evidence"):
            errors.append(f"Missing visual evidence: {sid}")
        prompt = scene.get("prompt", "")
        for required in ("SOFTWARE-ONLY", "FRAME SCOPE: software-only", "CAMERA:", "POV MODE:", "REQUIRED VISIBLE EVIDENCE", "SOFTWARE ANCHOR", "FORBIDDEN OUT-OF-SOFTWARE"):
            if required not in prompt:
                errors.append(f"Missing software-only constraint {required}: {sid}")
        if anchor and f"POV MODE: {anchor.get('viewpoint_mode')}" not in prompt:
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
