# 20260828-i-pane-census-deferred-every-dae — Pane census deferred every daemon-lane seat forever

kind: issue
component: supervisor
date: 2026-08-28
commit: fa6bd7a0
deployed: no
pin: ignite/coord/coord_selftest.py
components: coord

## Observed
On 2026-08-28 05:16Z the acceptance wave induced a seat death on the DAEMON-LANE goal
`scratch-death-recovery-1-exec`: `cadence-writer` (descriptor `agent_type: staff`) was `kill -9`ed
and stamped `failed`/`crash` honestly 10 s later. The leader ruled a re-run and ran
`supervise launch --only cadence-writer --rerun <anchor>`. The act printed
`cadence-writer: ADMITTED by --rerun` and then, in the same output,
`capacity: CAP UNENFORCEABLE — the census could not be produced: state.json is ABSENT at
<goal>/state.json` followed by
`cadence-writer: DEFERRED (capacity) — cap.agent_panes headroom is UNKNOWN for this act`,
exited 0, dispatched nothing, and named a pickup lane that bars `--force` and `--force-memory` by
name. The daemon then journalled `lane watch: daemon-assigned goal seeded … enqueued:[]` every 10 s
with no session row ever opening, and the goal stayed stranded at 3/20 items. The leader filed
`G-leader-0828-0524`. Reproducible offline at 26f4510e; the deployed worktree carried the same code.

## Mechanism
`supervisor/launch.py`'s capacity term (7.278/7.363/7.406) reads `<goal>/state.json` — the TMUX
ROOM's census — computes `_cap_blind = _cap_c is None or _cap_stale is True`, and on that reading
DEFERS every seat whose declared `agent_type` is in `budget.json`'s `counting.counts_toward_cap`.
Neither that predicate nor 7.406's cold-start bound asks which LANE the goal runs on, although
`_lane` was already resolved a few hundred lines above through `goal_execution_lane`. A goal whose
`execution-lane` reads `daemon` has no tmux room, so it has no panes for `cap.agent_panes` to count
and no writer that could ever produce the census — the team-monitor sensor was deleted [T4-R8,
del-observers] and `launch.py`'s own comment says so. Once such a goal has run any seat it also has
a `sessions.csv`, so `_cap_virgin` is False and 7.406's empty-room admission cannot fire either.
The result is a permanent, unliftable deferral of every counted seat on the daemon lane: the fail
direction of a term whose subject does not exist. The wrong behaviour is born at the first consumer
that REJECTS the census's absence — the `_cap_blind` branch — not at the absent file, because the
contract permits the absence (nothing writes it and nothing can).

