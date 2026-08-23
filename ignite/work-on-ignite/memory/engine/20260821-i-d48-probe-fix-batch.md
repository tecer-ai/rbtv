# 20260821-i-d48-probe-fix-batch — D48 probe fix batch

kind: issue
component: engine
date: 2026-08-21
commit: 0c505934,f00aba41,bb13d3a9,4d47c796,d27c44f4,3303c80e
deployed: yes
pin: self-pinning, all scheduled
components: team-kit,server,deploy
seeded: true

## Observed
On 2026-08-21 the post-cutover decision-review (four read-only seats under `decision-review/seats/`; durable record `redesign-plan/seed/decision-review-2026-08-21.md` §2) measured six scheduled probes red. The owner approved fixing them as one batch (D48 item 1, same day, interactive) so the D-7 goal-level session would not start against a red suite (D48 item 4). This entry is the engine-filed slice: six commits at 16:09–16:54Z that close four of those named probes plus the suite-diagnose companion of the fifth. The other two named reds — D-4 `probe-cast-spawn-drift.js` (join on `carrier` instead of catalog `mode`) and `probe-chat-live-session.js` (fixture still injected under retired `kimi:`) — live at `launch-profiles/20260821-i-cast-spawn-drift-probe-fix.md` and `bridges/20260821-i-chat-live-session-refixture.md`.

What was red here: `probe-store-ready-suppression.py` still used the archived `rbtv-sb-merge-refactor-core-build` tasks file as `DEFAULT_STORE`; `probe-enqueue-record.js` Arm E expected `migrate()` from `LATEST-1` to create `enqueue_log` and the table was absent; `probe-error-map-drift.js` failed because `dispatch.js` `NOT_WIRE_REACHABLE` still listed `E_CAGE_GROUND_TRUTH`; `probe-daemon-lane-watch.js` blew the suite's 180 s budget at L8/L9; and when that TIMEOUT wrote no fresh `.out`, `probe-suite.js` `diagnose()` pasted the previous PASS body as this run's evidence — the review called that half "the dangerous one" because it can mask a real lane failure. Engine/server/deploy JS is inert until `rbtv ignite daemon deploy`; these commits rode the same-day D47–D49 deploy that closed at `ac1c08d8` (17:23:40Z), after which HEAD and the deployed tree matched.

## Mechanism
Five independent leftovers, not one shared bug.

`DEFAULT_STORE` still named `1-projects/rbtv-sb-merge-refactor-core-build/rbtv-sb-merge-refactor-core-build-tasks.md`. The live store had moved to `1-projects/build-ignite/build-ignite-tasks.md`, so the probe was asserting suppression against a file that no longer existed.

Arm E stamped the scratch DB `PRAGMA user_version` to `LATEST - 1` (7) before `migrate()`. `migrate()` in `server/heart/migrations.js` walks versions *greater than* `user_version`, so 7 skipped `MIGRATION_ENQUEUE_LOG` (v6) and the table the arm asserts never appeared. The walker was correct; the probe's baseline was not.

`NOT_WIRE_REACHABLE` still mapped `E_CAGE_GROUND_TRUTH` to a comment about `assertGroundTruthUnwritable <- spawnSeat`. No errors module defines that code; the assertion went away with the cage anti-forgery check. The drift probe compares the map to the live vocabulary and went red on the leftover row.

`diagnose()` graded a TIMEOUT correctly, then — when this run wrote no `.out` (`r.outAfter` null or equal to `r.outBefore`) — still `readFileSync`'d the probe's existing `.out` and quoted it as this failure's evidence. Combined with the lane-watch hang, a timed-out run could present as a prior PASS. Selftest S12 previously *required* that stale line shown and labelled, so the suite's own test encoded the G-171 failure class it exists to prevent.

L8 mutation arms `cpSync`'d the entire fixture goals tree, then ran `seatBootPrompt`/`coord` per seat per goal past the 180 s budget. Inheriting the caller's `TMUX` made `tmux new-session` talk to the live server or hang on a client. After copies were scoped, a second clock still fired: each L8 mutant called `maybeReconcile` → `recover-room.py` (120 s timeout; measured 137 s on L8), and L9 re-walked the full fixture tree, re-paying `readySeats`/`seatBootPrompt`/`maybeReconcile` for every sibling.

