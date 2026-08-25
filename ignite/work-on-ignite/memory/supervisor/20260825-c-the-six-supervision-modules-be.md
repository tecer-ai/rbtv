# 20260825-c-the-six-supervision-modules-be — The six supervision modules become real imports

kind: change
component: supervisor
date: 2026-08-25
commit: 1cbb7c76,bc0af66f
deployed: no
pin: ignite/coord/probes/probe-lifecycle-idents.py
components: coord,planning

## Motivation
`spec-component-map` §3 homes six of `coord.py`'s split modules in `supervisor/`, and they had
never gone: `coord.py` `exec`s its `SPLIT_MODULES` siblings out of its OWN directory into one
shared namespace, so a file that left broke the CLI. That was recorded as a spec-vs-disk
conflict. The owner ruled the other way on 2026-08-25 ("SPLIT_MODULES / coordinate split"): the
six move, the loader is redesigned to permit it, and the seat must PROVE the namespace separation
before moving anything.

## Design
The proof came first and it decided the structure. An AST walk over all 17 product files found
1,506 cross-module references and exactly ONE at module level (`cli_main.py`'s `READ_LIMIT`,
agent-side, never crossing). Everything else is read inside a function body, so the module cycle
the two halves form resolves at CALL time and plain module-object imports are sound. There is no
shared layer to extract and none was invented: the halves are mutually recursive (18 agent →
supervision edges over 30 symbols) and the six need 192 distinct agent-side names, so
`supervisor/` depends on `coord` as a library and `coord` names the six back.

The six became real modules; the other ten stay exec-loaded into `coord`'s namespace, because
that half's textual sharing still buys what it always bought and nothing asked it to change.

## How it works
`git mv` first, in its own commit, with the loader resolving two directories and no body touched
— then the rewrite. A scope-exact rewriter qualified 1,099 references (`coord.NAME` out of the
six, `<module>.NAME` out of the ten and the selftest); each of the six gained its own stdlib
import header plus `import coord` and its peers. Zero names were ambiguous — no symbol is defined
on both sides. `coord.py` imports the six AFTER the exec loop, so they meet a namespace that
already carries every agent-side name. Running `coord.py` directly is now a TRAMPOLINE that loads
`__file__` under the name `coord`, so exactly one namespace exists. `PRODUCT_ORDER` /
`PRODUCT_FILES` keep `PRODUCT_SOURCE` the same corpus in the same sequence.

## Consequences
`SPLIT_MODULES` names ten files, not sixteen. `spec-component-map` §3's re-export shim is real and
DERIVED: `materialize-seats.py` imports `validate_seat` off the module and `goal_cli.py` loads
`coord.py` by path and reads `parse_after_member` / `after_member_limbs` off it. Three
`Path(__file__)` sites in the moved bodies meant `coord/` and were repointed; one of them, a
`materialize-seats.py` pointer, had already been one folder wrong since the component migration.
Eight structural selftest checks that identified a call site by its callee's bare Name read
through one `called_name()` helper now. Both probes that derived a file list from the flat layout
read `coord.PRODUCT_FILES` instead, and `probe-lifecycle-idents`' two mutation anchors were
re-derived against the qualified call sites.

## Verification
`coord.py selftest` PASS, 0 failures, run at every stage. `materialize-seats.py --selftest` PASS —
0 failed checks, 0 failed rows of 62. `probe-lifecycle-idents` 42/42 CHECKS with 7/7 RED ARMS.
`probe-save-gate` PASS 27/27. `git log --follow` reaches each module's pre-move extraction commit.
A machine audit shows each of the six has ZERO free names that are not builtin, stdlib-imported by
its own header, or module-qualified. Not deployed: worktree branch `ignite/core-redesign` only.

## ATTENTION
- NEVER `from coord import NAME` in a supervision module, and never copy kit names in at import.
  The selftest rebinds ~60 kit names at runtime; a copied name is a SNAPSHOT and every stub goes
  inert — measured 2026-08-24 as 913 ok under a copying bind vs 1039 ok / PASS through call-time
  lookup. Qualify: `coord.NAME` one way, `<module>.NAME` the other.
- `coord.py` re-exports the six modules' public names for callers OUTSIDE the kit. NOTHING inside
  the kit may read one of those aliases — an alias is a snapshot a selftest stub cannot reach.
- A MODULE-LEVEL read of a peer's attribute breaks the import cycle. Adding one is a measurement,
  not an edit; today exactly zero exist and that is what makes plain imports sound.
- A pathspec-scoped commit of a rename needs BOTH sides of the pathspec. Naming only the new paths
  recorded the six as ADDED while their old copies stayed in HEAD; it took a second commit to
  retire them.
- A new file beside `coord.py` must be added to `SPLIT_MODULES` AND to `PRODUCT_ORDER`.
- supervision modules qualify coord.NAME at call time — never from coord import, which snapshots and kills every selftest stub
