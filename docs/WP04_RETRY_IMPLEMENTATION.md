# WP-04 visual failure recovery — evidence-bound retries

**Status:** Implemented as an offline retry planning/validation step. It does **not** guarantee a successful image or perform autonomous paid retries. PRODUCT-002 applies: these are ORIGINAL products, not replicas of existing software.

## Why this exists

Real image generation repeatedly returned a 2×3 portfolio/contact-sheet containing multiple unrelated use-case states where one full-bleed software screen was required. The original single-frame prompt contract did not prevent the observed failure. Cropping a contact sheet does **not** count as independently generating six valid steps.

## New CLI commands

- `concept-observe`: self-attested human/assistant observation of the exact image and composition class; **not** a model audit and **not** user approval. It records the actual image hash and links one variant/scene.
- `concept-retry`: accepts a *matching* `concept-audit` output or `concept-observe` record plus the exact image, and builds **one** targeted, immutable render packet and one hash-bound lineage manifest. It never calls the image API.
- `concept-retry-verify`: checks lineage and retry packet integrity.
- Existing `concept-render`: preview is free/offline; actual generation is opt-in with `--execute --max-images N`, model key, and output files.

## Example end-to-end commands

```bash
# One original product, one chosen variant and one step.
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json \
  --variants 2 --out out/planned.json
ucscene concept-packet out/planned.json --mode draft --variant VAR-01 \
  --step STEP-001 --out out/first-packet.json

# After inspecting the ORIGINAL, actual image from any source:
ucscene concept-observe out/first-packet.json \
  --image images/real-failed-output.png \
  --variant VAR-01 --scene new-asset-studio--UC-001--STEP-001 \
  --composition multi-frame-board --software-only pass \
  --observer assistant-visual-observation --out out/observation.json

ucscene concept-retry out/first-packet.json --audit out/observation.json \
  --image images/real-failed-output.png \
  --out out/retry-packet.json --manifest out/retry-lineage.json
ucscene concept-retry-verify out/retry-packet.json --manifest out/retry-lineage.json
ucscene concept-render out/retry-packet.json --out out/retry-dry-run

# Explicit real API execution only if authorized, key available, cost accepted:
# ucscene concept-render out/retry-packet.json --execute --max-images 1 \
#   --out out/retry-generated
```

If a new image also fails, run a **fresh** `concept-audit` or `concept-observe` on **the new retry packet** and image, then pass `--previous-manifest out/retry-lineage.json` to build retry #2. A verified chain cannot request retry #3; escalate for explicit design review.

## What the retry algorithm guarantees

- Original design authority and DesignSystem digest/revision do not change.
- Exactly **one variant and one scene** in each retry packet, even when the initial plan covered multiple screens.
- Hard requirements, exact UI text, states, and original prompt remain included; revisions only ADD bounded, deterministic repair constraints.
- Both original packet and actual image hashes must match the saved visual observation.
- Freeform model/observer advice, reasoning, and correction text are **not** copied into paid generation prompts; only enumerated failure classes and exact original requirements can influence retry text.
- Known composition/physical-boundary/evidence failures can trigger repair even if unrelated evidence is still marked uncertain. An entirely uncertain audit or already-passing one cannot trigger a gratuitous retry.
- Output is new files only; source image remains untouched. Image output still requires a separate explicit authorization.

## What it does NOT guarantee

- An AI image model will comply with single-frame instructions on the second or third attempt.
- A self-attested observation is correct, or made by the real user named in its observer field. It is not an authentication or consent system.
- A retry automatically improves UI design, readable text or visual continuity. Review new output independently.
- Retry manifests are SHA-256 integrity records, **not digital signatures or tamper-proof approval evidence**.
- Model-assisted `concept-audit` is paid and advisory. The offline manual observation is likewise unverified and cannot be substituted for user's visual acceptance.

## Automated acceptance

`tests/test_concept_retry.py`: actual saved PNG inspection, single-item retry, prompt injection isolation, strict packet/manifest digests, stale image rejection, unchanged approved DesignSystem, two-attempt chain cap, unclear findings, CLI observation/retry/review, and no paid calls during offline planning.

`python -m unittest discover -s tests -v`; GitHub Actions Python 3.10/3.12. The visual reference-image failure should be kept as an external review artifact rather than committed binary benchmark ground truth; source requirements for the original product must remain independent of this image.
