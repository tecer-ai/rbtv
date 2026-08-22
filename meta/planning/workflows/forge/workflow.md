---
name: forge
default-execution-mode: interactive
---

# forge — the workflow

**Default execution mode.** `interactive` — declared above, in this workflow's own scaffolding. It is the value a goal created from this workflow is BORN with: goal creation writes it into the goal's `execution-mode` file, and from there the control plane gates every agent-initiated owner contact on it. Declared rather than left to derivation because `forg-intake`'s whole remit is reaching the owner, and the declaration is what lets a later owner ruling say otherwise without rewriting the manifest. A per-goal value supplied in the creation request overrides this default; this is the floor, never a lock.

**Goal.** Turn ONE small component-part request — create, edit, or parse a reference, a prompt, a task, a seat, a capability (a CLI included), an exposure entry, or a sub-agent definition — into finished artifacts on disk, registered and exposed, tried against the spec that ordered them.

**Scope.** Forge builds PARTS of components that already exist, and it EXECUTES what it specifies: the same run that writes the spec lands the files. It never mints a component, never authors a workflow or a DAG, and never plans — a request needing any of those escalates at intake, and the planning workflow takes it from there.

**The three modes.** Every request is exactly one of: **create** (the artifact does not exist yet) · **edit** (an existing artifact changes) · **parse** (an existing artifact is read back and reported, and nothing is written). `forg-intake` classifies the mode, and the mode picks the owner round: CREATE runs the two-perspective user-stories gate, EDIT and PARSE run one confirm round.

**Each request is a NEW mini-goal.** Forge keeps no backlog and no memory across requests. One request is one goal folder, one run of this chain, one spec, one build, one trial. A second request is a second goal, never an amendment to a finished one.

**The chain (`forge.csv` is the DAG).** Three seats, serial, guard-free:

1. `forg-intake` — classify kind and mode, ground every answerable question off the owner, run the escalation test, run the mode's owner round, enumerate the pieces with their target paths and exposure decisions, write `forge-spec.md`.
2. `forg-builder` — build every spec row, land each artifact at its target path, apply exactly the registration acts the spec decided, lint every touched component, write `forge-build.md`.
3. `forg-judge` — try every built piece against its spec done clauses and the ratified user stories, and record one verdict.

**The escalation exit.** `forg-intake` writes `disposition: escalate` as the first line of `forge-spec.md` when a NEW COMPONENT is needed (this one ALWAYS escalates), when the pieces span more than one component in a way one build pass cannot carry, when a new workflow or DAG is needed, or when the request is a symptom of an unstated bigger goal. The chain still runs to completion on that line: `forg-builder` and `forg-judge` each write a one-line "escalated at intake — no work performed" record and finish, so the run closes clean while the owner carries the planning-ready goal seed to the planning workflow.
