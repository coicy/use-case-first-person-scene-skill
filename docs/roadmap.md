# Product Roadmap

## Implemented — v0.1.0

- Structured use-case JSON to reproducible first-person scene prompts and step-specific evidence.
- Optional image-generation provider and offline tests.

## Implemented — v0.2.0

- Bilingual structured Markdown input; opt-in AI free-prose extraction with source quote checks.
- Fixed-reference/chain image edits, model-assisted POV/evidence review (advisory).

## Implemented — v0.3.0

- Explicitly human-approved, use-case-bound reference image manifests with SHA-256 file integrity checks.
- Offline perspective mapping of a **real provided UI screenshot** into four user-chosen screen corners on any generated scene; pixel preservation outside in-software overlay quad.
- Batch per-step screenshots, input preflight, provenance reports and a completely offline reproducible demonstration.
- Python optional Pillow extra, CI matrix and offline tests for anchors, composition and invalid inputs.

## Not yet implemented (candidates for v0.4 and beyond)

- Automatic detection/interactive editing of software-internal panels and HUD regions; no physical-device screen mapping.
- Source-aware Markdown/PRD references with filename and line-level traceability.
- Specialized game/editor/warehouse/POS archetypes with empirically evaluated prompt libraries.
- End-to-end real API acceptance suite using a limited authorized test budget.
- Repeatable quantitative comparison of visual anchor fidelity and multi-step visual consistency.
- Batch visual QA with independent reviewers, cost ceilings, image regeneration on targeted errors.
- Diff-based regeneration and repository CI for changing requirements/assets.

## Non-goals / limitations

- No guarantee a model's images follow the requested camera geometry.
- Approved reference manifests express a human assertion, not independent certification or tamper-resistant signature.
- Composited UI screenshots do not establish functional correctness; tiny text may become unreadable after resampling.
- Generated imagery must not replace executable acceptance tests.

## v0.4 — Retired real-world camera semantics (historical only; superseded by v0.5)

- Official-doc-curated cases for VS Code, Blender, GIMP, Godot, OpenTTD, and Luanti.
- Former physical-user/avatar-eyes semantics are deprecated; old external-device visuals must not be reused as acceptance.
- Offline source-traceability checks, deterministic golden prompt lock, case plan export, optional provenance-verified audit aggregation.
- Still requires real paid image sampling and blinded human ratings before any claim that fixed anchors or chain editing actually improve image quality.


## v0.4 — Historical evaluation protocol (old physical framing invalid)

- Source-referenced public UI/game cases (VS Code, Blender, GIMP, Godot, OpenTTD, Luanti).
- Old real-user-device camera distinction is retired; software-only application/game views supersede it.
- Golden prompt hashes; offline CI-based source/scene integrity and export.
- Real-image 3-arm manual rating packet and digest-bound human score aggregation.
- No valid generation-quality scores until real images and reviewed scores are available.

## v0.5 — authoritative user correction (implemented)

- All output frames are **software-only**; realistic operator environments and physical displays are explicitly excluded.
- `application-ui`/`gameplay` and explicit in-game camera semantics replace `physical-user`/`avatar-eyes`.
- Deprecated input modes and old plans rejected; all six benchmark fixtures, prompt lock and docs migrated.
- Vision QA now explicitly checks `software_only`, with physical content as a failure.
- Perspective UI overlay is a legacy/general image operation for software-internal surfaces only, not the default render pipeline.


## v0.6 completed

- Software-only six-project offline acceptance gallery that binds generated images to source use-case scene IDs, original source URLs, reference prompt hashes, and actual image hashes.
- An HTML review page that records explicit user verdicts; no fake visual passing score.
- Per-image source provenance; external images are never claimed to be made with CLI prompts.
- Evidence-backed state carryover for multi-step UI operations, fixing the Godot RigidBody2D vs CharacterBody2D regression.

## Next

- Manual acceptance imports with schema checking and signed-off reviewers.
- Verified app runtime screenshot references for exact UI, source code and game-specific texture fidelity.
- Multi-frame controlled comparisons; no model quality claims without real paired images and evaluators.
