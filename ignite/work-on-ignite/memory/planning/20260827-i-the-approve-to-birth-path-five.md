# 20260827-i-the-approve-to-birth-path-five — The approve-to-birth path, five refusals deep

kind: issue
component: planning
date: 2026-08-27
commit: cf79c881
deployed: no
pin: ignite/planning/probes/probe-planning-path-b-materialize.py
components: coord,meta-planning,meta-leader

## Observed

The acceptance wave's re-run #8 (`scratch-tool-inventory-8`, 2026-08-27) got the plan-console
pipeline through to a real approval for the first time — the leader bound `planning/` at a commit,
the verify seat wrote the approve-package, the approval thread reached Slack — and the owner's
`approve` produced no goal. The failure record on the planning goal
(`planning/current/materialize-failure.json`) read `class: roster-name-collision`,
`code: scaffold-refused`, reason
`refused: --contract planning/execution-contract.md: No such file or directory`. Nothing was named
`scratch-tool-inventory-8-exec` anywhere, so the class was wrong as well as the act. Behind that
first refusal stood four more, each of which would have fired in turn: the package had fallen back
to `lane: console` (a lane the daemon never adopts) because a daemon-lane scaffold was refused;
the mint would have asked for a workflow named `execute`, which exists in no catalog
(`meta/planning/workflows/` carries d13-replan, forge, plan-console); the catalog root defaulted to
the GOALS tree, which carries no staff component; and a birth against that default reports success
with no `leader` and no `goal-master` on the goal at all. Filed as
`G-leader-0827-{2224,2226,2256}` and, on the goal's own `issues.md`,
`G-plan-designer-0827-2230`. HEAD and deployed were the same commit (96732ef0) throughout;
`path_b.py` is read live by the daemon's `start-execution` executor as a subprocess, so no deploy
separated the two.

## Mechanism

Five independent causes on one path, each in `ignite/planning/path_b.py`.

`run_scaffold` composed `[--root, --json, scaffold, <name>, --contract, --lane]` and never
`--materialize-follows`. `goal_cli.py#cmd_scaffold` refuses `daemon-lane-unmaterialized` on a
daemon-lane goal without that flag, because `scaffold` writes no `taskforce.csv` and
`lane-watch.js#runLaneWatch` adopts a daemon-lane goal only when one exists. Path B DOES mint in the
same act — the flag is exactly the declaration it was built for — so the refusal was a true gate
firing on a caller that had simply never made its declaration.

`contract_file` was used BARE: `Path(pkg["contract_file"])`, a goal-relative path resolved against
whatever directory the daemon's python was started in, never joined to `planning_goal`
(`path_b.py:223` held that value one line above). And no seat wrote the file at all — the review
stage had assigned it to "the approving act", which has no authoring step.

`planning_mint_argv(workflow=pkg.get("workflow") or "execute", sheet=… or <new folder>/bindings.json)`
defaulted BOTH values to names that describe nothing: there has never been an `execute` workflow,
and a freshly scaffolded folder holds no `bindings.json`.

`catalog_root` defaulted to `goals_root`. `mint_staff_chairs` skips a chair whose row the catalog
does not carry — deliberately, so a fixture or foreign catalog renders as it always did — and the
goals tree carries no component catalog at all, so both chairs were skipped silently and the mint
still reported success.

Two more surfaced only once the path was walked end to end. A brand-new goal folder has no
`taskforce.csv`, so `plan_package_creation` refuses `create-inputs-missing` without `--claude-md`
and `--budget-json`; Path B named neither. And `--goal-local` SWAPS the catalog for a lane
synthesized out of the goal's own planning product, then hands that lane to `mint_staff_chairs` —
which therefore can never find a chair on a goal-local run. On a live goal that skip is invisible
(the chairs are already registered); on a birth it is the whole staff.

Finally `failure.py`: `run_scaffold` stamped every refusal it caught `roster-name-collision`,
the class of the one failure it had been written for.

## Attempts

