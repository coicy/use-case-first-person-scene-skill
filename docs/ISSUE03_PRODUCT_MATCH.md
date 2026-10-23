# Issue #3 — Target product identity / cross-product contamination repair

**Status:** Engineering implementation & local regression complete. Real Images API and model-vision end-to-end remain **not tested**; the previous real wrong-product image is still a visual failure.

Authority: [PRODUCT-002](PRODUCT_REQUIREMENTS.md). This tool designs **new** original software/game scenes; exact existing-software screenshots are not required. Every deliverable must depict **only the designated product and one use-case step**.

## Observed defect

The saved 2026-10-24 experiment contains three independent images. All are single-frame software interfaces, but only the first matches the intended application. The other two, requested as the original isometric town-building game, depict the previously used asset-manager application. The prior `concept-audit` checked single-frame layout and software-only scope but had no separate product-identity field. The prior `concept-retry` therefore could not repair a single-frame, software-only image that belonged to the wrong product.

**Causal limitation:** These images came from the conversation image-generation route. Their returned image descriptions were also asset-manager descriptions. This suggests a request/context route mismatch; it does **not** establish a bug in the repository's live Images API route. No key was available for a real paid end-to-end check.

## Engineering changes

1. **Audit 1.1:** `target_product_match` = `pass | fail | uncertain` and `product_match_reason` are independent of `composition`, `software_only`, and step evidence. A pass across other fields **cannot** yield `advisory-pass` if product matching is fail or uncertain. The vision reviewer receives the exact source product/step prompt as read-only task data.
2. **Operator observation 1.1:** `concept-observe --product-match fail` records a self-attested observation. Omission defaults to `uncertain` (never success). This is **not** authenticated user approval.
3. **Corrective retry:** Explicit `target_product_match=fail` generates a deterministic `wrong-product` repair category in the one-step retry packet. Original `product_id`, step, source requirements, selected design, and prompt digest lineage remain unchanged. Untrusted reviewer reasons and free-form suggestions are **not** inserted into the retry prompt.
4. **Request identity binding:** New `concept-render-packet` version `1.1` includes `TARGET IDENTITY JSON` (product, variant, scene, step) inside each individual image prompt. `verify_render_packet()` checks this exact binding even if someone recomputes the outer hash. A generated report also records `product_id`, `identity_bound`, and the submitted prompt hash and rejects mismatched entries.
5. **Migration:** Render packet `1.0` can still be loaded and integrity-checked, but cannot be used for **new paid image execution**. Regenerate using `concept-packet` to receive version 1.1. Old audit `1.0` reports remain acceptable to `concept-retry` for their explicitly known failure classes, with product matching treated as **uncertain**, not implicitly passed.
6. **Conservative limits:** Two retries maximum across a verified chain. `concept-retry` itself never calls a paid API. Real model outputs and visual quality require separate inspection.

## Real-file failure reproduction (offline)

```bash
ucscene design-plan benchmarks/new-products/new-hamlet-builder.wp02.brief.json \
  --variants 2 --out game-design-plan.json
ucscene concept-packet game-design-plan.json --mode draft --variant VAR-01 \
  --step STEP-001 --out game-packet.json
ucscene concept-observe game-packet.json \
  --image wrong-product-real-image.png --variant VAR-01 \
  --scene new-hamlet-builder--UC-001--STEP-001 \
  --composition single-frame --software-only pass --product-match fail \
  --observer assistant-visual-observation --out wrong-product-observation.json
ucscene concept-retry game-packet.json --audit wrong-product-observation.json \
  --image wrong-product-real-image.png \
  --out retry-packet.json --manifest retry-lineage.json
ucscene concept-retry-verify retry-packet.json --manifest retry-lineage.json
ucscene concept-render retry-packet.json --out retry-dry-run
```

**Observed result:** 1 retry packet for `new-hamlet-builder--UC-001--STEP-001`, failure category `wrong-product`, verified image SHA-256 and lineage, no generated PNG, no paid API request. In the submitted reproducer, image SHA-256 is `4b510fb4faded9e70df1189e91ad0413f3f77d28988077cd9d18bf5ed428ad37`.

## Tests and remaining gate

- Python 3.10/3.12 CI should run `python -m unittest discover -s tests -q`.
- Unit tests verify wrong-product failure despite single-frame success, uncertainty handling, digest/identity tampering, cross-product prompt isolation through injected fake provider, old packet compatibility, no paid API calls during retry creation, and CLI end-to-end request/observation/retry/verify.
- Fake provider tests validate the **prompt selected and passed** to the provider. They cannot prove the external model obeys it.
- Release gate remains open until independent real images from the actual CLI Images API are generated for both fictional products, evaluated for product type, step content, software-only boundary and single-frame composition, and reviewed by a person.
