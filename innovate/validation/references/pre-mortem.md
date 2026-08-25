---
description: "Pre-mortem for a venture — declare the business failed twelve months from now, explain why across seven failure categories, rank the modes by likelihood × severity, and write mitigations with early-warning signals."
tags: [validation]
---

# Pre-mortem

Prospective hindsight: instead of asking "what could go wrong?", which invites defensive optimism,
state it as fact — "the venture failed; it is twelve months from now; why?" The reframe gives
permission to voice doubts that would otherwise stay unsaid, and it measurably increases how many
reasons for a future outcome people can generate.

Run it LAST in validation. It consumes the output of every other framework in the milestone; run
first, it produces generic worries instead of specific risks.

> Boundary: the generic conversational pre-mortem — pre-mortem as a thinking move on any plan,
> decision or design — is a mode of the `brainstorm` skill in `core/functions`. THIS reference is
> the validation-milestone application to a venture: seven business failure categories, a scored
> risk register, and mitigations wired to the venture's kill criteria.

## The structure

**Seven failure categories** — brainstorm across all of them; a good run touches at least five.

| Category | What fails |
|---|---|
| Market | Customers do not exist, do not care, or cannot be reached |
| Product | The solution does not solve the problem, is unusable, or is undifferentiated |
| Team | Missing skills, founder conflict, burnout, a key person leaves |
| Financial | Revenue too low, costs too high, funding not secured, cash runs out |
| Technical | Cannot build it, performance inadequate, integration fails, security breach |
| Competitive | An incumbent responds, a new entrant takes the market, an open-source alternative appears |
| Operational | Regulatory block, legal issue, a partner dependency fails, a scaling bottleneck |

**Score each mode** on likelihood and severity, 1–5. Risk score = likelihood × severity (1–25).

| Score | Likelihood | Severity |
|---|---|---|
| 5 | Near certain — signals already point at it | Fatal — the venture dies, no recovery path |
| 4 | Probable — more likely than not on current evidence | Crippling — major pivot, months of work lost |
| 3 | Possible — could go either way, evidence mixed or absent | Serious — significant setback, recovery expensive |
| 2 | Unlikely — several things would have to go wrong | Moderate — noticeable, manageable with effort |
| 1 | Remote — possible only with extreme bad luck | Minor — an inconvenience, a normal correction |

**Mitigation card** — one per top failure mode: the failure mode in one sentence; its root cause (the
underlying assumption, gap or weakness); the mitigation action that reduces likelihood or severity;
an early-warning signal that is observable and measurable WITH a threshold; the trigger response
(what happens when the signal fires); the owner; and the timeline for both the action and the first
signal check.

**Kill-criteria alignment.** For each mitigation: if the failure mode maps to an existing kill
criterion, align their early-warning signals; if it reveals an uncovered risk, propose a new kill
criterion. Every severity-5 failure needs a contingency plan for the case where the mitigation
itself fails.

## What a good output contains

- A failure framing that actually uses prospective hindsight — past tense, the failure assumed.
- 15+ failure modes spanning five or more of the seven categories.
- Every mode written as a concrete past-tense explanation. Reject "market risk"; demand "we could not
  reach buyers because the only channel that converted was one we could not afford".
- A ranked table with likelihood × severity for every mode.
- Complete mitigation cards for the top 5–8, every field filled.
- A contingency plan behind every severity-5 mode.
- Kill criteria updated where this run exposed a risk they did not cover.
- An overall risk posture, and the risks that carry forward into later milestones.

Failure looks like: running it before the other validation frameworks; filtering during the
brainstorm instead of capturing everything and filtering at ranking; vague failure modes; treating
it as a pessimism exercise (the goal is to surface and mitigate, not to talk the founder out of the
venture); and early-warning signals with no owner and no check-in date.

## Builds on / feeds

Builds on every prior validation framework — kill criteria and high-impact assumptions from
`leap-of-faith.md`, unvalidated Test-quadrant items from `assumption-mapping.md`, market gaps from
`tam-sam-som.md`, sensitivity points and break-even risk from `unit-economics.md`, and low-readiness
components from `technology-readiness-level.md`. It OWNS failure modes and risk mitigation; nothing
downstream re-derives them. Completing it closes the validation milestone, which ends with an
explicit persevere / pivot / kill recommendation backed by the milestone's evidence.

## Sources

Distilled from
`3-resources/tools/rbtv/innovation/workflows/business-innovation/bi-m2/bi-m2-pre-mortem/`
(`data/pre-mortem-framework.md`, `workflow.md`, `steps-c/step-05-synthesis.md`). Underlying method:
Gary Klein, "Performing a Project Premortem", *Harvard Business Review*, 2007; Daniel Kahneman,
*Thinking, Fast and Slow*; Bland & Osterwalder, *Testing Business Ideas*.
