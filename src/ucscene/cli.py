"""ucscene command-line interface."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from .core import SceneError, build_plan, load_json, review_plan, save_json, validate_use_case
from .provider import ProviderError, generate_openai_image

def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ucscene", description="Use-case first-person scenario planning and image generation")
    sub = parser.add_subparsers(dest="command", required=True)
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
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
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
            report = []
            for s in scenes:
                safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", s["id"]).strip("._")
                if not safe_id:
                    raise SceneError("Unsafe empty scene file name")
                path = Path(args.out) / (safe_id + ".png")
                item = generate_openai_image(s["prompt"], path, model=args.model, size=args.size, quality=args.quality)
                report.append({"scene_id": s["id"], "prompt_sha256": s["prompt_sha256"], **item})
                print("Generated:", item["path"], file=sys.stderr)
            save_json(Path(args.out) / "generation-report.json", {"images": report, "warning": "Generated images have not been visually reviewed for strict first-person compliance or accurate UI text."})
            print(json.dumps({"ok": True, "images": len(report)}, ensure_ascii=False))
    except (SceneError, ProviderError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    return 0

def main() -> None:
    raise SystemExit(run())

if __name__ == "__main__":
    main()
