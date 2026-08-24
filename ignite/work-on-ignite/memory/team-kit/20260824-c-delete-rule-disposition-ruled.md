# 20260824-c-delete-rule-disposition-ruled — delete rule-disposition + RULED_FLIP_FROM states

kind: change
component: team-kit
date: 2026-08-24
commit: 7b978663
deployed: no
pin: NONE

## Motivation
D19 (redesign ruling [T2-R12, T1-R9]): the grant-store authority model is gone — owner authority
is now an answer to a live ask, not a leader-ruled disposition flip recorded through a dedicated
verb. `rule-disposition` (the leader's act of writing `done`/CLEAR/`--hold` onto an already-ENDED
`sessions.csv` row) and its two from-state constants (`RULED_FLIP_FROM`, `RULED_FLIP_FROM_STATES`)
implemented exactly that superseded model and had to go with it.

## Design
Full deletion, not a stub or a flag-gated bypass: `cmd_rule_disposition`, its argparse
registration, its docstring verb-table row segment, the `session_rule_disposition` helper (its
ONLY caller), and the `RULED_FLIP_FROM`/`RULED_FLIP_FROM_STATES` constants. `rule_awaiting_disposition`
(the awaiting-close.json re-pointer) is deleted too, on the same reasoning: `cmd_rule_disposition`
was its only caller, so it became dead code the moment the verb went. All four selftest sections
that exercised `cmd_rule_disposition` end to end (`7.155`, `RD-EC`, `D33(b)`, `D12` — the whole
`_r155_ns`/`_r155_pkg` fixture family) and the D42-part-3 `--hold` selftest block are deleted
whole; nothing survives that asserted only against the deleted verb.

Explicitly NOT touched (out of scope, named by the task): `validate_disposition`, `session_close`,
`attest-exit`, `checkout`, `RECORD_DISPOSITION_WRITER`, the `--reopen`/`--rerun` mechanisms
themselves, and the `hold-anchor` column/store/other-readers (SESSIONS_COLS schema comment,
`cmd_ready_seats`'s hold display, `attest-exit`'s closing hint). Where those surviving functions'
own text/comments *named* the deleted verb or constant as a live instrument, the ones outside the
explicit do-not list were re-worded to state the verb is gone with no replacement wired yet
(`--rerun`'s and `--reopen`'s from-state refusal-door messages, `cmd_launch`'s deferred-admission
detail, `staff_mail_body`, `ready_seat_rows`' internal routing comments, the `--reopen` help
text) rather than left pointing at dead CLI syntax.

## How it works
This entry records a deletion, so there is no new mechanism to describe. The surviving
`--rerun`/`--reopen` doors on `cmd_launch` still exist and now inline the literal `"exited"` string
where they used to read the `RULED_FLIP_FROM` constant, which is the one code shape that changed
on a still-live surface.

## Consequences
- No leader instrument now exists in `coord.py` to flip an `exited`/empty/`unverified`/`incomplete`
  row to `done`, to CLEAR it, or to `--hold` it. Every code path that used to point a leader at
  `rule-disposition` now says so was deleted and names no replacement — this is a real capability
  gap, not cosmetic, until whatever T1-R9's "owner auth = answer to a live ask" replacement is
  lands and is wired into these same call sites.
- `HOLD_ANCHOR_COL` ("hold-anchor") stays in `SESSIONS_COLS` with no writer left anywhere in this
  file — `cmd_ready_seats` (line ~15403) and `attest-exit`'s hint (line ~15235) still reference the
  deleted verb by name in their own text; left untouched per the task's explicit hold-anchor-store
  boundary and disclosed as a loose end.
- Cross-component staleness (NOT fixed here, out of `team-kit` scope): `ignite/engine/reconcile.js`
  (builds a leader mail payload literally containing `rule-disposition <seat> ... --go` lines and
  a comment about `--hold`), `ignite/engine/reconcile.selftest.js` (asserts that payload contains
  the string `"rule-disposition"`), `ignite/bridges/chat/README.md`,
  `ignite/capabilities/attached-execution/attached-execution.md`,
  `ignite/server/spawn/live-sessions.js`, and `meta/leader/prompts/{consultant,leader}.md` +
  `meta/leader/tasks/serve-staff-mail.md` (the leader's own standing operating instructions name
  `rule-disposition <seat> done --anchor ... --go` as "the ONE sanctioned act"). None of these are
  under `ignite/team-kit/`; `ignite/team-kit/protocol.md`, `roles.md`, `communication.md`, and
  `team-kit.md` were checked and carry no reference to the deleted verb, so no team-kit doc needed
  a fix.

## Verification
`python3 -B -c "import py_compile; py_compile.compile('ignite/team-kit/coord.py', doraise=True)"`
clean. `python3 -B ignite/team-kit/coord.py selftest` — 1105 checks, `selftest: PASS (0 failure(s))`,
run twice for consistency. Deployed: no (worktree only, not yet on the live ignite tree).

## ATTENTION
1. `rule_awaiting_disposition` and the whole `cmd_rule_disposition` docstring/comment block that
   preceded `session_rule_disposition` (the "7.155: THE RULED FLIP" header) were deleted even
   though the task's explicit list did not name them by symbol — they were orphaned dead code the
   moment their one caller went, so leaving them would have violated no-dead-code hygiene.
2. `HOLD_ANCHOR_COL`'s column and its two OTHER readers (`cmd_ready_seats`'s report line,
   `attest-exit`'s closing hint) still name `rule-disposition` as the way to release/act on a hold
   — deliberately left alone (out of scope per the task's hold-anchor-store boundary) but they are
   now stale: nothing in this file can write a hold anymore, so a hold anchor already on a row from
   before this deletion has no in-file release path left.
3. `--rerun`'s and `--reopen`'s refusal-door text for `unverified` rows used to hand the leader a
   working `rule-disposition ... done --go` command; it now says the ruling instrument was deleted
   with no replacement wired. Anyone landing the T1-R9 replacement (owner-auth-as-live-ask) needs
   to grep this file for `[T2-R12, T1-R9]` to find every spot that needs the new instrument's name
   wired back in — there are 6: two in `cmd_launch`'s refusal-door dicts, one in its
   deferred-admission detail, one in `staff_mail_body`, one in `ready_seat_rows`'s routing comment,
   and one in `--reopen`'s own `--help` text.
4. The engine (`reconcile.js`/`reconcile.selftest.js`) and the leader's own prompt docs
   (`meta/leader/prompts/leader.md` etc.) still actively construct/assert/instruct with the exact
   dead CLI syntax `rule-disposition <seat> done --anchor ... --go` — these are LIVE operating
   instructions handed to a leader seat, not just stale prose, and they were left untouched because
   they sit outside `ignite/team-kit/` (different components' ownership), not because they're low
   priority.
5. The `--rerun` from-state check (`if _rr_disp != RULED_FLIP_FROM ...`) and its two f-string
   references now inline the literal `"exited"` rather than a named constant — if another verb
   ever needs that same value again, it should probably get its own small constant rather than a
   second inlined literal, but minting one wasn't this task's job.
