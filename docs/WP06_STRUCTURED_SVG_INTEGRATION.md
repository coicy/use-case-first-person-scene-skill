# WP-06 Stage 1 — Semantic Scene Graph to authoritative SVG

**Implementation status:** Code implemented, executable example, automatic regression coverage. This **does not** mean the user approved the example design, or that generated software can run. The Agent-art hybrid composition stage is **not yet implemented**.

## Why this exists

The project's previous prompt-to-PNG approach allowed beautiful but functionally wrong screens: a farm panel attached to the wrong object, success feedback during save failure, disappearing layout regions, or wrong-product outputs. Product decision [PRODUCT-004](decision-004-semantic-fidelity.md) requires layout, structure, functionality and state fidelity **regardless of output composition**.

We now introduce a typed intermediate scene contract. `ProductBrief -> validated DesignPlan -> Agent-authored scene-graph spec -> validated Semantic Scene Graph -> deterministically rendered SVG`. The SVG is a projection of the graph, never an independent competing source of truth.

## Commands

```bash
python -m pip install -e '.[ui,dev]'

# A complete fictional desktop-product example. Agent/designer authors *.spec.json;
# the software does NOT invent a fully functional UI from text alone.
ucscene scene-compile \
  benchmarks/new-products/scenegraph/new-asset-studio.plan.json \
  --spec benchmarks/new-products/scenegraph/new-asset-studio.spec.json \
  --out /tmp/asset-graph.json

ucscene scene-verify /tmp/asset-graph.json \
  --plan benchmarks/new-products/scenegraph/new-asset-studio.plan.json

ucscene svg-render /tmp/asset-graph.json \
  --plan benchmarks/new-products/scenegraph/new-asset-studio.plan.json \
  --out-dir /tmp/asset-svg

ucscene svg-verify /tmp/asset-graph.json --manifest /tmp/asset-svg/manifest.json
```

Repeat with `new-hamlet-builder.plan.json` and `.spec.json`. Each yields **three separate SVG files**: STEP-001, STEP-002, STEP-003. SVGs can be viewed directly in browsers and vector-editing tools. Rendering to PNG is an optional preview conversion (CairoSVG is not a core dependency).

## Data and authority contracts

- `schemas/scene-graph.schema.json`: schema for compiled typed scene graphs.
- `src/ucscene/scenegraph.py`: planner-bound compiler, semantic validator, deterministic SVG renderer and byte-for-byte verifier.
- `benchmarks/new-products/scenegraph/`: independently authored, **not user-approved**, example specs and their input plans.
- `source_plan_sha256` and `source_spec_sha256`: cryptographic hashes of source data. `graph_sha256`: canonical graph content hash, not a signature or a remote attestation.
- Each SVG has `data-product-id`, `data-scene-id`, `data-step-id`, `data-graph-sha256` and `data-authority=proposed`. Elements include stable IDs, region, binding, object target, action and evidence data.

The implementation is deliberately **fail-closed for proposal-only**. It refuses to claim an approved or locked DesignSystem based on AI-authored spec. Integration with confirmed DesignSystem approval is a subsequent extension requiring an authenticated decision and revision binding.

## Explicit static invariants

1. Same product ID, candidate ID, candidate layout/navigation and exact source step sequence.
2. Stable canvas/regions/elements across steps; bounds and supported sidebar/workspace/inspector or world/HUD/inspector topology.
3. No duplicate object, element, region or action IDs; no element outside its parent region.
4. State bindings must exist and bind to the declared object, not another existing object.
5. Visible elements must account for each required UI evidence string and mandated UI text.
6. Action preconditions and effects must explain every change between snapshots; unreported state changes fail.
7. Exact SVG bytes must be reproducible from the source graph; any edits outside a new authorized compile fail verification.

Note: element evidence IDs are **authored semantic assertions**, not computer-vision proof of their visible correctness. More sophisticated functional verification and user evaluation remain necessary.

## Example product data (design proposal, not game rules)

**Asset Studio:** filter model resources -> open detail for the same selected castle -> attempt to edit tags and show `保存失败` while the persisted tags stay unchanged.

**Hamlet Builder:** select `farm-01` -> inspect its production -> assign one worker. Example demonstration worker count `2 -> 3`, production `4 -> 6`, available workers `3 -> 2`. The numbers are arbitrary test assumptions; the user did not approve these as product mechanics.

## Security limitations

The renderer does **not** accept raw arbitrary SVG input from an Agent. It emits a restricted fixed set of SVG tags via ElementTree with XML-escaped text and known theme colors. It generates no scripts, event handlers, foreignObject, external images, fonts or URLs. All SVG files are statically reproducible.

The renderer supports only the two layout archetypes exercised by the benchmark (`sidebar-workspace-inspector` and `world-hud-right-panel`), a small collection of visual widget shapes, and **proposal-only** contracts. It is an explicit staging implementation, not a general Figma replacement.

## Stage 2 (unimplemented)

1. **Structured art slots and hybrid compositing.** The Agent generates only assets for graph-identified art slots, then a trusted compositor crops/clips assets into those slots beneath protected SVG labels, values and controls.
2. **Approved DesignSystem binding.** Carry approvals, frozen layout decisions, revision and source evidence into the graph without self-approval.
3. **Semantic verification for new outputs.** Compare final composed images and slot restrictions against the generated graph; human review still required for actual appearance and usability.
4. **More interface types.** Parameterize layouts for mobile, web, strategy, action and 3D applications rather than hardcoding two demos.
5. **Agent bridge.** Change `concept-agent-export` so it passes graph identities, expected art slots and SVG previews as constraints; do not assume every native host image tool can receive the exact prompt.

The outputs are structured interactive-design **concept depictions**, not executable applications or proofs of actual software behavior. Visual design decisions remain `proposed` until explicitly approved by the user.
