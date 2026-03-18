# Shape - BI-M4 Follow-Up

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Address the 7 "keep that in mind" items from the BI-M4 quality review (founder-migration p6-3)
- Replace Lavoisier references with current RBTV mechanism (visual-design-extraction, playwright-browser-automation, design-validation)
- Add explicit BMAD create-ux-design path and adapt framework codes to mentor's simpler standards
- Create bi-m4-design-context bridge workflow; maintain referral logic (milestone = entry points, framework synthesis = update project_memo + return to milestone menu)
- Document how to verify {project-root} in all milestone output paths via file content search
- UPDATE p6-3.task.md to reflect discovery mechanism (no Lavoisier)
- OPEN M4, M5, M6 in business-innovation-migration_v3.plan.md into separate tasks per framework (like M1–M3); when executing this fix, read p6-3.task.md for current state (p6-1 and p6-2 executed, p6-3 WIP)

**Current M4 state and intent:** Only bi-m4-user-flow-ia exists; other M4 framework workflows (build-prototype, conversion-centered-design, heuristic-evaluation, testing-prep) are not yet created. Lavoisier replacement is agreed: replace with visual-design-extraction, playwright-browser-automation, optionally design-validation; a fuller plan may follow later.

**What this plan does NOT include:**
- Fixing milestone steps-c/ missing files (handled in business-innovation-migration_v3 via p3-8, p4-8, p5-8, p6-10)
- Creating bi-m4-build-prototype, bi-m4-conversion-centered-design, bi-m4-heuristic-evaluation, bi-m4-testing-prep (only user-flow-ia exists for now; those may be created later)

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|------------|
| Lavoisier replacement | Use bmad-rbtv-visual-design-extraction, bmad-rbtv-playwright-browser-automation, optionally bmad-rbtv-design-validation | Lavoisier agent no longer exists; work split across skills/commands |
| Bridge workflow | CREATE bi-m4-design-context | Formats M1–M3 for BMAD UX; routes to create-ux-design; integrates into project_memo |
| Framework codes | Adapt to mentor's simpler standards ([U], [D], [B], [C], [H], [F]) | Consistency with shape p6-1 and mentor menu |
| Output path verification | Document file content search instructions for user | Avoid token-heavy AI sweep; user runs search |
| Referral logic | Maintain: milestone = entry points; framework last step = update project_memo + return to milestone menu | Agreed architecture |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Referral logic | User/plan discussion | Bridge and framework synthesis steps must not break return-to-milestone flow |
| Only bi-m4-user-flow-ia exists | Current repo state | Do not assume other M4 sub-workflows exist |
| {project-root} required in output paths | User: multiple projects in projects/founder/ | All milestone files must reference project-root; user will verify via search |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Lavoisier replacement | "agree (keep that in mind, we will create a plan later on)" | Plan includes task to replace Lavoisier refs; fuller plan may follow |
| 2 | Scope | "only user-flow-ia have been created (keep that in mind)" | Scope note: other M4 frameworks not built; no tasks that assume they exist |
| 3 | Bridge | "create the bridge (keep that in mind)" | p3-1: CREATE bi-m4-design-context bridge workflow |
| 4 | Framework codes | "adapt to the mentor's standards which is more simple" | p2-3: UPDATE bi-m4 workflow codes to mentor standard |
| 5 | BMAD path | "agree to ur proposed action" | p2-2: Add explicit create-ux-design path in bi-m4 |
| 6 | Output paths | "there must always be the {project root}... AI can just instruct me how to do it using file content search" | p1-2: CREATE verification instructions (user runs search) |
| 7 | p6-3 task doc | "agree" | p2-4: UPDATE p6-3.task.md — replace Lavoisier, discovery mechanism |
| 8 | Founder-migration plan structure | M4/M5/M6 nested in single tasks; want them "open" like M1–M3; agent must read p6-3.task.md for current state (p6-1, p6-2 executed, p6-3 WIP) before opening M4 | p4-open-migration-plan: OPEN M4, M5, M6 in founder-migration plan into separate tasks; read p6-3.task.md first |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|------------------|------------------|
| 1 | Plan scope | 7 items as "keep that in mind" | Structured into phases: scope/verification, content fixes, bridge, close | Accepted |

