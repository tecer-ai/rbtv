---
description: "Use BEFORE editing anything under rbtv ignite/ or meta/ and AGAIN at the close of that edit"
tags: [ignite, memory]
exposes-cli:
  - coord/file-issue
  - rbtv:core/rbtv-embed-search
---

# work-on-ignite

Ten days of agents fixing ignite patch-by-patch kept surfacing new defects — the loop only turned around once agents read git history, then a file derived from it, before touching code. This skill makes that structural: read the build memory at `ignite/work-on-ignite/memory/` BEFORE editing, file to it AFTER. Full mechanics (layout, kinds, entry/index shape, distillation): `ignite/work-on-ignite/references/build-memory.md` — this file is the WHEN, that file is the WHAT.

Binds: the `ignite-engine` goal's seats at build/closure, AND any other console session or goal seat editing `ignite/` or `meta/`.

## Procedure

1. **Name the components you will touch.** A component is a top-level folder under `ignite/` (`bridges capabilities cli config deploy engine gateway injection-ladder jobs launch-profiles lib server skills team-kit work-on-ignite`) or one of the four `meta/` trees (`meta-installer meta-leader meta-master meta-planning`). List every one your edit will reach — a cross-component fix is filed once, under the component the fix lands in, with the others named on its index line.

2. **Read each component's memory** — for every component named in step 1, read `ignite/work-on-ignite/memory/<component>/_summary.md`, `_issues.md`, and `_creations.md`.

3. **Semantic + deterministic search**, both required:
   - `rbtv embed-search query --root /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/work-on-ignite/memory "<symptom or feature>"` — once for the symptom/feature you're working, once more for the specific file paths you will touch.
   - Grep floor (never skip even if embed-search answered): `grep -rn '<component>\|<path-fragment>' /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/work-on-ignite/memory/*/_issues.md /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/work-on-ignite/memory/*/_creations.md`

4. **List what you consulted.** Every entry id (filename) surfaced by steps 2–3, and any ATTENTION bullets carried by it. These ids go into your proposal AND into your commit message as `memory: <ids>` — they are the citation that lets the next reader trust the read happened.

5. **Read recent creations before you write.** For each component you touch, skim its newest `_creations.md`/`_issues.md` entries to learn the motivation behind the code you're about to change — a decision you'd otherwise blindly reverse. Then do the work.

6. **Before closing the sitting, file.** Write the body to the contract in `ignite/work-on-ignite/references/build-memory.md` § Entry content contract. Run the quality-gate questions (self, or a judge seat of a different model); any "no" rewrites the body before filing. Then:
   ```
   file-issue memory file --component <name> --kind issue --title "<title>" \
     --body-file <path-to-contract-body> --commit <hash> --deployed yes|no|at \
     --pin <probe-path|NONE> --components <other,other> --attention "<bullet>"
   ```
   For every new thing added, removed, renamed, or refactored, run the same command with `--kind creation` (or `--kind change` for a refactor/removal/rename) and a body carrying the creation headings. Templates: `ignite/work-on-ignite/memory/_templates/issue.md`, `ignite/work-on-ignite/memory/_templates/creation.md`. One index line per entry, ≤400 chars (the command enforces this). The command refuses bodies missing the headings or carrying placeholder phrases.

7. **If the filing command refuses, report the refusal.** Never hand-edit `_issues.md`, `_creations.md`, or any index — the command is the only writer. A refusal you cannot resolve is a loose end in your report, not a workaround.

## What this is not

Not a task list, not the open-issue register, not a place for open questions — those go to the calling goal's own `issues.md` / `loose-ends.md`, or, for a system defect on this surface, through `file-issue file` (skill `file-system-issue`). Memory here is the CLOSED side: only fixed issues and landed creations, cited against the deployed tree.
