# 20260824-c-probe-cage-argv-size — probe-cage-argv-size

kind: creation
component: server
date: 2026-08-24
commit: 02660b1a
deployed: no
pin: ignite/server/spawn/probes/probe-cage-argv-size.js

## Motivation

The auto-memory mask defect (`20260824-i-tmux-argv-ceiling-memory-mask`, `02660b1a`) had a failure mode no existing probe could catch: the composed cage was CORRECT and merely too long to speak. Every `server/spawn` probe asserts what a caged process sees or what a composer emits; none asserted anything about the SIZE of what `tmux new-window` is handed, so the defect stayed invisible until the host accumulated enough project stores to cross tmux's command-length limit — 696 stores and 68,503 bytes of argv against a ceiling measured at roughly 16 KB on this box. A defect that appears only on busy machines and vanishes on a clean `HOME` needs an assertion that does not depend on how busy the machine running the probe happens to be.

## Design

`ignite/server/spawn/probes/probe-cage-argv-size.js` builds a SYNTHETIC home holding a chosen number of project stores and measures the full launch composition against it. The synthetic home is the whole point of the shape: `composeAncestorMasks` already accepts a `home` parameter, so the probe can assert against 1000 stores — more than this box has ever had — on any machine, rather than asserting that today's host happens to fit. Store names are long and path-like (`-home-agent-ht-wkdir-second-brain-…`) because the real slugs are; a fixture of short names would understate the argv the defect produced.

Two assertions rather than one, and the pair is deliberate. A ceiling check alone would pass on a machine that simply has few stores; a constancy check alone would pass on a mask that is constant and enormous. Rejected: measuring `mask.flags.length` only, which would not have caught a regression that moved per-store cost into some other layer of the nesting; and asserting against the real `os.homedir()`, which makes the probe's verdict a property of the box.

## How it works

`tmuxCommandFor(fixture, home)` runs the real composition end to end — `composeSeatCage` -> `composeAncestorMasks` -> `specToBwrapFlags` -> `buildBwrapArgv` -> `buildScopeArgv` -> `tmux new-window` — and returns `tmuxArgv.join(' ')`, because a single joined string is what tmux's command-length limit is applied to. Leg 1 asserts that string under 8 KB with 1000 stores (measured 1,587 bytes; the pre-fix composer produced 118,899 on the same fixture). Leg 2 composes again at 10 stores and asserts the memory-mask flag count is identical and pinned at seven, and the byte delta is zero — pinning the NUMBER, not just its constancy, is what catches a fix that trades per-store flags for per-something-else flags. Leg 3 runs a real `bwrap` and reads back that the own store's transcript survives while its `memory/` and every foreign store do not, so an O(1) mask cannot buy its constancy by masking less. Leg 4 holds the absent-path discipline: a home with no project store composes no flags at all. The probe is discovered automatically by `probe-suite.js` (any `probe-*.js` under a `probes` directory) and needs no registration.

## Consequences

Replaces nothing; the `server/spawn` probe count goes 32 to 33. It creates a project-store directory under the synthetic home as a side effect of `composeMemoryMask` and removes its whole fixture root in `finally`. Leg 3 duplicates part of `probe-ancestor-mask` leg (e) on purpose — leg (e) measures the contract against the REAL store on the box, this one against a synthetic one at scale, and losing either loses a different half. Its first run found a real error in its own leg 2, which asserted six flags where the composition emits seven.

## Verification

`node ignite/server/spawn/probes/probe-cage-argv-size.js` prints ALL PASS (4 legs). Red-before was measured directly rather than assumed: the pre-fix `cage.js` was run against the same 1000-store fixture and produced a 118,899-byte tmux command, failing leg 1's ceiling and exceeding the real ~16 KB tmux limit. `node ignite/deploy/probe-suite.js --dir server/spawn/probes` discovers and runs it (33 discovered). Deployed: no.

## ATTENTION

- The synthetic home is not a convenience, it is the assertion. Re-pointing this probe at `os.homedir()` makes its verdict a property of how busy the box is, which is exactly the blindness that let the original defect ship.
- Leg 2 pins the flag count at seven. If the mask legitimately gains a mount, update the pin deliberately and say why in the leg — do not relax it to "small", which is what leg 1 already covers.
- Leg 3 must keep running a real `bwrap`. An O(1) mask that achieves constancy by masking less passes legs 1 and 2 silently, and only a read-back from inside the namespace distinguishes the two.
- The synthetic home is the assertion, not a convenience — re-pointing this probe at os.homedir() makes its verdict a property of how busy the box is.
