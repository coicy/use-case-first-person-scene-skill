# WP-02 — New-product use-case design proposals (v0.7)

**Status:** Implemented as code and offline tests. Real AI API responses and actual concept PNG generation have not been externally validated.

**Authority:** [PRODUCT-002](PRODUCT_REQUIREMENTS.md); [v0.7 plan](V07_WORK_PLAN.md). New software and games are the primary target. Existing software screenshot reproduction is **not** the product goal.

## Working commands

```bash
# No API key, deterministic baseline: two original desktop UI candidates × three steps
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --variants 2 --out out/asset-design-plan.json
ucscene design-plan-review out/asset-design-plan.json
ucscene design-export out/asset-design-plan.json \
  --variant VAR-01 --out out/asset-variant-01-prompts.json

# Three isometric builder game concepts × three steps (also no API key)
ucscene design-plan benchmarks/new-products/new-hamlet-builder.wp02.brief.json \
  --variants 3 --out out/hamlet-design-plan.json

# EXPLICIT opt-in to model-based, creative design via OpenAI Responses API
# Requires OPENAI_API_KEY and may incur usage charges
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --ai --variants 2 --model gpt-4.1-mini --out out/ai-design-plan.json
```

The output **DesignPlan** has a SHA-256 fingerprint of the complete source ProductBrief, an unapproved WP-01 DesignBundle, a MUST/MAY/UNKNOWN classification, and 2-3 candidate layouts. Each candidate includes navigation, style, concrete step controls, information priority, failure/waiting/success feedback, tradeoffs, per-step prompts, prompt hashes and requirement/decision IDs.

## Why two generators?

| Path | What it does | Status | Costs |
| --- | --- | --- | --- |
| Default `design-plan` | Deterministic, broad UI layout and game HUD heuristic proposals. Useful for smoke tests and scaffolding; not evidence of model creativity. | Tested offline | No API calls |
| `design-plan --ai` | Sends the new-product Brief to a text model requesting distinct original UI interaction candidates. Verifies source hard constraints and data shape before compiling. | Mocked provider response tested; real API call unverified | Requires operator-approved API usage |

Neither method produces images or proves the quality of a generated concept. Images and candidate selection remain WP-04 and WP-03 respectively.

## Key invariants

1. User-stated use-case action, branch, status, exact visible text and evidence remain untouched in the design plans. Machine-readable hard constraints for `ui.layout`, `ui.navigation` and `ui.visual_style` take precedence. Conflicting AI candidates fail immediately.
2. Novel UI controls and layouts are **proposals**. All decisions remain `status=proposed, locked=false` and the overall design plan `approval=none`. The WP-02 engine cannot approve or freeze a design.
3. Visual output is always software-internal. External monitors, hardware, hands typing on a desk and marketing mockup compositions are forbidden.
4. One candidate represents a coherent product layout across the source use-case steps; another candidate changes the design approach, not the original functional requirements.
5. Every exported prompt is reproducible. `design-plan-review` rejects tampered source requirements, proposal decisions, interaction details and prompt hashes.
6. Unknown natural-language contradictions require human review: this implementation validates structured constraints but does not claim complete semantic contradiction solving.

## Files

- `src/ucscene/design/planner.py`: planner, opt-in AI call and deterministic prompt compiler.
- `schemas/design-plan.schema.json`: formal candidate-plan artifact.
- `benchmarks/new-products/*.wp02.brief.json`: fictional new desktop asset manager and isometric builder game, each with 3 steps, not existing-product screenshots.
- `tests/test_design_planner.py`: source requirement retention, original candidate variety, exception feedback, AI mock, hard constraints, schema and CLI tests.

## Explicit limitations

- This is **not** a trained layout synthesis or text-to-image model. Heuristic mode is intentionally limited; exact pixel positions are not authored at WP-02.
- Actual OpenAI Responses API design output has **not** been tested against a live API. API compatibility and quality require opt-in acceptance testing.
- AI may produce low-quality UI ideas; tests validate structure and known constraints, not creative merit.
- UI text fidelity remains a concern for WP-04 rendering. The generated prompts must not be represented as running software/screenshots.
- `ucscene generate` still consumes legacy ScenePlan JSON and does NOT yet consume a WP-02 DesignPlan. Exported prompts can be used by an available image model, but automatic generation and revision workflows are WP-04.
- WP-03 is responsible for formal user approval/freeze and longitudinal DesignSystem consistency. Do not treat simple per-candidate coherence as an implemented frozen design system.
