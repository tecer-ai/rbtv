---
title: 'Compound: Context Preservation in Interactive Sessions'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - projects/ai-101/structured-problem-2026-03-14.md
  - projects/ai-101/project-context.md
outputPath: '_admin/roadmap/todos'
date: '2026-03-14'
yoloMode: false
---

# Context Preservation in Interactive Sessions

**Type:** Rule
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Interactive multi-turn sessions produce rich conversational context — decisions with rationale, domain knowledge, entity relationships, corrections with background, structured data. This context is lost when sessions end.

Two distinct failure modes:

**Failure 1: No capture mechanism.** Workflows produce a single structured output. All conversational context is lost. The user must explicitly request a companion context file.

*Triggering incident:* Dom Cobb problem structuring for AI-101 essay. Workflow produced `structured-problem.md`. Henri had to explicitly ask for `project-context.md` to capture: audio transcript content, credibility timeline, metaphor examples, Syngenta stakeholder details, strategic reasoning, and 14 open challenges.

**Failure 2: Capture exists but wrong destination/format.** Even if context is captured (e.g., in a shape.md), it may belong to an external system with its own conventions. A generic shape file becomes an intermediate artifact requiring manual translation.

*Triggering incident:* Trello → Second Brain organization session. 6+ turns of rich context: people and relationships, financial structures with payment logic, career situation, ongoing legal and financial processes. Henri had to explicitly say "garanta que o contexto dessa conversa não será perdido" and instruct the agent to read the Second Brain's CLAUDE.md. The context needed to go to 7+ different files across PARA structure, memory files, and CLAUDE.md — each with its own format and conventions — not a single generic shape.md.

### Goals

- Rich conversational context is always preserved — never lost when sessions end
- Context is captured in the most appropriate mechanism for the destination system
- When the destination has its own conventions, use those conventions
- When no destination conventions exist, fall back to shape.md
- The agent detects when preservation is needed and confirms the approach with the user
- Minimal overhead — no trigger for low-context sessions

### Constraints

- Must work across any interactive session, not limited to RBTV workflows
- Must not break existing workflow output patterns
- Must respect external system conventions when writing to external systems
- Detection must be reliable without being rigid
- Must follow existing RBTV/BMAD conventions
- Must not add overhead to simple, low-context sessions

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap — systemic

**Failure 1 analysis:** The system has no mechanism for preserving conversational context as an artifact alongside workflow outputs. The `doc-context-handoff` workflow exists but requires explicit user invocation. Only `plan-lifecycle` produces companion context files (`shape.md`, `learnings.md`). All other workflows — 35+ of them — produce single outputs with no companion context.

**Failure 2 analysis:** Even with shape capture, the system has no concept of destination awareness. Shape.md is written in a generic format regardless of whether the context belongs to an external system with its own conventions. The agent doesn't discover target system conventions before writing. In the Second Brain incident, the agent needed to write to: `.claude/memory/general.md` (memory format), `2. Areas/pessoal/README.md` (MoSCoW + Obsidian Tasks format), `2. Areas/financeiro/pagamentos-recorrentes.md` (structured tables), and 4+ other files — each with different conventions.

### Context Source Evaluation

| File | Influence | Gap |
|------|-----------|-----|
| `core/tasks/workflow.xml` | Universal workflow engine — `default_output_file`, `template-output` | Single-output only. No companion file concept |
| `doc-context-handoff/workflow.md` | Context transfer — extracts decisions, constraints | On-demand only. User must invoke. Produces single summary, not multi-destination routing |
| `plan-lifecycle/` | Produces `shape.md` + `learnings.md` | Pattern exists but isn't replicated to other workflows. No destination awareness |
| `bmad-rbtv-chat-discipline.mdc` | "Full detail belongs in output files" | Doesn't specify which output files or how to determine the right destination |
| `projects/second-brain/CLAUDE.md` | Defines Second Brain conventions (PARA, memory, Obsidian Tasks) | Agent has no rule requiring it to discover and follow target system conventions |

### Improvement Options

1. **New Rule: Shape Capture Rule (original proposal)**
   - Create rule requiring interactive workflows to produce companion `{output-name}-shape.md`. Agent writes continuously, not at completion.
   - **Rationale:** Reuses proven plan-lifecycle pattern. Continuous capture prevents loss.
   - **Location:** New rule file `bmad-rbtv-shape-capture.mdc`
   - **Pattern Consistency:** Extends existing shape.md pattern. Does NOT address destination routing — always produces generic shape.md regardless of target system.

