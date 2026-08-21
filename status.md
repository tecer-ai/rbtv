
## 2026-08-20 17:35Z — D39 + D40 LANDED in reconcile.js (commit `d813ebcc`, deployed); D39 propagation into coord.py IN FLIGHT

All 9 clauses of the dispatched fix MET, with LIVE post-deploy proof — not a fixture:

- **D39.** The flag spelling was read off `coord.py launch --help` before writing (`--declare-only
  LEADER-ANCHOR` confirmed). The pre-deploy control (meet's 17:13 leader wake,
  `prompts/ab08fee5-….txt`) carried the false `# CLEAR → ordinary relaunch`. Within ~2 minutes of the
  deploy, a REAL leader wake on meet (`prompts/3b5a646e-….txt`, rows `plan-3-plan-check-assembler` /
  `plan-3-plan-check-clarity`) carried: `# CLEAR the row` … `CLEARING IS NOT A RELAUNCH — they are TWO
  acts (D39). A cleared row reads UNDECLARED, the daemon maps that to not-waitable, and NEVER re-seeds
  it. … launch --only <seat> --declare-only <p-*/d-* or message ref> … Clear without that second
  command and the seat simply sits there.` The selftest arm now asserts `!/ordinary relaunch/` and
  requires both needles.
- **D40.** New arm — same seat, same word, DIFFERENT `ended` (10:05 then 14:47): `attempts=1 stuck=0`
  → `attempts=2 stuck=1`, `signature=incomplete:worker-a` both passes. RED by mutation on a compiled
  COPY (restoring `:${item.ended}`): `attempts across 3 sittings = [1,1,1], stuck sends = 0` — the
  live defect reproduced.
- Probe `probe-reconcile.js` EXIT=0; suite `--only reconcile` `verdict=GREEN exit=0` (the agent found
  `rbtv-probe-suite.service` `activating` and BLOCKED until `inactive` before running — correct).
- ONE commit `d813ebcc` (2 files, 104 ins / 6 del), ONE deploy `a06723ec -> d813ebcc`, pid 2837616,
  `health healthy`. **Ride-alongs: NONE** — `git log --oneline a06723ec..d813ebcc` is exactly one line.
  Orchestrator re-verified: `git show --stat`, deploy-tree HEAD = `d813ebcc…`, health field `healthy`.

**One-time expected effect:** the old-format `reconcile_attempts` row
(`stools/audio-component-smith/incomplete/attempts=1/signature=incomplete:audio-component-smith:2026-08-20 17:14`)
resets to 1 once under the new signature format, then accrues. No cleanup owed.
Also observed, and correct by design: meet's leader `nonterm` row sits at `attempts=5, stuck_emitted=1`
— D34 emits `stuck` ONCE, then the wake repeats quietly.

**IN FLIGHT — the same falsehood survives on the MORE-READ surface.** The fix agent surfaced that
`coord.py` still asserts a clear "re-arms an ordinary relaunch through seeding" at ~5 sites INCLUDING
the user-facing `rule-disposition --help` text — the surface a leader actually reads before ruling.
Orchestrator confirmed by python scan (lines 2629, 3855, 15352, 17071, 35828; line 21552 is an
UNRELATED tmux fixture and is excluded). A scoped agent is correcting them now: coord.py only, saved
through the `save-coord.py` gate, selftest green, ONE pathspec commit, and NO deploy or restart is
owed (coord.py is read live per invocation → effective on commit).

**`resolve-verify` stays HELD until that lands** — it drives the LEADER through these very verbs, and
must not be briefed off a `--help` text that states what the owner ruled false.
