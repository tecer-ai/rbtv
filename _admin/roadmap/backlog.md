# RBTV PRD Backlog

> Generated: 2026-02-13
> Source: `_admin/roadmap/todos/prd-*.md`
> Total PRDs: 13

---

## Summary

| # | PRD | Priority | Type | Scope |
|---|-----|----------|------|-------|
| 1 | Git PR Mode | High | Workflow | Small |
| 2 | Mentor Help Mode | High | Agent Enhancement | Small |
| 3 | Business Innovation Migration | High | Workflow + Agent | Large |
| 4 | BMAD Version Declaration | Medium | System + Docs | Moderate |
| 5 | BMAD Compatibility Check | Medium | System + Tooling | Moderate |
| 6 | Standardize main_config | Medium | Process | Low effort |
| 7 | Reduce Path Resolution Hops | Medium | System + Config | Large |
| 8 | BMAD Delegation Standards + M2 Analyst | Medium | Workflow + Arch | Large |
| 9 | Consistency Criterion | Low | Process | Minimal |
| 10 | Checkpoint HALT Enforcement | Low | Process | Minimal |
| 11 | Workflow Continuation Compliance | Low | Workflow Enhancement | Large |
| 12 | Advanced Elicitation Integration | Low | Integration | Low effort |
| 13 | Agent Menu Externalization Rule | Low | Process | Minimal |

### Dependency Chain
```
PRD #4 (Version Declaration) ──→ PRD #5 (Compatibility Check)
```
All other PRDs are independent.

---

## High Priority

### 1. Add PR Mode to Git Workflow
**File:** `prd-git-sq-pr-merge-mode.md`
**Type:** Workflow
**Description:** The git workflow's SQ mode performs local squash merges directly to the target branch, bypassing collaborative safeguards (review trails, CI checks, branch protection). There is no PR-based path within the workflow.
**Goals:** Add a fifth PR mode that pushes the current branch and creates a Pull Request via `gh pr create`. PR is a peer to SQ -- SQ is the fast path for solo/admin work, PR is the collaborative path for team/code changes.
**Scope:** Modify 5 existing step files in `workflows/git-commit/`. No new step files needed.
**Dependencies:** None.

### 2. Mentor Help Mode [H]
**File:** `prd-mentor-help-mode.md`
**Type:** Agent Enhancement
**Description:** Mentor guides founders through a 6-milestone lifecycle, but founders lose track of where they are. No orientation mechanism exists -- the only way to check progress is manually reading `project-memo.md` frontmatter.
**Goals:** Add an [H] Help menu item to Mentor displaying current milestone, framework progress (done/current/pending), and available workflows. Concise "you are here" output (15 lines max).
**Scope:** Modify `agents/mentor.md` -- add 1 menu item + 1 action block (~20-25 lines).
**Dependencies:** None.

### 3. Business Innovation Migration
**File:** `founder-migration/business-innovation-migration_v3.plan.md`
**Type:** Workflow + Agent
**Description:** Migrate the founder system from local refs to BMAD architecture, creating a 3-level workflow hierarchy (master, milestone, framework) with YC mentor agent orchestration across 6 milestones (Conception, Validation, Brand, Prototypation, Market Validation, MVP).
**Goals:** Build all milestone and framework workflows, mentor agent routing, project-memo state tracking, and BMAD integration for M4-M6. 7 phases, 60+ tasks.
**Scope:** Large -- Phases 1-4 complete, Phase 5 complete, Phase 6 partially complete (M4 done, M5 + M6 pending), Phase 7 pending.
**Dependencies:** None.

---

## Medium Priority

### 4. BMAD Version Declaration for RBTV
**File:** `prd-config-bmad-version-declaration.md`
**Type:** System File + Documentation
**Description:** RBTV has no explicit declaration of which BMAD version it targets. The BMAD mirror is pinned to Beta.4 but RBTV never reads or exposes this. Two developers run different BMAD versions with no shared baseline.
**Goals:** Declare target BMAD version in `_config/config.yaml` (`bmad_target_version`, `bmad_min_version`), add `MIRROR-VERSION.md` to mirror folder, create RBTV `CHANGELOG.md`.
**Scope:** 1 modified file, 2 new files, mirror update to Beta.8.
**Dependencies:** None. Foundation for PRD #5.

### 5. BMAD Compatibility Check Pipeline
**File:** `prd-config-bmad-compatibility-check.md`
**Type:** System File + Tooling + Workflow
**Description:** RBTV has no structured process to evaluate whether a new BMAD release is compatible. Every RBTV-to-BMAD touchpoint is a potential breakage point discovered accidentally.
**Goals:** Create a three-layer pipeline: `bmad-compat.yaml` (data -- lists all touchpoints), `tasks/check-bmad-compat.xml` (process -- evaluates new releases), and installer pre-flight version check (enforcement).
**Scope:** 3 new files, 1 modified file (`install-rbtv.py`).
**Dependencies:** PRD #4 (BMAD Version Declaration) must be implemented first.

