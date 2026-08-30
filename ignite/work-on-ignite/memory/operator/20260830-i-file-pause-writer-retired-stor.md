# 20260830-i-file-pause-writer-retired-stor — file pause writer retired; store row is one truth

kind: issue
component: operator
date: 2026-08-30
commit: 660e6cf2
deployed: no
pin: ignite/runtime/internal-api/probes/probe-pause-resume.js
components: supervisor,state-store

## Observed

Two ways to pause a goal disagreed. `rbtv goal pause` stashed a `paused ` prefix in the goal's `execution-lane` file (`goal_cli.py#cmd_pause`). Slack/daemon `pause` wrote the ending-store goal-state row (`heart/pause-resume.js#writeGoalWord`). `lane-watch.js#laneIsPaused` was an OR over both, and `applyResume` refused a store-side resume that met a live file marker. A goal paused one way and resumed the other stayed paused. Owner ruling D-1 (a), 2026-08-30 (`live-acceptance-tests/checkpoints/wave-close-decisions.md`): retire the lane-file writer; the store row is the only truth. Measured on HEAD 54960623 before this sitting; four live goals still carried the leftover prefix (`stools-canvas-audio-elevenlabs`, `ignite-engine`, `meet-transcript-summarizer`, `goal-memory-management`) and were not written.

## Mechanism

The wrong value was born at `cmd_pause`/`cmd_resume`, which treated the lane file as a pause surface while the daemon's mechanical verb already had a store writer. `laneIsPaused` then had to OR the two, which re-opened a0d7e42c's stale-marker freeze on purpose (4a032354, OWNER-GATED retirement). `applyResume`'s `lane-file-paused` refusal made the split visible instead of silent, and `cmd_resume` had to unstash FIRST so it would not refuse itself (8c226055). That is two writers of one fact.

## Attempts

First attempt held — checked: `4a032354` / `20260828-c-laneispaused-two-pause-writers` (OR gate, retirement owner-gated); `a0d7e42c` / `20260824-c-one-pause-record-the-goal-stat` (row wins, file shim); `919be192` / `20260828-i-pause-wrote-a-store-the-lane-g` (executor takes no store handle); `8c226055` / `20260828-i-the-console-resume-never-fired` (console resume already called the executor after unstash). Nothing had retired the file writer because that was owner-gated until D-1 (a).

## Fix

Console pause and resume write the row through the same executor Slack uses: `state-store/cli.js --op pauseResume`, no `--db` (that absence is 919be192). Direct sqlite from Python was rejected; routing through the gateway was rejected (`canPauseResume` is `sender.kind === 'bridge'` only). The lane file keeps only the lane word. `laneIsPaused` reads the row; a leftover `paused ` prefix is consumed once — port `paused` into the row if the store has no word, then strip; if the store already has a word, strip the stale prefix and believe the row. Never strip a prefix that is the only pause evidence. `applyResume` no longer refuses a leftover prefix. `runLaneWatch` now `continue`s when the row is paused: seeding used to skip only because the prefix made `readLane` return console.

## Consequences

`laneMarkerRefusal` / `laneFileParks` deleted. Python `lane_is_paused(raw)` remains as leftover-prefix detection for `cmd_lane` / `add-seat` so a live leftover still reads paused without this sitting writing `.rbtv/`. `_`-prefixed names are addressable but `pauseResume`'s roster still excludes them (`no-such-goal`). `evidence_pointer` still says `in chat` (R0d/R4 pin the parameter list). `supervisor/component.md` still describes the OR (another seat holds that file). `authz.js` still comments on two writers.

## Verification

`goal_cli.py selftest` pause/resume arms green (file unchanged, row paused then running, leftover ported); three pre-existing coord-symbol failures remain. `lane-skip.selftest.js` 6/6. `probe-pause-resume.js` 54/54 EXIT 0 including R3 leftover-consumption mutant. `probe-console-resume-rearm.py` 29/29. `probe-goal-splice.py` 48/0. `probe-daemon-lane-watch` L2/L5 pause arms green; sole remaining red is the named L9 M9. `reconcile.selftest.js` still dies at the named `:392` BOOT-PROMPT-BODY red (pause row not reached). Four live goals' `rbtv goal lane --json` identical before/after (paused true, paused_from daemon). tmux list byte-identical. NOT DEPLOYED; DAEMON must restart for lane-watch/reconcile; console CLI is live on save.

## ATTENTION

1. THE EXECUTOR STILL TAKES NO STORE HANDLE. Handing `--db` to `--op pauseResume` re-opens 919be192: a pause written in the caller's lane store is invisible to `laneIsPaused`.
2. `runLaneWatch` MUST continue when `laneIsPaused` is true. Without that continue, a store-paused goal whose lane file reads `daemon` is adopted — the file prefix is gone, so `readLane` no longer flattens it to console.
3. A leftover prefix with no row is paused until ported. Stripping it because "the file is not the pause surface" silently un-pauses every goal that still carries the old marker, including the four live parked goals.
4. Do not widen `pauseResume`'s parameter list without moving `probe-pause-resume` R0d/R4. Those arms match the signature as a literal string.
- THE EXECUTOR STILL TAKES NO STORE HANDLE. Handing --db to --op pauseResume re-opens 919be192.
- runLaneWatch MUST continue when laneIsPaused is true or a store-paused daemon-lane goal is adopted.
- A leftover prefix with no row is paused until ported; stripping it silently un-pauses live parked goals.
- Do not widen pauseResume parameter list without moving probe-pause-resume R0d/R4.
