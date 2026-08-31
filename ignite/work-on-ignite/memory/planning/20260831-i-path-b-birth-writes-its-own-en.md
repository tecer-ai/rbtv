# 20260831-i-path-b-birth-writes-its-own-en — Path-B birth writes its own envelope.json

kind: issue
component: planning
date: 2026-08-31
commit: 7d8cb4a2
deployed: no
pin: ignite/planning/probes/probe-planning-path-b-materialize.py
components: envelope
register-id: owner-flagged-birth-writes-no-envelope

## Observed
Owner-flagged 2026-08-30 (`owner-flagged-birth-writes-no-envelope`, filed by
`meet-transcript-summarizer-planning/goal-master`): nothing in the Path-B birth
(`ignite/planning/path_b.py#run_path_b`) ever wrote `<born-goal>/envelope.json` —
`envelope/launch.js#FILL_IN_NAME='envelope.json'`, and `loadFillIns` is the SOLE
reader, returning `null` when the file is absent and falling back to
`compilePlanning` silently. Grepping `ignite/` for writers of that filename found
only a selftest and two probes, none on the birth path. Compounding:
`path_b.py#goal_name_taken` refuses `name-exists` if the goal folder already
exists, so the file could not be pre-written before `approve` either — the
approval digest's own instruction to do so was unfollowable. The owner proceeded
by hand-writing the file post-birth (option a, a systemd-armed watcher
`land-envelope.sh`) and filed this as the durable fix (option b). Confirmed
independently by `meet-transcript-summarizer-planning`'s plan-drafter (IG-DR1)
and plan-verifier (approval digest, coordination msg #43).

## Mechanism
`approve_package.py`'s `OPTIONAL_KEYS` carries no fill-in field at all
(`namedRepos`/`projectFolder`/`credentialNames`/`extraPaths` are not among
`roster, contract, contract_file, workflow, sheet, catalog_root, git_dir,
envelope_stamp, planning_pass_id`) — the plan's write-grant fill-ins exist ONLY
as plan prose (draft-plan.md §13b) today, never as a package field the birth
could read. `path_b.py#run_path_b`'s `_mint()` minted seats/chairs and returned;
no step downstream of it ever touched `envelope.json`.

## Attempts
First attempt held — checked `20260824-c-plan-time-envelope-compiler.md`,
`20260824-c-envelope-launch-refuse-and-inj.md` and
`20260824-c-path-b-execution-goal-birth-vi.md`: the compiler and launch-consumer
sittings built `loadFillIns` as a pure reader by design ("Launch is the
consumer"), and the Path-B birth sitting never assigned itself the writer role —
none of the three claims to write `envelope.json`, so this is a gap between two
correct designs, not a regression of either.

## Fix
The plan may commit `<plan-artifacts>/envelope.json` (sibling of
`execution-contract.md`, at the plan_artifacts root) instead of a new
approve-package field: `bound_envelope_fillins` reads it with a single targeted
`git show <bound-commit>:<rel>/envelope.json` (never the working tree, [T5-R5],
the same discipline `bound_contract_file` already applies) — a `git show`, not
`stage_plan_artifacts`'s full `git archive`, because most one-off plans declare
no write grant at all and paying a full-tree extraction to test one optional
file is the cost the staging design already rejected. Rejected: a new
`approve_package.py` field carrying the fill-ins inline — `approve_package.py`
is outside this fix's walls, and a plan-authored JSON artifact bound at the same
commit as the contract needs no new writer-side validation surface at all.

`_land_envelope` (new, called from `run_path_b`'s `_mint()` for both the real
subprocess mint and an injected test stub) runs the fill-ins through the
DEPLOYED `envelope/compiler.js#compile()` shape via `compile_check_envelope` —
mkdir'ing `{goal}/scratch` and `{workspace}/.rbtv/runtime/ignite` first, the
same ordering `envelope/launch.js#admitLaunch`'s own `ensureGoalScratch`/
`ensureEndingStore` calls document as load-bearing, measured directly (compile
refused `unresolved …/.rbtv/runtime/ignite` on a fixture missing that mkdir). A
refusal raises `MaterializeFailure(CLASS_ENVELOPE_REFUSAL, "envelope-fillins-refused", …)`
— `_mint()` runs after `scaffolded=True` is already set in
`supervised_materialize`, so the raise reclaims the folder exactly as a
chairless mint already does. `write_envelope_if_absent` uses `O_CREAT|O_EXCL`
rather than `tmp+rename`: `land-envelope.sh` (the hand-armed watcher for the one
goal blocked on this defect) may still be racing the birth, and a plain
`tmp+rename` unconditionally replaces whatever is at the destination — exactly
the clobber this must not do. `_land_envelope` also checks `dest.exists()`
BEFORE the compile-check, so a file already sitting there is never judged by
whether the plan's own fill-ins would compile — it is left untouched either way,
and the birth never reclaims over a fillins refusal when a valid file already
stands.

`meta_catalog_root` was refactored to share its `rbtv.json`-through-the-book
resolution (`_rbtv_repo_root`) with the new compile-check, so the two can never
resolve different rbtv repo roots for the same package; `stage_plan_artifacts`
was refactored to share its repo/rel derivation (`_bound_repo_and_rel`) with
`bound_envelope_fillins` for the same reason. Neither changed behaviour.

`envelope/launch.js#loadFillIns` now warns once to stderr when a goal has no
`envelope.json` AND carries `planning/bound-plan.json` (`path_b.py`'s own
`BOUND_PLAN_NAME`, stamped on every Path-B birth and no other goal shape) — the
one signal available in `launch.js` to tell a Path-B-born goal apart from a
planning goal or a fixture. A goal with no such marker (any other shape) stays
silent, unchanged.

## Consequences
`approve_package.py`, `goal_cli.py`, `materialize-seats.py` and `compiler.js`
are byte-unchanged — the birth was made to read an artifact the plan may now
commit, never the reverse. A plan that declares no write grant still births
exactly as before (no `envelope.json` in the bound commit → `_land_envelope`
returns immediately, no scratch/ending-store mkdir, no node invocation, no cost
paid). The one pending live approval this defect blocked
(`transcript-summarizer-build`, package at
`meet-transcript-summarizer-planning/planning/approve-package.json`) still has
NO `planning/envelope.json` bound at its commit — this fix does not retroactively
help that approval; someone must commit one there (content per draft-plan.md
§13b) before the next `approve`, or the goal-master's own `land-envelope.sh`
watcher remains its path.

## Verification
Offline only, no live birth, no goal created under the real goals tree.
`python3 -m py_compile ignite/planning/path_b.py` exit 0.
`node --check ignite/envelope/launch.js` exit 0.
`python3 -B ignite/planning/probes/probe-planning-path-b-materialize.py`: 6/6 →
9/9 PASS (P7 envelope compiles + `loadFillIns` reads it back non-null; P8
envelope refuses at compile → `class: envelope-refusal`, folder absent; P9
pre-existing `envelope.json` left untouched, birth still succeeds). Both P7 and
P8 confirmed RED by mutation (short-circuiting `_land_envelope`), P9 stayed
green under the same mutation (proving it does not depend on the write path),
byte-identical file restored after (`diff` clean).
`python3 -B ignite/planning/probes/probe-planning-path-b-failure.py` 3/3 PASS,
unchanged. `node ignite/envelope/envelope-launch.selftest.js`: added
`PASS path-b-born-warns-once` (warns once when `planning/bound-plan.json`
present and `envelope.json` absent; silent when the marker is absent), confirmed
RED by short-circuiting the new branch, byte-identical file restored after.
`node ignite/envelope/{envelope-compiler,envelope-shims,wall-report}.selftest.js`
all still PASS. `component_lint --component ignite/planning` and
`--component ignite/envelope`: identical finding counts before/after (11/10 and
5/3 respectively) — both runs pre-existing, neither file I touched appears in
either. `materialize-seats.py --selftest` and
`ignite/planning/probes/probe-approve-package.js` both fail identically on
unmodified HEAD (an environment gap needing a real workspace install marker,
confirmed via `git stash`) — pre-existing, not caused by this change.
NOT DEPLOYED: the live daemon boots `ignite/state-store/heart/start-execution.js`
from the deploy worktree (`/home/henri/.local/state/rbtv-deploy`, HEAD
`fb16f975`, an ancestor of this commit's parent), which resolves `PATH_B_PY`
relative to its own `__dirname` — a deploy sync plus daemon restart is required
before this is live; neither performed here (owner's/daemon-owner's step, three
live goals paused on it).

## ATTENTION
1. THE ENVELOPE ARTIFACT IS READ FROM THE BOUND COMMIT, NEVER THE WORKING TREE —
   same [T5-R5] discipline as the contract. A future editor who reads it off
   disk instead reintroduces the exact race `stage_plan_artifacts`/
   `bound_contract_file` already exist to close.
2. A FILE ALREADY AT THE DESTINATION IS NEVER JUDGED BY COMPILING THE PLAN'S
   OWN FILL-INS. `_land_envelope` checks `dest.exists()` BEFORE the
   compile-check for exactly this reason — moving the compile-check first would
   make the birth reclaim a folder over a fill-ins refusal even when a valid
   hand-placed or watcher-landed file already stands there.
3. SCRATCH AND THE ENDING STORE MUST BE MKDIR'D BEFORE `compile()` RUNS, at
   birth exactly as at launch — `compile_check_envelope` duplicates
   `admitLaunch`'s own `ensureGoalScratch`/`ensureEndingStore` ordering
   deliberately; do not "simplify" it away, the compiler refuses `unresolved`
   on a fresh goal or a fresh workspace without it regardless of the plan's
   fill-ins.
4. `_land_envelope` RUNS FOR AN INJECTED `mint=` STUB TOO, not only the real
   subprocess mint — it sits after the `if mint is not None: … else: …` fork in
   `_mint()`, not inside either branch. Moving it back inside the else-branch
   would silently stop every probe using a mint stub from exercising it.
5. THE PENDING `transcript-summarizer-build` APPROVAL IS NOT FIXED BY THIS.
   Its bound commit carries no `planning/envelope.json` — this closes the
   mechanism, not that specific goal's missing artifact.
- The envelope artifact is read from the bound commit, never the working tree
- A file already at the destination is never judged by compiling the plan's own fill-ins
