# Use Cases Context for Doc Component PRD

**Purpose:** Reference material from `docs/use_cases/` relevant to designing the unified `/rbtv_doc` command.

---

## 1. Handoff Mode Design Inputs

**Source:** `docs/use_cases/handoff_planning_workflow_adjustments.md`

### Two Handoff Types Identified

| Handoff Type | Purpose | Key Sections |
|--------------|---------|--------------|
| **Plan development** | Continue plan creation/modification | Problem, Goals, Constraints, Decisions, Judge Feedback, Planning Resources |
| **Execution** | Execute tasks from approved plan | Problem, Goals, Constraints, Decisions, Files to Load, Task Instructions |

### Plan Development Handoff Structure

Required sections for plan development continuation:

1. **Problem Being Solved** — Issues in current plan
2. **User Goals** — What user wants next agent to accomplish
3. **Constraints Gathered** — Technical, process, project constraints
4. **Decisions Already Made** — With rationale and alternatives (prevent re-deciding)
5. **Information Gaps Remaining** — Unclear or needs resolution
6. **Judge Feedback Summary** — Status, issues, requirement coverage
7. **Files to Load** — Planning resources (SKILL.md, guardrails, spec)
8. **Next Steps** — Guidelines for plan fixes

**Key difference from execution handoff:** Plan development handoffs include Judge Feedback prominently; execution handoffs focus on task dependencies and code files.

### Five Workflow Gaps to Address

| Gap | Description | Implication for /rbtv_doc |
|-----|-------------|----------------------|
| No plan development handoff pattern | Handoffs assume execution, not plan iteration | Handoff mode should support both types |
| Judge feedback integration unclear | No standard for capturing/communicating judge feedback | Include optional judge feedback section |
| User requirements vs judge requirements | No priority hierarchy documented | Handoff should capture requirement sources |
| Plan iteration cycle not formalized | No "create → review → fix → resubmit" workflow | Consider iteration context in handoff |
| Handoff file location not standardized | Inconsistent placement | Define location rules in handoff mode |

### Handoff File Location Standards

| Handoff Type | Location | Naming |
|--------------|----------|--------|
| Plan development | `.cursor/plans/[plan-name]/` | `[plan-name]-handoff.md` |
| Task execution | `.cursor/plans/[plan-name]/` | `[plan-name]-handoff.md` |
| Project handoff | Project root or `docs/` | `handoff.md` or `[project]-handoff.md` |

---

## 2. Execution Handoff Structure

**Source:** `docs/use_cases/domcobb_to_execution_pipeline.md`

### Current Handoff Sections (8 sections)

1. **Context Summary** — Problem background and current state
2. **Problem Being Solved** — Clear statement of what's wrong
3. **User Goals** — What the user wants to achieve
4. **Constraints Gathered** — Scope, principles, violations to detect
5. **Decisions Already Made** — Rule location, mandatory language, exclusions
6. **Files to Load** — Required files with MUST READ FIRST priority
7. **Information Gaps** — None - all context provided (or list gaps)
8. **For the Agent Reading This Handoff** — Step-by-step instructions

### Handoff Value Proposition

- Fresh agent can start immediately without reading full conversation
- All critical decisions preserved with rationale
- Clear instructions for execution
- Files to load identified upfront

---

## 3. Tool Gaps Pattern

**Source:** `docs/use_cases/km_pipeline_planning.md` Section 1.1

### Tool Gaps Table Structure

Documents where robotville tools didn't work automatically or required manual intervention:

| Session | Gap Type | Description | Tool/Behavior Expected | What User Did Instead | Improvement Suggestion |

### Relevant Gap Examples for Doc Component

| Gap Type | Description | Implication |
|----------|-------------|-------------|
| Manual invocation | Mentor agent not auto-invoked for strategic planning | Doc modes could suggest appropriate next steps |
| Missing auto-detection | Plan-creation guardrails not triggered | Doc component could detect when handoff/doc is needed |
| Workflow gap | Informal planning session vs formal workflow | Mode transitions could be smoother |

---

## 4. Learnings Mode Inputs

**Source:** `docs/use_cases/km_pipeline_planning.md` Section 7 (Key Decisions Log)

### Decision Capture Pattern

| Date | Decision | Rationale | Made By |
|------|----------|-----------|---------|

### Decision Types Observed

- Architecture changes (label structure, theme presets)
- Implementation decisions (file naming, function signatures)
- Process decisions (checkpoint rules, execution decisions scope)
- Quality decisions (judge requirements, metadata packaging)

**Implication for learnings mode:** Template should capture decision type, rationale, and source (user, agent, judge).

---

## 5. Product Documentation Patterns

**Source:** `docs/use_cases/km_pipeline_planning.md` Sections 4, 6

### Architecture Documentation Sections

From spec.md created during km-pipeline-v2:

1. Document Classification (static vs dynamic)
2. Tag System (behavior per tag type)
3. Folder Structure (hierarchy diagram)
4. Build Order (dependency graph)
5. MVP Scope (in scope vs out of scope table)
6. Architectural Changes (change log with before/after)

### Current State Tracking

| Aspect | Status |
|--------|--------|
| Architecture | ✅ Defined |
| Implementation | 🔄 In progress |
| Testing | ⏳ Not started |

**Implication for product mode:** Template could include status tracking and change log sections.

---

## 6. Use Case Documentation Pattern

**Source:** All three use case files

### Common Structure

1. **Overview** — Purpose, functions showcased, complexity, success metrics
2. **The Problem** — Initial state, root cause, user goal, challenge
3. **Workflow/Sessions** — Step-by-step documentation with timestamps
4. **Key Decisions** — Decision log table
5. **Lessons for System Improvement** — What worked, what could improve
6. **References** — Files created, files referenced, components used

**Implication:** Could inform a "usecase" mode template structure.

---

## 7. Cross-Cutting Insights

### Mode Detection Phrases

From tool gaps analysis, these phrases could trigger mode suggestions:

| Phrase Pattern | Suggested Mode |
|----------------|----------------|
| "for the agent that will execute" | handoff (execution) |
| "for an agent that will continue developing" | handoff (plan development) |
| "document what we learned" | learnings |
| "create documentation for" | product |
| "capture this use case" | usecase |

### Files to Load Pattern

All handoffs should specify:

| Document | Purpose | Priority |
|----------|---------|----------|
| [file] | [why needed] | MUST READ FIRST / Reference |

---

## References

| File | Key Sections Used |
|------|-------------------|
| `docs/use_cases/handoff_planning_workflow_adjustments.md` | Sections 4-5 (Gaps, Handoff Structure) |
| `docs/use_cases/domcobb_to_execution_pipeline.md` | Section 4 (Stage 5: Handoff) |
| `docs/use_cases/km_pipeline_planning.md` | Sections 1.1, 4, 6, 7, 8 |
