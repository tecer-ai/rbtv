---
name: context-preservation
overview: Implement RBTV Memory System and Context Preservation Rule — agent self-improvement memory, session context capture, and plan-lifecycle integration
todos:
  - id: p1-1
    content: "p1-1: CREATE .cursor/rules/bmad-rbtv-memory-system.mdc with agent behavior instructions (directory structure, read at session start, write immediately, self-correction capture, entry format) [phase-1/p1-1.task.md]"
    status: completed
  - id: p1-2
    content: "p1-2: CREATE reorganize memory skill implementing the 7-step maintenance protocol [phase-1/p1-2.task.md]"
    status: completed
  - id: p1-3
    content: "p1-3: UPDATE .gitignore to add .claude/memory/ exclusion"
    status: completed
  - id: p1-4
    content: "p1-4: UPDATE _config/bootstrap.py to protect .claude/memory/ directory during install/sync operations [phase-1/p1-4.task.md]"
    status: completed
  - id: p1-checkpoint
    content: P1 CHECKPOINT - Validate memory system deliverables against PRD acceptance criteria
    status: completed
  - id: p2-1
    content: "p2-1: CREATE universal shape template at _shared/templates/shape-template.md by generalizing plan-lifecycle template with conditional plan-specific sections [phase-2/p2-1.task.md]"
    status: completed
  - id: p2-2
    content: "p2-2: CREATE .cursor/rules/bmad-rbtv-context-preservation.mdc with Detect→Discover→Confirm→Capture sequence, 8 detection signals, shape.md fallback, living document principle [phase-2/p2-2.task.md]"
    status: completed
  - id: p2-checkpoint
    content: P2 CHECKPOINT - Validate context preservation rule and template against compound acceptance criteria
    status: completed
  - id: p3-1
    content: "p3-1: UPDATE plan-lifecycle/steps-c/step-04-generate-artifacts.md to check for existing shape.md and merge instead of overwrite [phase-3/p3-1.task.md]"
    status: completed
  - id: p3-2
    content: "p3-2: UPDATE plan-lifecycle/data/plan-creation-rules.md to reference context preservation rule for shape.md writes instead of containing independent instructions"
    status: completed
  - id: p3-3
    content: "p3-3: UPDATE plan-lifecycle/workflow.md shapeTemplateFile to point to universal template at _shared/templates/shape-template.md"
    status: completed
  - id: p3-checkpoint
    content: P3 CHECKPOINT - Validate plan-lifecycle integration preserves existing functionality
    status: completed
  - id: p4-refs
    content: "p4-refs: Verify all markdown links in plan artifacts resolve and comply with plan linking standard (internal = file-relative, external = root-relative)"
    status: completed
  - id: p4-compound
    content: "p4-compound: Review learnings.md and compound into system improvements"
    status: completed
  - id: p4-checkpoint
    content: P4 FINAL CHECKPOINT - User approval to complete plan
    status: completed
isProject: false
---

# Context Preservation

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (path in `[brackets]` at end of todo content) for per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.


| Principle                               | Enforcement                                                                                    |
| --------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Memory files are never committed to git | Verified at P1 checkpoint — `.gitignore` includes `.claude/memory/`                            |
| "Write immediately" principle           | Both rules enforce immediate capture — never deferred to session end                           |
| Installer must not overwrite memory     | `bootstrap.py` protection verified at P1 checkpoint                                            |
| Rule files must be self-contained       | Each `.mdc` file interpretable without reading other files — per atomic files rule             |
| Universal template owns shape format    | Plan-lifecycle references shared template at `_shared/templates/`, not its own copy |
| Self-correction is autonomous           | Agent writes to `tools/{tool}.md` on fail→retry→succeed without user prompting                 |


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

## Phase 1: Memory System

