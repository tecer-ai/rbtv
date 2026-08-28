# 20260828-c-the-planning-mint-pass-an-admi — The planning-mint pass: an admission key with no producer

kind: change
component: planning
date: 2026-08-28
commit: 9a083777
deployed: no
pin: ignite/planning/probes/probe-queue-request-pass.js
components: runtime

## Motivation

The planning door's per-tick mint pass was DEAD CODE that read as a live repair path. Bounded by
the role-action program's acceptance wave test 17 (`bound-direct-create`, issue G-channel-master-
0825-2213), whose suggested option 1 leaned on it: a daemon-lane goal created without a taskforce
would, the issue reasoned, be repaired by the door on the next cadence. It would not. The pass
admitted a goal ONLY when its `goal.md` frontmatter carried `role: planning`, and nothing has ever
written that key. The one producer of goal frontmatter, `operator/goals-tree/tool/goal_cli.py`
`cmd_scaffold`, builds a six-key dict — `name`, `creation-date`, `due-date`, `type`, `goal-kind`,
`status` — and no route anywhere writes a `role` key at all; a grep of `ignite/` and `meta/` for
`role: planning` at `28ad5a22` returned the admitting regex, one README sentence describing it, and
nothing else; no live goal under `.rbtv/goals/` carries the key; and the string `planning-mint`,
which every one of the pass's own log lines starts with, appears 0 times in 592,458 daemon journal
lines. The pass ran twice per ~10s cadence (boot plus interval), before the lane watch, for as long
as the daemon has existed, and could never fire.

The trigger the spec actually names — `redesign/specs/spec-planning-door.md` §1: "a planning goal
exists AND its five pipeline seats are not yet minted" — is satisfied AT BIRTH, not on a cadence, and
already was: `operator/goal-creation-request/tool/goal_creation_request.py` `create()` runs
`scaffold-seats --workflow plan-console` unconditionally in the same act that scaffolds the goal
(the two input refusals were moved ahead of the scaffold at `4ed8acc8` precisely so that call is
unconditional), and the direct route now refuses `daemon-lane-unmaterialized` before its first write
rather than producing an unminted daemon goal.

## Design

Delete the mechanism, keep the trigger's answer where it already is. This is a deviation from
spec-planning-door §1's MECHANISM only, recorded by the role-action program's orchestrator in its
`decisions.md` and reversible by git.

Writing the missing key was the alternative, and it was rejected on the same evidence that condemns
the pass: with the creation route minting at birth and the direct route refusing, there is no
production route that produces a daemon-lane planning goal with unminted seats, so a `role: planning`
key written by `cmd_scaffold` would give the pass an admission it still had nothing to do with. It
would also add a seventh frontmatter key with one reader, on a projection (`goals.csv`) that fails
the whole tree on an unparseable `goal.md`. Minting at the creation route instead of deleting was
rejected for being what the route already does.

Keeping the pass "just in case" was rejected as the exact defect being fixed: the wave's finding was
not that the pass misbehaves but that its presence made an unreachable repair path read as live, and
the issue's own repair option was built on that misreading.

The deletion's blast radius was walked symbol by symbol rather than by file. `runPathA` and
`planningMintArgv` had no caller but the pass. `taskforceRows` had exactly one. `runQueueRequestPass`
was a wrapper whose whole body was the pass, and it was in turn the ONLY caller of
`resolveCatalogRoot` — a 36-line resolver with four typed refusal codes that the deletion orphans, so
it goes in the same change rather than becoming dead code this fix created. `PLANNING_CODE` existed
only for that resolver's bindings-sheet path.

## How it works

