---
description: "Assumption Mapping — score each assumption on importance × uncertainty, place it in a Test / Accept / Monitor / Ignore matrix, and write a test card for everything in Test."
tags: [validation]
---

# Assumption Mapping

Turns a flat list of assumptions into a decision tool: what gets tested now, what is accepted as a
working belief, what is merely watched, and what is ignored. Use it immediately after Leap of Faith,
on the inventory that framework produced — never on an unharvested set of beliefs.

## The structure

Two 1–5 axes. **Importance:** if this is wrong, how much damage? **Uncertainty:** how little
evidence do we have?

| Score | Importance | Uncertainty |
|---|---|---|
| 5 | Fatal if wrong — the business model collapses (matches a kill criterion) | No evidence — pure guess, no data, no interviews, no analogy |
| 4 | Severe — major pivot; revenue model or core value proposition breaks | Weak signal — one anecdote, one data point, or founder intuition |
| 3 | Significant — an important feature, channel or cost assumption fails; workaround possible but painful | Mixed signals — some evidence supports, some contradicts, or it is indirect |
| 2 | Moderate — affects efficiency or timeline, not viability | Moderate evidence — several data points or interviews, minor gaps |
| 1 | Minor — nice to know, no material effect on go/no-go | Strong evidence — robust data, or already validated in an adjacent market |

The intersection decides the action:

| Quadrant | Importance | Uncertainty | Action |
|---|---|---|---|
| Top-right | 3–5 | 3–5 | **TEST** — design and run a validation experiment |
| Top-left | 3–5 | 1–2 | **ACCEPT** — treat as a working assumption; record what would force a revisit |
| Bottom-right | 1–2 | 3–5 | **MONITOR** — track passively; move to Test if importance rises |
| Bottom-left | 1–2 | 1–2 | **IGNORE** — no action |

**Test card** — one per Test assumption:

- **Assumption** — the statement.
- **Hypothesis** — "If [assumption] is true, then [observable outcome]."
- **Test method** — the lightest-weight method that still produces credible evidence: desk research,
  5–10 targeted customer interviews, a landing page or smoke test, a technical spike, a financial
  model with sensitivity analysis, or an expert consultation.
- **Success signal** — concrete evidence that validates. "Seems interested" is not a signal.
- **Failure signal** — concrete evidence that invalidates, connected to the kill criteria.
- **Timeline** — days or weeks, never months.
- **Owner** — who runs it.
- **Downstream framework** — which later validation framework consumes the result.

**Healthy distribution** for an early-stage venture: Test 20–40%, Accept 20–30%, Monitor 15–25%,
Ignore 10–25%. If Test exceeds 50%, there are too many unknowns to proceed without de-risking first.

## What a good output contains

- A normalized, deduplicated inventory of 8–25 assumptions.
- Importance and uncertainty scores for every one, each with a written justification — not a bare
  number.
- The full 2×2 with every assumption placed and an action assigned.
- A test card carrying all eight fields for every Test assumption.
- A sequenced validation backlog that fits inside 2–4 weeks.
- A statement of which assumptions each later framework will address.

Failure looks like: starting without a completed assumption harvest; scoring everything 4–5 on
importance so nothing is differentiated; designing multi-month research; treating "Accept" as
"proven"; and freezing the map instead of re-scoring it as tests return evidence.

## Builds on / feeds

Builds on `leap-of-faith.md`, which owns the assumption inventory and its Value/Growth
classification — this framework scores and prioritizes that inventory, it does not restate it. It
OWNS the scoring and the test cards; no later framework re-derives them. The assumptions it flags go
to `tam-sam-som.md` (market), `unit-economics.md` (financial), `technology-readiness-level.md`
(technical), and every Test and Accept assumption becomes a candidate failure mode for
`pre-mortem.md`.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/bi-m2-assumption-mapping/`
(`data/assumption-mapping-framework.md`, `workflow.md`, `steps-c/step-06-synthesis.md`).