---

## Standards Applied

| Standard | Application |
|----------|-------------|
| BMAD workflow pattern | Bridge uses workflow.md + steps-c/; referral logic preserved |
| Explicit file operations | Tasks use CREATE/UPDATE verbs with paths |
| Single action per task | One deliverable per task |

---

## Verification: Output Paths

**Purpose:** Ensure all milestone and framework workflows use `{project-root}` (or equivalent) in output paths so multiple projects in `projects/founder/` are supported. Run this check yourself using file content search — no AI sweep needed.

### Paths to check

**Master and milestone workflows:**

- `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` — frontmatter `outputFolder`, any `{project-root}` references
- `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-02-project-setup.md` — `outputFolder`, `outputFolder/`
- `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-03-milestone-select.md` — `projectMemo`
- `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md` — `projects/`, `project-memo`, output folder structure
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m1/workflow.md` — frontmatter `outputFolder`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m2/workflow.md` — frontmatter `outputFolder`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m3/workflow.md` — frontmatter `outputFolder`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md` — frontmatter `outputFolder`

**Framework workflows (every `workflow.md` under bi-m1-*, bi-m2-*, bi-m3-*, bi-m4-*):**

- `_bmad/rbtv/workflows/bi-business-innovation/bi-m1/bi-m1-*/workflow.md`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m2/bi-m2-*/workflow.md`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m3/bi-m3-*/workflow.md`
- `_bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-*/workflow.md`

Step files use `{outputFolder}` (inherited from workflow); the critical check is that each **workflow.md** sets `outputFolder` (or equivalent) with `{project-root}` in the path.

### Search instruction

1. **In IDE:** File content search (e.g. Cursor Search, grep) in folder `_bmad/rbtv/workflows/`.
2. **Search for:** `projects` or `outputFolder:` or `projectMemo:`.
3. **Confirm:** Every occurrence that defines an output path uses `{project-root}` (or `{project-root}/`) before `projects`. Example: `outputFolder: '{project-root}/projects/{project-name}/founder/...'`.
4. **Fail if:** Any path is hardcoded without `{project-root}` (e.g. `projects/` alone or a fixed absolute path).

### Optional: grep pattern for “missing project-root”

From repo root, search for output-path-like lines that do **not** include `project-root`:

- Search for: `outputFolder:` or `projectMemo:` in `_bmad/rbtv/workflows/`.
- Manually inspect each match: the value should contain the literal `{project-root}`.

### Success criteria

- Every `workflow.md` under `bi-business-innovation`, `bi-m1`, `bi-m2`, `bi-m3`, `bi-m4` (and their framework subfolders) that sets `outputFolder` or `projectMemo` uses `{project-root}` in the path.
- `founder-process.md` and master steps that reference `projects` or project paths use `{project-name}` (and, where applicable, `{project-root}`) so multiple projects are supported.

---

## Execution Log

> **APPEND-ONLY:** After each task, append an entry below. Never modify or delete previous entries.

### Entry Format

```markdown
### Task [id]: [Title]
**Completed:** YYYY-MM-DD
**Outcome:** [Brief summary]
**Files Modified:** [List]
```

<!-- Execution entries appended below -->

### Task p1-1: Document Scope and Lavoisier-Replacement Intent
**Completed:** 2026-02-05
**Outcome:** Confirmed scope and Lavoisier-replacement intent in shape; added explicit "Current M4 state and intent" line under Scope Definition.
**Files Modified:** .cursor/plans/bi-m4-follow-up/shape.md

### Task p1-2: Create Verification Instructions for {project-root} in Milestone Paths
**Completed:** 2026-02-05
**Outcome:** Added "Verification: Output Paths" section to shape.md with paths to check, search instruction, optional grep note, and success criteria.
**Files Modified:** .cursor/plans/bi-m4-follow-up/shape.md

