"""Offline visual acceptance gallery with strict provenance and no fabricated ratings.

Image creation, content inspection, and the user's sign-off are separate stages.
The generated HTML is an offline *review interface*, never an approval record.
"""
from __future__ import annotations

from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
from typing import Any

from .benchmark import run_benchmark
from .core import SceneError, build_plan, load_json, save_json
from .imaging import inspect_image

ALLOWED_ORIGINS = {
    "conversation-image-generation", "ucscene-cli", "external-image-model",
    "app-runtime-screenshot", "manually-composited",
}
MAX_ENTRIES = 100


def _safe_relative(source_dir: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise SceneError("Image path must be nonempty")
    part = Path(raw)
    if part.is_absolute() or not part.parts or any(x in (".", "..") for x in part.parts):
        raise SceneError("Image paths must be relative to --images and cannot traverse directories")
    root = source_dir.resolve()
    path = (root / part).resolve()
    if not path.is_relative_to(root):
        raise SceneError("Image resolves outside --images directory")
    if not path.is_file():
        raise SceneError(f"Image does not exist: {raw}")
    return path


def create_gallery(suite_path: str | Path, selection_path: str | Path, images_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Validate actual image bytes, then generate a self-contained local reviewer gallery.

    selection JSON: {"samples": [{"scene_id":..., "image": relative PNG path,
      "origin": one of ALLOWED_ORIGINS, "notes": optional description}]}
    """
    suite_path = Path(suite_path)
    suite = load_json(suite_path)
    bench = run_benchmark(suite_path)
    if not bench["static_pass"]:
        raise SceneError("Benchmark suite structural audit failed")
    selection = load_json(selection_path)
    entries = selection.get("samples")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_ENTRIES:
        raise SceneError("Selection must contain between 1 and 100 samples")
    case_info = {}
    for case in suite["cases"]:
        source = (suite_path.parent / case["file"]).resolve()
        if not source.is_relative_to(suite_path.parent.resolve()):
            raise SceneError("Unsafe benchmark fixture location")
        data = load_json(source)
        plan = build_plan(data)
        for scene in plan["scenes"]:
            case_info[scene["id"]] = {
                "project": case["project"], "title": data["title"],
                "use_case_id": data["id"], "step_id": scene["step_id"],
                "step_action": scene["action"], "evidence": scene["evidence"],
                "prompt_sha256": scene["prompt_sha256"],
                "viewpoint_mode": plan["anchor"]["viewpoint_mode"],
                "game_camera": plan["anchor"].get("game_camera", "documented"),
                "source_urls": [s["url"] for s in case["official_sources"]],
            }
    source_dir = Path(images_dir)
    output_dir = Path(output_dir)
    dest_root = output_dir.resolve()
    if dest_root == source_dir.resolve() or dest_root.is_relative_to(source_dir.resolve()):
        raise SceneError("Output directory must not be inside the source image directory")
    ready = []
    seen = set()
    for i, item in enumerate(entries):
        if not isinstance(item, dict):
            raise SceneError(f"samples[{i}] must be an object")
        scene_id = item.get("scene_id")
        if not isinstance(scene_id, str) or scene_id not in case_info:
            raise SceneError(f"Unknown scene id in samples[{i}]: {scene_id!r}")
        if scene_id in seen:
            raise SceneError(f"Duplicate image scene id: {scene_id}")
        seen.add(scene_id)
        origin = item.get("origin")
        if origin not in ALLOWED_ORIGINS:
            raise SceneError(f"Invalid or undisclosed image origin for {scene_id}")
        original_prompt_hash = item.get("generation_prompt_sha256")
        if original_prompt_hash is not None and (not isinstance(original_prompt_hash, str) or len(original_prompt_hash) != 64 or any(c not in "0123456789abcdef" for c in original_prompt_hash)):
            raise SceneError("generation_prompt_sha256 must be an actual lowercase SHA-256 digest")
        if origin == "ucscene-cli" and original_prompt_hash != case_info[scene_id]["prompt_sha256"]:
            raise SceneError("ucscene-cli claims require a matching generation_prompt_sha256")
        notes = item.get("notes", "")
        if not isinstance(notes, str):
            raise SceneError("notes must be a string")
        if len(notes) > 1000:
            raise SceneError("notes must be 1000 characters or fewer")
        src = _safe_relative(source_dir, item.get("image"))
        meta = inspect_image(src)
        ext = src.suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise SceneError("Image file extension must match a supported raster image")
        ready.append({**case_info[scene_id], "scene_id": scene_id, "image": f"images/sample-{i+1:02d}{ext}",
                      "origin": origin, "operator_notes": notes,
                      "generation_prompt_sha256": original_prompt_hash,
                      "generation_prompt_match": ("not_verified" if original_prompt_hash is None else
                                                   "matched" if original_prompt_hash == case_info[scene_id]["prompt_sha256"] else "different"),
                      "image_sha256": meta["sha256"],
                      "width": meta["width"], "height": meta["height"], "bytes": meta["bytes"],
                      "_source": src})
    images_out = output_dir / "images"
    images_out.mkdir(parents=True, exist_ok=True)
    for row in ready:
        shutil.copyfile(row["_source"], output_dir / row["image"])
        del row["_source"]
    manifest = {
        "format_version": "1.0", "suite_id": bench["suite_id"], "suite_sha256": bench["suite_sha256"],
        "source_selection_sha256": hashlib.sha256(Path(selection_path).read_bytes()).hexdigest(),
        "origin_policy": "explicit per-image origin; benchmark prompt hashes are references and NOT proof of image-generating prompts",
        "visual_verdict": "user_review_pending", "all_images_verified": True,
        "partial_selection": len(ready) != bench["planned_scenes"],
        "selected_samples": len(ready), "suite_planned_scenes": bench["planned_scenes"],
        "samples": ready,
        "warning": "Images and hashes are real, but no automated score proves visual accuracy. The HTML page collects separate human review. No app runtime is asserted unless origin is app-runtime-screenshot.",
    }
    save_json(output_dir / "manifest.json", manifest)
    (output_dir / "index.html").write_text(_render_html(manifest), encoding="utf-8")
    return manifest


def verify_gallery(manifest_path: str | Path) -> dict[str, Any]:
    """Detect missing or replaced image assets; never adjudicate their visual content."""
    manifest = load_json(manifest_path)
    if manifest.get("format_version") != "1.0" or not isinstance(manifest.get("samples"), list):
        raise SceneError("Unsupported acceptance manifest")
    root = Path(manifest_path).resolve().parent
    checked = 0
    for row in manifest["samples"]:
        path = _safe_relative(root, row.get("image"))
        meta = inspect_image(path)
        if meta["sha256"] != row.get("image_sha256") or meta["width"] != row.get("width") or meta["height"] != row.get("height"):
            raise SceneError(f"Image asset changed: {row.get('scene_id')}")
        checked += 1
    return {"ok": True, "image_integrity_verified": checked, "visual_verdict": "not_checked", "user_approval": "not_checked"}


def _render_html(manifest: dict[str, Any]) -> str:
    cards = []
    for row in manifest["samples"]:
        title = escape(row["project"] + " · " + row["step_id"])
        meta = escape(row["step_action"])
        evidences = "".join("<li>" + escape(e) + "</li>" for e in row["evidence"])
        camera = escape(row["viewpoint_mode"] + (" / " + row["game_camera"] if row["viewpoint_mode"] == "gameplay" else ""))
        src = escape(row["image"], quote=True)
        sid = escape(row["scene_id"], quote=True)
        notes = escape(row["operator_notes"])
        prompt_match = escape(row["generation_prompt_match"])
        cards.append(f'''<article data-scene="{sid}"><h2>{title}</h2><div class="sub">{meta}</div>
<img src="{src}" alt="{title} software-only generated image" loading="lazy">
<small>视角: {camera} · 来源: {escape(row["origin"])} · 图片 SHA256: {escape(row["image_sha256"][:16])}… · 生成提示词匹配: {prompt_match}</small>
<details><summary>原用例画面证据</summary><ul>{evidences}</ul><p>{notes}</p></details>
<label>用户验收结论 <select class="verdict"><option value="pending">待评</option><option value="pass">通过</option><option value="fail">需修改</option><option value="uncertain">不确定</option></select></label>
<label>详细意见 <textarea class="comment" placeholder="核查软件边界、用例证据、UI 正确性、产品还原度；记录原因"></textarea></label></article>''')
    # All text interpolated in HTML is escaped; the JSON ID is only written into a data attribute.
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>软件内场景 · 真实图片验收</title>
<style>:root{color-scheme:dark}body{font-family:system-ui,-apple-system,sans-serif;background:#10141e;color:#eaf0fa;margin:0}main{max-width:1180px;margin:24px auto;padding:0 18px}h1{font-size:26px}p{line-height:1.7}.notice{padding:12px 18px;background:#263143;border-left:3px solid #8cb2f7}#cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;margin-top:20px}article{border:1px solid #3a4659;border-radius:12px;padding:14px;background:#19212e;min-width:0}article img{width:100%;height:auto;aspect-ratio:16/9;object-fit:contain;background:#0c1119;border-radius:8px;margin:10px 0}article h2{font-size:18px;margin:4px 0}.sub,small{color:#b9c6d8;font-size:13px;display:block}summary{cursor:pointer;margin-top:8px}label{display:block;margin-top:14px;font-size:14px}select,textarea{box-sizing:border-box;width:100%;padding:10px;margin-top:6px;border-radius:6px;background:#111927;color:#fff;border:1px solid #4e5a6c}textarea{min-height:88px}button{background:#a2c4ff;color:#0f1625;border:0;border-radius:8px;padding:12px 18px;font-weight:bold;cursor:pointer;margin:16px 0}footer{margin:24px 0;color:#a9b9ce}</style></head><body><main>
<h1>软件内部场景 · 图片验收</h1><p class="notice">所有图片均绑定原用例步骤和文件哈希。画面不等于软件真实运行结果；评分必须由验收者自行完成。本地 HTML 不发送数据，使用“导出意见”保存 JSON。请先核查是否出现真实显示器、用户、桌面或其他软件外内容，再检查步骤证据、UI 和产品特征。</p>
<p id="count">等待逐图验收</p><button type="button" id="export">导出用户验收意见 JSON</button><section id="cards">''' + "\n".join(cards) + '''</section><footer>Software-only scene benchmark · offline gallery. 视觉结论由用户提供，图片哈希不能保证语义正确。</footer></main>
<script>document.getElementById('export').addEventListener('click',()=>{const rows=[...document.querySelectorAll('article[data-scene]')].map(card=>({scene_id:card.dataset.scene,verdict:card.querySelector('.verdict').value,comment:card.querySelector('.comment').value}));const data={format_version:'1.0',method:'user-entered-manual-review',created_at:new Date().toISOString(),reviews:rows};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='user-visual-review.json';a.click();URL.revokeObjectURL(u)});</script></body></html>'''
