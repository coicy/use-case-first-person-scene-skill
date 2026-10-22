# WP-01 implementation note — v0.7 design contracts

**Status:** Implemented on the WP-01 milestone; WP-02 through WP-05 are not implemented.
Product authority: [PRODUCT-002](PRODUCT_REQUIREMENTS.md). Work order: [V07_WORK_PLAN](V07_WORK_PLAN.md).

## What was implemented

- **ProductBrief** (`schemas/product-brief.schema.json`) contains a concept for a **new** software product or game, source-stated vs unreviewed requirements, optional structured hard constraints, unknown design questions and associated use-case steps. A screenshot or an existing implementation is **not required**.
- **DesignDecision** (`schemas/design-decision.schema.json`) records new design proposals, explicitly tracked status, revision, scalar effect keys and evidence metadata for a user-approved decision. A program-created proposal starts at `proposed`, `locked=false`; it cannot be marked approved/locked without an explicit approval record. Approval metadata is **self-reported**, not a cryptographic proof of user consent. WP-03 will implement a separate controlled approval workflow.
- **UseCaseScene** (`schemas/scene-design.schema.json`) identifies a single software-internal use-case step. The initial scaffold is `unresolved` and has **no invented UI elements**, not a generated layout or image.
- **DesignBundle** (`schemas/design-bundle.schema.json`) links the three models. Offline validation checks unique IDs, cross-model links, rejected/unapproved decisions, structured hard-constraint conflicts, and conflicting approved decisions.
- **Legacy migration** converts v0.6 structured use cases into new-product briefs with original case/step IDs and source statements intact. All migrated requirements are marked `review-required`. It never automatically grants approval.

## Local CLI walkthrough

```bash
python -m pip install -e '.[ui,dev]'

ucscene brief-init \
  --product-id task-atelier \
  --name 'Task Atelier' \
  --category desktop \
  --prompt '设计一款原创的团队任务与素材管理软件' \
  --use-case '用户按标签筛选素材并打开详情' \
  --out out/task-atelier-brief.json

ucscene design-validate out/task-atelier-brief.json --kind brief
ucscene design-scaffold out/task-atelier-brief.json --out out/task-atelier-bundle.json
ucscene design-validate out/task-atelier-bundle.json --kind bundle

# Safe migration from a legacy use case; prior case/step IDs are preserved
ucscene migrate-legacy examples/warehouse-scan.json \
  --product-id legacy-warehouse --name 'Warehouse Concept' \
  --category web --out out/migrated-brief.json
```

Inspect the generated `ProductBrief` and `DesignBundle` JSON. An `unresolved` scene is normal at this stage: WP-02 will propose UI/layout decisions, attach them to scenes, and compile image prompts. **Do not feed an unresolved bundle to the legacy `ucscene generate`** command, which expects a v0.6 `scene-plan.json`, not a v0.7 DesignBundle.

## Original-product smoke fixtures

- `benchmarks/new-products/new-asset-studio.brief.json`: an original desktop game-asset catalog product.
- `benchmarks/new-products/new-hamlet-builder.brief.json`: a fictional isometric building game.
- Corresponding `.bundle.json` files contain no approved decisions and one unresolved scene each.

These use only fictional/new products and do not attempt to reconstruct Godot, VS Code or OpenTTD screenshots. Six legacy project benchmarks remain for backwards compatibility, not for measuring v0.7 design quality.

## Contract guarantees and explicit limitations

- Known structured `hard_constraints` in ProductBrief conflict with mismatching decision `effects` and are rejected.
- Unstructured natural-language requirement **semantic contradictions** are **not** yet understood by this validator. WP-02 must detect/flag them at the planning layer and permit human review. Do not claim natural-language theorem proving.
- Missing UI/visual styling is allowed as an unresolved design decision. The initial scaffold must not invent screenshots or grant approval.
- `brief-init` **preserves the entire prompt as user-supplied text**, but does not extract individual requirements from arbitrary text. Automatic interpretation and multi-candidate design belong to WP-02.
- `migrate-legacy` works only on valid v0.6 software-only JSON use cases; it does not migrate images, image hashes or old plan files.
- `design-validate` performs application-level checks in pure Python. JSON Schema files use draft 2020-12 and are checked in the dev test suite; additional semantic referential checks occur in Python.
- No paid API calls occur in WP-01, and tests do not claim actual UI images exist.

## Tests and acceptance

Run `python -m unittest discover -s tests -v`. CI runs Python 3.10 and 3.12, checks exported schema files through `jsonschema`, and performs CLI smoke tests for new contracts while preserving old behavior.

WP-01 acceptance is successful only when real code, examples, validation tests and CI pass. Full v0.7 approval requires WP-02 to WP-05, including actual generated concept images for two original products and human review.
