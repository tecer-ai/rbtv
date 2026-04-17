---
title: 'Compound: Compound Workflow Asks for Filename Before Naming Convention Is Known'
docType: 'compound'
mode: 'create'
priority: 'Low'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - _bmad/rbtv/_admin/roadmap/todos/cp-rule-shape-capture.md
outputPath: '_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-14'
yoloMode: true
---

# Compound Workflow Asks for Filename Before Naming Convention Is Known

**Type:** Workflow
**Priority:** Low
**Tracker:**
**Status:** Testing

---

## Overview

### Problem

The compound workflow (`doc-compound-learning`) asks the user to confirm a filename at Step 1 (Init), but the naming convention (`cp-{component}-{description}.md`) is only defined at Step 4 (Document). This creates a file with a user-guessed name that must be renamed at Step 4, which is wasteful and confusing.

In practice: the file was created as `compound-context-preservation-rule.md` and had to be renamed to `cp-rule-shape-capture.md` at the end — an unnecessary rename caused by the workflow's own sequencing.

### Goals

Step 1 must either apply the naming convention itself or defer filename selection to Step 4.

### Constraints

- Must not break the existing workflow architecture
- Must not require the user to know the naming convention upfront

---

## Self-Assessment

### Error Analysis

**Error type:** Execution failure — the workflow's step sequencing places filename selection before the naming convention is available.

### Context Source Evaluation

| File | Gap |
|------|-----|
| `doc-compound-learning/steps-c/step-01-init.md` | Step 3 asks user for filename confirmation — but has no reference to the `cp-{component}-{description}.md` convention |
| `doc-compound-learning/steps-c/step-04-document.md` | Step 2 defines the naming convention and suggests a filename — but by this point the file already exists with a different name |

### Improvement Options

1. **Move naming convention to Step 1** — Step 1 applies the `cp-{component}-{description}.md` convention when generating the filename suggestion. Step 4 no longer needs a rename step.
   - **Rationale:** Simplest fix. Convention is applied from the start.
   - **Location:** `doc-compound-learning/steps-c/step-01-init.md` — add the naming convention and format instructions to the "Generate filename suggestion" sub-step
   - **Pattern Consistency:** Follows the principle that file naming should happen once, at creation. No rename needed.

2. **Defer file creation to Step 4** — Step 1 works in memory only. Step 4 creates the file with the correct name.
   - **Rationale:** Avoids the rename entirely.
   - **Location:** `step-01-init.md` (remove file creation), `step-04-document.md` (add file creation)
   - **Pattern Consistency:** Breaks the pattern of creating output early — other workflows create output at step 1 to enable state tracking via frontmatter.

---

## Proposed Solution

**Option 1: Move naming convention to Step 1.** Add the `cp-{component}-{description}.md` naming convention and format instructions to Step 1's filename generation sub-step. Remove the filename determination from Step 4 (keep only the save step).

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `doc-compound-learning/steps-c/step-01-init.md` (add naming convention), `doc-compound-learning/steps-c/step-04-document.md` (remove filename determination, keep save) |
| Scope of change | Minimal — move naming convention text between two step files |
| Related files | None |

---

## Rationale

Files should be named correctly at creation. Renaming at the end is a symptom of missequenced logic. The naming convention is simple enough to apply at Step 1 without requiring Step 4's context.

---

## Acceptance Criteria

- [ ] Step 1 suggests filenames using the `cp-{component}-{description}.md` convention
- [ ] Step 4 does not ask for or change the filename — it only saves the final content
- [ ] No file renames occur during the compound workflow

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/doc-compound-learning/steps-c/step-01-init.md` | Filename generation — needs naming convention added |
| `_bmad/rbtv/workflows/doc-compound-learning/steps-c/step-04-document.md` | Filename determination — needs removal |

---

## References

- Triggering incident: `cp-rule-shape-capture.md` was created as `compound-context-preservation-rule.md` and required a rename
