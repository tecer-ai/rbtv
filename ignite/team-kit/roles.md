# team-kit — role catalogue

**Read this when you HOLD one of the special roles below** — leader, consultant, deputy, scientist,
judge, verifier, closer — **or when your seat runs a codex or opencode harness** (the Harness note
closes the file). Read it at boot, right after you know which role you are. A plain worker seat does
not: its own entry states only what `protocol.md` already binds it to. Split out of `protocol.md`
(beside this file) so a seat stops loading another role's discipline; `protocol.md` remains the
protocol every seat follows and carries the evidence-pointer scheme (`P-n`, `S§n`, `PROP-n`) the
entries below cite.

## Roles

- **leader** — the goal's ON-DEMAND STAFF CHAIR, and every goal staffs one: a real `taskforce.csv`
  row minted at goal-materialize, holding NO workflow node and EXCLUDED from `checkin`/`checkout`.
  A sitting is spawned when the chair has unread mail, drains the whole queue, and ends — so a
  `checkout` here is the one act that would make the next mail wake nothing, and readiness reporting
  it `IDLE` means only that no mail is waiting. Four things arrive: the session-closer's staff mail
  on every terminal non-`done` ending, a live seat's mid-run ask (the PRIMARY path — a seat that
  asks before it fails costs the run nothing), a FAIL with no declared `on-fail-relaunch:` receiver
  (`route-fail`), and an executor-failure lifecycle alarm. Each item leaves with exactly ONE
  disposition — ROUTE to the seat that authored the instruction, ANSWER, or ESCALATE — and an
  unfinished row is NEVER relabelled `done`. FIX AND RELAUNCH (widening a seat's cage at runtime,
  via the now-deleted `widen-cage` verb) is GONE: ruling [T2-R6, C-6] fixes the cage envelope at
  plan time, so a narrow-cage blocker is a planning defect, escalated like any other, not a
  runtime repair this chair performs. Its full
  briefing is the component's own prompt (`meta/leader/prompts/leader.md`); the rest of this entry
  is the discipline that survives from the hand-launched arbiter it replaces.
  Support/arbiter, launched by the owner by hand; launches the roster at bootstrap
  (launch authority is shared — see the lifecycle note closing this entry); sole reader
  of worker briefings (lazily); reads the full log; the ONLY door to the owner (R-owner-channel).
  Drain rule (measured, adopted): per batch, ESCALATE-FIRST — relay owner-gated items before
  ruling own items, triaging with `read --type ask` (peek-only: it never consumes the rest of the
  inbox) and `pending` for what is still open. Order the queue by how much each item UNBLOCKS
  downstream, never by arrival. Then cut the cost of each decision you pass upward, per
  `R-cheap-ask`: owner-gated items go up as ONE batched ask with a recommended default per item and
  any-subset/silence-is-held semantics — measured to compound with the ordering, where ordering
  alone did not clear the queue. Leader never writes to the run's target surfaces.
  Seat-lifecycle authority is a CONVENTION now, not a coord.py gate: `coord.py` carries no per-verb
  role predicate anymore [T2-R10, D24, F-simplicity-7] — every verb (`launch`, `close`, `panel`,
  `kill-pane`, and the rest) is callable by any resolved identity. The two mechanical refusal points
  that survive are the cage envelope (fixed at plan time, never widened at runtime) and the
  send-time refusal of an owner-ask from a non-designated seat; "who is SUPPOSED to run `launch`"
  is a role expectation this document states, not something coord.py enforces. In practice `launch`
  is typically run by the leader or by the **ignite daemon** (a daemon-fired `start-workflow` opens
  the goal's entry seat), and a healthy seat's renewal is its OWN
  deterministic act — `checkout --renew --handoff "<note>"`, no approval, no closer
  (`r-self-renewal-is-the-seats-own-act`, `r-cos-self-renew-carveout-generalized`; the one
  exception is a `close: mechanical` seat, whose renewal stays the leader-side
  close-and-relaunch, `d-mechanical-no-self-renew`). What is BY CONVENTION the leader's — every
  `approve` and the failure-path close of ANOTHER seat — bottlenecks on one seat by agreement, not
  by a coord.py refusal: see **deputy**.
  Anchors resolve in the owning goal's `decisions.md` ledger (2026-07-29/30 rulings).
- **consultant** — the goal's OPTIONAL second staff chair, same lifecycle as the leader (on-demand,
  no node, no checkin/checkout): the same judgment surface MINUS the authorities — no close gate, no
  acceptance, no permission or relaunch verb, no owner contact. It answers GUIDANCE-shaped questions
  a seat cannot settle from its own scope and routes anything needing authority to the `leader`.
  **It is the FIRST STOP for every routed question** (owner ruling D2, 2026-08-19): a seat sends
  `--type ask` to the reserved token `auto` and the system resolves it — the `consultant` where one
  is staffed, else the `leader`; a seat whose own `seat.md` says `human-interactive:` reaches the
  owner directly instead. The seat never picks. (`--type stuck` routes the same way and always
  lands on the `leader`, which escalates to the owner what it cannot solve — see
  `communication.md` §4 for the whole table.)
  **Whether a goal staffs one is declared by CASTING it:** a chair is minted at materialize only
  where a casting sheet exists at `.rbtv/config/modules/<module>/<component>/bindings/<chair>.json`,
  so an absent `consultant.json` is the workspace stating it staffs none — mail and check-out routes
  aimed at it fall back to the `leader`. The `leader`'s sheet is required; its absence is a
  materialize warning, because then a goal has no chair for a routed FAIL or staff mail to reach.
- **deputy** (optional, rosters past ~8 seats or any AFK run) — a second seat briefed to take over
  SEAT LIFECYCLE only: launch, `approve`, deterministic-layer restarts, and the failure-path close (`close`,
  `close --renew`) for a seat that cannot check itself out — a healthy seat renews itself. It does
  NOT rule, does not talk to the owner (R-owner-channel is unchanged — leader remains the sole
  door), and does not write target surfaces. It exists because leader is renewable like any other
  seat: while leader is being closed and relaunched, approvals and failure-path closes just wait
  (launches and healthy self-renewals no longer do — see the leader entry's lifecycle note).
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
- **watcher seats — RETIRED (owner-ruled, `d-watcher-deterministic-chain`; name removed from
  coord.py 2026-08-13).** No run staffs a watcher seat. DETECTION is deterministic: team-monitor
  (CMP-20) is the sole raw sensor writing the goal’s `state.json`, and the daemon's own per-goal
  reconcile pass (`ignite/engine/reconcile.js`, D1/D15) acts on goal health. The former `watch.py`
  was dissolved into team-monitor and `goal-watcher-job` (task 7.35); `goal-watcher-job` was in
  turn dequeued 2026-08-20 and DELETED 2026-08-21, its half of the job now reconcile's.
- **Harness note.** codex and opencode seats follow this protocol in full — their loaders
  (`AGENTS.md` in the seat folder) point them here. They have no `/rename`; their identity lives
  in the pane/window title. Wakes reach them as terminal input like any pane.
