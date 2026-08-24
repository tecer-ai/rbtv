# 20260824-c-kit-endings-via-store-client — kit endings via store client

kind: change
component: team-kit
date: 2026-08-24
commit: 795459fa
deployed: no
pin: team-kit/probes/probe-checkout-disposition.py
components: capabilities

## Motivation
Spec-state-store §4.1 required the Python kit disposition path to stop dual-writing `sessions.csv` plus a second debt file, and to stamp the ONE ending store that impl-state-store-core already hosts. The old enum (`done`/`renew`/`revive`/`exited`/`unverified`) and the leader flip verb had no successor.

## Design
A thin `ending_store.py` client calls `state-store/cli.js` (`stampSeatDeclare` / `stampSystem` / `getCurrentEnding` / `isLaunchable` / `seatWaitingOnOwner`). Checkout is the seat-declare path: `done` (mechanical output check via the store), `renew` → `incomplete`+`armed=1`+`diagnostic=context full`, `--incomplete` → armed incomplete, undeclarable/missing outputs → `failed:outputs-missing`. The closer stamps `failed:crash` and will not overwrite an existing current row (`replace=False`). Rejected: rebuilding the store in Python, and keeping a compatibility verdict enum as stored work-state.

## How it works
`coord.py` imports `ending_store`. `cmd_checkout` computes one kind then `stamp_checkout_ending`. `close_session_seat` / `attest_exit_seat` call `stamp_system(..., reason_class=crash)`. `terminal_disposition` reads the current ending-store row only. `materialize-seats` staff-chair mint skips when a current `seat_endings` row exists. Relative declared outputs are resolved under `{pkg}/workers/{seat}` before `checkDoneOutputs`, because the JS check is cwd-relative.

## Consequences
`RECORD_DISPOSITION_WRITER`, `set_awaiting`, and the hold-anchor column writer are gone. `sessions.csv` still closes the open row (`ended`) but is not a work-state writer. `coord_selftest.py` still contains many rows written against the old dual-file model; those will fail until retargeted. `ready_seat_rows` still emits a presentation `verdict` field for existing JSON consumers while also adding `launchable` / `waiting_on_owner`.

## Verification
`python3 -B ignite/team-kit/probes/probe-checkout-disposition.py` printed 11/11 green (done on present output, failed/outputs-missing on a missing declared file, incomplete+armed=1 on `--incomplete`, mutant without the outputs gate still stamps done). Every edited `.py` was compiled with `py_compile.compile(..., doraise=True)` and exited 0. Not deployed: worktree branch `ignite/core-redesign` only; no daemon restart.

## ATTENTION
- Never write a work ending to `sessions.csv` or revive a second debt file — the store is write-once per sitting; the closer must use `replace=False` so a completed checkout is not overwritten as crash.
- Pass absolute output paths into `stampSeatDeclare`. The kit's own output check is seat-cwd-relative; `checkDoneOutputs` is process-cwd-relative. Relative `./file.md` stamps `failed:outputs-missing` even when the file exists.
- `coord_selftest.py` still names the retired writer in AST scans and string fixtures. A green selftest is not automatic after this change; retarget those rows before treating `probe-coord-selftest-notmux` as a gate.
- absolutize outputs before stamp; closer replace=False
