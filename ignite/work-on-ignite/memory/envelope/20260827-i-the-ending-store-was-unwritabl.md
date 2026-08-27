# 20260827-i-the-ending-store-was-unwritabl — The ending store was unwritable from every caged seat

kind: issue
component: envelope
date: 2026-08-27
commit: 297765d8
deployed: no
pin: ignite/envelope/envelope-compiler.selftest.js
components: coord,supervisor

## Observed
Every caged seat's own check-out lost its ending, and its check-in lost its session row.
On `scratch-tool-reach-note` (2026-08-27, deployed HEAD 5c641b04) `plan-verifier` ran
`coordinate checkout --incomplete --route leader` at 19:32Z and got
`refused [coord state]: ending-store write FAILED — attempt to write a readonly database.
Checkout REFUSED.` — after the session log already carried `sessions.csv:
8ec728ab-… ended` and `checked out: plan-verifier` (both verbatim in
`~/.local/state/rbtv-ignite/logs/8ec728ab-….log`). The store read `null` for that seat
while the four seats the leader accepted read `done`. Earlier, at 19:25Z, its check-in
printed `sessions.csv native-session-id NOT backfilled — OSError: [Errno 16] Device or
resource busy` and `sessions.csv checkin stamp NOT written — [Errno 16]`; the row's
`checkin` cell is empty to this day. The goal's `issues.md` carries all three as
`#G-plan-verifier-0827-1931`, `#-1934` and `#-1935`.

## Mechanism
The live cage is the ENVELOPE's, and its bind list had no rw opening for the store at
all: `coord/ending_store.py:18-25` resolves the ONE store to
`<ws>/.rbtv/runtime/ignite/heart.db`, `envelope-template.yaml` family 5 binds
`{workspace}` ro, and no narrower family named that path. The daemon's own bwrap argv
(journal 19:25:27Z) confirms it: `--ro-bind /home/henri/ht-wkdir/second-brain …` and no
`--bind` under `.rbtv/runtime`. Second, `checkout.py` stamped the ending AFTER
`session_close` and `update_row`, so the refusal left both closing surfaces written and
the store empty — and `attest.py#close_session_seat` / `#attest_exit_seat` walk OPEN
session rows, so nothing stamped it afterwards: no staff mail, no leader wake, no DAG
edge, and no retry for the seat (a second checkout refuses "no ACTIVE roster row").
Third, `daemon-owned-records.yaml#files` listed `sessions.csv` and `state.csv`, and
`compiler.js:183-187` ro-binds each such name under the goal folder AS A FILE — while
`records.py#write_csv_table` is tmp + `os.replace`, and `rename(2)` onto a bind
MOUNTPOINT is unconditionally EBUSY. Staff seats were unaffected only because they are
never caged (`envelope/launch.js:11` STAFF).

## Attempts
The goal's own `#-1935` correction concluded the EBUSY was "transient contention…not an
architectural mismatch", because the same seat's check-out wrote `sessions.csv`
successfully seven minutes later. That verdict is WRONG and was measured wrong here: in a
real bwrap cage over the compiled bind set, tmp+rename onto the ro-bound `sessions.csv`
fails EBUSY; then, after an UNCAGED process does its own atomic replace of that file
(which the daemon does constantly), the seat's bind is left over a detached inode, the
in-namespace path resolves to the new host file with no mount on it, and the identical
rename succeeds. Nothing contended — the carve dissolved. Acting on "add a retry/lock"
would have fixed nothing. Checked before editing: `envelope/20260827-i-coordination-was-
read-only-in`, `team-kit/20260824-c-kit-endings-via-store-client`,
`server/20260824-c-plan-time-envelope-compiler`,
`server/20260824-i-lastcovering-ignored-the-compi`.

## Fix
`envelope-template.yaml` gains family 8 `ending-store`, `{workspace}/.rbtv/runtime/ignite`
rw, consumed by `compiler.js` beside the other seven; `load-config.js` derives the row
count from `REQUIRED_FAMILY_IDS` instead of the literal 7; `launch.js#ensureEndingStore`
mkdirs the dir before the compile, the rule `ensureGoalScratch` already follows. THE
DIRECTORY, not `heart.db`: sqlite in WAL mode writes `heart.db-wal`/`-shm` beside the db,
so a file-level opening is still a read-only database, and no dedicated store subfolder
exists. `authorizedCarve` already admits an rw narrow inside the vault-wide-read ro wide,
so no carve rule was added. `checkout.py` moves the ending stamp ahead of `session_close`
and the roster flip (export first, for the evidence pointer), so a refused stamp closes
NOTHING and the seat can retry. `sessions.csv` and `state.csv` leave
`daemon-owned-records.yaml#files`. Rejected: a carve-back list for the four daemon
artifacts sharing the store directory (a second list to keep in step with a directory the
daemon keeps adding to; record forgery is a stated NON-goal, D3); a file-level bind of
`heart.db` alone (WAL); making the refusal UNDO the flip instead of reordering (a
compensating rollback across two files that can itself fail); a retry/lock around the
`sessions.csv` rename (fixes a mechanism that was never the cause).

