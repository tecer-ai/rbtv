---
description: "The validation component — milestone 2 of the innovation trail: stress-testing a business concept against evidence before any resource is committed to it. Seven references carry the frameworks (assumption surfacing, assumption scoring, market sizing, unit economics, technical readiness, pre-mortem, V1 scoping)."
---

# validation

The frameworks that ask *what must be true, what evidence do we have, and what would change our
mind* about a business concept. An agent enters here to run one of them with a founder, or to check
a founder's existing analysis against the framework's shape and quality bar.

The boundary with the sibling `conception/` component: conception PRODUCES the concept (customer,
problem, value proposition, business model); validation tests whether that concept survives
contact with evidence and pre-commits the founder to kill/pivot/persevere rules. A statement made
in conception is an input here, never re-derived here.

| Part | What it is |
|---|---|
| `references/leap-of-faith.md` (reference) | Surfacing every untested belief in the concept, classifying it Value or Growth, ranking it by impact × uncertainty, and pre-committing kill/pivot/persevere criteria. The first framework of the milestone and the source of its agenda. |
| `references/assumption-mapping.md` (reference) | Scoring assumptions on importance × uncertainty, placing them in a Test / Accept / Monitor / Ignore matrix, and writing a test card for every Test assumption. |
| `references/tam-sam-som.md` (reference) | Market sizing by two independent methods (top-down and bottom-up), the SAM narrowing waterfall, and building SOM from go-to-market capacity rather than a share percentage. |
| `references/unit-economics.md` (reference) | The economics of one customer — lifetime value, acquisition cost, their ratio, payback period, break-even, and sensitivity analysis across pessimistic/base/optimistic scenarios. |
| `references/technology-readiness-level.md` (reference) | Rating each technical component on the NASA 1–9 readiness scale with evidence, and designing a spike for every component below level 4. |
| `references/pre-mortem.md` (reference) | Prospective hindsight — declaring the venture failed twelve months out and explaining why, then ranking failure modes and writing mitigations with early-warning signals. |
| `references/v1-scoping.md` (reference) | Cutting a testable V1 from a product definition: the minimum flow, conscious exclusions, operational workarounds, and the hypothesis V1 exists to test. |

## Entry points

- `references/` — one file per framework, read on demand; the trail sequence and the run pacing
  live in the sibling `trail/` component, not here.
- No exposure manifest: no part of this component is exposed on its own. The frameworks are reached
  through the trail reference and the innovation-mentor prompt, which is a sanctioned state per the
  reference kind's default, not a gap to fill.

## Origin (owner-ruled 2026-08-21)

Migrated from the old rbtv innovation module at
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/`, whose six frameworks were
each a multi-step workflow with its own menu, state frontmatter, and memo-update machinery. Only
the framework substance and its quality bar were carried; the step machinery, navigation codes, and
per-step state were deliberately dropped — pacing and state belong to `trail/`.

`references/v1-scoping.md` was folded in from
`3-resources/tools/rbtv/innovation/workflows/product-discovery/` (step 05) under the owner's ruling
to include that workflow's value rather than copy it verbatim, and without minting a fourth
milestone. Its sibling folds — benchmark analysis and product landscape — went to `conception/`.
