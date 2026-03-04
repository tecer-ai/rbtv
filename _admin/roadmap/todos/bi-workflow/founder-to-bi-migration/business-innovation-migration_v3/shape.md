# Shape - Business Innovation Migration

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Migrate the founder system from `robotville/system/founder/` to BMAD architecture in `_bmad/rbtv/`
- Create a 3-level workflow hierarchy: master workflow → milestone workflows → framework workflows
- Build YC mentor agent as master orchestrator
- Create IDE command entry point with new/continue project modes
- Establish `project_memo` as cumulative summary of all framework results

**What this plan does NOT include:**
- Migrating source code (this is documentation/workflow migration only)
- Deleting the original founder system (preservation for reference)
- Creating user-facing documentation (focus is on BMAD components)

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Folder structure | Flat at workflows/ root | BMAD standard, all workflows at same level |
| Naming convention | `bi-business-innovation/`, `bi-m1/`, `bi-m1-[framework]/` | Consistency and discoverability |
| Framework names | Full names, not abbreviated | Clarity over brevity |
| Milestone names | Abbreviated (m1, m2, etc.) | Balance of brevity and clarity |
| Entry point | IDE command with new/continue modes | User control over project state |
| State document | project_memo as cumulative summary | Single source of truth |
| Agent persona | YC mentor | Domain expertise for startup guidance |
| Output folder | `_bmad-output/founder/` (no project subfolder) | Simplicity |
| Framework synthesis | Last step of each framework updates project_memo | Cumulative learning capture |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| BMAD architecture patterns | BMAD standards | Must use workflow.md + steps-c/ structure |
| Micro-file architecture | BMAD principles | Files under 200 lines, one responsibility |
| Sequential enforcement | BMAD principles | Steps execute in order, no skipping |
| Output folder location | User decision | All outputs to `_bmad-output/founder/` |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Workflow hierarchy | "master workflow, milestone workflows, framework workflows" | 3-level workflow structure with routing at each level |
| 2 | Agent persona | "a mentor from Y combinator" | YC mentor agent with startup expertise persona |
| 3 | Folder naming | "all start with bi-; use abbreviations for milestones" | `bi-business-innovation/`, `bi-m1/`, `bi-m1-[framework]/` pattern |
| 4 | Framework names | "no need to abbreviate framework names" | Full framework names like `bi-m1-working-backwards/` |
| 5 | Output structure | "no project-name folder necessary" | Flat structure under `_bmad-output/founder/` |
| 6 | Framework completion | "last step of each framework must summarize into project_memo" | Architectural constraint for all framework workflows |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Master workflow name | Not specified initially | Suggested `bi/` | Changed to `bi-business-innovation/` per user feedback |
| 2 | M4-M6 handling | "evaluate case by case" | Proposed evaluation phase with decision checkpoints | Phase 6 dedicated to evaluation with per-milestone decisions |
| 3 | Plan phases | Not specified | Proposed 7-phase structure | Accepted with minor refinements |

---

## Standards Applied

### BMAD Architecture Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Micro-file architecture | All workflow.md files under 120 lines, step files under 250 lines |
| Sequential enforcement | Each step file includes HALT instructions and menu pattern |
| State tracking | stepsCompleted in output document frontmatter |
| Thin loaders | IDE command only loads agent, no logic |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Framework synthesis | Every framework workflow's final step must UPDATE project_memo.md |
| BMAD template compliance | All components use BMAD templates from `_bmad/bmb/workflows/` (workflow, agent, module builders) |
| Naming consistency | All BI workflows start with `bi-` prefix |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | Judge needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Execution Log

> **APPEND-ONLY RULES:**
> 1. After completing each task, append an entry below
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Use the exact format shown

### Entry Format

```markdown
### Task [id]: [Title]
**Completed:** YYYY-MM-DD
**Outcome:** [Brief summary of what was delivered]
**Decisions:**
- [Decision]: [Rationale]
**Issues:** [Any blockers or surprises encountered]
**Files Modified:** [List of files created/updated/deleted]
```

<!-- Execution entries will be appended below this line -->

### Task p1-1: Create IDE Command Entry Point
**Completed:** 2026-02-04
**Outcome:** Created thin loader command for YC mentor agent
**Decisions:**
- Used agent command template pattern (not workflow pattern): Agent needs to be loaded with persona activation
- Named `rbtv-bi` for consistency with other RBTV commands
**Issues:** None
**Files Modified:** `_bmad/rbtv/.cursor/commands/rbtv/bmad-rbtv-bi.md` (created)

### Task p1-2: Create YC Mentor Agent
**Completed:** 2026-02-04
**Outcome:** Created YC mentor agent with startup expertise persona and milestone routing menu
**Decisions:**
- Persona traits: Critical 10/10, Constructive 10/10, Direct 10/10, Sycophancy 1/10, Verbosity 1/10 — matches source mentor
- Menu routes to workflow.md files (not yet created): bi-business-innovation, bi-m1 through bi-m6
- Used domcobb.md as structural reference
**Issues:** None
**Files Modified:** `_bmad/rbtv/agents/paul.md` (created)

### Task p1-3: Create Project Memo Template
**Completed:** 2026-02-04
**Outcome:** Created cumulative project summary template with YAML frontmatter for state tracking
**Decisions:**
- Added stepsCompleted array in frontmatter for BMAD state tracking
- Progress section has subsection per milestone with framework synthesis placeholders
- Adapted 6-pager format for BMAD workflow integration
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-business-innovation/templates/` (created folder)
- `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` (created)

### Task p1-4: Create Founder Diary Template
**Completed:** 2026-02-04
**Outcome:** ~~Created session state template with 280-char status fields and append-only logs~~
**Status:** ⛔ CANCELLED — See Discovery 1. Founder-diary eliminated; state tracking moved to project-memo frontmatter; decision tracking moved to shape.md per milestone.
**Decisions:**
- ~~Single diary per project (not per milestone) — simplified from original multi-milestone approach~~
- ~~Framework Status table covers all 18 frameworks across M1-M3~~
- ~~Working Memory Log + Decision Log for append-only tracking~~
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-business-innovation/templates/founder-diary.md` (created, then DELETED)

### Task p2-1: Create Master Workflow Entry
**Completed:** 2026-02-04
**Outcome:** Created master workflow.md with mode routing and milestone navigation
**Decisions:**
- Included all 6 critical rules with emojis per BMAD template
- Mode Overview supports Create (new project) and Continue (resume) modes
- Milestone routing table references bi-m1 through bi-m6 workflows
- Output folder set to `{project-root}/_bmad-output/founder`
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` (created)

### Task p2-2: Create Founder Process Knowledge File
**Completed:** 2026-02-04
**Outcome:** Created milestone overview knowledge file with routing tables and state tracking docs
**Decisions:**
- Adapted content from robotville founder_process.md for BMAD structure
- Output folder structure includes all 6 milestone subfolders
- Framework naming convention documented: bi-m{N}-{framework-name}
- Agent handoff protocol simplified for BMAD workflow integration
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-business-innovation/data/` (created folder)
- `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md` (created)

