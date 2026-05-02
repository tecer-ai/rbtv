---
stepNumber: 4
stepId: finalize
nextStepFile: null
---

# Step 4: Finalize

**Goal:** Produce a final summary of orchestrated execution and surface anything incomplete.

---

## MANDATORY SEQUENCE

### 1. Build Summary Table

Present:

| Phase | Batches dispatched | Reviewer findings | Status |
|-------|-------------------|-------------------|--------|
| Phase 1 | [N] | [fixes applied / clean] | ✅ Complete |
| Phase 2 | [N] | [...] | ✅ Complete |
| ... | ... | ... | ... |

### 2. Surface Incomplete Items

If any of the following occurred during execution, list them explicitly:

- Tasks the user halted before completion
- Doubts that were resolved but worth noting for future plan iterations
- Reviewer findings that required user input
- Any deviations from the original delegation plan

If nothing to surface, write: "No incomplete items. All phases completed cleanly."

### 3. Recommend Next Steps

Suggest one or more of:

- Update the plan document to reflect what was done (if it tracks status)
- Commit the resulting changes (if a git repo is involved)
- Run any project-specific validation skill (e.g., `sb-vault-integrity` for vault changes)

### 4. End

Inform the user the orchestration workflow is complete. Do not auto-invoke any follow-up skill — let the user decide.
