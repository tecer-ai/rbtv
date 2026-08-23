# 20260822-i-ro-mask-private-scope-fix — Ro mask private scope fix

kind: issue
component: server
date: 2026-08-22
commit: 6b55b1c4
deployed: yes
pin: NONE
seeded: true

## Observed

Every daemon-fired `leader` for `meet-transcript-summarizer` died before the harness exec'd, with `bwrap: Can't mkdir parents … Read-only file system` (`6b55b1c4` message; D53). The same crash shape had already been measured the previous evening: three fresh daemon-fired `leader` spawns died before check-in at 20:59:57 / 21:05:01 / 21:10:09Z (`system-problems/seats/dead-shared.md`, p576-spawn). Those deaths are dead sittings that spend zero tokens — the process never reached a model request — but the work still did not run. D53 (owner interview 2026-08-22 ~00:30–01:30Z, `redesign-plan/decisions.md`) named the instance and the order: fix the read-only cage mount, then let the watcher resume. `#576` on 2026-08-20 05:37–08:00Z (39 daemon-fired spawns dead in 7–18s, zero check-ins) was a different root cause — HTTP 429 session-limit, visible only in per-seat logs — reused under the same issue number. The predicate still matches HEAD; deployed-vs-HEAD do not differ on this excuse.

## Mechanism

D48 (`92e7156c`, 2026-08-21) replaced `tmpfs:{goalDir}/seats` with `ro-mask:{goalDir}/seats` so a write into a peer-seat folder would refuse instead of succeeding into a disappearing tmpfs (`redesign-plan/decisions.md` D48 clause 2). `composePrivateScope`'s `visible()` decides whether a path is worth a second, deeper bwrap mount. Before this commit it was `return !!cover && cover.verb !== 'tmpfs'` — only a tmpfs cover counted as already absent in-namespace. After the verb swap, a pattern-floor hit such as `**/*token*` under a peer seat's now-`ro-mask`-covered subtree still returned true, so `composePrivateScope` laid a deeper mask under an already-read-only parent. bwrap's `mkdir` for that mount failed EROFS and killed the spawn. `visible()` did not treat the path as invisible; it treated it as still worth masking.

## Attempts

First attempt held — checked: D1–D53 text, `fix-inventory.csv` D53 row still reading "NONE — zero commits… NOT DEPLOYED" (the CSV predates `6b55b1c4`), and `git log --before=2026-08-22T13:35:07 --grep=EROFS|Read-only -- ignite/server/spawn/` which returned `92e7156c` (D48 truly-everything / seats-cover swap) and `ac4726a6` (D3 fence) — neither audited this predicate. The precondition is D48 itself: that commit fixed silent discard of peer writes and did not extend `visible()`'s cover-verb list. Seeding map `missed_trials_source` is NONE.

## Fix

D71 scopes the work: excuse the `ro-mask` cover in `private-scope.js` now; file a general pre-launch viability check to the engine-goal backlog. `visible()` becomes `return !!cover && cover.verb !== 'tmpfs' && cover.verb !== 'ro-mask'`. The same excuse is added to `composeAncestorMasks` in `cage.js` (`if (!cover || cover.verb === 'tmpfs') continue` gains `|| cover.verb === 'ro-mask'`) by shape-match — the commit says that site had not been independently observed to fire. The class-level check was the rejected-for-now alternative: it would have caught any later cover verb the two predicates forgot, at the cost of a broader design D71 explicitly deferred. No other alternative (skip already-covered paths at the caller, a shared "already excluded" helper) is named in D53/D71 or the commit.

## Consequences

D48's `ro-mask` stays; this only stops stacking a second mount under it. `7f6eaf3e` (~40 min later, D56/D74) adds `needsDeclaration` in the same file, walking the same deny-list / pattern-floor data for the undeclared-tool PATH shim — it builds on the floor, it does not revert the excuse, and it does not consult cover verbs. No later D-ruling (D72–D92) mentions `6b55b1c4`, `ro-mask`, or `composePrivateScope` again. D88 records that after the `#576` deploy (`6b55b1c4`, 15:15Z) the meet leader stayed down: `heart.db` `reconcile_attempts` `nonterm:leader=exited` at 219 with `stuck_emitted=1`, because the D44 brake re-arms only on a changed signature and D70's owner-message re-arm was still unbuilt. That is not this predicate failing. `20260821-c-truly-everything-master-cage` already names this entry as one of two next-day hardenings of the D48/D49 cage.

## Verification

`probe-private-scope.js` (existing scheduled probe; no new pin file — header `pin: NONE` matches) is the only probe the commit touches. Leg 9's TEMPLATE switches `tmpfs:{goalDir}/seats` → `ro-mask:{goalDir}/seats` so the fixture matches the shipped D48 config; a nested `peerDir/sessions/deadbeef/dump/channel/tokens/tok-msg-0001.json` exercises the `**/*token*` collision; the assertion adds `!/Read-only file system|Can't mkdir/.test(nine)` on top of the peer-absence / own-folder checks. The prior tmpfs fixture could not reproduce this collision at all. Commit 13:35:07Z; D88 independently dates the deploy 15:15Z the same day. No post-deploy probe-run transcript is in the decisions log or the commit message.

## ATTENTION

- The excuse list is duplicated in `composePrivateScope.visible()` and `composeAncestorMasks`. D71 scoped the fix as one more verb now; a third cover verb that updates only one site (or neither) recurs the EROFS spawn-death. The class-level pre-launch viability check was deferred to the engine-goal backlog and had not landed at seeding.
- `#576` names at least two unrelated death modes (HTTP 429 session-limit on 2026-08-20 vs this ro-mask EROFS). Search by commit `6b55b1c4` or date, not issue number.
- After the 15:15Z deploy the meet leader stayed down (D88). That was the D44 brake at 219 `nonterm:leader=exited` attempts with D70's owner-message re-arm unbuilt — not this predicate failing. Do not revert the excuse as if the deploy did not take.
- `probe-private-scope.js` TEMPLATE must keep `ro-mask:{goalDir}/seats` (the D48 shipped shape). Switching it back to `tmpfs` makes leg 9 unable to reproduce the collision.