2. **Modify Existing Rule: Extend Chat Discipline**
   - Add sub-rule: conversational context not captured by output template must be preserved in companion file.
   - **Rationale:** Minimal change. Intent already exists in "full detail belongs in output files."
   - **Location:** `bmad-rbtv-chat-discipline.mdc` — new row in content type table
   - **Pattern Consistency:** Extends existing rule. Still relies on agent compliance. No destination awareness.

3. **Update System File: Add context capture to workflow final steps**
   - Modify each interactive workflow's final step to include mandatory context capture.
   - **Rationale:** Structural enforcement per workflow.
   - **Location:** Final step of each interactive workflow
   - **Pattern Consistency:** Follows micro-step pattern. Requires modifying multiple files. Completion-dependent — unreliable because Henri rarely completes workflows.

4. **Add Constraint: Mandatory context section in output templates**
   - Add `## Session Context` section to every output template.
   - **Rationale:** Single self-contained artifact.
   - **Location:** Every workflow output template
   - **Pattern Consistency:** Follows atomic files principle. Makes outputs much longer and mixes conclusions with raw context.

5. ~~**Auto-trigger handoff at workflow completion**~~ — ELIMINATED
   - **Reason:** Henri rarely marks workflows as completed. Any completion-triggered mechanism is unreliable.

6. **Context Preservation Rule — Detect, Discover, Confirm, Capture (SELECTED)**
   - Standalone rule mandating that conversational context must always be preserved. Agent detects accumulating context using explicit signals, discovers the target system's conventions, proposes a capture mechanism to the user, confirms, and captures continuously. Shape.md is the universal fallback when no target-system conventions exist.
   - **Rationale:** Addresses both failure modes. Destination-aware. User confirms approach. Works regardless of workflow completion.
   - **Location:** New rule at `_config/.cursor/rules/bmad-rbtv-context-preservation.mdc`
   - **Pattern Consistency:** Extends and subsumes the shape.md pattern. Borrows "write immediately" from Memory System. Generalizes plan-lifecycle's shape pattern to any interactive session.

---

## Proposed Solution

**Selected: Option 6 — Context Preservation Rule (Detect, Discover, Confirm, Capture)**

### Design

A standalone rule with four sequential behaviors.

#### 1. Detect — Context Accumulation Signals

The rule activates when the agent detects **2+ of these signals** across multiple turns:

| Signal | Description |
|--------|-------------|
| **Decision with rationale** | User explains WHY they chose something, not just WHAT |
| **Correction with background** | User corrects the agent and provides context that wasn't available before |
| **Undocumented knowledge** | User provides information not present in any loaded file |
| **Structured data** | User provides lists, hierarchies, schedules, mappings, or tabular information |
| **Entity relationships** | User describes how people, systems, concepts, or components relate to each other |
| **Undocumented constraints** | User reveals rules, conventions, or limitations not written anywhere |
| **Process descriptions** | User explains workflows, routines, sequences, or operational procedures |
| **Historical context** | User provides past events, decisions, or circumstances that inform the current session |

The rule does NOT trigger for:
- Single-turn tasks (one prompt, one output)
- Simple file edits or quick questions
- Sessions where the user provides only task instructions without context beyond the task

#### 2. Discover — Target System Conventions

When the rule triggers, before writing any context:

1. **Identify the target system** — Where will the session's outputs land? Options: current project, external project, or no specific project.
2. **Read conventions** — If the target has a CLAUDE.md, memory system, documentation standards, or other context preservation conventions → read and understand them.
3. **Map context to destinations** — Determine which pieces of accumulated context go where, and in what format.

If no target-system conventions exist → default to shape.md using the universal shape template.

#### 3. Confirm — Propose to User

The agent tells the user how it will preserve context and asks for confirmation. The proposal must be specific enough for the user to evaluate — not a generic "I'll save context."

The user can approve, redirect to a different mechanism, or decline.

#### 4. Capture — Continuous, Destination-Aware

After confirmation:

- Write to the confirmed destination(s) continuously — same turn as context is provided
- Follow the target system's format and conventions
- If using shape.md, follow the universal shape template and living document principle
- Never defer writes to session end

### Shape.md as Universal Fallback

When no target-system conventions exist, shape.md is the default capture mechanism. The file is created alongside the primary output as `{output-name}-shape.md`.

