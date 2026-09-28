---
description: Deterministic lint over a component folder — manifest canon, seat/manifest integrity, dangling refs, kind sections, dimension roster, carried-block drift, and the interactive fallback field.
---
# component-lint

One growing lint over any rbtv component folder. Detection only — it never writes. Owner ruling D19 picks the roster; design rationale is the mechanization survey § 3 (one tool, one parse, one exit code).

## What it checks

| check id | what |
|---|---|
| `exposure-canon` | `exposure.csv` seven-column header, closed `method` and `part-kind` vocabularies, no method-less row, no duplicate part-id; `method=path` rows: entry-point exists on disk, `rbtv-cli`/`description` empty. Plus the W6 surfaces: a `write-roots` cell is legal on `method=path` rows ONLY, every entry carries the in-cell danger marker `!`, takes the entry-point grammar (`ws:` base, `..` refused) and names a directory that exists; and `skill-cli-dangling` — every `exposes-cli:` ref on a `method=skill` row's entry-point file resolves to a `method=path` row (`rbtv:` refs are materialize's to resolve and are not judged here) |
| `seat-integrity` | every `seats.csv` executor/task resolves to a pool file; no orphan prompt/task; `id:` == filename stem; every manifest row resolves to a seat; every `after` ref (guards parsed, alternation inside a guard preserved) resolves to a manifest row; the graph is acyclic; `Modality` in vocabulary |
| `task-no-context` | no task file carries a `context:` frontmatter field — the field is DELETED (W6/R3, `references/file-task.md`); standing pointers live in the task's own `<scope>` and instruments in the paired prompt's `<resources>`. It REPLACED `context-refs` on this slot: over a field no author may write, a resolution check could only ever pass |
| `task-no-capabilities` | no task file carries a `capabilities:` frontmatter field — the field is RETIRED (`d-task-capabilities-retired`, `references/file-task.md`); the paired prompt's `exposes:`/`<resources>` carry the means |
| `kind-sections` | per carrier kind: required sections present, n-a sections absent, no duplicate section of one kind, canonical order — matrix and order both HARDCODED **and** cross-checked against the KG `cognitive unit` record and the `file-prompt.md`/`file-task.md` guides, so the copies police each other |
| `dimension-roster` | the check-dimension set is one set across three homes — dimension task files, `seats.csv` pairings, manifest rows — each with a non-empty kill-criteria block and its dimension named in seat description and manifest i/o |
| `carried-blocks` | byte-diff of EVERY `<tag source="path[#anchor]">` block against `<!-- name:start -->`/`<!-- name:end -->` in its source (generalizes the ethos-specific drift checker) |
| `interactive-fallback` | `human-interactive: yes` ⇒ a typed `fallback:` (`park`/`default-and-disclose`/`block-and-queue`); `fallback:` present ⇒ the flag or an `interactive`-modality row; an `interactive` row's prompt carries the flag |
| `fork-discharge` | every manifest guard `pred[key=value]` is SERVABLE: `pred`'s prompt declares, under its `<io-spec>` `## Outputs` heading, a `.json` artifact stating a top-level field `key`. An alternate is checked limb by limb. Outputs written only as prose do not provide a checkable guard value |

| `exposes-body-match` | `exposes:` and the prompt body name the same instruments in both directions. Unused declarations and undeclared tools named by a dispatch step are findings; skill and workflow names in ordinary prose are not treated as dispatches |
| `resources-coverage` | each declared `path`, `skill`, or `sub-agent` used by the prompt gets its own `<resources>` bullet naming when and why it is used. A missing section or a bullet over the 280-character ceiling is a finding. `command`, `rule`, and `hook` entries are exempt |

Detail — options, per-check applicability, the exit contract — is in the tool's own `-h`.

## How to run

From the vault root:

```bash
python -B 3-resources/tools/rbtv/meta/planning/capabilities/component-lint/tool/component_lint.py \
  --root 1-projects/build-ignite
python -B .../component_lint.py --component <component-path> --json
python -B .../component_lint.py --list-checks
```

`--root` declares an extra root a source reference may resolve against. `--component` targets any component folder; a check whose surfaces are all absent is reported SKIP, never silently passed. `--kg` optionally cross-checks the built-in section matrix against a query command; it is not required. `-B` keeps `__pycache__` out of the mirror.

## I/O

- Input: a component folder; an optional read-only `--kg` query for a matrix cross-check. The vocabulary cross-checks read the references of the component this tool SHIPS IN (`--home`), never the linted one — a cross-check indicts the tool's own hardcoded copy.
- Output: a census line, one `SKIP` line per non-applicable check, one `BLOCKED <check>: <reason>` line per check whose precondition broke (that check alone did not run — the others still did, and the run exits 2), one line per finding (`FAIL` gates, `INFO` reports), and a summary line carrying the counts. `--json` emits census + `checks-run` + `checks-skipped` + `checks-blocked` + findings + `fail-count`.
- Exit codes: `0` clean · `1` findings · `2` broken preconditions (component absent, unreadable file, unparseable frontmatter, KG query unavailable).

**Accept a run on the CENSUS, never on the exit code alone.** A green run over files the tool failed to discover is a false green — invisible rather than loud. Every check whose surface exists but yielded zero objects fails on that ground alone.

Self-test (every check ships a red arm — a fixture that makes it fail for the right reason):

```bash
python -B 3-resources/tools/rbtv/meta/planning/capabilities/component-lint/tool/test_component_lint.py
```
