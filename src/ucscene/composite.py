"""Offline screen overlay: perspective-map a real UI screenshot to a device quadrilateral.

This preserves the supplied UI image as a resampled asset. It makes no claim that
its contents represent executable software or that the screen quad is correctly
located: these are operator-specified inputs.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .core import SceneError, save_json
from .imaging import _pillow, inspect_image


def load_quad(path: str | Path) -> list[list[float]]:
    try:
        spec = json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise SceneError('Screen quad JSON could not be read') from exc
    if not isinstance(spec, dict) or spec.get('coordinate_system') != 'normalized' or not isinstance(spec.get('points'), list):
        raise SceneError('Screen quad needs coordinate_system=normalized and points')
    points = spec['points']
    if len(points) != 4:
        raise SceneError('Screen quad must have four points in TL, TR, BR, BL order')
    for p in points:
        if not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
            raise SceneError('Screen points must be finite normalized x/y pairs in [0, 1]')
    # Convexity and expected image-coordinate clockwise order. Reject bow ties.
    cross = []
    for i in range(4):
        a, b, c = points[i], points[(i+1)%4], points[(i+2)%4]
        cross.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
    if min(cross) <= 0.000001:
        raise SceneError('Quad is degenerate, inverted or self-intersecting; expected TL, TR, BR, BL')
    area = sum(points[i][0]*points[(i+1)%4][1]-points[(i+1)%4][0]*points[i][1] for i in range(4))/2
    if area < 0.001:
        raise SceneError('Screen quad is too small')
    return [[float(v) for v in p] for p in points]


def _solve(rows: list[list[float]], values: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting for 8 homography coefficients."""
    n = len(values)
    augmented = [list(row) + [float(v)] for row, v in zip(rows, values)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(augmented[i][col]))
        if abs(augmented[pivot][col]) < 1e-9:
            raise SceneError('Screen quad leads to singular perspective transform')
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        factor = augmented[col][col]
        augmented[col] = [v / factor for v in augmented[col]]
        for other in range(n):
            if other != col:
                scale = augmented[other][col]
                augmented[other] = [a - scale*b for a, b in zip(augmented[other], augmented[col])]
    return [row[-1] for row in augmented]


def _inverse_homography(points: list[tuple[float, float]], width: int, height: int) -> list[float]:
    src = [(0., 0.), (float(width-1), 0.), (float(width-1), float(height-1)), (0., float(height-1))]
    rows: list[list[float]] = []
    vals: list[float] = []
    for (x, y), (u, v) in zip(points, src):
        rows.append([x, y, 1, 0, 0, 0, -u*x, -u*y])
        vals.append(u)
        rows.append([0, 0, 0, x, y, 1, -v*x, -v*y])
        vals.append(v)
    return _solve(rows, vals)


