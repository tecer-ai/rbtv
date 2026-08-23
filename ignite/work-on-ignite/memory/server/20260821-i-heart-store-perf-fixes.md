# 20260821-i-heart-store-perf-fixes — Heart store perf fixes

kind: issue
component: server
date: 2026-08-21
commit: fecd3b6a,6fc989bc
deployed: yes
pin: NONE
seeded: true

## Seen
Full-history scans + a missing index were starving the gateway's event loop.

`heart-store.js`'s `listExecutionsByStatus` ran a full-history table scan on every call with no cache, and `jobs_log` had no index on (job_id, fired_at) — together these were starving the gateway's event loop (the "gateway stall").

## Missed
none recorded in sources — caching landed first, indexing landed as "the other half."

`6fc989bc` (caching) landed first the same morning; `fecd3b6a` (indexing) landed as "the other half" per its own commit message, implying the cache alone was known to be only a partial fix.

## Held
Cache listExecutionsByStatus; add the missing jobs_log index.

`6fc989bc` adds an in-memory cache to `listExecutionsByStatus` (41 lines); `fecd3b6a` adds the missing `schema.sql` index on `jobs_log(job_id, fired_at)`.

## commit
fecd3b6a,6fc989bc

## files
ignite/server/heart/heart-store.js; ignite/server/heart/schema.sql

## deployed
yes

## pin
NONE

## ATTENTION
- fecd3b6a's own commit message ("the other half of the gateway stall") signals this was a two-part fix landed as two commits — if only one of the two is ever reverted or migrated away from, the gateway stall it fixed can return partially.
- No dedicated pin — a future gateway-event-loop stall investigation should check both the cache (heart-store.js) and the index (schema.sql) before assuming a new cause.
- two-part fix landed as two commits; reverting only one can partially reopen the gateway stall
