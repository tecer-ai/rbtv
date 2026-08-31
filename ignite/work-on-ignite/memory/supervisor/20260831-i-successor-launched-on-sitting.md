# 20260831-i-successor-launched-on-sitting — Successor launched on sitting done, not gate verdict

kind: issue
component: supervisor
date: 2026-08-31
commit: 48c86e40523233450f9e9a11dad41facfde2882d
deployed: no
pin: ignite/supervisor/probes/probe-failed-upstream-gate.py
components: coord
register-id: G-leader-0823-1443

## Observed
On ignite-engine m4 at 2026-08-23 14:33Z, `proposal-record-smith` checked out `done` (honest sitting) while `planning/m4-triage-contract/evidence/proposal-record-smith.json` opened with `verdict: FAIL`. `triage-rehearser` (`after=proposal-record-smith`) launched 14s later, ran 9s, never checked in, and left a 0-byte evidence file — the goal's only `crashed` execution (session `97af3e6e-efd1-4729-a7da-50eaae152b99`). Filed G-leader-0823-1443. Deployed daemon still has the old arithmetic until this commit ships.

## Mechanism
`ready.py#after_member_state` treated a predecessor as satisfied when `terminal_disposition` was the word `done`. That word is session disposition (the sitting ended), not milestone verdict (the work succeeded). Seeding consumes `verdict === READY` only, so the successor launched behind a gate its own contract already failed.

## Attempts
First attempt held — checked: supervisor memory (`20260830-i-launch-frontier-honours-kit-re` honours kit READY vs endings, a different dual-read); 7.383 `name[key=value]` guards against `guard-values.csv` (not an on-disk evidence file); options (b) checkout rider and (c) launch-door WARN, rejected as dearer than a read of a file already on disk.

## Fix
Option (a): optional taskforce columns `gate-artifact` and `gate-required` (`key=value`). After `after` members are met, readiness reads the JSON at that path and requires the first key to match. Undeclared rows keep today's disposition-only edge. Not a 7.383 overload. Materialize's exact header is unchanged (extra columns are fixture/hand-edit). Disposition writers were not touched.

## Consequences
No new verdict word. BLOCKED reason names `gate=…`. A FAIL artifact does not mark the seat `dead` (the file can later read PASS). Live goals do not declare the columns until a writer exists; without a declaration the old edge still advances. The archived `triage-rehearser` hold is not cleared.

## Verification
`coord_selftest.py` dag-10 GATE arm green. `supervisor/probes/probe-failed-upstream-gate.py` PASS via `probe-suite.js --only probe-failed-upstream-gate`. Scratch `ready-seats --json`: FAIL artifact → succ BLOCKED; PASS → READY. Scratch worktree with the hunk disabled: succ READY, then live tree BLOCKED. Not deployed.

## ATTENTION
- Extra columns are not in `TASKFORCE_HEADER`; materialize still exact-matches the eight-column header and will refuse a live goal that carries them.
- 7.383 guards are a different surface (`guard-values.csv`); do not encode a file path as `name[key=value]`.
- Task 98 (`coord-death-class`) reclassifies dispositions; this change must not fold into that — no ending-store write path was edited.
- Extra taskforce columns are not in TASKFORCE_HEADER; materialize exact-match refuses them on a live goal.
- 7.383 guards are not a gate-artifact read; do not encode a file path as name[key=value].
- Task 98 reclassifies dispositions; this change must not fold into that — no ending-store write was edited.
