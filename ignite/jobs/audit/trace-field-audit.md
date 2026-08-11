# trace-field-audit — task `7.118` / `M4-03`

The field-by-field contract between the run trace and its two new consumers, task rows **`7.56`
items (b) and (c)** and **`7.77`**. Produced by seat `trace-field-auditor`, 2026-07-30.

This artifact is a **design input**, not documentation: `M4-08`, `M4-11`, `M4-12` and `M4-14` build
against its `reads` list, and `M4-07` (task `7.122`) routes on its `verdict.sufficient`.

**The two halves are separated on purpose.** §2 is the JUDGMENT half — which sites the consumers
read, derived from their task-row text, arguable. §3 is the EXACT half — whether each named field
exists, produced by a command whose invocation and output are recorded in §4 and re-runnable. A
reader who did not watch this seat work can re-run §4 and check §3 without trusting §2.

---

## 1. Verdict

```
verdict:
  sufficient: true
  missing: []
```

`sufficient` is **true**, and it is true *by construction*: §4's command computes
`missing[]` by set arithmetic over the `reads` list (`{surface}::{field}` for every row whose
`present` is false) and then computes `sufficient = (missing == [])`. Neither value is transcribed.

**What this verdict does and does not claim.** It claims: every column the derivation in §2 says
these consumers read EXISTS in the header of the surface it must live on, measured against the
live files. It does **not** claim the trace is populated for every session, and it does not claim
any consumer has ever run — nothing has resumed from or recomputed off this trace. §5 carries the
population measurement, which is a different claim and answers differently on two fields.

**Routing consequence:** `M4-07` (task `7.122`) takes its EARLY EXIT. Its declared no-op output
applies: `{sufficient: true, action: none, reason: "every field enumerated in trace-field-audit.md
§3 is present in the live header of its surface; missing[] is empty"}`. **No criterion is added to
task `7.37`, and `7.37` is not closed, proposed for closure, or touched by this audit.**

---

## 2. The JUDGMENT half — deriving the read sites

Each site below is derived from the consuming task row's own words, quoted. Where the row does not
name a column, the derivation is stated and the ambiguity is named in §2.4 rather than resolved
silently.

### 2.1 `7.56` item (b) — the run-state recompute CLI (built by `M4-12`, task `7.127`)

Row text: *"**(b) the run-state recompute CLI** — done/ready/running/skipped/failed derived from
disk artifacts (check-out record + declared outputs), no status column anywhere; the CLI is
REGISTERED AS A JOB so human, agent, and daemon share one computation"*.

Five states, taken one at a time:

| State | Derived read | Field · surface |
|---|---|---|
| `done` | the seat's **check-out record**. Its durable home is the `disposition` column of the session row (`coord.py:1860-1867`: *"`disposition` (dag-09) is APPENDED LAST, and it is the DURABLE home of the value the DAG reads"*). It is located by the seat's LAST ENDED row (`session_disposition`, `coord.py:2510-2541`), so `seat` and `ended` are read to find the row before `disposition` is read off it. | `seat`, `ended`, `disposition` · `{RUN}/sessions.csv` |
| `failed` | the SAME three fields, read for the complement: an `ended` row whose `disposition` is `exited`, or is empty. **`coord.py:1867` — "AN EMPTY CELL IS `unknown`, NEVER `done`"**; `session_disposition` returns `None` for it, and `None` never means `done`. No extra field is needed to distinguish failure from success. | `seat`, `ended`, `disposition` · `{RUN}/sessions.csv` |
| `ready` | every `after` predecessor holding a `done` check-out. The `after` set is **not on the trace** — it is the `after` column of `taskforce.csv`, read per `seat` (`taskforce_after`, `coord.py:8667`). Recorded here because the done-contract requires the site to name a concrete column rather than a surface. | `seat`, `after` · `{RUN}/taskforce.csv` |
| `running` | **reading taken:** the seat's LAST session row has `ended` empty — an open row is a live sitting, and it is the only disk-artifact answer the trace itself gives. **See ambiguity A-2**: the kit's existing predicate answers `RUNNING` from the roster instead. | `ended` · `{RUN}/sessions.csv` (taken) · `agent`,`active` · `{RUN}/coordination/workers.md` (alternative) |
| `skipped` | **resolves to NO column.** The state is guard-excluded, `M4-09` builds no guard evaluator, and nothing can produce it (DAG §M4-12: *"ONE STATE IS DEFINED AND UNREACHABLE"*; `issues.md` G-301, G-308). Carried as a visible read-site with `field: null` rather than dropped or padded with a fabricated column. | — |

