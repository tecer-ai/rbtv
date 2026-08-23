# 20260821-i-heart-store-perf-fixes — Heart store perf fixes

kind: issue
component: server
date: 2026-08-21
commit: fecd3b6a,6fc989bc
deployed: yes
pin: NONE
seeded: true

## Observed

On the live daemon the morning of 2026-08-21, `rbtv ignite inspect` POSTs outlived the CLI's 10 s timeout while the process still reported healthy. `6fc989bc` (05:00:33Z) measured gateway first-byte at 39.7–60+ s and ~9.5 s of every 10 s cadence blocked on the same Node event loop that serves HTTP. The engine passes `recordView`, `executionsByJob`, `publishToRecord`, and the queue-request/lane-watch pass around them called `HeartStore.listExecutionsByStatus` ~20× per cadence; each call re-materialized every `jobs_log` row of that status — 29,301 `done` rows × 197 ms a scan. Fourteen minutes later `fecd3b6a` (05:14:54Z) measured the leftover after that cache: `listEnqueueUnfired`'s correlated `NOT EXISTS` spent 1.54 s (goal `meet`) + 1.46 s (goal `stools`) per cadence scanning the whole 31 k-row `jobs_log`, leaving worst-case inspect at ~8 s against the same 10 s timeout. Deployed-vs-HEAD: both commits are in the deployed tree (`deployed: yes`); `_execListCache` / `_jobsLogGen` and `idx_jobslog_jobid_firedat` are still present at HEAD.

## Mechanism

Two independent SQL paths, both synchronous on the gateway loop, both growing with store size.

`listExecutionsByStatus(status, {withThread})` ran `SELECT * FROM jobs_log WHERE status = ? ORDER BY exec_id` on every call. After `a6528bec` the per-row recursive CTE was skippable via `{withThread: false}`, so the remaining cost was the scan and JS materialization itself — still O(rows), still paid ~20× per cadence because each pass asks per status per goal. Only `idx_jobslog_status` existed; nothing cached the result.

`listEnqueueUnfired(goal, cutoffIso)` asks `NOT EXISTS (SELECT 1 FROM jobs_log j WHERE j.job_id = e.job_id AND j.fired_at >= e.at)` once per `enqueue_log` row. With no index covering `(job_id, fired_at)` SQLite planned `SCAN j` of the whole table for each of those probes. `consecutiveFailures(jobId)` walks `WHERE job_id = ? ORDER BY exec_id DESC` and had the same missing `job_id` prefix. Neither path goes through `listExecutionsByStatus`, so a cache on that method cannot help them.

The daemon looked healthy because the HTTP server was still up; it simply could not answer while the loop was inside SQLite.

## Attempts

The cache half is the second attempt at this stall. `a6528bec` (2026-08-12 23:38:40Z, `perf(ignite): stop full-store scans starving the gateway event loop`) diagnosed "stops accepting after ~1–2 min of uptime" as event-loop starvation, not a socket fault: per-tick paths materialized the whole 117 MB store (recursive CTE per execution row; `getMessages` fetching 27 MB of corpus to filter one thread in JS), blocking ~6 s per 12 s tick. It added the `{withThread}` opt-out, moved `getMessages({thread})` into SQL, pointed cadence callers at `withThread: false`, and landed `probe-hot-path-scan.js` (11 checks, proved red by five mutations). It did not hold because `listExecutionsByStatus` still issued a fresh `SELECT … WHERE status = ?` every call. The store then grew from the 26,791 rows cited in the `execution-record.js` ponytail (2026-08-12, 131 ms a scan) to 29,301+ `done` rows alone; the now-cheap-per-row scan became the new multi-second block. `a6528bec` itself flagged the leftover unbounded shape in `engine/attached-execution.js` and that `heart.db` retention never prunes ticks.

The ponytail at `execution-record.js:362` reserved the next step: "a watermark on `exec_id` plus a re-scan of the non-terminal rows only" once the full scan "stops being cheap." `6fc989bc`'s message cites that note as the upgrade it is taking — without naming `a6528bec` by sha.

The index half had no earlier trial. First attempt held — checked: `git log --before=2026-08-21T05:14:54` on `ignite/server/heart/` and `ignite/engine/execution-record.js` (gateway greps); `schema.sql` carried only `idx_jobslog_status`; map.csv `missed_trials_source` empty; neither 2026-08-21 message cites a prior index attempt.

