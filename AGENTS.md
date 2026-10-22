# Engineering Agent Contract

## Purpose and boundaries

Maintain an installable first-person scene generation skill for software/game use cases. UML diagramming, generating a working UI prototype, and ungrounded lifestyle art are outside the v0.1 scope.

## Architecture

- `src/ucscene/core.py`: standard-library-only validation, anchors, deterministic prompts, and static audits. No network.
- `src/ucscene/cli.py`: explicit command dispatch and reports. No hidden network calls.
- `src/ucscene/provider.py`: opt-in image API adapter, must not log secrets or provider bodies.
- `schemas/`: formal use-case contract (synchronize with runtime validation).
- `examples/`: realistic inputs with happy/exception paths.
- `tests/`: offline regression suite, including mocked paid-provider tests.
- `.github/workflows/`: CI may validate and test but must never incur paid API usage.

## Rules for every code change

1. Preserve Python >=3.10 compatibility and local installability.
2. Identical inputs must generate byte-for-byte stable prompts and prompt hashes.
3. Each scene maps to a source use-case step and non-empty visual evidence.
4. Keep true first-person POV; do not substitute third-person explanation pictures.
5. Do not invent business requirements when source data is missing.
6. Keep image-generation credentials in environment, not files or logs.
7. Distinguish structural review, provider request success, and human image inspection.
8. Write regression tests for new constraints, failure branches, injection of unsupported states, and path handling.
9. Update README, examples, schema, and implementation together when contracts change.

## Merge gates

Run `python -m unittest discover -s tests -v`, install the package locally, and smoke test `ucscene validate/plan/review` against the included warehouse example. No paid API call is required for CI.