`ignite/planning/door.js` is now the pipeline-seat MIRROR and nothing else: it loads
`pipeline-seats.json` into `PLANNING_SEATS` and exposes `pipelineMinted(rows)`, the one executable
statement of what "minted" means (every name in the mirror is a `seat` row on the goal's
`taskforce.csv`). Both survive because their subject is live: `argv.py` reads the same json for
`PLANNING_SEATS`, its `--seats-json` flag and `path_a.py`'s uncast set. The file keeps the name
`door.js` because `planning/exposure.csv` exposes it by path and a dangling `exposes` path shuts
seat minting at every door (`20260827-i-dangling-embed-search-ref-block`, `20260827-i-two-dangling-
path-exposures-sh`); its header comment now states in full what the file was, why the pass went, and
what still reads the json.

`ignite/planning/queue-request.js` keeps the `plan-console` module/component/workflow constants, the
`Refusal` class, `planningManifestPath`/`planningManifestSeats`, and the re-export face of
`./unbuilt-seats` — `supervisor/lane-watch.js` requires `buildUnbuiltSeats` from this path and is
untouched. Its module selftest still deep-equals the manifest column against `PLANNING_SEATS`; only
the `planningMintArgv` argv assertions went, with the function.

`ignite/runtime/index.js` loses the require, the `queueRequestPass` closure and both call sites (boot
and interval). A comment block stands where the closure was, stating that the pass is gone, why its
key had no producer, and that the lane watch's `no-taskforce-yet` warn is the whole remaining answer
for a daemon goal that arrives without a taskforce.

`ignite/planning/probes/probe-queue-request-pass.js` keeps leg M whole — four checks, all derived
from the checked-in `meta/planning/workflows/plan-console/plan-console.csv`, including the reflexive
grep of the probe's own source that fails if any leg hand-types a seat id — and replaces the thirteen
pass legs with leg D, which greps `door.js`, `queue-request.js` and `runtime/index.js` for each of ten
deleted symbols, for a surviving `role:` read outside comments, for the absent require and call sites,
and asserts `buildUnbuiltSeats` is still exported. The probe's header names every removed leg by its
old check string, so a reader of the `.out` file learns the coverage was removed deliberately.

## Consequences

`path_a.py` now has no code invoker. It survives on disk as a standalone CLI, exposed as
`planning-path-a` in `planning/exposure.csv`, and `argv.py` — its argv builder — stays fully live
because `path_b.py` imports `planning_mint_argv` for execution-goal birth. Whether Path A itself
should be retired is a separate ruling and was deliberately left alone: `path_a.py` and `argv.py`
were outside this change's write surface, and retiring a file that an exposure row names is the
dangling-ref hazard above. This is the change's one loose end and it was surfaced, not captured.

The four `queue-request-workspace-*` / `queue-request-catalog-root-absent` /
`queue-request-bindings-sheet-absent` refusal codes no longer exist anywhere in the tree; a grep
confirmed they were named nowhere outside the function that threw them. `MATERIALIZE_PY` and
`SUBPROCESS_TIMEOUT_MS` remain declared and unused in `queue-request.js` — duplicates of
`unbuilt-seats.js`'s own, dead already at `28ad5a22` and left alone as pre-existing.

`ignite/module.md` still describes `planning/` as "Planning-door Path A mint + lock + supervised
wrapper (goal-wide trigger, …)". The phrase is now only half true and the file was left untouched
because it is a contended shared surface with sibling hunks from other components — surfaced as a
loose end.

Docs moved in the same change: `planning/component.md`'s `door.js` and `pipeline-seats.json` rows,
`planning/README.md` (a new paragraph stating there is no per-tick mint pass and why, the `door.js`
module row, and the minted-definition paragraph, which had asserted the `role: planning` definition
as fact), the `planning-door` and `planning-queue-request` description cells in
`planning/exposure.csv`, and `runtime/exposure.csv`'s daemon description, which listed
"queue-request pass" among the cadence loop's passes.

## Verification

Commit `9a083777` on `ignite/core-daemon`, by explicit pathspec — `git show --stat` carries exactly
the eight intended files and no sibling session's hunks (`runtime/gateway/parse.js`,
`internal-api/*` and `supervisor/*` were dirty from a parallel seat throughout and are not in it).

