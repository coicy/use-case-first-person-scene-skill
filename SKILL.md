---
name: use-case-first-person-scene
description: Generate software-only use-case visuals, the application UI or rendered game framebuffer itself. Never draw real users, people interacting with computers, monitors, keyboards, hands outside games, or desks.
---

# Use Case → Software-Only Scene Skill (v0.5)

**Authoritative product rule (2026-10-22):** Output contains ONLY pixels/content that belong inside the software/game. It must not be a photo or illustration of someone using the software. This supersedes all former interpretations of 'user first-person' as physical-user POV.

## Correct visual boundaries

- Desktop applications (VS Code, Godot editor, Blender, GIMP, mobile app): **full-bleed in-application UI**, editor toolbars, views, panels, content, selected state, messages. Not a picture of a laptop/phone.
- Games (OpenTTD): **full-bleed in-game scene and UI**, preserving the game's isometric/top-down camera, not a train driver POV or physical screen.
- First-person games (Luanti): **full-bleed in-game character camera** with only warranted HUD/character limbs; never a photo of a gamer or monitor.
- Game characters, virtual hands and virtual environments may be depicted ONLY if they are part of the original application's visible content. Real-world operator visuals are forbidden.
- One frame = one concrete use-case step; no poster, collage, explanatory background or extraneous decorative environment.

## Workflow

1. Read requirements and examples/screenshots from user's project. Preserve the user-visible task, state, exact UI labels and explicit evidence. Treat other elements as unknown, not inspiration to invent features.
2. Extract the use case with `ucscene extract input.md --out out/case.json` or opt-in `--ai`. A *software-internal* environment is required; physical usage location/device information is optional metadata and never a visual object.
3. Choose `viewpoint_mode` from `application-ui` (default) or `gameplay`. For `gameplay`, set `game_camera` to one of `documented`, `first-person`, `isometric`, `top-down`, `side-scrolling`, `third-person` only when justified by the use case or source.
4. Run `ucscene validate CASE`, `ucscene plan CASE --out PLAN` and `ucscene review PLAN`. The plan must be `format_version=1.1`, `anchor.frame_scope=software-only`. v0.4 physical-user plans are invalid. No external UI/device context in a visual evidence item.
5. Prefer exact application screenshots, UI compositions, and programmatic overlays to invented text. For multi-step output, use app/game-only reference images with `anchor-create`, `anchor-verify`, then `generate --anchor` only after human approval and explicit authorization of paid model calls.
6. `compose-ui`/`compose-batch` can geometrically overlay real UI into regions INSIDE a software screenshot/game framebuffer. Never put software into a photograph of a physical monitor. Geometry preflight and provenance hashes are mandatory.
7. Optionally run `review-image PLAN --step ID --image PNG` to check software-only frame, camera, step evidence and text. Human review is needed: model-audit PASS is not verified software correctness.
8. Deliver images and source plans. State whether generation was performed, which source screenshots are real/synthetic, whether visual audits occurred, and any unresolved behavior.

## Non-negotiable tests

- Real hands on a keyboard, physical screens, desk, office and people using software → visual failure, even when the UI on the pictured screen is accurate.
- In-game third-person character imagery is allowed when the *game itself* renders it.
- Preserve the original software/game camera; do not force every use case into literal human-eye POV.
- No invented app controls, game mechanics, behavior or acceptance claims.
- Never claim offline plan tests or CI mocks prove actual visual correctness.

## Quick start

```bash
python -m pip install -e '.[ui]'
ucscene extract examples/warehouse-scan.md --out out/case.json
ucscene plan out/case.json --out out/plan.json
ucscene review out/plan.json
ucscene benchmark benchmarks/famous-projects/suite.json --lock benchmarks/famous-projects/prompt-lock.json
```

See [docs/decision-001-software-only.md](docs/decision-001-software-only.md) for the contract revision and migration rules. See README for `generate`, `review-image` and `compose-ui` options.
