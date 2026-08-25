---
description: Use when minting planning seats or birthing an execution goal through the supervised materialize door.
---

# planning

The planning-door lock, Path A mint, Path B birth, and supervised-materialize wrapper. Not a CLI — mint/birth import these modules.

| Part | One line |
|---|---|
| `lock.py` `take_lock` | Exclusive flock on `<goal>/planning/current/.materialize.lock`; same pass-id re-enters; distinct trigger refuses `lock-collision`; dead pid is stolen |
| `wrapper.py` `supervised_materialize` | Shared path-A/path-B wrapper: validate → uncast → scaffold (B) → lock → mint → release; five failure classes; no Slack |
| `wrapper.py` `uncast_in_sheet` | Refuse-before-write: any seat without harness+model refuses the whole act |
| `argv.py` `planning_mint_argv` | Path A argv: `--package` at the existing goal; never `--milestone-id`, never `--nested`, never full/collapsed |
| `path_a.py` `run_path_a` | Path A caller: uncast + wrapper + one materialize invocation |
| `path_b.py` `run_path_b` | Path B birth: validate-then-scaffold-then-mint; reclaim folder+catalogue on mint fail |
| `path_b.py` `main --package` | The daemon's entry into Path B: `server/heart/start-execution.js` writes the approve-package and runs this on the fourteenth gateway intent `start-execution` (owner ruling 2026-08-24 (b)) |
| `door.js` `runPlanningMintPass` | Goal-wide trigger: planning goal + five seats absent → mint once; already-minted is a quiet no-op |
| `pipeline-seats.json` | Mirror of the `plan-console` manifest's `Seat/workflow` column — the names already-minted is decided by; divergence = a forever re-mint |
| `materialize-seats.py` derived-tree refusal | The lane builder plants `DERIVED.md` at the `seat-lane/` root (`source: ..` = `planning/current/`, plus its regenerator); `_ref_target` and the five non-lane writers call coord's `refuse_if_derived`, so an `exposes` target or a seat surface resolving UNDER a marked derived root refuses `target-under-derived-tree` (C10). The lane REGENERATOR is exempt by construction — it stages and replaces the root rather than writing through a guarded door. spec-component-map §4 |
| `failure.py` | Record fields `origin`/`origin-id`/`class`/`code`/`subject`/`reason`; D12 approval-thread; D13 gate-lane `incomplete: materialize-failed` |
