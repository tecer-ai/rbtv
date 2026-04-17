---
name: bi-workflow-framework-dedup-and-integrity
overview: Eliminate cross-framework content duplication and drift in the BI workflow by adding canonical assumptions, content ownership, consistency gates, and dedup verification across all milestone frameworks.
todos:
  - id: p1-1
    content: "p1-1: UPDATE project-memo template — add Canonical Assumption Inventory with Existential / High / Lower / Founder Convictions tiers [phase-1/p1-1.task.md]"
    status: completed
  - id: p1-2
    content: "p1-2: UPDATE 40+ BI workflow files — bulk rename founder/ path references to business-innovation/ (path-specific only) [phase-1/p1-2.task.md]"
    status: completed
  - id: p1-checkpoint
    content: P1 CHECKPOINT - Validate path references resolve correctly and project-memo template is well-formed
    status: in_progress
  - id: p2-1
    content: "p2-1: UPDATE founder-process.md — add content ownership mapping per milestone (which framework owns each concept) [phase-2/p2-1.task.md]"
    status: completed
  - id: p2-2
    content: "p2-2: UPDATE all framework template files — add Prior Context section (builds on, inherits, adds) [phase-2/p2-2.task.md]"
    status: completed
  - id: p2-checkpoint
    content: P2 CHECKPOINT - Review content ownership mapping completeness and Prior Context section design
    status: completed
  - id: p3-1
    content: "p3-1: UPDATE all 22 framework synthesis steps — add canonical assumption merging instruction [phase-3/p3-1.task.md]"
    status: completed
  - id: p3-2
    content: "p3-2: UPDATE all 22 framework synthesis steps — add conditional consistency gate (Party Mode recommendation, ≥3 frameworks trigger) [phase-3/p3-2.task.md]"
    status: completed
  - id: p3-3
    content: "p3-3: UPDATE all 22 framework synthesis steps — add deduplication verification instruction [phase-3/p3-3.task.md]"
    status: completed
  - id: p3-checkpoint
    content: P3 CHECKPOINT - Validate all 22 synthesis files contain assumption merging, consistency gate, and dedup verification
    status: completed
  - id: p4-refs
    content: "p4-refs: File reference review — verify all markdown links resolve and comply with Plan Linking Standard"
    status: completed
  - id: p4-compound
    content: "p4-compound: Review learnings.md and compound into system improvements"
    status: completed
  - id: p4-checkpoint
    content: P4 FINAL CHECKPOINT - User approval to complete plan
    status: completed
isProject: false
---

# BI Workflow Framework Dedup and Integrity

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (path in `[brackets]` at end of todo content) for per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.


| Principle                          | Enforcement                                                                                                                                                                             |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Path-specific replacement only     | Every `founder/` → `business-innovation/` replacement must be validated as a path reference; non-path uses of "founder" (e.g., "founder/team", "Founder Convictions") must be preserved |
| Content ownership is authoritative | The ownership mapping in `founder-process.md` is the single source of truth for which framework owns which concept — all Prior Context sections and dedup checks reference it           |
| Synthesis block ordering           | Dedup verification → main synthesis output → assumption merging → consistency gate → completion menu                                                                                    |
| First-framework exception          | First framework in each milestone is the concept originator — it gets the originator variant of dedup instruction, not the checker variant, and no Prior Context section                |
| Atomic Files compliance            | All modified files must remain self-contained and interpretable independently per `_bmad/rbtv/.cursor/rules/bmad-rbtv-atomic-files.mdc`                                                 |


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

## Phase 1: Structural Foundation

**Goal:** Establish the structural prerequisites — canonical assumption inventory in project-memo template and normalized output paths across all BI workflow files.

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Two deliverables from Phase 1:
>
> 1. Updated project-memo template at `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` — new `## Canonical Assumption Inventory` section added
> 2. Bulk path rename across 40+ files in `_bmad/rbtv/` — all `founder/` path references changed to `business-innovation/`
>
> ## Quality Criteria
>
> 1. Project-memo template contains a `## Canonical Assumption Inventory` section with four tiers: Existential, High-Risk, Lower-Risk, Founder Convictions
> 2. Each tier has a placeholder table with columns: ID, Assumption, Source Framework, Status, Evidence
> 3. Section is positioned logically within the template (after Tenets, before Progress)
> 4. Grep `_bmad/rbtv/` for `founder/` — every remaining match must be a non-path usage (prose context like "founder/team", labels like "Founder Convictions")
> 5. Grep for `business-innovation/` confirms replacements landed in all expected files (workflow.md frontmatter, step files, templates, config, tasks)
> 6. YAML frontmatter syntax is valid in all modified files (spot-check 5 files from different workflow groups)
> 7. No false-positive replacements — non-path "founder" occurrences are preserved unchanged

