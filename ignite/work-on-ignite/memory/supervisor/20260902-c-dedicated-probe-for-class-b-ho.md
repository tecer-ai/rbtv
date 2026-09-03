# 20260902-c-dedicated-probe-for-class-b-ho — dedicated probe for class-B hold suppression

kind: creation
component: supervisor
date: 2026-09-02
commit: 4f0d80335c574974d7ce953db45b80d68a9f65fd
deployed: yes
pin: ignite/supervisor/probes/probe-hold-classb.js

## Motivation
The class-B (unread-mail) hold-suppression fix itself (`if (holdMap.has(chair)) continue;` added to
`classifyOwed`'s class-B loop, commit `bb1e6350`, filed as
`memory/supervisor/20260831-i-class-b-unread-relaunch-bypass.md`) has its only automated proof inside
`reconcile.selftest.js`'s own class-B hold arms — and that shared suite aborts at an unrelated,
pre-existing `D35` fixture failure before reaching them (the same D35 the `0e4a270c` fixture fix in
this plan addresses). `judge-final` required committed-and-reachable proof for this fix independent of
that aborting suite.

## Design
`probe-hold-classb.js` is self-contained: it drives the real `classifyOwed` function directly against
constructed chair/hold/mail state, with no dependency on `reconcile.selftest.js` reaching any
particular line. Three arms: a control (an unheld chair with pending mail IS relaunched — proves the
harness itself isn't vacuously green), a held arm (the same chair/mail under a live hold — no launch,
`heldExcluded` still names the chair, the counter stays frozen), and a RED arm (removing
`holdMap.has(chair)` from a COPY of the live source reproduces the exact 2026-08-30 live bypass this
fix closed). Placed under `ignite/supervisor/probes/` so `ignite/deploy/probe-suite.js` discovers it
automatically, rather than requiring a manual wire-up.

## How it works
Run directly: `node ignite/supervisor/probes/probe-hold-classb.js`. It imports `classifyOwed` from the
live `owed-from-endings.js` source (not a reimplementation), constructs the three scenarios above in
memory, and asserts the expected `classB`/`heldExcluded` contents and launch counts for each.

## Consequences
While tracing why the aborting suite had gone unnoticed for so long, this seat also found a second,
independent defect: `probe-reconcile.js` (the scheduled wrapper around `reconcile.selftest.js`) checks
`finish.status !== 0` on the child process result instead of the actual exit status field — a guard
that can never observe a nonzero exit, so a selftest failure inside the wrapped suite cannot fail the
scheduled probe run. This was folded into the existing `probe-suite` loose end as a fix-this-first item
rather than fixed inside this seat (outside this fix's granted surface). No production code changed by
this commit — probe file only.

## Verification
`node ignite/supervisor/probes/probe-hold-classb.js` → exit 0, 10/10 PASS. `judge-supervisor`
re-verdict on relaunch: PASS — control launches, hold suppresses, RED arm relaunches while
`heldExcluded` still names the chair. Deployed live on deploy tree `e8524c31` (`ignite/core-daemon`) —
the probe itself has no separate "deploy" step beyond being present on the branch and discoverable by
`probe-suite.js`.

## ATTENTION
1. This probe is the ONLY reachable, committed proof of the class-B hold-suppression fix
   (`bb1e6350`) until `reconcile.selftest.js`'s pre-existing `D35`-region abort is cleared end to end —
   do not delete or disable this probe on the assumption the shared suite already covers it.
2. `probe-reconcile.js`'s exit-status check is broken (`finish.status !== 0` never fires) — the
   scheduled probe suite currently CANNOT detect a `reconcile.selftest.js` failure. This is a live gap
   in deploy-time regression detection, tracked as a probe-suite loose end, not yet fixed.
- probe-reconcile.js `finish.status !== 0` never fires — suite cannot detect a reconcile.selftest failure
