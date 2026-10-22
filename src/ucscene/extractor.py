"""Conservative, fully offline extraction from structured Chinese/English use-case markdown.

Unknowns are left empty (and validation fails) rather than being guessed.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .core import SceneError, validate_use_case

_FIELDS: dict[str, tuple[str, ...]] = {
    "id": ("用例编号", "用例ID", "用例 ID", "use case id", "id"),
    "title": ("用例名称", "名称", "标题", "title", "use case"),
    "actor": ("参与者", "用户角色", "主要参与者", "actor", "role"),
    "goal": ("用例目标", "业务目标", "目标", "goal", "purpose"),
    "environment": ("所处环境", "场景环境", "环境", "environment", "location"),
    "device": ("交互设备", "设备", "终端", "device", "interface"),
}
_ALIASES = {alias.lower(): field for field, aliases in _FIELDS.items() for alias in aliases}
_TITLE = re.compile(r"^\s*#{1,6}\s+(.*?)\s*$")
_FIELD = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?([\w\u4e00-\u9fff ]+)(?:\*\*)?\s*[:：]\s*(.*?)\s*$")
_STEP = re.compile(r"^\s*(?:[-*]\s+|\d+[.、)）]\s+)(.+?)\s*$")
_SECTION_NAMES = {
    "主流程": "main", "基本流程": "main", "正常流程": "main", "main flow": "main", "main scenario": "main",
    "异常流程": "exception", "异常分支": "exception", "exception flow": "exception", "error flow": "exception",
    "替代流程": "alternative", "备选流程": "alternative", "alternative flow": "alternative",
}
_EVIDENCE_SPLIT = re.compile(r"(?:\s+\|\s*|\s+[;；]\s*)(?:画面|可见|视觉证据|visible|evidence)\s*[:：]", re.I)
_VISIBLE_LINE = re.compile(r"^\s*(?:[-*]\s*)?(?:画面|可见|视觉证据|visible|evidence)\s*[:：]\s*(.*?)\s*$", re.I)


def _split_evidence(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*[,，、;；]\s*", value) if part.strip()]


def extract_markdown(source: str, *, overrides: dict[str, str] | None = None) -> dict[str, Any]:
    """Return a draft with extraction_issues; only drafts with ready=True can be planned."""
    if not isinstance(source, str) or not source.strip():
        raise SceneError("Use-case Markdown must not be empty")
    case: dict[str, Any] = {field: "" for field in _FIELDS}
    case["steps"] = []
    section = "main"
    in_steps = False
    for line_no, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        match = _TITLE.match(line)
        if match:
            title = match.group(1).strip().rstrip(":：")
            key = title.lower()
            if key in _SECTION_NAMES:
                section = _SECTION_NAMES[key]
                in_steps = True
            elif key in {"步骤", "用例步骤", "步骤流程", "steps", "flow"}:
                in_steps = True
                section = "main"
            elif not case["title"] and not in_steps:
                case["title"] = title
            continue
        m = _FIELD.match(line)
        if m:
            field = _ALIASES.get(m.group(1).strip().lower())
            if field and m.group(2).strip():
                case[field] = m.group(2).strip()
                continue
        evidence = _VISIBLE_LINE.match(line)
        if evidence and case["steps"] and in_steps:
            case["steps"][-1]["visible_evidence"].extend(_split_evidence(evidence.group(1)))
            continue
        if in_steps:
            m = _STEP.match(line)
            if m:
                raw_step = m.group(1).strip()
                chunks = _EVIDENCE_SPLIT.split(raw_step, maxsplit=1)
                action = chunks[0].strip()
                if not action:
                    continue
                visible = _split_evidence(chunks[1]) if len(chunks) > 1 else []
                state = "failure" if section == "exception" else "in-progress"
                case["steps"].append({
                    "id": f"step-{len(case['steps'])+1:02d}",
                    "action": action,
                    "visible_evidence": visible,
                    "state": state,
                    "branch": section,
                    "source_line": line_no,
                })
    overrides = overrides or {}
    for field, value in overrides.items():
        if field not in _FIELDS:
            raise SceneError(f"Unknown override: {field}")
        case[field] = value.strip()
    # A source-generated ID is deterministic but isn't silently treated as a requirement ID.
    if not case["id"]:
        case["id"] = "DRAFT-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:10].upper()
    issues: list[str] = []
    for field in ("actor", "goal", "environment", "device"):
        if not case[field]:
            issues.append(f"Missing explicit {field}; edit the draft or use --{field}")
    if not case["steps"]:
        issues.append("No numbered steps under a main/exception/alternative flow section")
    for step in case["steps"]:
        if not step["visible_evidence"]:
            issues.append(f"{step['id']}: Missing explicit visible evidence (e.g. | 画面: ...)")
    if not issues:
        validate_use_case(case)
    case["extraction"] = {
        "method": "structured-markdown-offline",
        "ready": not issues,
        "issues": issues,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "source_generated_id": case["id"].startswith("DRAFT-"),
    }
    return case
