## PRODUCT-003: host-Agent image generation comes first

Agent native generation is preferred. Portable CLI supports independent task export, PNG import and hash verification with no extra API key. Actual generation happens in the host Agent; separate paid API remains opt-in fallback. Image quality and user approval are separate acceptance gates. See decision-003-agent-native-generation.md.

# Product Roadmap

> **2026-10-22 Product decision 002:** The primary purpose is to **design original new-software use-case scene visuals from prompts**, not to reproduce existing application screenshots. [Authoritative requirements](PRODUCT_REQUIREMENTS.md) · [v0.7 execution plan](V07_WORK_PLAN.md).

## Next — v0.7 (planned, NOT implemented)

1. ProductBrief / DesignDecision / UseCaseScene schemas, migrate old plans.
2. AI design engine: requirement facts vs creative proposals, UI/scene layout and interaction design prior to image prompting.
3. DesignSystem consistency, explicit approval/lock and changes across use cases.
4. Concept generation with explore/draft/consistent/revise purposes and real human visual reviews.
5. Original new-product benchmark: desktop app + builder game, at least three steps per product, with multiple variants.

**Acceptance priority:** use-case fidelity, interaction clarity, readability, coherent original visual design, cross-use-case consistency. Existing-app screenshot pixel similarity is not an acceptance criterion for new products.

## Previous releases and historical context

The v0.1–v0.6 features remain in the repository for compatibility: structured use-case extraction, software-only framing, optional image APIs, reference image anchors, image composition, official-source reference benchmarks, image QA and human acceptance galleries. Previous rendering behavior and screenshot-fidelity ambitions must not override PRODUCT-002.

- PRODUCT-001 ([decision-001-software-only.md](decision-001-software-only.md)) continues to govern output framing: **only in-software pixels**, no physical user/monitor/desk.
- PRODUCT-002 ([PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md)) supersedes the presumption that every UI element requires existing-product screenshot evidence and that AI must avoid independently designing controls.
- Six famous software/game fixtures remain **historical compatibility and design-reference** tests; v0.7 quality must be tested on novel software/game products.
- Actual image-generation and multi-scene design consistency cannot be established from unit tests or mocked API calls alone.

No new v0.7 feature should be marked implemented until code and tests verify it.

## v0.7 implementation progress — WP-01 completed (2026-10-22)

- Implemented: ProductBrief / DesignDecision / UseCaseScene / DesignBundle model contracts and validation, safe v0.6 migration, new commands `brief-init`, `design-scaffold`, `design-validate`, `migrate-legacy`, original-product fixtures, and regression tests.
- See [WP01_IMPLEMENTATION.md](WP01_IMPLEMENTATION.md).
- **Still planned:** WP-02 AI-based interface decisions and variants; WP-03 design system approvals/locks; WP-04 actual v0.7 rendered images; WP-05 human-reviewed new-product image benchmarks. Model scaffolds are not designed or rendered images.


## WP-02 implementation milestone (2026-10-22)

WP-01 and WP-02 are implemented. WP-02 includes new-product design-plan/review/export commands, 2–3 variant original interface proposals, MUST/MAY/UNKNOWN requirement classification, source-bound per-step interaction design and SHA-256 prompt verification. Offline deterministic heuristics are tested; optional model ideation requires explicit `--ai` and has not been live-validated.

**Still planned:** WP-03 approval and frozen DesignSystem; WP-04 image output for new-product plans; WP-05 real visual-quality acceptance benchmark. Read [WP02_IMPLEMENTATION.md](WP02_IMPLEMENTATION.md) and [V07_WORK_PLAN.md](V07_WORK_PLAN.md). Older roadmap phases above are historical and do not supersede PRODUCT-002.


## v0.7 WP-03 — implemented, offline only

- User-acknowledged selected candidate → versioned product DesignSystem, optional frozen keys.
- Explicitly authorized revision with predecessor digest and affected-key diff.
- Consistent new-use-case scene plan using approved layout/navigation/style and step-specific feedback.
- Schema/CLI/integrity tests. See [WP03_IMPLEMENTATION.md](WP03_IMPLEMENTATION.md).
- Actual PNG images, visual authenticity and user acceptance are **not** established here. WP-04 remains next.



## Follow-up: audit-bound single-scene retries (implemented offline)

The observed image generator continued to produce a six-panel board even after explicit single-frame instructions. Offline failure observation / targeted immutable retry packets, image digest checks and up to two verified repair attempts are implemented. No successful standalone image API recovery or real visual QA success should be inferred from regression tests. See [WP04_RETRY_IMPLEMENTATION.md](WP04_RETRY_IMPLEMENTATION.md).

## Issue #3 implementation — 2026-10-24

Implemented product-identity binding for new render packets, independent visual product-match QA, self-attested `--product-match` observations, and `wrong-product` corrective retry. These are **engineering** safeguards, not proof of actual paid-model image compliance. The WP-05 release gate remains: real Images API generation for two original products, separate per-step visual acceptance, and cross-step consistency evidence. See [ISSUE03_PRODUCT_MATCH.md](ISSUE03_PRODUCT_MATCH.md).
