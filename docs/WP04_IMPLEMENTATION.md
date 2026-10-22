# WP-04 implementation — original-product concept image execution and human review

**Status: implemented engineering workflow; model-specific visual quality NOT PASSED.**

Product authority: [PRODUCT-002](PRODUCT_REQUIREMENTS.md). `WP-04` does not implement a working application or turn generated images into user-approved designs. The original image workflow is separate from the previous v0.6 existing-software scene generator.

## Commands and modes

```sh
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/asset-design-plan.json

# Exploratory request for ALL variants, all steps (6 image requests), WITHOUT API spend
ucscene concept-packet out/asset-design-plan.json --mode explore --out out/asset-explore.json
ucscene concept-render out/asset-explore.json --out out/asset-preview
# Result: a manifest with status=pending, no files claiming actual PNG generation

# One unapproved concept proposal for all three steps
ucscene concept-packet out/asset-design-plan.json --mode draft --variant VAR-02 --out out/asset-draft.json

# TARGETED revision does not mutate the original DesignPlan or claim approval
ucscene concept-packet out/asset-design-plan.json --mode revise --variant VAR-02 \
  --change-request 'Improve readability of metadata labels while retaining navigation' \
  --out out/asset-revision.json

# Previously explicitly-approved WP-03 DesignSystem only; no layout changes allowed
ucscene design-system-create out/asset-design-plan.json --variant VAR-02 --approve \
  --evidence-ref 'EXAMPLE-ONLY-USER-SUPPLIED-REFERENCE' --lock --out out/design-system.json
ucscene design-apply out/design-system.json benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --out out/consistent-scenes.json
ucscene concept-packet out/consistent-scenes.json --mode consistent \
  --system out/design-system.json --brief benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --out out/asset-consistent.json
```

**Important:** The commands above that use approval flags are examples of the mechanism, NOT evidence that the user approved any specific UI. The CLI stores self-attested evidence strings; it cannot authenticate the actor.

### Real OpenAI Images API generation (only if explicitly authorized)

```sh
export OPENAI_API_KEY='your-own-secret'    # never put key in repository
ucscene concept-render out/asset-draft.json --execute --max-images 3 \
  --model gpt-image-1.5 --size 1536x1024 --quality medium \
  --out out/asset-images

# Optional: choose a single fixed visual reference instead of blindly chaining
ucscene concept-render out/asset-draft.json --execute --max-images 3 \
  --reference-image images/your-approved-concept-reference.png \
  --out out/asset-images-with-reference
```

`--execute` AND a sufficient `--max-images` cap are mandatory. Each request may incur fees; the cap limits calls, not total currency cost. No implicit retries, unbounded batches, or tests/CI paid calls. The provider must return genuine image bytes, which are decoded and hashed before recording as generated. Chained edits (`--chain`) are supported only within a single candidate to avoid blending mutually exclusive proposals; visual drift remains possible.

## Gallery of real original-product images

For images created by this CLI, require the successfully completed report:

```sh
ucscene concept-gallery out/asset-draft.json --images out/asset-images \
  --report out/asset-images/generation-report.json --out-dir out/asset-review
ucscene concept-verify out/asset-review/manifest.json
# Open out/asset-review/index.html, evaluate each frame and export human-concept-review.json
```

For images produced by a different provider or **in this chat**, use explicit external metadata:

```json
{"samples":[{"variant_id":"VAR-02","scene_id":"new-asset-studio--UC-001--STEP-001","image":"asset-01.png","origin":"conversation-image-generation","notes":"External generation; prompt not identical to CLI scene prompt"}]}
```

```sh
ucscene concept-gallery out/asset-draft.json --images examples/external-pngs \
  --selection external-images.json --out-dir out/asset-review
```

An externally imported image **cannot** assert `ucscene-cli` provenance or a verified current prompt hash. The image hash does NOT prove that the image follows the intended prompt or was generated separately. The HTML review captures six dimensions and explicit user verdicts; it does not automatically approve candidate designs.

## Real visual evaluation on 2026-10-22

- The conversation image generator produced **two** real PNG comparison boards for two fictional new products, but **both violate the one-frame-per-use-case-step boundary** because the model composed explanatory six-panel boards.
- Six screenshot-like UI regions were extracted via exact non-generative cropping from one comparison board (3 desktop + 3 builder game), then imported into two honest external-provenance galleries. This tests real-image integrity, rendering/manifest packaging and reviewer UX, **not independent CLI image generation**.
- No paid OpenAI API call from the `ucscene` CLI was made: `OPENAI_API_KEY` was not available in the working runtime. All provider tests use small, valid mock image files.
- Image-level accuracy, text legibility, and multi-step visual continuity need external review. The third game step depicts an unconfirmed assignment panel rather than unambiguous post-confirmation success, so it should not be pre-approved.

## Engineering validation and limitations

- `concept-packet`: verifies the full source DesignPlan or WP-03 ConsistentScenePlan; preserves prompt hash, candidate, use-case IDs, required evidence and approved baseline digest.
- `concept-render`: offline by default, paid API only with explicit flags; refuses file overwrite, cross-candidate image chain, unsafe file names, changed packets, missing key and exceeding explicit cap.
- `concept-gallery`: accepts decoded PNGs, hashes, external provenance; writes self-contained offline review UI with export and no fake human verdict.
- `concept-verify`: validates image bytes and manifest integrity only, never model semantics or screenshot authenticity.
- Image API outputs may render gibberish UI text or disregard single-frame instructions; conceptual designs must be reviewed. Chained images may drift; image similarity and semantic consistency are not automatically established.

### Next — WP-05

Create several **independently generated** single-frame PNGs for each original product, do two-candidate comparisons with exact per-scene prompts and collect manual acceptance by actual evaluators. Fail screenshots that are infographics, explanatory multi-panels, real physical-device photos or missing the stated use-case action. Report both passed and failed examples.

## Single-frame contract (post-acceptance regression)

Every request is scoped to exactly **one** software/game state and prepended/appended with a non-negotiable single-frame composition rule. Montage, contact sheet, storyboard, step captions and portfolio boards are explicitly forbidden. The offline packet validator rejects contract tampering. The acceptance gallery includes a distinct **single-frame** human review criterion. This is a **prompt and provenance guard**, not proof that an image model will obey; real images require visual inspection and failures must stay recorded. Crops from a generated collage are external derived samples, not independent successful generations.

## Optional single-frame visual audit (added after repeated collage failures)


define exactly one existing render packet item, then execute:

```bash
ucscene concept-audit out/concept-packet.json \
  --image out/generated/VAR-01--PRODUCT--UC--STEP.png \
  --variant VAR-01 --scene PRODUCT--UC--STEP \
  --out out/concept-audit.json
```

This command **explicitly opts in to a potentially paid vision API request**. It uses a structured independent assessment of whether the pixels show a single complete app/game state or a montage, whether outside-software imagery exists, and whether visible evidence appears. It records the real PNG SHA-256 and original prompt digest. Model judgments can be wrong; `advisory-pass` is NOT a human signoff. A montage requires manual rejection/revision and should not count as a successful generated use-case image.
