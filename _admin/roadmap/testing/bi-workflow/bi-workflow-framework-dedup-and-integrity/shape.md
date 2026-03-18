# Shape - BI Workflow Framework Dedup and Integrity

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Add canonical assumption inventory to project-memo template (tiered: Existential / High / Lower / Founder Convictions)
- Rename output folder from `founder/` to `business-innovation/` across all BI workflow files (40+ files)
- Define content ownership mapping per milestone (which framework owns which concept)
- Add `## Prior Context` section to framework templates (builds on, inherits, adds)
- Add assumption merging instructions to all 22 framework synthesis steps
- Add conditional consistency gate (Party Mode recommendation) to synthesis steps
- Add deduplication verification to synthesis steps

**What this plan does NOT include:**
- Changes to existing project outputs already using `founder/` paths (backward compatibility for existing projects is not in scope)
- Automated reconciliation of cross-framework drift (gate is non-blocking recommendation only)
- M5/M6 workflows (not yet built)
- Changes to non-BI workflows except where they reference `founder/` paths (pitch workflow, tasks, config)

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Execution order | Default Structures → Consistency Gate → No-Duplication | Dependency chain: canonical assumptions is foundation; gate benefits from renamed paths; dedup generalizes the rule |
| Consistency gate mechanism | Party Mode in fresh context | Avoids token saturation; user-initiated via copy-paste prompt |
| Gate trigger threshold | ≥3 frameworks completed in milestone | Enough data for meaningful cross-checking |
| Folder rename target | `founder/` → `business-innovation/` | Function-based naming over persona-based |
| Assumption inventory tiers | Existential / High / Lower / Founder Convictions | Prioritization by criticality |
| Synthesis file grouping | All 3 synthesis enhancements in Phase 3 | Same 22 files — grouping reduces context switching |
| Path replacement strategy | Path-specific only | Preserve non-path uses of "founder" (e.g., "founder/team", "Founder Convictions") |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| 40+ files contain `founder/` path references | Codebase exploration | Bulk rename must be path-specific, not global find-replace |
| "founder" appears in non-path contexts | JTBD interview steps, label text | Replacement regex must distinguish path vs. prose usage |
| RBTV is its own git repo at `_bmad/rbtv/` | Repository structure | All changes are within one repo; use `git mv` where applicable |
| Synthesis step structure varies per framework | step-05 vs step-06 vs step-07 | Each synthesis file must be individually reviewed for insertion point |
| No M5/M6 workflows exist yet | Incomplete milestone coverage | Only M1-M4 synthesis steps (22 files) are in scope |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Plan scope | "the execution of bi-workflow folder" | All 3 CPs/PRDs in bi-workflow folder treated as one coordinated plan |
| 2 | Plan name | "provide a different name which covers all 3 prds/cps" | `bi-workflow-framework-dedup-and-integrity` |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Phase structure | Accepted proposed 4-phase structure | Proposed separating Foundation → Content Architecture → Synthesis Enhancement → Finalization based on dependency analysis | 4 phases with dependency-ordered tasks |
| 2 | Task granularity for synthesis steps | Implicit acceptance | Proposed 3 separate tasks (assumption merge, gate, dedup) touching same 22 files rather than per-milestone grouping | Separate tasks by concern; executing agent can batch per file |

---

## Standards Applied

### RBTV Workflow Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Atomic Files Rule | All modified files must remain self-contained and interpretable independently |
| No Content Repetition | Framework templates must reference via Prior Context, not restate |
| Mandatory Language | Instructions in synthesis steps use "must", "never", "always" |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Path-specific replacement | Every `founder/` replacement must be validated as a path reference, not prose |
| Non-path "founder" preservation | Grep for `founder` post-rename to verify no false positives |
| Synthesis insertion consistency | Same block structure across all 22 synthesis files |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

<!-- Decisions and discovery entries will be appended below this line -->

### 2026-03-17 — p1-1 Execution

**Task:** Add Canonical Assumption Inventory to project-memo template.

**What was done:** Inserted `## Canonical Assumption Inventory` section after Tenets and before Progress in `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md`. Four tiers: Existential Assumptions, High-Risk Assumptions, Lower-Risk Assumptions, Founder Convictions. Each tier has a placeholder table (ID, Assumption, Source Framework, Status, Evidence). Includes "Consolidated from" header and M2 guidance text. Founder Convictions tier includes explanatory note about intellectual honesty.

**Decision:** Used task file's column specification (ID, Assumption, Source Framework, Status, Evidence) rather than CP specification's columns (ID, Assumption, Category, Confidence, Falsification Test). The task file is the authoritative execution instruction.

