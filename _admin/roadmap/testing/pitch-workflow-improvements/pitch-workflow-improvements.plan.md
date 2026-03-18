---
name: pitch-workflow-improvements
overview: Improve pitch workflow HTML quality, output management, and artifact synchronization across three compound improvement areas
todos:
  - id: p1-1
    content: "p1-1: UPDATE html-patterns.md with Logo Pattern section, Background Image Pattern section, and Design Constraints rows 13–16 [phase-1/p1-1.task.md]"
    status: completed
  - id: p1-2
    content: "p1-2: UPDATE step-07-generate.md to add content-fit validation and logo-rendering verification rows"
    status: completed
  - id: p1-checkpoint
    content: P1 CHECKPOINT - Validate asset handling patterns and step-07 verification
    status: in_progress
  - id: p2-1
    content: "p2-1: UPDATE step-01-init.md to prompt for output path with client/fundraising folder conventions, defaults, and user approval gate"
    status: completed
  - id: p2-2
    content: "p2-2: CREATE step-10-pdf-validation.md with Decktape PDF export and Playwright visual QA loop [phase-2/p2-2.task.md]"
    status: completed
  - id: p2-3
    content: "p2-3: UPDATE step-09-synthesis.md frontmatter to chain to step-10-pdf-validation"
    status: completed
  - id: p2-4
    content: "p2-4: UPDATE workflow.md to register step-10 in the workflow step table"
    status: completed
  - id: p2-checkpoint
    content: P2 CHECKPOINT - Validate folder conventions, step-10 structure, and workflow chain integrity
    status: completed
  - id: p3-1
    content: "p3-1: UPDATE leo.md and roelof.md to add artifact sync rule in <rules> section"
    status: completed
  - id: p3-2
    content: "p3-2: UPDATE vivian.md to add artifact sync rule and update INPUT rule for content-change detection"
    status: completed
  - id: p3-3
    content: "p3-3: UPDATE step-e01-load.md to load narrative and companion docs during edit initialization"
    status: completed
  - id: p3-4
    content: "p3-4: UPDATE step-e02-edit.md to enforce sync check after content edits"
    status: completed
  - id: p3-5
    content: "p3-5: UPDATE step-07-generate.md to add post-generation artifact sync check"
    status: completed
  - id: p3-checkpoint
    content: P3 CHECKPOINT - Validate sync rules in agents, edit step enforcement, CSS-only exemption
    status: in_progress
  - id: p4-refs
    content: "p4-refs: File reference review — verify all modified files have valid internal links"
    status: completed
  - id: p4-compound
    content: "p4-compound: Review learnings.md and compound into system improvements"
    status: completed
  - id: p4-checkpoint
    content: P4 FINAL CHECKPOINT - User approval to complete plan
    status: completed
isProject: false
---

# Pitch Workflow Improvements

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (path in `[brackets]` at end of todo content) for per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.


| Principle                         | Enforcement                                                                                       |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| Compound docs are source of truth | All implementation content derived from compound docs — do not invent requirements                |
| step-07 change ordering           | Phase 1 verification rows must be in place before Phase 3 sync check                              |
| Existing file structure preserved | New sections/rows follow existing formatting, numbering, and ordering conventions in target files |
| Agent rule consistency            | Same sync rule wording for leo and roelof; vivian-specific changes documented separately          |
| Path verification                 | Verify target file paths exist before editing — flag path discrepancies in shape.md               |


**Inviolable Rules:**

1. Read shape.md execution log before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints require quality-review subagent execution before user-facing gate decision — never skip the review
5. Checkpoints require human approval — never auto-continue, even after `APPROVED` verdict
6. `REJECTED` checkpoints cannot advance — address feedback before re-evaluation
7. Append to shape.md after each task — never modify previous entries
8. Internal links use file-relative paths (`./`, `../`); external links use project-root-relative paths — see Plan Linking Standard

## Checkpoint Execution Protocol

Every checkpoint has a **"Checkpoint Review Prompt"** subsection in its phase body (marked with `####` heading and a blockquote containing the full prompt). At each checkpoint:

1. Locate the checkpoint's review prompt in the phase body section (e.g. "P1 Checkpoint Review Prompt")
2. Fire Task tool with `subagent_type='quality-review'`, passing the blockquoted prompt content
3. Present the `APPROVED` / `REJECTED` verdict to user
4. **HALT for human approval regardless of verdict**
5. If `REJECTED`, do not advance to the next phase — address feedback first

**Why body, not YAML:** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom fields are silently stripped when the executor updates task status.

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in shape.md
- Complex discovery: add new task to plan, document in shape.md, notify user

## Phase 1: Asset Handling & Layout Constraints