### Task p2-1: Replace Lavoisier References with Current Mechanism
**Completed:** 2026-02-05
**Outcome:** Replaced all Lavoisier references in bi-m4/workflow.md and bi-m4-user-flow-ia/steps-c/step-04-synthesis.md with current mechanism wording (RBTV skills: visual-design-extraction, playwright-browser-automation; optionally design-validation). Grep confirms no remaining "Lavoisier" in bi-m4 or bi-m4-user-flow-ia.
**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md, _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-user-flow-ia/steps-c/step-04-synthesis.md

### Task p2-2: Add Explicit BMAD create-ux-design Path in bi-m4
**Completed:** 2026-02-05
**Outcome:** Added explicit path and load instruction to BMAD Integration Note in bi-m4/workflow.md: path `{bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md`, plus sentence "When user selects [DD], load this workflow with User Flow & IA output as context." Path confirmed to exist.
**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md

### Task p2-3: Adapt Framework Codes to Mentor's Simpler Standards
**Completed:** 2026-02-05
**Outcome:** Updated bi-m4/workflow.md and bi-m4-user-flow-ia/steps-c/step-04-synthesis.md: framework codes [UF],[DD],[BP],[CC],[HE],[TP] → [U],[D],[B],[C],[H],[F] per founder-migration p6-1. Table, BMAD Integration Note, Recommended Sequence, and step-04-synthesis Design Direction references updated. Navigation [S],[B] unchanged. Grep confirms no remaining old codes.
**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md, _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-user-flow-ia/steps-c/step-04-synthesis.md

### Task p2-4: Update p6-3.task.md — Replace Lavoisier and Discovery Mechanism
**Completed:** 2026-02-05
**Outcome:** Replaced all Lavoisier references in p6-3.task.md with current mechanism wording. "Update mentor agent" bullets now say design discovery via bmad-rbtv-visual-design-extraction, bmad-rbtv-playwright-browser-automation; optionally bmad-rbtv-design-validation. Removed [L] Lavoisier Discovery from Execute-phase code block; [D] Design Direction line now includes discovery skills. Removed human-input note. Grep confirms no remaining "Lavoisier".
**Files Modified:** .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-3.task.md

### Task p3-1: Create bi-m4-design-context Bridge Workflow
**Completed:** 2026-02-05
**Outcome:** Created bridge workflow _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/ with workflow.md and steps-c/ (step-01-init, step-02-format-context, step-03-invoke-bmad, step-04-synthesis). Bridge loads project-memo and user-flow-ia, formats design-context.md for BMAD create-ux-design, instructs run of BMAD workflow with explicit path, then synthesis step updates project-memo and instructs return to M4 milestone menu. No Lavoisier reference; uses current discovery mechanism wording. Referral logic preserved.
**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/workflow.md (CREATE), _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/steps-c/step-01-init.md (CREATE), _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/steps-c/step-02-format-context.md (CREATE), _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/steps-c/step-03-invoke-bmad.md (CREATE), _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/steps-c/step-04-synthesis.md (CREATE)

### Task p3-2: Route [D] Design Direction to Bridge in bi-m4
**Completed:** 2026-02-05
**Outcome:** Updated bi-m4/workflow.md: FRAMEWORK ROUTING [D] row now points to ../bi-m4-design-context/workflow.md (output: design_brief.md + design.json via bridge). BMAD Integration Note updated to state [D] routes via bi-m4-design-context bridge, which prepares context and invokes BMAD create-ux-design; return to M4 after bridge completes.
**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md