### 2026-03-17 — p1-2 Execution

**Task:** Bulk rename `founder/` path references to `business-innovation/` across BI workflow files.

**What was done:** Replaced `founder/` → `business-innovation/` in path references across 44 files:
- Main BI workflow: workflow.md, step-01-project-setup.md, step-02-milestone-select.md, project-memo.md template, founder-process.md
- M1: bi-m1/workflow.md, step-01-init.md, + 6 framework workflow.md files
- M2: bi-m2/workflow.md, step-01-init.md (8 replacements), + 6 framework workflow.md files, bi-m2-leap-of-faith/step-01-init.md (6 M1 file refs)
- M3: bi-m3/workflow.md, step-01-init.md, + 7 framework workflow.md files
- M4: bi-m4/workflow.md, step-01-init.md, + 4 framework workflow.md files, 6 heuristic-evaluation step files, step-05-synthesis.md (2 refs)
- Pitch: step-02-context-gather.md (14 replacements)
- Tasks: update-bmad-config.xml, quality-review.xml, quality-evaluator-atomic-files.md

**Non-path occurrences preserved (3 matches):**
- `step-08-images.md`: "provided by founder/team"
- `step-03-interview.md` (x2): "founder/team knowledge"

**Files with no `founder/` references found (contrary to task expectation):** bootstrap.py, mentor-help.xml — no matches found, no changes needed.

### 2026-03-17 — p2-1 Execution

**Task:** Define content ownership mapping per milestone in founder-process.md.

**What was done:** Added `## Content Ownership Mapping` section to `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md` with ownership tables for M1 (8 concepts), M2 (6 concepts), M3 (7 concepts), and M4 (4 concepts). Each table maps Concept → Owning Framework → What later frameworks add. Each milestone identifies its first framework (concept originator).

**Discovery:** No separate template files exist per framework (`bi-m{N}-{framework}/templates/`). Output structures are defined inline in each framework's `step-01-init.md`. This impacts p2-2 — Prior Context sections must be added to init step files, not template files.

**Decision:** M4 framework order follows the workflow.md recommended sequence: User Flow & IA → Design Context → Conversion-Centered Design → Heuristic Evaluation. Build Prototype [B] and Testing Prep [F] are planned/not-yet-built and excluded from scope per plan constraints.

### 2026-03-17 — p2-2 Execution

**Task:** Add Prior Context sections to all non-first framework init step files.

**What was done:** Added `## Prior Context` section (Builds on / Inherits / This framework adds) to 19 framework `step-01-init.md` files — 5 in M1, 5 in M2, 6 in M3, 3 in M4. Section inserted after STEP GOAL and before MANDATORY EXECUTION RULES. Four first-framework files (Working Backwards, Leap of Faith, Brand Archetypes, User Flow & IA) were correctly excluded as concept originators.

**Discovery confirmed:** No separate template files exist per framework. Prior Context sections were added to `step-01-init.md` files instead, which serve as the initialization and context-loading entry point for each framework. This is the natural location because it instructs the executing agent about prior context before it begins execution.

### 2026-03-17 — p3-1, p3-2, p3-3 Execution (Batched)

**Tasks:** Add all three synthesis enhancements to all 22 framework synthesis files — deduplication verification, assumption inventory update, and cross-framework consistency gate.

