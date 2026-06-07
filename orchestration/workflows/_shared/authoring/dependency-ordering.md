# Dependency Ordering

How to order a task set so every dependency lands before its dependents. Consumed by `rbtv-planning` and orchestration intake — both order the tasks they author by these rules before finalizing.

---

## Ordering rules

| Rule | Description |
|------|-------------|
| Dependencies first | If task B consumes task A's output, A comes before B |
| CREATE before UPDATE | A file cannot be UPDATEd before it is CREATEd |
| Layer by dependency depth | Group tasks by how many dependencies they carry; shallower layers first |
| Critical path first | Blocking tasks before non-blocking |
| High-value first / low-value last | Complex, critical work early; routine, administrative work late |
| Shared dependencies grouped | When several tasks need the same prerequisite, place it once, ahead of all of them |

## Shared-file serialization

When multiple tasks touch the SAME file, declare an explicit serialization order for that file in the plan (e.g., `commands.js: T5→T7`; `runtime-main.js: T5→T9→T8`). Parallel waves are built strictly from these orders. This is what produced zero merge conflicts across 3-, 4-, and 6-wide Kimi waves (`learnings-kimi-worker.md` §3). A task set with parallel-safe slices MUST carry the serialization order for every shared file before any wave is dispatched.

## Validity checks

Run all four before finalizing the ordered task set:

1. No task references the output of a LATER task.
2. No circular dependencies (A→B→C→A).
3. CREATE precedes UPDATE for the same file.
4. Every shared file has a declared serialization order — written in the plan document (per Shared-file serialization above) — covering all tasks that touch it.

A set that fails any check is not ready to dispatch — reorder, split, or add the missing serialization order, then re-check.
