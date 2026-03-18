---
title: 'PRD: No Content Duplication Within Milestones'
docType: 'prd'
mode: 'create'
priority: 'High'
tracker: ''
date: '2026-03-11'
---

# No Content Duplication Within Milestones

**Type:** Workflow Rule
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Within a single milestone, frameworks overlap conceptually. When the agent generates a framework's output, it rewrites concepts already defined in a previously completed framework instead of referencing or evolving them. The result: the same idea — customer problem, assumption, segment definition, value proposition — appears in multiple framework files with slightly different wording, creating redundancy, inconsistency risk, and wasted token output.

**Example (M1: Conception):**
- Working Backwards defines the target customer and their core problem.
- Jobs-to-be-Done rewrites the customer definition and restates the problem using JTBD vocabulary instead of building on WB's definition.
- Problem-Solution Fit restates both the customer and the problem a third time.
- Lean Canvas does it a fourth time in its Customer Segments and Problem boxes.

Each framework adds legitimate new analytical dimensions (jobs, pains/gains, solution mapping, unit economics), but the shared underlying concepts — who the customer is, what the problem is — get duplicated 3-4 times per milestone. Every line in a framework file must add or evolve a concept, never rewrite one already defined.

### Goals

1. Establish a **single-definition rule**: within a milestone, each concept lives in one place only — the framework that first defines it
2. Later frameworks MUST reference prior definitions and build on them (add new dimensions, challenge, refine) — never restate
3. The project-memo serves as the cumulative synthesis layer; individual frameworks do NOT replicate what the memo already contains
4. Reduce total output volume per milestone by eliminating redundant content

### Constraints

- Must not reduce the analytical depth of any framework — the goal is eliminating repetition, not removing analysis
- Must work within the existing sequential framework execution model (frameworks are completed one at a time)
- Must be enforceable via template and step-file instructions (no runtime validation tooling)
- Must not break the atomic file principle — each framework file must still be interpretable independently (references to prior frameworks must be explicit and traceable)

---

## Proposed Solution

### 1. Framework Content Ownership Rule

Define which concepts each framework within a milestone owns (first-defines) vs. inherits (references from prior frameworks). This is not a rigid schema — it is a guiding principle embedded in the framework templates and synthesis steps.

**Rule statement (to embed in milestone workflow data or step files):**

> Within a milestone, every concept MUST have exactly one owning framework — the first framework in the milestone sequence that defines it. Later frameworks MUST reference the owning framework's definition by file path and section. They may extend, challenge, or refine the concept with new analytical dimensions, but they MUST NOT restate the original definition.

### 2. Template-Level Enforcement

Each framework template must include a `## Prior Context` section at the top (after overview) that:
- Lists which previously completed frameworks in the current milestone are relevant
- States which concepts from those frameworks this framework builds on (by reference, not by restating)
- Explicitly names what **new** analytical dimension this framework adds

**Template addition (applies to all framework templates):**

```markdown
## Prior Context

**Builds on:** [List of prior frameworks in this milestone already completed]
**Inherits (do not restate):** [Concepts defined in prior frameworks — reference by framework name and section]
**This framework adds:** [Net-new analytical dimensions this framework contributes]
```

### 3. Synthesis Step Instruction

Each framework's synthesis/completion step must include a deduplication check:

> Before writing the framework output, review all completed framework files in the current milestone folder. For any concept already defined in a prior framework, reference it — do not restate it. If this framework's analysis refines or challenges a prior definition, state only the delta (what changed and why).

### 4. Project-Memo as Synthesis Layer

The project-memo already serves as cumulative synthesis. Reinforce that individual framework files are analytical contributions, not standalone summaries. Framework files must assume the reader has access to the project-memo and prior frameworks.

---

## Rationale

Duplication is the default behavior because each framework's template and methodology is designed to be self-contained in academic/consulting contexts. In the BI workflow, frameworks execute sequentially within a milestone — each has full access to prior frameworks' outputs. Self-containment is unnecessary and counterproductive: it wastes tokens, creates drift risk when the same concept has 3-4 slightly different phrasings, and makes the project-memo synthesis harder (which version of the customer definition is canonical?).

The fix is structural (template changes + synthesis step instructions), not procedural. Agents follow templates — if the template says "reference, don't restate," the agent will comply.

---

## Acceptance Criteria

- [ ] A content ownership rule is defined and embedded in milestone workflow data or step files
- [ ] Framework templates include a `## Prior Context` section that mandates reference over restatement
- [ ] Each framework's synthesis step includes a deduplication instruction
- [ ] Within a milestone, no concept (customer definition, problem statement, assumption, segment) appears in full in more than one framework file — later frameworks reference the original and state only their delta
- [ ] Framework files remain independently interpretable (references are explicit, not implicit)
- [ ] No reduction in analytical depth — each framework still contributes its unique dimensions

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/bi-business-innovation/data/founder-process.md` | Master milestone/framework navigation — defines framework sequence per milestone |
| `workflows/bi-business-innovation/templates/project-memo.md` | Synthesis layer — cumulative project state |
| `workflows/bi-m1-*/templates/*.md` | M1 framework templates — first targets for template changes |
| `workflows/bi-m2-*/templates/*.md` | M2 framework templates — second wave |
| Each milestone's step files | Synthesis steps that need deduplication instruction |
| `cp-workflow-bi-cross-framework-consistency-gate.md` | Related — the consistency gate addresses drift detection; this PRD prevents drift at the source |
| `cp-workflow-bi-default-structures.md` | Related — canonical assumption inventory is one instance of this rule applied to assumptions specifically |

---

## Discussion Notes

- The canonical assumption inventory from `cp-workflow-bi-default-structures.md` is a specific instance of this broader rule — it consolidates assumptions into one place. This PRD generalizes the principle to all concepts, not just assumptions.
- The `## Prior Context` section in templates balances atomicity (file is interpretable alone) with non-duplication (references instead of restates). The reader knows where to look without the content being copied.
- Implementation priority: start with M1 (6 frameworks, highest overlap) and validate the pattern before rolling to M2-M6.
