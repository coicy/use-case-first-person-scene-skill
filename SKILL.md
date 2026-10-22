---
name: use-case-first-person-scene
description: Generate evidence-grounded first-person scenario images for software and game use cases. Use when a user needs experiential concept scenes or step-by-step storyboard images, not UML, abstract diagrams, or generic screenshots.
---

# Use Case First-Person Scene Skill

## Execution workflow

1. Read the user's real use case, requirements, UI references, or code-derived constraints. Preserve the original source step identifiers.
2. Extract actor, goal, environment, device, interaction target, step/action, visible evidence, state, and exception flow. Do not fabricate product features.
3. Build a JSON use case according to `schemas/use-case.schema.json`. Record every explicitly visible requirement under `visible_evidence`.
4. Use true first-person camera geometry. The camera is at the active actor's eye position; hands may appear if physically plausible. Never show the current user in a third-person or over-the-shoulder view.
5. Determine output scope: one decisive step, an ordered multi-step sequence, or success-versus-exception comparison. Keep actor, location, device, lighting, style, and scene anchor constant unless the use case explicitly changes them.
6. If CLI is installed, execute `ucscene validate <usecase>`, `ucscene plan <usecase> --out <plan>`, and `ucscene review <plan>`.
7. To produce actual PNGs, use an available authorized image renderer. Local CLI rendering requires `OPENAI_API_KEY` and explicit `ucscene generate`. Without an image provider, return usable planned prompts and do not claim images exist.
8. Visually inspect generated images: point of view, action evidence, physical realism, cross-scene continuity, invented features, exact UI text, and stated state.
9. Communicate source evidence, assumptions, generation status, and unsatisfied constraints.

## Non-negotiable rules

- Do not default to UML, flowcharts, abstract concepts, generic marketing images, or third-person shots.
- Do not present imagined UI labels, controls, permissions, or outcomes as product requirements.
- Do not confuse static plan review with actual visual image review.
- Do not commit API keys or sensitive input.
- A local prompt plan does not prove image content, and image content does not prove working software.

## Files

- `schemas/use-case.schema.json` — source data contract
- `examples/warehouse-scan.json` — positive and exception branch example
- `src/ucscene/core.py` — deterministic plan generator
- `src/ucscene/provider.py` — optional image provider
- `AGENTS.md` — engineering contract
