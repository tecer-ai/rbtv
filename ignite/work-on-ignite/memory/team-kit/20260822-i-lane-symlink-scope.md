# 20260822-i-lane-symlink-scope — lane-symlink-scope

kind: issue
component: team-kit
date: 2026-08-22
commit: d487c072
deployed: yes
pin: NONE
seeded: true

## Observed
At 2026-08-22 15:30Z every seat launch into the `meet` goal died on the leader (exec 31384, exit 1). bwrap refused with `Can't bind mount … seat-lane/.git: No such file or directory`. That path is the goal-local lane `build_goal_local_lane` writes under `<goal>/planning/current/seat-lane/`. The window opened 26 minutes earlier: `919e1595` (15:04:50Z) retargeted catalog-root from `.rbtv/mirror/meta` onto `3-resources/tools/rbtv/meta` inside the rbtv git repo. team-kit Python is live-tree, so HEAD and deployed are this same file; the filter `d487c072` added is still the loop inside `build_goal_local_lane`.

## Mechanism
`build_goal_local_lane(package, component_root)` (landed 2026-08-17 as `deb1c9b4`) synthesizes a catalog under `planning/current/seat-lane/` and, so `_ref_target` can resolve a goal-authored `exposes:` of the form `module/component/part`, symlinks every sibling of `component_root` into that tree. The generator was `for mod in sorted(p for p in component_root.parent.iterdir() if p.is_dir())`, skipping only `GOAL_LOCAL_MODULE`. That was safe while the parent was the mirror (no `.git`). After `919e1595` the parent is the rbtv repo root, so `.git`, `.pytest_cache`, and `__pycache__` became siblings and were linked in. The cage's `**/.git` private-scope mask then asked bwrap to bind-mount a cover onto `seat-lane/.git`; bwrap cannot cover a symlink dest that is not a directory, and the launch itself failed for every seat using a goal-local lane.

## Attempts
First attempt held — checked: `git log -- ignite/team-kit/materialize-seats.py` before `d487c072` (newest prior on the file is `0563266b` at 14:56:54Z, D86 discovery share, unrelated to the loop); `deb1c9b4` introduced the sibling loop to fix a different refusal (`exposes-ref-dangling` when the lane sat one level too high) and did not anticipate a repo-root parent; map.csv `missed_trials_source` is empty; the seeded Missed section carried no earlier trial.

## Fix
`d487c072` (15:45:34Z) kept the `deb1c9b4` sibling-symlink design and narrowed the generator to `p.is_dir() and not p.name.startswith('.') and p.name != '__pycache__'`. Denylist, not an allowlist of module names: the set of modules an `exposes:` may reach is open; the non-module directory shapes at a repo root are known and few (`.pytest_cache` is a dotdir; `__pycache__` is not, so it is named). No D-id or E-id governs this. The eight-line comment at the loop is the hazard record; no probe was added.

## Consequences
No later commit has touched `materialize-seats.py` — `d487c072` is still the file's tip. The same sitting removed three already-materialized symlinks from the live `meet` lane by hand; that cleanup is not in the diff and was not applied to any other goal. The lane is a derived index rebuilt on every invocation, including `--dry-run` (block comment above `GOAL_LOCAL_SOURCE`), so a later materialize after this commit rewrites a stale lane without the bad links. The paragraph immediately above the new comment still names `.rbtv/mirror/meta` as `component_root` — leftover from `deb1c9b4`, not updated. No other memory entry cites `d487c072` or `build_goal_local_lane`.

## Verification
`d487c072` added no selftest and no probe (`pin: NONE`). The existing GL-1 arm of `run_selftest` (`g_ok` / `g_rw`, `--goal-local` against `build_fixture`'s catalog in a `TemporaryDirectory`) never sees a `.git` sibling, so it would have stayed green with the unfiltered loop. Proof is the measured meet-leader failure plus the live-tree save at 15:45:34Z; `deployed: yes` is that save, not a later daemon deploy.

## ATTENTION
- After `919e1595` the parent of `component_root` is the rbtv repo root. Widening `build_goal_local_lane`'s sibling loop back to every directory re-links `.git` into `seat-lane/`; the cage `**/.git` mask then asks bwrap to bind-mount a cover onto a symlink and every seat launch into the goal dies (meet leader, 2026-08-22 15:30Z, exec 31384).
- The comment immediately above the MODULE DIRS ONLY block still says `component_root` is `.rbtv/mirror/meta`. That describes the pre-`919e1595` tree; treating it as current makes the filter look redundant.
- `__pycache__` is named because it does not start with `.`; `.pytest_cache` is covered by the dotdir skip. Dropping either arm shares bytecode or pytest cache across goals via the lane.
- GL-1 (`g_ok`/`g_rw` via `build_fixture` in a `TemporaryDirectory`) will not fail a re-widened loop. `pin: NONE` — there is no regression probe.
