# WP-05 — Agent-native prompt routing preflight

Product decisions: PRODUCT-002 (original new software concept visuals) and PRODUCT-003 (host-Agent native generation first).

## Observed host limitation — 2026-10-24

Two independent ChatGPT host image-generation responses yielded six-frame storyboard boards despite requests to render ONE software-internal step. They do not count as independently generated acceptance images. In this run the available host route could not accept and isolate the exact per-step prompt from the CLI handoff. This is **not** evidence that the standalone repository Images API route has the same behavior.

The test package `ucscene-wp05-agent-20261024-failed-experiment.zip` contains both real 1536x1024 failures, each image SHA-256, six distinct offline step packets, two assistant visual observations and one hash-bound retry packet. No model-vision audit or owner approval is claimed.

## New fail-closed preflight

Command:

```sh
ucscene concept-agent-preflight out/packet.json --capabilities out/native-tool-capabilities.json --out out/preflight.json
```

Example capabilities file:

```json
{"format_version":"1.0","tool_id":"my-agent-image-tool",
 "explicit_prompt_supported":true,"one_image_per_call":true,
 "prompt_isolation_supported":true,"png_output_available":true,
 "submitted_prompt_record_available":false}
```

The four first Boolean capability flags must all be true. If not, the CLI writes a hash-bound report with `route=host-native-blocked`, lists missing capabilities, and exits 4. It never calls the image provider, does not authorize API charges and cannot claim design approval. Host capability data is a **self-reported declaration**, not proof of actual prompt execution.

For the observed host in this test, the explicit prompt and context isolation flags are false. This produces `host-native-blocked`. The correct next step is to use a prompt-addressable host image tool or an isolated execution context. A separately billed image API remains an optional **explicitly authorized** fallback, never an automatic switch.

Only after a provider passes this routing preflight should the Agent call `concept-agent-export`, submit each task separately, and `concept-agent-import` the actual PNGs. Confirm submitted-prompt provenance when available; human review of the actual images remains mandatory.
