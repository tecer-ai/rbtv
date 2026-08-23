# 20260822-c-admission-brake-door — Admission brake door

kind: creation
component: engine
date: 2026-08-22
commit: 8478c7a5,affceae2,6c997616,c833046e
deployed: yes
pin: server/ticker/probes/probe-seat-queue.js (scheduled)
components: server,gateway
seeded: true

## What it is
Fail-closed admission brake in enqueue() that no caller can opt out of.

`heart-store.js`'s `enqueue()` gains a fail-closed admission brake door (`c833046e`, 125 lines) that no caller can bypass; `reconcile.js` threads a reason+signature into every enqueue call (`affceae2`) and excludes system mail from the brake; heart-store's migrations/schema gain a braked-outcome column + mirrored reason allowlist (`6c997616`); `gateway/parse.js` and `dispatch.js` are updated to carry the reason/signature through the request path; `probe-seat-queue.js` gets a distinct synthetic reason per test row under the brake (`8478c7a5`).

## Why
D52/D66/D70/D84: enqueue() had no fail-closed gate; any caller could enqueue unboundedly.

`redesign-plan/decisions.md#D52,D66,D70,D84` — the queue's enqueue() path had no fail-closed gate; any caller (including a runaway mechanical relaunch loop) could enqueue unboundedly. This closes that with a brake that is structurally impossible to opt out of, not merely convention.

## How to use & where wired
Every enqueue() caller must supply a reason+signature evaluated by the brake.

Every enqueue() call site (reconcile.js, dispatch.js) now must supply a reason+signature; heart-store.js's brake logic evaluates admission before the row is written.

## commit
8478c7a5,affceae2,6c997616,c833046e

## deployed
yes

## pin
server/ticker/probes/probe-seat-queue.js (scheduled)

## ATTENTION
- This is a fail-closed, no-opt-out gate by design (D52/D66/D70/D84) — do not add a bypass parameter for "trusted" callers; that reopens exactly the unbounded-enqueue problem this closes.
- system-problems.md#5 records this same probe (probe-seat-queue.js) caught a live regression the same day it was introduced, during the build-chain's 07-brake step (commit fa69c6ec, outside this seat's rows) — treat a red probe-seat-queue.js as a real regression, not a flaky fixture.
- fail-closed, no-opt-out by design (D52/D66/D70/D84); do not add a trusted-caller bypass
- probe-seat-queue.js caught a real same-day regression once; treat red as real, not flaky
