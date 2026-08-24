# 20260824-i-lastcovering-ignored-the-compi — lastCovering ignored the compiler carve rules

kind: issue
component: server
date: 2026-08-24
commit: f6df6cae
deployed: no
pin: ignite/server/spawn/probes/probe-ancestor-mask.js

## Observed

A workspace the envelope compiler ADMITTED was refused by the mask composer. Measured 2026-08-24 by `impl-cage-argv-ceiling` on HEAD of `ignite/core-redesign` in the `rbtv-redesign` worktree: for a fixture workspace rooted under `/tmp`, `compile()` returned `ok` with 19 binds, and `cage.js#lastCovering(spec, workspaceRoot)` on that same bind list threw `E_LAUNCH_REFUSED: lastCovering mixed access at /tmp/…/work`. The symptom does not have a red probe of its own, which is the interesting part — it has a WORKAROUND instead, and the workaround is load-bearing enough to be documented in the file that carries it. `server/spawn/probes/lib.js` opens with a warning block forbidding fixture workspaces under `os.tmpdir()` or `/tmp`, states the exact error string, and roots every fixture at `/var/tmp` because "`/var/tmp` is in no baked family — that is the whole reason it is used here". `20260824-c-probe-fixtures-migrated-to-the` records ten fixtures migrated to satisfy it. Not deployed; the redesign branch is `deployed: no` throughout.

## Mechanism

spec-envelope §2 defines a conflict as two sources covering the same path at different access "and neither is an authorized carve", and `compiler.js#findConflict` implements exactly that: pairwise, skipping any pair `authorizedCarve` accepts. `lastCovering` answered the same question with a different and cruder rule — it collected every entry covering the target, set a flag if any was RW and another if any was RO, and threw if both flags were set. That is coarser in two independent ways. It has NO carve rules at all, so the two authorized carves the spec names (deny-list over vault-wide READ, daemon-owned records RO over goal-folder RW) and the three more the compiler implements (temp-floor carves under families 4 and 7 among them) are all invisible to it. And "some RW somewhere and some RO somewhere" is not "some RW covering some RO": it answers yes for lists in which no single pair conflicts.

The envelope template bakes `/tmp` and `{tmpdir}` into family 4 (`scratch-temp`) and family 7 (`benign-cache-config-temp`) as RW for every seat, while family 5 (`vault-wide-read`) binds `{workspace}` RO. A workspace under `/tmp` is therefore covered by an RW `/tmp` and an RO `{workspace}` at once. The compiler sees `wide.family` in `TEMP_FAMILIES` with `wide.access === 'rw'` and authorizes the carve; `lastCovering` saw one RW and one RO and refused. Two spellings of one rule, and this pair had drifted in the direction that refuses launches the compiler admitted. `bindsToSpec` was the reason the drift could not be repaired in place: it mapped each bind to `{verb, path}` and dropped `family` and `origin`, so by the time the spec reached `lastCovering` the information the carve rules turn on was gone — a `/tmp` opening is a carve because of the FAMILY that opened it, not because of how the path is spelled.

## Attempts

First attempt held as a FIX; the problem itself had been met before and routed around rather than repaired. Checked: `c9615ca2`, whose creation entry (`20260824-c-envelope-launch-refuse-and-inj`) already describes `lastCovering` as "a visibility query that throws on mixed access" and warns in its own ATTENTION "Do not re-run `conflictBind` over a compiled bind list: authorized temp-floor carves (workspaces under `/tmp`) look like covering conflicts" — the class was known at that sitting and the sibling predicate was not brought along. Checked `570131d9`, whose ATTENTION says "parent/child covering under `/tmp` (probe workspaces live there) is an authorized temp-floor carve, not `lastCovering`". Checked `ea10c914` and the other three commits behind `20260824-c-probe-fixtures-migrated-to-the`, which moved ten fixtures to `/var/tmp`: that is the avoidance, and it is why no probe went red. Checked `6b55b1c4`, which edited the neighbouring cover-verb excuse in `composeAncestorMasks` and did not touch the access rule.

## Fix

