---
stepNumber: 2
stepName: 'milestone-route'
knowledgeFile: ../data/founder-process.md
projectMemo: '{bmad_output}/{project-name}/business-innovation/project-memo.md'
---

# Step 02: Milestone Route

**Progress: Step 2 of 2** — Route directly to current milestone (no menu)

---

## STEP GOAL

Read project state from project-memo and route the user directly to the appropriate milestone workflow. New projects go to M1; existing projects go to their current milestone.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a YC mentor. Get the founder to the right place in the journey with no extra steps.

### Step-Specific Rules

- Read project-memo frontmatter to determine current state
- No milestone menu: route immediately based on state
- New project → M1: Conception
- Existing project → current milestone from project-memo

---

## MANDATORY SEQUENCE

### 1. Load Project State

Read `{projectMemo}` frontmatter to understand:
- currentMilestone (e.g. "M1: Conception", "M2: Validation", …)
- stepsCompleted array

### 2. Determine Target Milestone

| State | Target | Workflow path |
|-------|--------|---------------|
| New project (stepsCompleted empty) | M1: Conception | `../bi-m1/workflow.md` |
| Existing project | Use currentMilestone from frontmatter | See mapping below |

**currentMilestone → workflow path (relative to this file):**

| currentMilestone | Load |
|------------------|------|
| M1: Conception | `../bi-m1/workflow.md` |
| M2: Validation | `../bi-m2/workflow.md` |
| M3: Brand | `../bi-m3/workflow.md` |
| M4: Prototypation | `../bi-m4/workflow.md` |
| M5: Market Validation | `../bi-m5/workflow.md` |
| M6: MVP | `../bi-m6/workflow.md` |

### 3. Route Immediately

1. Resolve the workflow path for the target milestone (replace `../` with the actual path from `{project-root}/_bmad/rbtv/agents/paul/workflows/business-innovation/` so that bi-m1 → `{project-root}/_bmad/rbtv/agents/paul/workflows/business-innovation/bi-m1/workflow.md`).
2. Load that workflow file and follow its instructions.
3. Do not present a milestone menu. Do not HALT for milestone selection.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Project state correctly read from project-memo frontmatter
- New project (empty stepsCompleted) routed to M1
- Existing project routed to currentMilestone workflow
- No milestone menu shown; user lands directly in the milestone

❌ **FAILURE:**
- Showing a milestone selection menu
- Routing to wrong milestone (e.g. existing project sent to M1 when currentMilestone is M2)
- Failing to load project-memo (e.g. Continue without project-memo @-mention)
