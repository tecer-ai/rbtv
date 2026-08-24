---
description: "The innovate module — taking a business idea from conception through validation to a brand book, and the individual innovation frameworks that do that work."
---

<module>

# innovate

`innovate/` hosts the components that work a VENTURE: an idea, a product, or a brand of the user's
own, taken forward through named business frameworks. Three components carry the frameworks
themselves, one carries the journey through them. The boundary against `core/functions` is the
SUBJECT, not the activity: `brainstorm` and `interview` there are generic cognitive functions that
run on any subject at all; the frameworks here only make sense against a venture, and each one has a
fixed structure and a defined output. Generic idea generation or problem structuring with no venture
in front of it belongs to `core/functions`, not here.

## Components

| Component | What it is |
|-----------|-----------|
| `conception/` | M1 Conception — structuring a raw idea into a business concept: Working Backwards, Jobs-to-be-Done, Competitive Landscape, Problem-Solution Fit, Lean Canvas, Five Whys, plus the benchmark-analysis and product-landscape references folded in from the old product-discovery workflow. |
| `validation/` | M2 Validation — testing whether the concept holds: Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, Technology Readiness Level, Pre-mortem, plus the V1-scoping reference folded in from the old product-discovery workflow. |
| `brand/` | M3 Brand — turning the validated concept into a brand: Brand Archetypes, Brand Prism, Golden Circle, Brand Positioning, Tone of Voice, Messaging Architecture, and the Brandbook that consolidates them. |
| `trail/` | The journey itself — the M1 → M2 → M3 sequence, its minimal per-project state and resume protocol, and the mentor persona that runs it conversationally. This is the module's front door: both exposed parts live here. |

## Why this module exists (owner-ruled 2026-08-21)

The rbtv repo's `innovation/` module (`3-resources/tools/rbtv/innovation/`) is OLD-standard — a
module-root `exposure.csv`, no `component.md` anywhere — and is therefore invisible to `install2.py`
by design. It could not be upgraded in place, so its content was migrated here, into mirror
standards. That old module is superseded by this one, and was DELETED from the rbtv repo on
2026-08-21 (owner-directed; rbtv commit `fef8f455` — its content survives in that repo's git
history; recovery pointers in `trail/component.md` § "Mapped but not yet migrated").

What was migrated: M1 Conception, M2 Validation and M3 Brand, complete — every framework became a
declarative reference under the matching component. The old step machinery (per-framework numbered
`steps-c/` files, `[S]`/`[B]` menu navigation, per-step frontmatter state) was deliberately NOT
carried: pacing and state are now the `trail/` component's job, and one file each.

The adjacent `workflows/product-discovery/` workflow was folded IN as three references
(`benchmark-analysis`, `product-landscape`, `v1-scoping`) rather than migrated as a fourth
milestone — the owner ruled to take its value, not its shape.

M4 Prototypation and the downstream M5/M6 names were NOT migrated. They exist in the old module as a
work-in-progress map, and that map is preserved verbatim in `trail/component.md` § "Mapped but not
yet migrated" so a later reader can find and migrate them deliberately.

</module>
