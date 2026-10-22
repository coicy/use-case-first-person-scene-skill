# Engineering Contract — Use Case Driven Software Concept Designer

## Current product authority (PRODUCT-002, 2026-10-22)

**Before any implementation or prompt change, read docs/PRODUCT_REQUIREMENTS.md and docs/V07_WORK_PLAN.md.** The project designs visual use-case concepts for **NEW, not-yet-built software and games**. Inventing missing interface arrangements, components and interactions is a REQUIRED design capability when labeled as an AI proposal; it is not automatically a hallucination. Confirmed user requirements override AI proposals; a proposal may not silently become locked. Existing software is a design reference, not the required replication target. Maintain the software-only output boundary of PRODUCT-001. Legacy v0.6 behaviors below remain compatibility constraints until explicitly migrated, not v0.7 product requirements.


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

## v0.7 WP-01 model and test contract

`src/ucscene/design/` is the current model layer for new products; four draft-2020-12 JSON Schemas under `schemas/` are its formal interface. The new CLI commands are `brief-init`, `design-scaffold`, `design-validate`, `migrate-legacy`. Preserve existing CLI contracts while extending the design layer. Do not allow AI-generated proposals to become approved/locked merely by creating a plan; explicit user decision evidence is mandatory and is still self-reported metadata until WP-03 establishes a controlled approval workflow. Preserve each source use-case action, flow, state, required evidence and exact UI labels. Reject structural conflicts with user hard constraints.

Test `tests/test_new_product_design.py`, two original-product fixtures in `benchmarks/new-products/`, existing offline tests, and CI Python 3.10/3.12. Refer to `docs/WP01_IMPLEMENTATION.md`. WP-02 UI design, image rendering for v0.7 bundles and cross-use-case visual consistency remain unimplemented.


## WP-02 engineering contract

- For original/new products, use `src/ucscene/design/planner.py`, not legacy existing-software screenshot copying.
- Preserve all user-supplied use-case actions, state, flows, visible evidence, required UI text and machine-readable hard constraints. Source facts and optional creative UI suggestions must remain separate.
- Every design candidate, decision and step interaction is `proposed`, never silently approved or locked; the explicit approval workflow is WP-03.
- Default design-plan runs offline deterministic heuristics. Paid AI ideation is only permitted via explicit `--ai`; CI must never call paid API.
- Schema, plan validation and prompt-hash replay are required. Tests cover original desktop and game projects, 2–3 variants, prompt tampering, exact hard constraints, machine-API mock, and backwards compatibility.
- A passing WP-02 model test does NOT prove live AI ideation quality or final image quality. Only WP-04 generates actual PNG concepts.


## WP-03 design-system safeguards (implemented)

- Treat `DesignPlan` as unapproved suggestions. Never issue `design-system-create --approve` without an actual user confirmation; test/CI must label mock approvals `CI-SYNTHETIC`.
- DesignSystem records approved choice, digest, revision, 3 effects, and optional lock. Metadata `approval.by=user` is a caller assertion, not identity verification.
- Preserve previously approved layout, navigation, visual style, common controls and information priority in new use case prompts, even when a future brief adds steps.
- Reject silent changes to structured hard constraints and frozen design keys. Locked changes require separate new approval and explicit `--override-lock`.
- Compare consecutive revisions with `design-system-diff`; mark related scenes for re-review. Do not claim it performs image regeneration.
- CI must run `tests/test_design_system.py` and CLI smoke tests. Keep WP-04 image-generation claims separate from WP-03 offline planning.


## WP-04 generation and visual acceptance gate
Use concept-packet then concept-render. One item is one full-bleed software/game frame of one use-case step, never a multi-panel storyboard or marketing board.
Paid calls require explicit --execute --max-images N plus API credentials. Do not claim visual pass from hash/mocked tests.
Cropped panels from multi-panel failures are external derivative samples, never six independent successful generations.
Only explicit user consent grants approval of product design decisions.