First attempt held for four of the five — checked `git log -S` over `path_b.py`,
`argv.py` and `materialize-seats.py#mint_staff_chairs` back to `e9e0ac21` (2026-08-24, the Path-B
landing) and its memory entry `capabilities/20260824-c-path-b-execution-goal-birth-vi`. That entry
records the birth as verified by `probe-planning-path-b-materialize.py` EXIT 0 — and that probe was
RED at HEAD before this fix (P1 and P3), on the daemon-lane refusal, because `goal_cli`'s B12 gate
(`20260826-i-direct-created-daemon-goal-ski`) landed AFTER the probe's green was recorded and
nothing re-ran it against the new gate. The contract file had one prior trial that did not hold:
`ee4a0334` (2026-08-27, `meta-planning/20260827-c-the-plan-declares-its-birth-th`) added the
EXECUTION DECLARATION with `contract-file` as an optional field "where the plan names one", which
made the field expressible without making anyone responsible for the file. The catalog-root default
has a direct precedent that was never applied here: `919e1595`
(`meta-leader/20260822-i-retarget-catalog-root`) retargeted every catalog-root reader at
`rbtv.json`'s `rbtv_path` and its own ATTENTION names exactly this class — Path B was written two
days later and defaulted to a third value neither reader uses.

## Fix

`run_scaffold` passes `--materialize-follows`, and parses the refusal CODE out of goal_cli's
`--json` payload rather than guessing a class; `failure.class_for_code` maps it, with
`COLLISION_CODES` the narrow set whose subject is a name already held and `atomic-core-refusal`
everything else. The map lives in `failure.py` because both the scaffold arm and the mint arm read
it; a per-call-site literal is how the first one drifted.

