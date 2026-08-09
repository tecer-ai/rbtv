# rbtv-goal — the goals-tree machinery

The four deterministic surfaces over the CMP-4 goals tree. Built for task 7.63; the command
grammar is owner-ruled (`r-763-grammar-ruled` — all four decision items at their recommended
defaults) and is **implemented here, not re-derived**.

```
rbtv-goal scaffold <goal-name> --contract FILE|-  [--type T] [--kind K] [--due DATE] [--dry-run]
rbtv-goal reindex
rbtv-goal lint <goal-name>
rbtv-goal materialize <goal-name> --catalog-root DIR [--force] [--dry-run]
rbtv-goal selftest
```

`--root` (the `.rbtv/goals` root) and `--json` are accepted on either side of the verb. Without
`--root` the root is found by walking up from the working directory.

**`--kind interactive|non-interactive`** (default `interactive`) stamps `goal-kind` into `goal.md`
frontmatter. Owner ruling `d-owner-batch1` (2), 2026-08-08: the frontmatter IS the carrier — a
consumer looks the kind up on the descriptor and it is never carried on a queue row.

The field is **OPTIONAL on the descriptor**, and that has one consequence worth stating outright:
a goal scaffolded before the field existed carries no `goal-kind` key, **lints clean**, and reads
as `interactive`. So `goal-kind` is deliberately NOT in lint's identity-fields check (the same
treatment `due-date` gets); only its ENUM is checked, and only when a value is present. `reindex`
projects the declared value and leaves the cell EMPTY when the descriptor declares none — the
index reports what each descriptor says, and the default is applied by the reader, in one place
(`seat-folder.js#goalKind`), so the ruled default cannot fork across two files.

**Exit codes** (the `sd-graph` convention): `0` success/clean · `1` refusal, gate-fail, or
not-found · `2` usage error.

**`<goal-name>` is a single folder name directly under `--root`, never a path.** `lint` and
`materialize` resolve it and REFUSE (exit 1) anything landing outside the root — an absolute path
or a `..` traversal. Before the guard, `root / name` discarded the root whenever the name was
absolute: `materialize` wrote a `seat.md` outside the declared root and reported `"ok": true`,
which defeats the only sandbox this tool has (`--root` is how a write verb is aimed at a test tree
instead of a live package). Guarded by `../probes/probe-goal-root-escape.py`, whose red control
runs the pre-fix expression and requires it to escape.

All four verbs are LOCAL file operations — they work with the daemon down, which is why they live
on the `rbtv` side and never on `ignite` (the detached gateway client). v1 ships standalone and
folds into `rbtv goal <verb>` verbatim when the `rbtv` CLI lands (task 7.65) — the operator-surface
stand-in pattern, no contract change at fold-in.

## The verbs

| Verb | Does | Never |
|---|---|---|
| `scaffold` | Creates the goal root — NINE files: `goal.md` (identity frontmatter + the contract body), `runs.csv` (header), `threads.sql` (empty schema), plus the standard goal-folder artifacts of § below — then reindexes. Create-only: refuses an existing goal, never overwrites. `--contract` is REQUIRED, so a goal is born lint-green rather than sitting red until a second manual step. | Writes `runs/` compartments or seat folders — run birth is task 7.37's step |
| `reindex` | Rebuilds `goals.csv` whole from every `goal.md` frontmatter. Always the full projection; a partial one would leave silent staleness. Fails loud on an unparseable descriptor, naming the file, and leaves `goals.csv` **untouched** — a projection that silently drops a goal is corruption. | Touches any goal folder |
| `lint` | READ-ONLY validate + dry-run emulate (CMP-14). Exit 0 = gate open, 1 = gate blocks, every finding named with file + reason. | **Writes anything, ever** — conflating lint and materialize breaks the read-only contract |
| `materialize` | Creates `seats/<seat>/` per `taskforce.csv` row and assembles each `seat.md`; writes permissions. Assembles everything in memory FIRST, so a mid-assembly failure never leaves a half-materialized run. **Refuses (exit 1, nothing written) a manifest whose after-graph does not validate** — the same acyclicity + guard-grammar arm `lint` runs, now unskippable at the registration act (7.456/MC14). | Touches cognitive-unit sources, catalogs, or `taskforce.csv` |

### What `lint` checks

Folder name ≡ `goal.md` name · cross-goal name uniqueness · identity fields present · thin goal
state and type in their enums · the goal-radius contract body is non-empty · CMP-4 goal-level
layout · `runs.csv` / `milestones.csv` / `taskforce.csv` parse · one live run per goal · every
taskforce row resolves to a REAL seat with a parseable `seat.md` · the `after` graph is acyclic
(guards `ref[field=value]` stripped, alternates `a|b` split) and every predecessor names a real
seat row · **every guard and alternate is well-formed** (below) · each seat's binding matches the
`taskforce.csv` row it was copied from · every
frontmatter cognitive-unit reference has its assembled block in the body · permissions well-formed
· dry-run dispatch emulation (would this seat launch under its resolved harness+model+effort — no
launch, no LLM call).

### The standard goal-folder artifacts `scaffold` writes (7.582 / owner ruling R21)

Six of the nine files are written from **deterministic templates in `goal_cli.py`** — module-level
strings, the `THREADS_SCHEMA` precedent. **No agent is in the path**, and two scaffolds of the same
goal name produce byte-identical files.

