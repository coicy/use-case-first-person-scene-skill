---
name: use-case-first-person-scene
description: Use-case grounded first-person scene images and storyboards for software and games. Use when a user wants to see the experience from the current actor's eyes, not UML diagrams, decorative mockups, or third-person illustrations.
---

# Use Case First-Person Scene Skill

## Mission

Translate evidence-backed use-case steps into concrete first-person environments and images. Reconstruct what the active user sees, touches, and reacts to at a specific point in the scenario. Do not confuse conceptual illustrations with authentic screenshots of functioning software.

## Required workflow

1. Read the actual case, PRD, existing code, screen references, and product constraints. Identify the acting user's goal, visible objects and current step/branch.
2. If the input is structured Markdown, run `ucscene extract INPUT.md --out out/uc.json`. For unstructured documents, manually populate JSON or, with user-authorized API usage, run `ucscene extract INPUT.txt --ai --out out/uc.json`.
3. Review `extraction.issues`. **Do not plan or render with an unready draft**. Never silently invent a device, UI state, environment, actor or visible evidence. Ask for needed facts or explicitly label manual override decisions.
4. Run `ucscene validate out/uc.json`, then `ucscene plan out/uc.json --out out/plan.json` and `ucscene review out/plan.json`.
5. Choose one decisive step, a consistent sequence, or a normal-vs-error comparison. Viewpoint is the actor's actual eye position. Hands/forearms can appear when physically plausible; avoid third-person and over-the-shoulder compositions. Each image must show **the exact step-specific action and required visible evidence**.
6. Prefer a verified base reference image when scenes need identical architecture, props, characters or hardware. Use `ucscene generate ... --reference-image asset.png`; or use `--chain` for a sequential progression when cumulative drift is acceptable. No source/reference image should be claimed as a verified UI prototype.
7. Generate actual images only when the image provider is available and the user authorized external generation. CLI uses `OPENAI_API_KEY`. When unavailable, provide render-ready prompts and scene plan; never claim PNGs were generated.
8. Visually inspect all outputs. Optionally run `ucscene review-image PLAN --step STEP_ID --image IMAGE [--reference-image BASE]`; treat its `passed` result as advisory and check screenshots yourself.
9. Report completed files, traceable evidence, unverified assumptions, outstanding issues, and mismatches. Retain the original use-case ID and step identifiers when known.

## Render-quality rules

- Visual target: lived, concrete task context; the user is looking through their own eyes.
- Avoid third-person avatars representing current actor, decorative environment shots, stylized dashboard floating in space, irrelevant UI features, and explanatory text placed over the scene.
- Use concrete spatial camera-to-interaction geometry. Keep physical constraints plausible.
- For sequential imagery, fix environment/device/style/actor. Only update step action/state or intentionally changed objects.
- Screen text from a generative model can be inaccurate. For strict fidelity to real software, use a provided screenshot or compose a verified overlay post-generation.
- Never treat generated imagery as definitive code behavior, security proof, accessibility proof or finished UX design.

## Source files

- `schemas/use-case.schema.json`: source contract
- `src/ucscene/extractor.py` / `src/ucscene/ai_extract.py`: offline and optional model extraction
- `src/ucscene/core.py`: validation, deterministic plan and static audit
- `src/ucscene/provider.py`: generation and image-edit request
- `src/ucscene/vision.py`: optional image evidence audit
- `examples/warehouse-scan.md`: offline extracted example with an exception flow
- `AGENTS.md`: engineering maintenance contract