def compose_ui(scene_path: str | Path, ui_path: str | Path, quad_path: str | Path, output_path: str | Path, *, report_path: str | Path | None = None) -> dict[str, Any]:
    Image, ImageOps, ImageDraw, ImageChops = _pillow()
    output = Path(output_path).resolve()
    if output in {Path(scene_path).resolve(), Path(ui_path).resolve(), Path(quad_path).resolve()}:
        raise SceneError('Output must not overwrite the source scene, UI screenshot, or quad specification')
    scene_info = inspect_image(scene_path)
    ui_info = inspect_image(ui_path)
    points = load_quad(quad_path)
    try:
        with Image.open(scene_path) as source:
            scene = ImageOps.exif_transpose(source).convert('RGBA')
        with Image.open(ui_path) as source:
            ui = ImageOps.exif_transpose(source).convert('RGBA')
        if scene.size != (scene_info['width'], scene_info['height']) or ui.size != (ui_info['width'], ui_info['height']):
            raise SceneError('EXIF-rotated image dimensions differ; normalize orientation before compositing')
        polygon = [(x * (scene.width-1), y * (scene.height-1)) for x, y in points]
        coefficients = _inverse_homography(polygon, ui.width, ui.height)
        warped = ui.transform(scene.size, Image.Transform.PERSPECTIVE, coefficients, resample=Image.Resampling.BICUBIC, fillcolor=(0,0,0,0))
        clip = Image.new('L', scene.size, 0)
        ImageDraw.Draw(clip).polygon(polygon, fill=255)
        warped.putalpha(ImageChops.multiply(warped.getchannel('A'), clip))
        result = Image.alpha_composite(scene, warped).convert('RGB')
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.save(output, format='PNG')
    except (OSError, ValueError) as exc:
        raise SceneError('Failed to composite UI image') from exc
    report = {
        'method': 'offline-perspective-overlay',
        'scene_sha256': scene_info['sha256'],
        'ui_sha256': ui_info['sha256'],
        'screen_quad_sha256': hashlib.sha256(Path(quad_path).read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'output': str(output), 'normalized_quad': points,
        'warning': 'Supplied UI screenshot is perspective-resampled, not synthesized. Screen placement is user-specified and not automatically verified; UI image does not prove implemented behavior.',
    }
    if report_path is not None:
        save_json(report_path, report)
    return report


def compose_batch(plan: dict[str, Any], images_dir: str | Path, mapping_path: str | Path, output_dir: str | Path, *, strict: bool = False) -> dict[str, Any]:
    """Offline UI overlays for selected steps in a multi-step use-case plan.

    Source assets and geometry are fully preflighted before output is written.
    Unmapped steps are skipped by default; strict requires every step mapped.
    """
    import re
    from .core import review_plan

    faults = review_plan(plan)
    if faults:
        raise SceneError('Invalid scene plan: ' + '; '.join(faults))
    mapping_file = Path(mapping_path).resolve()
    try:
        mapping = json.loads(mapping_file.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise SceneError('Invalid UI mapping file') from exc
    if not isinstance(mapping, dict) or mapping.get('format_version') != '1.0' or not isinstance(mapping.get('screens'), dict):
        raise SceneError('UI map must have format_version=1.0 and a screens object')
    available = {s['step_id']: s for s in plan['scenes']}
    unexpected = set(mapping['screens']) - set(available)
    if unexpected:
        raise SceneError('UI map has unknown step IDs: ' + ', '.join(sorted(unexpected)))
    missing = set(available) - set(mapping['screens'])
    if strict and missing:
        raise SceneError('Missing UI screenshot mapping for steps: ' + ', '.join(sorted(missing)))
    jobs = []
    target_names = set()
    for step_id in available:
        if step_id not in mapping['screens']:
            continue
        entry = mapping['screens'][step_id]
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key] for key in ('ui', 'quad')):
            raise SceneError('Mapping entry for ' + step_id + ' requires ui and quad paths')
        scene_id = available[step_id]['id']
        name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', scene_id).strip('._')
        if not name or name in target_names:
            raise SceneError('Non-unique or unsafe output name for scene: ' + scene_id)
        target_names.add(name)
        scene = Path(images_dir) / (name + '.png')
        ui = (mapping_file.parent / entry['ui']).resolve()
        quad = (mapping_file.parent / entry['quad']).resolve()
        inspect_image(scene)
        inspect_image(ui)
        load_quad(quad)
        jobs.append((step_id, scene, ui, quad, name))
    if not jobs:
        raise SceneError('No mapped scenes to compose')
    output = Path(output_dir)
    assets = []
    for step_id, scene, ui, quad, name in jobs:
        item = compose_ui(scene, ui, quad, output / (name + '-ui.png'))
        assets.append({'step_id': step_id, **item})
    report = {
        'format_version': '1.0', 'method': 'offline-ui-batch',
        'use_case_id': plan['use_case_id'],
        'items': assets,
        'unmapped_step_ids': sorted(missing),
        'warning': 'Overlay coordinates are user-specified and require visual inspection; no runtime UI functionality is verified.',
    }
    save_json(output / 'composition-report.json', report)
    return report
