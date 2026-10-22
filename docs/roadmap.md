# Development roadmap

## v0.1 — functioning baseline

- Structured use case to first-person scene plan and prompts.
- Source traceability per step, anchored consistent environment.
- Optional explicit provider-based PNG rendering and offline static plan review.
- CLI, example, JSON schema, offline tests and CI.

## v0.2 — visual grounding

- Optional PRD and markdown extraction using an LLM adapter, with source quotes.
- Archetype library for POS, warehouse, kiosk, desktop, mobile, and in-game interactions.
- Vision-assisted quality review for viewpoint, required evidence and invented objects; human review remains required.

## v0.3 — continuity and UI accuracy

- Reference-image/edit-mode continuity and visual anchor assets.
- Screen overlay or screenshot compositing for exact UI.
- Delta regeneration on changed use cases, revision tracking and QA reports.

## v1.0 — repository integration

- Trace asset filenames to use case ids and specifications.
- Incremental CI checks of changed use cases with opt-in image budgets.
- Continuity QA for scene batches.

## Non-goals

- Replacing requirements or test cases with generated images.
- Fabricating complete UX flow from an underspecified story.
- Guaranteeing typography fidelity from image models.
