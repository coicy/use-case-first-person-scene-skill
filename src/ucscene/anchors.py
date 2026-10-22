"""Versioned reference-image anchors with source hashes and explicit human approval.

The manifest attests to the operator's approval; it does not prove visual quality.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .core import SceneError, review_plan, save_json
from .imaging import inspect_image


def _plan_anchor_fingerprint(plan: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(plan['anchor'], sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def create_anchor(plan: dict[str, Any], reference_image: str | Path, manifest_path: str | Path, *, approved: bool = False, note: str = '') -> dict[str, Any]:
    problems = review_plan(plan)
    if problems:
        raise SceneError('Invalid scene plan: ' + '; '.join(problems))
    info = inspect_image(reference_image)
    image = Path(reference_image).resolve()
    target = Path(manifest_path).resolve()
    if target == image:
        raise SceneError("Anchor manifest must not overwrite reference image")
    payload = {
        'format_version': '1.0',
        'use_case_id': plan['use_case_id'],
        'plan_anchor_sha256': _plan_anchor_fingerprint(plan),
        'reference_image': os.path.relpath(image, target.parent),
        'reference_sha256': info['sha256'],
        'width': info['width'], 'height': info['height'],
        'approved_by_operator': bool(approved),
        'approval_note': note,
        'scene_anchor': plan['anchor'],
    }
    save_json(target, payload)
    return payload


def verify_anchor(manifest_path: str | Path, *, plan: dict[str, Any] | None = None, require_approved: bool = False) -> tuple[dict[str, Any], Path]:
    target = Path(manifest_path).resolve()
    try:
        payload = json.loads(target.read_text(encoding='utf-8'))
    except (ValueError, TypeError) as exc:
        raise SceneError('Anchor manifest is not valid JSON') from exc
    if not isinstance(payload, dict) or payload.get('format_version') != '1.0':
        raise SceneError('Unknown anchor manifest format')
    if type(payload.get('approved_by_operator')) is not bool:
        raise SceneError('Anchor approval must be a boolean')
    if require_approved and not payload['approved_by_operator']:
        raise SceneError('Reference image has not been explicitly approved by the operator')
    path_string = payload.get('reference_image')
    if not isinstance(path_string, str) or not path_string or Path(path_string).is_absolute():
        raise SceneError('Anchor reference_image must be a relative path')
    image_path = (target.parent / path_string).resolve()
    info = inspect_image(image_path)
    if info['sha256'] != payload.get('reference_sha256'):
        raise SceneError('Anchor reference image hash mismatch; regenerate/approve anchor after intentional edits')
    if [info['width'], info['height']] != [payload.get('width'), payload.get('height')]:
        raise SceneError('Anchor reference image dimensions changed')
    if plan is not None:
        problems = review_plan(plan)
        if problems:
            raise SceneError('Invalid scene plan: ' + '; '.join(problems))
        if payload.get('use_case_id') != plan.get('use_case_id'):
            raise SceneError('Anchor belongs to a different use case')
        if payload.get('plan_anchor_sha256') != _plan_anchor_fingerprint(plan):
            raise SceneError('Scene anchor changed; verify or create an updated reference manifest')
    return payload, image_path