`f6df6cae` imports the rule instead of re-spelling it. `compiler.js` exports `authorizedCarve`; `lastCovering` becomes pairwise in the same shape as `findConflict`, skipping any differing-access pair the compiler would have authorized, and reports the offending PAIR (with its families) in `refuse.pair` while keeping the full covering list under `refuse.covering` for diagnosis. `bindsToSpec` now carries `access`, `family` and `origin` onto each spec entry; `specToBwrapFlags` reads only `verb`/`path`/`punchThrough`, so the extra fields reach the predicate and cost no argv. `compile()` adds `origin` to the emitted binds, which it had computed and then dropped.

Importing was chosen over three alternatives. Copying the carve table into `cage.js` reproduces the exact failure mode this entry documents, one drift later. Relaxing `lastCovering` to never throw was rejected because spec-envelope §10 lists "`lastCovering` as conflict resolver" as an ILLEGAL surface — the answer is that it must not RESOLVE conflicts, not that it must not notice them, and a launch whose bind list really does hold an unauthorized conflicting pair should still refuse. Loosening the fixture rule in `probes/lib.js` was rejected because the fixtures are not wrong: a real workspace under `/tmp` is legal to the compiler, so the composer must accept it.

Legacy specs are deliberately unaffected. `composeSeatCage` output and the probe templates carry no `family`/`origin`, so `authorizedCarve` finds nothing to authorize and their pre-existing refuse posture is byte-identical. Only compiler-composed binds, which alone know which family opened them, can carve.

## Consequences

The `/var/tmp` fixture rule in `probes/lib.js` is no longer load-bearing — it is now belt, not mechanism — but it was left in place and its comment left standing: removing it would be a fixture-wide migration in a file another seat is actively editing, and it costs nothing to keep. `refuse.pair` changes shape from "every covering entry" to "the two that actually conflict", and gains `family`; the full list moved to the new `refuse.covering` field, so any consumer reading `pair` as a complete inventory now reads two elements. `cage.js` gains a dependency on `ignite/envelope/compiler.js`, a new direction (`server/spawn` -> `envelope`) that `spawn.js` already travels; the require is top-level and introduces no cycle, since `compiler.js` reaches only `load-config.js` and `paths.js` and neither returns to `server/`. `private-scope.js` calls `lastCovering` twice and inherits the loosened predicate without change.

## Verification

`probe-ancestor-mask` leg (i) is new and is the assertion under the `probes/lib.js` workaround: it builds a fixture workspace deliberately rooted in `/tmp` — the shape the workaround exists to avoid — drives it through the REAL compiler, asserts the compiler admits it, asserts the covering set contains both a `bind` and a `ro-bind`, and asserts `lastCovering` returns rather than throws. Measured red before this commit (`E_LAUNCH_REFUSED: launch-refused: lastCovering mixed access at /tmp/anc-mask-carve-…/work`) and green after, with the pre-fix predicate spliced back onto the post-fix file to isolate it. `probe-ancestor-mask` is ALL PASS; `probe-private-scope`, `probe-private-scope-fresh`, `probe-seat-cage`, `probe-peer-identity`, `probe-worktree-flow` and `probe-envelope-walls` — the other `lastCovering` and cage consumers — all pass; `envelope-compiler`, `envelope-launch`, `envelope-shims` and `wall-report` selftests exit 0. Deployed: no.

## ATTENTION

- `lastCovering` must never carry its own copy of the carve rules. spec-envelope §2 makes `ignite/envelope/` the source of truth, and the one time this predicate re-derived them it refused workspaces the compiler had admitted — silently, because the only symptom was a fixture convention nobody read as a bug.
- The carve question is unanswerable from `{verb, path}`. If a future edit trims `family`/`origin` out of `bindsToSpec` as unused decoration, `authorizedCarve` sees `undefined` families, authorizes nothing, and the refusal returns in full.
- `lastCovering` still throws, and that is deliberate. spec-envelope §10 forbids it as a conflict RESOLVER, not as a detector; a bind list holding a genuinely unauthorized differing-access pair must still refuse the launch rather than fall back to later-wins.
- `refuse.pair` now holds exactly the two conflicting entries, not every covering one. A consumer that read it as the full covering inventory should read `refuse.covering` instead.
- The `/var/tmp` fixture rule in `probes/lib.js` is now redundant rather than required. Its comment still describes the defect as live; treat it as history, and do not conclude from it that the composer still refuses `/tmp` workspaces.
- lastCovering must never carry its own copy of the carve rules — spec-envelope §2 makes ignite/envelope/ the source of truth, and re-deriving them refused workspaces the compiler admitted.
