# 20260820-i-spawn-refresh-before-launch — Spawn refresh before launch

kind: issue
component: server
date: 2026-08-20
commit: ee64adde,a06723ec
deployed: yes
pin: server/spawn/probes/probe-spawn-refresh.js (ARM A2, scheduled)
seeded: true

## Observed
The `declare-and-refresh` seat of the redesign-plan (2026-08-20) measured that every already-materialized `seat.md` was a frozen render. `materialize-seats.py#render_descriptors` writes the sheet once; after that, `spawn.js`, `coord.py` checkout, and the admission gate all read the bytes on disk. RCA fact B1 (`redesign-plan/seed/rca-resolve-and-refresh-2026-08-20.md`) recorded the same: no daemon path re-rendered, no drift detector. Cost on the two live goals (meet-transcript-summarizer, stools): meet's chairs still printed pre-D30 "you have no checkout" prose, m4's 18 `plan-4-*` sheets predated `delta-anchors`, 118 sheets still carried EROFS-era prose, and D36's outputs projection would have reached nothing already on disk (ee64adde hunk comment). Loose-ends L36, L100, L133, L136 were the named instances.

A second measurement landed ~14 minutes after the first deploy. D37 and the design named `spawnSeat()` "the single launch route". On the live daemon, `server/index.js` routes to `spawnSeat` only when `sessionMode === 'headed'`; every reconcile/ticker launch on both production goals is HEADLESS and lands in `spawn()`. The journal at 17:03:32 and 17:08:34 shows `audio-component-smith` and `leader` launching with neither a refresh-success line nor a skip (a06723ec; D41). The hook fired on nothing.

The refresh functions at HEAD still match a06723ec (`git log -S refreshSeatDescriptor` on `spawn.js` is those two commits only). Later `spawn.js` edits (92e7156c sandbox binds, 7f6eaf3e D56/D74 PATH shims, 2b00b593 cli-write-roots) do not touch the hook. Header `deployed: yes`; inventory row D36/D41 records the batch at rbtv `ac1c08d8`, deployed 2026-08-21 18:14:37Z.

## Mechanism
`render_descriptors` is the only writer of `seat.md`. Spawn inlined the file into the first message as raw bytes. The `--refresh` verb already existed on `materialize-seats.py` as a manual CLI, but nothing called it at launch, and `--seat` on a composed instance name (`plan-4-*`) refused `seat-unknown` because the alias lane was gated to `--force-partial` (which `--refresh` itself refuses). Checkout re-reads `## Outputs` at checkout time, so a refresh under a live sitting would change the grade of work already in flight — that is why hand actors waited for a quiet window a self-dispatching goal never offers.

ee64adde then wired `refreshSeatDescriptor` only inside `spawnSeat()`, ahead of that function's three readers (`launchSpecForSeat`, `seatEffortRung`, `composeArgv`). Because production never enters `spawnSeat()`, the first deploy left the mechanism intact and unused.

## Attempts
No earlier commit of automatic refresh-before-launch — checked: `git log --before=2026-08-20T16:58:37 --grep=refresh -i` on `spawn.js` and `materialize-seats.py` returns only the manual `--refresh` CLI work (ed2fd7ee, 017ea4be, a58d4e21, 3f8175b3). What did not hold was the hand-actor loop: three actors each correctly refused to force a refresh against a live sitting (`rca-evidence-2026-08-20/glm3-investigation.md:45`; `design-opus-D.md:77` "the three-actors-failed ritual"). Pause, notice drift, refuse to force, nothing changes. L136 named the pattern: no quiet window on a self-dispatching goal.

## Fix
D37 (`redesign-plan/decisions.md`): run the proven `--refresh` for the seat about to launch; render to temp, swap on ok, never block a launch; `--seat` resolves composed names through their base row in the refresh lane; pause stays an owner ops lever; no drift reporter; L36/L100/L133/L136 close structurally.

ee64adde (2026-08-20 16:58:37Z) added `refreshSeatDescriptor` and `catalogRootForSeat`. Catalog root is the parent of the seat's own `component:` line — never a hardcoded module — so a `meta/planning` seat and an `office/meeting-summarizer` seat both refresh against the catalog that defines them. Goal-local seats with no `component:` skip. The call is `spawnSync` of `materialize-seats.py --package <goalDir> --seat <seat> --catalog-root <root> --refresh --root --json`, 60s timeout (measured cost 0.34 s). Any failure is one `spawn: descriptor refresh skipped` warn; the launch proceeds on the sheet already on disk. A `dryRun` refreshes nothing. Same commit opened the refresh-lane alias so `--seat plan-4-* --refresh` resolves at all.

a06723ec (17:12:22Z, same sitting) put the same call at the top of headless `spawn()`, before that door's three `seat.md` readers. It also silenced two not-applicable paths that had been warn lines: workdir is not a canonical seat folder, or the folder has no `seat.md` — this door also carries seatless dispatches, and a warn per those is noise. `parseSeatPath` now runs on `path.resolve(seatDir)`.

