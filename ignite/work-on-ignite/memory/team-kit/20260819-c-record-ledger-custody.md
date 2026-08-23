# 20260819-c-record-ledger-custody — record-ledger-custody

kind: change
component: team-kit
date: 2026-08-19
commit: e56d8704,85f0a30a
deployed: yes
pin: NONE
seeded: true

## Motivation
CW9 (2026-08-07) ran a real `checkout` inside a real composed cage: creating `sessions.csv.tmp` in the run dir was refused `errno 30 EROFS`. The anti-spoofing carve had made the durable ledger unwritable from inside the cage on purpose. W1 (`dc2b3f14`, 2026-08-13) answered with a proxy: the seat declared on a writable side file (`coordination/disposition-{seat}.json` via `write_seat_disposition`) and the daemon-lane closer transcribed that declaration onto `sessions.csv` under writer `kit-for-seat`.

The two-writer design failed in production. On 2026-08-18 `meet-transcript-summarizer`'s leader last-ended row was `98b6bcf1` / `exited` / `2026-08-17 23:05` while the seat's own JSON said `done` / `2026-08-18 01:22`. `session_disposition` returned the stale `exited`; `terminal_disposition` reported SKEW; `ready-seats` exited non-zero; the goal stopped seeding for ~4 hours (1,704 refusals, no owner-facing signal). Same-day patches `4a732552` (let a demonstrably-newer JSON override a stale ended row) and `60058a85` (name the fallback chain in the EROFS warning so seats would stop proposing a RW bind) treated the carve as permanent and kept reconciling two surfaces.

Same day as this change, `ac4726a6` (2026-08-19 20:45Z, ~90 minutes earlier) replaced the cage with the D3 fence: one RW bind of the goal folder; `assertGroundTruthUnwritable` and the `sessions.csv` ro-carves deleted ("record forgery is a non-goal"). A seat could write its own ledger again. The proxy's reason for existing was gone; the two-writer lag was still live.

## Design
`85f0a30a` (2026-08-19 22:09:45Z) deletes the proxy instead of patching reconciliation again. `cmd_checkout` now calls `session_close` unwrapped: a failed `sessions.csv` write `refuse`s the checkout — "a failed ledger write is not a done (D5). No swallow, no kit-for-seat proxy." `checkout_disposition` is computed once after the verify gate (`renew` / `incomplete` / `done`) and both remaining writers (`session_close` then `set_awaiting`) read that one name; the JSON record was the third consumer and is gone.

`session_disposition` shrinks from ~90 lines of two-surface freshness comparison (7.475/7.481) to the last-ended `sessions.csv` row. Leftover `coordination/disposition-{seat}.json` files are inert. `seat_disposition_path` and `write_seat_disposition` are deleted, along with the ~100-line CW9/CW10 comment that documented why they existed.

`attest_exit_seat` / `close_session_seat` no longer transcribe a seat declaration under `kit-for-seat`. They originate `exited` under writer `kit` unconditionally: "THE VALUE IS ORIGINATED, NEVER TRANSCRIBED. Checkout writes `sessions.csv` itself. This closer runs only when the process died without checking out (or died mid-checkout before the ledger write)." A declaration sitting on `awaiting-close.json` with an open row is treated as an unverified mid-checkout death.

`RECORD_DISPOSITION_WRITER` narrows: `done`/`renew`/`incomplete` no longer admit `kit-for-seat`. The constant `DISPOSITION_WRITER_KIT_FOR_SEAT` stays as a historical parse token for pre-D3 rows. `e56d8704` (10 seconds later) writes the rule into `ignite/CLAUDE.md` under "Ledger custody (D3, 2026-08-19)".

