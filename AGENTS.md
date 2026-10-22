# Engineering Contract — Use Case First-Person Scene Skill

## Scope

This repository implements a source-grounded **software-only** use-case-to-scene pipeline. The entire output must be application/editor/game pixels; never real-world user POV, external monitors, keyboard, desk, device or physical surroundings. It is **not** a UML generator, working UX frontend, asset licensing system, or guarantee of model accuracy. Do not add features or claims to the README unless the code and tests verify them.

## Architecture and data provenance

- `src/ucscene/extractor.py`, `ai_extract.py`: conservative text-to-use-case extraction. AI outputs must carry literal source evidence; keep unready drafts blocked.
- `src/ucscene/core.py`: input validation and deterministic scene prompts, hashes, step-to-source ID mapping. No network.
- `src/ucscene/anchors.py`: manifest creation, image digest check, plan-bound scene anchor fingerprint, operator approval gate. Not a cryptographic signature or image correctness certification.
- `src/ucscene/imaging.py`: optional local Pillow image inspection; enforce file size, format and reasonable dimensions.
- `src/ucscene/composite.py`: optional offline optional geometric UI overlay INSIDE application/game content and preflighted batch processing. UI is supplied, never inferred or generated; composition into physical screen photos is outside project scope. If the quadrilateral is bad, fail before writing output.
- `src/ucscene/provider.py`, `responses.py`: online image generation / edit and vision requests only through explicit CLI commands. Keep credentials in environment and never print raw server content.
- `src/ucscene/vision.py`: advisory machine visual QA. It is not an authoritative pass condition without human inspection.
- `src/ucscene/cli.py`: user-visible commands with stable argument contracts, actionable non-secret errors.
- `examples/` and `tests/`: scenarios and test assets are intentionally synthetic unless explicitly attributed.

## Required behaviors

1. Python >=3.10. Core functionality uses standard library. Perspective composition and verified anchors require `.[ui]` (Pillow), which must be listed in `pyproject.toml`.
2. No generated image or visual reference may depict a user operating software or an external device; only pixels INSIDE software or games. CLI must never silently make paid model requests. Unit tests/CI mock all provider traffic.
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

## v0.5 hard boundary / regression gate

- Default `viewpoint_mode=application-ui`, alternate `gameplay`; the `game_camera` preserves in-game isometric/first-person/other view, never forces human-eye POV.
- Former `physical-user` and `avatar-eyes` inputs are rejected with migration instructions. All old plans and prompt locks must be regenerated and reviewed.
- The entire image must be in-software content: an image of a physical display with valid app content is STILL INVALID.
- `device` is deprecated optional source metadata and may not cause monitors/hands/phones to be rendered.
- The benchmark suite, acceptance visuals, test fixtures, and evaluator must apply this definition. Do not reuse v0.4 device-shot demos as valid acceptance.
- If introducing a new demo, it must show direct interface/game pixels, not someone standing or sitting in front of a screen.


## Additional v0.6 quality gates

- Acceptance galleries use actual decoded image bytes, relative safe paths, per-image origin, and SHA-256 integrity manifests.
- An offline gallery cannot assign image quality or claim a human verdict. The user enters acceptance decisions in the HTML review UI and exports them separately.
- Distinguish benchmark reference prompts from the prompts actually used by external image generators; never infer equivalence.
- Carry forward only sourced software state from earlier use-case steps (`carry_forward`), so later screenshots retain object/node/class identity.
- A generated editor-looking image is never an official application screenshot unless provenance proves a real application capture.
