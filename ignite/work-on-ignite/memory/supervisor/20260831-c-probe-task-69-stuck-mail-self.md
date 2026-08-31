# 20260831-c-probe-task-69-stuck-mail-self — probe: task-69 stuck-mail self-feed proven stale

kind: creation
component: supervisor
date: 2026-08-31
commit: ab5dea93
deployed: no
pin: ignite/supervisor/probes/probe-stuck-mail-dedupe.js

## Motivation
Task 69 (`redesign-continue-1.md`) asked to stop the daemon's stuck-mail alarm counting its own
prior `type: stuck` messages as unread mail and self-feeding — the seed's evidence was 114
`ignite-daemon`-authored `type: stuck` rows to `leader` on `meet-transcript-summarizer`,
2026-08-22, growing by ~1/10min while the leader chair stayed down.

## Design
Investigated whether the seed's mechanism still exists before building anything (`read-first.md`'s
refactor hazard). It does not: `reconcile.js`'s `sendStuck` — the function that wrote a `type:
stuck` message from `ignite-daemon` to `leader` on every dead cadence — is DELETED as of the
2026-08-25 attempt-counter redesign (`20260825-c-attempt-counter-replaces-both.md`). The daemon no
longer emits a `type: stuck` row on a repeating timer; a stalled retry now stamps an ending-store
exhaustion record and an ask, never a bus message. Separately, D70 (commit `affceae2`,
2026-08-22) already excludes the ONE surviving system-mail sender (`ignite-daemon`,
`SYSTEM_MAIL_SENDER`) from class B's unread count in `owed-from-endings.js`, so even the one
remaining system-authored bus write (`seeding.js`'s idempotent-per-(seat,reason)
`surface-refusal`) can never count as progress or re-arm the class B wake. No code change was
needed; a probe was added instead, to guard the finding.

## How it works
`ignite/supervisor/probes/probe-stuck-mail-dedupe.js` drives `reconcile.js`'s `owedFromLedgers`
(the real production wiring) against a fixture goal folder with the leader chair down: one real
unread message plus four `ignite-daemon`-authored `type: stuck` rows numbered exactly as the seed
observed (`unread:leader:846` -> `#847` -> `#848` ...). Asserts `classB[0].unreadCount === 1` and
`lastNum === 846` (the daemon's own rows are invisible to the count). A control arm confirms a
genuine `type: stuck` report from a REAL seat (not the daemon) still counts and wakes the chair —
the exclusion is sender-scoped, never a blanket filter on the `stuck` type. A red arm reverts the
`m.sender !== SYSTEM_MAIL_SENDER` clause in a scratch copy of `owed-from-endings.js` (module-cache
substitution, cleaned up after) and confirms `unreadCount` then climbs to 3 and `lastNum` drifts
to the daemon's own last row — proving the fixture actually discriminates rather than passing
either way.

## Consequences
No production file changed. Confirms task 69 is STALE on the current tree — the self-feed
mechanism it targeted was removed by an unrelated refactor before this seat ran, and the
narrower symptom it also named (class B counting system mail as unread) was already fixed by
D70. The probe is new regression coverage; nothing existing was replaced.

## Verification
`node ignite/supervisor/probes/probe-stuck-mail-dedupe.js` — ALL PASS (3/3 arms), exit 0. Run
through the runner: `node ignite/deploy/probe-suite.js --dir supervisor/probes --only
probe-stuck-mail-dedupe` — SUITE-COMPLETE verdict=GREEN. Also re-ran the existing
`ignite/supervisor/owed-from-endings.selftest.js` (10/10 arms, including its own D40
SYSTEM_MAIL_SENDER mutation guard) — ALL PASS, unmodified. Not deployed — no deploy needed (no
source changed).

## ATTENTION
1. `reconcile.selftest.js` currently fails on an UNRELATED, pre-existing arm (D33(a) class A
   relaunch payload naming, "leader payload never names ... BOOT-PROMPT-BODY") on a clean,
   unmodified checkout of `ignite/supervisor/reconcile.js` / `reconcile.selftest.js` — not caused
   by this change and out of this seat's scope (shared-custody file; only the class B / unread
   arms were this seat's concern, and those passed before the unrelated failure). Surfaced, not
   fixed.
2. `ignite/coord/checkout.py#unread_for` still does NOT exclude system-authored mail — but it
   feeds `ready.py`'s READINESS verdict (whether to spawn a never-sat chair at all), a
   structurally different one-shot gate under the `readiness-gate` custody wall, not the repeating
   class B relaunch alarm this task targeted. Left untouched; no observed present cost since the
   daemon's own repeating stuck-mail source is gone.
