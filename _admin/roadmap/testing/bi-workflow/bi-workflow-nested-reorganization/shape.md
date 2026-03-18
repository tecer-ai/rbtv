# Shape - BI Workflow Nested Reorganization

> **Purpose:** This document captures shaping decisions and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- Reorganize 28 flat `bi-*` workflow folders into a nested hierarchy under `bi-business-innovation/`
- Fix all path references across the codebase so workflows, agents, config, and docs resolve correctly

**What this does NOT include:**
- Changing workflow logic, step content, or output behavior
- Introducing `{bmad_rbtv}` variables to replace hardcoded paths (future improvement)
- Creating M5/M6 folders (referenced but not yet implemented)
- Changing how project memos store `stepsCompleted` framework IDs

### Target Structure

```
_bmad/rbtv/workflows/
└── bi-business-innovation/              ← master (stays in place)
    ├── workflow.md
    ├── data/
    ├── templates/
    ├── steps-c/
    ├── bi-m1/                           ← hub moves inside master
    │   ├── workflow.md
    │   ├── data/
    │   ├── steps-c/
    │   ├── bi-m1-five-whys/             ← framework moves inside hub
    │   ├── bi-m1-lean-canvas/
    │   ├── bi-m1-competitive-landscape/
    │   ├── bi-m1-jobs-to-be-done/
    │   ├── bi-m1-problem-solution-fit/
    │   └── bi-m1-working-backwards/
    ├── bi-m2/
    │   ├── bi-m2-assumption-mapping/
    │   ├── bi-m2-leap-of-faith/
    │   ├── bi-m2-pre-mortem/
    │   ├── bi-m2-tam-sam-som/
    │   ├── bi-m2-technology-readiness-level/
    │   └── bi-m2-unit-economics/
    ├── bi-m3/
    │   ├── bi-m3-brand-archetypes/
    │   ├── bi-m3-brand-positioning/
    │   ├── bi-m3-brand-prism/
    │   ├── bi-m3-brandbook/
    │   ├── bi-m3-golden-circle/
    │   ├── bi-m3-messaging-architecture/
    │   └── bi-m3-tone-of-voice/
    └── bi-m4/
        ├── bi-m4-conversion-centered-design/
        ├── bi-m4-design-context/
        ├── bi-m4-heuristic-evaluation/
        └── bi-m4-user-flow-ia/
```

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Folder names stay the same | Keep `bi-m1-five-whys/` not just `five-whys/` | Preserves grep-ability and framework ID consistency in project memos |
| Master folder stays in place | `bi-business-innovation/` does not move | It's the root — everything else moves into it |
| Phase 1 does all git moves at once | Single batch, not per-milestone | Git history is cleaner, and all relative paths break simultaneously anyway |
| Parallel phases for path fixes | One phase per milestone + separate phases for config and docs | Enables parallel agent execution across independent file sets |
| No microstep files | Plan is detailed inline | User requested clear inline instructions for cheaper agents |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| `_bmad/rbtv/` is a git repo | Repository structure | All moves MUST use `git mv` |
| `bootstrap.py` and `bmad-help.csv` are runtime-critical | Framework architecture | Must be updated correctly or all BI workflows break |
| `mentor-help.xml` constructs paths dynamically | Agent tasks | Uses `bi-m{N}` pattern — needs structural change |
| Relative paths change depth by 1-2 levels | Nesting adds depth | Every `../bi-mN/` and `../bi-mN-framework/` reference must be recalculated |
| Admin/plan docs are mostly historical | Completed plans, done items | Lower priority but still need updating for consistency |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Plan structure | "separated in phases... so I can execute each phase in parallel, by a different agent" | Phases split by independent file sets (per-milestone + config + docs) |
| 2 | Task granularity | "no need for microstep files... just make the plan very clear" | Detailed inline task descriptions with exact find-replace patterns |
| 3 | Phase ordering | "first task is the actual moving using git mv, then the other agents come in place" | Phase 1 = git moves, all subsequent phases = path fixes |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Phase parallelism | Wants parallel execution by separate agents | Identified independent file sets per milestone | Phases 2-5 (one per milestone) can run in parallel; Phase 6-7 (config, docs) run after |

