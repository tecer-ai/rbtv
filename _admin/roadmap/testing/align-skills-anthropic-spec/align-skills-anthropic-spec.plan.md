---
name: align-skills-anthropic-spec
overview: "Align RBTV skill-building infrastructure with Anthropic's official Claude Skills specification: fix name mismatches, extend template, create standards rule, archive guide, update builder."
todos:
  # Phase 1: Standards & Compliance
  - id: p1-1
    content: "p1-1: UPDATE ide-loader-template.md skill section with Anthropic-aligned fields, naming rules, and optional subdirectories"
    taskFile: "phase-1/p1-1.task.md"
    status: completed
  - id: p1-2
    content: "p1-2: UPDATE name field in all 7 existing SKILL.md files in _config/.cursor/skills/ to match folder names"
    taskFile: "phase-1/p1-2.task.md"
    status: completed
  - id: p1-3
    content: "p1-3: CREATE bmad-rbtv-skill-standards.mdc rule in _config/.cursor/rules/"
    taskFile: "phase-1/p1-3.task.md"
    status: completed
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - Review template, name fixes, and rule before proceeding to knowledge archival"
    status: completed
  # Phase 2: Knowledge & Integration
  - id: p2-1
    content: "p2-1: CREATE platform knowledge document for Anthropic Skills guide and UPDATE knowledge-index.csv"
    taskFile: "phase-2/p2-1.task.md"
    status: completed
  - id: p2-2
    content: "p2-2: UPDATE agents/fernando.md to reference skill-standards rule in [CI] handler"
    status: completed
  - id: p2-checkpoint
    content: "P2 CHECKPOINT - Review knowledge archive and builder integration"
    status: completed
  # Phase 3: Validation & Completion
  - id: p3-refs
    content: "p3-refs: File reference review - verify all internal links resolve"
    taskFile: "phase-3/p3-refs.task.md"
    status: completed
  - id: p3-compound
    content: "p3-compound: Compound learnings - process learnings.md entries into actionable changes"
    status: completed
  - id: p3-checkpoint
    content: "P3 FINAL CHECKPOINT - User approval to complete plan"
    status: completed
isProject: false
---

# Align Skills with Anthropic Spec

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (referenced via `taskFile`) for per-task execution instructions.

## Architectural Constraints

| Principle | Enforcement |
|-----------|-------------|
| Edit `_config/` not `.cursor/` | All skill/rule file changes target `_config/.cursor/`; installer propagates to `.cursor/` |
| Preserve existing skill behavior | Name field change must not alter triggering or activation logic |
| Thin loader convention | Skills remain 20-35 line thin loaders; optional subdirs documented but not enforced |
| Platform knowledge format | Archive follows existing `platform_knowledge/` pattern |
| tools-manifest unchanged | Manifest uses `id` (short form), not YAML `name`; no manifest edits |

**Inviolable Rules:**
1. Read shape.md execution log before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints require quality-review subagent execution before user-facing gate decision — never skip the review
5. Checkpoints require human approval — never auto-continue, even after `APPROVED` verdict
6. `REJECTED` checkpoints cannot advance — address feedback before re-evaluation
7. Append to shape.md after each task — never modify previous entries

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

## Phase 1: Standards & Compliance

**Goal:** Update the skill template, fix name mismatches in all existing skills, and create a dedicated skill-standards rule.

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Three deliverables from Phase 1 of the align-skills-anthropic-spec plan:
> 1. Updated skill template at `workflows/build-rbtv-component/templates/ide-loader-template.md` — added optional Anthropic fields (license, compatibility, metadata, allowed-tools), name==folder rule, optional subdirectories note, three new critical rules
> 2. Updated `name` field in 7 SKILL.md files under `_config/.cursor/skills/bmad-rbtv-*/` to match folder names
> 3. New rule file at `_config/.cursor/rules/bmad-rbtv-skill-standards.mdc`
>
> ## Quality Criteria
> 1. Template skill variants (Agent and Workflow/Task) both include optional fields block with correct YAML syntax
> 2. All 7 SKILL.md files have `name:` matching their parent folder name exactly (e.g., `name: bmad-rbtv-doc` for folder `bmad-rbtv-doc`)
> 3. Rule file has valid MDC frontmatter with correct `globs` targeting `_config/.cursor/skills/**`
> 4. Rule content covers all Anthropic spec requirements: naming, folder structure, required fields, optional fields, security restrictions
> 5. Rule follows atomic files principles (lean, mandatory language, no content repetition)
> 6. No existing skill behavior is broken (activation sections, descriptions unchanged except `name:`)

## Phase 2: Knowledge & Integration

**Goal:** Archive the Anthropic Skills guide as platform knowledge and update the builder agent to reference the new rule.

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Two deliverables from Phase 2 of the align-skills-anthropic-spec plan:
> 1. Platform knowledge document at `workflows/prompting-assistance/data/platform_knowledge/claude_skills.md` and new entry in `workflows/prompting-assistance/data/knowledge-index.csv`
> 2. Updated `agents/fernando.md` — [CI] handler now references `bmad-rbtv-skill-standards.mdc` rule
>
> ## Quality Criteria
> 1. Platform knowledge document follows the format of existing docs (e.g., `claude_projects.md`) — header, sections, tables
> 2. Document captures key Anthropic spec content: YAML fields, folder structure, naming, testing, distribution, patterns, troubleshooting
> 3. knowledge-index.csv entry has correct columns (id, type, name, source_path, tags, description)
> 4. fernando.md change is minimal — only adds rule reference, no structural changes to agent menu or handlers
> 5. No content repetition between the platform knowledge doc and the rule file

## Phase 3: Validation & Completion

**Goal:** Verify references, compound learnings, complete plan.

#### P3 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Full plan deliverables across all phases of align-skills-anthropic-spec:
> - Updated template: `workflows/build-rbtv-component/templates/ide-loader-template.md`
> - 7 updated skills: `_config/.cursor/skills/bmad-rbtv-*/SKILL.md`
> - New rule: `_config/.cursor/rules/bmad-rbtv-skill-standards.mdc`
> - Platform knowledge: `workflows/prompting-assistance/data/platform_knowledge/claude_skills.md`
> - Updated index: `workflows/prompting-assistance/data/knowledge-index.csv`
> - Updated builder: `agents/fernando.md`
> - Companion files: `shape.md`, `learnings.md`
>
> ## Quality Criteria
> 1. All internal markdown links and file references resolve correctly
> 2. Learnings have been compounded into actionable system improvements
> 3. No broken references between deliverables
> 4. All files follow RBTV atomic files principles