### Task p4-open-migration-plan: Open M4, M5, M6 in Founder-Migration Plan
**Completed:** 2026-02-05
**Outcome:** Opened M4, M5, M6 in business-innovation-migration_v3.plan.md Phase 6 into separate tasks following M1-M3 pattern. Original p6-3 (bundled M4 components) split into p6-3 through p6-8 (one task per component). M5 and M6 structured as evaluate/decide/create with placeholders. p6-10 renumbered to p6-15 (milestone steps-c). Total Phase 6 tasks: 16 (was 11).
**Decisions:**
- M4 split: p6-3 (bi-m4 milestone, completed), p6-4 (user-flow-ia, completed), p6-5 (design-context bridge, completed), p6-6 (conversion-centered-design, pending), p6-7 (heuristic-evaluation, pending), p6-8 (update mentor, pending)
- M5 structure: p6-9 (evaluate), p6-10 (decide), p6-11 (create - will be split after p6-10 decision)
- M6 structure: p6-12 (evaluate), p6-13 (decide), p6-14 (create - will be split after p6-13 decision)
- p6-15: Create milestone steps-c for M4, M5, M6 (renamed from p6-10)
**Files Modified:**
- .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md (YAML todos and Phase 6 body updated)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-3.task.md (updated to milestone workflow only, marked completed)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-4.task.md (created - user-flow-ia, marked completed)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-5.task.md (created - design-context bridge, marked completed)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-6.task.md (created - conversion-centered-design, pending)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-7.task.md (created - heuristic-evaluation, pending)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-8.task.md (created - update mentor, pending)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-9.task.md (created - evaluate M5)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-10.task.md (created - decide M5)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-11.task.md (created - create M5, placeholder)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-12.task.md (created - evaluate M6)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-13.task.md (created - decide M6)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-14.task.md (created - create M6, placeholder)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-15.task.md (created - milestone steps-c)

### Task p4-fix-m5m6-structure: Fix M5 and M6 Task Structure
**Completed:** 2026-02-05
**Outcome:** Fixed M5 and M6 task structure in business-innovation-migration_v3.plan.md by removing unnecessary evaluate/decide phases (p6-9/p6-10 for M5, p6-12/p6-13 for M6) and opening them directly like M1-M3 per existing integration strategy. M5 is RBTV-native with 6 frameworks (Mom Test, SPIN Selling, Smoke Test, Van Westendorp, Bullseye, Sean Ellis PMF). M6 is minimal with full BMAD routing.
**Decisions:**
- M5 structure: p6-9 (bi-m5 milestone), p6-10 through p6-15 (6 framework workflows), p6-16 (update mentor)
- M6 structure: p6-17 (bi-m6 milestone - minimal BMAD routing), p6-18 (update mentor)
- Steps-c split: p6-19 (M4 steps-c), p6-20 (M5 steps-c), p6-21 (M6 steps-c) - split per user request for granularity
- Phase 6 tasks: 21 total (was 16 with evaluate/decide structure)
**Files Modified:**
- .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md (YAML todos and Phase 6 body updated)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-9.task.md (updated to bi-m5 milestone)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-10.task.md (updated to bi-m5-mom-test)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-11.task.md (created - bi-m5-spin-selling, deleted old placeholder)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-12.task.md (created - bi-m5-smoke-test, deleted old evaluate M6)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-13.task.md (created - bi-m5-van-westendorp, deleted old decide M6)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-14.task.md (created - bi-m5-bullseye, deleted old create M6 placeholder)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-15.task.md (created - bi-m5-sean-ellis-pmf)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-16.task.md (created - update mentor for M5)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-17.task.md (created - bi-m6 milestone)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-18.task.md (created - update mentor for M6)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-19.task.md (created - M4 steps-c)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-20.task.md (created - M5 steps-c)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-21.task.md (created - M6 steps-c)

### Task p4-refs: File Reference Review for bi-m4 and Bridge
**Completed:** 2026-02-05
**Outcome:** Verified all internal links and references in bi-m4, bi-m4-user-flow-ia, and bi-m4-design-context. Fixed broken references to non-existent framework workflows by marking them as "to be created" in routing table and success criteria. Confirmed all existing references (parentWorkflow, nextStepFile, BMAD path, return-to-milestone codes) are valid.