## Consequences
A caged seat can now stamp its own ending, close its own session row and stamp its own
check-in. `seat.md` stays read-only — a wall-control surface, not a record (D3 item 3) —
and so do `goal.md`, `milestones.csv`, `taskforce.csv`. The store directory's four other
artifacts (`asks/`, `leader-instructions/`, `outbox.json`, `system-digest.json`) become
writable from every caged seat; stated in the template, accepted under D3, not defended.
`seat-grants.js:91` still refuses a DECLARED rw-path naming `sessions.csv`/`coordination`
with the message "the identity/ground-truth surfaces … stay unwritable", which now
contradicts the cage it describes — a declaration gate, not a bind, and untouched here.

## Verification
`node ignite/envelope/envelope-compiler.selftest.js` → `PASS planning-zero-fill-in`,
`PASS compiler`, with three new positive arms (`innermostAccess` rw on the store dir AND
on the `heart.db-wal` sidecar path; family 8 emitted) and the `sessions.csv ro` row
INVERTED into two positive rw ones plus a `seat.md` stays-ro pin. RED-CONFIRMED three
ways: family 8 flipped to `ro`, family 8 deleted from `compiler.js`, and `sessions.csv` +
`state.csv` put back in `files:` — each throws exactly its own arm. REAL-CAGE PROOF: a
bwrap launched over `admitLaunch`+`bindsToSpec`+`specToBwrapFlags`+`composeAncestorMasks`
for a `/var/tmp` fixture workspace, against a byte copy of `heart.db`, printed
`mountinfo: rw`, `scratch write: OK`, `stampSeatDeclare: OK` and a readback with
`who_stamped: seat`; with family 8 removed the same cage printed `touch: … Read-only file
system` and `attempt to write a readonly database`. Same harness proved the sessions.csv
half: `T1 tmp+RENAME … FAILED` (EBUSY) with the carve, `OK` without it, and `T2 … OK`
after a host-side atomic replace — the dissolving-carve measurement. `python3 -B
ignite/coord/coord.py selftest` 1014 → 1015 ok, 0 failures; the new arm `CW-cage` asserts
exit≠0, the store error named, NO `checked out` line, roster still ACTIVE and the session
row still OPEN, and goes RED when the pre-fix order is restored. `envelope-launch`,
`envelope-shims`, `wall-report` selftests exit 0; `probe-cage-workspace-grammar`,
`probe-cagespec-mirror`, `probe-seat-cage`, `probe-envelope-walls`, `probe-private-scope`,
`probe-ancestor-mask`, `probe-checkout-disposition` (11/11), `probe-finish-edge` all exit
0. No `exposure.csv` touched, so `component_lint` is unchanged by construction. tmux
session list byte-identical. Deployed: NO.

## ATTENTION
- ⚠ DEPLOY AND RESTART IN ONE OPERATION. The daemon re-reads the three envelope YAMLs per
  compile but holds `load-config.js` in its require cache, so a deploy worktree carrying
  the 8-row template under an un-restarted daemon throws `families must be a 7-row list`
  on EVERY caged launch. Restart `rbtv-ignite` in the same step.
- A caged seat executes `coord/*` from the WORKING repo, not the deploy worktree: the
  `exposed-clis` entry point is an absolute path baked into `seat.md` by the materializer
  (`spawn.js#resolveExposedCliGrants`), and the live argv symlinks
  `/home/henri/.rbtv-bin/coordinate` → `…/3-resources/tools/rbtv/ignite/coord/coord.py`.
  So the checkout reorder is live for the next seat with no deploy; the envelope/spawn
  half is daemon code and is not.
- Do NOT put `sessions.csv`, `state.csv` or `coordination` back in
  `daemon-owned-records.yaml`. A file-level ro carve there does not survive the daemon's
  own next atomic replace of the file — it protects nothing and only breaks check-in.
- `cage.SeatBinds` in `spawn-profiles.yaml` is NOT the live composer; `compiler.js` is.
  `spawn.js`'s ground-truth paragraph claimed otherwise until this change.
- The ending store dir is opened WIDER than the db. If `asks/` or `outbox.json` ever needs
  protecting from a seat, the answer is a store subfolder for `heart.db`, not a carve list.
- deploy the 8-row template and restart the daemon in ONE step; load-config.js is require-cached
