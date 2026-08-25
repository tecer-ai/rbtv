# 20260825-c-the-python-kit-goes-component — the Python kit goes component-first, both ways

kind: change
component: team-kit
date: 2026-08-25
commit: 0e662f82,73f3a980,95c0d0bc,d5d4b4c9,ff6917e3
deployed: no
pin: ignite/envelope/probes/probe-cagespec-mirror.py
components: coord,planning,envelope,skills,injection-ladder,capabilities,server,engine,jobs,cli,config,deploy,meta-planning

## Motivation
`spec-component-map` §1/§2 [D22, T4-R11, C-15] gives every functional unit a conforming
`ignite/<component>/` home. impl-structure-moves-js landed the JS half; this is the Python
half plus the module-root manifest retirement, and the cross-language sweep in BOTH
directions that a two-sided move needs.

## Design
`git mv` per §2, never copy+delete, so `git log --follow` still reaches every file's
history: `team-kit/` → `coord/` as a WHOLE TREE, `cagespec.py` → `envelope/`, the intact
`materialize-seats.py` → `planning/`, `injection-ladder/` → `coord/injection-ladder/`,
`skills/team-kit/` → `coord/skills/team-kit/`, and the extra-module `meta/teambuild/` →
`ignite/teambuild/` keeping its shape. Probes travelled with their product file:
`probe-cagespec-mirror.py` went to `envelope/probes/`.

The whole-tree move of `team-kit/` was forced, not chosen. `coord.py` does not import its
sixteen split siblings — it `exec`s them out of `Path(__file__).parent` into ONE shared
namespace, and `probe-lifecycle-idents` and `probe-save-gate` derive their file lists the
same flat way. So the six modules §3 names for `supervisor/` (`process`, `lifecycle_exec`,
`ready`, `launch`, `attest`, `carrier`) cannot leave without redesigning the loader and two
probes, which is not a move. They stayed with `coord.py` and the conflict is reported
rather than silently resolved either way.

## How it works
Every path reference broken in either direction was re-pointed by resolving it against the
OLD location and recomputing it from the NEW one. Python side: `materialize-seats.py`'s
`_coord_import` read its OWN directory for `coord.py` and no longer sits beside it;
`link-tools.py`'s `TOOLS` map assumed one kit folder and now carries module-relative
targets; four probes walked parents for a `team-kit/self_isolate.py` ancestor. JS side, all
left by the JS move and each found by RUNNING the thing rather than reading it:
`meta/rbtv-cli`'s route table still named `ignite/capabilities/*` and `ignite/cli/ignite.js`,
so `rbtv ignite`, `rbtv ignite daemon`, `rbtv ignite ticker`, `rbtv goal` and `rbtv run` all
refused with "the delegate is not on disk"; `rbtv-execution` required
`engine/attached-execution.js` and read `config/spawn-profiles.yaml`; the watchdog resolved
`daemon-operator` as a sibling CAPABILITY when the move made it a sibling COMPONENT, so
every restart arm raised FileNotFoundError; the two `jobcontain` probes went one level
deeper with `jobs/` → `runtime/jobs/` and their `parents[2]` repo-root walk landed on
`ignite/`; `meta/embed-search` imported teambuild's provider from `meta/`.

The watchdog's `code_scope_note` branched on `root.name == "server"` and named a blind list
of `("engine", "bridges")`. Both were stale, so the SCOPE sentence appended to a `current`
verdict was silently wrong — the exact W8 failure that sentence exists to prevent. It now
recognises the `runtime/` fingerprint root and names the six sibling components the daemon
loads from plus `chat/`.

Every `exposes:` reference of the form `rbtv:ignite/team-kit/coordinate` resolves by
`module/component/part`, so the component rename broke thirteen `meta/` seat prompts and the
four references that rule them; those were repointed with the prose.

## Consequences
`ignite/` no longer has `team-kit/`, `injection-ladder/` or `skills/`; `meta/` no longer has
`teambuild/`. `coord/` and `deploy/` gained their `component.md`; `planning/module.md` became
`planning/component.md` (a component folder is marked by `component.md`; `module.md` is the
module root's name). The materializer's two exposure rows left `coord/` for `planning/` with
the file, `cagespec` gained an `envelope/` row, the kit's skill row arrived from the module
root — and the module-root `ignite/exposure.csv` is DELETED, every one of its twelve live
rows now sitting on the component that owns it (§2, §7.3).

## Verification
`coord.py selftest`: PASS, 0 failures. `coord.py --help`, `materialize-seats.py --help` and
`rbtv run --help` all exit 0. `py_compile` clean on all 55 edited Python files and all 66
under `coord/ planning/ envelope/ teambuild/`; `node --check` clean on all 40 edited JS
files. probe-suite by chunk: coord+injection-ladder+envelope+planning 17/19 (the two
non-greens are both `coord.py selftest` under a 165s probe budget against a 202s run —
`coord_selftest.py` is byte-identical to its pre-move self, so this is box timing, not the
move); spawn+jobs+heart 53/59 then 56/59 after the jobcontain and spawn-refresh repairs;
operator+watchdog with `probe-watchdog-staged-failure` going 9-failures → PASS. Every
`rbtv` route target verified to exist on disk. Not deployed: worktree branch
`ignite/core-redesign` only; the cutover seat owns the restart.

## ATTENTION
1. The six §3 supervisor-landing modules are STILL IN `coord/` and that is a recorded
   spec-vs-disk conflict, not an oversight — `coord.py` execs its `SPLIT_MODULES` siblings
   out of its own directory, so moving one without redesigning that loader breaks the CLI.
2. A guard that names a component FOLDER goes vacuously quiet rather than red when the
   folder is renamed. The watchdog's scope note printed nothing, and `probe-seam-closed-set`
   still classifies crossings by a `server/` rule that matches nothing.
3. `meta/` seat prompts carry LIVE component references in `exposes:` — a component rename
   is a prompt-tree edit, not just a code edit, and materialize refuses a dangling ref.
4. Component names in `work-on-ignite/memory/` are disk-derived and do NOT follow a rename:
   this entry is filed under `team-kit`, which is `coord/` on disk.
5. `materialize-seats.py` still reads the workspace policy file at
   `.rbtv/config/modules/ignite/team-kit/interactive-exposes.json`. Left deliberately: that
   is INSTANCE data, and moving the address orphans an existing file — an owner call.
- coord.py execs its SPLIT_MODULES siblings from its own directory — a split file cannot move out of coord/ without redesigning that loader
