# Deliverables Template

Use this template to create the `deliverables.md` companion file for each plan. Deliverables is the plan's **artifact index** — one row per task recording where that task's output lands and its current status. `decisions.md` answers "why did we choose X"; `deliverables.md` answers "where is X".

---

## Template

```markdown
# Deliverables Map - {Plan Name}

> **Single index of every artifact this plan produces.**
>
> **Every agent working on this plan MUST:**
> 1. Read this file BEFORE starting any task — it tells you the exact path your output must land at.
> 2. UPDATE this file AFTER delivering — flip the Status to ✅ and confirm the Path matches what you produced.
> 3. EDIT Status/Path cells in place — this file is mutable (unlike append-only decisions.md); NEVER append duplicate rows to record a status change. A task added during execution gets a `pending` row in its phase table; a removed task's row is ~~struck~~, never deleted.
>
> The synthesis tasks ({synthesis-task-ids}) read this map to find every input they need. If an artifact lands somewhere this map doesn't list, the synthesis agent will miss it. The index being accurate is a hard dependency, not a courtesy.

---

## Phase 1 deliverables

| Task | Artifact | Path | Status |
|------|----------|------|--------|
| p1-1 | {What the task produces} | {Landing path} | pending |
| p1-2 | {What the task produces} | {Landing path} | pending |
| p1-checkpoint | Phase 1 evaluation findings + user approval | `./decisions.md` (Decision entry) | pending |

{One section per phase. One row per task in the plan's task list — including checkpoints and final-phase tasks (pN-refs, pN-compound, pN-checkpoint).}

**Status values:** `pending` | `in-progress` | `✅` | `⏸ deferred` — deferrals carry a parenthetical reason in the cell.

---

## How the synthesis tasks consume this index

A fresh agent at {synthesis-task-id} reads, in order:

1. **This file (`deliverables.md`)** — the artifact index.
2. `./decisions.md` end-to-end — every Decision and Discovery; the running rationale (harvest-worthy entries carry the one-word `compoundable` marker).
3. Each artifact referenced above, in document order — they build on each other.

{Adapt to the plan's actual synthesis tasks: name each one and state what it folds the artifacts into.}

---

## Sub-folder creation

{List the conventional sub-folders the Path column uses — e.g., `phase-1/move-logs/`, `phase-1/inventories/`, `phase-2/verifications/`.} Sub-folders are created on demand by the first task that needs them — never pre-created empty.
```

---

## Usage Instructions

Creation mechanics (when to create, row derivation, 1:1 validation) are owned by `../steps-c/step-04-generate-artifacts.md` §6 — follow it there. Execution-time update rules ride INSIDE the generated artifact's header block above, where their real consumer (the executing agent) reads them.

### deliverables.md vs decisions.md

| | decisions.md | deliverables.md |
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
