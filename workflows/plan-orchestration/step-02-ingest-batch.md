---
stepNumber: 2
stepId: ingest-batch
nextStepFile: ./step-03-orchestrate-loop.md
---

# Step 2: Ingest and Batch

**Goal:** Read the entire plan + shape, map phases to tasks, and produce a private delegation map that avoids both micro-delegation and macro-delegation.

---

## MANDATORY SEQUENCE

### 1. Read Plan + Shape

- Read the FULL plan file.
- Locate and read the plan's `shape.md` (or equivalent design/spec doc) if it exists. Common locations: same directory as the plan, parent directory, `_design/` subfolder.
- Locate any docs the plan references (e.g., readiness docs, requirements docs). Note their paths but do NOT read them now — they are loaded on-demand by the doc-reader sub-agent.

If no shape exists, note that. Doubt escalation will skip the "re-read shape" step and go directly to sonnet doc-read.

### 2. Map Phases to Tasks

Build a private delegation map (in working memory only — do not write to disk):

| Phase | Tasks | Estimated complexity |
|-------|-------|---------------------|
| Phase 1 | task 1.1, 1.2, 1.3 | low / medium / high |
| Phase 2 | task 2.1, 2.2 | ... |

### 3. Batch Tasks (Avoid Micro/Macro Delegation)

For each phase, group tasks into executor batches:

**Avoid micro-delegation:** if 2+ adjacent tasks are small, related, and share context, group them into ONE batch for ONE executor sub-agent.

**Avoid macro-delegation:** if a single task is large, multi-faceted, or touches unrelated areas, split it across multiple batches.

Heuristic:
- 1 batch = 1 sub-agent dispatch
- Batch size target: 30-90 minutes of equivalent human work
- Same batch only if the executor needs the same context to complete the tasks

### 4. Present Delegation Plan to User

Show a summary table:

| Phase | Batches | Reviewer dispatch |
|-------|---------|-------------------|
| Phase 1 | [N] batches: [brief list] | After all Phase 1 batches complete |
| Phase 2 | [N] batches: [brief list] | After all Phase 2 batches complete |
| ... | ... | ... |

Add: "Doubts at any point will halt and surface to you. Confirm to proceed?"

Wait for user approval. If the user adjusts batching, update the map and re-present.

### 5. Proceed

On approval, load `./step-03-orchestrate-loop.md`.
