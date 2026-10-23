# PRODUCT-003 — Prefer the host Agent's native image-generation tool

**Status:** Authoritative product decision (2026-10-24).

This repository is an Agent Skill for generating concept images of NEW software and games from prompts and use-case steps. The primary image provider is the **host Agent's available image-generation tool**. A separate Images API credential is NOT a prerequisite for ordinary use.

## Provider precedence

1. Inspect the image-generation capabilities actually offered by the host Agent. If available, use the native tool directly, **one product and one use-case step per generation call**. Never submit an entire packet, storyboard, or multiple candidates to one image request.
2. Export verified per-scene prompt files with concept-agent-export; the Agent calls its tool and saves the actual resulting PNG.
3. Import through concept-agent-import, verify bytes and request linkage using concept-agent-verify, then review with concept-gallery. Where useful, record Agent visual observations using concept-observe, clearly distinguished from the user's design approval.
4. If the host tool cannot save an accessible file, report that limitation rather than inventing an import or claiming a successful generation.
5. If no usable native image tool is available, a separate Images API via concept-render --execute is an **optional, explicitly user-authorized fallback**. Never silently call a separately billed API.

## Trust boundaries

A portable Python CLI cannot invoke arbitrary host-private tools; the handoff must be orchestrated by the Agent itself. An exported prompt is not an image. An imported PNG and SHA-256 prove only the image bytes and the declared scene mapping; actual tool identity, tool-call IDs and prompt submission are **self-attested**, not verified server receipts. Do not fabricate invocation IDs, response summaries, or a user's approval. An Agent's own visual review is useful but is NOT authenticated human sign-off.

PRODUCT-002 remains authoritative about designing original interfaces for not-yet-built software; PRODUCT-001 requires the image to contain only the software/game screen, not a real user or device.

## Acceptance

- Each original product has an independent handoff, unique product/scene/step IDs and prompt hashes.
- Tampered prompts, wrong-product mapping and modified image files are rejected.
- The host tool is called separately for each scene when actually generating images.
- The API-independent handoff/import is exercised without keys in CI; actual image quality still requires real image outputs and review.
