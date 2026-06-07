# Card: State

The state-spine card for `rbtv-orchestrating`. Opened at spine init (intake hands the WHERE; this card owns the WHAT), at every registrar moment (a dispatch goes out, a return comes back, a gate fires, a probe runs), and at refresh/resume. It owns the SEMANTICS of the three state files — which file holds what, who may read each, which is mutable and which is append-only, and how a decision that affects queued work propagates. Every sibling card writes to these files; this card is the single definition of how they are written.

Iron rules it serves (from the core protocol): **disk = truth** (the spine IS the run's durable state — the orchestrator reconciles against it, never against chat memory, and a resumed conductor rebuilds from it alone), and **registrar discipline** (log dispatches AND results; re-read the tail after any context gap — an unlogged dispatch is an invisible one).

The other cards DEFER their file mechanics here and never restate them: intake (§3) fixes where the spine is created; routing writes the delegation map; the dispatch-wrapper points workers at `decisions.md`; halt-recovery writes errata, recovery rows, red-set operations, and override rows; verification writes gate verdicts, drift instances, and the debug pre-commitment slate. This card tells each of them which file the write lands in and in what shape.

---

## 1. The three-file spine (D12)

A run carries exactly three state files. Each has ONE audience and ONE mutability discipline; the two NEVER mix in a single file (the mutable+append-only seam corrupts — the reason the old 4+ file taxonomy was rejected).

| File | Mutability | Audience | Holds |
|------|------------|----------|-------|
| **`run-log.md`** | **Append-only audit** | The OWNER + the conductor reviewing post-hoc — NEVER a worker | Every orchestration event: dispatch / return / gate / probe rows; the exit scorecard; the D- / U- / ADX registers; autonomous unilateral decisions as LABELED, confidence-rated rows |
| **`state-capsule.md`** | **Mutable, atomic-overwrite** | The NEXT conductor session, resuming after interruption or refresh | The small in-flight state needed to resume cleanly: resume point, run configuration, approved delegation map, active red sets, active doubts / blockers |
| **`decisions.md`** | **Append-only, worker-facing** | WORKERS (alongside their own task file), plus the later compound/synthesis step that harvests forward-affecting decisions at run close | ONLY decisions / discoveries / errata that affect FUTURE work — never an execution log |

The split is load-bearing: the audit log accretes forever (the owner's accountability record), the capsule is overwritten every beat (only the latest resume state matters), and the worker-facing decisions file carries forward-affecting SIGNAL only. A finding written to the wrong file is lost to its real audience — the two routing-confusion compounds (below, §6) exist because findings landed in audit/state files and never reached `decisions.md` / `learnings.md`.

---

## 2. `run-log.md` — the append-only audit log

The run's complete event history, append-only, owner-facing. It absorbs the old `autonomous-run-log.md` as one entry TYPE (the labeled unilateral-decision row) rather than as a separate file. Instantiate it from `{rbtv_path}/orchestration/skills/orchestrating/templates/run-log-template.md` at spine init.

| What lands here | Shape |
|-----------------|-------|
| **Event rows** | One row per orchestration event — a dispatch sent, a return reconciled, a gate fired (return gate / review / cold verifier), a probe run. Each row: timestamp, event, task/batch id, outcome. This is the registrar's ledger (§5). |
| **Exit scorecard** | At run end: the per-feature and cross-feature verification results, the exit-probe verdicts, the honest exit reason — the run's final accountability summary. |
| **D- / U- / ADX registers** | `D-` decisions (orchestrator rulings), `U-` unilateral autonomous decisions, `ADX-` errata — each numbered so a `decisions.md` entry or a resumed worker cites "per ADX-N" without re-reading history. The register is the audit copy; the worker-facing copy of an ADX erratum lives in `decisions.md` or the task file (§4). |
| **Labeled unilateral-decision rows (autonomous mode)** | In `autonomous` mode, every halt the conductor skipped and every decision it made unilaterally is appended as a LABELED row carrying a confidence rating (`high` / `medium` / `low`) — the audit trail that makes autonomous execution accountable. The finalization message surfaces `medium` and `low` rows explicitly. |
| **Drift instances** | When verification's reconciliation finds message ≠ disk, the discrepancy is logged here (disk won; the record proves it). |
| **`[PRECONDITION-OVERRIDE]` rows** | The precondition-override protocol (halt-recovery §6) records its labeled row here: the PRECONDITION verbatim, the user justification verbatim, the protective-scope verification result, confidence, risk, reversibility. |

**Append-only is absolute.** NEVER edit or delete a prior `run-log.md` entry. New events append at the bottom in chronological order. This is the file's whole value — an audit trail you can rewrite is not an audit trail.

---

## 3. `state-capsule.md` — the mutable resume state

The small, mutable file the next conductor reads to pick up cleanly. The orchestrator OVERWRITES it (atomic) at each batch close and each reviewer close — overwriting is the contract, not a violation. Instantiate it from `{rbtv_path}/orchestration/skills/orchestrating/templates/state-capsule-template.md` at spine init.

| Section | Holds | Updated |
|---------|-------|---------|
| **Resume point** | Last completed (phase / batch / task), next dispatch, last-update timestamp | Every beat |
| **Run configuration** | Run mode (halt / end-to-end / autonomous), context-refresh setting (suggest / off), plan + decisions paths | At intake; rarely after |
| **Approved delegation map** | The (model, variant) assignment per batch + reviewer timing + refresh candidates the user approved | At routing / delegation approval |
| **Completed batches** | The batches already done (batch / phase / tasks / worker / status / reviewer) — the resume reads this to skip finished work | As each batch closes |
| **Active red sets** | The test files whose failures are PLANNED (a RED task landed, its GREEN pair has not) — halt-recovery §5 registers and retires these; this file STORES them | As reds register / retire |
| **Active doubts / blockers** | The open doubt or blocker that stopped the run, or none | When a halt fires / clears |
| **Notes for resuming conductor** | Critical context the next session needs: user overrides, irreversibility warnings, model-tier exceptions, a no-commit condition — overwritten, not appended | When the carried context changes |

These seven sections match the state-capsule template exactly; a conductor maintaining the capsule from this table creates and updates every one the template carries.

**Atomic-overwrite discipline.** Write the new content to a sibling `state-capsule.md.tmp`, verify it is well-formed (parses, required sections present), then atomically replace the live file. A stray `.tmp` at session start = a prior interrupted write — surface it to the user before proceeding. Never append to this file; never let it carry a planning decision (those are append-only and belong in `decisions.md`).

**Size cap.** Keep the capsule small — it exists for fast, clean resumption, not history. Collapsing applies ONLY to the **Approved Delegation Map** and **Completed Batches** rows: collapse THEIR rows from phases older than the previous one into a single summary row. The protected sections — Run Configuration, Active Red Sets, Active Doubts/Blockers, the Resume Point, and the Resuming-Conductor Notes — are NEVER collapsed or dropped regardless of size (collapsing them would swallow the resume contract). Full audit history belongs in `run-log.md`, never stuffed here.

---

## 4. `decisions.md` — the append-only, worker-facing file

The file WORKERS read (with their own task file) to pick up decisions, discoveries, and errata that change future work. It is append-only and carries SIGNAL only — never an execution log, never a files-changed list.

| Run kind | Which `decisions.md` |
|----------|----------------------|
| **Plan-backed** | REUSE the plan's worker-facing decisions file — `decisions.md` after the D13 rename, or `shape.md` for a plan authored before it (the rename lands at p4-2; earlier plans, including this build's own, carry `shape.md`). Do NOT create a second one. The plan's companion IS the run's worker-facing decisions file; match the name it actually carries. |
| **Plan-less** | CREATE one at intake, in the spine location. It starts empty and accretes forward-affecting entries as the run proceeds. |

The `Decisions file:` field in `state-capsule.md` records the ONE resolved path (the plan's file for a plan-backed run; the spine-local file for a plan-less run) — never both, never ambiguous. A resumed conductor reads exactly that path.

**Entry-shape discipline is NOT restated here — it lives in one source.** Follow `{rbtv_path}/orchestration/workflows/_shared/authoring/decisions-discipline.md`: every entry is decision + rationale + scope ONLY; never a files-changed list; never an N→M count narrative; supersede an earlier entry by APPENDING a new one (UPDATE-not-REWRITE), never by rewriting it; routine completions are excluded. That file is the source the `decisions-template` hard text carries (lands at p4-2).

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

---

## 5. Audience separation — workers NEVER read the audit log

The single most-confused boundary, stated as a hard rule:

| Reader | Reads | NEVER reads |
|--------|-------|-------------|
| **A worker** (dispatched executor, reviewer, verifier) | Its own task file + the run's `decisions.md` (pointer carried in the dispatch header, per the dispatch-wrapper). A reviewer ALSO reads the specific artifacts its review brief names (the diff, the spec/contract, a deliverables index to audit) — the conductor HANDS it those; that is distinct from autonomously reading the audit log. | `run-log.md` (the audit log) and `state-capsule.md` (the conductor's resume state) — these are conductor/owner surfaces; a worker never reads them as an INPUT, even a reviewer auditing a deliverables index works from the brief, not the run-log |
| **The next conductor** (resume / refresh) | `state-capsule.md` first (the resume contract), then `run-log.md` tail + `decisions.md` as needed | — |
| **The owner / post-hoc reviewer** | `run-log.md` (the accountability record) + the exit scorecard | — |

A worker handed the audit log inherits noise it cannot act on and may mistake an execution event for a decision. The dispatch-wrapper carries ONLY the `decisions.md` pointer into a dispatch — never a path to `run-log.md` or `state-capsule.md`. Keep this boundary; it is what makes the worker's surface minimal and its reads deterministic.

---

## 6. Propagation discipline — a decision that touches queued work

When the conductor makes (or a worker surfaces) a decision that affects work already queued, the decision MUST reach the affected task files AND the audit log — never just one.

| Step | Action |
|------|--------|
| **1. Assign the ADX number, then amend the affected task files** | FIRST claim the next `ADX-N` from the run-log ADX-register (assign atomically before writing the erratum body) — so two concurrent errata never collide on the same N. THEN, for every queued task the decision changes, APPEND the ruling to that task file as the `ADX-N` erratum — append-only, never a rewrite of the task body. The resumed/re-dispatched worker consumes the ruling FROM the task file on disk, not from chat. (This is the same erratum halt-recovery §2 and verification §2d write; this card owns that the number is register-assigned, it is append-only, and it lands in the consumed artifact.) |
| **2. Log the row** | Record the decision in `run-log.md` (the `D-`/`ADX-` register) so the audit trail carries it. |
| **3. Carry forward-affecting findings to `decisions.md`** | If the decision is a discovery/erratum that changes FUTURE work (not just the one task), append a `decisions.md` entry per §4's discipline so every later worker and the compound step see it. |

The rule in one line: a decision that changes queued work is placed IN the artifacts the affected workers read, append-only, AND logged — never left in conversation, never written to only one surface.

### The dual-write rule (mode-independent)

A single source event MAY qualify for BOTH an audit/state file AND the compound-source `learnings.md` (plan runs). When it does, write TWO separate entries — one to each, each in that file's shape — NEVER one entry with the other's shape grafted in. This holds in every multi-agent mode (the two routing-confusion compounds proved the gap recurs across modes):

| Mode | The audit/state write | The compound write |
|------|-----------------------|--------------------|
| **Autonomous** | The unilateral DECISION → `run-log.md` (labeled, confidence-rated row) | The compoundable FINDING → `learnings.md` |
| **Orchestrated** | A finding that changes FUTURE work → `decisions.md` (worker-facing, append-only). A finding that changes only the IN-FLIGHT resume state (an active doubt, a new red set, a changed resume point) → the matching `state-capsule.md` Active section (atomic overwrite). A finding that is BOTH goes to both; one that is neither is logged in `run-log.md` only. (No "residual" catch-all — each finding routes by what it changes.) | The compoundable FINDING → `learnings.md` (do NOT rely on the compound step to harvest it back out of state/decisions later — the harvest is lossy) |
| **Interactive halt** | Findings surface to the user live | The executor SHOULD still append the `learnings.md` entry so the compound step has a durable source |

`learnings.md` and `deliverables.md` are the PLAN's files (owned by `rbtv-planning`), unchanged by this spine — the dual-write rule is the seam between the run's state files and the plan's compound source. A plan-less run has no `learnings.md`; its compoundable findings, if any, surface to the user at run end per the run mode.

---

## 7. Registrar discipline — log dispatches AND results

The orchestrator is the run's registrar: every dispatch and every result is logged to `run-log.md` AS IT HAPPENS. An unlogged dispatch is invisible to a resumed conductor — it cannot tell a never-sent task from a sent-but-unreturned one.

| Rule | Detail |
|------|--------|
| **Log both directions** | Append a row when a dispatch goes OUT (task, worker, timestamp) AND when its result comes BACK (status, reconciled outcome). A run-log with dispatches but no returns cannot be resumed correctly. |
| **Re-read the tail after any gap** | After a context refresh, an interruption, or ANY gap in the conductor's continuity, RE-READ the `run-log.md` tail (and `state-capsule.md`) before dispatching again — never resume from memory of what was dispatched. The log is the ground truth for "what is in flight." |
| **Update the capsule in lockstep** | Each logged event that ADVANCES the run also updates `state-capsule.md` (resume point + timestamp). "Advances" = changes the resume point (a batch/task completed, the next dispatch changed), the active red sets, or the active doubts/blockers. An event that does NOT change any of those (e.g., a logged drift instance the conductor immediately reconciled, a mid-batch probe) lands in `run-log.md` ONLY — it does not force a capsule rewrite. The append-only log records every event; the mutable capsule records only the new resume state. |

This is the discipline that makes the run survivable across sessions: state lives in the files, not in the process.

---

## 8. Refresh and resume

The spine is the resume artifact — there is NO separate handoff document. Context-refresh and resume both rebuild the conductor from `state-capsule.md`.

| Operation | Procedure |
|-----------|-----------|
| **Context-refresh (suggest mode)** | At an APPROVED clean phase boundary ONLY, offer to stop and resume with a fresh conductor. Never refresh mid-phase or before the full delegation map is set (intake §7 sets the policy; this card owns the mechanics). On accept: ensure `state-capsule.md` reflects the next dispatch, the log tail is current, then STOP — the fresh session resumes from the capsule. |
| **Context-refresh (off mode)** | Keep the same conductor unless the session is interrupted; the spine is still the recovery artifact if it is. |
| **Resume (new session)** | Read `state-capsule.md` FIRST (resume point + delegation map + active red sets + active doubts), THEN the `run-log.md` tail to confirm what is in flight, THEN `decisions.md` for the rulings in force. Skip already-completed work per the resume point + completed batches; never redo a batch the capsule marks done. **Capsule absent or corrupted (and no recoverable `.tmp`):** reconstruct the resume state from the `run-log.md` tail — the last Run Configuration row gives mode/refresh/paths, the last logged event gives the resume point and what was in flight, and the registers give the rulings — then re-write a fresh capsule before dispatching. The run-log is the append-only ground truth the mutable capsule is derived from; it can always rebuild the capsule. |

A resumed conductor that reads the capsule, reconciles the log tail against disk, and re-pins the in-flight dispatch is a clean continuation — the run does not restart, it continues. NEVER create a separate context-handoff file: the capsule is the contract.

---

## Hand off — back to the loop

This card's job is to keep the spine correct: the right file holds the right thing, in the right shape, with the right audience, and a decision that touches queued work reaches every artifact that must carry it. From here the run's normal flow continues — routing and the dispatch-wrapper produce and send the next dispatch (carrying the `decisions.md` pointer), verification reconciles its return against the disk the spine records, and halt-recovery writes its errata and recovery rows through this card's semantics. Follow the situation table in the core protocol; this card is opened whenever a state file is written and whenever a run is resumed, and its responsibility is that those writes obey the spine.
