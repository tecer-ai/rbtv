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
| `declared-mode-carry` | the produced `workflow.md` declares `default-execution-mode:` exactly as the planning run's `goal.md` carries it — dropped, altered, and invented declarations all fail; absent on both sides stays legal (the creation path derives from Modality). Needs the `--goal` + `--workflow` pairing, else SKIP |
| `interactive-fallback` | `human-interactive: yes` ⇒ a typed `fallback:` (`park`/`default-and-disclose`/`block-and-queue`); `fallback:` present ⇒ the flag or an `interactive`-modality row; an `interactive` row's prompt carries the flag |
| `fork-discharge` | every manifest guard `pred[key=value]` is SERVABLE: `pred`'s prompt declares, under its `<io-spec>` `## Outputs` heading, a `.json` artifact (a backticked token carrying a `/` and an extension) stating a top-level field `key` — the edge runner's own read. An alternate is checked limb by limb (a bare limb needs nothing). Outputs written as prose declare nothing, so the guard reads UNEVALUABLE and the fork neither opens nor dies |

| `exposes-body-match` | `exposes:` and the prompt BODY name the same instruments, both directions: every declared entry's LAST path segment appears somewhere in the body (an unused grant outlived its procedure), and every `exposure.csv` part-id named in a body is declared in some `exposes:` group (a caged seat cannot reach what it was not granted) — this second direction reads only `method=path` parts plus `method=sub-agent` parts mentioned on a line that talks dispatch/fan-out, and skips `method=skill` and `part-kind=workflow` rows, whose names double as prose vocabulary (measured over the live pool 2026-08-12). The standing checkout grant `path: [rbtv:ignite/coord/coordinate]` is EXEMPT from the first direction — every seat holds it, few name it in prose. Matches inside a carried `<!-- ethos:start -->…<!-- ethos:end -->` block, and a prompt naming its own part-id, do not count |
| `resources-coverage` | workflow-authoring-checklist.md §2: every `exposes:` entry of method `path`/`skill`/`sub-agent` gets its OWN bullet inside the prompt's `<resources>` section — a FAIL names the part-id and distinguishes itself from `exposes-body-match` (this check reads the `<resources>` SECTION only). A prompt with non-exempt entries but no `<resources>` section at all is ONE finding, not one per entry. Every `<resources>` bullet that NAMES a declared instrument (top-level `- ` item, leading `- ` and leading backtick token stripped) over 280 measured characters FAILS; no grandfather list exists, deliberately — an over-cap instrument bullet is trimmed, and prose about a file, folder, or output contract answers to no ceiling. Exempt from needing a bullet at all: the standing `rbtv:ignite/coord/coordinate` checkout grant, and every `command`/`rule`/`hook` entry |

Detail — options, per-check applicability, the exit contract — is in the tool's own `-h`.

## How to run

From the vault root:

```bash
python -B 3-resources/tools/rbtv/meta/planning/capabilities/component-lint/tool/component_lint.py \
  --root 1-projects/build-ignite
python -B .../component_lint.py --component <component-path> --json
python -B .../component_lint.py --list-checks

# the execution-mode carry check, at the edge of the task that authored the
# workflow definition a planned taskforce produced:
python -B .../component_lint.py --component <component-path> \
  --check declared-mode-carry --goal .rbtv/goals/<goal> --workflow <workflow-name>
```

`--goal` and `--workflow` are declared TOGETHER or not at all (half the pairing is exit 2, never a quiet skip): `--workflow` names the definitions THIS goal produced, so the check never widens onto workflows the component already held — those declare their own mode and would fail for the wrong reason.

`--root` declares an extra root a declared path may resolve against — since `context:` was deleted its one consumer is `carried-blocks`, whose carried-block source references may name a tree outside the component (the planning component's blocks cite `system-definition/`, whose home on this vault is `1-projects/build-ignite/`). `--component` targets any component folder; a check whose surfaces are all absent (a produced workflow has `taskforce.csv` and `seat.md`, not `seats.csv` and `prompts/`) is reported SKIP, never silently passed. `-B` keeps `__pycache__` out of the mirror.

## I/O

- Input: a component folder; a read-only KG query command, `--kg` (for the `kind-sections` cross-check). The vocabulary cross-checks read the references of the component this tool SHIPS IN (`--home`), never the linted one — a cross-check indicts the tool's own hardcoded copy.
- Output: a census line, one `SKIP` line per non-applicable check, one `BLOCKED <check>: <reason>` line per check whose precondition broke (that check alone did not run — the others still did, and the run exits 2), one line per finding (`FAIL` gates, `INFO` reports), and a summary line carrying the counts. `--json` emits census + `checks-run` + `checks-skipped` + `checks-blocked` + findings + `fail-count`.
- Exit codes: `0` clean · `1` findings · `2` broken preconditions (component absent, unreadable file, unparseable frontmatter, KG query unavailable).

**Accept a run on the CENSUS, never on the exit code alone.** A green run over files the tool failed to discover is a false green — invisible rather than loud. Every check whose surface exists but yielded zero objects fails on that ground alone.

Self-test (every check ships a red arm — a fixture that makes it fail for the right reason):

```bash
python -B 3-resources/tools/rbtv/meta/planning/capabilities/component-lint/tool/test_component_lint.py
```
