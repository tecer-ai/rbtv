# 20260825-c-the-js-side-of-ignite-goes-com — the JS side of ignite goes component-first

kind: change
component: runtime
date: 2026-08-25
commit: f4b4de44,7e671b15,50da76bf,d8a48796,b83c05d3
deployed: no
pin: ignite/supervisor/lane-skip.selftest.js
components: supervisor,state-store,chat,operator,envelope,observation,ignite-cli,planning

## Motivation
`ignite/` was a flat dir-per-subsystem tree (`engine/ server/ gateway/ jobs/ lib/ bridges/ cli/
capabilities/ config/ launch-profiles/`); only `work-on-ignite/` conformed to the component-first
layout D22 requires, and T4-R11 forbids ratifying today's tree 1:1. `spec-component-map` is the
owner-approved map; this change lands its JS half.

## Design
`git mv` per `spec-component-map` §2, never copy+delete, so `git log --follow` still reaches every
file's history. Component-first destinations: `bridges/chat` → `chat/`, `cli/` → `ignite-cli/`,
`capabilities/` → `operator/` (except `daemon-watchdog/` → `observation/`), `gateway/`+`jobs/`+
`lib/` → `runtime/`, `launch-profiles/` → `supervisor/launch-profiles/`, `config/` split three ways
(spawn-profiles → `envelope/`, chat settings + senders seed → `chat/`, worker settings →
`supervisor/`), `server/` split (heart → `state-store/heart/`, spawn → `supervisor/spawn/`, the rest
→ `runtime/`), `engine/` split (reconcile/lane-watch/seeding/execution-record/ending-reads/
owed-from-endings → `supervisor/`, queue-request + unbuilt-seats → `planning/`, cage-admission →
`envelope/`, attached-execution → `operator/`, bus-answer → `chat/`, index/substrate/run-board/
frozen-pass → `runtime/`, restart-window → `observation/`). Probes travelled with their product file.

Subtree names were PRESERVED wherever the source was a folder (`spawn/`, `heart/`, `ticker/`,
`lease/`, `internal-api/`, `seat-identity/`, `gateway/`, `jobs/`, `launch-profiles/`) rather than
flattened: it keeps most relative requires the same shape and keeps sibling name collisions
impossible. Rejected: flattening everything into each component root (two `errors.js`, two
`config.js`, two `index.js` collide immediately).

Exactly ONE file was renamed, and only because two `index.js` files landed in the same home:
`engine/index.js` → `runtime/engine.js`. `server/index.js` keeps `index.js`, because that is the
path systemd's `ExecStart` names and the daemon entry is what `runtime/` is for. No symbol was
renamed anywhere and no body was split.

## How it works
The repointing was done by resolving each relative require against the file's OLD directory,
mapping the target through the rename map, and recomputing the specifier from the NEW directory —
so a move that changed depth (`bridges/chat/**` one level up, `gateway/**`, `jobs/**`,
`launch-profiles/**` one level down) is handled by construction rather than by eye. The same map
was then applied to quoted path segment lists (`path.join(IGNITE, 'server', 'heart', …)`) and to
path strings inside literals. Verification passes: a resolver over all 363 JS files reports zero
unresolvable relative requires; `node --check` is clean on all of them; `runtime/engine.js`,
`runtime/index.js`'s dependency graph, `supervisor/spawn/spawn.js`, `runtime/ticker/ticker.js`,
`state-store/heart/heart-store.js`, `planning/door.js` and eleven more load under `node -e require`.

## Consequences
`ignite/` no longer has `engine/ server/ gateway/ jobs/ lib/ bridges/ cli/ capabilities/ config/
launch-profiles/`. `runtime/`, `chat/`, `operator/` and `ignite-cli/` were created with their
`component.md` + `exposure.csv`; arrival rows and a "what moved in" note were appended to
`supervisor/`, `envelope/`, `state-store/`, `observation/` and `planning/`; the module-root
`module.md` and `exposure.csv` rows were repointed. Deploy units and the `spawn-profiles.yaml` tool
allowlist now name `runtime/index.js`, `chat/index.js`, `envelope/spawn-profiles.yaml` and
`observation/daemon-watchdog/`.

Three guards would have silently lost their teeth and were repaired in the same change: the gateway
boundary scanner's `/server/` rule (no such path exists now), the heart seam probes' `PROD_DIRS`
list, and probe-g225's `closeSession` enumerator, which walked the whole old `server/` tree and now
walks all three homes that tree became. `supervisor/lane-skip.selftest.js` went RED for the right
reason — it read `__dirname/index.js` for the engine facade, which in `supervisor/` is the registry —
and is green again against `runtime/engine.js`.

Left for the Python-side sweep (`impl-structure-moves-py`, by design): every `.py` caller naming an
old path, including `observation/daemon-watchdog/tool/rbtv-ignite-watchdog`'s `code_scope_note`,
whose `root.name == "server"` test and `("engine", "bridges")` blind list are now both stale.

## Verification
`node --check` over all 363 JS files: 0 failures. A require resolver over the same set: 0
unresolvable relative specifiers (the 6 remaining textual hits are inside assertion strings and
comments, verified by hand). Green selftests after the move: `supervisor/reconcile.selftest.js`,
`supervisor/lane-skip.selftest.js` (5/5), `supervisor/registry.selftest.js`,
`envelope/envelope-compiler.selftest.js`, `observation/frozen.selftest.js`,
`state-store/ending-store.selftest.js`. `git log --follow` reaches pre-move history on
`runtime/engine.js`, `supervisor/spawn/spawn.js` and `chat/reply-leg.js`. Not deployed: this is the
`ignite/core-redesign` worktree and the cutover seat owns the restart.

## ATTENTION
1. `runtime/engine.js` is the old `engine/index.js` — `createEngine`, the composition root both
   attachments boot. `runtime/index.js` is the old `server/index.js`, the daemon entry. Requiring
   `runtime/` as a directory now gets NEITHER (there is no `runtime/index.js` barrel export of
   `createEngine`); name the file.
2. A `path.join(__dirname, …)` read is move-blind: it keeps resolving after a move, just to the
   wrong file. Auditing requires alone would have missed five probes and one selftest here.
3. A guard that names a path or a directory list (`PROD_DIRS`, a `/server/` regex, a tree walk)
   silently narrows to nothing when that path stops existing — it does not fail, it passes
   vacuously. Any layout change must re-point those by hand.
4. The component names are DISK-DERIVED for the installer and for `file-issue memory`: the memory
   folders still carry the old names (`engine`, `server`, `cli`, …) and do not follow a rename.
5. Instance-hardcoded absolute paths still sit in `envelope/spawn-profiles.yaml`'s tool allowlist
   (pre-existing, not introduced here). Their suffixes were updated to the new homes; the hardcoded
   prefix is a separate defect nobody has fixed.
- runtime/engine.js is the old engine/index.js; runtime/index.js is the old server/index.js — requiring the directory gets neither
- a path.join(__dirname, ...) read survives a move and resolves to the WRONG file; audit those separately from requires
