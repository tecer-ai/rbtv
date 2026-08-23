# 20260822-i-retarget-catalog-root — retarget-catalog-root

kind: issue
component: meta-leader
date: 2026-08-22
commit: 919e1595
deployed: yes
pin: NONE
components: capabilities,engine,config
seeded: true

## Seen
Every catalog-root reader still pointed at the mirror after `meta/` moved into the rbtv repo.

Companion to `20260822-c-home-leader-master-planning-ca.md`: once the leader/master-agent/planning catalogs moved to `3-resources/tools/rbtv/meta/` (commit 49c03d35), every reader that had hardcoded or defaulted to the `.rbtv/mirror/meta/` catalog root was stale — spawn profiles, the queue-request verb, bindings probes, and the master-profile tool default.

## Missed
none recorded in sources.

## Held
Retarget every catalog-root reader to the repo `meta/` via `rbtv_path`.

`capabilities/bindings/probes/probe-bindings.py`, `ignite/config/spawn-profiles.yaml`, `ignite/engine/queue-request.js`, and `capabilities/master-profile/tool/master_profile.py` (plus their probes and `ignite/team-kit/starter-set/CLAUDE.md`, `modules/ignite.md`, `ignite/engine/probes/probe-queue-request-pass.js`) now address `3-resources/tools/rbtv/meta` via `rbtv_path` instead of the mirror path.

## commit
919e1595

## files
ignite/config/spawn-profiles.yaml; ignite/engine/queue-request.js; capabilities/bindings/probes/probe-bindings.py; capabilities/master-profile/tool/master_profile.py; capabilities/goal-creation-request/goal-creation-request.md; capabilities/execution-mode-birth/probes/probe-execution-mode-birth.py; ignite/engine/probes/probe-queue-request-pass.js; ignite/team-kit/starter-set/CLAUDE.md; modules/ignite.md

## deployed
yes — effective on commit (JS/py read live per invocation, D6 exception).

## pin
NONE

## ATTENTION
- Any future catalog-root literal (a new reader hardcoding `.rbtv/mirror/meta/...` instead of resolving via `rbtv_path`) recreates this same staleness the moment `meta/` content changes only in the repo — resolve catalog roots through `rbtv_path`, never a hardcoded mirror path.
