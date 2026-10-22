# Product Roadmap

## Implemented — v0.1.0

- Structured use-case JSON to reproducible first-person scene prompts and step-specific evidence.
- Optional image-generation provider and offline tests.

## Implemented — v0.2.0

- Bilingual structured Markdown input; opt-in AI free-prose extraction with source quote checks.
- Fixed-reference/chain image edits, model-assisted POV/evidence review (advisory).

## Implemented — v0.3.0

- Explicitly human-approved, use-case-bound reference image manifests with SHA-256 file integrity checks.
- Offline perspective mapping of a **real provided UI screenshot** into four user-chosen screen corners on any generated scene; pixel preservation outside projected device screen.
- Batch per-step screenshots, input preflight, provenance reports and a completely offline reproducible demonstration.
- Python optional Pillow extra, CI matrix and offline tests for anchors, composition and invalid inputs.

## Not yet implemented (candidates for v0.4 and beyond)

- Automatic detection/interactive editing of device screen quadrilateral; occlusion behind hands and reflections.
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

## v0.4 — Public project benchmark and semantic viewpoint (implemented)

- Official-doc-curated cases for VS Code, Blender, GIMP, Godot, OpenTTD, and Luanti.
- `physical-user` vs `avatar-eyes` camera semantics, with structural tests to prevent isometric-world perspective collapse.
- Offline source-traceability checks, deterministic golden prompt lock, case plan export, optional provenance-verified audit aggregation.
- Still requires real paid image sampling and blinded human ratings before any claim that fixed anchors or chain editing actually improve image quality.
