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
| **`decisions.md`** | **Append-only, worker-facing** | WORKERS (alongside their own task file) | ONLY decisions / discoveries / errata that affect FUTURE work — never an execution log; harvest-worthy entries carry the one-word `compoundable` marker (the single harvesting home — `rbtv-compounding` covers correction-driven capture in the moment) |

The split is load-bearing: the audit log accretes forever (the owner's accountability record), the capsule is overwritten every beat (only the latest resume state matters), and the worker-facing decisions file carries forward-affecting SIGNAL only. A finding written to the wrong file is lost to its real audience — the two routing-confusion compounds (below, §6) exist because findings landed in audit/state files and never reached `decisions.md`.

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

> Append-only discipline (NEVER edit/delete a prior entry; supersede by appending; size-floor on rewrites) is owned by `_shared/authoring/decisions-discipline.md`. Follow it.

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

**Regeneration discipline — a boundary write REGENERATES the capsule; it NEVER edits the prior one in place.** At every boundary write (batch close, reviewer close, pre-refresh), re-instantiate the capsule from the template skeleton carrying ONLY live values — NEVER edit the prior capsule's rows in place. In-place editing is overwrite-as-append: a long-lived conductor accretes superseded rows, stale vintages, and contradictions (duplicate resume rows, a next-dispatch that disagrees between sections, a worker-quota state stated both refreshed and exhausted) that a resuming conductor would act on. A fresh session regenerates naturally; this discipline makes leanness contractual, independent of session age. Two tests decide what survives regeneration:

| Test | Rule |
|------|------|
| **Per-row liveness** | For each row ask "does the NEXT dispatch need this?" — if not, it does not belong here. History goes to `run-log.md`, rulings to `decisions.md`. The capsule carries POINTERS (commit hashes, findings paths, D-/ADX-numbers), never narratives. |
| **Volatile facts once** | Each volatile fact — the next dispatch, the next hard halt, each worker's quota state — is stated EXACTLY ONCE. A fact restated in two sections is the contradiction this discipline exists to prevent. |

The conductor-scope `stamp.py` lockstep (§7) touches ONLY the Resume Point's three labeled bullets — `**Last completed:**` (from `--resume-note`, derived fallback), `**Next dispatch:**` (from `--next-dispatch`), `**Last update:**` (auto timestamp) — labels preserved, and is not a boundary write — the boundary regeneration is the conductor's own rewrite at batch/reviewer close. `stamp.py --scope conductor` validates the capsule's structure on every stamp and REFUSES (non-zero EXIT, no write) a capsule that carries a duplicate section header, a next-dispatch claim outside Resume Point (the leak the 2026-06-10 defect showed), the next dispatch stated more than once, or a Resume Point missing any of the three labeled bullets (off the template skeleton — regenerate it) — the deterministic guard against accretion between regenerations. The guard is a tripwire, not a cleaner: it REFUSES an accreted capsule but never regenerates one for you — a conductor that only stamps and never regenerates by hand will have its next stamp refused, so boundary regeneration remains the conductor's standing obligation.

**Every capsule claim is COMPUTED at the moment of writing.** Each factual claim the capsule carries — the resume point, a completed-batch status, a red-set row, a count — is derived from a command run AS THE CAPSULE IS WRITTEN, never from the conductor's memory of having done the thing. This is `rbtv-deterministic-first`'s Compute gate binding the capsule's WRITE, where this card's iron rule already binds its read; follow the rule, do not restate it. The **resume point is the load-bearing case**: it is the first thing the next conductor reads and the thing it trusts before anything else, so a resume point asserted from memory rather than re-derived from disk (the `run-log.md` tail, `git log`, the task's own `status:`) hands the next session a run that does not exist — and a next-dispatch six dispatches stale reads exactly like a correct one (2026-07-15: a resume capsule carried precisely that, inside a run already declared done). Disk = truth governs the capsule's write, not only its read.

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

**Entry-shape discipline is NOT restated here — it lives in one source.** Follow `{rbtv_path}/orchestration/workflows/_shared/authoring/decisions-discipline.md`: every entry is decision + rationale + scope ONLY (plus an optional one-word `compoundable` marker for harvest-worthy findings); never a files-changed list; never an N→M count narrative; supersede an earlier entry by APPENDING a new one (UPDATE-not-REWRITE), never by rewriting it; routine completions are excluded. That file is the source the `decisions-template` hard text carries (lands at p4-2).

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.

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
| **2. Log the row** | Record the decision in `run-log.md` (the `D-`/`ADX-` register) so the audit trail carries it. (A decision that also advances a task's STATE rides the `stamp.py` event of that transition — §7's stamp call, not a separate manual run-log edit.) |
| **3. Carry forward-affecting findings to `decisions.md`** | If the decision is a discovery/erratum that changes FUTURE work (not just the one task), append a `decisions.md` entry per §4's discipline (carrying the `compoundable` marker if harvest-worthy) so every later worker sees it. |

The rule in one line: a decision that changes queued work is placed IN the artifacts the affected workers read, append-only, AND logged — never left in conversation, never written to only one surface.

### The dual-write rule (mode-independent)

A single source event MAY qualify for BOTH an audit/state file AND a compoundable FINDING. When it does, write TWO separate entries — one to each, each in that file's shape — NEVER one entry with the other's shape grafted in. The compound destination is the worker-facing `decisions.md` entry carrying the one-word `compoundable` marker — the single harvesting home (there is no separate `learnings.md`). This holds in every multi-agent mode (the two routing-confusion compounds proved the gap recurs across modes):

| Mode | The audit/state write | The compound write |
|------|-----------------------|--------------------|
| **Autonomous** | The unilateral DECISION → `run-log.md` (labeled, confidence-rated row) | The compoundable FINDING → a `decisions.md` entry marked `compoundable` |
| **Orchestrated** | A finding that changes FUTURE work → `decisions.md` (worker-facing, append-only). A finding that changes only the IN-FLIGHT resume state (an active doubt, a new red set, a changed resume point) → the matching `state-capsule.md` Active section (atomic overwrite). A finding that is BOTH goes to both; one that is neither is logged in `run-log.md` only. (No "residual" catch-all — each finding routes by what it changes.) | The compoundable FINDING → its `decisions.md` entry carries the `compoundable` marker (a forward-affecting finding that is ALSO harvest-worthy is ONE marked entry, not a second file) |
| **Interactive halt** | Findings surface to the user live | A compoundable finding is still appended to `decisions.md` with the `compoundable` marker so the harvest source is durable; correction-driven capture is `rbtv-compounding`'s job in the moment |

`deliverables.md` is the PLAN's file (owned by `rbtv-planning`), unchanged by this spine. The compound source is no longer a separate file: harvest-worthy findings are `decisions.md` entries carrying the `compoundable` marker, and `rbtv-compounding` covers correction-driven capture in the moment. A plan-less run's compoundable findings surface to the user at run end per the run mode.

---

## 7. Registrar discipline — log dispatches AND results

The orchestrator is the run's registrar: every dispatch and every result is logged to `run-log.md` AS IT HAPPENS. An unlogged dispatch is invisible to a resumed conductor — it cannot tell a never-sent task from a sent-but-unreturned one.

| Rule | Detail |
|------|--------|
| **Log both directions** | Append a row when a dispatch goes OUT (task, worker, timestamp) AND when its result comes BACK (status, reconciled outcome). A run-log with dispatches but no returns cannot be resumed correctly. |
| **Re-read the tail after any gap** | After a context refresh, an interruption, or ANY gap in the conductor's continuity, RE-READ the `run-log.md` tail (and `state-capsule.md`) before dispatching again — never resume from memory of what was dispatched. The log is the ground truth for "what is in flight." |
| **Update the capsule in lockstep** | Each logged event that ADVANCES the run also updates `state-capsule.md` (resume point + timestamp). "Advances" = changes the resume point (a batch/task completed, the next dispatch changed), the active red sets, or the active doubts/blockers. An event that does NOT change any of those (e.g., a logged drift instance the conductor immediately reconciled, a mid-batch probe) lands in `run-log.md` ONLY — it does not force a capsule rewrite. The append-only log records every event; the mutable capsule records only the new resume state. |
| **Name a CLI-worker result by (harness, harness-version, model)** | When a CLI-worker result is recorded in the spine (the run-log result row, a delegation-map entry, a capsule resume note), name it as **(harness, harness-version, model)** — e.g. `opencode 1.17.11 / deepseek-v4-flash` — NEVER a bare provider word. A CLI harness serves configurable models (opencode's provider set is the live case: one `opencode` harness, many selectable `provider/model` ids), so a bare provider word under-identifies which worker actually ran and is not reproducible on resume. This is the single statement of the attribution convention; other surfaces that record a result POINT here. |

This is the discipline that makes the run survivable across sessions: state lives in the files, not in the process.

**Merge-back discipline — never merge onto a foreign-dirty target.** When a wave's work was done on a worktree branch and is to be merged back, NEVER merge that branch onto a target path carrying uncommitted changes owned by ANOTHER session (foreign-dirty). A merge over a foreign-dirty target silently clobbers the other session's applied-but-uncommitted work. Instead DEFER the merge and record it in `state-capsule.md` as a resume obligation (an Active doubt/blocker or a Resuming-Conductor note): the branch to merge, the target, why it is held (foreign-dirty), and the condition that clears it (the foreign hunks committed or attributed). The resumed conductor reads the obligation and completes the merge once the target is clean.

### Conductor commit discipline — pathspec-scoped, index-clean, atomic (possibly-concurrent repos)

In a repo that may have concurrent writers, the conductor performs ALL spine/fold commits under three binding constraints. `git commit` commits the WHOLE index, so a bare commit sweeps a parallel session's staged files (fold commit `5fc186f` swept 22 foreign staged deletions; a later close commit then swept 6 more through a TOCTOU window despite a hard gate that ran in a separate shell call):

| Constraint | Rule |
|------------|------|
| **Pathspec-scoped** | Stage with `git add <exact paths>` and commit with `git commit -- <exact paths>`; NEVER `git add -A` / `git add .` / a bare `git commit`. The pathspec ON THE COMMIT excludes foreign staged entries mechanically — even ones already in the index. |
| **Hard index-clean gate** | Before staging, the index-clean check is a HARD CONDITIONAL that aborts the chain — `git diff --cached --quiet || <stop and reconcile>` — NEVER a printed observation (a printed-but-ungated check is a no-op under exactly the concurrency it exists for). On a dirty index: stop, identify the foreign staging, then either let it ride DISCLOSED (the commit message names it) or unstage-and-restage around it — never proceed blind. |
| **Atomic** | The gate, the staging, the staged-list verification (`git diff --cached --name-only` is only-yours), and the commit run as ONE chained shell invocation — never across separate tool calls. A gate in one call and the commit in a later one leaves a sub-second window a parallel session stages into. |

Recovery is forward-only: a foreign sweep is disclosed in a follow-up commit, NEVER fixed by `git commit --amend` / `reset` in a shared repo (the vault parallel-sessions rule). The worker-side twin of the pathspec rule is dispatch-wrapper §2 (Commit discipline); this is the conductor side.

### The state-transition stamp — `stamp.py` performs the four writes (single authority)

A semantic state transition (a task reaching `in_progress` / `completed` / `deferred`) touches up to four bookkeeping files: the plan task-list checkbox, the task file's `status:` frontmatter, the `deliverables.md` row, and — conductor only — the `run-log.md` event with its `state-capsule.md` lockstep. These four are NOT four hand-edits: they are ONE invocation of `{rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py`. This is the single specification of that call; every other procedure that advances a task's state POINTS here and never restates the invocation.

| Scope | Call | Surfaces written |
|-------|------|------------------|
| **Worker** stamping its OWN task | `stamp.py --plan-dir {plan} --task {id} --status {in_progress\|completed\|deferred} --scope worker` (+ `--reason` for a deferral, `--artifact` to set the deliverables Path cell) | The three worker surfaces ONLY: plan checkbox, task `status:` frontmatter, `deliverables.md` row. The run-log and capsule are HARD-BLOCKED in worker scope (§5 audience separation enforced at the CLI). |
| **Conductor** advancing the run | `stamp.py --plan-dir {plan} --task {id} --status {…} --scope conductor --event-type {dispatch\|return\|gate\|probe\|drift\|recovery\|override\|handover} --outcome "<text>" --next-dispatch "<text>"` (+ `--worker "<cell>"`, default `conductor`; `--resume-note "<text>"` for the capsule `Last completed` bullet, derived fallback if absent; `--reason` / `--artifact` as needed). The script COMPOSES the Event Log row — timestamp auto-generated; NEVER pass a pre-formatted table row. | All four: the three worker surfaces PLUS the composed-and-appended `run-log.md` Event Log row and the `state-capsule.md` Resume Point lockstep (`Last completed` / `Next dispatch` / `Last update`, labels preserved). |

The call is all-or-nothing (every target validated before any write — a missing target writes nothing and EXITs non-zero), idempotent (a re-run is a no-op; the run-log append is deduped on `(event-type, task, worker, outcome)` — the auto timestamp is ignored), and refuses to guess on unrecognized structure. Run with `--explain` to preview every target's current→would-write value (including the composed row) without writing.

**Conductor-executed plan-line task — no task file (the `--no-task-file` flag).** A task the conductor executes itself has plan presence (checkbox + deliverables row) but NO `{id}.task.md` — no worker, so nothing scaffolded the artifact. For its transitions (in_progress AND completed/deferred), add `--no-task-file` to the conductor call: the script SKIPS the absent task-frontmatter surface and stamps the three that exist (checkbox, deliverables, run-log + capsule), reporting `task_frontmatter: skipped (no task file)`. This is the SAME one call the conductor always makes plus one flag — NOT the stamp-failure path below: a missing task file is the EXPECTED, sanctioned shape here (intake §52), not an error. The flag REQUIRES the task file to be absent and refuses if one exists, so a genuinely missing WORKER task file (a scaffold defect) is still caught by the unflagged call.

**A stamp FAILURE halts the transition loudly.** A non-zero EXIT from `stamp.py` means the transition did NOT complete — STOP. Do NOT fall back to hand-editing the four files to "finish" the transition: a manual fallback is allowed ONLY when the conductor first appends a `run-log.md` event recording the stamp failure, the reason, and that the transition is being completed by hand (so the audit trail shows the deviation). Re-running the same stamp after fixing the cause is the normal recovery — the convergent writes already applied stand, and the dedup key keeps the re-run clean (§S9 recoverable-partial-write model). Full CLI contract and failure semantics: `{rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py` (run `--help`).

---

## 8. Refresh and resume

The spine is the resume artifact — there is NO separate handoff document. Context-refresh and resume both rebuild the conductor from `state-capsule.md`.

| Operation | Procedure |
|-----------|-----------|
| **Context-refresh (suggest mode)** | The refresh offer is a MANDATORY CHECKLIST ROW of the phase-boundary / checkpoint procedure — a deterministic step the conductor runs every time it reaches an approved clean phase boundary, NOT a mid-phase self-assessment the conductor must remember to fire. At EVERY such boundary, before advancing, the conductor records one line: **offer context refresh — yes/no + a one-line reason** (e.g. "yes — phase 3 done, {N}% context used, clean capsule" where {N} is the real % injected by the context-monitor hook; "no — phase short, context ample"). On a yes that the owner approves: ensure `state-capsule.md` reflects the next dispatch, the log tail is current, then STOP — the fresh session resumes from the capsule. The row fires at the boundary ONLY — never mid-phase, never before the full delegation map is set (intake §7 sets the policy; this card owns the mechanics). Making the offer a boundary-row replaces the old unmeasurable "offer when context feels like it is filling" self-trigger, whose protective intent (catch long-session drift before it corrupts a run — the ~9h session that missed its refresh) is now CARRIED by this deterministic row: the boundary is the measurable moment, and the one-line reason forces the conductor to state the context/drift judgment explicitly instead of silently skipping it. For NON-Claude conductors that cannot read the Claude Code transcript, the worker-return count since the last refresh is a documented fallback proxy — the harness-agnostic-conducting task owns the full treatment; that counting script is not built here. |
| **Context-refresh (off mode)** | Keep the same conductor unless the session is interrupted; the spine is still the recovery artifact if it is. |
| **Resume (new session)** | Read `state-capsule.md` FIRST (resume point + delegation map + active red sets + active doubts), THEN the `run-log.md` tail to confirm what is in flight, THEN `decisions.md` for the rulings in force. Skip already-completed work per the resume point + completed batches; never redo a batch the capsule marks done. **Capsule absent or corrupted (and no recoverable `.tmp`):** reconstruct the resume state from the `run-log.md` tail — the last Run Configuration row gives mode/refresh/paths, the last logged event gives the resume point and what was in flight, and the registers give the rulings — then re-write a fresh capsule before dispatching. The run-log is the append-only ground truth the mutable capsule is derived from; it can always rebuild the capsule. |

A resumed conductor that reads the capsule, reconciles the log tail against disk, and re-pins the in-flight dispatch is a clean continuation — the run does not restart, it continues. NEVER create a separate context-handoff file: the capsule is the contract.

---

## Hand off — back to the loop

This card's job is to keep the spine correct: the right file holds the right thing, in the right shape, with the right audience, and a decision that touches queued work reaches every artifact that must carry it. From here the run's normal flow continues — routing and the dispatch-wrapper produce and send the next dispatch (carrying the `decisions.md` pointer), verification reconciles its return against the disk the spine records, and halt-recovery writes its errata and recovery rows through this card's semantics. Follow the situation table in the core protocol; this card is opened whenever a state file is written and whenever a run is resumed, and its responsibility is that those writes obey the spine.
