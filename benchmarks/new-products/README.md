# v0.7 WP-01 — Original product model fixtures

These are **new products**, not attempted screenshots of any existing software.
The initial ProductBrief captures the user's proposed product concept and the
first use case. The DesignBundle contains one unresolved scene scaffold with
**no approved design decisions**. These are not images and do not demonstrate
an operational UI/UX design engine (WP-02) or multi-scene visual consistency.

Examples:
- `new-asset-studio`: a new desktop asset management application
- `new-hamlet-builder`: an original isometric building game

```sh
ucscene design-validate benchmarks/new-products/new-asset-studio.brief.json --kind brief
ucscene design-validate benchmarks/new-products/new-asset-studio.bundle.json --kind bundle
ucscene design-validate benchmarks/new-products/new-hamlet-builder.brief.json --kind brief
ucscene design-validate benchmarks/new-products/new-hamlet-builder.bundle.json --kind bundle
```

The user's actual approvals are separate actions in a future implementation;
no test fixture declares that any AI-created proposal has been approved.
