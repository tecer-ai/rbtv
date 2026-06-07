# Spec Template

Template for a behavior spec with an embedded test plan. Authored before any executor builds a code feature. Both consumers fill it: `rbtv-planning` (code-work plans) and orchestration intake writer agents (plan-less code goals).

Validated pattern: in the hypresent pilots, Opus spec-writer agents authored detailed behavior specs and the matching verification plan from the architecture; executors (Kimi) then built strictly to the spec, and a separate pass exercised the test plan. Decoupled spec files — not conversation history — carried the contract between agents.

---

## Why a spec is separate from a task file

A task file says WHAT to do and HOW to confine the worker (the task-file contract). A spec says what the FEATURE must DO and how its doing is PROVEN. One spec can back several task files; a task file references its spec rather than restating it. The spec is the behavior source of truth; the test plan inside it is the acceptance source of truth.

## Template

```markdown
# Spec — {Feature}

## Goal
{One bounded behavioral deliverable, owner-framed: "the owner can {gesture} and {visible result} happens".}

## Context Snapshot
{Every interface, data shape, and current-code excerpt the work depends on — inlined with content anchors, never line numbers. A worker reading ONLY this spec must be able to build the feature without exploring a broad PRD.}

## Behavior Specification
{The exact behavior to build, stated as observable rules. One row per rule.}

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | {trigger} | {visible outcome} |

## Edge Cases & Error Behavior
{Boundary conditions, empty states, and failure modes — each with its required observable behavior. A blank here is a silent bug at build time.}

## Out of Scope
{What this feature explicitly does NOT do — bounds the worker so adjacent behavior is not "improved" unasked.}

## Test Plan
{The acceptance contract. Each criterion is owner-observable or worker-runnable — exercised the way the owner will use the feature, never an internal assertion. One row per criterion.}

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | {what the owner will see work} | {the real input/gesture, at the fidelity floor} | {the visible result} | {file written during the exercise — screenshot, output capture, log} |

**Fidelity floor for every criterion:** the real application running whole, on the owner's real data when one exists; UI criteria use a visible browser + real input, never synthetic `dispatchEvent`. Evidence is a file on disk written DURING the exercise — a prose claim alone does not satisfy a criterion. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker, never silently skipped.

**Evidence plausibility:** metrics in test evidence must be physically plausible (a browser e2e under 1s, an OS-dialog test under 1.5s, are auto-reject + rerun). Exit 0 plus an evidence file is not proof if the metrics are impossible.

## Return Expectations
{What the executor reports back: files changed, validation commands run + their exit codes + any skips with reasons, local commit hash if committed, concerns, blockers. The report is a hint; the repo state is the truth.}
```

## Authoring rules

| Rule | Detail |
|------|--------|
| Behavior before tests | Fill Behavior Specification and Edge Cases first; the Test Plan exercises THEM, so it cannot be written against a vague behavior |
| Criteria are observable | Every Test Plan row is something the owner can watch happen or the worker can run — internal/technical assertions belong in the executor's own unit tests, not here |
| One spec, many tasks | Reference this spec from each backing task file; never copy the spec body into a task file |
| Content anchors | Current-code excerpts in Context Snapshot use exact-text anchors, not line numbers |
| No version connotation | Name and describe the feature as the feature — never "v1", "basic", "first cut" |
