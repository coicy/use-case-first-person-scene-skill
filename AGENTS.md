# Agent Engineering Contract — Use Case First-Person Scene Skill

## Goal and boundaries

Maintain an installable, source-grounded, true first-person experience visualization tool for software and game use cases. Do not add UML chart generation or confuse generated illustrations with finished UI or implementation proofs.

## Code ownership and architecture

- `src/ucscene/core.py`: deterministic validation, scene anchor, prompts and static plan audit. **No network**.
- `src/ucscene/extractor.py`: conservative offline extraction from structured Chinese/English Markdown; never infer missing evidence.
- `src/ucscene/ai_extract.py`: opt-in freeform extraction through source-quote-validated structured model output.
- `src/ucscene/responses.py`: explicit opt-in OpenAI Responses request and image payload adapter.
- `src/ucscene/vision.py`: reference-image optional visual audit. AI judgement is advisory; uncertain is not pass.
- `src/ucscene/provider.py`: explicit image generation or reference-based editing. No secret logging; test with mocks only.
- `src/ucscene/cli.py`: CLI commands, robust error reporting and file output. No hidden paid calls.
- `schemas/`: user input contract; preserve backwards compatibility with v0.1 JSON data.
- `examples/`: checked-in source-backed normal and exception cases.
- `tests/`: offline regression tests, HTTP payload mocks, failure cases.
- `.github/workflows/`: no secrets or real image generation requests.

## Product invariants

1. Only a stated visual requirement can become required visual evidence. The agent must record explicit manual decisions separately.
2. Do not silently fill unknown actor, environment, device, workflow state, UI copy or background actors.
3. Eye-level first-person POV is mandatory for each rendered scene, not a third-person shot with an implied user.
4. One canonical actor/environment/device/style anchor per use case. Reference edits improve continuity but cannot guarantee identity or geometry.
5. Scene prompt generation is deterministic given the same structured inputs; prompt SHA-256 must remain stable.
6. Source case ID and step ID must survive planning. Any new output must preserve source traceability.
7. Static review is not image inspection; visual model review is not human sign-off.
8. API key stays in environment only. Do not print raw provider response or include private prompts/images in version control.

## Completion gates

- `python -m unittest discover -s tests -v` passes offline on Python 3.10 and 3.12.
- CLI `validate`, `extract`, `plan`, `review` succeed for checked-in normal examples.
- Missing visual evidence or missing key fields yields an **unready draft** and blocks planning.
- Real paid requests are made only by explicit commands; integration tests mock the provider.
- Release notes explain untested assumptions and model nondeterminism.
