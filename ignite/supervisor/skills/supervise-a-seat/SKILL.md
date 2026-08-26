---
name: supervise-a-seat
description: "Act on a seat you are not sitting in — rule on its ended session, accept its finished work, close or relaunch it, or route a FAIL back to its receiver. Use when a seat ended non-done and keeps re-waking your chair, when work you were asked to accept is finished, when a seat is blocked or out of context, or when a verdict has to reach the seat that authored the thing it failed. The instrument is the `supervise` CLI; `coordinate` is the OTHER door and does not accept these verbs."
exposes-cli:
  - supervise
---

# supervise a seat

`supervise` is the remedial half of the coordination entry point, split by AUDIENCE (owner ruling
2026-08-25): the daemon and a leader type these verbs; every working seat types `coordinate`. No
verb sits on both doors, so `coordinate accept` is refused by name at the parser — that refusal IS
the audience bound, and there is no per-verb role check anywhere in this kit
[T2-R10, D24, F-simplicity-7].

**Deterministic first: the CLI decides and records, you supply the judgment.** Every verb below
carries its own signature, one example and the step that usually follows in `supervise <verb> -h`.
Read that before composing a call; this file is the WHEN, the `-h` is the WHAT.

## Before anything: bare first, `--go` second

`instruct`, `accept`, `attest-exit`, `route-fail` and `reap` all REPORT when run bare and only
WRITE with `--go`. Run bare, read what it says it would change, then add `--go`. A bare run writes
nothing, so it costs a re-run and nothing else.

## The row ended and nothing can advance on it

A seat whose current ending is `failed` re-wakes your chair every reconcile cadence and will keep
doing so until a ruling changes that ending. Two verbs, and which one you use is a finding about
the WORK, never a preference:

| The work | Act |
|---|---|
| in fact CONCLUDED — you checked the artifacts | `supervise accept <seat> --anchor "<what you read>" --go` |
| did NOT conclude | `supervise instruct <seat> <kind> --go` |
| the harness simply DIED and the work must run again | `supervise launch --only <seat> --rerun <anchor>` — an ordinary working session; the `failed` row stays on the record (D42) |

**`accept`** stamps the seat's ending `done` in one act and every `after` edge waiting on it
advances. The seat's declared `## Outputs` are RE-CHECKED against disk first — an acceptance of
work whose outputs are not there is refused by name. `--anchor` is mandatory and is recorded, never
verified: no tool can check that an anchor names a real investigation, and a `done` citing nothing
is a `done` nobody can audit. Your authority for this act is the goal's own
(`concepts/leader.md`: *the leader holds the goal's authority — acceptance, the failure-path close
gate, the relaunch, the escalation*); the value-space ruling that admits it is `d-exited-row-closure`
(A-10).

**`instruct`** records your judgment where the daemon already drains it. Four kinds, a CLOSED list
— a fifth would be a remedy verb nobody ruled [D6, T4-R6]:

| Kind | What it says | It needs |
|---|---|---|
| `rewrite-brief` | the brief was wrong; here are the new words | `--brief-file <file> --brief-path <target>` |
| `reassign` | a different seat design takes this work | `--to-seat <seat>` |
| `blocked-pending-plan-gap` | the gap is in the PLAN, not the seat | `--gap "<what the plan does not say>"` (`--milestone <id>`) |
| `escalate` | nobody in this room can settle it; the owner must | `--report-file <file>` |

The file lands in the daemon's leader-instruction inbox and is applied ONCE at the top of the next
reconcile pass, then filed under `done/` with the outcome beside it. One file per (goal, seat):
writing again before it drains REPLACES your judgment rather than adding a second.

**THE WALL [CF-3, T2-R5]** — an instruction may carry a JUDGMENT, never the seat's work. A payload
holding a patch, a file body or an output is refused at the door. You report; you do not do the
seat's work for it.

**Text rides a FILE, never argv.** A shell eats backticks and `$(...)` before the command can see
them, and the corruption is undetectable afterwards. That is why `--brief-file` and `--report-file`
take paths and not strings.

⚠ **Do not reach for `rule-disposition`.** It was deleted whole with the authority model it
implemented [T2-R12, T1-R9], and `disposition` is a refused word at the ending store's own door.
Older mail in a goal's `messages.md` may still name it as *"the ONE sanctioned act"* — that mail is
stale. `accept` and `instruct` are not its return: they write the seat's ENDING, never a
`sessions.csv` cell.

## The seat is alive and has to stop, or come back

| Situation | Act |
|---|---|
| finished, or near its context limit | `supervise close-seat <seat> [--renew]` — exports its transcript, checks its row out, kills its pane |
| its pane is gone but the seat should continue | `supervise relaunch-pane <seat>` |
| panes are leaking | `supervise reap --go` |
| a NON-SEAT process must die | `supervise terminate-pid <pid>` — the authorization is recorded |
| it is stuck on a permission prompt | `supervise approve <seat>` |

`close-seat` on YOUR OWN name kills or respawns your own pane, so every step you planned after it
never runs. The command warns you; believe it.

## A FAIL has to reach whoever authored the thing that failed

`supervise route-fail "<the fail>" --go` (or `--file <path>`). The route is the seat's own
`on-fail-relaunch:` declaration; an UNDECLARED fail comes to the `leader`, because a verdict with
no declared receiver is exactly the case this system used to lose silently. The target is checked
for EXISTENCE — a well-formed name that names no seat is how a routed FAIL reached nobody.

## What is ready to run now

`supervise ready-seats` recomputes launchability from disk; `supervise ready-seats --explain <seat>`
says why one seat is not ready. Run it after any ruling — it is how you see what your act unblocked.

## What this door is NOT

Checking in, checking out, messaging, reading your queue, records and groups are `coordinate`'s —
skill `team-kit`. Recording a ruling in the goal's decision-log is `coordinate send --record
"<title>"`, which appends the ruling to `<goal>/decisions.md` in the SAME act as the message: a
ruling recorded only in a message is not recorded.
