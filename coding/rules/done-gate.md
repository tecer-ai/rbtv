# Done Gate

An agent MUST NOT declare a coding task done until it has exercised every contracted criterion the way the owner will use the feature and exhibited the evidence — nothing else buys done. Evidence is **weight-graded**: a disk evidence sheet for Full-tier work, the same rows inline in the done message for Light-tier (the protocol owns the tier split). This trigger layer is always-on; the gate mechanics load on fire (Load Gate).

## Activation

Fires at TWO moments on every gated coding task:

| Moment | When | Action |
|--------|------|--------|
| Contract | A coding task starts — feature, bug fix, behavior change | Load the protocol; run Contract (owner-confirmed criteria + per-criterion Drivability Check) BEFORE Build |
| Exercise + Exhibit | A done-claim is about to be made | Exercise each criterion at the Fidelity Floor; fill the evidence sheet |

## Scope — what is gated

Default-ON for every coding task. **Does NOT apply to:**

- Non-code work (documents, plans, vault content) — out of scope entirely.
- The exempt list — the ONLY exit for coding tasks: typo and comment fixes, formatting-only changes, internal cleanups with zero behavior change (renames, dead-code removal), config changes invisible at runtime. **Fails safe: not on the list → gated.**
- Drivability only: a criterion the agent can ALREADY drive and observe with a real gesture is `drivable` — no seam needed. All other surface classification and seam-building is the protocol's job.

**Boundary:** tests green, builds passing, and code review do NOT buy done — internal correctness stays the agent's normal testing job.

## The Lock

No exercised evidence — the sheet (Full tier) or the inline rows (Light tier) — → done is UNDECLARABLE. A `failed` row → back to Build, then re-exercise. `unexercisable` and `held-surprising` rows → done declarable ONLY with those rows surfaced explicitly in the done message; the owner decides acceptance, never the agent.

## Load Gate — MANDATORY

The exemption decision (gated vs exempt) is made HERE, with this rule loaded — NEVER with the protocol unloaded, so "this task is exempt" can never be decided to dodge the body. The moment a coding task starts and is NOT exempt, you MUST invoke the `rbtv-done-gate` skill and follow the protocol it loads, BEFORE drafting criteria or writing code. Declaring done without loading and exercising that protocol is a rule violation.

| Thought | Action |
|---------|--------|
| "Small task / tests pass — I'll skip loading the protocol" | Exemption is decided against the exempt list above, not by convenience or test results. Not on the list → load the protocol and Contract. |