## Fix

`6fc989bc` puts an in-memory per-status cache on `HeartStore` (`_execListCache`, `_jobsLogGen`). A repeat `listExecutionsByStatus` with no intervening `jobs_log` write costs an array copy. Invalidation is two-signalled: every store writer of `jobs_log` (`fireQueueRow`, `recordExecutionStart`, `updateExecutionStatus`, `recordMessage`) increments `_jobsLogGen`; `PRAGMA data_version` moves on any other connection's commit, so a foreign writer cannot be served stale rows. Rows are cached without `thread`; `_attachThread` runs on `{...r}` copies so the cache never grows a `thread` property a `withThread: false` caller did not ask for. Chosen over the reserved watermark because it is the cheaper upgrade that still answers the ~20 identical full-history reads inside one cadence; the watermark (re-scan only non-terminal rows) was left for when even one scan stops being cheap. No D/E ruling names this pair.

`fecd3b6a` adds `CREATE INDEX IF NOT EXISTS idx_jobslog_jobid_firedat ON jobs_log(job_id, fired_at)` to `schema.sql`. Necessary because the cache cannot reach `listEnqueueUnfired` / `consecutiveFailures`. `schema.sql` runs at every boot, so an existing store gains the index at the deploy restart rather than on a live `CREATE INDEX`.

## Consequences

The `{withThread}` opt-out from `a6528bec` stayed; the cache sits on top of it (`rows.slice()` vs `_attachThread({...r})`). The watermark upgrade is still unbuilt. `idx_jobslog_status` was kept. Later `heart-store.js` work did not revert the cache or the index: `0bce303b` (2026-08-22) dropped a dead import; `c833046e` / `6c997616` (2026-08-22, D52/D66) added the admission-brake door and taught `listEnqueueUnfired` to exclude `outcome = 'braked'` — a filter on `enqueue_log`, not a change to the `jobs_log` index. No later memory entry cites `fecd3b6a` or `6fc989bc`. Adding a new `jobs_log` writer that forgets `_jobsLogGen += 1` is a silent stale-cache hole; that class of follow-up has not appeared yet.

## Verification

No dedicated pin was added (`pin: NONE`); unlike `a6528bec` these two commits touch only `heart-store.js` and `schema.sql`. Proof was ad-hoc on a copy of the live store plus the existing suite. `6fc989bc`: byte-equivalence per status; own-write and foreign-write invalidation; 20 cached `done` scans 3,940 ms → 2.2 ms; red arm — with the generation bump mutated away the cache served a stale count; `server/heart` probe suite 23/23 green. `fecd3b6a`: 1,540 ms → 0.3 ms, identical result rows, plan flips `SCAN j` → `SEARCH j USING COVERING INDEX`; suite 23/23; `probe-enqueue-record` kept exactly its two pre-existing Arm E failures (present at `2138307d`, verified by stash). Deployed yes; the JS cache and the `IF NOT EXISTS` index both take effect at the next daemon deploy/restart, not on a running process.

## ATTENTION

- This is a two-path fix landed 14 minutes apart. `_execListCache` only helps `listExecutionsByStatus` callers (`recordView`, `executionsByJob`, `publishToRecord`, queue-request/lane-watch). `idx_jobslog_jobid_firedat` only helps `listEnqueueUnfired`'s `NOT EXISTS` and `consecutiveFailures`' `job_id` walk. Dropping one path reopens that half of the stall; `fecd3b6a`'s own subject calls itself "the other half of the gateway stall."
- Second fix of the same stall in nine days. `a6528bec` (2026-08-12) only added `{withThread}` and was outgrown as the store went 26,791 rows → 29,301+ `done`. A returning stall may mean the store has grown past what this pair was measured against (29 k `done` / 31 k `jobs_log`), not a new cause.
- The next reserved upgrade is still unbuilt: a watermark on `exec_id` plus a re-scan of non-terminal rows only (`execution-record.js` ponytail at the `publishToRecord` scan). The cache is the middle step.
- `pin: NONE` — no probe asserts cache invalidation or the covering-index plan. A new `jobs_log` writer that skips `_jobsLogGen += 1` serves stale lists with no test failure; mutating a returned row poisons every later caller because the cache shares the row objects.
