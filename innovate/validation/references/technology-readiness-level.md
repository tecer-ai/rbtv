---
description: "Technology Readiness Level — rate each technical component of the product on the 1–9 readiness scale against demonstrated evidence, and design a spike for every component that scores below 4."
tags: [validation]
---

# Technology Readiness Level

A 9-level scale, originally NASA's, for how close a technology is to operational deployment, adapted
here for digital products. Its value is that it forces a per-component, evidence-based rating instead
of a comfortable opinion about "the product". Use it once the solution concept is defined and there
is something concrete to decompose.

The load-bearing insight: a product whose five components sit at levels 8, 8, 8, 8 and 2 is NOT at
level 7. The weakest component sets the risk profile.

## The structure

| Level | Name | What it means |
|---|---|---|
| 1 | Basic principles observed | The principle is understood but has not been applied to this problem |
| 2 | Concept formulated | There is a concept for applying the principle here |
| 3 | Proof of concept | The core concept was demonstrated in a controlled setting |
| 4 | Validated in lab | It works in a development environment with representative data |
| 5 | Validated in a relevant environment | It works in staging, approximating production |
| 6 | Demonstrated in a relevant environment | Tested with real users or real data near production |
| 7 | Prototype in an operational environment | A working prototype runs in the real environment |
| 8 | System complete and qualified | Fully integrated, tested, meeting its stated requirements |
| 9 | Proven in operations | A track record of reliable real-world operation |

**Component type** sets the expected starting point: novel (built from scratch, a new approach) →
levels 1–3; adapted (existing technology applied to a new context) → 3–5; standard (well understood,
widely available) → 6–8.

**Risk categories** — assess each component across all seven: performance (speed, accuracy,
throughput, latency), scalability (volume within cost constraints), integration (external services
that could change or fail), data (do we have it, is its quality proven), security and compliance,
skills (does the team have the expertise), and cost (do variable costs become prohibitive at scale).

**Spike card** — one per component below level 4:

- Component, current level, target level (4–5 minimum).
- Key question, phrased concretely: "can we [capability] under [constraint]?"
- Method: a minimal proof of concept, a benchmark against representative data, an evaluation of a
  third-party service, an expert consultation, or an analysis of comparable implementations.
- Success criteria — specific and measurable ("85% accuracy on a 500-sample test set").
- Failure criteria — what would invalidate this component; connect it to the kill criteria.
- Estimated effort, dependencies, owner.

**Overall posture.** Green: all components at level 4 or above, no spikes needed — technically ready
to prototype. Yellow: one or two components below 4 with spikes under two weeks — proceed after the
spikes. Red: three or more below 4, or any below 2 with no path — technical feasibility is genuinely
in question.

## What a good output contains

- A component inventory of 4–10 technical building blocks — the product decomposed, not summarized.
- A level for every component WITH the evidence statement that justifies it.
- A technical risk inventory with the unknowns categorized.
- A spike card, complete, for every component below level 4.
- An overall posture stated plainly with its rationale, and the de-risking effort and timeline.
- The technical risks named and handed to the risk analysis.

Failure looks like: scoring on capability rather than demonstrated evidence; assessing "the system"
instead of each component; assuming a third party's maturity transfers (a widely used service at
level 9 may be level 4 for THIS integration); spikes that grow past one question and two weeks; and
skipping the framework for a "simple" product — authentication, data migration and deployment are
components too.

## Builds on / feeds

Builds on the solution concept from conception (what must actually be built) and the technical
assumptions flagged by `leap-of-faith.md` and `assumption-mapping.md`. It OWNS technical feasibility
and component readiness; no later framework re-rates them. Its low-level components and technical
unknowns feed `pre-mortem.md`, and the readiness table plus spike results are the input to
prototyping and to the eventual minimum viable product's scope constraints.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/bi-m2-technology-readiness-level/`
(`data/trl-framework.md`, `workflow.md`, `steps-c/step-05-synthesis.md`).
