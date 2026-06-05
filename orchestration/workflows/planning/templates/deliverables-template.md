# Deliverables Template

Use this template to create the `deliverables.md` companion file for each plan. Deliverables is the plan's **artifact index** — one row per task recording where that task's output lands and its current status. `shape.md` answers "why did we choose X"; `deliverables.md` answers "where is X".

---

## Template

```markdown
# Deliverables Map - {Plan Name}

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
>
> The synthesis tasks ({synthesis-task-ids}) read this map to find every input they need. If an artifact lands somewhere this map doesn't list, the synthesis agent will miss it. The index being accurate is a hard dependency, not a courtesy.

---

## Phase 1 deliverables

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | {What the task produces} | {Landing path} | pending |
| p1-2 | {What the task produces} | {Landing path} | pending |
| p1-checkpoint | Phase 1 evaluation findings + user approval | `./shape.md` (Decision entry) | pending |

{One section per phase. One row per task in the plan's task list — including checkpoints and final-phase tasks (pN-refs, pN-compound, pN-checkpoint).}

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the synthesis tasks consume this index

A fresh agent at {synthesis-task-id} reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./shape.md` end-to-end — every Decision and Discovery; the running rationale.
3. Each artifact referenced above, in document order — they build on each other.
4. `./learnings.md` — meta-observations that may inform the synthesis.

{Adapt to the plan's actual synthesis tasks: name each one and state what it folds the artifacts into.}

---

## Sub-folder creation

{List the conventional sub-folders the Path column uses — e.g., `phase-1/move-logs/`, `phase-1/inventories/`, `phase-2/verifications/`.} Sub-folders are created on demand by the first task that needs them — never pre-created empty.
```

---

## Usage Instructions

### Creating deliverables.md

1. Create during plan creation (step-04), AFTER micro-step task files — Artifact and Path cells derive from each task's Output Requirements
2. One row per task in the plan's task list, including checkpoints and final-phase tasks — row count MUST equal task count (step-04 validates this 1:1)
3. **Artifact** — what the task produces, one phrase: from the task's Output Requirements (micro-step tasks) or the task description (inline tasks)
4. **Path** — intended landing path. Internal artifacts use `./` file-relative paths; external artifacts use project-root-relative paths (Plan Linking Standard). Decision-only tasks land in `./shape.md` (Decision entry)
5. **Status** — `pending` on every row at creation
6. Fill the synthesis section with the plan's actual synthesis task IDs and the document-order read list
7. Derive the sub-folder list from the Path column

### During Execution

1. **Before any task:** read this file — it tells you where your output must land
2. **After delivering:** update your task's row — flip Status to `✅` (or `⏸ deferred` with reason) and correct the Path if the artifact landed somewhere other than planned
3. **Status and Path cells are mutable in place** — unlike shape.md (append-only), this file is EDITED. Never append duplicate rows to record a status change
4. **Task added during execution** (revolving plan): add its row to the matching phase table with Status `pending`
5. **Task removed during execution:** strike the row (~~strikethrough~~), mirroring the plan task list convention — never delete it

### deliverables.md vs shape.md

| | shape.md | deliverables.md |
|---|----------|-----------------|
| Content | Decisions + discoveries + rationale | Artifact index |
| Mutability | Append-only narrative | Mutable Status/Path cells |
| Answers | "Why did we choose X" | "Where is X" |
| Consumer | In-flight executors needing context | Synthesis tasks gathering every input |

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Header block | 8-10 lines | 12 lines |
| Per task row | 1 line | 2 lines |
| Synthesis section | 5-10 lines | 15 lines |
| Sub-folder section | 3-5 lines | 8 lines |

**Note:** deliverables.md grows only when the plan gains tasks. Growth from appended status rows indicates misuse — Status flips happen in place.