Why this shape: RCA row 9 (RC-4) voted 3–1–1 for (a) refresh-before-launch at the spawn door. "The refresh verb was already proven; what it lacked was a moment. THIS is the moment, and it is free" (ee64adde comment) — a seat being spawned is provably not sitting. Rejected (b) GLM-D's no-code pause→refresh→resume plus delete-and-remint of unstarted plan-4 rows: "the honest patch — it closes the instances and leaves the cause." Rejected (c) GLM-A's drift stamp/reporter plus pause. Rejected making `rbtv goal pause` the mechanism. The never-block trade-off is load-bearing: a descriptor one pass stale is a working seat; a launch that does not happen is a frozen goal.

D41 later accepted the two-deploy stretch rather than reverse it, and corrected the "single launch route" claim wherever it was repeated.

## Consequences
The ritual is gone. redesign-plan `loose-ends.md` marks L36/L100/L133/L136 closed 2026-08-20 by D37. Live proof at 17:13:02Z: meet `leader` `seat.md` md5 `374b8fe8e67e` → `ed62462b9cfb`, EROFS-era "you have no checkout" count 1 → 0, on an autonomously-dispatching goal — the condition that defeated the three earlier actors.

Sibling creation `engine/20260820-c-outputs-declared-at-gate` is D36 on the same ee64adde; D36's projection reaches live sheets only because this hook re-renders them. D41 accepted both disclosed stretches (two deploys; the D36 goal-relative reader). L148 recorded that the design, D37, and seat files still repeated "single launch route" after the code was fixed.

Later `spawn.js` commits do not revert the hook: 92e7156c (2026-08-21, D48/D49 sandbox binds), 7f6eaf3e (2026-08-22, D56/D74 undeclared-tool PATH shims), 2b00b593 (2026-08-22, cli-write-roots goals-tree rule). `20260823-i-lane-aware-launch-doors` (a554197b) rewired `--rerun` / `--declare-only` / `--reopen` to enqueue a caged headless sitting via the daemon gateway, so those doors inherit `spawn()`'s hook rather than composing a new spawn path. A door that does not land in `spawn()` or `spawnSeat()` would skip refresh with no probe to notice.

The silent-skip change means a real seat folder whose `seat.md` is missing produces no skip warn either — the check does not distinguish "not a seat" from "a seat with a missing file." Goal-local seats (stools' `audio-component-smith` has no `component:`) can never be healed by this hook.

## Verification
`probe-spawn-refresh.js` drives the real `materialize-seats.py --refresh` over the materializer's own catalog fixture (no stub). ARM A (ee64adde): `spawnSeat` after a post-materialize catalog edit; the sheet carries `REFRESHED-BY-PROBE-D37` before `launchSpecForSeat` (the first reader) throws. ARM A2 (a06723ec): `ctx.mgr.spawn(..., 'headless', ...)` and asserts `REFRESHED-VIA-HEADLESS-DOOR` — the arm that would have caught the dead first deploy. ARM A-control: `dryRun: true` leaves md5 unchanged. ARM B: broken catalog → sheet byte-identical, exactly one skip journal line, launch still proceeds to its own refusal (never `E_REFRESH_FAILED`). ARM C: a goal-local seat (no `component:`) is one named skip, never a guessed module. a06723ec: "PASS, 7 arms."

Companions on ee64adde: `coord.py` selftest PASS (0 failures, 4 new D36 arms); `materialize-seats.py --selftest` PASS (60 rows, 6 new arms including composed-name refresh and `repass+force-partial` still refused); red-by-mutation: refresh-lane predicate neutered → `--seat plan-4-plan-check-clarity --refresh` refuses `seat-unknown` again.

Deployed yes, two deploys the same sitting; D41 accepted the second. Inventory records the batch at `ac1c08d8`, 2026-08-21 18:14:37Z. Pin is ARM A2, scheduled.

## ATTENTION
- `refreshSeatDescriptor` may never block or throw. Every failure (no python, no `component:`, refusal, nonzero, timeout, unparseable JSON) is one journal line and the launch proceeds on the sheet already on disk. Making failure a gate reintroduces the freeze class this plan exists to end.
- `spawnSeat()` is not the single launch route. `server/index.js` routes to it only when `sessionMode === 'headed'`; every reconcile/ticker launch on the production goals is HEADLESS and lands in `spawn()`. ee64adde's own framing is the lie that shipped a hook that fired on nothing (journal 17:03:32 / 17:08:34). D41: "The stale 'single launch route' claim is now corrected wherever it is repeated." Any new launch door must call `refreshSeatDescriptor` ahead of its first `seat.md` read, or it silently regresses the same way. `20260823-i-lane-aware-launch-doors` inherits only because it enqueues onto the daemon's headless door.
- After a06723ec, a workdir that is not a canonical seat folder, or a seat folder with no `seat.md`, is silent rather than a skip warn. The headless door also carries seatless dispatches. The same silence now hides a real seat whose descriptor file is missing.
- A seat with no `component:` line (goal-local; stools' `audio-component-smith` is the live case) has no catalog root and is skipped by name. Catalog edits never reach those sheets through this hook.