| Section | Content | When Updated |
|---------|---------|-------------|
| **Scope Definition** | What this session accomplishes, what it excludes | At start, refined during |
| **Key Decisions** | Decision / Choice / Rationale (table) | After each decision |
| **Constraints** | Constraint / Source / Impact (table) | As identified |
| **User Inputs** | Input Topic / User's Input / Developed Into (table) | After each substantive input |
| **Collaborative Decisions** | Decision / User Position / AI Contribution / Resolution (table) | After each collaborative exchange |
| **Standards Applied** | *(Conditional — plan workflows only)* | During planning |
| **Decisions & Discoveries** | Date / Source / Finding / Impact (append-only) | Continuously |
| **References** | Source Documents Analyzed / Files to Load (tables) | As referenced |

### Living Document Principle — CRITICAL

Whether writing to shape.md or to target-system files, context preservation is a LIVING process.

| Behavior | Required |
|----------|----------|
| First write | When rule triggers and user confirms |
| Update after new context provided | ALWAYS — same turn, not deferred |
| Update after a decision | ALWAYS |
| Update after a correction or nuance | ALWAYS |
| Update after a direction change | ALWAYS |
| Defer writes to session end | NEVER |
| Write once and forget | NEVER |

### How This Affects Plan-Lifecycle

Plan-lifecycle already creates shape.md. This rule strengthens it but introduces three conflicts:

**Conflict 1: Creation timing**
- Current: Plan-lifecycle creates shape.md at step 4, populating from step 2 context.
- New: Create on first substantive interaction.
- Resolution: Step 4 checks if shape.md exists. If yes, MERGE. If no, create from template.

**Conflict 2: Template ownership**
- Current: Plan-specific template with plan-only sections.
- New: Universal template with conditional sections.
- Resolution: Single universal template in shared location. Plan-specific sections marked conditional on `workflowType`. Plan-lifecycle references the shared template.

**Conflict 3: Update authority**
- Current: Plan's Revolving Plan Rules say "document discoveries in shape.md."
- New: This rule is the authority on shape.md writes.
- Resolution: Plan rules reference this rule instead of containing independent shape.md instructions.

**Implementation changes to plan-lifecycle:**

| File | Change |
|------|--------|
| `plan-lifecycle/templates/shape-template.md` | Replace with reference to universal template OR move to shared location |
| `plan-lifecycle/steps-c/step-04-generate-artifacts.md` | Add check: if shape.md exists, merge; if not, create from template |
| `plan-lifecycle/data/plan-creation-rules.md` | Replace shape.md update instructions with reference to context preservation rule |
| `plan-lifecycle/workflow.md` | Update `shapeTemplateFile` path to shared template location |

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to create | `_config/.cursor/rules/bmad-rbtv-context-preservation.mdc` (new rule) |
| File(s) to modify | `plan-lifecycle/templates/shape-template.md` (generalize), `plan-lifecycle/steps-c/step-04-generate-artifacts.md` (merge logic), `plan-lifecycle/data/plan-creation-rules.md` (reference rule) |
| Shared template location | `_shared/templates/shape-template.md` (universal shape template) |
| Scope of change | New rule + template generalization + plan-lifecycle integration |

---

## Rationale

1. **Addresses both failure modes** — Captures context (failure 1) AND routes it correctly (failure 2).
2. **Detection signals are explicit** — Concrete signal table provides reliable triggers without relying on agent heuristics.
3. **Destination discovery** — Agent reads target system conventions before writing, preventing format mismatches.
4. **User confirmation** — Keeps the user in control of how their context is preserved.
5. **Shape.md as fallback** — Universal safety net when no target conventions exist.
6. **Continuous, not completion-triggered** — Works even for abandoned sessions.
7. **Standalone rule** — Agents read it every session; not buried in another rule.
8. **Borrows from Memory System** — "Write immediately when you learn something" applied to session context.

---

## Relationship to RBTV Memory System

**PRD:** `_admin/roadmap/todos/_claude-code-workspace/agent-architecture/prd-rbtv-memory-system.md`

| Dimension | Memory System | Context Preservation (this) |
|-----------|--------------|-------------------------------|
| **Purpose** | Agent self-improvement — reusable knowledge across sessions | Session continuity — specific context between agents/systems |
| **Scope** | Cross-session, cross-project | Project/system-specific, session-specific |
| **Content** | Short entries: "date, what, why" | Rich narrative: inputs, decisions, reasoning, nuances |
| **Location** | `.claude/memory/` | Target system's files OR shape.md fallback |
| **Persistence** | Permanent until reorganized | Lives with the project/system output |

Both follow the "write immediately" principle. Both are file-based. They do not compete — an agent uses BOTH: write reusable learnings to memory, write session context to the appropriate destination.

---

## Acceptance Criteria