---

## Standards Applied

### Path Reference Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Relative paths for workflow internals | All `../` and `./` paths within workflow files must be recalculated for new nesting depth |
| Variable paths for cross-module refs | `{bmad_rbtv}`, `{bmad_core}`, `{bmad_bmm}` paths are NOT affected by this reorganization (they resolve from config) |
| Project-root paths in config | `bootstrap.py` and `bmad-help.csv` use project-root-relative paths that must change |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Phase 1 must complete before any other phase starts | Git moves must land before path fixes can be validated |
| Phases 2-5 are independent and parallelizable | Each phase operates on a disjoint set of files (M1, M2, M3, M4) |
| Phase 6 depends on Phases 2-5 completing | Config/agent files reference all milestones — need final paths |
| Phase 7 can run after Phase 1 | Admin/plan docs are historical — no runtime dependency |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Path Reference Cheat Sheet

This section documents every path pattern that changes, organized by reference type. Executing agents MUST consult this section.

### Depth Changes After Reorganization

| File Location (post-move) | Old depth from `workflows/` | New depth from `workflows/` | `../` delta |
|---------------------------|----------------------------|----------------------------|-------------|
| `bi-business-innovation/` (master) | 1 | 1 | 0 (no change) |
| `bi-m1/` (hub) | 1 | 2 | +1 |
| `bi-m1-five-whys/` (framework) | 1 | 3 | +2 |
| `bi-m2/` (hub) | 1 | 2 | +1 |
| `bi-m2-assumption-mapping/` (framework) | 1 | 3 | +2 |
| `bi-m3/` (hub) | 1 | 2 | +1 |
| `bi-m3-brandbook/` (framework) | 1 | 3 | +2 |
| `bi-m4/` (hub) | 1 | 2 | +1 |
| `bi-m4-design-context/` (framework) | 1 | 3 | +2 |

### Pattern A: Milestone hub `workflow.md` referencing master

**Old:** `../bi-business-innovation/workflow.md`
**New:** `../workflow.md` (master is now the direct parent)

### Pattern B: Milestone hub `steps-c/step-01-init.md` referencing master

**Old:** `../../bi-business-innovation/workflow.md`
**New:** `../../workflow.md`

### Pattern C: Milestone hub `workflow.md` referencing its frameworks

**Old:** `../bi-m1-five-whys/workflow.md` (sibling)
**New:** `./bi-m1-five-whys/workflow.md` (child)

### Pattern D: Milestone hub `steps-c/step-01-init.md` referencing its frameworks

**Old:** `../../bi-m1-five-whys/workflow.md` (up to workflows/, then into sibling)
**New:** `../bi-m1-five-whys/workflow.md` (up to hub, then into child)

### Pattern E: Framework `workflow.md` referencing its milestone hub

**Old:** `../bi-m1/workflow.md` (sibling)
**New:** `../workflow.md` (direct parent)

### Pattern F: Framework `steps-c/*.md` referencing milestone hub

**Old:** `../../bi-m1/workflow.md`
**New:** `../../workflow.md`

### Pattern G: Framework `steps-c/synthesis.md` referencing `founder-process.md`

**Uses `{bmad_rbtv}` variable:** `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md`
**No change needed** — variable-based path, master folder didn't move.

### Pattern H: Master `steps-c/step-02-milestone-select.md` referencing milestone hubs

**Old:** `../../bi-m1/workflow.md`
**New:** `../bi-m1/workflow.md` (hub is now a child of master)

### Pattern I: `bootstrap.py` and `bmad-help.csv`

**Old path:** `_bmad/rbtv/workflows/bi-business-innovation/workflow.md`
**No change** — master folder didn't move.

### Pattern J: `mentor-help.xml` dynamic paths

**Old:** `{project-root}/_bmad/rbtv/workflows/bi-m{N}/workflow.md`
**New:** `{project-root}/_bmad/rbtv/workflows/bi-business-innovation/bi-m{N}/workflow.md`

### Pattern K: `founder-process.md` table references

