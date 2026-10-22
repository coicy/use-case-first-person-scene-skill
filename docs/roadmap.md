# Roadmap

## v0.1.0 — initial working skill

- Structured use case JSON, deterministic prompt plans, POV constraints, generation provider, offline tests and CI.

## v0.2.0 — grounded extraction and visual QA (implemented)

- Offline Chinese/English Markdown extraction with unready draft mechanism.
- Opt-in freeform AI extraction with exact source quote checks.
- Reference-based image editing and optional sequential chaining.
- Vision-based advisory image quality check for POV, visible evidence, exact UI text and optional reference continuity.
- Mocked provider tests and CI smoke test.

## v0.3.0 — higher-fidelity representation

- Support for document/PRD import, explicit source provenance spans and image archetypes by use case type.
- Reusable manually reviewed scene anchor asset library, style manifests and composition maps.
- Verified UI screenshots composited into generated scene frames to avoid synthetic/incorrect lettering.
- Visual QA metrics with multiple independent reviewers and stability experiments.

## v1.0 — engineering integration

- Incremental regeneration after requirement changes; trace from cases to assets and release reports.
- Optional design review workflows, versioned image anchors, cost ceilings and budget reporting.

## Non-goals

- Generated images are not proof of functioning software or business logic.
- Model-generated exact text is not reliable and cannot replace verified UI overlays.
- The skill does not guarantee background, object, or identity consistency between images.
