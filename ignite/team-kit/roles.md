# team-kit — role catalogue

**Read this when you HOLD one of the special roles below** — leader, deputy, scientist, judge,
verifier, closer, watcher — **or when your seat runs a codex or opencode harness** (the Harness note
closes the file). Read it at boot, right after you know which role you are. A plain worker seat does
not: its own entry states only what `protocol.md` already binds it to. Split out of `protocol.md`
(beside this file) so a seat stops loading another role's discipline; `protocol.md` remains the
protocol every seat follows and carries the evidence-pointer scheme (`P-n`, `S§n`, `PROP-n`) the
entries below cite.

## Roles

- **leader** — support/arbiter, launched by the owner by hand; launches everyone else; sole reader
  of worker briefings (lazily); reads the full log; the ONLY door to the owner (R-owner-channel).
  Drain rule (measured, adopted): per batch, ESCALATE-FIRST — relay owner-gated items before
  ruling own items, triaging with `read --type ask` (peek-only: it never consumes the rest of the
  inbox) and `pending` for what is still open. Order the queue by how much each item UNBLOCKS
  downstream, never by arrival. Then cut the cost of each decision you pass upward, per
  `R-cheap-ask`: owner-gated items go up as ONE batched ask with a recommended default per item and
  any-subset/silence-is-held semantics — measured to compound with the ordering, where ordering
  alone did not clear the queue. Leader never writes to the run's target surfaces.
  Leader also carries the run's ONLY seat-lifecycle authority (launch/close/renew/approve), which
  makes it a single point of failure — see **deputy**.
- **deputy** (optional, rosters past ~8 seats or any AFK run) — a second seat briefed to take over
  SEAT LIFECYCLE only: launch, `approve`, watcher restarts, and the failure-path close (`close`,
  `close --renew`) for a seat that cannot check itself out — a healthy seat renews itself. It does
  NOT rule, does not talk to the owner (R-owner-channel is unchanged — leader remains the sole
  door), and does not write target surfaces. It exists because leader is renewable like any other
  seat: while leader is being closed and relaunched, nothing else in the run can start, close or
  unblock a seat, and an approval gate or a context-exhausted worker just waits.
- **scientist** — optional observer: reads the full log (auto-woken on every send), reads no
  briefings, writes field notes + improvement proposals incrementally, touches nothing else.
- **judge seats** — checkers per the registry's checker record: judge against PRE-DECLARED done
  criteria, issue structured verdicts (`--type verdict`) with explicit fail reasons, and also
  check leader's (and the run-assembler's) work. **Post per acceptance criterion, as each one is
  decided** (R-2) — one `verdict` message per AC the moment it is settled, never a batch held to
  the end. A batched verdict is write-through's exact failure mode (R-write-through): the findings
  exist only in the judge's context until the end, so a context loss takes all of them, and the
  worker sits idle on criteria that were settled an hour earlier. Judges still deliberate in their
  own group, and still close with ONE consolidated verdict — but that message SUMMARISES rulings
  already posted, it does not carry them for the first time.
- **verifier seats** (standing, one per kit-affecting fix) — every change to this kit's own code
  or rules gets an independent seat that re-derives the fix's claim against the pre-registered
  acceptance bar, adversarially, on its own fixtures. Not the fixer, not the fixer's judge for
  anything else. P35 needed three rounds and each round's defect was found by exactly this seat
  re-deriving the claim rather than reading the diff.
  **A verification script written as part of a change is INSIDE that change's blast radius** (D31):
  if the fix is wrong, the script built beside it is wrong in the same direction, and running it
  proves only that the two agree. The verifier's evidence must come from something the fix did not
  author — its own fixture, its own script, or a real captured artifact — which is also why this
  seat is never the fixer.
- **workers** — everyone else: execute exactly one briefing, message at coordination points,
  escalate decisions.
- **closer seats** (`closer-<target>`, spawned by `close`, kit prompt `closer-prompt.md`) —
  one-shot, and a FAILURE PATH ONLY: leader spawns one to dirty-close or salvage a seat that
  cannot check itself out. A healthy seat renews itself with `checkout --renew --handoff "<note>"`
  and no closer is in that path. The ceremony: co-write the target seat's `memory.md` with the
  target (transcript + log + a draft the worker corrects), run `close-seat` (with `--renew` when
  leader ordered the salvaged seat brought back), depart.
  A closer never touches deliverables, never rules open questions, never messages beyond target
  and leader.
- **watcher seats** — sentinel pattern: a deterministic monitor (`watch.py` beside `coord.py`)
  measures liveness, inactivity, approval-gate parking, claude-seat context usage, system
  RAM/load pressure (PROP-9) and leftover all-dead wave windows (PROP-10) on a loop and
  flags leader with the exact command to run (`close <agent> --renew` at the context threshold,
  `approve <agent>` at a gate, `tmux kill-window` for a dead wave window); the watcher agent
  keeps the loop alive and interprets, never acts
  on seats directly. Context is measurable for claude-harness seats only — codex/opencode seats
  get liveness/inactivity/approval watching.
  **Something must watch the watcher (P32).** The loop is detached, so its death produces no
  signal — a dead watcher and a healthy quiet run look identical. Every pass stamps
  `coordination/watch-heartbeat.json` and `workers` reports the watcher `ok` or `STALE`; leader
  checks that line at every drain, and restarts the loop on STALE. On a long AFK run, add the
  redundancy the single sentinel cannot give itself: a second watcher seat on a different cadence,
  or the deputy running one `watch.py` pass by hand at each of its own checkpoints.
- **Harness note.** codex and opencode seats follow this protocol in full — their loaders
  (`AGENTS.md` in the seat folder) point them here. They have no `/rename`; their identity lives
  in the pane/window title. Wakes reach them as terminal input like any pane.