### Task p2-3: Create Init Step (Mode Selection)
**Completed:** 2026-02-04
**Outcome:** Created step-01-init.md with new/continue mode detection and routing
**Decisions:**
- Context detection checks for project-memo reference to suggest Continue mode
- Menu presents project info if detected, otherwise shows milestone overview
- Routes to step-02 for new projects, step-03 for continuing projects
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-business-innovation/steps-c/` (created folder)
- `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-init.md` (created)

### Task p2-4: Create Project Setup Step
**Completed:** 2026-02-04
**Outcome:** Created step-02-project-setup.md for new project initialization
**Decisions:**
- Creates all 6 milestone folders upfront (m1-conception through m6-mvp)
- Initializes both project-memo.md and founder-diary.md from templates
- Gathers project name before creating any files
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-02-project-setup.md` (created)

### Task p2-5: Create Milestone Selection Step
**Completed:** 2026-02-04
**Outcome:** Created step-03-milestone-select.md with milestone routing and status display
**Decisions:**
- Reads project state from founder-diary and project-memo
- Suggests next logical milestone based on framework completion status
- Routes to bi-m1 through bi-m6 workflows
- [S] option shows detailed framework-level status
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-03-milestone-select.md` (created)

### Task p2-checkpoint: Phase 2 Checkpoint
**Completed:** 2026-02-04
**Outcome:** Validated master workflow routing logic — all checks passed
**Decisions:** None required — validation only
**Issues:** None
**Validation Results:**
| Check | Status |
|-------|--------|
| workflow.md size | ✅ 87 lines (max 120) |
| step-01-init.md size | ✅ 141 lines (max 250) |
| step-02-project-setup.md size | ✅ 154 lines (max 250) |
| step-03-milestone-select.md size | ✅ 195 lines (max 250) |
| founder-process.md size | ✅ 118 lines (max 300) |
| Mode routing (new/continue) | ✅ Implemented in step-01 |
| Milestone routing (M1-M6) | ✅ Implemented in step-03 |
| Output folder path | ✅ `_bmad-output/founder` |
| Template references | ✅ Correct paths |
| Knowledge file reference | ✅ Correct path |

---

## Execution Discoveries

> **DISCOVERY RULES:**
> 1. When execution reveals contradictions or unforeseen work, append entry
> 2. If work is simple (<5 min), do it immediately and mark checkbox
> 3. If work is complex, add new task to plan and note the task ID
> 4. NEVER modify Original Shaping - discoveries explain divergence

### Entry Format

```markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]
**Details:** [Explanation]
```

<!-- Discovery entries will be appended below this line -->

### Discovery 1 (from task p2-checkpoint post-review)
**Date:** 2026-02-04
**Finding:** Founder-diary should be eliminated. State tracking moves to project-memo frontmatter; decision tracking moves to shape.md per milestone.
**Contradicts:** Original Shaping decision to use founder-diary for session state
**Resolution:**
- [x] Simple fix applied immediately
**Details:**
- currentMilestone, currentFramework, stepsCompleted now in project-memo.md frontmatter
- Working memory log eliminated (tracked directly in instance files)
- Decision log becomes shape.md at milestone level (e.g., m1-conception/shape.md)
- Shape.md workflow executed at end of each working session
- founder-diary.md template deleted
- All step files updated to remove founder-diary references

### Discovery 2 (from user request during p3-6/p3-7)
**Date:** 2026-02-05
**Finding:** Output folder should include project name for isolation: `_bmad-output/{project-name}/founder/`
**Contradicts:** Original Shaping decision to use `_bmad-output/founder/` (no project subfolder)
**Resolution:**
- [x] Simple fix applied immediately
**Details:**
- Project name captured in step-02-project-setup when creating new project
- Output folder structure changed to `_bmad-output/{project-name}/founder/`
- Enables multiple business innovation projects without collision
- All workflow files updated to use new path pattern
- Plan file updated to reflect new output structure

### Task p3-1: Create M1 Milestone Workflow
**Completed:** 2026-02-04
**Outcome:** Created M1 Conception milestone workflow with framework routing menu
**Decisions:**
- Added parentWorkflow field to link back to master workflow
- Framework routing table with 6 frameworks matching conception_process.md
- Navigation codes [S] for status and [B] for back to milestone selection
- Success criteria adapted from conception_process.md (removed founder-diary reference per Discovery 1)
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-m1/workflow.md` (created, 62 lines)