Plus **`declared outputs`**, the row's second named input: it resolves to no column either. A seat's
outputs are declared in its own materialized `seat.md` `<io-spec> Outputs`, and the artifacts are
files at those paths. Carried with `field: null`; 44 `seat.md` instances exist on disk (§4).

### 2.2 `7.56` item (c) — the check-out fast path (built by `M4-11`, task `7.126`)

Row text: *"**(c) the check-out fast path** — a seat's clean check-out (CMP-22 surface) enqueues
that seat's edge job immediately"*.

Two things must be read: **whose** edge job, and whether the check-out was **clean**.

- `seat` · `{RUN}/sessions.csv` — which seat's edge job to enqueue.
- `disposition` · `{RUN}/sessions.csv` — "clean" means exactly `done`. The value space is closed and
  named: `RECORD_DISPOSITION_WRITER = {done, renew, revive, exited}` (`coord.py:1917-1920`),
  validated at write time by `validate_disposition` (`coord.py:1923`), which RAISES and never
  normalizes. `done` is the only value that advances an edge; `M4-11`'s discriminating control
  (a `renew`/`exited` check-out produces NO edge job) is answerable from this one field.
- `disposition` · `{RUN}/coordination/awaiting-close.json` — the LIVE declaration at the moment of
  check-out, written by `set_awaiting` from the same enum through the same validator. The fast path
  fires *during* `cmd_checkout`, so it may read the value in-process from this surface rather than
  re-reading the csv it is in the middle of writing. Recorded so a builder is not blind to it;
  `terminal_disposition` (`coord.py:8689`) reads BOTH and reports SKEW rather than tie-breaking.

**`ended` is NOT read by item (c)** — the fast path fires as the row is closed, so the value it
would test is the one its own act is writing.

### 2.3 `7.77` — the R9 one-live-run queue rule (built by `M4-14`, task `7.129`)

Row text: *"a recurring goal's scheduled start that finds an OPEN run **QUEUES and notifies the
owner** — it never overlaps two live runs of one goal, and it **never silently skips**"*.

- `state` · `<goal>/runs.csv` — the single answer to *"is this run live?"*. `.rbtv/goals/CLAUDE.md`
  makes this normative: *"Never introduce a second place that answers 'is this run live?' (PRIN-11)"*.
- `run-id` · `<goal>/runs.csv` — names the open run the scheduler found, which the queued row and
  the notification must both reference.

**`closed` is deliberately NOT a read site.** Deriving open-ness from `closed` being empty would be
a second answer to the same question and is refused by PRIN-11 — `state` answers it. **`7.77` reads
NOTHING from `sessions.csv`**; its surface is the goal-level index only. That null result is stated
rather than left as an omission.

The queued row and the notification are not trace surfaces — they live in the daemon queue and the
notifier path, which `M4-14` and `M4-15` own.

### 2.4 Ambiguities — NAMED, not silently resolved

Both consuming rows describe behaviour and name **no columns at all**. Every field in §2 is
therefore derived, not quoted. Two derivations are genuinely contestable:

**A-1 — item (b) names its inputs as "check-out record + declared outputs" and enumerates no
fields.** Reading taken: the check-out record IS the `disposition` column plus the `seat`/`ended`
pair that locates it, because that is the surface `coord.py`'s own durable reader
(`session_disposition`) uses and the comment at `coord.py:1860-1866` states it was placed on the
session row deliberately, rejecting `taskforce.csv` and a new coordination file as the alternatives.
"Declared outputs" resolves to no column at all (§2.1). **Discriminator:** if `M4-12` finds it needs
a field not in §3, `M4-08`'s and `M4-12`'s own criteria require it be REPORTED rather than added
silently — this list is a floor, and it is safe as a superset, dangerous as a subset.

