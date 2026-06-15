# Prompt-Refinement Checklist

Reference data for the create-component workflow. A pre-ship refinement pass for a component's drafted instructions — the markdown the agent will execute literally. Run every pass below on the draft BEFORE the component ships; each pass closes a different instruction-quality failure mode (hidden assumptions, vague wording, missing context, missing constraints, unforced clarification, excessive executive load).

A component's text IS its runtime: the executing agent follows the words literally, with none of the drafting conversation in context. These passes harden the words against that reading.

## How to Run This Pass

Apply each of the six passes to the drafted component file. For each, perform the listed action ON the draft, then apply the fix to the file. A pass with no findings is recorded as clean; a pass with findings rewrites the draft before the next pass runs.

| # | Pass | Closes |
|---|------|--------|
| 1 | Assumption Exposer | Instructions that only work if the executing agent guesses correctly |
| 2 | Anti-Vague Pass | Subjective qualifiers an agent cannot act on deterministically |
| 3 | Expert-Reframe Pass | Missing context, constraints, and output shape a domain expert would state |
| 4 | Constraint Injector | Outputs that drift because nothing bounds them |
| 5 | Clarification Gate | Gaps that should halt-and-ask rather than be silently filled |
| 6 | Executive-Load Pass | Irreducible judgment the agent must hold all-at-once, buried directives, unscaffolded deliberation |

## 1. Assumption Exposer

List every assumption the executing agent would have to make to follow this draft. Then rewrite the draft so none of those assumptions is left to the agent's discretion.

| Check | Action |
|-------|--------|
| Implicit path/file | Name the exact file, folder, or `{rbtv_path}`-rooted path the agent must read or write — never "the relevant file" |
| Implicit prior state | State what must already exist before this step runs, or have the step verify it |
| Implicit reader | The executing agent has zero memory of the drafting conversation — every fact it needs lives in the file or it does not exist |
| Implicit "obvious" step | If a human would infer a step, the agent will skip it — write the step out |

Fix: every surfaced assumption becomes an explicit instruction, a precondition check, or a named input — not a gap the agent fills.

## 2. Anti-Vague Pass

Identify every vague or subjective word in the draft — "good", "professional", "detailed", "appropriate", "as needed", "high-quality", "better", "robust". Replace each with a specific, measurable, or enumerated alternative the agent can act on without back-and-forth.

| Vague (BAD) | Specific (GOOD) |
|-------------|-----------------|
| "Keep the file reasonably short" | "Keep the file under 200 lines; if it exceeds the max, split it" |
| "Write a good persona" | "Give the persona a metaphor, three specific beliefs, and one communication quirk" |
| "Validate the output" | "Confirm required frontmatter keys `name`, `description`, `nextStepFile` are present" |
| "Handle edge cases appropriately" | "On missing input X, HALT and ask; on empty result, write the no-op marker" |

Fix: no qualifier survives that two agents could interpret differently. Where a number governs (size, count, threshold), state the number.

## 3. Expert-Reframe Pass

Reread the draft as if a senior author in the component's domain wrote it for a specialist to execute. Add the context, constraints, and output format that author would naturally include and the casual draft omits.

| Element | Add if missing |
|---------|----------------|
| Trigger | When this component/step activates — the input pattern, task type, or moment |
| Scope boundary | When it does NOT apply — unbounded instructions get over-applied or ignored |
| Output format | The exact shape produced (table, frontmatter keys, file at a named path, menu) |
| Path discipline | Cross-references use `{rbtv_path}` and runtime output resolution — never `../` or absolute paths |
| Control transfer | If another agent owns the next step, the handoff names the exact installed invocation and menu item |

Fix: a specialist could execute the component cold, from the file alone, and produce the intended artifact.

## 4. Constraint Injector

Add the constraints that make the component's output focused, actionable, and hard to misinterpret. Name at least three the component itself implies but does not state.

| Constraint family | Example to inject |
|-------------------|-------------------|
| Size | "Recommended {lo}-{hi} lines, {max} max; split if exceeded" per the component type |
| Thin-loader | "This skill/command contains zero logic — it LOADs and delegates to {target}" |
| Self-containment | "Every instruction needed lives in this file; reference other files only to be read, never to be summarized" |
| Halt discipline | "End with the menu and an explicit 'HALT and WAIT for user input'" where a step yields control |
| Determinism | "Produce {named artifact} every run; on a blocker, emit the blocker, never a silent skip" |

Fix: the drafted component carries the bounds that keep its executor on rails, stated in the file, not assumed.

## 5. Clarification Gate

Find every point where the draft would force the executing agent to guess on something only the owner can decide. Convert each into an explicit halt-and-ask instead of a silent fill.

| Gap pattern | Convert to |
|-------------|------------|
| Owner-only choice baked as a guess (which module, which persona, which routing) | "If {choice} is unspecified, HALT and ask the owner; do not assume" |
| High-impact missing input | A precondition the step verifies and halts on, never invents |
| One-pass confirmation needed | An explicit "confirm with the owner in ONE pass before proceeding" beat |

Fix: high-impact gaps halt and ask; low-impact gaps state the assumption inline and proceed. A silent guess on an owner-only decision is the defect this gate exists to prevent.

## 6. Executive-Load Pass

Find every step where the agent must reason, and minimize what it holds at once. Reasoning the agent can't avoid is paid in output tokens the owner never sees as context, and a long, unscaffolded trace dilutes attention and propagates an early error through everything after it. This pass shapes irreducible judgment; the Anti-Vague Pass (2) removes ambiguity load — they are different cuts.

| Check | Action |
|-------|--------|
| Unscaffolded deliberation | An open directive ("consider all the ways…", "reason about…", "use judgment") gets an enumerated frame — the dimensions, checklist, or candidate set the thinking must cover — so the reasoning trace stays bounded |
| Buried directive | The decisive instruction and the HALT move to the step's head or foot, adjacent to the menu — never mid-prose where attention is weakest |
| Simultaneity | Interacting constraints the agent must weigh at once are sequenced into ordered sub-steps; if a lookup can decide them instead, that is a DECIDE fix (table/script), not this pass |
| Re-derived frame | The 1–3 governing facts the step needs to reason (mode, prior decisions, scope) are restated at the step head, not left for the agent to reconstruct |

Fix: a step that requires judgment bounds it — framed, hoisted, sequenced — so the agent spends reasoning on the task, not on holding the step's own structure in mind.

## Ship Gate

The draft ships only when all six passes are clean or their findings are fixed in the file:

| Pass | Clean condition |
|------|-----------------|
| Assumption Exposer | No instruction depends on the executing agent guessing an unstated fact |
| Anti-Vague Pass | No subjective qualifier two agents could read differently survives |
| Expert-Reframe | Trigger, scope boundary, and output format are all explicit |
| Constraint Injector | The component's bounds (size, thin-loader, self-containment, halt) are stated in the file |
| Clarification Gate | Every owner-only decision halts-and-asks rather than guessing |
| Executive-Load Pass | Every judgment step is framed, the decisive directive is hoisted, and no unscaffolded "consider all…" survives |

A draft that fails any row is not ready — fix the file and rerun that pass.