Rejected: keep the freshness-comparison override (`4a732552`'s approach). The D3 fence made the constraint removable; removing one writer is cheaper than teaching every reader to pick between two. The D3/D5 labels in these comments are coord.py-local same-day design points (D3 = the fence that dropped the carve; D5 = a failed or unverified done is not a done), not numbered rulings in `redesign-plan/decisions.md` or `engine-goal/decisions.md`.

## How it works
A seat ends with `coordinate checkout` (optionally `--renew` / `--incomplete "<why>"`). After the outputs verify gate, `cmd_checkout` computes `checkout_disposition` once, then `session_close(..., writer=DISPOSITION_WRITER_SEAT)` stamps `ended` plus disposition on the seat's last open `sessions.csv` row. Exception → `refuse("state", "sessions.csv write FAILED … Checkout REFUSED")` and nothing after that line runs. `set_awaiting` then records the same name. `exited` is refused on this path by construction — a seat cannot witness its own harness death.

Readers (`session_disposition`, `ready-seats`, the then-live watcher) take the last ended `sessions.csv` row. They do not open `disposition-*.json`.

The daemon-lane closer (`attest-exit` → `close_session_seat`) is the crash path only. It ignores any awaiting-close declaration and stamps `exited`/`kit` via `close_session_row_by_id` (keyed on session-id, never seat name — concurrent sittings). `daemon_close_blockers` refuses to re-stamp a row checkout already closed.

Old rows may still say `disposition-writer=kit-for-seat`. Parse it; nothing writes it.

## Consequences
Deleted the interim JSON surface and the transcription closer. Same-commit fixture rewrites: `probe-checkout-disposition.py` `disposition_of()` now reads the last-ended `sessions.csv` row and asserts `disposition-writer == "seat"` plus a filled `ended` cell; A5 asserts `RECORD_DISPOSITION_WRITER["incomplete"] == frozenset({"seat"})`. `goal-watcher-job.py` CAGED-SHADOW selftest stamps `sessions.csv` directly instead of calling the deleted `write_seat_disposition` — that job was itself deleted two days later (`20260821-c-delete-goal-watcher-job`).

Does not close the dead-process-but-row-not-closed window: a process that dies before `session_close` still waits for the kit crash-stamp. Next day `20260820-i-staff-wake-mint-mismatch` names this entry as the same defect class from the other side — `sessions_last_ended` had not yet been re-stamped when a staff-wake bound to the previous sitting. No revert of `e56d8704`/`85f0a30a`. Next coord.py touch `eda7e4c7` (2026-08-20, D29 summoned-chair checkout exemption) is unrelated. D32 later split D5's unverifiable-done out of `incomplete` into `unverified` (`20260820-c-verified-done-resolver`, then `20260822-c-unverified-into-dispositions`); that is a later widening of `checkout_disposition`, not a regression of this custody split.

## Verification
`85f0a30a` rewrites the existing `probe-checkout-disposition.py` in place (A1/A2 writer=`seat` and `ended` filled; A5 kit-for-seat retired) and the `_selftest_checks` arms that used to prove the JSON fallback and the meet-transcript freshness override (7.481 now asserts leftover JSON is inert and a stale ended `exited` is what `session_disposition` returns). W1/C2 flips: the daemon-lane closer originates `exited`/`kit` even when a declaration is present. `deployed: yes` is the entry field; no separate deploy log for this pair was located. `pin: NONE` because the probe was updated, not added.

## ATTENTION
- The D3 fence (`ac4726a6`, same day) is a silent runtime dependency: this custody model assumes `sessions.csv` is writable inside the fence. Re-carving it read-only would make `cmd_checkout`'s new `refuse` fire on every caged checkout — there is no fallback surface left.
- `DISPOSITION_WRITER_KIT_FOR_SEAT` / the string `kit-for-seat` is still a historical parse token for pre-2026-08-19 rows. A reader or migration that drops the spelling will misread old packages; a writer that starts emitting it again reopens the two-surface lag this change deleted.
- Kit still originates `exited` for a process that dies before checkout completes. That remaining crash-stamp lag is the same dead-process-but-row-not-closed class `20260820-i-staff-wake-mint-mismatch` hit the next day — this change narrows the checkout path only.
- Leftover `coordination/disposition-{seat}.json` files may still exist on old run packages and are inert. Teaching `session_disposition` to consult them again recreates the 2026-08-18 seeding stall.
