# 20260821-i-stools-undeclared-tool-refusal — Stools undeclared tool refusal

kind: issue
component: server
date: 2026-08-21
commit: 7f6eaf3e,9060c3cc
deployed: yes
pin: server/spawn/probes/probe-master-cage.js; probe-exposed-cli-secrets.js
seeded: true

## Seen
Undeclared tools raised a raw PermissionError instead of a named refusal.

Per the system-problems digest §4, undeclared-but-reachable tools (stools — the file-transfer tool, sd-graph, gtools) raised a raw, unnamed PermissionError instead of a recognizable refusal (41 log hits) — "the owner's own Slack door could not receive a file handoff" because the failure gave no actionable signal.

## Missed
none recorded in sources.

## Held
A named refusal class for undeclared tools, pinned by a red-control test on the master cage.

`7f6eaf3e` adds a NAMED refusal class in private-scope.js/spawn.js for any undeclared tool a seat tries to reach; `9060c3cc` adds a "red control" test arm to probe-master-cage.js that specifically pins the stools pierce (proving the wide master cage from `truly-everything-master-cage` doesn't silently let stools through undeclared).

## commit
7f6eaf3e,9060c3cc

## files
ignite/server/spawn/private-scope.js; ignite/server/spawn/spawn.js; ignite/server/spawn/probes/probe-exposed-cli-secrets.js; ignite/server/spawn/probes/probe-master-cage.js

## deployed
yes

## pin
server/spawn/probes/probe-master-cage.js; probe-exposed-cli-secrets.js

## ATTENTION
- The "red control" arm in probe-master-cage.js is DELIBERATELY a negative test (proves refusal fires) — if it ever passes for the wrong reason (e.g. the tool call errors before reaching the refusal check), that's false confidence; verify the refusal message itself, not just a non-zero exit.
- This closes the SAME class of raw-PermissionError failure the Slack file-handoff bug hit — any new tool exposed to a caged seat needs an explicit declaration or it re-triggers this class.
- red-control arm is a negative test; verify the refusal message fires, not just non-zero exit
- any new tool exposed to a caged seat needs explicit declaration or reopens this class
