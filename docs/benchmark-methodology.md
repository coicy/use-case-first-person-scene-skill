# Public software/game scene generation benchmark — methodology

## Objective

Evaluate **whether a generated image demonstrates the software/game viewport content actually displayed at the use-case step** at a given use-case step, rather than whether a text prompt contains the right words. Cover common user-facing workflows across desktop software, 3D tools, game editors, isometric games and first-person games.

## Fixtures and source policy

The v1 suite consists of six public projects and 18 specified steps, with 36 evidence targets. These are curated **use-case paraphrases**, not verbatim product specifications or full reproduction of official UI.

| Project | Source | Camera interpretation |
|---|---|---|
| Visual Studio Code | https://code.visualstudio.com/docs/debugtest/debugging | Direct VS Code debugger UI frame |
| Blender | https://docs.blender.org/manual/en/5.0/modeling/meshes/editing/face/extrude_faces.html | Direct Blender edit-mode workspace and mesh viewport |
| GIMP | https://docs.gimp.org/3.0/en_GB/gimp-tutorial-quickie-crop.html | Direct GIMP crop-tool UI frame |
| Godot Engine | https://docs.godotengine.org/en/stable/getting_started/first_2d_game/04.creating_the_enemy.html | Direct Godot editor scene tree, 2D viewport and inspector |
| OpenTTD | https://wiki.openttd.org/en/Manual/Railway%20construction | Direct isometric in-game framebuffer, not a train driver POV or a monitor photo |
| Luanti | https://docs.luanti.org/for-players/controls/ | Direct character-eye game framebuffer, not a photograph of a gaming PC |

Use the actual suite manifest for the canonical source URLs (Blender version can differ). All images and UI screenshots must have legal provenance; **do not redistribute proprietary product screenshots without permission**. The provided suite has no third-party screenshot binaries.

## Offline preflight (required)

```bash
ucscene benchmark benchmarks/famous-projects/suite.json \
  --lock benchmarks/famous-projects/prompt-lock.json \
  --out out/benchmark.json
ucscene benchmark-export benchmarks/famous-projects/suite.json \
  --out-dir out/benchmark-plans
ucscene benchmark-rating-template benchmarks/famous-projects/suite.json \
  --out out/ratings.json
```

The preflight must verify unique use case IDs, source links and step references, prompt hashes, viewpoint mode, scene count, and stable exports. **It does not evaluate generated pixels.** The golden prompt lock must only be updated deliberately after reviewing changed source fixtures and prompts.

## Three-arm visual experiment (optional; paid, user-approved)

Collect images for each case under these output directories, using the exported scene plans:

1. **`prompt-only/`**: one independent generation per scene, no reference image.
2. **`fixed-reference/`**: reference-image edit from a separately reviewed, approved anchor for each case; no chain.
3. **`sequential-chain/`**: first scene independent generation; later scenes edit the preceding image. This may amplify cumulative drift.

Use the same model, resolution, quality, language, prompts, dataset, selection and compute budget across treatments, and preserve exact API settings. Note that the fixed-reference and chain methods are not strictly comparable in number of image-edit calls; report request counts and cost separately. For stronger comparisons run at least 3 independently regenerated trials per method, **with a distinct rating packet and image directory per trial** (the v0.4 scorer covers one trial at a time). Do not pool repeats into the same packet or assert statistical significance from one trial. Keep all trials and rejected generations; do not cherry-pick. Keep API keys outside outputs/repository.

Expected image names: `<scene_id>.png` under each mode's subfolder. Do not mix visual reference screenshots with generated images or synthetic mock images.

## Human review protocol

At least two blinded reviewers per scene are recommended. Each reviewer should read the verified use-case evidence and inspect each actual image, without seeing which method produced it; assign distinct reviewer IDs. The CLI supports multiple rows per scene and mode by duplicating template entries, each with a unique reviewer ID.

| Field | 0 (fail) | 1 (partial / uncertain) | 2 (satisfies) |
|---|---|---|---|
| `point_of_view` | Third-person or wrong camera mode | Ambiguous | Software-only framebuffer with the game's or editor's own camera; no physical user/device |
| `visible_evidence` | Key interaction impossible to see | Partial evidence | All required evidence clearly present |
| `app_fidelity` | Wrong interface, invented gameplay camera or impossible UI | Plausible but uncertain | Matches application/game's documented interaction and viewpoint |
| `continuity` | Device/scene/actor contradict earlier frames | Some drift or cannot be verified | Same scene anchor maintained across steps |

`unsupported_product_features=true` if the image clearly presents undocumented product interactions, workflows, permissions, or outcomes. Strict pass requires all four metrics == 2 and **no unsupported features**. Uncertain always fails the strict threshold. If the reviewer lacks enough reference material to judge a criterion, assign 1 and record the reason rather than guessing.

Fill `image_sha256` from the actual generated image file, `rater_id`, all four numeric scores, and `unsupported_product_features`. Never fill in scores for missing images. The report binds every rated image to its source prompt and image digest and inspects valid PNG/JPEG/WebP image structure. `benchmark-score` counts only actual scored entries; unscored rows stay unevaluated.

## Aggregate interpretation

- `static_pass`: input/plan/traceability consistency only.
- `scored_reviews`, `actual_image_verifications`: number of validated reviewer observations with actual image bytes.
- `strict_pass_rate`: **reviewed** images satisfying the conservative four-factor threshold; null when no scored images.
- `fully_paired_scene_rater_groups`: identical scene **and reviewer** appearing under all three methods.
- `comparison_ready`: all scenes have at least one complete same-rater, 3-arm comparison. This is not a statistical significance test.
- True generalization requires additional unseen use cases, human inter-rater agreement, controlled repeats and source-faithfulness verification.

## Current verified baseline

The preflight verified **6 cases, 18 scenes, 36 evidence items**. Generated image count: **0** for this offline baseline. Real first-person fidelity and image-to-image consistency: **not yet measured**. Provider mocks/CI must not be reported as real-generation performance.

## v0.5 product correction

The canvas must be full-bleed software/game content. Every image depicting a physical screen, real user, hands outside gameplay, desk, peripherals or outside location is an automatic visual failure. The two modes are application-ui and gameplay; gameplay further respects its documented camera (OpenTTD isometric; Luanti first-person). Retire any v0.4 real-world user-view ratings and restart image grading on the corrected outputs.
