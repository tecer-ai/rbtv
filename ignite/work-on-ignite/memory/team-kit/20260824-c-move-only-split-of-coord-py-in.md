# 20260824-c-move-only-split-of-coord-py-in — move-only split of coord.py into 16 loaded siblings

kind: change
component: team-kit
date: 2026-08-24
commit: 867a240f
deployed: no
pin: team-kit/probes/probe-coord-selftest-notmux.py

## Motivation
`coord.py` was a 38k-line monolith and D23 / T4-R12 require any touched monolith to be split into
cohesive units, as a move-only phase with behavior unchanged [D1] and the selftests kept green.
The split-module list is owner-approved in `redesign/specs/spec-component-map.md` §3; this sitting
implements that list and nothing else. Component-folder migration stays with impl-structure [D22].

## Design
Sixteen map-named units left the monolith as sibling files under `team-kit/`, and `coord.py`
remains the import-level entry (184 lines: docstring, imports, the shared constants, the load, the
`__main__` guard). The split is TEXTUAL, not modular: coord.py loads each sibling with
`exec(compile(src), globals())` over the names in its own `SPLIT_MODULES` tuple, so all sixteen
files share ONE runtime namespace. The rejected alternative is what the first nine extractions
actually did — import each sibling as a module and copy coord's globals into it once at import
time. That copy is a snapshot: the selftest substitutes ~60 names at runtime (`global wake,
tmux_send_text, atomic_write, RUNS_INDEX, ...` plus 24 `globals()[...] = stub` sites) and a moved
body read its own frozen copy instead, so every stub was inert. Measured on the same bytes: 913 ok
under the copying bind's predecessor, ABORTED after 23 checks with it, 1039 ok / PASS with the
shared namespace. Startup was measured, not assumed: `--help` costs 0.43 s split vs 0.46 s before,
because a script run as `__main__` was never `.pyc`-cached either.

## How it works
`SPLIT_MODULES` in `coord.py` names the sixteen files in load order: `addressing`, `outputs`,
`tmux`, `process`, `records`, `identity`, `carrier`, `closeout`, `attest`, `checkout`,
`lifecycle_exec`, `messages`, `launch`, `ready`, `coord_selftest`, `cli_main`. The loader reads
each file's text, appends it to `_SPLIT_SOURCES` and execs it into `globals()`. It then joins the
shim's own text with those sources into `PRODUCT_SOURCE` — the corpus the audits that scan "this
module's source" now read, at no extra I/O. Every public and private name still lands on `coord`,
so `import coord`, the `coordinate` symlink, daemon argv and every probe pinning `COORD_PY` are
untouched; `SUMMONED_SEATS`, `STAFF_SEATS`, `SESSIONS_COLS`, `cmd_send` and `main` were each
verified present through a real `spec.loader.exec_module` load.

## Consequences
Four modules are over the 2000-line budget by owner ruling (a), 2026-08-24, recorded in the map as
named exceptions and not to be sub-split here: `checkout` 2118, `lifecycle_exec` 2157, `messages`
3049, `launch` 2880. `coord_selftest.py` (15519) is the test module and is excluded from the
budget; `materialize-seats.py` stays intact and excluded. Eleven selftest scan sites, the
advice-coaching scanner and four probes had to be repointed at the moved files — a scan-target
change in each case, never a logic change: `probe-lifecycle-idents` locates the seven guarded acts
in the product source, `probe-save-gate` derives its stand-in kit from `SPLIT_MODULES` and mutates
`argparse` before the `__main__` guard now that `build_parser` moved, `probe-checkout-disposition`
performs its two-seam surgery on `checkout.py`, `probe-verdict-vocabulary` extracts over the
product files, and `probe-secret-add-cage` stages the siblings in its cage kit.

## Verification
`python3 coord.py selftest`: PASS, 1039 ok, 0 failures, exit 0 (it was PASS at the seat's start
commit too — a 128-failure control run in a `/tmp` copy was a venue artifact of that copy, not a
baseline). Symbol census over `team-kit/**/*.py` is 1120 before the first move and after the last
commit. Every `team-kit` file `py_compile`s; `coord.py --help` exits 0 directly and through a
symlink. probe-suite by chunk: team-kit 11/11, cli+engine+injection-ladder+jobs+gateway 36/36,
server/spawn 36/36, ticker+heart 50/50, chat+internal-api+seat-identity+server+lease 37/37,
capabilities+launch-profiles 19/21 with the two non-greens matching the recorded baseline exactly
(`probe-bindings.py` FAIL — the worktree is not an admissible tree for that tool — and
`probe-master-profile.py` INOPERATIVE — no live casting sheet here). `reconcile.selftest.js`,
`probe-suite.js --selftest` 26/26, `probe-self-isolate.js`, `test_nudge.py` 16/16 and
`test_secret_add.py` all green. Not deployed: worktree branch `ignite/core-redesign` only.

## ATTENTION
- NEVER `import coord` from inside a split sibling, and never re-add per-module `from coord import`
  re-exports: `python coord.py` runs as `__main__`, so such an import re-executes the file under a
  second name and the two namespaces diverge — which is the exact failure the shared load removes.
- A NEW SPLIT FILE MUST BE ADDED TO `SPLIT_MODULES`, nothing else. Four scan sites now derive their
  file list from that tuple (two probes, the vocabulary extract, `PRODUCT_SOURCE`), so a file added
  to the directory but not the tuple is invisible to all of them and loads nowhere.
- `WORKER_ROW`, `TYPE_COLOR` and `HARNESS_PROCS` assignments STAY IN `coord.py` SOURCE: `test_nudge.py`
  and `probe-message-type-vocabulary.js` read them out of that file's text, not from the module.
- A source scan that reads `Path(__file__)` inside a moved body still reads `coord.py`, because
  `__file__` is a global of the shared namespace — such a scan goes SILENTLY EMPTY rather than red.
  Point it at `PRODUCT_SOURCE`; check any new scan for this shape before trusting a green.
- Do not sub-split `checkout`, `lifecycle_exec`, `messages` or `launch` to reach the 2000-line
  budget: owner ruling (a) made each one file for this plan, and a later impl rewrite shrinks them.
- extracted siblings must never import coord — one shared namespace, loaded from SPLIT_MODULES
- a source scan reading Path(__file__) in a moved body goes silently empty, not red — use PRODUCT_SOURCE
