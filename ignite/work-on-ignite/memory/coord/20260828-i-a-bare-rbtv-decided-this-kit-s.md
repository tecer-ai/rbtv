# 20260828-i-a-bare-rbtv-decided-this-kit-s — a bare .rbtv/ decided this kit's store and inbox

kind: issue
component: coord
date: 2026-08-28
commit: db1609e1
deployed: no
pin: ignite/coord/probes/probe-workspace-record-walk.py
components: supervisor,planning

## Observed
The two walkers `5815fbaa` named as loose ends outside its own walls, at HEAD 5771be33 (= the
deployed worktree): `ignite/coord/ending_store.py:18-26 ending_store_db` and
`ignite/coord/ruling.py:51-61 workspace_root`. Both answered "the workspace" with the first
ancestor holding a bare `.rbtv/` DIRECTORY. `ending_store_db` additionally CREATED one: with no
`.rbtv/` anywhere above it, it returned `<start>/.rbtv/runtime/ignite/heart.db` and
`ending_store_op` then `mkdir(parents=True)`'d that path into existence on the next write. It is
the resolver 5815fbaa identified as the writer of the stray
`3-resources/tools/rbtv/.rbtv/runtime/ignite/heart.db` that appeared 19 seconds after the watchdog
probe planted `<repo>/.rbtv/runtime/watchdog/` at 03:02:15Z on 2026-08-28 (moved to
`/tmp/nested-rbtv-evidence-20260828T073428Z/`).

The cost was not hypothetical and was still being paid on this box. `/tmp/.rbtv/` existed, created
2026-08-28 07:33, holding exactly one file: `runtime/ignite/heart.db`. It is the same fallback's
work, and it made `/tmp` the first bare-`.rbtv/` ancestor of every scratch package the coord
selftest builds. All 73 of them therefore shared ONE ending store, and that store OUTLIVED each
run's tempdir. Measured at HEAD 5771be33/7652dc10: `coord.py selftest` = 1015 ok / 7 FAIL, and the
seven were `dag-08 EX-1/EX-2/EX-3`, `§1.2 the voice model`, `dag-11 RS-11+AE-1 / RS-13 / AE-2` —
every one of them an ending-store row reading another run's leftovers. The last measurement on
record before that (`impl-leader-verbs`, entry `20260826-c-the-leader-s-ruling-acts-accep`) was
1008 ok / 0 fail, taken before `/tmp/.rbtv/` was planted.

