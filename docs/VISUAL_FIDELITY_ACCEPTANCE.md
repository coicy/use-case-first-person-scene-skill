# Visual fidelity acceptance protocol (PRODUCT-004)

## Mandatory independent scores

For each screen (or each screen inside a requested storyboard), preserve:
- product_id, use_case_id, step_id, design_system_revision, scene_id
- image_sha256 and the exact image file path
- intended image organization and actual observed organization
- required navigation and layout regions; expected component tree/selection relations
- supported user actions, effect and error states, known values/labels
- origin of any unconfirmed visual proposal

Rate the following **independently**, never through one aggregate "looks good" score:

| Dimension | Observation required | Example of FAIL |
| --- | --- | --- |
| identity | Actual software/game category and product match | Game scene replaced by file manager |
| layout | Relative placement and hierarchy of required sections | Approved bottom command toolbar disappears |
| structure | Components and object associations are coherent | Farm selected, warehouse details shown |
| functionality | Present actions make the use case executable and results sensible | Nonexistent save method or missing confirm |
| state | State and values match current step and causal continuity | Failure case shows successful save |
| evidence | Required on-screen clues and exact text are visible | Filter chips absent in filtering step |
| presentation | Requested output organization (single/multiple) is followed | Unrequested 2×3 marketing board |

Mark `pass`, `fail`, `uncertain`, or `not_applicable`; give brief visible grounds. Do not infer executable functionality solely from a static image.

### Decision rule

- Any identity/layout/structure/functionality/state failure against **confirmed or approved** contracts => **semantic rejection** regardless of format or visual beauty.
- In a still-unapproved concept alternative, the choice of layout may differ from another candidate, but it must be internally realistic and clearly documented as `proposed`; it must not violate user requirements.
- Any `uncertain` on a required semantic dimension => hold for review, never silently convert to pass.
- A requested multi-screen board passes only if **every panel** independently passes required semantic checks, cross-panel design continuity holds, and its presentation format matches the request.
- A single frame can be failed for product/function inconsistency even if framing is correct.
- Reviewer records are advisory unless a real user approves the selected design. CI/mock tests cannot prove visual accuracy.

### Two mandatory new-software regression examples

1. Asset Studio, filtering → detail → save failed: UI library/sidebar and labels consistent; filter visibly changes result set; selecting a model shows its matching details; `保存失败` must not coexist with a success confirmation for that same action.
2. Hamlet Builder, select farm → view production → assign worker: same isometric town; same farm remains selected; production information belongs to that farm; assigning a worker produces a sensible worker count/state, not an unrelated construction screen.

### WP-05 implementation follow-up

1. Evolve `concept-audit` and human-review export to include separate identity/layout/structure/functionality/state/evidence/presentation findings and bound source IDs.
2. Encode structural and functional facts in a Product UI Contract, not only freeform prompt text; include component and action/state relations.
3. Make semantic failures block "passed" regardless of composition; handle multi-panel independently when the **requested deliverable** includes multiple scenes.
4. Regression tests: a well-styled and correctly formatted **wrong-function** image MUST fail; a useful user-requested storyboard with correct panels MUST NOT fail just for being multi-panel.
5. Re-run two original-product three-step benchmarks with real agent images; human verdicts required for actual vision quality. Prompt hashes and static tests are insufficient.