**Reference Validation Results:**

**✅ Valid References:**
- bi-m4/workflow.md → parentWorkflow: ../bi-business-innovation/workflow.md (exists)
- bi-m4-user-flow-ia/workflow.md → parentWorkflow: ../bi-m4/workflow.md (exists)
- bi-m4-design-context/workflow.md → parentWorkflow: ../bi-m4/workflow.md (exists)
- All step files' nextStepFile paths resolve correctly
- BMAD path in design-context: {bmad_bmm}/workflows/2-plan-workflows/create-ux-design/workflow.md (exists)
- bi-m4-user-flow-ia data/user-flow-ia-framework.md (exists)
- Return-to-milestone instructions use correct codes: [B] Back, [D], [U], [C], [H], [F]

**🚧 Fixed References (Non-existent Workflows):**
- bi-m4/workflow.md FRAMEWORK ROUTING table: marked [B], [C], [H], [F] as "to be created" with status column
- bi-m4/workflow.md RECOMMENDED SEQUENCE: added "(to be created)" notes to [B], [C], [H], [F]
- bi-m4/workflow.md SUCCESS CRITERIA: added framework availability notes and "Current State" paragraph
- bi-m4/workflow.md KNOWLEDGE FILES: removed reference to non-existent data/milestone-overview.md; added note about milestone steps-c/ deferred to p6-19

**🛑 Removed References:**
- bi-m4/workflow.md frontmatter: nextStep set to null (milestone steps-c/ deferred to business-innovation-migration_v3 p6-19)

**Files Modified:** _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md

### Task p4-compound: Review learnings.md and Compound into System Improvements
**Completed:** 2026-02-05
**Outcome:** Reviewed learnings.md for learning entries. No learning entries were recorded during this plan execution. Appended compound output to learnings.md Compound Generation section stating "No learning entries recorded during this run."
**Files Modified:** .cursor/plans/bi-m4-follow-up/learnings.md

### Plan Completion
**Completed:** 2026-02-05
**All Checkpoints Approved:** p1-checkpoint, p2-checkpoint, p3-checkpoint, p4-checkpoint

**Plan Summary:**
- Phase 1: Documented scope and created {project-root} verification instructions ✅
- Phase 2: Replaced Lavoisier references, added BMAD path, adapted framework codes, updated p6-3.task.md ✅
- Phase 3: Created bi-m4-design-context bridge workflow and routing ✅
- Phase 4: Opened M4/M5/M6 in founder-migration plan, fixed M5/M6 structure, verified references, compounded learnings ✅

**Deliverables:**
- Updated bi-m4, bi-m4-user-flow-ia workflows with current mechanism (no Lavoisier)
- Created bi-m4-design-context bridge workflow (5 files: workflow.md + 4 steps)
- Updated bi-m4 with explicit BMAD path and simplified framework codes
- Updated p6-3.task.md with current discovery mechanism
- Opened 21 tasks in business-innovation-migration_v3 Phase 6 (was 11)
- Fixed M5 (6 frameworks) and M6 (minimal BMAD routing) structure
- Verified all references in bi-m4 ecosystem; marked planned frameworks as "to be created"
- Created {project-root} verification instructions in shape.md
- Compounded learnings (none recorded)

**Files Modified (Total):**
- .cursor/plans/bi-m4-follow-up/shape.md
- .cursor/plans/bi-m4-follow-up/learnings.md
- _bmad/rbtv/workflows/bi-business-innovation/bi-m4/workflow.md
- _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-user-flow-ia/steps-c/step-04-synthesis.md
- _bmad/rbtv/workflows/bi-business-innovation/bi-m4/bi-m4-design-context/ (5 files created)
- .cursor/plans/founder-migration/business-innovation-migration_v3.plan.md
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/ (15 task files created/updated)
- .cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-3.task.md

---

## Execution Discoveries

> **APPEND-ONLY:** Discoveries that affect scope or approach. Never modify or delete previous entries.

<!-- Discovery entries appended below -->
