# Deterministic First

Agents MUST reach for the deterministic capabilities available in the workspace instead of improvising with LLM reasoning — and MUST compute, never estimate, whenever an exact, verifiable answer exists.

## The Three Arms

| Arm | Fires when | Required action | Teeth |
|-----|-----------|-----------------|-------|
| **Reach** | About to perform a step by LLM reasoning AND a deterministic capability plausibly exists (a tool, API, runtime, or existing script) | Consult the workspace capability inventory if one exists (a Capabilities section in the root CLAUDE.md or the file it points to) plus the available runtimes, BEFORE improvising; prefer the deterministic capability | Advisory |
| **Compute** | The step has an exact, verifiable answer — arithmetic, reconciliation, counting, sorting, dedup, date math, aggregation, parsing or transforming structured data | Produce the result from an ACTUAL deterministic computation (a tool, script, or runtime invocation), NEVER from reasoning | **Hard gate** |
| **Register** | During the task you wrote a script or command that solves a deterministic sub-step that WILL RECUR | Propose promoting it: persist it where the recurring work lives (the owning workflow folder or the workspace scripts location), wire the caller to it, add usage notes, and add it to the capability inventory — following `rbtv-compounding` (state the fix and its location; ask before implementing) | Advisory |

**Compute is not Build.** Computing an exact answer (cheap — a one-liner, a `python -c`, a single tool call) is a different act from building and persisting a script (only past the Register trigger). A one-off `git mv` of three files: perform the deterministic action, do NOT author a script. Only Register carries build cost, and only when the work recurs. Before building anything, test: *will this script run more than once?* No → do the task, build nothing.

## The Compute Gate

**Tripwire — scan before stating any exact-answer result.** If you are about to write a number, count, date, total, or reconciliation outcome that you derived by reasoning rather than by running a deterministic computation, STOP and compute it. The compliance artifact is the computation itself — the tool or script invocation and its output, visible in the transcript. A reasoned exact answer with no computation behind it is a correctness defect, not an answer.

Exception — an explicit request for an estimate ("ballpark it", "roughly") is a legitimate ask: provide the estimate and label it as one. The gate fires when an exact answer is expected or consequential.

## Scope and Exemptions

Always active; fires only on the triggers above.

**Exempt:**
- One-off trivial deterministic actions you simply perform (a small rename, a single move) — do them; persist nothing.
- Pure judgment, prose, or design work with no exact answer and no available deterministic capability.

Fail-safe: if an exact verifiable answer plausibly exists, or a capability plausibly exists, treat the step as in-scope — ambiguity resolves toward Compute/Reach, never toward improvising.

## Anti-Patterns

| Type | Thought | Action |
|------|---------|--------|
| Skip | "It's a small sum — I'll do it in my head" | An exact answer exists. Compute it; estimating it is a bug. |
| Skip | "There's probably no tool for this" | Check the capability inventory and available runtimes BEFORE concluding none exists. An unchecked absence is not absence. |
| Skip | "I'll promote this script later" | Later is never. If the script addresses recurring work, propose registering and wiring it now. |
| Skip | "I'm done — let me clean up my temp scripts" | If a script solved a RECURRING workflow step, deleting it forces every future run to re-derive it. Run the Register check and propose promoting it BEFORE deleting. |
| Game | "I'll run `python -c` but just print the number I already reasoned" | The computation MUST derive the result from the inputs. Laundering a guess through a tool call is not computing. |
| Game | "I'll call it 'judgment, no exact answer' so the gate doesn't apply" | Escape-hatch abuse. If an exact verifiable answer exists, the gate applies — the no-exact-answer exit must be justified by the task. |
| Game | "I'll build a script for a one-off so it looks diligent" | Over-building. Register is recurrence-gated and `rbtv-reasoning`'s Simplicity-first forbids it. Perform the action; build nothing. |

Boundary: this rule complements `rbtv-done-gate` (exercise outcomes with real computation, not theater) and is bounded by `rbtv-reasoning`'s Execution Discipline (Simplicity-first caps the Register arm). Promote-and-wire mechanics live in `rbtv-compounding` — follow it; never restate it here.
