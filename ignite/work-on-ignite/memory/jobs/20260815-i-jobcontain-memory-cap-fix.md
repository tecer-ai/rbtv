# 20260815-i-jobcontain-memory-cap-fix — Jobcontain memory cap fix

kind: issue
component: jobs
date: 2026-08-15
commit: f79bcdec
deployed: yes
pin: NONE
seeded: true

## Seen
goal-watcher-job died silently under jobcontain's 256MB cap, undetected for 4 days.

`ignite/jobs/goal-watcher-job.py` (the daemon job that watched goal health) was dying silently under `jobcontain`'s 256MB memory cap; the job itself never observed its own crash, so it kept believing it was healthy for 4 days before anyone noticed the ignorance.

## Missed
none recorded in sources.

## Held
jobcontain now observes and reports a cap kill instead of disappearing silently.

`jobs/jobcontain.py` (the wrapper that enforces the memory cap on daemon jobs) gained an observation path that reports a cap kill to its parent instead of silently disappearing; a new probe `jobs/probes/probe-jobcontain-uncapped.py` pins the behavior. Also touched: `config/spawn-profiles.yaml`, `jobs/README.md`, `jobs/goal-watcher-job.py`, and the `daemon-watchdog` capability's tool/doc.

## commit
f79bcdec

## files
ignite/jobs/jobcontain.py; ignite/jobs/goal-watcher-job.py; ignite/jobs/probes/probe-jobcontain-uncapped.py; ignite/config/spawn-profiles.yaml; ignite/jobs/README.md; core/capabilities/daemon-watchdog/tool/rbtv-ignite-watchdog; core/capabilities/daemon-watchdog/daemon-watchdog.md

## deployed
yes

## pin
NONE

## ATTENTION
- `goal-watcher-job.py` itself was later deleted entirely (2026-08-21, commit `9c3aee33` — see the `jobs` creation/change entry `delete-goal-watcher-job`) — this fix's original target file no longer exists; the surviving value is `jobcontain.py`'s cap-observation behavior, which now guards whatever daemon job runs under it.
- `probe-jobcontain-uncapped.py`'s location matters for scheduling — the daemon's scheduled probe-suite only auto-discovers `probe-*.js`/`probe-*.py` inside a directory literally named `probes/`; verify it still sits there before assuming it runs on schedule.
- goal-watcher-job.py deleted 2026-08-21 (9c3aee33); surviving value is jobcontain.py cap-observation
- probe-jobcontain-uncapped.py must live under a probes/ dir to be scheduled
