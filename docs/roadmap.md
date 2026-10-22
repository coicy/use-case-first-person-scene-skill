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