# 20260824-c-planning-door-lock-and-wrapper — planning-door lock and wrapper

kind: creation
component: team-kit
date: 2026-08-24
commit: 9dcfdf44
deployed: no
pin: ignite/planning/probes/probe-planning-lock.py

## Motivation
C5 planning non-termination is the IE-2 splice: the old door re-nests planning into the same goal with no lock on `planning/current/` and no supervision of materialize failures. spec-planning-door §3–§4 required two new foundations before mint/birth can call them — a mechanical lock and a supervised-materialize wrapper that writes a C-16 failure record instead of fire-and-forget.

## Design
Three sibling modules under `ignite/planning/`, one responsibility each, rather than growing `queue-request.js` or `materialize-seats.py`. The lock holds the lock-file inode (exclusive `flock`, never `tmp + os.replace`) because that is the same-inode discipline `_rewrite_in_place` already proved on bind-mounted goal files. Holder identity is the planning-pass id: same-pass re-entry is not a collision; a distinct trigger while held refuses and does not queue. Staleness is a dead holder pid only — getting the flock after the OS released it is a steal, not C-16. No wall-clock timeout. The wrapper is a skeleton: callers inject validate / scaffold / mint; order is validate → (path B) scaffold → lock → mint → release. Envelope refusal is consumed as the `failed: launch-refused` stamp input. Slack is not this module. Ending-store WRITE is not merged; the gate-lane stamp uses the session-close fallback (`incomplete` on `sessions.csv` plus a sidecar carrying `incomplete: materialize-failed`) with a marked handoff for impl-state-store.

Rejected: a JS lock (path B is Python and flock already lives in the kit), a queued second materialize, and inventing an ending-store writer ahead of impl-state-store-core. The marked handoff for that store is in `failure.py` (`impl-state-store`).

## How it works
`take_lock(goal, planning_pass_id)` creates `<goal>/planning/current/` if needed, opens `.materialize.lock` in place, and takes `LOCK_EX|LOCK_NB`. Same pass-id in-process re-enters; a live distinct pass raises `LockCollision` (`lock-collision`). `supervised_materialize` is the call interface mint and birth use. On any of the five classes it writes the six-field record (`origin`, `origin-id`, `class`, `code`, `subject`, `reason`) and, for `origin=gate-lane`, stamps the lane. D12 (`approval-thread`) writes the record only — there is no execution goal to stamp.

## Consequences
Nothing deleted. `GOAL_LOCAL_SOURCE` stays `("planning", "current")`. `queue-request.js` and `cmd_scaffold` are untouched — mint and birth wire the call sites. `ignite/module.md` has an uncommitted planning row mixed with other in-flight seats; this creation did not pathspec-commit that shared file.

## Verification
`python -B ignite/planning/probes/probe-planning-lock.py` exit 0 (P1 second call `lock-collision`; P2 first holder finishes; P3 same-pass re-entry; P4 steal). `python -B ignite/planning/probes/probe-planning-failure-record.py` exit 0 (five classes, six fields, approval-thread vs gate-lane, session-close fallback stamp). `py_compile` on every new `.py` exit 0. Not deployed.

## ATTENTION
- Do not `tmp + os.replace` the lock file — the live identity is the inode, same reason as `_rewrite_in_place`.
- Same planning-pass id is the same holder. Treating review→draft relaunch as a second trigger re-opens C-16.
- A steal of a dead-pid lock is not a collision. Do not add a wall-clock timeout.
- Gate-lane `incomplete: materialize-failed` is a sidecar + `sessions.csv` `incomplete` until impl-state-store's write API exists (marked handoff in `failure.py`). Do not Slack-post from the wrapper.
- Do not tmp+replace the lock file — inode is the live identity
- Same planning-pass id is the same holder; a steal of a dead pid is not C-16
