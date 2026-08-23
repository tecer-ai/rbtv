# 20260819-i-d3-fence-replaces-cage — D3 fence replaces cage

kind: issue
component: server
date: 2026-08-19
commit: ac4726a6,e37853b2,fb8db289
deployed: yes
pin: server/spawn/probes/probe-seat-cage.js; probe-cage-workspace-grammar.js
components: config,team-kit
seeded: true

## Seen
The bwrap anti-forgery cage was a repeated launch-death cause.

The old sandbox design was a heavyweight bwrap "anti-forgery cage" (`server/spawn/bwrap.js`, `cage.js`). Per the system-problems seed digest §4, the sandbox/cage was a repeated launch-death cause: cgroup/identity mismatches, then EROFS mkdir failures on a different path after an earlier fix landed.

## Missed
none recorded beyond the general cage-failure class (system-problems.md §4 "sandbox/cage denying observation or write").

## Held
Replace the cage with a thin "D3 fence" built on git worktrees.

`ac4726a6` replaces the cage with the "D3 fence" — a thinner sandbox model built on git worktrees rather than a full anti-forgery bwrap cage (`config/spawn-profiles.yaml` cut from 326 lines to a fraction; `cage.js`/`spawn.js`/`bwrap.js` all simplified, net negative ~96 lines). `e37853b2` rewrites `ignite/CLAUDE.md` to describe the fence, not the old cage. `fb8db289` fixes probes to assert the fence, not the retired cage.

## commit
ac4726a6,e37853b2,fb8db289

## files
ignite/server/spawn/cage.js; ignite/server/spawn/bwrap.js; ignite/server/spawn/spawn.js; ignite/config/spawn-profiles.yaml; ignite/team-kit/cagespec.py; ignite/team-kit/materialize-seats.py; ignite/server/spawn/probes/probe-seat-cage.js

## deployed
yes

## pin
server/spawn/probes/probe-seat-cage.js; probe-cage-workspace-grammar.js

## ATTENTION
- This is the FOUNDATIONAL sandbox-model change of the whole redesign — nearly every later server/spawn fix (truly-everything-master-cage, ro-mask-private-scope-fix, stools-undeclared-tool-refusal) builds on the fence, not the old cage. Any code or doc still describing a bwrap "anti-forgery cage" is stale against this commit.
- The fence was hardened repeatedly afterward — treat those later entries as the fence's CURRENT shape, this one as its origin only.
- foundational sandbox change; later fences build on this, not the old cage
- any doc/code still describing a bwrap anti-forgery cage is stale
