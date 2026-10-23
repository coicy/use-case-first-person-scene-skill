---
name: use-case-first-person-scene
description: Design software-only concept visuals for NEW or not-yet-built software and games from user prompts and use cases. Act as a UI/UX and scene designer, not an existing-product screenshot copier. Keep requirements separate from AI proposals and maintain cross-use-case consistency.
---

# Use Case Driven Software Concept Designer

## Authoritative product intent

Read docs/PRODUCT_REQUIREMENTS.md (PRODUCT-002) before planning or developing features. This product creates **new software / game use-case concept images**, based on user requirements and AI design proposals. It does not require actual app screenshots. The older v0.6 screenshot-fidelity objective is superseded as a primary use case.

## Visual boundary inherited from PRODUCT-001

Each generated image must be entirely **inside the target software or game**. No actual users, monitor/phone hardware, keyboards, desk or promotional mockup. For a game show the game's designed camera; it need not be first-person gameplay. Virtual hands are acceptable when part of the in-game image.

## Design-first working method

1. Determine what the **new product** is, what goal the user pursues and which use-case step is shown.
2. Separate **confirmed requirements** from **AI-proposed design** and **unknowns**. Do not present proposals as user-approved facts.
3. Propose suitable navigation, panels, visible objects, controls, feedback, information hierarchy, styling and camera. Missing design details are opportunities to design; they are not an automatic reason to refuse image generation.
4. Produce an explicit design plan for the screen/scene **before** an image prompt. If alternate layouts matter, propose several comparable candidates.
5. Reuse established product-wide design choices across related use cases. A decision may only become approved or locked by explicit user action.
6. Generate software-only visuals. If exact UI copy, numeric values or text must be guaranteed, use deterministic UI overlays or verified supplied assets; do not claim images prove functioning software.
7. Review visible use-case evidence, interaction clarity, composition, legibility, consistency and design value. Preserve input IDs and generation provenance.
8. Present image concepts as proposals until approved; when revising, retain all existing approved constraints.

## How to treat other software

Godot, VS Code, Blender, OpenTTD, GIMP and Luanti are **examples to learn interaction patterns**, not exact-replication targets for new products. References are optional. Do not demand runtime screenshots of a new product that does not exist.

## Existing CLI caveat

The released v0.6 CLI still implements source-grounded scene prompting, reference anchors, and acceptance galleries. The ProductBrief/DesignDecision/DesignSystem design workflow and modes explore/draft/consistent/revise are **planned for v0.7**, not already implemented. Keep describing CLI behavior truthfully until the implementation and tests land.

## Engineering plan

See docs/V07_WORK_PLAN.md for deliverables and acceptance gates. Retain the existing no-external-hardware boundary and no-silent-paid-API policy.

## Implemented v0.7 WP-01 foundation (modeling only)

The `ProductBrief`, `DesignDecision`, `UseCaseScene` and `DesignBundle` contracts are implemented under `src/ucscene/design/` with JSON Schemas and tests. Use `ucscene brief-init` for a brand-new software product, `ucscene migrate-legacy` for review-required historical cases, `ucscene design-scaffold` for an UNRESOLVED scene model, and `ucscene design-validate --kind brief|decision|scene|bundle` for static validation.

A missing design detail is not a reason to require an existing software screenshot. The WP-01 scaffold is NOT a designed UI, a selected proposal, or a generated image. The AI-driven proposal/planning workflow is WP-02 (pending). Only describe WP-01 as implemented. See `docs/WP01_IMPLEMENTATION.md`.


## v0.7 WP-02 — implemented original product design planning

For NEW software/game concept design, start from ProductBrief, run `ucscene design-plan BRIEF --variants 2 --out out/design-plan.json`, then `ucscene design-plan-review out/design-plan.json` and `ucscene design-export out/design-plan.json --out out/prompts.json`. The result contains 2–3 alternative layouts, interaction designs, state-specific feedback, tradeoffs and source-bound per-step image prompts. Original design elements are allowed but must be labeled `proposed`. Existing application screenshots are NOT required.

Default `design-plan` is a deterministic heuristic generator; opt-in `--ai --model gpt-4.1-mini` requests creative model proposals through a paid API with the operator's key. Never imply the offline mode is an LLM, that model output has been live-tested, or that prompt generation produced images. WP-03 approval/freeze and WP-04 actual concept image generation are not implemented yet. See docs/WP02_IMPLEMENTATION.md.


## v0.7 WP-03 — design continuity (implemented)

A user-approved, selected candidate is represented by a DesignSystem. **Never automatically approve or lock a variant**. Only after the user explicitly chooses and approves it may an agent run `ucscene design-system-create PLAN --variant VAR-XX --approve --evidence-ref USER-MESSAGE-REFERENCE [--lock]`. The evidence reference is caller-asserted metadata, not a verified signature or proof of approval. Use `design-apply SYSTEM NEW_BRIEF` to keep the same original product layout, navigation, visual language and core controls across use cases. A locked design may only be modified with a *new* explicit user approval and `design-system-revise --override-lock --approve --evidence-ref ...`; compare revisions with `design-system-diff`. `design-apply-review` verifies the source and baseline. Full instructions: [WP03_IMPLEMENTATION.md](docs/WP03_IMPLEMENTATION.md). No images are generated by this milestone.


## WP-04 render concepts (implemented)
Compile one new-product candidate with ucscene concept-packet PLAN --mode draft --variant VAR-01 --out PACKET; then dry-run ucscene concept-render PACKET --out OUT.
Paid rendering requires explicit --execute --max-images N and a configured API key. concept-gallery and concept-verify bind real files to prompts and hashes, not to automatic design approvals.
Inspect actual output and reject any montage, storyboard, contact sheet, or non-software surrounding. Each image must show exactly one use-case step.
See docs/WP04_IMPLEMENTATION.md for mode and provenance details.



## Failed-image recovery (WP-04)

When the image is a storyboard or a multi-screen presentation board, record it with `concept-audit` (optional paid advisory) or `concept-observe` (self-attested, offline), then generate a single-scene, hash-bound retry through `concept-retry`. Never claim a montage crop is an independently generated image or a human acceptance. The retry is only a prompt request until an explicitly authorized `concept-render --execute --max-images 1`; keep user requirements and frozen DesignSystem unchanged. See `docs/WP04_RETRY_IMPLEMENTATION.md`.
