# Run-Log Template

Instantiate this as `run-log.md` in the run's spine location at spine init (intake §3). It is the run's **append-only audit log** — owner-facing, NEVER read by a worker. The State card (`{rbtv_path}/orchestration/skills/orchestrating/cards/state.md`) owns its semantics; this template is the render-ready body. Copy the block below, fill `{run-name}` + the init timestamp, leave the registers and event log empty.

---

## Template

```markdown
# Run Log — {run-name}

> [!warning] Append-only audit log — follow `_shared/authoring/decisions-discipline.md` (never edit or delete a prior entry).

> **Distinct from the compound source.** This file is the DECISION / EVENT audit trail. Harvest-worthy findings live in `decisions.md` entries carrying the one-word `compoundable` marker (the single compound home — there is no separate `learnings.md`). A single event MAY warrant entries in BOTH this log AND a `compoundable` decisions entry — when it does, write two separate entries, each in its own shape (dual-write rule: state card §6). NEVER merge the two shapes into one entry.

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

> ID format: `D1`, `D2`, … (bare `D` + integer, no hyphen). Cited as "per D-N" in prose.

| ID | Decision | Rationale | Scope (which queued work it affects) |
|----|----------|-----------|--------------------------------------|
<!-- example: D1 | chose X over Y | Z constraint | affects p3-4, p3-5 -->

### U-register (unilateral decisions — autonomous mode)

| ID | Confidence | Decision | Why decided unilaterally | User might have chosen | Risk accepted | Reversibility |
|----|-----------|----------|--------------------------|------------------------|---------------|---------------|
<!-- example: U1 | low | defaulted flag to false | autonomous mode, no user reachable | true | minor rework | revert commit -->

### ADX-register (errata)

> ID format: `ADX-1`, `ADX-2`, … (the `ADX-` prefix + integer). Cited as "per ADX-N". Numbers are claimed from this register atomically before the erratum is written (state card §6).

| ID | Erratum | Task(s) amended | Logged-from event |
|----|---------|-----------------|-------------------|
<!-- example: ADX-1 | use the v2 endpoint | p3-8 | doubt ruling 2026-06-07 -->


### Precondition Overrides

> Each `[PRECONDITION-OVERRIDE]` row (halt-recovery §6) — its fields do not fit the Event Log's five columns, so they land here. The Event Log carries a one-line `override` event pointing to the matching row below.

| ID | PRECONDITION (verbatim) | User justification (verbatim) | Protective-scope result | Confidence | Risk accepted | Reversibility |
|----|-------------------------|-------------------------------|-------------------------|-----------|---------------|---------------|
<!-- example: OV1 | "MUST NOT dispatch until p1b closed" | "p1b output not needed by these reads" | intersection empty | medium | stale-context | per-output drift markers -->

---

## Event Log

> Registrar discipline (state card §7): append a row when a dispatch goes OUT and when its result comes BACK. Re-read this tail after any context gap before dispatching again. Event types (use ONLY these — ad-hoc names destroy grep-ability): `dispatch` · `return` · `gate` (return-gate / review / cold-verifier) · `probe` · `drift` · `recovery` · `override` (precondition-override) · `handover` (USER-EXECUTED-ONLY step handed to the user; Outcome = the verbatim ask + confirmation status). A row that rides a state transition is COMPOSED by `stamp.py --scope conductor` from `--event-type` / `--worker` / `--outcome` (timestamp auto) — never hand-format it; hand-append only events with no stampable surface (state card §7 / intake light path).

| Timestamp | Event | Task / Batch | Worker | Outcome |
|-----------|-------|--------------|--------|---------|
<!-- example: 2026-06-07T14:02Z | dispatch | p2-9 | sonnet (agent-tool) | sent -->
<!-- example: 2026-06-07T14:48Z | return  | p2-9 | sonnet (agent-tool) | DONE — reconciled vs disk -->
<!-- example: 2026-06-07T15:10Z | handover | p4-x | — | "user: run install.py" — awaiting confirmation -->


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
| **Append-only, absolute** | NEVER edit or delete a prior entry; new events append at the bottom in chronological order. Full discipline (supersede-by-appending, size-floor): follow `_shared/authoring/decisions-discipline.md`. |
| **Both directions logged** | Every dispatch logs an OUT row and, on return, a BACK row. A log with dispatches but no returns cannot be resumed correctly (registrar discipline: state card §7). |
| **Unilateral rows are labeled + confidence-rated** | In autonomous mode every skipped halt / unilateral decision is a U-register row carrying `high` / `medium` / `low`. The finalization surfaces medium and low explicitly. |
| **Drift is recorded, never smoothed** | When verification finds message ≠ disk, append a `drift` event (disk won; the record proves it) — never silently reconcile away a discrepancy. |
| **This is an event log, not a decision file** | Forward-affecting decisions that workers must act on ALSO go to `decisions.md` (its own shape — state card §4/§6). This file records that the decision was MADE; `decisions.md` carries it TO the workers. |

## Render note

This template is instantiated mechanically at spine init — copy the fenced block, substitute `{run-name}` and the timestamp, and write it to the spine location. No section is optional at init: the empty registers and event log are filled as the run proceeds. The U-register and the Precondition Overrides table stay EMPTY in non-autonomous, no-override runs — an empty table there is the expected state, not a defect; they are retained for uniformity so any run's log has the same shape. The two leading callouts (append-only + dual-write) are part of the file and MUST survive instantiation — they are what keep the audience boundary and the dual-write rule visible at the point of use.