**What was done:** All three blocks were added to all 22 synthesis files in a single pass per file (batched execution per plan's collaborative decision #2 — "executing agent can batch per file"):

**Block 1 — Deduplication Verification (p3-3):**
- Inserted BEFORE the main synthesis output write step in all 22 files
- 4 originator-variant files (first framework per milestone): Working Backwards (M1), Leap of Faith (M2), Brand Archetypes (M3), User Flow & IA (M4) — these state "this framework is the concept originator" with no checker logic
- 18 checker-variant files — these instruct: read ownership mapping, verify no restatement, reference owning framework, permit deltas only

**Block 2 — Assumption Inventory Update (p3-1):**
- Inserted AFTER the project-memo update step in all 22 files
- Consistent block across all files: review assumptions, check against canonical inventory, add new or update existing

**Block 3 — Cross-Framework Consistency Gate (p3-2):**
- Inserted AFTER assumption inventory update, before the menu/completion section in all 22 files
- Conditional on ≥3 frameworks completed in milestone's `stepsCompleted` array
- Non-blocking recommendation with copy-paste prompt template
- Milestone number (M1/M2/M3/M4) correctly specified per file

**Step numbering:** All subsequent steps in each file were renumbered to maintain sequential ordering.

**Decision:** Batched all three tasks into a single pass per file to minimize context switching and ensure consistent insertion ordering. The plan's synthesis block ordering rule (dedup → main synthesis → assumption merge → consistency gate → completion menu) was followed exactly.

### 2026-03-17 — p4-refs Execution

**Task:** File reference review — verify all markdown links resolve and comply with Plan Linking Standard.

**What was done:** Launched 4 parallel verification agents to audit:
1. Remaining `founder/` path references across `_bmad/rbtv/`
2. Internal plan link compliance with Plan Linking Standard
3. `business-innovation/` path reference completeness
4. Phase 3 synthesis block presence and ordering in all 22 files

**Findings:**
- **shape.md broken links (fixed):** 3 source document references in the References section used stale external paths (`_bmad/rbtv/_admin/roadmap/todos/_claude-code-workspace/bi-workflow/...`). The actual files exist in the plan folder. Fixed to internal relative paths (`./cp-workflow-bi-default-structures.md`, etc.) per Plan Linking Standard.
- **`founder/` path remnants in `_admin/roadmap/`:** ~11 files under `_admin/roadmap/` (testing, done, todos) still contain `founder/` path references. These are outside this plan's scope (plan covers BI workflow files, not admin/roadmap docs — per shape.md "What this plan does NOT include").
- **`business-innovation/` references confirmed:** 47 files contain the renamed path. All expected locations from the p1-2 execution log are present.
- **Synthesis blocks verified:** All 22 (23 counting design-context's delegate step) synthesis files contain all 3 required blocks (dedup, assumption inventory, consistency gate). 4 originator-variant files and 18+ checker-variant files are correctly assigned. Block ordering is correct in all files.
- **Pre-mortem ordering false alarm:** Explore agent flagged bi-m2-pre-mortem step ordering, but analysis confirmed the ordering is correct — dedup (step 5) occurs before synthesis output write (step 6, "Finalize Pre-mortem Document"). The preceding step 4 ("Update Project Memo") is a separate operation, not the synthesis output.

### 2026-03-17 — p4-compound Execution

**Task:** Review learnings.md and compound into system improvements.

**What was done:** Reviewed learnings.md — no entries were accumulated during plan execution. Documented as empty in learnings.md with compound review date. No compounds to generate.

### 2026-03-17 — p4-checkpoint Remediation

**Task:** Fix issues identified by P4 quality-review checkpoint (REJECTED verdict).

**Issue 1 (HIGH — fixed):** All 19 checker-variant synthesis files referenced `founder-process.md` as a bare filename in the dedup verification block. This file is a workflow data file at `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md`, not a project output file. Fixed all 19 files to use `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` — a resolvable variable-based path consistent with the BMAD config system.

**Issue 2 (MEDIUM — fixed):** Golden Circle Prior Context section only declared "Builds on: Brand Archetypes, Brand Prism" but its step files explicitly pull from JTBD (emotional jobs) and Working Backwards ("Why it matters" narrative, leader quote) from M1. Added both M1 frameworks to Prior Context with appropriate Inherits entries in `bi-m3-golden-circle/steps-c/step-01-init.md`.

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `./cp-workflow-bi-default-structures.md` | Canonical assumption inventory structure, folder rename specification |
| `./cp-workflow-bi-cross-framework-consistency-gate.md` | Party Mode gate mechanism, trigger threshold, prompt design |
| `./prd-no-content-duplication-in-milestones.md` | Content ownership rules, Prior Context template, dedup check |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` | Template to add canonical assumptions section | p1-1 |
| `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` | Main BI workflow frontmatter path | p1-2 |
| `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md` | Folder creation logic | p1-2 |
| `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md` | Founder process doc, ownership mapping target | p1-2, p2-1 |
| All M1-M4 milestone and framework `workflow.md` files | `outputFolder` frontmatter | p1-2 |
| All 22 framework synthesis step files | Gate, merging, dedup instructions | p3-1, p3-2, p3-3 |
| `_bmad/rbtv/workflows/pitch/steps-c/step-02-context-gather.md` | Pitch workflow `founder/` references | p1-2 |
| `_bmad/rbtv/_config/bootstrap.py` | Installer path reference | p1-2 |
| `_bmad/rbtv/tasks/mentor-help.xml` | Task file path references | p1-2 |
| `_bmad/rbtv/tasks/quality-review.xml` | Task file path references | p1-2 |
| `_bmad/rbtv/tasks/update-bmad-config.xml` | Task file path references | p1-2 |
| `_bmad/rbtv/tasks/data/quality-evaluator-atomic-files.md` | Task data file path references | p1-2 |