### 6. Standardize main_config Declaration Pattern
**File:** `prd-standardize-main-config-frontmatter.md`
**Type:** Process Improvement
**Description:** 4 utility workflows declare `main_config` in frontmatter while all BI workflows load config in body text. No single pattern exists, creating inconsistency and reduced discoverability.
**Goals:** Standardize on frontmatter declaration for all workflows. Audit all 38 workflows, migrate BI workflows, update component patterns documentation.
**Scope:** ~10 files to modify out of 38 audited.
**Dependencies:** None.

### 7. Reduce Path Resolution Hops for AI Agents
**File:** `prd-reduce-path-resolution-hops.md`
**Type:** System File + Config
**Description:** AI agents resolving `{project-root}` paths must perform a 5-step conditional lookup against a resolution table. This is error-prone (the table itself contained a bug) and expensive (failed resolution triggers fallback glob/grep searches).
**Goals:** Replace the conditional table with direct path variables in `_config/config.yaml` (`{bmad_core}`, `{bmad_bmm}`, etc.) that agents load once during activation. One-step substitution instead of five.
**Scope:** ~60 files reference cross-module paths. Both installers need updates.
**Dependencies:** None, but large migration scope.

### 8. BMAD Delegation Standards and Optional Analyst at M2
**File:** `prd-bmad-analyst-delegation-at-m2.md`
**Type:** Workflow + Architecture
**Description:** M4 currently uses a 6-step/5-file bridge for BMAD delegation. M6 is planned as a full BMAD routing milestone. The existing pattern is heavier than necessary, and gaps exist (no project-memo updates, no return routing, persona conflicts).
**Goals:** (1) Standardize a lightweight BMAD delegation pattern applicable everywhere, (2) add optional BMAD analyst step at M2 start, (3) simplify M4 from 5 to 3 step files, (4) update migration plan with delegation standards for M6.
**Scope:** Large -- M2 init step, 6 M2 framework init steps, M4 refactoring, task enhancement, architecture docs, migration plan update.
**Dependencies:** `update-bmad-config.xml` and `restore-bmad-config.xml` tasks (already built).

---

## Low Priority

### 9. PRD Option Evaluation -- Format Consistency Criterion
**File:** `prd-consistency-criterion.md`
**Type:** Process Improvement
**Description:** The compound workflow's option evaluation weighted technical factors but missed "consistency with existing patterns" as a criterion, leading to a recommendation the user rejected in favor of structural consistency.
**Goals:** Add "consistency with existing patterns" as a standard evaluation criterion in compound PRD option analysis.
**Scope:** Add 1 evaluation criterion to compound workflow step file(s).
**Dependencies:** None.

### 10. Plan Checkpoint HALT Enforcement
**File:** `prd-plan-checkpoint-halt.md`
**Type:** Process Improvement
**Description:** Plan checkpoints instruct "Agent must STOP and wait for human approval," but agents auto-continue past checkpoints. The rule exists in plan-creation-rules but the executing agent reads the plan file, not the creation rules.
**Goals:** Update `plan-creation-rules.md` checkpoint section to require checkpoint tasks to include explicit HALT instruction text ("PRESENT results to user. HALT. Do NOT proceed until user confirms.").
**Scope:** Add 1 line to Checkpoint Rules section in `plan-creation-rules.md`.
**Dependencies:** None.

### 11. Add Continuation Support to All RBTV Workflows
**File:** `prd-workflow-continuation-compliance.md`
**Type:** Workflow Enhancement
**Description:** Two templates exist for multi-session workflow continuation (`step-init-continuable-template.md`, `step-continue-template.md`) but zero of 28 output-producing workflows comply. No `step-01b-continue.md` files exist.
**Goals:** Add continuation support to all 28 output-producing workflows: update each `step-01-init.md` with continuation detection, create `step-01b-continue.md` for each.
**Scope:** Large -- 28 workflows x 2 file changes = 56 file operations.
**Dependencies:** None, but high volume and risk of copy-paste errors.

### 12. Integrate Advanced Elicitation with RBTV
**File:** `prd-integrate-advanced-elicitation.md`
**Type:** Integration
**Description:** RBTV step templates include an `[A] Advanced Elicitation` menu option, but the `advancedElicitationTask` frontmatter field is commented out. BMAD's advanced elicitation task is fully functional but RBTV has never validated the integration.
**Goals:** Uncomment `advancedElicitationTask` in the step template, audit existing step files, validate the integration works in an installed BMAD instance.
**Scope:** Template update + audit of step files with A/P/C menus.
**Dependencies:** Requires installed BMAD instance for validation (path resolves only in installed context).

### 13. Agent Menu Item Externalization Rule
**File:** `prd-agent-menu-externalization-rule.md`
**Type:** Process Improvement
**Description:** PRDs and AI agents default to inline `<action>` blocks for new menu items, but agent files have a 100-line limit and existing patterns use `exec=`/`workflow=` for complex operations. No explicit rule codifies when to externalize.
**Goals:** Add rule to component pattern standards: agent menu items with non-trivial logic must delegate to external files via `exec=` or `workflow=`. Inline `<action>` reserved for trivial operations (exit, simple state set).
**Scope:** Add 1 rule to `admin-rbtv-component-patterns.mdc` Agent Files table.
**Dependencies:** None.
