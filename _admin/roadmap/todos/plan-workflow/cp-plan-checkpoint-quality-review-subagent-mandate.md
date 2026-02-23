---
title: 'Compound: Mandatory Quality-Review Subagent at Plan Checkpoints'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - '.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md'
  - '_bmad/rbtv/tasks/quality-review.xml'
  - '_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md'
outputPath: '_bmad/rbtv/_admin/roadmap/todos'
date: '2026-02-13'
yoloMode: false
---

# Mandatory Quality-Review Subagent at Plan Checkpoints

**Type:** Workflow  
**Priority:** High  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

Plan checkpoints currently require a human approval halt, but checkpoint task content does not consistently require execution through the `quality-review` subagent before presenting a gate decision. This allows uneven checkpoint rigor and increases the chance of subjective pass-through without a standardized five-criteria evaluation.

### Goals

- Require every plan checkpoint to run the `quality-review` subagent.
- Standardize checkpoint output as an explicit gate verdict (`APPROVED` or `REJECTED`).
- Block checkpoint completion when quality verdict is `REJECTED`.
- Keep the existing human-approval checkpoint halt behavior intact.

### Constraints

- Must preserve current checkpoint model (pause point, no micro-step files).
- Must use explicit invocation syntax (`subagent_type='quality-review'`), not ambiguous wording.
- Must remain compatible with current plan-lifecycle rules and templates.

---

## Self-Assessment

### Error Analysis

**Error type:** Process gap in checkpoint enforcement.

Current rules include general checkpoint halt behavior and explicit agent invocation guidance, but they do not mandate quality-review execution for every checkpoint. The gap is not tooling capability; it is missing mandatory rule text at checkpoint specification level.

### Context Source Evaluation

| File | Issue |
|------|-------|
| `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` | Has checkpoint halt requirement, but no universal rule requiring quality-review subagent execution at checkpoints. |
| `_bmad/rbtv/tasks/quality-review.xml` | Defines a strict gate evaluator and verdict format, but not yet mandated as checkpoint execution default. |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md` | Includes checkpoint entries but does not encode standardized quality-review invocation in checkpoint content. |

### Improvement Options

1. **Rule Update (SELECTED)**: Add a mandatory checkpoint rule requiring `quality-review` subagent execution before user-facing gate decision.
   - **Rationale:** Smallest high-impact change; updates source-of-truth behavior for all future plans.
   - **Location:** `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md`

2. **Template Hardening**: Add fixed checkpoint content snippet in plan templates with explicit quality-review invocation.
   - **Rationale:** Improves default generation quality.
   - **Location:** Plan template and checkpoint content guidance files

3. **Workflow Guard**: Add validation step that rejects checkpoint tasks missing quality-review instructions.
   - **Rationale:** Strong enforcement, but increases workflow complexity.
   - **Location:** Plan-lifecycle validation steps

4. **Post-Generation Lint Rule**: Add checker that scans plan checkpoint content for required invocation string.
   - **Rationale:** Automated detection; separate from generation.
   - **Location:** Rule/validator tooling

5. **Human-Only Policy**: Keep current process and rely on human reviewers to request quality review ad hoc.
   - **Rationale:** No implementation work, but inconsistent and weak.
   - **Location:** N/A

---

## Proposed Solution

Select Option 1 with optional future extension from Option 2.

### Required behavior change

Every checkpoint task definition must include mandatory execution language equivalent to:

- "Use Task tool with `subagent_type='quality-review'` to evaluate checkpoint deliverables."
- "Present the `APPROVED`/`REJECTED` verdict to user."
- "If `REJECTED`, do not advance to the next phase."
- "Halt for human approval regardless of verdict."

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` (required), optional follow-up in plan template/checkpoint examples |
| Scope of change | Add explicit mandatory bullet(s) under Checkpoint Rules and checkpoint task content guidance |
| Related files | `_bmad/rbtv/tasks/quality-review.xml`, any plan template or generation workflow file that emits checkpoint task text |

---

## Rationale

Checkpoint quality gates are already conceptually present; this change makes them operationally enforceable and consistent. By requiring the same evaluator (`quality-review`) at every checkpoint, decisions become reproducible, feedback is complete in one pass, and advancement criteria become transparent.

---

## Acceptance Criteria

- [ ] Checkpoint Rules explicitly mandate `quality-review` subagent execution for every checkpoint.
- [ ] Rule text uses explicit invocation syntax: `use Task tool with subagent_type='quality-review'`.
- [ ] Checkpoint task content standard includes required verdict handling (`APPROVED`/`REJECTED`).
- [ ] Rules state that `REJECTED` checkpoints cannot advance phase status.
- [ ] Rules retain human-approval halt semantics after evaluation.
- [ ] At least one checkpoint example in plan-lifecycle docs reflects the new mandatory quality-review instruction.

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` | Primary enforcement file |
| `_bmad/rbtv/tasks/quality-review.xml` | Required evaluator protocol and verdict logic |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md` | Example plan where checkpoint rigor requirement surfaced |

---

## References

- Checkpoint behavior baseline in plan-lifecycle rules (`Checkpoint Rules` section)
- Explicit subagent invocation conventions in `Agent Invocation in Tasks`
- Quality gate protocol in `_bmad/rbtv/tasks/quality-review.xml`

---

## Discussion Notes

- User intent: "all plan checkpoints must include quality review as sub agent to execute the task."
- Storage constraint: save compound output under `_bmad/rbtv/_admin/roadmap/todos/`.
