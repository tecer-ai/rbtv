---
title: 'Compound: PRD Option Evaluation — Format Consistency Criterion'
docType: 'compound'
mode: 'update'
priority: 'Low'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - .cursor/plans/ps-lite-domcobb/learnings.md
  - _admin/roadmap/todos/compound-ps-lite-domcobb.md
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-12'
yoloMode: false
---

# PRD Option Evaluation — Format Consistency Criterion

**Type:** Process Improvement
**Priority:** Low
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The compound PRD for ps-lite-domcobb evaluated five implementation options using technical criteria (latency, overhead, file size, reusability). It recommended inline `<action>` based on these factors. The user overrode this recommendation, preferring structural consistency — all menu items should follow the same pattern (workflow loaded via `exec=`). The PRD's evaluation framework missed "consistency with existing patterns" as a criterion, leading to a recommendation the user rejected.

### Goals

- Add "consistency with existing patterns" as a standard evaluation criterion in compound PRD option analysis
- Prevent future PRDs from recommending technically optimal but structurally inconsistent approaches

### Constraints

- Must not over-constrain option evaluation — consistency is one factor, not always the deciding one
- Must integrate naturally into existing compound workflow steps

---

## Self-Assessment

### Error Analysis

**Error type:** Incomplete evaluation framework

The compound workflow's option evaluation weighted technical factors (latency, overhead, file size) but didn't evaluate whether the proposed approach matches existing patterns in the target system. Users value structural consistency for maintainability and cognitive load reduction — factors that don't surface in purely technical analysis.

### Improvement Options

1. **Add criterion to compound workflow step**: Update the compound workflow's self-assessment or discussion step to include "pattern consistency" as an evaluation dimension.

2. **Add to plan-creation-rules**: Include pattern consistency check in the plan creation knowledge file.

---

## Proposed Solution

**Option 1: Add criterion to compound workflow step**

Identify the compound workflow step that evaluates improvement options and add "consistency with existing patterns" as a required evaluation dimension alongside technical criteria.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | Compound workflow step file(s) responsible for option evaluation |
| Scope of change | Add 1 evaluation criterion to option analysis |
| Impact | Future compound PRDs will evaluate pattern consistency before recommending approaches |

---

## Acceptance Criteria

- [ ] Compound workflow option evaluation includes "consistency with existing patterns" as a criterion
- [ ] Criterion is weighted appropriately (not overriding technical factors, but considered alongside them)

---

## Related Files

| File | Relationship |
|------|--------------|
| Compound workflow steps | Target — option evaluation step |
| `_admin/roadmap/todos/compound-ps-lite-domcobb.md` | Example of PRD that missed this criterion |
| `.cursor/plans/ps-lite-domcobb/learnings.md` | Source learning (L2) |

---

## Origin

Compounded from learning L2 in `.cursor/plans/ps-lite-domcobb/learnings.md` during ps-lite-domcobb plan execution (2026-02-12).
