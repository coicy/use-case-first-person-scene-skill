---
name: use-case-first-person-scene
# Codex and compatible Agent Skills
# Describes a scene-production workflow; code is the source of runtime truth.
description: Create and check first-person experience scene images grounded in software or game use cases. Trigger for scenario illustrations from the actual actor's viewpoint, multi-step storyboard images, reusable visual anchors, and authentic UI screenshot overlays; not for UML, abstract diagrams or generic concept art.
---

# Use Case → First-Person Scene Skill (v0.3)

Use this skill when a developer requests a **concrete user-experience visual** of a use case or a set of use case steps. Do not silently switch to use-case diagrams, third-person illustrations, polished marketing art, or screenshots purportedly captured from a running application.

## Workflow

1. **Read authoritative requirements:** consult the supplied use-case document, issue, PRD, interface references and/or code. Preserve explicit IDs, actions, states and source evidence. Treat all other details as unresolved.
2. **Extract structured use cases:** use `ucscene extract ...` only for supported Markdown. For truly free prose use `ucscene extract ... --ai` with opt-in provider calls; inspect source-quote traceability and resolve extraction issues before continuing. Never let speculative elements masquerade as documented requirements.
3. **Choose the scenes:** separate main, alternate, exception and success paths. Select distinct visual moments, with one scene per important user-perceived state. Distinguish machine-internal steps (not directly visible) from user-visible evidence.
4. **Plan first-person visuals:** run `validate`, `plan`, `review`. Camera is at the actor's eyes, not outside the actor. Foreground hands appear only when physically plausible. Key controls, object, environment and changed state should be visible, but not invented.
5. **Anchor consistency:** for multi-step output, choose a user-reviewed visual reference of the same scene. Run `anchor-create` (without `--approved` while unreviewed). After a human explicitly approves the image, run `anchor-create --approved --note ...`, then `anchor-verify --plan ... --require-approved`. The manifest hashes the reference and binds it to one use-case anchor.
6. **Generate images if authorized:** `generate --anchor` requires an approved compatible manifest and provider key. The API request may incur cost. If no renderer/key is accessible, supply plans and prompts honestly; **do not claim images were created**. Store provider outputs separately from source assets.
7. **Integrate exact UI when available:** preferably use real designer/developer-provided screenshots (with private data removed) and the offline `compose-ui` or `compose-batch` commands. UI screen quadrilateral must be measured/reviewed in each scene; use normalized TL → TR → BR → BL points. Never depict composited UI as verified functional software.
8. **Review actual results:** use optional `review-image` on final scene PNGs, and manually inspect viewpoint, coherent hand position, UI placement/legibility, required evidence, hallucinated elements, state accuracy and cross-step differences. Flag uncertainty.
9. **Hand off artifacts:** include traceable scene ID, state, source, missing decisions, image paths, relevant SHA reports and whether real API rendering/visual QA took place.

## Non-negotiable constraints

- Requirements and implementation reality outrank artistic plausibility.
- When information is missing, keep an incomplete draft and ask for a decision; never invent devices, states, screen layouts or permissions.
- No third-person hero portrait for the user's first-person use case.
- Neither SHA hashes nor manifest `--approved` automatically validate image semantics.
- Static plan review is not visual image review. Model visual reviews are advisory, not guarantees.
- `compose-ui` preserves source image content under geometric resampling, not guaranteed typographic pixel equality.
- Never commit API secrets, personal information, or private UI screenshots without authorization.

## CLI quick reference

```bash
python -m pip install -e '.[ui]'
ucscene extract examples/warehouse-scan.md --out out/case.json
ucscene plan out/case.json --out out/plan.json
ucscene review out/plan.json
# Once you have checked and approved a suitable reference image:
ucscene anchor-create out/plan.json --image path/to/ref.png --out out/anchor.json --approved --note 'operator reviewed POV and device'
ucscene anchor-verify out/anchor.json --plan out/plan.json --require-approved
# Paid: ucscene generate out/plan.json --anchor out/anchor.json --out out/generated
# Offline: ucscene compose-ui --scene scene.png --ui real-ui.png --quad quad.json --out composed.png
```

See `README.md` for complete commands, `schemas/use-case.schema.json` for structured inputs, `src/ucscene/anchors.py` for manifests, and `src/ucscene/composite.py` for perspective overlay rules. Source of image-generation behavior is `src/ucscene/provider.py`; an approved anchor is not a guarantee that the model's image edit preserves every detail.
