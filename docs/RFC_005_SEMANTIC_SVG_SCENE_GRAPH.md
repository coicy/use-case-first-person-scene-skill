# RFC: Semantic Scene Graph + SVG as authoritative visual layout

**Status: experimental architectural proposal; not yet merged, not user-approved.**

## Problem

The current new-software use-case image pipeline mainly relies on natural-language layout and behavior descriptions. A raster generator can invent controls, contradict business states, drift across views, or confuse products. Image hashes prove only integrity.

## Source-of-truth hierarchy

1. User-confirmed ProductBrief and product rules; DesignSystem decisions with provenance.
2. Typed **Semantic Scene Graph** (JSON): component/object IDs, parent-child relations, positions, actions, state data, and requirement links. A missing decision remains *proposed*.
3. Deterministically rendered **SVG**: authoritative 2D visual structure, labels, panels, selection/highlight shapes, HUD and stable element anchors. SVG carries element IDs, `data-role`, `data-binding`, `data-action`, contract digest and explicit unapproved status.
4. Native Agent image generation: optional art/background/thumbnail/texture **inside explicitly allocated slots**. It is not the source of truth for text, numbers, control existence or navigation.
5. Final PNG or SVG/raster hybrid is compiled/composited deterministically. The validator tests exact SVG/layout data and visual overlays, not only the aesthetic quality of the raster.

Proposed rendering: `ProductBrief + DesignSystem + UseCaseState -> SceneGraph.json -> SVG -> [art assets] -> composed image`. SVG is a deterministic projection of the canonical scene graph, not an independent document that can silently change data.

## Example invariant

This demonstrator illustrates an original isometric town-builder farm flow:

- `STEP-001`: `selected_object = farm-01`, `workers = 2`, production = 4, free workers = 3.
- `STEP-002`: the same selected farm, business data unchanged; inspector production tab is selected.
- `STEP-003`: after `assign-worker`, workers = 3, production = 6, free workers = 2, with success feedback.

Values/ratios and the specific SVG style are **illustrative assumptions**, not accepted game rules.

The renderer must validate components' bounds, world/inspector adjacency, unique IDs, farm/inspector binding, action target, constraints, and state transition deltas. It generates three independent SVGs from the same contract. Changing object identity, worker count, binding, or inspector placement must fail validation before any costly image generation.

## How to inspect

Run `python -m unittest -v test_contract.py` then `python render.py`. Open `renders/step-001.svg`, `renders/step-002.svg`, `renders/step-003.svg` in a browser or vector editor. The provided PNGs are deterministic previews, not AI images. `renders/render-manifest.json` contains source and image checksums.

## Non-goals and limitations

- SVG cannot on its own certify runnable interaction or server/business logic. State-machine semantics remain in JSON and must be checked separately.
- Beautiful vector drawings and verified positions do not prove the interaction is ergonomic; visual/user evaluation is still required.
- For 3D gameplay use semantic world/entity state or a 3D scene representation for the world, with SVG authoritative for HUD, labels, selection overlays and screen-space anchors. Do **not** require every world texture and perspective geometry to become SVG paths.
- Raster art remains creative, but can only affect editable/non-authoritative regions. Verify compositing doesn't touch protected SVG-derived UI layers.
- SVG from unknown agents must be parsed safely: disallow script, event handlers, `foreignObject`, external URLs, external fonts and network fetches in production output. Use a trusted renderer.
- Preserve original source IDs, proposal/approval statuses, versions, hashes, and meaningful differences; do not infer approval from any generated image.

## Recommended next repo milestone

`WP-06: Structured Concept Authority` (dependent on PRODUCT-004): `schemas/scene-graph.schema.json`, `ucscene scene-compile`, `ucscene svg-render`, `ucscene scene-diff`, `ucscene scene-verify`, and `ucscene hybrid-compose`. First test on 3 asset-manager screens + 3 original-builder screens. A changed SVG component must be traceable to an explicit scene graph change and allowed proposal/approval path.
