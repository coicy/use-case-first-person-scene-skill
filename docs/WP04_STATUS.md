# WP-04 current state — implementation merged (2026-10-23)

The v0.7 WP-04 source has been merged to main (see repository history) and includes: `concept-packet`, `concept-render`, `concept-gallery`, `concept-verify`. CI is the only source of truth for which Python versions passed.

**Engineering stage complete once CI passes; visual release gate still OPEN.** Real user-visible image model outcomes remain uncertain. Two earlier conversation image attempts produced six-panel montage boards, **violating** the one-step/one-image contract. Six cropped panels are useful for pipeline/gallery tests only, not independent full-frame successful generations.

A new single-frame prompt contract prohibits gallery boards and presentation wrappers for each individual provider request. The human review gallery separately checks whether the final image really obeyed it. This requirement cannot be proven through mocked providers or SHA checks. The CLI does not initiate paid calls without `--execute --max-images N` and an API key.

Refer to `docs/WP04_IMPLEMENTATION.md` for implementation details; WP-05 must perform genuinely independent single-step generations and real human evaluation of two new products before visual acceptance is claimed.