## Attempts
First attempt held — checked: 7.278 (the capacity term's origin, `capacity-admission-spec.md`),
7.363/G-m4-demo-clause1-driver-0803-2335 (which split IMPERFECT from ABSENT and made ABSENT defer),
7.406/G-leader-0805-2036 (which added the cold-start admission for a virgin room and is the closest
prior fix — it addressed the same absent census but bounded itself to rooms nothing had ever
observed, so a daemon-lane goal that had already run seats fell straight through it),
`team-kit/20260824-c-delete-team-monitor-cli-and-te` (the deletion that made every room read the
census as permanently absent, whose own "How it works" predicted the cold-start branch would carry
the load — true for the tmux lane, false for a lane with no room at all).

## Fix
The capacity term is SCOPED to the lane it measures. A first arm on the existing decision chain
reads `_lane` and, when it is `daemon`, prints `CAPACITY_LANE_INAPPLICABLE_LINE` and admits
unchanged: the pane cap is skipped, never reported as an unknown headroom and never deferred. The
line names why (this lane opens no pane; every admitted seat is handed to the daemon's own spawn
door as an `enqueue-job`) and names the gates that DO bind the lane — the memory floor read live at
the launch gate from the package's own `budget.json` (`coord.launch_gates`, both lanes) and the
daemon door's IDEMPOTENT DEDUP, which refuses a second sitting under one seat.

Chosen over the leader's stated alternative (restore a census writer for roomless goals), which
would build a sensor to count panes that do not exist, and over an override flag, which the
deferral text rightly bars — `cap.agent_panes` is an owner ruling (r-pane-cap-10) and a leader may
not lift it. Scoping is neither: the gate is not weakened, it is applied where its subject exists.
The lane is READ, never derived, through the value the command already resolved via the goals-tree
speller, keeping DEC-1's two-speller bound intact. The census read above the chain is left
UNCONSULTED rather than skipped at the read, so the read stays one home and the decision stays one
home.

## Consequences
Nothing changes on the tmux lane: every reading, branch and printed string there is untouched, and
an absent census still defers in the same words. The daemon lane loses no protection it had —
`cap.agent_panes` never bound it in any meaningful way (it only ever refused it) — and keeps the
memory floor and the door's dedup. The new line deliberately carries NEITHER wire marker
(`CAP UNENFORCEABLE`, `CAP NOT CONSULTED`): rows assert the absence of both to prove which branch an
act took. It names the door's dedup and NOT its admission brake, because that brake was deleted
whole [C-4 kill map, 01196394] — `server/20260825-c-delete-the-enqueue-door-admiss` ATTENTION 2
names `launch.py`'s surviving brake text as a dead reference, and `launch_daemon_lane`'s
`if not result.get("jobId")` branch still carries it (surfaced, not fixed here — the correct
replacement text needs to establish what a missing `jobId` means now that nothing can brake).

## Verification
`python3 ignite/coord/coord.py selftest` — 1016 checks ok / PASS (0 failures) at 26f4510e, 1022 ok /
PASS (0 failures) at fa6bd7a0; the six new rows are `E22-CAP` (precondition), `E22-CAP-1` (daemon
lane + no `state.json`: ADMITTED, the skip line present, `DEFERRED (capacity)`/`CAP UNENFORCEABLE`/
`CAP NOT CONSULTED`/`capacity: COLD-START` all asserted ABSENT, and
`enqueue-job job_id=seat-pkg-gamma session_mode=headless` composed for the daemon's door),
`E22-CAP-2` (console lane, same absent census: still DEFERRED in the unchanged words — the row that
proves the fix is not vacuous, since gamma is genuinely under the cap there), `E22-CAP-3` (daemon
lane + a present STALE `state.json`: unaffected, the file ignored), plus a byte-identity row on
`sessions.csv` and a fixture postcondition. RED MUTATION on a scratch copy of HEAD with the lane
arm reverted: `selftest: FAIL (2 failure(s))` — exactly `E22-CAP-1` and `E22-CAP-3`, with
`E22-CAP-2` and both fixture rows still green. `node
ignite/supervisor/probes/probe-daemon-lane-watch.js` exits 1 on its one documented pre-existing red
(`L9 M9`, the prompt-key mutation arm) and no other, unchanged by this Python-only edit. NOT
deployed: the change is in the working repo, which is what `~/.rbtv-bin/supervise` symlinks to; the
daemon boots from `/home/henri/.local/state/rbtv-deploy` and its `execFileSync` calls into
`supervise.py` resolve there, so nothing daemon-side picks this up until a deploy and no unit
restarts.

## ATTENTION
1. Every launch-path gate in this file must ask WHICH LANE before it requires a tmux artifact.
   `state.json`, a pane id, `$TMUX_PANE` and a room lease are all console-lane facts; a term that
   requires one on the daemon lane fails closed forever, because no writer exists and none is
   coming. This defect is the second of its shape after the daemon-lane goal's missing room opener
   (`supervisor/20260827-i-daemon-lane-goal-s-first-room`).
2. A green E22 arm did NOT mean the capacity term worked on the daemon lane. The `pkg` fixture
   declared FLOORS ONLY — no `counting.counts_toward_cap`, no `cap.agent_panes` — so every seat in
   it was UNCOUNTED and the term could not defer anybody there whatever the census said. An arm
   over a package with no counting block measures nothing about the cap; add both the counting
   block and a counted `agent_type` or the row passes with the mechanism absent.
3. Do not put a policy number or either wire marker in a capacity string. `CAP UNENFORCEABLE` and
   `CAP NOT CONSULTED` are asserted ABSENT by rows proving which branch an act took, so a new line
   that merely narrates the census using their words reddens correct code (measured once already at
   7.555); and the cap is named by FIELD, never by value.
4. `enq.braked` is dead and `launch_daemon_lane` still names it. The `if not result.get("jobId")`
   branch attributes a missing queue row to "its admission brake (D52/D66)", a mechanism deleted at
   01196394 — anything written near that branch must not inherit the claim.
5. Run `python3 coord.py selftest` after any edit near the capacity/census messages, never just
   `compile()` — it is the only thing that catches a stale literal-string assertion or a digit
   landing in a no-digit assertion.
- a launch gate that requires a tmux artifact fails closed forever on the daemon lane
