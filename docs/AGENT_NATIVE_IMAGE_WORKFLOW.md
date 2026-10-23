# Agent-native concept image generation — default workflow

This Skill is an Agent workflow, not a standalone API integration. When the host Agent supports image generation, use it FIRST.

## Step 1: prepare ONE scene request

```bash
ucscene design-plan benchmarks/new-products/new-asset-studio.wp02.brief.json --variants 2 --out out/plan.json
ucscene concept-packet out/plan.json --mode draft --variant VAR-01 --step STEP-001 --out out/packet.json
ucscene concept-agent-export out/packet.json --out-dir out/host-tasks
ucscene concept-agent-verify out/packet.json --handoff out/host-tasks/manifest.json
```

The Agent reads only the text file under out/host-tasks/tasks/ for the requested step, calls its **own image generation tool**, and saves that actual PNG to out/host-images/step1.png. Do not pass a multi-step plan or any other product's context to the image tool. Three steps require three independent images.

## Step 2: record output provenance

Create out/results.json (file is relative to the host-images directory):

```json
{"images":[{"variant_id":"VAR-01","scene_id":"new-asset-studio--UC-001--STEP-001","file":"step1.png","tool":"host-Agent-native-image-tool"}]}
```

If the host can capture the actual submitted text, save it in a UTF-8 file and add submitted_prompt_file to the mapping, relative to results.json. Do not fill this field with merely the planned prompt unless it truly was submitted. The tool name is a self-reported identifier; include tool_call_ref only if a genuine reference exists.

## Step 3: import, verify, review

```bash
ucscene concept-agent-import out/packet.json --handoff out/host-tasks/manifest.json --mapping out/results.json --images out/host-images --out-dir out/received
ucscene concept-agent-verify out/packet.json --handoff out/host-tasks/manifest.json --import-manifest out/received/manifest.json
ucscene concept-gallery out/packet.json --images out/received/images --selection out/received/gallery-selection.json --out-dir out/gallery
ucscene concept-verify out/gallery/manifest.json
```

Open out/gallery/index.html, inspect one-step composition, product match, visible evidence, UI legibility and continuity. An Agent can use its own visual capabilities to record a self-attested concept-observe finding without requiring the separate paid concept-audit endpoint. A visual finding is not a user's sign-off.

If an image fails, create a single-scene concept-retry packet and repeat the Agent handoff. Do not treat imports from earlier conversations as current generation successes.

## Optional standalone API fallback

Only with explicit user authorization for separately billed calls and configured credentials:

```bash
ucscene concept-render out/packet.json --execute --max-images 1 --out out/paid-api-fallback
```

Do not default to this method or demand OPENAI_API_KEY when native host generation is available.