## Mechanism
ONE wrong definition of "workspace", in two functions, one of which promised in prose to match the
other. D27 and its canonical implementation `ignite/ignite-cli/lib/config.js#findInstallRoot`
define a workspace as the folder that ROOTS THE INSTALL — the nearest ancestor holding the
committed endpoint record `.rbtv/modules/ignite/server.json` ("walk up to the NEAREST ancestor
holding `.rbtv/modules/ignite/server.json`. Nearest wins"). A `.rbtv/` directory is a runtime
scratch folder; any process that runs once with the wrong cwd mints one, it is gitignored
(`.gitignore:76 **/.rbtv/`), and from that moment it OUT-VOTES the real install for every walk
starting below it.

`ruling.workspace_root`'s docstring read "⚠ RESOLVED THE WAY `ending_store.ending_store_db`
RESOLVES IT, walking up for `.rbtv`, so the kit and the engine land on the same directory by
construction rather than by configuration." The two really did agree — on the wrong rule — and the
agreement was held by a comment, which is the shape that drifts the moment one side is fixed.

The create-at-cwd fallback is the half that does damage rather than merely reading wrong: an ending
stamped into a store no daemon opens is indistinguishable, to its writer, from a recorded one. That
is the absence-reads-as-health failure, and it is why the fallback had to become a refusal rather
than a better guess.

## Attempts
First attempt held — checked: `5815fbaa` (2026-08-28), which fixed this exact rule at
`ignite/deploy/probe-suite-scheduled.py#find_workspace_root` and in
`observation/daemon-watchdog/tool/rbtv-ignite-watchdog#resolve_workspace`, wrote the mirrored
six-line rule both files now carry, and deliberately left these two untouched as out-of-wall loose
ends (its Consequences section names both by file:line). `02d989ef` gave `config.js` the
`findInstallRoot` walk (entry `ignite-cli/20260827-i-gateway-lookup-was-cwd-only-no`) and, being
JS-side, left every Python walker on the old rule. `d7841291`
(`coord/20260826-c-the-leader-s-ruling-acts-accep`) CREATED `ruling.workspace_root` and is where
the "resolves the way ending_store does" docstring came from — the promise, not a fix of it. No
earlier attempt targeted the coord copies.

## Fix
The rule is the INSTALL RECORD, and in this kit it is ONE function.

`ending_store.workspace_root(start)` walks up for `.rbtv/modules/ignite/server.json`, NAMES on
stderr any bare `.rbtv/` it walks past ("a .rbtv/ that does not root the install is NOT a
workspace; walked past it"), and returns None when nothing roots an install. Nearest-ancestor-wins
is unchanged, so a genuinely nested install still shadows an outer one. `INSTALL_RECORD_REL` is the
one spelling of the path in this component and the fixtures read it off that constant.

`ruling.py` DELETED its walk and calls that function; `ending_store` is already bound in coord's
namespace at `coord.py:48`. Rejected: leaving two mirrored copies here. 5815fbaa mirrored the rule
per file because its two files are stdlib-only tools that must run when everything else is down and
`gateway_client.py` (re-checked: `resolve_workspace_root(default, env=None)`) takes the root as an
ARGUMENT and owns no walker to reuse. Neither reason applies inside one component whose modules
already import each other — `supervisor_door.py` imports `ending_store_db` today. Rejected: a new
shared module under `coord/`, which would be a third file and a `SPLIT_MODULES` registration to
carry six lines that already have a home.

`ending_store_db`'s create-at-cwd fallback is DELETED. With no record anywhere it raises
`EndingStoreError` naming the record and `findInstallRoot`, because the only alternative is minting
the decoy. Decided from the callers: `ending_store_op` and `supervisor_door.supervisor_op` both
already surface the exception; `planning/materialize-seats.py#_chair_current_ending` CATCHES
`EndingStoreError` by design ("an UNREACHABLE store reads as no ending") so a materialize over a
fixture tree behaves exactly as before; the selftest's `clear_ending` / `read_ending_direct` reach
it on fixture packages, which now carry a record. `ENDING_STORE_DB` stays the FIRST branch and is
NOT validated — five kinds of fixture point it at scratch stores that root no install, and
validating it would convert each into a test of the refusal (the same reasoning 5815fbaa recorded
for the watchdog's env override).

## Consequences
Nothing else changed behaviour; the fixtures changed to say what they always meant. Six scratch
workspaces gained the install record: `coord_selftest.py`'s main fixture root (via a new
`seed_workspace()` helper reading `ending_store.INSTALL_RECORD_REL`) plus `d8h-ws`, `tdW4`, `tdW8`
and `tdD2`, `cli_main.py#advice_refused_sends`'s own tempdir (its `checkin` seeding reaches the
store through `awaiting_debts`), and the fixture roots of `probe-leader-hold`,
`probe-checkout-disposition` and `probe-lifecycle-idents`. That is the whole blast radius: it was
found by instrumenting the resolver to log every start path it could not root and running the suite
once, not by fixing aborts one at a time.

The seven ending-store selftest rows red at 5771be33 went GREEN with those records in place, which
is the leakage being removed rather than a row being changed: each run now writes a store inside
its own tempdir and starts empty. `/tmp/.rbtv/` was left in place, surfaced not deleted.

`ignite/coord/probes/` gained `probe-workspace-record-walk.py`; probe-suite discovery is by
structure, so the count moves on its own. No doc is stale: neither `coord/component.md` nor
`coord/exposure.csv` enumerates probes, and no prose in the component stated the old rule.

Three sibling walkers in this component were NOT touched and are surfaced: `worktree-flow.py:161`
walks up from cwd for a bare `.rbtv/` (mitigated by an explicit `--ws`), `file-issue.py:79` gates on
`.rbtv/config/` and `owed-answers.py` takes its workspace as an argument. `gateway_client.py:195`
walks for the FILE `.rbtv/config/sender-token.env`, which is `config.js`'s own token walk and is
not this defect.

## Verification
`ignite/coord/probes/probe-workspace-record-walk.py` — 13 checks, exit 0, 2.2s. The fixture is the
outage in miniature: `<ws>` holding the install record, a nested `<ws>/sub/repo/.rbtv/runtime/`
holding none, and the goal package under it. It proves resolution answers `<ws>` and not the nested
repo (A1), the `heart.db` path follows (A2), the skipped bare `.rbtv/` is named on stderr (A3),
resolving creates NOTHING (A4, asserted as the tree's file list), a real
`supervise instruct worker-a reassign --go` run with its cwd INSIDE the nested repo lands the
leader's inbox under `<ws>` and leaves no JSON in the repo (B1), and — the discriminating control —
that adding ONLY an install record inside the nested repo moves that inbox there (C1). With no
record anywhere both doors refuse naming the record (D1, D2), the whole tree is unchanged
afterwards (D3), and `ENDING_STORE_DB` still wins from that same tree (E1). THREE RED CONTROLS: the
resolver's own source with the record test swapped back to `(p / '.rbtv').is_dir()` resolves to the
nested repo (F1) and answers a `heart.db` inside the no-record tree (F2); and a COPY OF THE KIT
(`coord`+`supervisor`+`state-store`, `__pycache__` dropped) carrying only that one mutated line
writes the leader's inbox into the NESTED REPO through the real `supervise instruct` (G1) — which
is the ruling half demonstrated to ride the one shared walker rather than asserted to.

`coord.py selftest` run FROM THE REPO ROOT deliberately: PASS, 1022 ok, 0 failures, exit 0 (before:
1015 ok / 7 FAIL at the same head). `ls <repo>/.rbtv` absent before and after every run in this
sitting. Coord probes all green afterwards: `probe-leader-hold` 14 checks exit 0,
`probe-checkout-disposition` 11/11, `probe-finish-edge` PASS, `probe-store-ready-suppression` 5/5,
`probe-defect-fix` 15/15, `probe-save-gate` 27/27, `probe-731-pipe-pane-capture` 15/15,
`probe-nudge-degrade` no failures, `probe-lifecycle-idents` exit 0. `component-lint` on
`ignite/coord`: 2 findings, both `exposure-canon` rows 11-12, pre-existing and untouched.
PRE-EXISTING RED, PROVEN NOT MINE: `probe-coord-selftest-notmux` and `-tmuxpane` both time out —
the selftest's wall was 194s BEFORE any edit here and 199s after, against the venue's budget.

NOT DEPLOYED anywhere, and nothing needs a restart: `~/.local/bin/coordinate` and
`~/.local/bin/supervise` are symlinks INTO THE SOURCE TREE
(`.../ignite/coord/coord.py`, `.../ignite/supervisor/supervise.py`), and every component in
`.rbtv/config/install.json` carries `tree_root` = the source repo, so a caged seat's CLI grant
resolves there too. `/home/henri/.local/state/rbtv-deploy` serves the two systemd units only, which
are node and import none of this.

## ATTENTION
1. A `.rbtv/` DIRECTORY IS NOT A WORKSPACE — the test is `.rbtv/modules/ignite/server.json`. This
   component now has exactly one walker, `ending_store.workspace_root`. A second one added here
   would be the fourth copy of the rule on the tree and the first that nothing pins.
2. `ending_store_db` RAISES where it used to answer. A new caller that treats a missing workspace
   as "no store yet" must catch `EndingStoreError` the way
   `materialize-seats.py#_chair_current_ending` does; one that lets it escape turns a fixture tree
   into an abort, which is how this change was measured rather than guessed.
3. ANY fixture that reaches the ending store must root an install — `<td>/.rbtv/modules/ignite/
   server.json`, one file. Building `<ws>/.rbtv/goals/<goal>` is NOT enough and never was: before
   this change such a fixture silently resolved to the first bare `.rbtv/` above it, which on this
   box was `/tmp/.rbtv/`, shared by every run.
4. `/tmp/.rbtv/runtime/ignite/heart.db` (created 2026-08-28 07:33) IS STILL THERE. Nothing reads it
   any more, but it is a live decoy for any remaining bare-`.rbtv/` walker started under `/tmp`,
   and `worktree-flow.py:161` is one.
5. The env override `ENDING_STORE_DB` is deliberately NOT validated against the record, for the
   same reason 5815fbaa left `RBTV_WATCHDOG_WORKSPACE` unvalidated: the fixtures that use it point
   at scratch stores by design, and validating it would test the refusal instead of the store.
- a .rbtv/ DIRECTORY is not a workspace — the test is .rbtv/modules/ignite/server.json, and this kit now has exactly one walker
- any fixture that reaches the ending store must root an install: <root>/.rbtv/modules/ignite/server.json, one file