## Phase 2: Content Architecture

**Goal:** Define which framework owns each concept per milestone and add the Prior Context referencing structure to framework templates.

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Two deliverables from Phase 2:
>
> 1. Content ownership mapping added to `_bmad/rbtv/workflows/bi-business-innovation/data/founder-process.md` — defines which framework owns each concept per milestone
> 2. `## Prior Context` sections added to non-first framework template files across M1-M4
>
> ## Quality Criteria
>
> 1. Every repeating concept (customer, problem, segment, value prop, competitors, jobs, assumptions) has exactly one owning framework per milestone — no gaps, no overlaps
> 2. Ownership assignments are consistent with the framework execution sequence (earlier frameworks own foundational concepts)
> 3. The mapping covers at minimum M1 (6 frameworks) and M2 (6 frameworks)
> 4. Non-first framework templates have a `## Prior Context` section with Builds on / Inherits / Adds structure
> 5. First frameworks in each milestone do NOT have a Prior Context section (they are concept originators)
> 6. "Inherits" entries in Prior Context match the ownership mapping — each inherited concept points to the correct owning framework

## Phase 3: Synthesis Step Enhancement

**Goal:** Upgrade all 22 framework synthesis steps with three new capabilities: deduplication verification, assumption merging, and cross-framework consistency gate.

#### P3 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Three blocks added to all 22 framework synthesis step files across M1-M4:
>
> 1. Deduplication verification instruction (pre-output check)
> 2. Canonical assumption merging instruction (post-synthesis)
> 3. Conditional consistency gate block (Party Mode recommendation when ≥3 frameworks complete)
>
> Synthesis files (all paths relative to `_bmad/rbtv/workflows/`):
>
> - M1 (6): bi-m1-working-backwards, bi-m1-jobs-to-be-done, bi-m1-competitive-landscape, bi-m1-problem-solution-fit, bi-m1-lean-canvas, bi-m1-five-whys
> - M2 (6): bi-m2-leap-of-faith, bi-m2-assumption-mapping, bi-m2-tam-sam-som, bi-m2-unit-economics, bi-m2-technology-readiness-level, bi-m2-pre-mortem
> - M3 (7): bi-m3-brand-archetypes, bi-m3-brand-prism, bi-m3-golden-circle, bi-m3-brand-positioning, bi-m3-tone-of-voice, bi-m3-messaging-architecture, bi-m3-brandbook
> - M4 (3+1): bi-m4-user-flow-ia, bi-m4-heuristic-evaluation, bi-m4-design-context, bi-m4-conversion-centered-design
>
> ## Quality Criteria
>
> 1. All 22 synthesis files contain the deduplication verification block
> 2. All 22 synthesis files contain the assumption merging instruction block
> 3. All 22 synthesis files contain the conditional consistency gate block
> 4. Block ordering is correct: dedup verification appears BEFORE main synthesis output write; assumption merging appears AFTER synthesis; consistency gate appears AFTER assumption merging
> 5. First-framework files in each milestone have the originator variant of dedup instruction (not the checker variant)
> 6. Consistency gate trigger correctly references `stepsCompleted` from project-memo frontmatter
> 7. Consistency gate prompt template is consistent across all 22 files
> 8. All blocks use mandatory language ("must", "never") per Atomic Files rule

## Phase 4: Finalization

**Goal:** Verify reference integrity and compound system learnings.

#### P4 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> Complete plan deliverables across all 4 phases:
>
> - Phase 1: Project-memo template with canonical assumptions + 40+ files with path rename
> - Phase 2: Content ownership mapping + Prior Context sections in framework templates
> - Phase 3: 22 synthesis files with dedup, assumption merging, and consistency gate blocks
> - Phase 4: Reference verification and learnings compound
>
> ## Quality Criteria
>
> 1. All internal markdown links within modified files resolve correctly
> 2. No remaining `founder/` path references in workflow files (only non-path prose uses)
> 3. Learnings have been reviewed and compounded into actionable system improvements (or documented as empty if none accumulated)
> 4. All modified files comply with Atomic Files rule (self-contained, no content repetition, mandatory language)
> 5. Content ownership mapping, Prior Context sections, and dedup instructions form a consistent, non-contradictory system

