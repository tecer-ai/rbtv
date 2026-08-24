---
description: "V1 scoping — cut a testable first version out of a product definition: the minimum flow that delivers value, conscious exclusions, manual workarounds instead of features, and the one hypothesis V1 exists to test."
tags: [validation]
---

# V1 scoping

Reduces a full product definition to the smallest thing that can prove or disprove the concept. Use
it once a product landscape exists — a founder-owned map of modules and features with a first-cut
classification of what belongs in V1. The posture is brutal prioritization: the best V1 has the
fewest moving parts, and the facilitator's job is to push back on every feature that survives only
because losing it feels uncomfortable.

## The structure

**1. Challenge every "V1 core" classification.** For each feature currently marked as essential, ask
three questions and hold the founder to the answers:

- Remove this feature. Does V1 still work?
- Can this be manual or operational in V1 instead of a built feature?
- What is the minimum version of this feature that still proves value?

More than seven features surviving as V1 core is a signal to challenge again explicitly, not a
result to accept.

**2. Define the seven V1 essentials.** Work each one through with the founder:

| # | Definition |
|---|---|
| 1 | Who is the initial user — a specific role, persona and context, not a segment |
| 2 | What specific pain does V1 address |
| 3 | What is the main output the product delivers |
| 4 | What input does the user provide |
| 5 | What is the minimum flow that generates value — numbered steps |
| 6 | What is explicitly OUT of V1 — conscious exclusions, each with its rationale |
| 7 | What hypothesis does V1 test — what must be true for V1 to count as successful |

**3. Separate operational from product.** For every feature cut from V1, decide whether it can be
done by hand in V1 — a manual process, a person doing the work behind the interface, a spreadsheet.
If yes, record it as "operational in V1, product in V2". This is not a consolation prize: it keeps
the capability available to the customer while removing it from the build, and it removes the fear
of loss that drives most scope creep.

**4. Write the scope document.** One file carrying: the seven essentials; the features in V1, each
described at its minimum viable version; the conscious exclusions with the rationale for each; the
operational workarounds; the hypothesis; and the success criteria.

## What a good output contains

- A minimum flow written as numbered steps that a reader could follow end to end without asking what
  happens next.
- Exclusions stated as decisions with reasons — "not in V1 because X" — never as an omission.
- Every cut feature resolved: either an operational workaround is named, or the document says
  plainly that the capability is simply absent from V1.
- A single hypothesis, falsifiable, with success criteria that state a threshold rather than a
  direction.
- A V1 core small enough that removing any one item visibly breaks the value proposition.

Failure looks like: a V1 that is the whole product with a smaller label; exclusions listed with no
rationale; success criteria phrased as "users like it"; and a hypothesis that no realistic result
could contradict.

## Builds on / feeds

Builds on the founder-owned product map in `../../conception/references/product-landscape.md`, which
supplies the modules, features and the first-cut V1 / later / maybe-never classification this
framework challenges. It OWNS the V1 boundary — what is in, what is out, and what is done by hand.
Its hypothesis and success criteria are an input to the validation frameworks in this component:
they are assumptions like any other and belong in the inventory that `leap-of-faith.md` owns and
`assumption-mapping.md` scores. The scope document itself is the input to downstream product
planning — the specification, roadmap and build sequencing that follow this module.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/product-discovery/steps-c/step-05-v1-scoping.md`. The
old step ended by handing its output to an external product-brief workflow shipped by another
plugin; that dependency was deliberately dropped in this migration — the output is named as the
input to downstream product planning, wherever that planning happens.