**A-2 — item (b)'s `running` state has two disk-artifact answers, and this audit did not settle
which the CLI must use.** (i) The trace: the seat's last row has `ended` empty. (ii) The roster:
`ready_seat_rows()` (`coord.py:8720`) derives `RUNNING` from *"an ACTIVE roster row"* via
`load_workers`, i.e. `{RUN}/coordination/workers.md` `agent`/`active`, not from the trace at all.
Reading taken: (i), because item (b) says *derived from disk artifacts (check-out record …)* and the
trace is where the sitting is recorded. **But `M4-12`'s criterion 1 requires the CLI's output to
AGREE with `M4-09`'s predicate on the same fixture**, and `M4-09`'s ancestor predicate uses (ii) —
so if the two disagree on a crashed seat (open trace row, no active roster row) the criterion fails
regardless of which is right. **Both readings' fields are carried in `reads` and both are present**,
so no builder is blind either way; **which one the CLI must use is a design question above this
seat's radius and is reported to the `leader`.** What would discriminate it: a fixture with a seat
whose session row is open and whose roster row is inactive — the two readings return different
states on exactly that seat.

**No surface named by any consumer is absent.** All five surfaces resolved on disk (§4).

---

## 3. `reads` — the field-by-field list

`present` in this table is the EXACT half, copied from §4's recorded output. `field: null` marks a
read-site that resolves to no column; those rows are excluded from the presence arithmetic
explicitly, never silently.

| # | consumer | item | field | surface | present |
|---|---|---|---|---|---|
| 1 | `7.56` | (b) run-state recompute CLI — seat key | `seat` | `{RUN}/sessions.csv` | **true** |
| 2 | `7.56` | (b) run-state recompute CLI — `done`/`failed` | `ended` | `{RUN}/sessions.csv` | **true** |
| 3 | `7.56` | (b) run-state recompute CLI — `done`/`failed` | `disposition` | `{RUN}/sessions.csv` | **true** |
| 4 | `7.56` | (b) run-state recompute CLI — `ready` | `after` | `{RUN}/taskforce.csv` | **true** |
| 5 | `7.56` | (b) run-state recompute CLI — `ready` | `seat` | `{RUN}/taskforce.csv` | **true** |
| 6 | `7.56` | (b) run-state recompute CLI — `running`, reading TAKEN | `ended` | `{RUN}/sessions.csv` | **true** |
| 7 | `7.56` | (b) run-state recompute CLI — `running`, ALTERNATIVE reading (A-2) | `agent` | `{RUN}/coordination/workers.md` | **true** |
| 8 | `7.56` | (b) run-state recompute CLI — `running`, ALTERNATIVE reading (A-2) | `active` | `{RUN}/coordination/workers.md` | **true** |
| 9 | `7.56` | (c) check-out fast path — whose edge job | `seat` | `{RUN}/sessions.csv` | **true** |
| 10 | `7.56` | (c) check-out fast path — is the check-out CLEAN | `disposition` | `{RUN}/sessions.csv` | **true** |
| 11 | `7.56` | (c) check-out fast path — live declaration at the moment of check-out | `disposition` | `{RUN}/coordination/awaiting-close.json` | **true** |
| 12 | `7.77` | one-live-run queue rule — is a run OPEN | `state` | `<goal>/runs.csv` | **true** |
| 13 | `7.77` | one-live-run queue rule — WHICH run is open | `run-id` | `<goal>/runs.csv` | **true** |
| 14 | `7.56` | (b) run-state recompute CLI — `declared outputs` | `null` | `{RUN}/seats/*/seat.md` `<io-spec>` Outputs + the artifact paths it names | `null` — no column resolves this site (44 instances on disk) |
| 15 | `7.56` | (b) run-state recompute CLI — `skipped` | `null` | none — DERIVED state, computed from `edge-runner-job.readiness()`'s THIRD verdict list (task 7.425 built the guard evaluator) | `null` — no column resolves this site |
| 16 | `7.475` | durable disposition reader — row selection among OPEN session rows (`sessions_open_ids`, `coord.py`; added by the 7.475 reader widening, audited 7.607 E4) | `session-id` | `{RUN}/sessions.csv` | **true** |
| 17 | `7.615` | nested launch arm — WHICH instance a nested-workflow row expanded to, and whether every row of THAT instance is terminal | `taskforce-id` | `{RUN}/taskforce.csv` | **true** |

