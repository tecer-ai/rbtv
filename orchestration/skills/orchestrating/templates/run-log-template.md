# Run-Log Template

Instantiate this as `run-log.md` in the run's spine location at spine init (intake §3). It is the run's **append-only audit log** — owner-facing, NEVER read by a worker. The State card (`{rbtv_path}/orchestration/skills/orchestrating/cards/state.md`) owns its semantics; this template is the render-ready body. Copy the block below, fill `{run-name}` + the init timestamp, leave the registers and event log empty.

---

## Template

```markdown
# Run Log — {run-name}

> **Append-only audit log.** Owner-facing accountability record. A WORKER never reads this file — workers read `decisions.md` + their own task file (audience separation: state card §5). Never edit or delete a prior entry; append new events at the bottom in chronological order.

> **Distinct from `learnings.md` (plan runs).** This file is the DECISION / EVENT audit trail. `learnings.md` (the plan's file) is the compound-source for future-plan agents. A single event MAY warrant entries in BOTH — when it does, write two separate entries, each in its own shape (dual-write rule: state card §6). NEVER merge the two shapes into one entry.

---

## Run Configuration

- **Run mode:** {halt | end-to-end | autonomous}
- **Context-refresh:** {suggest | off}
- **Spine location:** {path to the spine folder}
- **Decisions file:** {path to decisions.md — the plan's, or the plan-less one created at intake}

---

## Registers

> Numbered so a `decisions.md` entry or a resumed worker cites "per ADX-N" / "per D-N" without re-reading history. Append-only.

### D-register (orchestrator rulings)

| ID | Decision | Rationale | Scope (which queued work it affects) |
|----|----------|-----------|--------------------------------------|

### U-register (unilateral decisions — autonomous mode)

| ID | Confidence | Decision | Why decided unilaterally | User might have chosen | Risk accepted | Reversibility |
|----|-----------|----------|--------------------------|------------------------|---------------|---------------|

### ADX-register (errata)

| ID | Erratum | Task(s) amended | Logged-from event |
|----|---------|-----------------|-------------------|

---

## Event Log

> Registrar discipline (state card §7): append a row when a dispatch goes OUT and when its result comes BACK. Re-read this tail after any context gap before dispatching again. Event types: `dispatch` · `return` · `gate` (return-gate / review / cold-verifier) · `probe` · `drift` · `recovery` · `override`.

| Timestamp | Event | Task / Batch | Worker | Outcome |
|-----------|-------|--------------|--------|---------|

---

## Exit Scorecard

> Filled at run end — the run's final accountability summary.

- **Per-feature verification:** {feature → held / failed, cold-verifier sheet path}
- **Cross-feature EXIT verification:** {held / failed + evidence path}
- **Exit probes (conductor-executed):** {N probes → verdicts + capture paths}
- **Honest exit reason:** {complete | blocked | stalled | degrading | timeout}
- **Medium/low-confidence unilateral decisions (autonomous):** {surfaced list, or none}
```

---

## Entry-shape rules (hard text — carried, not duplicated)

These bind every entry the orchestrator appends. The full discipline lives in ONE source — `{rbtv_path}/orchestration/workflows/_shared/authoring/decisions-discipline.md` (§ Entry-shape rules); the rules below are the audit-log-specific hard text, consistent with that source.

| Rule | Statement |
|------|-----------|
| **Append-only, absolute** | NEVER edit or delete a prior entry. New events append at the bottom in chronological order. An audit trail you can rewrite is not an audit trail. |
| **Both directions logged** | Every dispatch logs an OUT row and, on return, a BACK row. A log with dispatches but no returns cannot be resumed correctly (registrar discipline: state card §7). |
| **Unilateral rows are labeled + confidence-rated** | In autonomous mode every skipped halt / unilateral decision is a U-register row carrying `high` / `medium` / `low`. The finalization surfaces medium and low explicitly. |
| **Drift is recorded, never smoothed** | When verification finds message ≠ disk, append a `drift` event (disk won; the record proves it) — never silently reconcile away a discrepancy. |
| **This is an event log, not a decision file** | Forward-affecting decisions that workers must act on ALSO go to `decisions.md` (its own shape — state card §4/§6). This file records that the decision was MADE; `decisions.md` carries it TO the workers. |

## Render note

This template is instantiated mechanically at spine init — copy the fenced block, substitute `{run-name}` and the timestamp, and write it to the spine location. No section is optional at init: the empty registers and event log are filled as the run proceeds. The two leading callouts (append-only + dual-write) are part of the file and MUST survive instantiation — they are what keep the audience boundary and the dual-write rule visible at the point of use.