**Goal:** Implement the memory system infrastructure — rule file, reorganize skill, git exclusion, and installer safety.

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> - `.cursor/rules/bmad-rbtv-memory-system.mdc` (new rule file — memory system agent behaviors)
> - Reorganize memory skill (new skill — location per RBTV conventions)
> - `.gitignore` (modified — added `.claude/memory/` exclusion)
> - `_config/bootstrap.py` (modified — memory directory protection)
>
> ## Quality Criteria
>
> 1. Memory rule defines complete `.claude/memory/` directory structure (memory.md, general.md, domain/, tools/)
> 2. Memory rule instructs agents to read memory.md at session start and write immediately when discovering knowledge
> 3. Self-correction capture is specified: fail→retry→succeed triggers autonomous write to `tools/{tool}.md` using format `date | SELF-CORRECTION: failed → working | reason`
> 4. Memory rule instructs agents to read relevant `tools/*.md` before executing commands to avoid repeating known failures
> 5. Reorganize memory skill implements all 7 maintenance steps from the PRD (read all files, remove duplicates, merge related, split large topics, re-sort by date, update index, show summary)
> 6. `.gitignore` excludes `.claude/memory/` for admin/standalone mode
> 7. `bootstrap.py` protects `.claude/memory/` directory during install/sync operations

## Phase 2: Context Preservation

**Goal:** Create the context preservation rule and universal shape template.

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> - `_shared/templates/shape-template.md` (new universal shape template)
> - `.cursor/rules/bmad-rbtv-context-preservation.mdc` (new rule file — context preservation behaviors)
>
> ## Quality Criteria
>
> 1. Context preservation rule defines 8 explicit detection signals with trigger threshold of 2+ signals across one or more turns
> 2. Rule specifies Detect → Discover → Confirm → Capture sequence in exact order
> 3. Rule requires reading target system conventions before proposing capture mechanism
> 4. Rule requires user confirmation before starting capture
> 5. Rule specifies shape.md as universal fallback with reference to universal template
> 6. Rule states living document principle — continuous writes, never deferred to session end
> 7. Universal shape template has both universal sections and conditional plan-specific sections clearly marked
> 8. Edge cases addressed: freeform session naming convention (`{date}-{topic}-shape.md`) and single-turn rich context trigger (changed from "multiple turns" to "one or more turns")

## Phase 3: Plan-Lifecycle Integration

**Goal:** Integrate context preservation into the existing plan-lifecycle workflow without breaking existing functionality.

#### P3 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> - `workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md` (modified — shape.md merge logic)
> - `workflows/plan-lifecycle/data/plan-creation-rules.md` (modified — CP rule reference)
> - `workflows/plan-lifecycle/workflow.md` (modified — shapeTemplateFile path)
>
> ## Quality Criteria
>
> 1. Step-04 checks for existing shape.md and merges planning context into it instead of overwriting
> 2. Plan-creation-rules references context preservation rule instead of containing independent shape.md instructions
> 3. workflow.md shapeTemplateFile points to universal template at `_shared/templates/shape-template.md`
> 4. No references to old plan-specific shape template location remain in modified files
> 5. Plan-lifecycle workflow structure is preserved — no broken step references or missing sections

## Phase 4: Finalization

**Goal:** Verify references, compound learnings, and obtain final approval.

#### P4 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
>
> All plan artifacts across all phases:
>
> - Rule files: `bmad-rbtv-memory-system.mdc`, `bmad-rbtv-context-preservation.mdc`
> - Reorganize memory skill
> - Universal shape template at `_shared/templates/shape-template.md`
> - Modified plan-lifecycle files (step-04, plan-creation-rules, workflow.md)
> - Modified `.gitignore` and `bootstrap.py`
> - Companion files: `shape.md`, `learnings.md`
>
> ## Quality Criteria
>
> 1. All internal markdown links in plan artifacts resolve correctly (file-relative paths)
> 2. All external markdown links use project-root-relative paths
> 3. Learnings have been compounded into actionable system improvements (or documented as empty)
> 4. Memory System PRD acceptance criteria (12 items) are met
> 5. Context Preservation compound acceptance criteria (13 items) are met

