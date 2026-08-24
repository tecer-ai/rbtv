# 20260824-i-attest-exit-becomes-the-superv — attest-exit becomes the supervisor death stamp

kind: issue
component: team-kit
date: 2026-08-24
commit: c7913f62
deployed: no
pin: NONE
components: engine,server

## Observed
coord selftest ABORTED after 389 checks and `reap` could never find a debt; both closers still stamped endings themselves.

Measured on the `ignite/core-redesign` worktree, 2026-08-24. `python3 ignite/team-kit/coord.py selftest` ABORTED after 389 checks with `NameError: name 'awaiting_path' is not defined at coord_selftest.py:4113`, taking `probe-coord-selftest-notmux.py` and `probe-coord-selftest-tmuxpane.py` red with it and leaving every check after 389 UNKNOWN rather than passing — 255 further checks, as the post-fix run showed. In the same tree `coordinate reap` could never report anything: `load_awaiting` answers `{}` by construction, so `awaiting_debts` was always empty and the sweep printed "no awaiting-close debt" on a run that was leaking. And both closers still spoke the retired vocabulary: `attest_exit_seat` and `close_session_seat` stamped the ending store themselves, `cli_main.py`'s `attest-exit` help still taught readers it "records disposition `exited`", and `live-sessions.js` built an `exited:<code>` reason string that travelled into the crash evidence pointer.

## Mechanism
`awaiting-close.json` went away with its writer `awaiting_path`, leaving stub readers, dead callers and two independent stampers.

`awaiting-close.json` was deleted as the second ending writer (spec-state-store §4.1 Row A), and `load_awaiting`/`clear_awaiting` were left as stubs answering `{}`/`False` — but the writer `awaiting_path` was removed outright while three groups of selftest rows and `checkout.py#confirm_reap` still called it. Those rows only reached it once `load_awaiting` returned a real entry, so the NameError sat latent until a fixture seeded one, and then aborted the whole suite instead of failing the rows that named the gap. The reap side had the deeper version of the same hole: the debt file WAS the reaper's subject, so deleting it left a G-134 pane-leak guard that can never fire, which guards nothing.

Separately, the two closers were independent stampers by construction: each held its own `ending_store.stamp_system(..., "failed", reason_class="crash")` call, so "what does a dead process mean" was answered in two places that could drift, and the door list in spec-supervisor §3 says this door must BECOME the supervisor death stamp rather than sit beside it.

## Attempts
First attempt held. Checked before writing: `20260819-c-record-ledger-custody` (which deleted the `kit-for-seat` transcription closer and left kit originating `exited`, and whose own ATTENTION names the remaining dead-process-but-row-not-closed lag), `20260820-i-staff-wake-mint-mismatch` (the same defect class from the other side), `20260820-c-verified-done-resolver` and `20260820-c-relaunch-instrument-rerun` (the `exited` row's relaunch doors, deliberately NOT touched here — they are the doors seat's). Earlier same-branch work had already moved both closers from `exited` to a direct `failed`/`crash` store write (`acd780e3` era); that narrowed the vocabulary but kept two stampers, which is what this change finishes.

## Fix
Both closers become CALLERS. `attest_exit_seat` and `close_session_seat` share one new `supervisor_stamp(args, pkg, seat, …)` helper that hands `supervisor_door.death_stamp` the facts the witness holds and renders the supervisor's answer as its step string; neither calls `ending_store` at all any more (`grep -c 'ending_store\.' attest.py` is 0). `close_session_seat` now RETURNS the ending the supervisor decided instead of a constant it chose — the old code returned the literal `"exited"` and then the literal `"failed"`, both of which misreport the evidence table's first row, a seat that checked out `done` and merely had to be reaped. That row now also suppresses the staff-mail arm, because mailing a chair "its work is NOT done" about a completed sitting is exactly the misgrading this arm's own header bars.

One shared helper rather than two call sites was deliberate: a second spelling of "hand the supervisor the evidence" is how two doors start disagreeing again. `supervisor_stamp` NEVER RAISES — a closer that dies on an unreachable stamper leaves the world worse than the silent arm it replaced — so every failure is reported as a step and the caller's remaining steps still run.

For the reap, the successor fact is DERIVED and needs no second store: a supervisor registry row still present while its sitting already carries an ending is, by registry write moment (iii), a reap that did not complete. `cmd_reap` gained `supervisor_reap_arm`, which observes by default and, under `--go`, calls `confirmAndReap`. Rejected: rebuilding a pane-keyed debt record. [T4-R8] deletes the pane as a liveness surface, so a reaper keyed on pane ids would rebuild the predicate spec-supervisor §6 retires; what is reaped here is the PROCESS.

The selftest rows that drove the deleted debt file were replaced, not re-pointed — re-pointing them at a hand-built dict would manufacture a subject the design removed. Four new rows assert the live subject on the real verb, and the two-pass confirmation ledger rows are deleted with a note saying why: the supervisor's confirm step is a DIRECT observation of the process, which is the evidence the two-pass rule was a proxy for.

## Consequences
`python3 coord.py selftest` no longer aborts at 389; it reaches 644 checks and then aborts on an unrelated pre-existing defect (`_rg_r["a"]["renewal"]` is None at `coord_selftest.py:8051`), with 53 failures now VISIBLE that were previously UNKNOWN. Those 53 are the `--rerun` / `--declare-only` / renew-gate rows that still speak `exited` — impl-supervisor-doors' scope, deliberately untouched here, and `cli_main.py`'s `--rerun` help text is left with them. `probe-lifecycle-idents.py` fails `2.6c` for the same pre-existing reason from the other side: `clear_awaiting` is a stub, so the renewal sequence never records `awaiting-and-closing-cleared`. `checkout.py`'s `load_awaiting` / `clear_awaiting` / `awaiting_debts` / `confirm_reap` are now dead code with no caller reaching their bodies; they were left in place because that file was held by a concurrent seat.

## Verification
`python3 -B ignite/team-kit/coord.py selftest` — the four new `G-134 successor` rows report `ok`, and the abort at check 389 is gone. `node --check` on each changed `.js` and `py_compile` on each changed `.py`, all silent. `node deploy/probe-suite.js --dir server/spawn/probes --dir supervisor` — 33/33 GREEN. `node ignite/supervisor/death-stamp.selftest.js` — `ALL PASS`. Landed on the `ignite/core-redesign` worktree branch; NOT deployed to the live tree.

## ATTENTION
- `supervisor_stamp` swallows every exception by design. A goal whose ending store or node runtime is unreachable will log "supervisor death stamp: NOT stamped" as one step among six and otherwise look like a healthy close — read that step, do not read the closer's exit code.
- `checkout.py`'s `load_awaiting`, `clear_awaiting`, `awaiting_debts` and `confirm_reap` are dead but still present, and `confirm_reap` still references the deleted `awaiting_path`. Anything that makes `load_awaiting` return a non-empty dict again re-arms that NameError instantly.
- The reap arm reaps PROCESSES, not panes. The pane-leak class G-134 was originally about, and the `relays:`-declared owner door `reap_blockers` exempts, have no successor guard on this path.
- `SUPERVISOR_REGISTRY` is what keeps a probe or selftest off the live registry file. A test that forgets it writes the daemon's own liveness surface, and the default is silent about it.
- supervisor_stamp swallows every exception — read its step, not the exit code