| Written | What it is |
|---|---|
| `CLAUDE.md`, `AGENTS.md` | the ROUTER, one per supported harness. It names the sibling artifacts and carries no content of its own. `AGENTS.md` is `CLAUDE.md`'s body behind a header saying so |
| `issues.md`, `decisions.md`, `doubts.md`, `gotchas.md` | the four **write-if-something** files — NOT logs. Nothing obliges an entry; an agent with nothing to note writes nothing |

`ROUTER_FILENAMES` is **measured, not assumed**: it is the distinct set of `guidance_file.convention`
values across every model package manifest (`orchestration/models/*/manifest.yaml`) — `CLAUDE.md`
(claude-code-cli) and `AGENTS.md` (codex-cli, kimi-code-cli, opencode). The API packages and
claude-code-native omit `guidance_file` deliberately: those workers load no workspace guidance file,
so no router of any name reaches them. A package adopting a third convention adds its filename to
that tuple and nothing else changes.

`write_standard_artifacts` is **skip-if-exists per file**. `scaffold` refuses an existing goal
outright so it never meets one — the guard lives in the writer because these are the files agents
write INTO, and an overwrite there is data loss. Scored by
`probes/probe-goal-scaffold-standard-files.py` (`--only goal-scaffold-standard-files`), whose two
mutants prove the presence arm and the no-clobber arm can each go red.

**Registry note:** the live `build-core-daemon-mvp` goal folder also carries `ideas.md`. R21's ruled
set is the FOUR files above; the fifth is **not** scaffolded here — adding it would be this tool
minting a convention no ruling names.

### The guard-grammar arm (7.426) and its carve-out

`lint <goal>`, `check-acyclic <file>` and — since **7.456 / MC14** — the `materialize` ACT validate
the `after` member grammar **on top of** acyclicity. Two rules, and a refusal names the one it broke:

| Rule (the finding's `check` string) | Refuses |
|---|---|
| ``guard grammar `ref[field=value]` `` | a member carrying brackets that is not a guard — `a[nokey]`, `a[k=v]x`, an unclosed `a[k=v`. `parse_after_member` hands such a token back WHOLE, so the edge-runner looks up a seat literally named `a[nokey]`, finds nothing, and the edge is permanently unmet with no reason given. Refused at registration instead. |
| ``alternate grammar `a|b` `` | an empty alternate limb — `a|`, `|b`, `a||b`. An alternate joins two NAMED predecessors. |

**Grammar only.** The arm rules on ADMISSIBILITY, never on whether a guard is satisfied — that
evaluation is the edge-runner's (CMP-25), against the predecessor's validated output. A clean
verdict here says the manifest is well-formed, nothing about how it will route.

**One decomposition, imported.** The member grammar is decomposed in exactly one place in this
system — `coord.py`'s `parse_after_member` (7.424/W1 collapsed the two readings that used to
exist). `after_member_grammar()` imports it; there is no copy of the grammar in this file, and if
the import fails the check REFUSES rather than reading clean. The same import backs
`check_acyclic`'s edge extraction, which previously truncated a member at its first `[` — under
that reading `a[g=y]|b` lost limb `b`, and a cycle through it was reported clean (the
strip-then-split defect #3386, closed here; the selftest keeps the control).

> **⚠ CARVE-OUT — the proof surface of this arm is the TEST GOAL, and nothing here is wired into
> the live room.** The arm activates only where a verb invokes it (`lint`, `check-acyclic`, and
> since 7.456/MC14 `materialize`, where it REFUSES the act rather than reporting on it); no
> daemon lane, job or watcher calls it, and 7.426 performed **no live-room wiring**. Live-room
> adoption is a separate, later act behind `r-cutover-gated`
> (`.rbtv/goals/build-core-daemon-mvp/decisions.md`). What was measured, not assumed: the live
> `build-core-daemon-mvp` run-3 `taskforce.csv` (356 rows, 331 members, 6 guarded, 0 alternates)
> yields the SAME two lint findings before and after this change — the arm adds none there. That
> is a measurement of one package, not a licence to adopt.

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

`selftest` exercises scaffold (+ its four refusals), `goal-kind` (the default stamped when
`--kind` is omitted, an explicit `--kind` round-tripping to frontmatter, the projected column, and
the lint PAIR — a key-less descriptor raising no finding *beside* an out-of-enum value raising
one, because the clean arm alone would also pass if the check never fired), the read-only property
of lint, name/layout
violation rejection, cycle rejection, the full assembly (frozen assembled refs, `@latest` invoked
refs, stamped XML blocks, loader stubs not inlined), refuse-without-`--force`, `--force`,
refuse-without-`--catalog-root`, reindex's fail-loud-and-leave-untouched behaviour, and the
guard-grammar arm (clean guarded manifest, malformed guard, empty alternate limb, a cycle through
an alternate limb, and the control that the arm stays silent on a clean file). Run it after
ANY edit to `goal_cli.py` — it must exit 0.

The one row the selftest CANNOT carry is that the grammar is imported rather than copied: it would
have to mutate `coord.py`. That control runs on a mirrored scratch tree — mutate
`GUARDED_MEMBER_RE` there and a manifest that validated clean must go red. Recorded for 7.426 in
`runs/run-3/planning/briefing-m6-remainder-drain/mrd-w3-lint-arm-record.md`.

A selftest sits inside its own blast radius, so it is not sufficient evidence on its own: vary the
invocation (bare, under `timeout`, via `sh -c`, from another cwd, absolute path, piped/no-tty) and
prove the assembly against real captured content, not only its own fixtures.