### Task p3-2: Create Working Backwards Framework Workflow
**Completed:** 2026-02-04
**Outcome:** Created complete Working Backwards framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, discover, press-release, faq, synthesis (consolidated Tasks 3+4 into single FAQ step for flow)
- step-05-synthesis explicitly updates project-memo.md per architectural constraint
- Framework knowledge extracted into data/working-backwards-framework.md (88 lines)
- Each step includes validation checklist before proceeding
- "Is it worth doing?" answer is mandatory in step-04 (cannot skip)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-working-backwards/workflow.md` (created, 55 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/data/working-backwards-framework.md` (created, 88 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/steps-c/step-01-init.md` (created, 88 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/steps-c/step-02-discover.md` (created, 106 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/steps-c/step-03-press-release.md` (created, 121 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/steps-c/step-04-faq.md` (created, 127 lines)
- `_bmad/rbtv/workflows/bi-m1-working-backwards/steps-c/step-05-synthesis.md` (created, 125 lines)

### Task p3-3: Create Jobs-to-be-Done Framework Workflow
**Completed:** 2026-02-04
**Outcome:** Created complete JTBD framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, job-hypotheses, interview, job-stories, synthesis (follows source framework task structure)
- step-01-init includes mandatory dependency check — Working Backwards MUST be completed first
- step-05-synthesis explicitly updates project-memo.md per architectural constraint
- Framework knowledge extracted into data/jtbd-framework.md (113 lines) — condensed from source while preserving methodology
- Four Forces model documented (Push, Pull, Anxieties, Habits)
- Job Map structure with 6 stages (Define, Locate, Prepare, Execute, Confirm, Evolve)
- Interview step supports both conducted interviews and founder-knowledge fallback with explicit limitation notes
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/workflow.md` (created, 77 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/data/jtbd-framework.md` (created, 113 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/steps-c/step-01-init.md` (created, 146 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/steps-c/step-02-job-hypotheses.md` (created, 160 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/steps-c/step-03-interview.md` (created, 200 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/steps-c/step-04-job-stories.md` (created, 202 lines)
- `_bmad/rbtv/workflows/bi-m1-jobs-to-be-done/steps-c/step-05-synthesis.md` (created, 204 lines)

### Task p3-5: Create Problem-Solution Fit Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Problem-Solution Fit framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, problem-space, solution-space, assumptions, synthesis
- Step-02 consolidated problem mapping (brief, triggers, emotions, behaviours, constraints) into single step for flow
- Prerequisites enforced: Working Backwards AND JTBD must be completed before starting
- step-05-synthesis explicitly updates project-memo.md per architectural constraint
- Framework knowledge extracted into data/psf-framework.md (67 lines)
- Traceability check in step-03 forces every solution element to trace to behaviour or constraint
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/workflow.md` (created, 60 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/data/psf-framework.md` (created, 67 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/steps-c/step-01-init.md` (created, 106 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/steps-c/step-02-problem-space.md` (created, 122 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/steps-c/step-03-solution-space.md` (created, 112 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/steps-c/step-04-assumptions.md` (created, 123 lines)
- `_bmad/rbtv/workflows/bi-m1-problem-solution-fit/steps-c/step-05-synthesis.md` (created, 164 lines)

### Task p3-4: Create Competitive Landscape Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Competitive Landscape framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, competitor-id, benchmarking, positioning, synthesis (consolidated 7 source tasks into 5 steps)
- Web research is MANDATORY — step-01 includes capability check and abort if unavailable
- Prerequisites enforced: Working Backwards and JTBD recommended before starting
- step-05-synthesis explicitly updates project-memo.md per architectural constraint
- Framework knowledge extracted into data/competitive-landscape-framework.md (114 lines)
- Geographic benchmarking covers US and China markets with specific player requirements
- Cross-industry analogues require problem abstraction before searching
- All competitor claims must include source URLs — training data alone is insufficient
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/workflow.md` (created, 86 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/data/competitive-landscape-framework.md` (created, 114 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/steps-c/step-01-init.md` (created, 175 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/steps-c/step-02-competitor-id.md` (created, 166 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/steps-c/step-03-benchmarking.md` (created, 250 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/steps-c/step-04-positioning.md` (created, 245 lines)
- `_bmad/rbtv/workflows/bi-m1-competitive-landscape/steps-c/step-05-synthesis.md` (created, 215 lines)

### Task p3-6: Create Lean Canvas Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Lean Canvas framework workflow with 6 step files and knowledge data
**Decisions:**
- 6-step sequence: init, customer-problem, value-solution, channels-revenue, metrics-advantage, synthesis (follows source framework 6-task structure)
- Prerequisites enforced: Working Backwards, JTBD, AND Problem-Solution Fit MUST be completed before starting
- step-06-synthesis explicitly updates project-memo.md per architectural constraint
- Framework knowledge extracted into data/lean-canvas-framework.md (104 lines) — covers all 9 blocks with guidance
- Assumption tagging convention documented (P1, CS1, UVP1, SOL1, CH1, REV1, COST1, MET1, UA1)
- Unfair Advantage step references Competitive Landscape for informed defensibility thesis
- Unit economics sanity check included in step-04 (LTV:CAC ratio validation)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/workflow.md` (created, 61 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/data/lean-canvas-framework.md` (created, 104 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-01-init.md` (created, 131 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-02-customer-problem.md` (created, 140 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-03-value-solution.md` (created, 135 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-04-channels-revenue.md` (created, 169 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-05-metrics-advantage.md` (created, 154 lines)
- `_bmad/rbtv/workflows/bi-m1-lean-canvas/steps-c/step-06-synthesis.md` (created, 148 lines)

### Task p3-7: Create Five Whys Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Five Whys framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, problem-framing, why-chain, root-cause, synthesis (follows source 5-task structure)
- Prerequisites enforced: Working Backwards MUST be completed before starting
- step-05-synthesis explicitly updates project-memo.md AND triggers M1 completion check (final M1 framework)
- Framework knowledge extracted into data/five-whys-framework.md (87 lines)
- Session rules displayed at start of every chain to enforce discipline
- Fact/Hypothesis labelling is mandatory for every chain link with evidence documentation
- Root Cause Map requires explicit targeted vs non-targeted decisions with rationale
- Non-targeted root causes MUST be documented — cannot claim to target everything
- Lean Canvas Problem block update required with structural causes
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1-five-whys/workflow.md` (created, 55 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/data/five-whys-framework.md` (created, 87 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/steps-c/step-01-init.md` (created, 102 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/steps-c/step-02-problem-framing.md` (created, 126 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/steps-c/step-03-why-chain.md` (created, 142 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/steps-c/step-04-root-cause.md` (created, 143 lines)
- `_bmad/rbtv/workflows/bi-m1-five-whys/steps-c/step-05-synthesis.md` (created, 173 lines)

### Task p4-1: Create M2 Milestone Workflow
**Completed:** 2026-02-05
**Outcome:** Created M2 Validation milestone workflow with 6 framework routing
**Decisions:**
- Followed M1 milestone pattern with identical structure
- 6 frameworks: Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem
- Navigation codes match task file spec ([LF], [AM], [TS], [UE], [TR], [PM])
- Success criteria adapted from validation_process.md
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-m2/workflow.md` (created, 88 lines)

### Task p4-2: Create Leap of Faith Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Leap of Faith framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, harvest, classify, prioritize, synthesis (maps to source framework 6 tasks, consolidated for flow)
- step-01-init includes mandatory M1 prerequisites check — all 6 M1 frameworks MUST be complete
- step-05-synthesis explicitly updates project-memo.md and defines kill/pivot/persevere criteria
- Framework knowledge extracted into data/leap-of-faith-framework.md (117 lines)
- Validation Backlog maps assumptions to M2/M5 downstream frameworks
- Kill criteria definition is emphasized as "most important part of entire framework"
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/workflow.md` (created, 85 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/data/leap-of-faith-framework.md` (created, 117 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/steps-c/step-01-init.md` (created, 136 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/steps-c/step-02-harvest.md` (created, 176 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/steps-c/step-03-classify.md` (created, 176 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/steps-c/step-04-prioritize.md` (created, 202 lines)
- `_bmad/rbtv/workflows/bi-m2-leap-of-faith/steps-c/step-05-synthesis.md` (created, 239 lines)

### Task p4-5: Create Unit Economics Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Unit Economics framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, cac-analysis, ltv-calculation, payback-period, synthesis (follows source 6-task structure consolidated into 5 steps)
- Prerequisites enforced: TAM/SAM/SOM MUST be completed before starting
- Mandatory use of pessimistic/base/optimistic ranges — never point estimates
- LTV:CAC ratio must be evaluated on pessimistic scenario, not optimistic
- All CAC must include fully-loaded costs (people, tools, founder time), not just ad spend
- Churn benchmarks provided with segment-specific defaults (SMB 3-7%, Mid-market 0.8-1.2%, etc.)
- Break-even analysis requires imputed founder salaries (not $0)
- Sensitivity analysis identifies top 3-5 critical assumptions with validation criteria
- step-05-synthesis explicitly updates project-memo.md with viability assessment
- Framework knowledge extracted into data/unit-economics-framework.md (104 lines)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m2-unit-economics/workflow.md` (created, 75 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/data/unit-economics-framework.md` (created, 104 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/steps-c/step-01-init.md` (created, 138 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/steps-c/step-02-cac-analysis.md` (created, 168 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/steps-c/step-03-ltv-calculation.md` (created, 159 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/steps-c/step-04-payback-period.md` (created, 163 lines)
- `_bmad/rbtv/workflows/bi-m2-unit-economics/steps-c/step-05-synthesis.md` (created, 220 lines)

### Task p4-6: Create Technology Readiness Level Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete TRL framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, current-trl-assessment, target-trl, gap-analysis, synthesis (follows source 5-task structure)
- Can run in parallel with TAM/SAM/SOM and Unit Economics — no strict prerequisite
- NASA TRL 1-9 scale adapted for digital startups with concrete examples
- Component decomposition requires 4-10 building blocks with type classification (Novel/Adapted/Standard)
- Novel components CANNOT be scored above TRL 3 without proof-of-concept evidence
- Technical risks assessed across 7 categories (Performance, Scalability, Integration, Data, Security, Skills, Cost)
- Spike cards required for all components below TRL 4 with measurable success/failure criteria
- At least one spike MUST connect failure criteria to kill criterion
- Overall posture assessment: Green (ready for M4), Yellow (spikes < 2 weeks), Red (feasibility in question)
- step-05-synthesis explicitly updates project-memo.md with posture and wires to Pre-mortem, M4, M6
- Framework knowledge extracted into data/trl-framework.md (96 lines)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/workflow.md` (created, 73 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/data/trl-framework.md` (created, 96 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/steps-c/step-01-init.md` (created, 134 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/steps-c/step-02-current-trl-assessment.md` (created, 175 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/steps-c/step-03-target-trl.md` (created, 176 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/steps-c/step-04-gap-analysis.md` (created, 192 lines)
- `_bmad/rbtv/workflows/bi-m2-technology-readiness-level/steps-c/step-05-synthesis.md` (created, 194 lines)

### Task p4-7: Create Pre-mortem Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Pre-mortem framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, failure-scenarios, risk-ranking, mitigations, synthesis (follows source 5-task structure)
- Prerequisites enforced: All prior M2 frameworks (LoF, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL) MUST be complete
- step-05-synthesis explicitly updates project-memo.md AND triggers M2 completion check (final M2 framework)
- Framework knowledge extracted into data/pre-mortem-framework.md (109 lines)
- Prospective hindsight framing enforced: past-tense "We failed because..." not conditional "might fail if"
- 7 failure categories documented (market, product, team, financial, technical, competitive, operational)
- Minimum 15 failure modes required across 5+ categories
- Mitigation cards require specific, time-bound actions with measurable early warning signals
- Severity 5 failures MUST have contingency plans
- Kill criteria cross-referencing is mandatory (align with Leap of Faith or propose new criteria)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/workflow.md` (created, 95 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/data/pre-mortem-framework.md` (created, 109 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/steps-c/step-01-init.md` (created, 170 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/steps-c/step-02-failure-scenarios.md` (created, 176 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/steps-c/step-03-risk-ranking.md` (created, 156 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/steps-c/step-04-mitigations.md` (created, 188 lines)
- `_bmad/rbtv/workflows/bi-m2-pre-mortem/steps-c/step-05-synthesis.md` (created, 200 lines)

### Task p5-1: Create M3 Milestone Workflow
**Completed:** 2026-02-05
**Outcome:** Created M3 Brand milestone workflow with 6 framework routing
**Decisions:**
- Followed M1/M2 milestone pattern with identical structure
- 6 frameworks: Brand Archetypes, Brand Prism, Golden Circle, Brand Positioning, Tone of Voice, Messaging Architecture
- Navigation codes: [BA], [BP], [GC], [PO], [TV], [MA], [S], [B]
- Success criteria adapted from brand_process.md
**Issues:** None
**Files Modified:** `_bmad/rbtv/workflows/bi-m3/workflow.md` (created, 62 lines)

### Task p5-2: Create Brand Archetypes Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Brand Archetypes framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, exploration, selection, application, synthesis
- step-01-init includes M1/M2 prerequisite verification (Working Backwards, JTBD, Lean Canvas + 3 M2 frameworks)
- step-02-exploration requires ALL 12 archetypes evaluated with evidence-backed scoring
- step-03-selection enforces primary archetype in top 2, or override requires explicit justification
- step-04-application defines 4 expression dimensions: voice, visuals, relationship, content themes
- step-05-synthesis includes differentiation and coherence stress tests, updates project-memo.md
- Framework knowledge extracted into data/brand-archetypes-framework.md (74 lines) with 12 archetypes organized by motivation quadrant
- Incoherent archetype combinations documented (Outlaw+Ruler, Innocent+Outlaw, etc.)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/workflow.md` (created, 57 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/data/brand-archetypes-framework.md` (created, 74 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/steps-c/step-01-init.md` (created, 116 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/steps-c/step-02-exploration.md` (created, 134 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/steps-c/step-03-selection.md` (created, 124 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/steps-c/step-04-application.md` (created, 164 lines)
- `_bmad/rbtv/workflows/bi-m3-brand-archetypes/steps-c/step-05-synthesis.md` (created, 152 lines)

### Task p6-1: Evaluate M4 Prototypation Against BMAD Workflows
**Completed:** 2026-02-05
**Outcome:** Evaluated all M4 Prototypation frameworks against BMAD workflows; produced integration strategy
**Decisions:**
- BMAD `create-ux-design` covers: Design Brief, Design Tokens, Visual Identity, Creative Discovery, Inspiration Research
- BMAD does NOT cover: User Flow Mapping, Information Architecture (conversion funnel vs visual design), Conversion-Centered Design, Heuristic Evaluation
- Lavoisier agent already exists in RBTV and is integrated with `create-ux-design` via skills (visual-design-extraction, playwright-browser-automation)

**M4 Framework Evaluation Table:**

| M4 Framework | BMAD Equivalent | Integration Strategy |
|--------------|-----------------|---------------------|
| User Flow Mapping | None (partial overlap with layout philosophy) | **CREATE RBTV**: Founder-specific conversion path mapping |
| Information Architecture | None (partial overlap with layout philosophy) | **CREATE RBTV**: Founder-specific content hierarchy |
| Design Brief + Design Tokens | `create-ux-design` (full) | **ROUTE TO BMAD**: design_brief.md + design.json |
| Atomic Design | `create-ux-design` (partial via component personality) | **EMBED**: Reference in BMAD workflow |
| Conversion-Centered Design | None | **CREATE RBTV**: Founder-specific conversion optimization |
| WCAG Accessibility | None (industry standard) | **EMBED**: Checklist in synthesis step |
| Responsive Design | None (industry standard) | **EMBED**: Checklist in synthesis step |
| Progressive Disclosure | `create-ux-design` (partial via layout philosophy) | **EMBED**: Reference in BMAD workflow |
| Heuristic Evaluation | None | **CREATE RBTV**: Nielsen's 10 heuristics evaluation |
| Lavoisier Agent | `create-ux-design` (uses same skills) | **KEEP RBTV**: Unique creative discovery agent |

**M4 Mentor Routing Structure:**
```
M4 Prototypation Mentor Routing:
├── [U] User Flow & IA → bi-m4-user-flow-ia (RBTV) → prepares conversion context
├── [D] Design Direction → BMAD create-ux-design (Lavoisier as facilitator)
├── [B] Build Prototype → bi-m4-build-prototype (RBTV) → HTML implementation
├── [C] Conversion Optimization → bi-m4-conversion-centered-design (RBTV)
├── [H] Heuristic Evaluation → bi-m4-heuristic-evaluation (RBTV)
└── [F] F&F Testing Prep → bi-m4-testing-prep (RBTV)
```

**Issues:** None
**Files Modified:** shape.md (this entry)

### Task p6-2: Decide and Document M4 Integration Scope
**Completed:** 2026-02-05
**Outcome:** Decision made: **Option A — Full BMAD Integration**
**Decision Rationale:**
- Avoids duplicating UX design capabilities that BMAD already provides excellently
- Preserves founder-specific value: conversion optimization, heuristic evaluation, F&F testing
- Leverages existing Lavoisier agent through BMAD skill integration
- Creates thin bridge workflows that prepare founder context for BMAD

**Option A Integration Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                     M4 PROTOTYPATION                            │
├─────────────────────────────────────────────────────────────────┤
│  RBTV WORKFLOWS (Founder-Specific)                              │
│  ├── bi-m4-user-flow-ia         User flows + content hierarchy  │
│  ├── bi-m4-build-prototype      HTML implementation guidance    │
│  ├── bi-m4-conversion-centered  Conversion optimization         │
│  ├── bi-m4-heuristic-eval       Nielsen's 10 heuristics         │
│  └── bi-m4-testing-prep         F&F test protocol               │
├─────────────────────────────────────────────────────────────────┤
│  BMAD INTEGRATION (Route to Existing)                           │
│  └── create-ux-design           Design brief + tokens via       │
│                                 Lavoisier creative discovery    │
├─────────────────────────────────────────────────────────────────┤
│  EMBEDDED STANDARDS (Checklists in synthesis)                   │
│  ├── WCAG Accessibility         AA compliance checklist         │
│  ├── Responsive Design          Breakpoint validation           │
│  └── Atomic Design              Component inventory ref         │
└─────────────────────────────────────────────────────────────────┘
```

**Components to Create in p6-3:**
1. `bi-m4/workflow.md` — Milestone workflow with routing to RBTV + BMAD
2. `bi-m4-user-flow-ia/` — User Flow Mapping + Information Architecture (combined)
3. `bi-m4-build-prototype/` — HTML prototype implementation guidance
4. `bi-m4-conversion-centered-design/` — Conversion-Centered Design framework
5. `bi-m4-heuristic-evaluation/` — Heuristic Evaluation framework
6. `bi-m4-testing-prep/` — F&F Testing preparation

**Issues:** None
**Files Modified:** shape.md (this entry)

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `refs/founder/founder_process.md` | 6-milestone lifecycle structure, agent handoff protocol |
| `refs/founder/agents/paul.md` | 4-act structure, personality traits, session protocol |
| `refs/founder/m1_conception/conception_process.md` | 9-step process, 6 frameworks, success criteria |
| `_bmad/bmb/workflows/workflow/templates/*.md` | BMAD workflow templates |
| `_bmad/bmb/workflows/agent/templates/*.md` | BMAD agent templates |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `refs/founder/agents/paul.md` | Source for mentor agent persona | p1-2 |
| `refs/founder/templates/project_memo.md` | Source for project-memo template | p1-3 |
| ~~`refs/founder/templates/founder_diary.md`~~ | ~~Source for founder-diary template~~ | ~~p1-4~~ (CANCELLED — founder-diary eliminated) |
| `refs/founder/founder_process.md` | Source for milestone overview | p2-2 |
| `refs/founder/m1_conception/conception_process.md` | Source for M1 structure | p3-1 |
| `refs/founder/m1_conception/conception_frameworks/*.md` | Source for M1 framework knowledge | p3-2 to p3-7 |
| `_bmad/bmb/workflows/agent/templates/*.md` | BMAD agent template | p1-2 |
| `_bmad/bmb/workflows/workflow/templates/*.md` | BMAD workflow template | All workflow tasks |

> **Note:** `refs/` is at `BMAD/_bmad-output/rbtv-development/wip/founder-migration/refs` and contains the exact founder module content.

---

### Task p6-3 through p6-15: Phase 6 Task Restructuring
**Completed:** 2026-02-05 (executed via bi-m4-follow-up p4-open-migration-plan)
**Outcome:** Restructured Phase 6 to follow M1-M3 pattern (one task per component instead of bundled tasks). Original p6-3 (bundled M4 components) split into separate tasks; M5 and M6 structured with evaluate/decide/create pattern. Phase 6 now has 16 tasks (was 11).

**New Phase 6 Structure:**
- **M4 Tasks (p6-1 to p6-8):**
  - p6-1: Evaluate M4 (completed)
  - p6-2: Decide M4 (completed)
  - p6-3: CREATE bi-m4 milestone workflow (completed - exists)
  - p6-4: CREATE bi-m4-user-flow-ia (completed - exists)
  - p6-5: CREATE bi-m4-design-context bridge (completed - exists via bi-m4-follow-up)
  - p6-6: CREATE bi-m4-conversion-centered-design (pending)
  - p6-7: CREATE bi-m4-heuristic-evaluation (pending)
  - p6-8: UPDATE mentor agent for M4 routing (pending)

- **M5 Tasks (p6-9 to p6-11):**
  - p6-9: Evaluate M5 (pending)
  - p6-10: Decide M5 (pending)
  - p6-11: CREATE M5 milestone and frameworks per p6-10 decision (pending - placeholder, will be split after decision)

- **M6 Tasks (p6-12 to p6-14):**
  - p6-12: Evaluate M6 (pending)
  - p6-13: Decide M6 (pending)
  - p6-14: CREATE M6 milestone and frameworks per p6-13 decision (pending - placeholder, will be split after decision)

- **Completion Tasks (p6-15, p6-checkpoint):**
  - p6-15: CREATE M4, M5, M6 milestone workflow complete files (steps-c) - renamed from original p6-10
  - p6-checkpoint: Final checkpoint

**Rationale:** Original bundled tasks (p6-3 for all M4, p6-6 for all M5, p6-9 for all M6) caused token load issues. M1-M3 pattern (one task per component) is more efficient for execution. M5 and M6 will be further split after evaluate/decide phases determine component list.

**Files Modified:**
- business-innovation-migration_v3.plan.md (YAML todos and Phase 6 body)
- phase-6/p6-3.task.md through p6-15.task.md (created/updated)

**Issues:** None

**Note:** This restructuring was executed as part of bi-m4-follow-up plan task p4-open-migration-plan. See bi-m4-follow-up/shape.md for detailed execution log.

### Task p4-fix-m5m6-structure: Fix M5 and M6 Task Structure (via bi-m4-follow-up)
**Completed:** 2026-02-05 (executed via bi-m4-follow-up plan task p4-fix-m5m6-structure)
**Outcome:** Fixed M5 and M6 task structure by removing unnecessary evaluate/decide phases and opening directly like M1-M3 per existing integration strategy.

**M5 Market Validation — Opened Like M1-M3:**
- p6-9: CREATE bi-m5 milestone workflow
- p6-10: CREATE bi-m5-mom-test (bias-free customer interviews)
- p6-11: CREATE bi-m5-spin-selling (hypothesis-testing conversations)
- p6-12: CREATE bi-m5-smoke-test (behavioral evidence)
- p6-13: CREATE bi-m5-van-westendorp (pricing research with web research)
- p6-14: CREATE bi-m5-bullseye (channel prioritization with web research)
- p6-15: CREATE bi-m5-sean-ellis-pmf (PMF signal assessment)
- p6-16: UPDATE mentor agent for M5 routing

**M6 MVP — Minimal BMAD Routing:**
- p6-17: CREATE bi-m6 milestone workflow (minimal, routes to BMAD)
- p6-18: UPDATE mentor agent for M6 routing to BMAD workflows

**Steps-c split:**
- p6-19: CREATE M4 milestone workflow complete files (steps-c)
- p6-20: CREATE M5 milestone workflow complete files (steps-c)
- p6-21: CREATE M6 milestone workflow complete files (steps-c)
- Split per user request for granularity (one task per milestone instead of bundled)

**Before/After:**
- Before: 16 Phase 6 tasks (with evaluate/decide for M5 and M6)
- After: 21 Phase 6 tasks (M5 and M6 opened per framework like M1-M3, plus split steps-c)

**Rationale:** Integration strategy was already defined in plan (M5: RBTV-native, M6: full BMAD integration), so evaluate/decide phases were unnecessary overhead. Opening directly like M1-M3 is more efficient for execution.

**Files Modified:**
- business-innovation-migration_v3.plan.md (YAML todos and Phase 6 body)
- phase-6/p6-9.task.md through p6-21.task.md (restructured)
- Deleted old evaluate/decide placeholders: p6-11 (old M5 create), p6-12 (old evaluate M6), p6-13 (old decide M6), p6-14 (old create M6)

**Issues:** None

### Task p3-8: Create M1 Milestone Workflow Complete Files (steps-c)
**Completed:** 2026-02-05
**Outcome:** Created M1 milestone workflow steps-c folder with step-01-init.md (framework menu) and supporting data/milestone-overview.md knowledge file
**Decisions:**
- step-01-init.md presents framework routing menu with completion status and dependency checking
- Prerequisites enforced for dependent frameworks (JTBD requires WB, PSF requires WB+JTBD, etc.)
- Suggested next framework logic based on dependencies and completion status
- Override mechanism for prerequisites with explicit warning
- [S] Status option shows detailed framework completion with prerequisites
- [B] Back routes to bi-business-innovation step-03-milestone-select.md
- Created data/milestone-overview.md with framework dependencies, success criteria, and referral logic documentation
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m1/steps-c/step-01-init.md` (created, 246 lines)
- `_bmad/rbtv/workflows/bi-m1/data/milestone-overview.md` (created, 136 lines)

**Referral Logic Validation:**
- ✅ Milestone workflow (bi-m1) provides framework menu via step-01-init.md
- ✅ Framework workflows (all 6) instruct return to `../bi-m1/workflow.md` in synthesis steps
- ✅ Framework synthesis steps update project-memo.md before returning to milestone menu
- ✅ project-memo.md frontmatter tracks stepsCompleted for state management
- ✅ nextStep resolves: bi-m1/workflow.md → ./steps-c/step-01-init.md (file exists)

### Decision: Add Recommended Next Step Indicator to Framework Menu
**Date:** 2026-02-05
**Context:** User requested that framework menus show a visual indicator (e.g., `← Recommended next`) next to the recommended framework based on the founder's intended execution order from source *_process.md files.

**Decision:**
- **Storage:** Framework execution order stored in `data/milestone-overview.md` (knowledge file) with "Recommended Execution Order" section
- **Logic:** Recommendation logic implemented in `steps-c/step-01-init.md` Section 2 "Analyze Progress and Dependencies" with deterministic mapping from stepsCompleted to next framework
- **Display:** Visual indicator `← Recommended next` added to framework menu template in Section 4 with instructions to display next to suggested framework
- **Override:** Users can still select any framework with met prerequisites (recommendation is guidance, not enforcement)

**Implementation Details:**

1. **Knowledge File (data/milestone-overview.md):**
   - Added "Recommended Execution Order" section at top of "Framework Sequence and Dependencies"
   - Order from conception_process.md Steps 2-7: WB → JTBD → CL → PSF → LC → 5W
   - Each framework entry now includes "Recommended Order" field

2. **Menu Logic (steps-c/step-01-init.md Section 2):**
   - Table maps completion state to recommended next framework
   - Examples: 
     - No frameworks complete → recommend Working Backwards (Order: 1)
     - Only WB complete → recommend Jobs-to-be-Done (Order: 2)
     - WB + JTBD complete → recommend Competitive Landscape (Order: 3)
     - etc.

3. **Menu Display (steps-c/step-01-init.md Section 4):**
   - Template includes `{recommended-indicator-if-suggested}` placeholder
   - Instructions specify: add ` ← Recommended next` only if framework matches Section 2 recommendation
   - Prerequisites show ✓/✗ for completion status
   - Example display: `[JT] Jobs-to-be-Done — Customer job analysis ← Recommended next`
                     `     Prerequisites: Working Backwards ✓`

**Rationale:**
- Follows founder module's original intention for framework sequencing (conception_process.md)
- Maintains user agency (can override recommendation if prerequisites met)
- Reduces cognitive load for new founders by providing clear guidance
- Deterministic logic ensures consistent recommendations across sessions

**Pattern to Replicate:**
- M2 (bi-m2): Order from validation_process.md Steps 2-7: LoF → AM → TAM/SAM/SOM → UE → TRL → Pre-mortem
- M3 (bi-m3): Order from brand_process.md Steps 2-7: BA → BP → GC → PO → MA → ToV
- Each milestone needs same 3-part implementation (knowledge file, logic, display)

### Task p4-8: Create M2 Milestone Workflow Complete Files (steps-c)
**Completed:** 2026-02-05
**Outcome:** Created M2 milestone workflow steps-c folder with step-01-init.md (framework menu) and supporting data/milestone-overview.md knowledge file
**Decisions:**
- step-01-init.md presents framework routing menu with completion status and dependency checking
- Prerequisites enforced for dependent frameworks (AM requires LoF, UE requires TS, PM requires all prior M2, etc.)
- Suggested next framework logic based on dependencies and completion status from validation_process.md Steps 2-7
- Override mechanism for prerequisites with explicit warning
- [S] Status option shows detailed framework completion with prerequisites
- [B] Back routes to bi-business-innovation step-03-milestone-select.md
- Created data/milestone-overview.md with framework dependencies, recommended execution order, success criteria, and referral logic documentation
- Applied same 3-part pattern from M1: knowledge file (recommended order) + logic (Section 2) + display (Section 4 with `← Recommended next` indicator)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m2/steps-c/step-01-init.md` (created, 282 lines)
- `_bmad/rbtv/workflows/bi-m2/data/milestone-overview.md` (created, 151 lines)

**Referral Logic Validation:**
- ✅ Milestone workflow (bi-m2) provides framework menu via step-01-init.md
- ✅ Framework workflows (all 6) instruct return to `../bi-m2/workflow.md` in synthesis steps
- ✅ Framework synthesis steps update project-memo.md before returning to milestone menu
- ✅ project-memo.md frontmatter tracks stepsCompleted for state management
- ✅ nextStep resolves: bi-m2/workflow.md → ./steps-c/step-01-init.md (file exists)
 
  
 
### Task p6-6: Create bi-m4-conversion-centered-design Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Conversion-Centered Design framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, funnel-mapping, hypothesis-generation, optimization-plan, synthesis
- Prerequisites enforced: User Flow & IA [U] MUST be completed before this framework
- Framework applies 7 CCD principles: Attention Ratio, Visual Hierarchy, Directional Cues, Friction Reduction, Urgency/Scarcity, Encapsulation, Congruence
- Friction point analysis uses 5-level severity rating (Critical to Cosmetic)
- Hypothesis generation uses IF/THEN/BECAUSE template linked to CCD principles
- Prioritization uses Impact vs. Effort matrix with Quick Wins first
- Testing roadmap structured for F&F qualitative feedback (not statistical A/B testing)
- step-05-synthesis explicitly updates project-memo.md and instructs return to M4 menu
- Framework knowledge extracted into data/conversion-framework.md (135 lines)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/workflow.md` (created, 57 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/data/conversion-framework.md` (created, 135 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/steps-c/step-01-init.md` (created, 109 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/steps-c/step-02-funnel-mapping.md` (created, 147 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/steps-c/step-03-hypothesis-generation.md` (created, 142 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/steps-c/step-04-optimization-plan.md` (created, 189 lines)
- `_bmad/rbtv/workflows/bi-m4-conversion-centered-design/steps-c/step-05-synthesis.md` (created, 159 lines)
- `_bmad/rbtv/workflows/bi-m4/workflow.md` (updated framework routing table to mark [C] as Available)

### Task p5-7: Create bi-m3-messaging-architecture Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Messaging Architecture framework workflow with 6 step files and knowledge data
**Decisions:**
- 6-step sequence: init, brand-promise, key-messages, proof-points, ctas-journey, synthesis
- Prerequisites enforced: M1 (Working Backwards, JTBD, Lean Canvas), M2 (3+ frameworks), M3 (Brand Positioning, Golden Circle, Brand Prism) MUST be complete
- Framework builds 4-level hierarchy: Brand Promise (max 15 words) → Key Messages (3-5 per audience) → Proof Points (2-3 per message) → CTAs (by journey stage)
- Four standard audiences: Early Adopters, Mainstream Customers, Partners, Investors
- Every message requires traceability annotation to framework output or validated assumption
- Proof points must document: point, source, type (data/customer quote/feature-benefit/third-party), status (validated/hypothetical)
- Messages with insufficient proof flagged for M5 validation with experiment suggestions
- CTAs mapped to 4 journey stages (Awareness, Consideration, Decision, Retention) with channel/message/proof links
- Audience Message Cards created as one-page operational quick-reference per audience
- Hierarchy traceability validation ensures CTAs→Messages→Promise and Messages→Proof connections
- Downstream integration notes prepared for Tone of Voice (M3), M4 Prototypation, M5 Market Validation, M6 MVP
- step-06-synthesis explicitly updates project-memo.md and instructs return to M3 menu
- Framework knowledge extracted into data/messaging-architecture-framework.md (249 lines)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/workflow.md` (created, 82 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/data/messaging-architecture-framework.md` (created, 249 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-01-init.md` (created, 170 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-02-brand-promise.md` (created, 182 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-03-key-messages.md` (created, 246 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-04-proof-points.md` (created, 228 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-05-ctas-journey.md` (created, 249 lines)
- `_bmad/rbtv/workflows/bi-m3-messaging-architecture/steps-c/step-06-synthesis.md` (created, 285 lines)

**Referral Logic Validation:**
- ✅ M3 milestone workflow (bi-m3) already includes Messaging Architecture [MA] in framework routing table
- ✅ Framework workflow instructs return to `../bi-m3/workflow.md` in step-06-synthesis
- ✅ step-06-synthesis updates project-memo.md before returning to milestone menu
- ✅ project-memo.md frontmatter tracks stepsCompleted for state management
- ✅ nextStep resolves: bi-m3-messaging-architecture/workflow.md → ./steps-c/step-01-init.md (file exists)

### Task p5-8: Create M3 Milestone Workflow Complete Files (steps-c)
**Completed:** 2026-02-05
**Outcome:** Created M3 milestone workflow steps-c folder with step-01-init.md (framework menu) and supporting data/milestone-overview.md knowledge file
**Decisions:**
- step-01-init.md presents framework routing menu with completion status and dependency checking
- Prerequisites enforced for dependent frameworks (BP requires BA recommended, GC requires BP+BA recommended, etc.)
- Suggested next framework logic based on dependencies and completion status from brand_process.md Steps 2-7
- Override mechanism for prerequisites with explicit warning
- [S] Status option shows detailed framework completion with prerequisites
- [B] Back routes to bi-business-innovation step-03-milestone-select.md
- Created data/milestone-overview.md with framework dependencies, recommended execution order, success criteria, and referral logic documentation
- Applied same 3-part pattern from M1/M2: knowledge file (recommended order) + logic (Section 2) + display (Section 4 with `← Recommended next` indicator)
- Recommended execution order: Brand Archetypes → Brand Prism → Golden Circle → Brand Positioning → Messaging Architecture → Tone of Voice
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m3/steps-c/step-01-init.md` (created, 290 lines)
- `_bmad/rbtv/workflows/bi-m3/data/milestone-overview.md` (created, 213 lines)

**Referral Logic Validation:**
- ✅ Milestone workflow (bi-m3) provides framework menu via step-01-init.md
- ✅ Framework workflows (all 6) instruct return to `../bi-m3/workflow.md` in synthesis steps
- ✅ Framework synthesis steps update project-memo.md before returning to milestone menu
- ✅ project-memo.md frontmatter tracks stepsCompleted for state management
- ✅ nextStep resolves: bi-m3/workflow.md → ./steps-c/step-01-init.md (file exists)

### Task p6-7: Create bi-m4-heuristic-evaluation Framework Workflow
**Completed:** 2026-02-05
**Outcome:** Created complete Heuristic Evaluation framework workflow with 5 step files and knowledge data
**Decisions:**
- 5-step sequence: init, heuristic-review, severity-rating, recommendations, synthesis
- Nielsen's 10 usability heuristics documented with founder-context examples
- Severity rating uses 0-4 scale (cosmetic to catastrophic) with frequency/impact/persistence factors
- Recommendations include effort estimates and quick wins identification (high impact, low effort)
- Pattern analysis identifies systemic issues vs. isolated problems
- Critical issues (severity 3-4) flagged for immediate attention before launch
- Assumptions to validate in M5 documented in synthesis
- step-05-synthesis explicitly updates project-memo.md and instructs return to M4 menu
- Framework knowledge extracted into data/heuristic-framework.md (193 lines)
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/workflow.md` (created, 55 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/data/heuristic-framework.md` (created, 193 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/steps-c/step-01-init.md` (created, 138 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/steps-c/step-02-heuristic-review.md` (created, 128 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/steps-c/step-03-severity-rating.md` (created, 140 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/steps-c/step-04-recommendations.md` (created, 189 lines)
- `_bmad/rbtv/workflows/bi-m4-heuristic-evaluation/steps-c/step-05-synthesis.md` (created, 201 lines)

### Task p6-8: Update Mentor Agent for M4 Routing Logic
**Completed:** 2026-02-05
**Outcome:** Added XML comment block after M4 menu item documenting M4's internal framework routing structure
**Decisions:**
- Comment documents all 4 M4 frameworks: [U] User Flow & IA, [D] Design Direction (bridge), [C] Conversion Optimization, [H] Heuristic Evaluation
- Design discovery mechanism note included (visual-design-extraction, playwright-browser-automation skills)
- No Lavoisier references (correctly references bi-m4-design-context bridge to BMAD create-ux-design)
- M4 menu item itself unchanged — documentation only
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/agents/paul.md` (updated, added comment block after line 81)

### Task p6-19: Create M4 Milestone Workflow Complete Files (steps-c)
**Completed:** 2026-02-05
**Outcome:** Created M4 milestone workflow steps-c folder with step-01-init.md (framework menu) and supporting data/milestone-overview.md knowledge file
**Decisions:**
- step-01-init.md presents framework routing menu with completion status and dependency checking
- Recommended execution order: User Flow & IA → Design Direction → Build Prototype → Conversion Optimization → Heuristic Evaluation → Testing Prep
- Frameworks [B] Build Prototype and [F] Testing Prep marked as "🚧 Planned (to be created)" and not selectable
- Prerequisites enforced for dependent frameworks (D requires U recommended, C requires U, H requires B recommended, F requires B+C+H recommended)
- Suggested next framework logic based on dependencies and completion status
- Override mechanism for prerequisites with explicit warning
- [S] Status option shows detailed framework completion with prerequisites
- [B] Back routes to bi-business-innovation step-03-milestone-select.md
- Created data/milestone-overview.md with framework dependencies, recommended execution order, success criteria, and referral logic documentation
- Applied same 3-part pattern from M1/M2/M3: knowledge file (recommended order) + logic (Section 2) + display (Section 4 with `← Recommended next` indicator)
- Updated bi-m4/workflow.md to set nextStep to ./steps-c/step-01-init.md and update knowledge files section
**Issues:** None
**Files Modified:**
- `_bmad/rbtv/workflows/bi-m4/steps-c/step-01-init.md` (created, 263 lines)
- `_bmad/rbtv/workflows/bi-m4/data/milestone-overview.md` (created, 140 lines)
- `_bmad/rbtv/workflows/bi-m4/workflow.md` (updated, 112 lines)

**Referral Logic Validation:**
- ✅ Milestone workflow (bi-m4) provides framework menu via step-01-init.md
- ✅ Framework workflows (U, D, C, H) instruct return to `../bi-m4/workflow.md` in synthesis steps
- ✅ Framework synthesis steps update project-memo.md before returning to milestone menu
- ✅ project-memo.md frontmatter tracks stepsCompleted for state management
- ✅ nextStep resolves: bi-m4/workflow.md → ./steps-c/step-01-init.md (file exists)
- ✅ Planned frameworks [B] and [F] clearly marked and not selectable until created

---

## Discovery 7: BMAD Config Management for RBTV-BMAD Integration

**Date:** 2026-02-05
**Context:** M4 Design Direction bridge invokes BMAD create-ux-design; M6 routes entirely to BMAD workflows. BMAD reads output_folder from config file, but RBTV uses project-specific paths.

**Problem:**
- RBTV workflows use project-specific output folders: `_bmad-output/{project-name}/founder/m4-prototypation/`
- BMAD workflows read config from disk: `_bmad/bmm/config.yaml` with `output_folder: {project-root}/_bmad-output`
- When RBTV invokes BMAD, BMAD outputs land in wrong location (root `_bmad-output/` instead of project folder)
- BMAD does not accept invocation-time overrides; only reads from config file

**Decision:**
Created two tasks to manage BMAD config before/after invocation:
1. `update-bmad-config.xml` — updates BMAD module config to use RBTV project folder
2. `restore-bmad-config.xml` — restores BMAD module config to defaults

**Convention:**
All RBTV workflows that invoke BMAD MUST:
1. Run `update-bmad-config.xml` BEFORE invoking BMAD
2. Run `restore-bmad-config.xml` AFTER BMAD completes

**Affected Workflows:**
- M4 Design Direction bridge (bi-m4-design-context) → invokes create-ux-design
- M6 all routes (bi-m6) → invokes create-prd, create-architecture, create-epics-and-stories, dev-story, qa-automate

**Implementation:**
- Tasks created: `_bmad/rbtv/tasks/update-bmad-config.xml`, `_bmad/rbtv/tasks/restore-bmad-config.xml`
- Plan updated: Added "BMAD Config Management Convention" section to Phase 6 integration strategy
- Task files updated: p6-17 (M6 milestone), p6-18 (M6 mentor) with config management instructions
- M5 not affected: RBTV-native, no BMAD invocations

**Files Modified:**
- `_bmad/rbtv/tasks/update-bmad-config.xml` (created)
- `_bmad/rbtv/tasks/restore-bmad-config.xml` (created)
- `.cursor/plans/founder-migration/business-innovation-migration_v3.plan.md` (updated)
- `.cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-17.task.md` (updated)
- `.cursor/plans/founder-migration/business-innovation-migration_v3/phase-6/p6-18.task.md` (updated)
- `_bmad/rbtv/workflows/bi-m4-design-context/workflow.md` (updated: step sequence + success criteria)
- `_bmad/rbtv/workflows/bi-m4-design-context/steps-c/step-02-format-context.md` (updated: nextStepFile)
- `_bmad/rbtv/workflows/bi-m4-design-context/steps-c/step-02b-update-config.md` (created)
- `_bmad/rbtv/workflows/bi-m4-design-context/steps-c/step-03-invoke-bmad.md` (updated: nextStepFile)
- `_bmad/rbtv/workflows/bi-m4-design-context/steps-c/step-03b-restore-config.md` (created)
- `.cursor/plans/founder-migration/business-innovation-migration_v3/shape.md` (this entry)
