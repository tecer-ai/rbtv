# Human Review Flag Criteria

When a task with `human_review: required` closes, the executor emits a Human Review Presentation block (per `plan-task-microstep-template.md`). The block lists what the human should review and surfaces red/yellow flags. To prevent rubber-stamping AND prevent false alarms, flags must be backed by concrete evidence drawn from this task's execution — never free-associated.

## Red Flag Triggers (high concern)

A red flag fires when ANY of these evidence-based conditions hold for this task:

| Trigger | Evidence required |
|---------|-------------------|
| Irreversible operation without rollback path | Specific destructive operation (delete, force-push, data overwrite) and absence of backup |
| Scope deviation | File or system modified outside the task's declared scope (compare against task Goal + Output Requirements) |
| Architectural-constraint deviation | Specific clause in the plan's Architectural Constraints section that this work conflicts with |
| Doubt resolved unilaterally | Sub-agent or executor returned `DOUBT_ESCALATED` and the orchestrator decided autonomously, OR executor surfaced a question and proceeded without user input |
| Discovery contradicts shape.md | Task execution revealed information that invalidates a Decision in shape.md |
| Tool denial worked around | A Bash/Write/Edit call was denied and the executor produced equivalent state via another path |
| New external dependency or public interface | New library import, new API exposed, new env var consumed, new permission required |

## Yellow Flag Triggers (worth noting)

A yellow flag fires when ANY of these evidence-based conditions hold for this task:

| Trigger | Evidence required |
|---------|-------------------|
| Multiple reasonable alternatives chosen unilaterally | Specific decision point (naming, location, signature) where executor picked without user explicit approval AND alternatives are non-trivially different |
| Scope-aligned but non-explicit choice | Implementation detail not specified by user that materially shapes future work (e.g., schema field types, endpoint shape) |
| Test coverage gap | Task delivered code or behavior, no matching test added, and the task description implied coverage |
| Cross-task coupling noticed but not acted on | Executor saw that this work creates tight coupling with another task's output but did not refactor |
| Style or convention drift | New file's style differs from neighboring files in the same folder |
| Performance or scalability concern visible in change | Specific code path with O(n²) over a bounded-but-large set, N+1 queries in a loop, etc. — not hypothetical |

## Anti-Flag Rules (suppress false alarms)

The executor MUST NOT flag any of the following. Each violation degrades signal value and conditions the human to skim.

| Anti-pattern | Why it's not a flag |
|--------------|---------------------|
| "Consider X for the future" hypotheticals | Flags are about THIS task's evidence, not speculative roadmap items |
| Standard library or framework idioms | Routine patterns are not risks |
| "Watch for edge cases" without naming one | Generic concern with no evidence pointer |
| "May need testing" without a coverage gap | Without a specific gap, this is filler |
| "Could be refactored later" | Out of scope — not a risk in the executed work |
| Style preferences disconnected from the project's conventions | Personal taste is not a flag |
| Re-stating what the task did | "We modified file X" is summary content, not a flag |

## No-Flag Affirmation

If no triggers fire after running through Red and Yellow tables, write `None identified.` in BOTH lists and add a one-line rationale that names which checks ran clean. Examples:

- "No irreversible operations, no scope deviation, no architectural-constraint conflicts."
- "Mechanical rename within scope; no new dependencies, no doubts surfaced."
- "Test added matching the task's claimed coverage; conventions match neighboring files."

The rationale is REQUIRED when both flag lists are empty — without it, the human cannot tell whether the executor checked or just skipped the analysis.

## Coverage in Orchestration Mode

Under orchestration mode (dispatched via `rbtv-orchestrating`), the executor's flags travel up the chain:

1. Executor includes the Human Review Presentation block in its return paragraph (per the dispatch wrapper's return schema).
2. Phase reviewer (one tier above) reviews the executor's flags AND adds its own per these same criteria. Reviewer's higher tier and broader read make it more likely to catch what the executor missed.
3. Orchestrator surfaces the merged flag set to the user at phase boundaries and in the run finalization (per `rbtv-orchestrating` verification card §6).

In standalone mode the executor is the only voice — the block goes straight to the user at Phase: Close.