- [ ] New rule file created at `_config/.cursor/rules/bmad-rbtv-context-preservation.mdc`
- [ ] Rule defines 8 explicit context accumulation signals as trigger criteria (2+ signals = activate)
- [ ] Rule specifies the Detect → Discover → Confirm → Capture sequence
- [ ] Rule requires agent to read target system conventions before proposing capture mechanism
- [ ] Rule requires user confirmation before starting capture
- [ ] Rule specifies shape.md as universal fallback when no target conventions exist
- [ ] Rule states living document principle — continuous writes, never deferred
- [ ] Universal shape template exists (generalized from plan-lifecycle template) with conditional plan-specific sections
- [ ] Plan-lifecycle step 4 checks for existing shape.md and MERGES instead of overwriting
- [ ] Plan-lifecycle Revolving Plan Rules reference this rule for shape.md writes
- [ ] Rule does NOT trigger for low-context sessions (single-turn, simple edits)
- [ ] Rule explicitly states relationship to Memory System (complementary, not overlapping)
- [ ] Rule is standalone — not embedded in another rule file

---

## Related Files

| File | Relationship |
|------|--------------|
| `prd-rbtv-memory-system.md` | Complementary system — Memory is agent-level knowledge, Context Preservation is session-level context |
| `plan-lifecycle/templates/shape-template.md` | Existing shape template — to be generalized for universal use |
| `plan-lifecycle/` | Existing workflow using shape.md — strengthened by this rule |
| `doc-context-handoff/workflow.md` | On-demand context transfer — context preservation reduces need for explicit handoff invocation |
| `core/tasks/workflow.xml` | Core workflow engine — no modification needed (rule-based, not engine-based) |
| `bmad-rbtv-chat-discipline.mdc` | "Full detail belongs in output files" — context preservation enforces this intent |

---

## References

- Triggering incident 1: Dom Cobb problem structuring for AI-101 essay project (2026-03-14)
- Triggering incident 2: Trello → Second Brain organization session (2026-03-14)
- Output from incident 1: `projects/ai-101/structured-problem-2026-03-14.md`, `projects/ai-101/project-context.md`
- Output from incident 2: Multiple Second Brain files across PARA structure, memory, CLAUDE.md
- Related PRD: `prd-rbtv-memory-system.md`

---

## Quality Review Observations

Review date: 2026-03-14. Status: APPROVED. All 5 criteria passed.

Non-blocking observations to address during implementation:

1. **`inputDocuments` incomplete** — Frontmatter lists only incident 1 inputs. Incident 2 inputs (Trello → Second Brain session) not listed. Add representative paths from incident 2.

2. **`outputPath` stale** — Frontmatter says `_admin/roadmap/todos` but file lives at `_claude-code-workspace/context-preservation/`. Caused by post-creation reorganization. Update frontmatter to match.

3. **6 options vs. template's "exactly 5"** — Option 6 was synthesized through user-directed discussion as evolution of the original 5. Documenting the full decision trail is more valuable than strict template conformance.

4. **Edge case: freeform session naming** — Shape.md fallback uses `{output-name}-shape.md`. Freeform sessions have no output name. Rule must specify a naming convention for this case (e.g., `{date}-{topic}-shape.md`).

5. **Edge case: single-turn rich context** — Trigger says "2+ signals across multiple turns." A single turn with massive context dump could contain 4+ signals. Change to "2+ signals across one or more turns" to avoid missing single-turn-but-rich scenarios.

---

## Discussion Notes

**Original discussion (incident 1 — 2026-03-14):**
- Selected Option 6: Continuous context capture using shape pattern
- Naming convention: `{output-name}-shape.md`
- Implementation: New standalone rule
- Template: Reuse/generalize plan-lifecycle shape template
- Must apply to plan-lifecycle too, strengthening the existing pattern
- Eliminated Option 5: Henri rarely completes workflows, so completion triggers are unreliable
- Relationship to Memory System: complementary — memory is agent-level, shape is project-level

**Extension discussion (incident 2 — 2026-03-14):**
- Shape capture alone insufficient — context needed routing to Second Brain in its native format (PARA, memory files, Obsidian Tasks format), not a generic shape.md
- User principle: "context must always be captured and preserved" — shape.md is ONE mechanism, not THE mechanism
- Shape.md becomes universal fallback, not universal destination
- Rule must discover target system conventions before proposing capture mechanism
- Rule must confirm capture approach with user
- Trigger detection: explicit signals (domain-agnostic table) — not left to agent heuristics
- Signals must be broadly applicable to any domain — not biased toward personal context
- Rule renamed from `bmad-rbtv-shape-capture` to `bmad-rbtv-context-preservation`