The contract is resolved against the planning goal and read FROM THE BOUND COMMIT. `run_path_b`
now stages `plan_artifacts` as the bound tree holds it (`git archive <sha>:<rel>` into a temp dir,
extracted with tarfile's `data` filter) whenever the package names a `contract_file` or takes the
one-off route, and both readers read the staging. This is `artifacts_resolvable`'s discipline moved
one step, from "resolvable at that sha" to "read at that sha" — the working tree keeps changing
after an approval is sent, and the tree the owner approved is the tree the birth must build from
[T5-R5]. The matching refusal is at the WRITER: `approve_package.refuse_bad_contract_file` requires
`--contract-file` to be a file under `--plan-artifacts` (`bad-contract-file`), because a birth-time
refusal is an owner reading it in Slack with the approval already spent, while a writer-time refusal
is a seat still sitting.

For the mint, a package that declares NO workflow is now a ONE-OFF PLAN and takes the
`--goal-local` lane: the plan's own `planning/current/` is copied out of the bound tree into the
goal being born, and the mint reads it there. That ordering is what makes it legal — the Path-B
landing's own ATTENTION says the lane must never target a foreign goal, and after the copy the goal
it targets IS the born goal. Rejected: minting a catalog workflow that would have to be authored
per plan (nobody maintains it, and the plan already authored its seats); rejected: a second door for
one-off plans. `planning_mint_argv` gained `goal_local=` (which FORCES `--workflow goal-local`, so
the flag and the lane's one manifest name cannot disagree) and `creation_inputs=`, which names the
owner-approved starter set (`ignite/coord/starter-set/`) the way the creation route already does —
Path A passes neither, because it mints into a goal that already has a registry.

`catalog_root` defaults to the rbtv `meta` tree resolved through `rbtv.json`'s `rbtv_path`, the same
book `unbuilt-seats.js#repoRootOf` reads, so the two lanes that mint into a goal cannot address
different catalogs. `mint_staff_chairs` reads its chairs from `args.catalog_root` — the COMPONENT
catalog — whenever the run swapped to a goal-local lane, and clears `goal_local` on the chair
sub-run so it does not rebuild the lane and refuse. And `path_b.refuse_if_chairless` checks the
goal's own `taskforce.csv` after the real mint: missing `leader` or `goal-master` refuses
`birth-chairless` and the folder is reclaimed. The check is on the PRODUCT rather than the catalog
input, so it catches every reason a chair can be missing — no row, no casting sheet, a standing
ending — not only the one that was measured. It is not in `mint_staff_chairs` itself because that
function's silent skip is correct where it lives: a materialize against a fixture catalog must
render as it always did. A birth is the one caller for which it is fatal.

Last, `roster-not-in-plan` at the writer: on the no-workflow route every roster id must appear in
`<plan-artifacts>/current/manifest.csv`, an empty roster is refused, and a missing manifest is
refused. That closes `G-plan-designer-0827-2230` ("an empty roster births successfully") at the
writer rather than by making the birth tolerate it.

## Consequences

Nothing was deleted. `wrapper.py`, `goal_cli.py` and `start-execution.js` are byte-unchanged — the
birth was made to fit the doors it calls, never the reverse. `run_path_b` now returns `[]` for its
argv when validation refuses before the argv is built (it is built inside `_validate` so a catalog
root that cannot be derived is a RECORDED refusal rather than a traceback out of the subprocess);
every caller but the probes ignores that value. The staging costs one `git archive` per birth that
names a contract file or takes the one-off route, and nothing on the old catalog route.
`mint_staff_chairs` reading the component catalog on a goal-local run is a behaviour change for the
lane-watch repair path too: a live goal that somehow lacks a chair row will now have it minted
instead of silently skipped — which is the behaviour that function's own docstring already
described. `probe-approve-package.js`'s DERIVED-tree arm had to declare a `--workflow` to keep
isolating its own gate, because without one the new roster check refuses first, on a different fact.

## Verification

Offline, on a scratch vault under `/tmp` with its own `goals` parent and a planning goal whose
`planning/` (draft, review, `execution-contract.md`, `current/{manifest.csv,seats/<id>/…,bindings.json}`)
was COMMITTED — never the live goals root, never Slack. The writer wrote a `lane: daemon` package
with no workflow and a roster from the manifest; `run_path_b` then birthed the goal: folder created,
`goal.md` body byte-equal to the committed contract, `taskforce.csv` carrying
`scratch-builder,scratch-checker,leader,goal-master`, four seat folders, `execution-lane` reading
`daemon`. Six red arms, each on a fresh fixture: a contract outside `--plan-artifacts` and a named
contract that does not exist both refuse `bad-contract-file` with no package written; a roster id
the manifest lacks and an empty roster with no manifest both refuse `roster-not-in-plan`; a contract
present on disk but absent from the bound commit refuses `contract-not-in-bound-tree` with no goal
folder created; a catalog with no staff component refuses `birth-chairless` and the folder is
reclaimed. `probe-planning-path-b-materialize.py` went 2 RED → 8/8 PASS (P5 and P6 are new: the
one-off route's argv, the copy coming from the bound tree rather than the edited working tree, and
the catalog-root resolution plus its refusal). `probe-approve-package.js` 16/16 → 22/22 (C1–C6 new).
`probe-planning-path-b-failure.py` 1 RED → 3/3. `materialize-seats.py --selftest` 63/63 rows both
arms, 0 failed checks — identical to a run of the same suite from a worktree at 96732ef0.
`component_lint` over `meta/planning` and `meta/leader`: the same 5 and 2 findings before and after
(the HEAD worktree reports 2 extra `ws:`-prefix findings, an artifact of linting from /tmp that
`20260827-c-the-plan-declares-its-birth-th` already recorded). NOT DEPLOYED.

## ATTENTION

- THE MINT ARGV IS BUILT INSIDE `_validate`, NOT AT THE TOP OF `run_path_b`. It is there so a
  catalog root that cannot be derived becomes a recorded failure record instead of a traceback the
  daemon reads as `path-b-unreachable`. Hoisting it back "so the return value is always populated"
  moves that refusal outside the supervised wrapper, where nothing writes it down.
- `--goal-local` MUST STILL NEVER TARGET A FOREIGN GOAL. The lane is built at
  `<package>/planning/current/seat-lane/` from `<package>/planning/current/`, so the COPY into the
  born goal is what makes the flag legal here. An "optimization" that skips the copy and points the
  mint at the planning goal would build the execution team inside the plan.
- A CHAIRLESS BIRTH IS REFUSED AT THE PRODUCT, AND `mint_staff_chairs` STILL SKIPS SILENTLY. Both
  are deliberate: the minter must render a fixture catalog as it always did, and the birth must not
  hand the daemon a goal with no leader. Moving the refusal into the minter reddens every fixture
  that materializes against a catalog without a staff component.
- THE CONTRACT AND THE PLAN'S SEATS ARE READ FROM THE BOUND COMMIT, NEVER FROM DISK. A future editor
  who "simplifies" the staging away will silently start building goals from a working tree that has
  moved on since the owner approved it — which is unobservable in a green test and is the entire
  reason [T5-R5] exists.
- A BIRTH NEEDS `--claude-md`/`--budget-json` BECAUSE IT COMPLETES A BRAND-NEW PACKAGE. They are the
  owner-approved starter set (`d-owner-starter-set-approved-0808`), resolved repo-relative from
  `ignite/coord/starter-set/`. Never default them to invented content and never add them to the
  approve-package — a seat that names a goal's constitution is authoring one.
- path_b builds its mint argv inside _validate so an underivable catalog root is a RECORDED refusal, not a traceback
