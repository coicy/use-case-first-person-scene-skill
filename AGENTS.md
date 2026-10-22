# Engineering Contract — Use Case First-Person Scene Skill

## Scope

This repository implements a source-grounded use-case-to-first-person scene pipeline. It is **not** a UML generator, working UX frontend, asset licensing system, or guarantee of model accuracy. Do not add features or claims to the README unless the code and tests verify them.

## Architecture and data provenance

- `src/ucscene/extractor.py`, `ai_extract.py`: conservative text-to-use-case extraction. AI outputs must carry literal source evidence; keep unready drafts blocked.
- `src/ucscene/core.py`: input validation and deterministic scene prompts, hashes, step-to-source ID mapping. No network.
- `src/ucscene/anchors.py`: manifest creation, image digest check, plan-bound scene anchor fingerprint, operator approval gate. Not a cryptographic signature or image correctness certification.
- `src/ucscene/imaging.py`: optional local Pillow image inspection; enforce file size, format and reasonable dimensions.
- `src/ucscene/composite.py`: optional offline perspective UI overlay and preflighted batch processing. UI is supplied, never inferred or generated. If the quadrilateral is bad, fail before writing output.
- `src/ucscene/provider.py`, `responses.py`: online image generation / edit and vision requests only through explicit CLI commands. Keep credentials in environment and never print raw server content.
- `src/ucscene/vision.py`: advisory machine visual QA. It is not an authoritative pass condition without human inspection.
- `src/ucscene/cli.py`: user-visible commands with stable argument contracts, actionable non-secret errors.
- `examples/` and `tests/`: scenarios and test assets are intentionally synthetic unless explicitly attributed.

## Required behaviors

1. Python >=3.10. Core functionality uses standard library. Perspective composition and verified anchors require `.[ui]` (Pillow), which must be listed in `pyproject.toml`.
2. CLI must never silently make paid model requests. Unit tests/CI mock all provider traffic.
3. Any plan must preserve use-case step IDs, visible evidence and stable hashes. A draft without source-backed core fields must be rejected.
4. Visual anchors should preserve both the approved source file digest and the plan metadata fingerprint; mismatches fail before paid generation.
5. Operators choose perspective polygons; only convex, normalized TL/TR/BR/BL points are accepted. Never claim pixels have been perfectly preserved after warping.
6. Batch composition validates all required source files and geometry before producing outputs, and produces SHA256-based provenance reports.
7. Use stable output paths, with input assets and generated assets separated. Protect secrets and sensitive screenshots.
8. Changes to CLI/schema/manifest contracts need compatible docs and regression tests. If a breaking change is needed, update version and migration instructions.

## Acceptance checks

```bash
python -m pip install -e '.[ui]'
python -m unittest discover -s tests -v
ucscene validate examples/warehouse-scan.json
ucscene extract examples/warehouse-scan.md --out /tmp/case.json
ucscene plan /tmp/case.json --out /tmp/plan.json
ucscene review /tmp/plan.json
python examples/make_demo_assets.py
ucscene compose-ui --scene out/demo/scene.png --ui out/demo/ui.png --quad examples/screen-quad.demo.json --out out/demo/composited.png
```

The GitHub Actions workflow must pass Python 3.10 and 3.12. Do not claim real API image-generation compatibility or cross-scene visual fidelity from mocked tests; report unverified API integration honestly.

- Human visual rating packet records are never populated by Agent defaults or fabricated scores; each scored record requires actual image bytes, strict digest integrity, and a human rater ID. `benchmark-score` must not perform model inference.
