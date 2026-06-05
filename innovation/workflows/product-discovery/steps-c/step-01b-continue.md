---
stepNumber: 1
stepName: continue
description: 'Resume pre-product discovery from last completed step'
workflowFile: '../workflow.md'
---

# Step 1b: Continue Previous Session

---

## STEP GOAL

Detect where the previous session left off and resume from the next incomplete step.

---

## MANDATORY SEQUENCE

### 1. Locate State Document

Ask the user for the path to their `discovery-state.md`, or scan the project's output folders for it.

### 2. Read State

Read the state document's frontmatter. Extract:
- `stepsCompleted` — which steps are done
- `processedBenchmarks` — which benchmarks have profiles (relevant for Step 2)
- All file paths (taxonomy, synthesis, product map, etc.)

### 3. Determine Next Step

| Last Completed Step | Next Step File |
|---------------------|----------------|
| _(none)_ | `./step-01-init.md` — start fresh |
| `step-01-init-taxonomy` | `./step-02-benchmark-loop.md` |
| `step-02-benchmark-loop` | `./step-03-comparative-synthesis.md` |
| `step-03-comparative-synthesis` | `./step-04-product-map.md` |
| `step-04-product-map` | `./step-05-v1-scoping.md` |
| `step-05-v1-scoping` | Workflow complete — all outputs produced |

### 4. Present Status

Show the user:
- Steps completed
- For Step 2 resumption: benchmarks processed vs. remaining, current taxonomy version
- Any output files already produced

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — resume from the next step

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[C] Continue** is selected: load the determined next step file and follow its instructions.
