# installer — the SECOND rbtv installer (KG-shape components)

`rbtv-install` — installs **CMP-5 component-first** components and realizes their exposure
through **CMP-12's** adapter matrix. Built for core-build task 7.64.

The first installer (`install.py` at the repo root) is **untouched** and keeps serving today's
flat module components. The two coexist deliberately: this one works with the new standards,
the old one is not migrated. Nothing here modifies, wraps, imports, or re-implements it.

The contract and reasoning behind the shapes below are the registry's — `CMP-5`
(component databases), `CMP-12` (exposure adapter matrix), `CMP-3` (mirror), `CMP-1`
(runtime root / install model), `concepts/exposure-manifest.md`, `concepts/module-entry-point.md`
— and are never restated here (`PRIN-11`).

```
rbtv-install list     --catalog-root R                what is installable under R
rbtv-install install  --catalog-root R --target W     install into workspace W
rbtv-install doctor   --catalog-root R                can this tool work against R?
rbtv-install selftest                                 this tool's own mechanics
```

Flags: `--module M` · `--component C` · `--harness claude,codex,opencode` · `--dry-run` ·
`--json` (accepted on either side of the subcommand).

**Exit codes** (the `sd-graph` / `rbtv-goal` / `daemon-operator` convention): `0` success ·
`1` refusal or not-found · `2` usage error.

## `--catalog-root` is explicit, required, and never inferred

A catalog root is **either** the rbtv repo **or** an install's `.rbtv/mirror/`. The tool cannot
tell them apart, by design — `CMP-3` makes them equivalent, so moving meta components from
`mirror/meta/` into `rbtv/` later must change nothing about how components work.

It is never guessed. With the CMP-5 tree unbuilt in the repo (issue `G-109`), a guessed root
would resolve silently into a tree with no such shape, and a wrong-but-plausible install is
worse than a refusal naming its reason.

**Proven, not asserted:** the same real component content placed at a mirror-shaped root and a
repo-shaped root installs to **byte-identical** trees (all file hashes equal), and a one-byte
mutation in either root is **detected** by that same comparison — so the check discriminates
rather than passing vacuously. No executable line branches on root identity; every occurrence of
"mirror" in this capability is a docstring or a help string.

## What it installs

| Input | Realized as |
|---|---|
| `<module>/module.md` (module entry point) | the module **discovery skill** on each harness — the pushed index of the progressive-disclosure ladder (`PRIN-3`) |
| each row of `<component>/exposure.csv` | its `method` resolved through CMP-12's map to that harness's native location, or its recorded fallback |
| `entry-point` = `prompts.csv#<row-id>` | the **assembled** cognitive units of that catalog row, in column order — content is a file, arrangement is a row |
| `entry-point` = a file path | that file, delivered in place |

Install state follows `CMP-1`'s install model: `.rbtv/modules/{module}/status.json` (**first-run
seed only**) + `settings.json` + an appended `settings-history.jsonl`. **`server.json` is never
written here** — it is the daemon's, and `installed` is DERIVED from it, never read as a stored
boolean.

## The four refusals

1. **A method outside the canonical vocabulary** (`skill · command · rule · hook · sub-agent ·
   agents.md · config`, `d-exposure-method-canon`) is refused, never guessed at.
2. **A (method, harness) pair CMP-12 records no realization for** — `hook` on opencode,
   `sub-agent` on codex — is skipped with its reason named, per harness, so the other harnesses
   still install.
3. **A pinned unit version** (`unit@v3`) is refused: without the repo-root
   `cognitive-units-index.csv` there is no table mapping a version-id to a commit, so accepting
   a pin would serve whatever is on disk under a name promising otherwise.
4. **A `hook` or `config` row** is refused — see below.

## Shared files: markdown is edited, structured config is refused

An `agents.md` row targets a file the **workspace** owns — `CLAUDE.md`, `AGENTS.md`. Overwriting
one whole would destroy hand-authored content that is not ours, so the row edits a managed
marker block:

```
<!-- rbtv-install:start id=<part-id> --> … <!-- rbtv-install:end id=<part-id> -->
```

Re-installing replaces the block **in place** — a changed unit updates the block rather than
appending a second one — and content outside it is untouched.

⚠ **`hook` and `config` rows are REFUSED, and this was a defect found by running rather than
reading.** Their targets are structured config files (`.claude/settings.json`,
`.codex/hooks.json`, `opencode.json`), and `<!-- … -->` **is not valid JSON**: an early build of
this capability appended a marker block to a real `settings.json` and left it unparseable —
corrupting exactly the content the marker mechanism exists to protect. Merging into those files
needs the harness-config schema, which the registry marks Phase-3/4 design output, so there is
nothing to implement against yet. The row is therefore skipped with its reason named while every
other row still installs. The selftest asserts the file stays **byte-identical** and still parses
as JSON — a bar that fails by construction on the pre-fix code (verified by mutation: 5 checks
go red).

## ⚠ STAND-IN, pending CMP-5 — do not let this harden into the real schema

`CMP-5` specifies a repo-root `cognitive-units-index.csv` mapping a version-id to
(commit, filepath). **It does not exist anywhere** (issue `G-109` — the component-database layer
is designed but unbuilt). Two consequences, and they are different:

- **Version resolution is a STAND-IN.** `@latest` freezes to `latest+sha256:<12 hex of the
  unit's bytes>`. This preserves the assembly lockfile's FUNCTION — a frozen, verifiable
  reference — without inventing the index schema. It is **not** the settled scheme.
- **Name resolution needs no index, and this is a correction to the briefed premise.** Every
  cognitive-unit file declares its own `id:` in frontmatter, and the catalog's reference id is
  **not** the file stem (`master-role` → `roles/master.md`). The pool is indexed by DECLARED id,
  which is deterministic and complete today.

When CMP-5's index lands, replace the freeze and delete `STANDIN_VERSION_PREFIX`; nothing else
in this capability depends on the stand-in.

## Registry divergences — FLAGGED for transcription, never applied as record edits

Per 7.64's criteria this capability reports divergences and repairs none of them. The full list
with evidence is the run's: `runs/run-2/seats/C3-installer/premise-audit.md`. The two that bear
on a reader of this file: the rbtv repo has **no KG-shape module** other than `ignite/module.md`
added here (D2), and the capability-folder shape stated at `rbtv/CLAUDE.md:43` carries a
component level that **both shipped precedents omit** (D1) — this capability follows the shipped
precedent and coins no third shape.
