"""ucscene command-line interface."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from .core import SceneError, build_plan, load_json, review_plan, save_json, validate_use_case
from .provider import ProviderError, generate_openai_image, edit_openai_image
from .extractor import extract_markdown
from .ai_extract import extract_with_ai
from .vision import review_image
from .anchors import create_anchor, verify_anchor
from .composite import compose_ui, compose_batch
from .imaging import inspect_image
from .benchmark import run_benchmark, export_benchmark_plans, make_prompt_lock, verify_prompt_lock
from .benchmark_human import rating_template, score_human_packet
from .acceptance import create_gallery, verify_gallery
from .design import (init_brief, migrate_legacy_case, create_bundle, validate_product_brief, validate_design_decision, validate_scene_design, validate_design_bundle)

def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ucscene", description="Use-case first-person scenario planning and image generation")
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="Extract source-backed use case from Markdown or arbitrary text")
    extract.add_argument("source")
    extract.add_argument("--out", default="out/extracted-use-case.json")
    extract.add_argument("--ai", action="store_true", help="Opt in to paid model-assisted extraction")
    extract.add_argument("--model", default="gpt-4.1-mini")
    for override in ("id", "title", "actor", "goal", "environment", "device"):
        extract.add_argument("--" + override)
    validate = sub.add_parser("validate", help="Validate a structured use case")
    validate.add_argument("use_case")
    plan_cmd = sub.add_parser("plan", help="Create a reproducible scene plan and prompts (offline)")
    plan_cmd.add_argument("use_case")
    plan_cmd.add_argument("--out", default="out/scene-plan.json")
    plan_cmd.add_argument("--step", action="append", dest="steps", default=None)
    review = sub.add_parser("review", help="Static checks for a scene plan")
    review.add_argument("plan")
    generate = sub.add_parser("generate", help="Generate actual PNGs through OpenAI Images API (requires key)")
    generate.add_argument("plan")
    generate.add_argument("--out", default="out/images")
    generate.add_argument("--model", default="gpt-image-1.5")
    generate.add_argument("--size", default="1536x1024")
    generate.add_argument("--quality", default="medium")
    generate.add_argument("--step", action="append", dest="steps", default=None)
    generate.add_argument("--reference-image", help="Apply the same reference image to all generated scenes")
    generate.add_argument("--chain", action="store_true", help="Edit every later scene using the previous generated scene as reference (potential drift)")
    generate.add_argument("--anchor", help="Approved, integrity-checked anchor manifest used as fixed reference for every scene")
    anchor_create = sub.add_parser("anchor-create", help="Write a reusable visual anchor manifest with image digest")
    anchor_create.add_argument("plan")
    anchor_create.add_argument("--image", required=True)
    anchor_create.add_argument("--out", required=True)
    anchor_create.add_argument("--approved", action="store_true", help="Record the operator's explicit visual approval")
    anchor_create.add_argument("--note", default="", help="Explain which reference details were manually verified")
    anchor_verify = sub.add_parser("anchor-verify", help="Verify anchor provenance, source integrity and optional plan compatibility")
    anchor_verify.add_argument("anchor")
    anchor_verify.add_argument("--plan")
    anchor_verify.add_argument("--require-approved", action="store_true")
    composite = sub.add_parser("compose-ui", help="Offline overlay of an exact UI screenshot in a normalized screen quadrilateral")
    composite.add_argument("--scene", required=True)
    composite.add_argument("--ui", required=True)
    composite.add_argument("--quad", required=True)
    composite.add_argument("--out", required=True)
    composite.add_argument("--report", help="Optional provenance JSON report")
    batch = sub.add_parser("compose-batch", help="Overlay per-step UI screenshots onto generated scenes (offline)")
    batch.add_argument("plan")
    batch.add_argument("--images", required=True, help="Directory containing generated scene PNGs")
    batch.add_argument("--map", required=True, help="JSON mapping from step ID to screenshot and quad")
    batch.add_argument("--out", required=True, help="Separate output directory for composited scenes")
    batch.add_argument("--strict", action="store_true", help="Require a mapping for every scene")
    bench = sub.add_parser("benchmark", help="Run offline sourced-project structural benchmark; optionally evaluate saved image audits")
    bench.add_argument("suite", help="A benchmark suite manifest JSON")
    bench.add_argument("--out", default="out/benchmark-report.json")
    bench.add_argument("--audits", help="Directory of review-image JSON results; must be paired with --images")
    bench.add_argument("--images", help="Directory of the matching actual scene PNGs; must be paired with --audits")
    bench.add_argument("--lock", help="Require byte-for-byte unchanged fixture and prompt fingerprints from an approved golden lock")
    bench_export = sub.add_parser("benchmark-export", help="Export per-case plans for generation and subsequent image auditing")
    bench_export.add_argument("suite")
    bench_export.add_argument("--out-dir", default="out/benchmark-plans")
    rating = sub.add_parser("benchmark-rating-template", help="Export empty 3-mode human image evaluation packet; does not rate anything")
    rating.add_argument("suite")
    rating.add_argument("--out", default="out/human-rating-template.json")
    score = sub.add_parser("benchmark-score", help="Verify actual image hashes and aggregate human-rated comparison")
    score.add_argument("suite")
    score.add_argument("--packet", required=True, help="Human-filled rating template JSON")
    score.add_argument("--images", required=True, help="Directory containing prompt-only/fixed-reference/sequential-chain image subfolders")
    score.add_argument("--out", default="out/human-score-report.json")
    bench_lock = sub.add_parser("benchmark-lock", help="Deliberately create or update the golden prompt lock after human review")
    bench_lock.add_argument("suite")
    bench_lock.add_argument("--out", required=True)
    accept = sub.add_parser("acceptance-gallery", help="Create offline reviewer gallery from real image files and official benchmark steps")
    accept.add_argument("suite")
    accept.add_argument("--selection", required=True, help="JSON mapping of scene ids to image files and explicitly identified origin")
    accept.add_argument("--images", required=True, help="Trusted directory containing actual image files")
    accept.add_argument("--out-dir", required=True, help="New output directory for an HTML gallery and hash manifest")
    acceptance_verify = sub.add_parser("acceptance-verify", help="Verify saved gallery asset hashes (NOT image semantics)")
    acceptance_verify.add_argument("manifest")
    inspect = sub.add_parser("review-image", help="Opt-in visual QA of a generated scene (paid vision API)")
    inspect.add_argument("plan")
    inspect.add_argument("--step", required=True)
    inspect.add_argument("--image", required=True)
    inspect.add_argument("--reference-image")
    inspect.add_argument("--model", default="gpt-4.1-mini")
    inspect.add_argument("--out", default="out/visual-audit.json")
    brief_init = sub.add_parser("brief-init", help="Initialize a new-product brief from a product prompt and one use case (offline)")
    brief_init.add_argument("--product-id", required=True)
    brief_init.add_argument("--name", required=True)
    brief_init.add_argument("--category", required=True, choices=["desktop", "web", "mobile", "game", "other"])
    brief_init.add_argument("--prompt", required=True)
    brief_init.add_argument("--use-case", required=True)
    brief_init.add_argument("--out", default="out/product-brief.json")
    migrate = sub.add_parser("migrate-legacy", help="Convert a v0.6 use case to an explicitly UNREVIEWED v0.7 ProductBrief")
    migrate.add_argument("use_case")
    migrate.add_argument("--product-id", required=True)
    migrate.add_argument("--name", required=True)
    migrate.add_argument("--category", default="other", choices=["desktop", "web", "mobile", "game", "other"])
    migrate.add_argument("--out", default="out/migrated-brief.json")
    design_check = sub.add_parser("design-validate", help="Validate a v0.7 ProductBrief, DesignDecision, UseCaseScene or DesignBundle")
    design_check.add_argument("document")
    design_check.add_argument("--kind", required=True, choices=["brief", "decision", "scene", "bundle"])
    design_scaffold = sub.add_parser("design-scaffold", help="Create UNRESOLVED scene skeletons, not final layouts or images")
    design_scaffold.add_argument("brief")
    design_scaffold.add_argument("--out", default="out/design-bundle.json")
    args = parser.parse_args(argv)
    try:
        if args.command == "brief-init":
            brief = init_brief(args.product_id, args.name, args.category, args.prompt, args.use_case)
            save_json(args.out, brief)
            print(json.dumps({"ok": True, "path": args.out, "unresolved": len(brief["unknowns"]), "approval": "none"}, ensure_ascii=False))
            return 0
        if args.command == "migrate-legacy":
            brief = migrate_legacy_case(load_json(args.use_case), product_id=args.product_id, name=args.name, category=args.category)
            save_json(args.out, brief)
            print(json.dumps({"ok": True, "path": args.out, "migrated_requirements": len(brief["requirements"]), "approval": "review-required"}, ensure_ascii=False))
            return 0
        if args.command == "design-validate":
            validators = {"brief": validate_product_brief, "decision": validate_design_decision,
                          "scene": validate_scene_design, "bundle": validate_design_bundle}
            validators[args.kind](load_json(args.document))
            print(json.dumps({"ok": True, "kind": args.kind, "path": args.document}, ensure_ascii=False))
            return 0
        if args.command == "design-scaffold":
            package = create_bundle(load_json(args.brief))
            save_json(args.out, package)
            print(json.dumps({"ok": True, "path": args.out, "scenes": len(package["scenes"]),
                              "design_status": "unresolved"}, ensure_ascii=False))
            return 0
        if args.command == "acceptance-gallery":
            packet = create_gallery(args.suite, args.selection, args.images, args.out_dir)
            print(json.dumps({"ok": True, "samples": packet["selected_samples"], "pending_human_review": True, "path": str(Path(args.out_dir) / "index.html")}, ensure_ascii=False))
            return 0
        if args.command == "acceptance-verify":
            packet = verify_gallery(args.manifest)
            print(json.dumps(packet, ensure_ascii=False))
            return 0
        if args.command == "benchmark-rating-template":
            packet = rating_template(args.suite)
            save_json(args.out, packet)
            print(json.dumps({"ok": True, "tasks": len(packet["ratings"]), "path": args.out}, ensure_ascii=False))
            return 0
        if args.command == "benchmark-score":
            report = score_human_packet(args.suite, args.packet, args.images)
            save_json(args.out, report)
            print(json.dumps({"ok": True, "rated": report["scored_reviews"], "paired": report["fully_paired_scene_rater_groups"], "path": args.out}, ensure_ascii=False))
            return 0
        if args.command == "benchmark-export":
            index = export_benchmark_plans(args.suite, args.out_dir)
            print(json.dumps({"ok": True, "cases": len(index["plans"]), "path": args.out_dir}, ensure_ascii=False))
            return 0
        if args.command == "benchmark-lock":
            report = run_benchmark(args.suite)
            save_json(args.out, make_prompt_lock(report))
            print(json.dumps({"ok": True, "locked_scenes": report["planned_scenes"], "path": args.out}, ensure_ascii=False))
            return 0
        if args.command == "benchmark":
            report = run_benchmark(args.suite, audits=args.audits, images=args.images)
            if args.lock:
                verify_prompt_lock(report, args.lock)
            save_json(args.out, report)
            print(json.dumps({"ok": report["static_pass"], "cases": report["cases"], "scenes": report["planned_scenes"], "evidence": report["checked_visible_evidence"], "visual": report["visual_evaluation"]["status"], "path": args.out}, ensure_ascii=False))
            return 0 if report["static_pass"] else 2
        if args.command == "extract":
            source = Path(args.source).read_text(encoding="utf-8")
            overrides = {key: getattr(args, key) for key in ("id", "title", "actor", "goal", "environment", "device") if getattr(args, key) is not None}
            case = extract_with_ai(source, model=args.model) if args.ai else extract_markdown(source, overrides=overrides)
            if args.ai:
                # Explicit overrides are manual operator decisions, applied only AFTER source verification.
                for key, value in overrides.items():
                    case[key] = value
                if overrides:
                    issues = [issue for issue in case["extraction"]["issues"]
                              if not any(issue == f"Missing source-backed {key}" for key in overrides)]
                    case["extraction"]["issues"] = issues
                    case["extraction"]["ready"] = not issues
                    case["extraction"]["manual_overrides"] = sorted(overrides)
                    if not issues:
                        validate_use_case(case)
            save_json(args.out, case)
            print(json.dumps({"ok": case["extraction"]["ready"], "path": args.out, "issues": case["extraction"]["issues"]}, ensure_ascii=False))
            return 0 if case["extraction"]["ready"] else 3
        elif args.command == "validate":
            data = validate_use_case(load_json(args.use_case))
            print(json.dumps({"ok": True, "id": data["id"], "steps": len(data["steps"])}, ensure_ascii=False))
        elif args.command == "plan":
            result = build_plan(load_json(args.use_case), args.steps)
            save_json(args.out, result)
            print(json.dumps({"ok": True, "path": args.out, "scenes": len(result["scenes"])}, ensure_ascii=False))
        elif args.command == "review":
            errors = review_plan(load_json(args.plan))
            print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
            return 2 if errors else 0
        elif args.command == "anchor-create":
            anchor = create_anchor(load_json(args.plan), args.image, args.out, approved=args.approved, note=args.note)
            print(json.dumps({"ok": True, "path": args.out, "approved": anchor["approved_by_operator"], "reference_sha256": anchor["reference_sha256"]}, ensure_ascii=False))
        elif args.command == "anchor-verify":
            anchor, image_path = verify_anchor(args.anchor, plan=load_json(args.plan) if args.plan else None, require_approved=args.require_approved)
            print(json.dumps({"ok": True, "approved": anchor["approved_by_operator"], "reference_image": str(image_path)}, ensure_ascii=False))
        elif args.command == "compose-ui":
            result = compose_ui(args.scene, args.ui, args.quad, args.out, report_path=args.report)
            print(json.dumps({"ok": True, "path": args.out, "output_sha256": result["output_sha256"], "report": args.report}, ensure_ascii=False))
        elif args.command == "compose-batch":
            report = compose_batch(load_json(args.plan), args.images, args.map, args.out, strict=args.strict)
            print(json.dumps({"ok": True, "images": len(report["items"]), "unmapped": report["unmapped_step_ids"], "path": str(Path(args.out) / "composition-report.json")}, ensure_ascii=False))
        elif args.command == "generate":
            p = load_json(args.plan)
            problems = review_plan(p)
            if problems:
                raise SceneError("Plan does not pass review: " + "; ".join(problems))
            if args.steps:
                known = {s["step_id"] for s in p["scenes"]}
                unknown = set(args.steps) - known
                if unknown:
                    raise SceneError("Unknown step(s): " + ", ".join(sorted(unknown)))
            scenes = [s for s in p["scenes"] if not args.steps or s["step_id"] in args.steps]
            if not scenes:
                raise SceneError("No matching scenes")
            if args.chain and args.steps:
                raise SceneError("--chain requires an ordered full plan; omit --step")
            if args.chain and args.reference_image:
                raise SceneError("Choose --reference-image or --chain, not both")
            if args.anchor and (args.chain or args.reference_image):
                raise SceneError("--anchor is exclusive with --reference-image and --chain")
            approved_anchor = None
            verified_reference = None
            if args.anchor:
                approved_anchor, verified_reference = verify_anchor(args.anchor, plan=p, require_approved=True)
            if args.reference_image:
                # Fail missing/invalid reference BEFORE any paid image API calls.
                inspect_image(args.reference_image)
            report = []
            previous_image = None
            for s in scenes:
                safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", s["id"]).strip("._")
                if not safe_id:
                    raise SceneError("Unsafe empty scene file name")
                path = Path(args.out) / (safe_id + ".png")
                source_reference = str(verified_reference) if verified_reference else args.reference_image or (str(previous_image) if args.chain and previous_image else None)
                if source_reference:
                    item = edit_openai_image(s["prompt"], source_reference, path, model=args.model, size=args.size, quality=args.quality)
                else:
                    item = generate_openai_image(s["prompt"], path, model=args.model, size=args.size, quality=args.quality)
                previous_image = path
                report.append({"scene_id": s["id"], "prompt_sha256": s["prompt_sha256"], **item})
                print("Generated:", item["path"], file=sys.stderr)
            save_json(Path(args.out) / "generation-report.json", {"images": report, "continuity_mode": "verified-manifest-anchor" if args.anchor else "fixed-reference" if args.reference_image else "sequential-chain" if args.chain else "prompt-only", "anchor_reference_sha256": approved_anchor["reference_sha256"] if approved_anchor else None, "warning": "Visual continuity is not guaranteed. Use review-image and inspect manually. Compositing exact UI screenshots is available offline with compose-ui."})
            print(json.dumps({"ok": True, "images": len(report)}, ensure_ascii=False))
        elif args.command == "review-image":
            p = load_json(args.plan)
            issues = review_plan(p)
            if issues:
                raise SceneError("Invalid plan: " + "; ".join(issues))
            matching = [s for s in p["scenes"] if s["step_id"] == args.step]
            if len(matching) != 1:
                raise SceneError(f"Unknown or duplicate step: {args.step}")
            report = review_image(matching[0], args.image, anchor=p.get("anchor", {}), reference_image=args.reference_image, model=args.model)
            save_json(args.out, report)
            print(json.dumps({"ok": report["passed"], "path": args.out, "method": report["method"]}, ensure_ascii=False))
            return 0 if report["passed"] else 4
    except (SceneError, ProviderError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    return 0

def main() -> None:
    raise SystemExit(run())

if __name__ == "__main__":
    main()