## Attempts
First attempt held — checked: map.csv `missed_trials_source` is NONE; `git log --before=2026-08-21` on the five touched files shows earlier work (probe-suite INOPERATIVE classification, lane-watch failure-surface, store-ready numbered-row fixture) aimed at other defects, not these five reds; decision-review §2 records discovery, not a prior patch. Exception: daemon-lane-watch did not hold on the first try. `d27c44f4` (16:09:53Z) added `copyGoals(dest, names)` so each mutation copies only the goals it asserts, isolated `TMUX_TMPDIR` and deleted inherited `TMUX`/`TMUX_PANE`, and made `say`/`check` call `flushOut()` so a timeout captures a fresh partial result instead of a stale PASS. Forty-five minutes later the suite still timed out. `3303c80e` (16:54:59Z) found the remainder: L8's 137 s was `maybeReconcile` → `recover-room.py` on those copies; L9's second full walk re-paid coord for every daemon-assigned sibling.

## Fix
D48 chose batch-all-six over sequential one-by-one so the owner could join the D-7 session only after the reds were gone. Each patch is the root-cause correction named in its commit, not a shared abstraction.

`0c505934` retargets `DEFAULT_STORE` at `1-projects/build-ignite/build-ignite-tasks.md`. `f00aba41` imports `MIGRATION_ENQUEUE_LOG` and stamps `user_version` to `MIGRATION_ENQUEUE_LOG.version - 1` so `migrate()` actually walks v6; rejected was changing `migrate()` to re-run the current version. `bb13d3a9` deletes the leftover map row rather than resurrecting `assertGroundTruthUnwritable` (the anti-forgery assertion had been deleted on purpose). `4d47c796` makes `diagnose()` return early when `wroteThisRun` is false, with the line "capture not written by this run — prior .out is not evidence"; S12 now asserts the stale EARLIER-run line is not quoted (the previous S12 required it shown-and-labelled, which would have rebuilt G-171). `d27c44f4` then `3303c80e`: scoped copies, tmux isolation, live `.out` flush; then `mutantWatch` stubs `maybeReconcile` to `{ skipped: 'probe-mutant' }` so mutation arms prove lane-watch guards not the watcher, `withOnlyGoals` parks siblings in place (copying to a new root would break L5c's path-keyed shout-memo and L9's boot-prompt byte-identity), and L9 runs over `prompt-goal` only. The stub is mutation-only — the green L5 pass still calls real `runLaneWatch`.

## Consequences
`bb13d3a9` is a one-line deletion in `dispatch.js`. Same-day `ac1c08d8` (D49.1 secret-add) and next-day `6c997616` (D52/D66 enqueue_log allowlist) touch that file and neither restores the row. `0afe6f88` (2026-08-22, D81) later aligns `SESSIONS_HEADER` fixtures in daemon-lane-watch with the D42 hold-anchor — a fixture follow-up, not a hang regression. Store-ready, enqueue-record, and probe-suite have no further commits after 2026-08-21. The two sibling D48 probes (`69760b69`, `cfdc49e4`) are not in this header; together they make the eight-commit batch the launch-profiles entry names. Decision-review §6 (~18:30Z) records "all six probe reds green" as part of that same session, not a later verification pass.

## Verification
S12 in `probe-suite.js` `selftest()` is the new pin for the stale-`.out` trap (rewritten in `4d47c796` from "shown, labelled" to "must not quote"). The five probes are themselves scheduled and self-pinning — no separate pinning-probe commit exists. Deployed yes with the rest of D47–D49 at `ac1c08d8` (2026-08-21 17:23:40Z). No post-fix probe-suite run log was located beyond the decision-review §6 green claim.

## ATTENTION
- daemon-lane-watch's hang had two stacked causes the same day. Bounding mutation copies (`d27c44f4`) left `maybeReconcile` → `recover-room.py` (120 s) still firing inside `mutantWatch`, plus L9's full-tree re-walk. A green single-arm run does not prove the hang is gone — the original failure was the 180 s suite budget under L8/L9 load.
- `diagnose()` quoting a prior `.out` on a TIMEOUT with no fresh capture rebuilds G-171 inside the suite. S12 now forbids quoting that stale line. If a probe result looks identical to the last run and the child wrote no `.out`, `wroteThisRun` is the check that stops a stale PASS masquerading as this run.
- `mutantWatch` stubs `maybeReconcile` so mutation arms stay inside the suite budget. The green L5 pass must keep calling real `runLaneWatch` — stubbing L5 would make the "watcher still works" arm vacuous. `withOnlyGoals` parks siblings in place because a flattened or new-root copy breaks L5c's path-keyed memo and L9's boot-prompt byte-identity.
- D48's "six probes" are not these six commits. The review named six probes; this header is four of them plus the suite-diagnose companion of the fifth, in six commits (lane-watch took two). D-4 (`carrier` vs catalog `mode`) and the chat-live-session kimi refixture are sibling entries. Two brief-claims in the same review were disproven (doc-only `8e66585e`, unproven "foreign deletions") — those are not causes of these reds.
