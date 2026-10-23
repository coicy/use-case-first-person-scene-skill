# WP-05 — 2026-10-24 real API acceptance checkpoint

**Status: blocked by missing API credentials; no image generated through the repository CLI in this execution. Not a passed visual acceptance.**

Authority: PRODUCT-002 / new-product original software-only use-case images. Baseline: main `b41d658` (194 preexisting offline tests pass).

## Commands actually executed

Two separate products were planned and validated using `design-plan --variants 2` and `concept-packet --mode draft --variant VAR-01 --step STEP-001`:
- `new-asset-studio`: asset tag filtering.
- `new-hamlet-builder`: isometric farm selection.

For each product, `concept-render` created a pending preview, then `concept-render --execute --max-images 1` was **actually attempted** with `gpt-image-1.5`, `1536x1024`, `quality=medium`.

Both attempts failed *before sending HTTP* with `OPENAI_API_KEY missing. The render packet is valid, but no image request was sent.` Thus: **actual HTTP image requests 0; responses 0; CLI-generated PNGs 0**. The two model-audit attempts on historical images were likewise stopped by absent credentials.

A six-step expansion was prepared offline, not executed: each product has `STEP-001`, `STEP-002`, `STEP-003`, a distinct `TARGET IDENTITY JSON` and a SHA-256 prompt hash. Total ledger entries 8 (two probes plus six expansion entries), planned unique steps 6. Only a *real* successful and human-reviewed two-image probe can unlock the full six-image run. No user's design approval is assumed.

## Previous images and honest visual findings

Two real images from **previous ChatGPT conversation generations**, not this CLI, were inspected:
- Asset application: one valid software-only frame with selected castle category, but unrelated asset types remain visible; strict tag filtering appears inconsistent.
- Intended town-building game: still depicts the Nebula Assets desktop app; wrong product, despite single-frame composition.

The `concept-observe` results were marked `assistant-visual-check-not-human`. The game image successfully triggered offline `wrong-product` `concept-retry`, and SHA-256 lineage verified. **No model image audit or paid retry occurred, and user/human approval remains pending.**

## Engineering improvements

- GPT Images provider now returns a safe response metadata summary: optional actual response ID/time, image count and numerical token usage. Never stores base64 image content or raw response secrets in JSON.
- `concept-render` includes this summary in each generated image record alongside product/scene/step IDs, prompt hashes, model and actual PNG digest.
- Added `WP05 Manual Original-Product API Probe` as **workflow_dispatch only**, never run on push or PR. It requires user typing `YES`, repo Secret `OPENAI_API_KEY`, and runs two independent capped image requests and two paid advisory model audits. On success or failure it uploads actual artifacts for human inspection.
- Extensive local reproducible runner, all six exact packets, command trace and earlier-image galleries are delivered separately as the WP-05 acceptance archive. No container key means this is a preparation and negative-path test, not actual provider success.

## Next gate

1. Repo owner configures OPENAI_API_KEY as a GitHub Actions secret (do not post it in chat or commit it).
2. Manually run **Actions → WP05 Manual Original-Product API Probe → Run workflow**, typing YES. Actual API usage incurs cost.
3. Review *two actual* independent PNGs and model-audit outputs; do not substitute model judgment for user acceptance.
4. Only after two real probes pass, run three consecutive independent steps per product, record each provider response, verify output hashes, perform human review and execute real retries for real failures.
5. Keep WP-05 and Issue #2 open until all six valid API-generated frames are human accepted.

**No model-success rate can be inferred from 194 baseline tests, mock calls, hashes or historical chat images.**
