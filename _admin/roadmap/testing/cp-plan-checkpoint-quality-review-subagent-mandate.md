---
title: 'Compound: Mandatory Quality-Review Subagent at Plan Checkpoints'
docType: 'compound'
mode: 'update'
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

Additionally, even when checkpoint tasks reference quality-review, the executing agent must improvise the review prompt — deciding what to evaluate and which criteria to apply. The plan generator has full context of the phase's tasks, deliverables, and acceptance criteria at creation time, but none of that is pre-composed into the checkpoint task YAML. This forces the executor to reconstruct context that was already available during planning.

### Goals

- Require every plan checkpoint to run the `quality-review` subagent.
- Standardize checkpoint output as an explicit gate verdict (`APPROVED` or `REJECTED`).
- Block checkpoint completion when quality verdict is `REJECTED`.
- Keep the existing human-approval checkpoint halt behavior intact.
- Plan generator must pre-compose the quality-review prompt at plan creation time, embedding it in the plan body markdown (not YAML — Cursor strips custom YAML fields) so the executor can fire it without improvisation.

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

### Pre-composed review prompt in plan body

The plan generator must compose the review prompt at plan creation time and embed it in the **plan body markdown** — not in YAML fields.

**Why body, not YAML:** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom fields (like `reviewAgent`, `reviewPrompt`) are silently stripped when the executor updates task status. This was discovered when the first plan using the YAML approach had all review prompts erased on the first checkpoint status change.

**Checkpoint YAML entry** (only standard fields):

```yaml
- id: p1-checkpoint
  content: "P1 CHECKPOINT - Review merged pitch workflow structure before proceeding"
  status: pending
```

**Checkpoint review prompt in plan body** (under the phase section):

```markdown
#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Description of deliverables to review, derived from the phase's completed tasks}
>
> ## Quality Criteria
> 1. {Criterion derived from phase task acceptance criteria}
> 2. {Criterion derived from phase task acceptance criteria}
> ...
```

**Generation rules for review prompts:**

1. **Work to Evaluate** — summarize what the phase produced (files created/modified, artifacts delivered), referencing specific paths
2. **Quality Criteria** — derive 3-7 criteria from the phase's task descriptions, architectural constraints, and any explicit acceptance criteria
3. The prompt must be self-contained — the quality-review agent runs in a fresh context and cannot see the plan's prior execution history

**Executor behavior at checkpoints:**

1. Locate the checkpoint's review prompt in the phase body section (heading format: `#### P{N} Checkpoint Review Prompt`)
2. Fire Task tool with `subagent_type='quality-review'`, passing the blockquoted prompt content
3. Present verdict to user
4. HALT for human approval regardless of verdict
5. If `REJECTED`, do not advance

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` (checkpoint rules + YAML schema), plan template (checkpoint content guidance), plan-lifecycle step that generates checkpoint tasks |
| Scope of change | Add checkpoint YAML schema extension (`reviewAgent`, `reviewPrompt`), add generation rules for reviewPrompt composition, update executor instructions for structured checkpoint handling |
| Related files | `_bmad/rbtv/tasks/quality-review.xml`, any plan template or generation workflow file that emits checkpoint task text |

---

## Rationale

Checkpoint quality gates are already conceptually present; this change makes them operationally enforceable and consistent. By requiring the same evaluator (`quality-review`) at every checkpoint, decisions become reproducible, feedback is complete in one pass, and advancement criteria become transparent.

Pre-composing the review prompt at plan creation time closes a second gap: the plan generator has full knowledge of phase deliverables and acceptance criteria, but currently discards that context. The executor then has to reconstruct it from scratch in a potentially saturated context window. Embedding the prompt in the plan body makes checkpoint execution mechanical — find heading, read blockquote, fire tool, present verdict — with no room for the executor to under-specify or skip criteria.

**Critical constraint (discovered 2026-03-09):** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom YAML fields are silently stripped when task status changes. Review prompts MUST be placed in plan body markdown, not YAML.

---

## Acceptance Criteria

- [ ] Checkpoint Rules explicitly mandate `quality-review` subagent execution for every checkpoint.
- [ ] Rule text uses explicit invocation syntax: `use Task tool with subagent_type='quality-review'`.
- [ ] Checkpoint task content standard includes required verdict handling (`APPROVED`/`REJECTED`).
- [ ] Rules state that `REJECTED` checkpoints cannot advance phase status.
- [ ] Rules retain human-approval halt semantics after evaluation.
- [ ] At least one checkpoint example in plan-lifecycle docs reflects the new mandatory quality-review instruction.
- [ ] Checkpoint YAML entries carry only `id`, `content`, `status` (no custom fields that Cursor would strip).
- [ ] Each checkpoint has a `#### P{N} Checkpoint Review Prompt` subsection in its phase body with blockquoted prompt.
- [ ] Plan generator composes review prompt from phase deliverables and acceptance criteria at plan creation time.
- [ ] Review prompt follows the two-section format: "Work to Evaluate" + "Quality Criteria" (3-7 criteria).
- [ ] Executor instructions specify: find body heading → read blockquote → fire Task tool → present verdict → HALT.

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
- Follow-up (2026-03-09): User identified that checkpoint tasks should carry the full review prompt pre-composed, not just a mandate to run quality-review. The plan generator has the phase context at creation time; the executor should not have to reconstruct it. Initially added `reviewAgent`/`reviewPrompt` YAML schema extension.
- Follow-up (2026-03-09): YAML approach failed in practice — Cursor's plan YAML serializer silently stripped custom fields when executor updated checkpoint status to `in_progress`. Executor then couldn't find the review prompt and started improvising. Fix: moved review prompts from YAML to plan body markdown as `#### P{N} Checkpoint Review Prompt` subsections with blockquoted prompts. Updated all plan-lifecycle files (rules, template, step-03, step-05) to reflect body-embedded standard.
