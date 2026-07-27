# rbtv-goal — the goals-tree machinery

The four deterministic surfaces over the CMP-4 goals tree. Built for task 7.63; the command
grammar is owner-ruled (`r-763-grammar-ruled` — all four decision items at their recommended
defaults) and is **implemented here, not re-derived**.

```
rbtv-goal scaffold <goal-name> --contract FILE|-  [--type T] [--due DATE] [--dry-run]
rbtv-goal reindex
rbtv-goal lint <goal-name>
rbtv-goal materialize <goal-name> --catalog-root DIR [--force] [--dry-run]
rbtv-goal selftest
```

`--root` (the `.rbtv/goals` root) and `--json` are accepted on either side of the verb. Without
`--root` the root is found by walking up from the working directory.

**Exit codes** (the `sd-graph` convention): `0` success/clean · `1` refusal, gate-fail, or
not-found · `2` usage error.

All four verbs are LOCAL file operations — they work with the daemon down, which is why they live
on the `rbtv` side and never on `ignite` (the detached gateway client). v1 ships standalone and
folds into `rbtv goal <verb>` verbatim when the `rbtv` CLI lands (task 7.65) — the operator-surface
stand-in pattern, no contract change at fold-in.

## The verbs

| Verb | Does | Never |
|---|---|---|
| `scaffold` | Creates the goal root: `goal.md` (identity frontmatter + the contract body), empty `decisions.md`, `runs.csv` (header), `threads.sql` (empty schema) — then reindexes. Create-only: refuses an existing goal, never overwrites. `--contract` is REQUIRED, so a goal is born lint-green rather than sitting red until a second manual step. | Writes `runs/` compartments or seat folders — run birth is task 7.37's step |
| `reindex` | Rebuilds `goals.csv` whole from every `goal.md` frontmatter. Always the full projection; a partial one would leave silent staleness. Fails loud on an unparseable descriptor, naming the file, and leaves `goals.csv` **untouched** — a projection that silently drops a goal is corruption. | Touches any goal folder |
| `lint` | READ-ONLY validate + dry-run emulate (CMP-14). Exit 0 = gate open, 1 = gate blocks, every finding named with file + reason. | **Writes anything, ever** — conflating lint and materialize breaks the read-only contract |
| `materialize` | Creates `seats/<seat>/` per `taskforce.csv` row and assembles each `seat.md`; writes permissions. Assembles everything in memory FIRST, so a mid-assembly failure never leaves a half-materialized run. | Touches cognitive-unit sources, catalogs, or `taskforce.csv` |

### What `lint` checks

Folder name ≡ `goal.md` name · cross-goal name uniqueness · identity fields present · thin goal
state and type in their enums · the goal-radius contract body is non-empty · CMP-4 goal-level
layout · `runs.csv` / `milestones.csv` / `taskforce.csv` parse · one live run per goal · every
taskforce row resolves to a REAL seat with a parseable `seat.md` · the `after` graph is acyclic
(guards `ref[field=value]` stripped, alternates `a|b` split) and every predecessor names a real
seat row · each seat's binding matches the `taskforce.csv` row it was copied from · every
frontmatter cognitive-unit reference has its assembled block in the body · permissions well-formed
· dry-run dispatch emulation (would this seat launch under its resolved harness+model+effort — no
launch, no LLM call).

### How `materialize` assembles a seat

The settled **catalog indirection** (`d-seat-assembled-projection`): a `seats.csv` row joins an
executor (`prompt-id`) and a `task-id`; the unit references live on the `prompts.csv` / `tasks.csv`
rows, never on the seat row. Units resolve to files under `--catalog-root` by frontmatter `id`.

- **Frontmatter** = the seat id + description, the executor binding copied from `taskforce.csv`
  (`harness` · `model` · `effort` · `ctx-refresh`), and the RESOLVED unit references — the
  assembly-lockfile realization. Plural kinds take list values (YAML forbids duplicate keys).
- **Body** = one kind-named XML block per unit, stamped by the assembler with `id` and `version`
  attributes. ASSEMBLED kinds carry their full content; INVOKED kinds (`capability`, `reference`)
  enter as loader stubs — description + entry-point pointer — and stay `@latest`.

Source unit files use the settled form: a **kind-named tag with no attributes** (`<persona>…`),
with the `id` in frontmatter only. The office-scaffold prototype's `<cognitive-unit id kind>`
wrapper is superseded and is not read.

## Stand-ins and divergences

`--catalog-root` is **required and explicit**. The live rbtv repo carries no CMP-5
component-database — no `cognitive-units-index.csv`, no `seats.csv` / `prompts.csv` / `tasks.csv`,
no `cognitive-units/` pools; CMP-5 is status `draft`, designed-unbuilt. Rather than guess a path
into a tree that has no such shape, `materialize` refuses with that reason named.

**Version strings are a STAND-IN, not the settled schema.** CMP-5 resolves versions through a
repo-root `cognitive-units-index.csv` mapping version-id → (commit, filepath). Until it exists, a
frozen `@latest` records `latest+standin-sha256:<12>` over the unit file's bytes — the lockfile
stays pinned and re-checkable without inventing an index schema. The marker is greppable and every
assembled `seat.md` carries the warning in its header. **When the index lands this format is
REPLACED by real version-ids, never grandfathered.** (Registry divergence 5.)

Registry divergences flagged for transcription — **never applied to `system-definition/`**:

1. **Seat-folder naming.** CMP-4 § Layout writes `seats/seat-{name}/`; 7.63's canonical path form
   and both live run packages use bare `seats/{seat}/`. Built BARE.
2. **Command spelling.** CMP-14 § Layout writes standalone `goal-lint` / `goal-materialize`; D1a
   ruled the one `rbtv goal <verb>` family.
3. **`threads.sql` at scaffold.** Created per the KG shape; the live run's kit `coordination/`
   stand-in stays noted under `r-kg-shape`.
4. **Goal-level watcher state.** CMP-4 and the `goal-folder` record place it at goal level but name
   no file; not invented here.
5. **`cognitive-units-index.csv` absent** — above.

## Safety

`scaffold`, `reindex` and `materialize` MUTATE. `materialize --force` regenerates seat folders,
which on a live run would rewrite the frozen lockfiles of seats that are currently executing —
including, if aimed at the executing package, the run's own. Aim write verbs at a test root with an
explicit `--root`. `lint` is read-only by contract and safe against any package (verified
empirically: a path+size+mtime fingerprint of a live goal folder is identical before and after).

## Verify

```
rbtv-goal selftest        # end-to-end on a throwaway tree; exit 0 / 1
```

`selftest` exercises scaffold (+ its three refusals), the read-only property of lint, name/layout
violation rejection, cycle rejection, the full assembly (frozen assembled refs, `@latest` invoked
refs, stamped XML blocks, loader stubs not inlined), refuse-without-`--force`, `--force`,
refuse-without-`--catalog-root`, and reindex's fail-loud-and-leave-untouched behaviour. Run it after
ANY edit to `goal_cli.py` — it must exit 0.

A selftest sits inside its own blast radius, so it is not sufficient evidence on its own: vary the
invocation (bare, under `timeout`, via `sh -c`, from another cwd, absolute path, piped/no-tty) and
prove the assembly against real captured content, not only its own fixtures.
