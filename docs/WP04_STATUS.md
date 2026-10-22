# WP-04 implementation status — 2026-10-22

**Status: local engineering implementation and real-image gallery demonstration; pending merge of source changes and independent visual acceptance.**

This note is authoritative about *the limits of the current WP-04 validation*. The main GitHub branch remains at WP-03 for the new rendering CLI unless and until a commit with code files is merged. Do not advertise WP-04 features as available in a fresh clone solely because this status note exists.

## Locally implemented and tested

- New commands under a proposed source patch: `concept-packet`, `concept-render`, `concept-gallery`, `concept-verify`.
- Rendering modes: `explore`, `draft`, `consistent`, `revise`.
- Explicit opt-in `--execute --max-images N` required before actual paid image API use; offline request preparation is the default.
- Real PNG hashes, plan/variant/step mapping, design-system revision/digest and explicit separation of CLI-generated vs external image provenance.
- Human-reviewed HTML acceptance galleries; generating or hashing an image is never an automatic sign-off.
- Local regression: **162 Python unit tests passed** (151 baseline + 11 WP-04-specific).
- CI status **not yet measured for WP-04 source**; previously passing WP-03 Actions cannot be counted as WP-04 CI.

## Actual image-generation finding

Two chat image-generation attempts produced six-panel presentation boards, violating the contract that one concept image must depict a **single use-case step within the new software/game**. Six individual UI areas were manually cropped from one board and imported as external samples (three new creative-asset application states, three fictional medieval town-builder states). This verifies external-image/gallery integrity, NOT six independent image-generation requests.

No image generation was executed through the new CLI with an online API key. A third game step still looks like an unconfirmed assignment operation rather than a clearly completed successful assignment; it needs visual revision and manual acceptance.

## Release gate

Do not close WP-04 as fully **visual-quality passed** until: (1) source changes merged and Python 3.10/3.12 CI passes; (2) independent full-bleed, single-state images generated using actual scene prompts; (3) real humans review each image's use-case coverage, clarity, visual quality and inter-step consistency.

The full source patch and real-image acceptance package were delivered as downloadable artifacts in the associated ChatGPT conversation; they are not source files in this GitHub commit.