**Old:** `bi-m1/workflow.md`, `bi-m1/steps-c/step-01-init.md`
**New:** `bi-business-innovation/bi-m1/workflow.md`, `bi-business-innovation/bi-m1/steps-c/step-01-init.md`
(These are display-only table entries — they need updating for accuracy but are not runtime-resolved.)

---

## Decisions and Discoveries

<!-- Decisions and discovery entries will be appended below this line -->

2026-03-17 | Phase 1 complete — 198 files renamed via `git mv`. 4 hubs + 23 frameworks nested under `bi-business-innovation/`. Quality review: APPROVED. Note: `_config/__pycache__/` is untracked (pre-existing, unrelated).
2026-03-17 | Phase 6 (p6-1) complete — Fixed all M4 path references: hub `workflow.md` (Pattern A + C), hub `steps-c/step-01-init.md` (Pattern B + D), all 4 framework `workflow.md` files (Pattern E), synthesis files in CCD and heuristic-evaluation (Pattern F). Total: 8 files modified.
2026-03-17 | Phase 4 complete — M2 hub and 6 framework path fixes applied. Pattern A: `bi-m2/workflow.md` parentWorkflow fixed. Pattern C: framework routing table updated to `./` (child). Pattern B: step-01-init.md `../../bi-business-innovation/workflow.md` → `../../workflow.md` (2 occurrences). Pattern E: all 6 framework workflow.md parentWorkflow fixed to `../workflow.md`. Pattern F: synthesis steps in leap-of-faith, assumption-mapping, tam-sam-som, pre-mortem updated. Discovery: milestone-overview.md in data/ and step-01-init.md framework routing were already correct for new structure (frameworks are children of hub).

2026-03-17 | Phase 3 (p3-1) complete — Fixed all M1 path references. Files changed: `bi-m1/workflow.md` (Pattern A + C), `bi-m1/steps-c/step-01-init.md` (Pattern B), 6× framework `workflow.md` (Pattern E), 6× framework synthesis steps (Pattern F: `../bi-m1/workflow.md` → `../../workflow.md`). Confirmed: `../bi-m1-{name}/workflow.md` in hub's steps-c and data/ are already correct (resolve to child after move).

2026-03-17 | Phase 8 (p8-1) complete — Fixed path references in admin docs and historical plans. Bulk replaced `workflows/bi-mN/` and `workflows/bi-mN-{name}/` patterns across 59 admin roadmap files + 1 dedup PRD file + 2 manual glob-pattern fixes (shape.md bi-m4-follow-up, prd-no-content-duplication). Also updated prose path references in p2-1.task.md (completed Lavoisier task). Zero double-prefix issues. Zero stale `workflows/bi-m[1-4]` patterns remain in admin roadmap. Project memo files (tecer-biz, tennis-arte, ayutan) had no matches and required no changes.

2026-03-17 | p9-compound complete — learnings.md populated: ripgrep PATH workaround (Cursor-bundled rg.exe), PowerShell `&&` → `;` correction, `step-02-milestone-select.md` `../bi-mN/` false-positive note. Memory entries written to `.claude/memory/tools/powershell.md`.

2026-03-17 | p9-refs complete — Full-codebase grep validation passed all 4 checks. CHECK 1: `rg "workflows/bi-m[1-4]/"` in `_bmad/rbtv/` → zero matches. CHECK 2: `rg "\.\./bi-business-innovation/"` inside `bi-business-innovation/` → zero matches. CHECK 3: `../bi-mN/` refs inside `bi-business-innovation/steps-c/` → only valid updated paths in `step-02-milestone-select.md` (correct, Phase 2 targets). CHECK 4: framework refs in hub workflow.md files → zero old-style patterns. Structure: no `bi-m*` at workflows root; `bi-business-innovation/` contains `bi-m1/`–`bi-m4/` + master files. Variable paths (`{bmad_rbtv}`) preserved in 19 files.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| Path reference exploration (context-distill agent) | Complete catalog of all path patterns used in BI workflow files |
| BI workflow structure exploration (explore agent) | Full tree of 28 folders, 203 files, 84 directories |
| Admin/config reference exploration (explore agent) | 62 admin files, 12 plan files, 2 critical config files |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| This shape.md, Path Reference Cheat Sheet section | Exact find-replace patterns for all path types | Every phase |