**Goal:** Add logo patterns, background image constraints, and content-fit validation to HTML generation so decks export cleanly on first PDF attempt.

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Updates to two files in the pitch workflow:
>
> - `_bmad/rbtv/workflows/pitch/data/html-patterns.md` — added Logo Pattern section, Background Image Pattern section, Design Constraints rows 13–16
> - `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` — added content-fit validation and logo-rendering verification rows
>
> ## Quality Criteria
>
> 1. Logo Pattern section covers single logo sizing, multi-logo layout, and color inversion on dark backgrounds
> 2. Background Image Pattern section enforces max 3 textured slides per deck with subtlety constraints
> 3. Design Constraints rows 13–16 exist with sequential numbering (no gaps or duplicates relative to existing rows)
> 4. step-07 verification rows check content-fit (no page-break overflow) and logo rendering
> 5. New sections follow the existing file's formatting conventions (heading levels, table structure, naming patterns)

## Phase 2: Output Management & PDF Validation

**Goal:** Structure output folders by target type and date, and add automated PDF export with visual QA loop as step-10.

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> New and modified files for pitch output management:
>
> - UPDATED: `_bmad/rbtv/workflows/pitch/steps-c/step-01-init.md` — output path prompt with folder conventions, defaults, and user approval
> - CREATED: `_bmad/rbtv/workflows/pitch/steps-c/step-10-pdf-validation.md` — Decktape export + Playwright QA loop
> - UPDATED: `_bmad/rbtv/workflows/pitch/steps-c/step-09-synthesis.md` — chains to step-10
> - UPDATED: `_bmad/rbtv/workflows/pitch/workflow.md` — registers step-10
>
> ## Quality Criteria
>
> 1. step-01 documents client folder structure (`_clients/{client}/presentations/YYYY-MM-DD-{objective}/`) and fundraising structure (`_fundraising/{round}/YYYY-MM-DD-{fund}/`) with subfolders (artifacts, assets, research) inline — no separate rule file
> 2. step-01 prompts for output path with sensible defaults and halts for user approval before creating folders
> 3. step-10 follows RBTV micro-file step conventions (frontmatter with stepNumber/stepName, MANDATORY SEQUENCE, menu, success criteria)
> 4. step-10 uses Decktape for PDF export (`npx decktape generic`) and Playwright MCP for page screenshots
> 5. Visual QA loop has explicit iteration limit (max 3 rounds)
> 6. Workflow chain is intact: step-09 nextStepFile points to step-10; workflow.md lists step-10

## Phase 3: Narrative Artifact Sync

**Goal:** Enforce bidirectional synchronization between HTML, narrative, and companion docs across all pitch agents and workflow steps.

#### P3 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Agent and step files updated for artifact synchronization:
>
> - UPDATED: `_bmad/rbtv/agents/leo.md` — artifact sync rule in `<rules>`
> - UPDATED: `_bmad/rbtv/agents/roelof.md` — artifact sync rule in `<rules>`
> - UPDATED: `_bmad/rbtv/agents/vivian.md` — artifact sync rule + INPUT rule update
> - UPDATED: `_bmad/rbtv/workflows/pitch/steps-e/step-e01-load.md` — loads narrative and companion docs
> - UPDATED: `_bmad/rbtv/workflows/pitch/steps-e/step-e02-edit.md` — sync enforcement after content edits
> - UPDATED: `_bmad/rbtv/workflows/pitch/steps-c/step-07-generate.md` — post-generation sync check
>
> ## Quality Criteria
>
> 1. All three pitch agents (leo, roelof, vivian) have artifact sync rule in `<rules>` section
> 2. Leo and roelof share identical sync rule wording
> 3. Vivian's INPUT rule updated to detect content-changing HTML edits vs. CSS-only changes
> 4. CSS-only changes do NOT trigger narrative sync (no false positives)
> 5. step-e01-load loads narrative and companion docs alongside HTML
> 6. step-e02-edit enforces sync check after content edits (not CSS-only)
> 7. step-07 includes post-generation sync check that validates HTML-narrative alignment

## Phase 4: Finalization

**Goal:** Verify references, compound learnings, complete plan.

#### P4 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> All plan deliverables across phases 1–3: `html-patterns.md`, `step-07-generate.md`, `step-01-init.md`, `step-10-pdf-validation.md`, `step-09-synthesis.md`, `workflow.md`, `leo.md`, `roelof.md`, `vivian.md`, `step-e01-load.md`, `step-e02-edit.md`. Plus `learnings.md` compound output.
>
> ## Quality Criteria
>
> 1. All internal markdown links in modified files resolve correctly
> 2. Learnings have been reviewed and compounded into actionable system improvements (or documented as empty if none)
> 3. Modified files remain self-contained per atomic files rule
> 4. All acceptance criteria from source compound docs are satisfied
> 5. No unintended side effects on existing pitch workflow steps 1–9