**15 rows `present=true` · 0 rows `present=false` · 2 rows `present=null` · `missing[] = []`.** (Row 16 appended 2026-08-10, task 7.607 E4 — the E3b `reads-match-coord-reader` red's prescribed remedy; the 13-row tally below this point is historical.)

> [!note] Row 17 appended 2026-08-10, task 7.615, under the owner grant `d-r2-taskforce-id-read-granted`.
> `present` is **true** off §4's own recorded header — `{RUN}/taskforce.csv` reads
> `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id`, and `taskforce-id` is its
> first column. No re-run of §4's script produced this row and none is claimed: the column's
> presence is read from the header §4 already recorded, which is the same evidence rows 4 and 5
> stand on for the same surface.
> **The grant is ONE COLUMN AT ONE STAGE.** It authorizes `edge-runner-job.py`'s STEP-5 nested arm
> to read `taskforce-id`, and nothing else. The arm needs it because a nested instance is a ROW SET
> and its id is the only thing that names it: a second instance of the SAME workflow carries the
> same four-letter name prefix, so scoping a terminal mark by name prefix marks a sibling
> instance's rows too. It reads no second column under this grant — the milestone-id a
> materialization would otherwise carry forward is deliberately NOT read, and the instance is
> materialized without one rather than acquiring an unaudited read.

> [!warning] Row 15's reason clause was CORRECTED on 2026-08-06 (task 7.454 / MC12). The original is retained here, not erased.
> **As originally written:** *"none — the state is unreachable, no guard evaluator is built (G-301/G-308)"*.
> That was true of M4-09's world and became FALSE when **task 7.425** built the guard evaluator:
> `edge-runner-job.readiness()` returns the guard-excluded rows as a third verdict list, and task
> 7.454 gave `run-state-job.py`'s `run_state()` the arm that emits them, so the state is REACHABLE
> and is reported on real rows.
> **The VERDICT column did not move and was never wrong** — `skipped` is derived state and no
> column resolves it (Rule 14), which the evaluator did not change. Only the reason moved.
> **The cited causes are NOT thereby closed:** `issues.md` G-301 and G-308 stand on their own rows;
> they simply stopped being the reason this state could not be produced.
> Corrected under a claim-shaped grant from the `leader` — that one claim in this one file, never
> this folder (run-3 `decisions.md#p-mc12-granted-the-audit-row-claim-not-the-folder`, message
> #5059). `planning/` remains the planning seats' surface in every other respect.

---

## 4. The EXACT half — the command, its invocation, and its output

**Script:** `{RUN}/seats/trace-field-auditor/presence-check.py`
`sha256 44d54102a7fe509d0c65a82168a043a597d274b1a43953adabf932e34fe4f62a`
**Invocation:** `cd {RUN}/seats/trace-field-auditor && python3 presence-check.py`

The script takes §2's derivation as data and computes everything else from disk: it reads each
surface's real header (csv header line · markdown table header row · json object keys), answers
`present` by membership, computes `missing[]` by set arithmetic over the reads list, and computes
`sufficient = (missing == [])`.

```
== SURFACES AS READ FROM DISK ==
{RUN}/sessions.csv  [csv]
    session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,pid-starttime,tty,disposition   (26 data rows)
<goal>/runs.csv  [csv]
    run-id,type,state,taskforce-ids,opened,closed   (3 data rows)
{RUN}/taskforce.csv  [csv]
    taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id   (44 data rows)
{RUN}/coordination/workers.md  [md]
    agent,active,tmux pane,working on,checked in,checked out,last-read
{RUN}/coordination/awaiting-close.json  [json]
    disposition,exported,handoff_stamp,pane,pids,since,transcript

== PRESENCE, per read row (EXACT half) ==
  7.56  (b) run-state recompute CLI — seat key                         seat         {RUN}/sessions.csv                         present=True
  7.56  (b) run-state recompute CLI — `done`/`failed`                  ended        {RUN}/sessions.csv                         present=True
  7.56  (b) run-state recompute CLI — `done`/`failed`                  disposition  {RUN}/sessions.csv                         present=True
  7.56  (b) run-state recompute CLI — `ready`                          after        {RUN}/taskforce.csv                        present=True
  7.56  (b) run-state recompute CLI — `ready`                          seat         {RUN}/taskforce.csv                        present=True
  7.56  (b) run-state recompute CLI — `running`, reading TAKEN         ended        {RUN}/sessions.csv                         present=True
  7.56  (b) run-state recompute CLI — `running`, ALTERNATIVE reading (A-2) agent        {RUN}/coordination/workers.md              present=True
  7.56  (b) run-state recompute CLI — `running`, ALTERNATIVE reading (A-2) active       {RUN}/coordination/workers.md              present=True
  7.56  (c) check-out fast path — whose edge job                       seat         {RUN}/sessions.csv                         present=True
  7.56  (c) check-out fast path — is the check-out CLEAN               disposition  {RUN}/sessions.csv                         present=True
  7.56  (c) check-out fast path — live declaration at the moment of check-out disposition  {RUN}/coordination/awaiting-close.json     present=True
  7.77  one-live-run queue rule — is a run OPEN                        state        <goal>/runs.csv                            present=True
  7.77  one-live-run queue rule — WHICH run is open                    run-id       <goal>/runs.csv                            present=True
  7.56  (b) run-state recompute CLI — `declared outputs`               (none)       {RUN}/seats/*/seat.md  <io-spec> Outputs + the artifact paths it names
        present=None — no column resolves this site; surface instances on disk: 44
  7.56  (b) run-state recompute CLI — `skipped`                        (none)       (none — DERIVED: readiness()'s third verdict list; task 7.425 built the guard evaluator)
        present=None — no column resolves this site; surface instances on disk: 0
        ⚠ CORRECTED 2026-08-06 (task 7.454 / MC12), same correction as the table's row 15 and on
          the same grant. As originally listed, retained verbatim and unwrapped so it stays one
          searchable string:
          "(none — the state is unreachable: no guard evaluator is built; G-301/G-308)"
          The present=None verdict is unchanged and was never wrong; only the reason moved.
          See the warning block under the row-15 table above.

== VERDICT (computed by set arithmetic over the reads list) ==
  rows total            15
  rows present=True     13
  rows present=False    0
  rows present=None     2
  absent-surfaces       []
  missing[]             []
  sufficient            True   (== (missing == []))
```

### 4.1 Red before green — the presence arithmetic proven to return false

A check nobody has watched fail establishes nothing. Two control rows were ADDED to the script's
`READS` list and the script re-run unchanged otherwise:

```
  MUTANT red control A — column absent from a PRESENT surface           no-such-column <goal>/runs.csv           present=False
  MUTANT red control B — surface absent                                 state          {RUN}/no-such-file.csv    present=False  <- surface absent
== VERDICT ==
  rows present=False    2
  missing[]             ['<goal>/runs.csv::no-such-column', '{RUN}/no-such-file.csv::state']
  sufficient            False   (== (missing == []))
```

Reverted, proven by hash: `sha256 44d54102a7fe509d0c65a82168a043a597d274b1a43953adabf932e34fe4f62a`
(identical to the pre-mutation hash), `grep -c MUTANT presence-check.py` → `0`, and the re-run
returns `missing[] = []`, `sufficient = True`.

**Bound this control exposed, stated rather than hidden:** control B shows a read row whose SURFACE
is absent scores `present=False` and lands in `missing[]` next to a genuinely missing column. This
audit's outcome map routes those two differently — a missing *surface* is not a missing *field* —
so the split would be made by hand. On the recorded run it is moot: `absent-surfaces = []` and no
read row names an unresolved surface.

### 4.2 Handed-down premises, confirmed on disk

| Premise handed to this seat | Confirmed | How |
|---|---|---|
| run-3 header is `session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,pid-starttime,tty,disposition` (manifest `7.118` input-description) | **YES, character for character** | python string equality against `head -1`; printed `EQUAL: True` |
| `pid`/`pid-starttime`/`tty` are present, i.e. 7.37's widen has fired on run-3 | **YES** | present in the header above; all three populated 26/26 |
| `taskforce_after()` is at `coord.py:8667` | **YES** | `sed -n 8667p` → `def taskforce_after(pkg):` |
| `session_disposition` / `session_close` / `validate_disposition` / `RECORD_DISPOSITION_WRITER` / `SESSIONS_COLS` line refs cited above | **YES** — 2510 · 2442 · 1923 · 1917 · 1868 | `grep -n` + `sed -n Np` on `coord.py` (`sha256 df7c231fe2bd0a21…`) |
| task rows `7.56` and `7.77` exist and carry items (b), (c) and the R9 rule | **YES** | `sb-task read rbtv-sb-merge-refactor-core-build 7.56` / `7.77` |

No handed-down premise was found wrong.

---

## 5. "The column exists" ≠ "the column is populated"

Required distinctly by `M4-03`'s DAG criterion 4, because a sufficiency claim is not a schema
claim. Measured by the same command, over run-3's live rows:

| surface | field | populated | observed values |
|---|---|---|---|
| `{RUN}/sessions.csv` | `seat` | 26/26 | 23 distinct |
| `{RUN}/sessions.csv` | `ended` | **19/26** | 18 distinct — 7 rows are open sittings, correctly empty |
| `{RUN}/sessions.csv` | `disposition` | **18/26** | `done`, `renew` only |
| `{RUN}/taskforce.csv` | `after` | **32/44** | 27 distinct — 12 empty cells are roots, correctly empty |
| `{RUN}/taskforce.csv` | `seat` | 44/44 | 44 distinct |
| `<goal>/runs.csv` | `state` | 3/3 | `open`, `closed` |
| `<goal>/runs.csv` | `run-id` | 3/3 | `run-1`, `run-2`, `run-3` |

Three population facts the builders must not read past. **None of them makes a field missing** —
each is a property of the data, not of the schema — and none changes `verdict.sufficient`.

**P-1 — one CLOSED session row carries NO disposition.** Measured:

```
== CROSS-CHECK: closed session rows carrying NO disposition ==
  ended set & disposition empty: 1/26  ['staffer-20260730-0534']
```

This is **by design, not a defect**: `session_close` (`coord.py:2442`) takes `disposition=""` by
default, and only `checkout` is the seat declaring its own — *"`close-seat` and `depart` are
somebody else ending the row, and neither witnessed what the occupant meant."* The empty cell reads
as **`unknown`, never `done`** (`coord.py:1867`; `session_disposition` returns `None`). So the
correct handling for `M4-08`'s and `M4-11`'s readers is: **empty ⇒ NOT done ⇒ no edge advances, no
edge job enqueued.** A reader defaulting an empty cell to `done` would advance this run's DAG past
`staffer` on a check-out nobody made.

**P-2 — `exited` and `revive` are in the enum but appear ZERO times in run-3's live trace.** The
observed value set is `{done, renew}`. `M4-08`'s criterion 2 requires the discriminating control
that `renew`, `revive` and `exited` each mark NOT-done — **run-3's trace supplies a live example for
`renew` only.** `revive` and `exited` must be exercised on a FIXTURE or on the throwaway goal
`{TG}`; they cannot be evidenced from this run's data. Stated here because "the column can carry
`exited`" (schema, true) and "an `exited` row has ever been written" (fact, false here) are two
claims, and `M4-08`'s control needs the second.

**P-3 — the `recorded` column is populated 0/26.** Not read by any consumer in §2 (it is task
7.31's pipe-pane marker), so it is out of this audit's radius and changes no verdict. Recorded
because a builder scanning the header will see it and should know it is empty on this run by
observation, not assume it is optional by design.

---

## 6. What this seat could NOT determine

Stated as prominently as what it could.

1. **Which `running` reading the recompute CLI must use (A-2).** Both readings' fields are present;
   choosing between them is a design question above this seat's radius. Reported to the `leader`.
2. **Whether the derivation in §2 is COMPLETE.** Neither consuming row enumerates columns, so §2 is
   a reading of intent, not a quotation. This list is safe as a superset and dangerous as a subset;
   `M4-08` criterion 3 and `M4-12` already require a builder needing a field absent here to REPORT
   it rather than add it silently. That reporting path is the backstop for this limit.
3. **Whether any of these consumers can actually run against the trace.** Nothing has ever
   recomputed run-state from it or resumed from it — `7.37` criterion 4 is recorded as *"MET AGAINST
   THE CONTRACT, NOT PROVEN BY USE"* and task `7.32`'s restart path is unbuilt. This audit answers a
   SCHEMA question and a POPULATION question. It answers no sufficiency-by-use question, and
   `verdict.sufficient` must not be read as one.

---

## 7. Feedback schema

```
{ambiguous-consumers: [
   {row: "7.56", item: "(b) run-state recompute CLI",
    readings: ["check-out record == sessions.csv{seat,ended,disposition} (taken)",
               "declared outputs resolve to no column — seat.md <io-spec> Outputs"]},
   {row: "7.56", item: "(b) run-state recompute CLI — `running`",
    readings: ["sessions.csv{ended} empty on the last row (taken)",
               "coordination/workers.md{agent,active} — what ready_seat_rows() uses, coord.py:8720"]},
   {row: "7.56", item: "(c) check-out fast path",
    readings: ["sessions.csv{seat,disposition} (taken)",
               "coordination/awaiting-close.json{disposition} — live, read in-process at check-out"]}],
 absent-surfaces: [],
 presence-command: "cd {RUN}/seats/trace-field-auditor && python3 presence-check.py",
 presence-output: "see §4 — 15 rows: 13 present=true, 0 present=false, 2 present=null;
                   missing[] = []; sufficient = true"}
```