Before and after on the same machine, 2026-08-28: `probe-queue-request-pass` went 22 legs / RESULT
PASS / EXIT 0 → 17 legs / RESULT PASS / EXIT 0. `node ignite/planning/queue-request.js` prints
`queue-request selftest OK`, exit 0, both sides. `probe-daemon-lane-watch` is byte-identical in
verdict: 82 green arms, 1 FAIL, EXIT 1, the same pre-existing `L9 M9` red. The five planning Python
probes (`probe-planning-lock`, `-failure-record`, `-path-b-failure`, `-path-b-materialize`,
`probe-d13-verify-notify`) and `probe-approve-package` all exit 0 before and after; `python3 -m
py_compile` is clean on every planning `.py`; `node --check` is clean on all four edited `.js`.

Leg D was proven to have TEETH rather than merely passing: a mutant copy of the whole `ignite/` tree
under `/tmp` that re-inserted `ROLE_RE` + `isPlanningGoal` into `door.js` and `queueRequestPass();`
into the daemon loop turned three D arms red (`D isPlanningGoal is gone`, `D door.js reads no role:
frontmatter key`, `D the daemon neither requires nor calls the pass`) while the surviving arms held.

The tick loop still composes, proven WITHOUT booting the daemon: `require`-ing `runtime/index.js`
calls `main()` at module scope and actually starts a daemon (it was run once by mistake during this
work, aborted at the absent `ignite/config/spawn-profiles.yaml` with exit 1, wrote nothing — the
install-state files under `.rbtv/modules/ignite/` kept their prior mtimes and the live unit's MainPID
was unchanged). The replacement check resolves every top-level `require()` specifier of
`runtime/index.js` and asserts every destructured name exists on the resolved module: 25 specifiers,
all resolved, all names present. `tmux list-sessions` is byte-identical before and after
(sha256 `a6ff557099f3a57a97d6fceb4c57bff5289e825ff255ee18400b7d78fd93d4c2`).

NOT DEPLOYED. `runtime/index.js` and `planning/*` are boot-loaded from the deploy worktree
`/home/henri/.local/state/rbtv-deploy`, so this needs a DAEMON restart to take effect; the seat was
walled from restarts and deploys. Nothing wakes on that restart because of this change: what it
removes is a pass that has never once acted on any goal.

## ATTENTION

- `role:` is NOT a goal.md frontmatter key and never was. `goal_cli.py#cmd_scaffold` writes six keys
  and no route writes a seventh, so any code, prose or repair plan that keys on `role: planning` is
  keying on nothing. The trap is that the key reads like an established field because door.js's
  regex, the README and the spec all spoke it — three surfaces agreeing with each other and with no
  producer.
- A daemon-lane goal with no `taskforce.csv` has ONE answer and it is not in this component: the lane
  watch names it (`no-taskforce-yet`) and the fix is `scaffold-seats`, never `rbtv goal materialize`
  (which refuses in exactly that state) and no longer any door here. Reaching for a planning-side
  repair re-invents the mechanism this entry deleted.
- Probe leg M must keep deriving from the checked-in `plan-console` manifest, and its last check
  greps the probe's own source for hand-typed seat ids — adding a literal seat id anywhere in that
  file, even in a comment, turns it red. The trap it closes is agreement between two copies of the
  same mistake reported as green, which is how the divergence at `8713ca14` survived nineteen legs.
- `pipeline-seats.json` still has a live reader in `argv.py`, so the mirror-vs-manifest alarm is not
  vestigial even though the door that once consumed it is gone. Deleting the json or `pipelineMinted`
  on the grounds that "the door is gone" silently changes what `path_a.py` uncasts.
- `door.js` and `queue-request.js` both now carry names that describe mechanisms they no longer hold.
  Renaming or deleting either requires editing `planning/exposure.csv` in the same act — a dangling
  `exposes` path is not a lint failure, it shuts seat minting at every door.
- role: is not a goal.md frontmatter key — cmd_scaffold writes six keys and no route writes a seventh; code or repair plans keying on `role: planning` key on nothing
