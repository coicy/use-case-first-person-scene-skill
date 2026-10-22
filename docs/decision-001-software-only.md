# Product decision 001 — Software-only frame (2026-10-22)

## Superseding decision

The user corrected the project's fundamental interpretation: **only draw what exists inside the software, not the user.** The older framing as a photograph of a user looking at a monitor was a misunderstanding and MUST NOT be used for any new images, prompts, fixtures, acceptance or scoring.

## Invariants

1. All image pixels represent software/application/game content. No real people, workstations, monitors, desks, keyboards, physical hands or photographed usage scenarios.
2. `application-ui`: full-bleed internal UI/window/editor content. The user's role remains metadata and is never visually represented.
3. `gameplay`: full-bleed game framebuffer. Preserve source game's original camera. OpenTTD remains isometric; Luanti may show first-person game-world view. In-game entities, virtual limbs and game environment ARE software content, so may appear when evidenced.
4. Exact product UI should be derived from authorized project screenshots, user-provided assets or explicitly scoped synthetic mockups, not hallucinated controls.
5. Visual review must fail if physical outside-world elements occur, independent of the quality of the UI visible inside a monitor.

## Migration v0.4 → v0.5

- Set `viewpoint_mode=application-ui` for desktop apps/editors; `gameplay` for games.
- Set `game_camera=isometric` for OpenTTD, `first-person` for Luanti; choose only what sources support.
- Rewrite `environment` as IN-SOFTWARE context. `device` becomes optional source metadata and must not be visualized.
- Replace visible evidence that refers to hands, physical screens, warehouses, keyboard or a real-life user with evidence *inside the software*.
- Regenerate `scene-plan.json` (`format_version=1.1`), anchors, image references and prompt lock. Old plans are deliberately rejected.
- v0.4 real-device images are invalid acceptance artifacts and must not contribute to reported visual pass rates.
- v0.3 `compose-ui` remains as a generic perspective transform only for in-software regions, not for physical screens.

## Proof obligations

Six-source benchmark with 18 steps and 36 in-software evidence targets, new golden prompt hashes, regression tests ensuring old modes are rejected and visuals containing physical surroundings are marked as failed by the reviewer. Static tests do not prove real image quality.
