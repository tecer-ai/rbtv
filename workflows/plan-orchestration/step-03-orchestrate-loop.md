---
stepNumber: 3
stepId: orchestrate-loop
nextStepFile: ./step-04-finalize.md
---

# Step 3: Orchestrate Loop

**Goal:** Execute the delegation plan phase by phase: dispatch executors per batch, dispatch reviewer per phase, honor checkpoint mode, halt on doubts.

---

## MANDATORY SEQUENCE

**Structure:** For each phase in order, sections 1 → 2 → 3 below run sequentially within the phase. Section 4 (Doubt Escalation) interrupts whenever any sub-agent returns DOUBT_ESCALATED during section 1 or 2. Section 5 (Loop or Advance) fires once after the final phase's section 3 completes.

### 1. Dispatch Executors (one per batch)

For each batch in the current phase:

1. Load the executor prompt template at `./templates/executor-prompt.md`.
2. Fill in the template variables:
   - `{batch_tasks}` — the full text of the tasks in this batch (paste from plan, do NOT just reference)
   - `{plan_path}` — full path to the plan file
   - `{shape_path}` — full path to shape.md, or `NONE` if no shape exists
   - `{rbtv_path}` — absolute path to the rbtv source repo (read from `rbtv.json` at the workspace root); the orchestrator MUST resolve this to a literal path before dispatch — sub-agents do not inherit the placeholder
   - `{referenced_docs}` — list of doc paths this batch needs, each tagged `[INLINED]` or `[FULL READ]` per the **Inlining Reference Document Context** rule (see §Inlining Reference Document Context below)
   - `{inlined_context}` — verbatim excerpts of `[INLINED]` docs, formatted per the rule; literal `NONE` if no docs inlined
3. Dispatch via the Agent tool with `subagent_type: general-purpose` and `model: <executor_model>`, where `<executor_model>` is the tier assigned to this batch in step-02 (haiku / sonnet / opus). If the user overrode the model for this batch or phase, honor the override.
4. Wait for the sub-agent's return.
5. Handle the return status:

| Status | Action |
|--------|--------|
| **DONE** | Mark batch complete. Proceed to next batch in phase. |
| **DONE_WITH_NOTES** | Note the observations. Proceed to next batch. |
| **DOUBT_ESCALATED** | STOP. Surface the doubt to the user (see Section 4). |
| **BLOCKED** | STOP. Surface the blocker to the user. |

6. After handling the return status, update `{plan_dir}/orchestration-state.md`: append a row to the Completed Batches table with the returned status, set Resume Point to the next batch, refresh the timestamp. If the status was DOUBT_ESCALATED or BLOCKED, also fill the Active State section with the doubt/blocker details. NEVER write per-batch outcomes to shape.md — that file is reserved for planning decisions and discoveries (per shape template's append-only rules).

Dispatch executors **sequentially** within a phase — never in parallel. Sequential dispatch prevents conflicts when batches touch overlapping files.

### 2. Dispatch Phase Reviewer

After ALL batches in the phase complete:

1. Load the reviewer prompt template at `./templates/reviewer-prompt.md`.
2. Fill in the template variables:
   - `{phase_name}` — name/number of the phase just completed
   - `{phase_scope}` — what this phase was supposed to accomplish (paste from plan)
   - `{plan_path}` — full path to the plan file
   - `{shape_path}` — full path to shape.md, or `NONE`
   - `{rbtv_path}` — absolute path to the rbtv source repo (resolved per executor section above); MUST be literal before dispatch
   - `{batches_completed}` — list of batch summaries returned by executors
   - `{referenced_docs}` — list of doc paths the reviewer needs for this phase, each tagged `[INLINED]` or `[FULL READ]` per the **Inlining Reference Document Context** rule (see §Inlining Reference Document Context below). Reviewer dispatches DEFAULT TO `[FULL READ]` for any doc whose compliance is part of this phase's review criteria — narrow excerpts can hide spec violations the executor missed
   - `{inlined_context}` — verbatim excerpts of `[INLINED]` docs, formatted per the rule; literal `NONE` if no docs inlined
3. Determine the reviewer model using this rule — one tier above the highest-tier executor in the phase, floor `sonnet`. Reviewer is NEVER haiku.

   | Highest executor tier in phase | Reviewer model |
   |--------------------------------|----------------|
   | haiku | `sonnet` |
   | sonnet | `opus` |
   | opus | `opus` |

   If the phase mixed tiers (e.g., 3 haiku batches and 1 sonnet batch), use the highest tier present (sonnet → opus reviewer).

4. Dispatch via the Agent tool with `subagent_type: general-purpose` and `model: <reviewer_model>` from the table above.
5. The reviewer is instructed to FIX issues in place, not just report them.
6. Wait for the reviewer's return.
7. If the reviewer escalates a doubt: STOP and surface to user.
8. After the reviewer returns CLEAN or FIXED, update `{plan_dir}/orchestration-state.md`: set the Reviewer Status cell to CLEAN or FIXED for every batch in this phase, advance Resume Point to the next phase's first batch (or "FINAL — orchestration complete" if this was the last phase), refresh the timestamp.

### 3. Honor Checkpoint Mode

After the reviewer returns clean:

- **`checkpoint_mode: halt`** — Present a brief summary of the phase and the reviewer's findings. Ask: "Phase [N] complete. Continue to Phase [N+1]?" Wait for user.
- **`checkpoint_mode: end-to-end`** — Proceed immediately to the next phase. No prompt.

### 4. Doubt Escalation Handling

When a sub-agent returns `DOUBT_ESCALATED`:

1. Present the doubt to the user verbatim, with context:
   > Sub-agent halted with a doubt during [phase/batch].
   > **Question:** [the doubt]
   > **What it tried:** [shape consultation result, sonnet doc-read result]
   > **Awaiting your input.**
2. Wait for user response.
3. Pass the user's answer back into a fresh executor (or reviewer) dispatch with the doubt resolved.

### 5. Loop or Advance

When all phases are complete, load `./step-04-finalize.md`.

---

## Inlining Reference Document Context

For each doc the plan references that a batch (or phase reviewer) needs to consult, the orchestrator picks ONE mode per dispatch and fills `{referenced_docs}` + `{inlined_context}` accordingly.

### Mode Selection

| Mode | When to use | How to fill |
|------|------------|-------------|
| **Inline whole doc** | Doc is small (~50 lines or ~2K tokens — line count is the agent-executable proxy) | `{referenced_docs}`: list with `[INLINED]` tag. `{inlined_context}`: full verbatim text under header `### {doc_name} — full text` with source path |
| **Inline excerpts** | Doc is larger than the trivial threshold AND relevant excerpts are a moderate portion of the doc (guideline: ~15-20% of line count is comfortable; exceed when a coherent excerpt genuinely requires more — this is guidance, not a hard cap) AND orchestrator has the doc loaded (or chooses to load it now) | `{referenced_docs}`: list with `[INLINED]` tag. `{inlined_context}`: each verbatim excerpt under header `### {doc_name} — {section label}` with source path + section reference |
| **Full read by sub-agent** | Inlining would defeat the purpose (slices approach the doc's whole content), OR aggregate inlined excerpts across all docs for THIS dispatch would exceed ~3K lines (per-dispatch sub-agent context cap), OR orchestrator chooses not to load the doc | `{referenced_docs}`: list with `[FULL READ]` tag. No entry in `{inlined_context}` for this doc. |

The orchestrator measures by line count (not tokens) — agents have no token counter at runtime. The 15-20% guideline exists because slices that large stop saving meaningful sub-agent context; treat it as a hint, not a rule, and let orchestrator judgment adapt to the actual doc structure.

### List Format for `{referenced_docs}`

Format each referenced doc as a bullet:

```
- **{doc_name}** (`{doc_path}`) — `[INLINED]` or `[FULL READ]`
```

Example:

```
- **Architecture Spec** (`./second-brain-os-architecture.md`) — `[INLINED]`
- **External API Reference** (`./api-reference.md`) — `[FULL READ]`
```

If no docs need inlining for a dispatch, set `{inlined_context}` to the literal string `NONE`.

### Always-Full-Read

**Plan, shape, and orchestration-state are NOT subject to this rule** — they are always read in full by the sub-agent. They are small (shape per its template's append-only rules; plan and orchestration-state by design) and authoritative; re-read cost is negligible.

### Orchestrator Context Budget

Inlining shifts read-cost from sub-agents to the orchestrator. The orchestrator carries inlined content in its own context across many dispatches; without discipline this becomes the system's bottleneck.

- Hold no more than ~3-4 referenced docs in working context at once
- When dispatching to a phase that needs different docs than the prior phase, drop no-longer-needed docs from active reasoning before loading new ones
- If a single doc is too large to hold AND too broad to excerpt, default to `[FULL READ]` — do NOT load it into orchestrator context at all
- Eagerly load a doc only when ≥3 batches across the plan will need it AND it's < ~5K tokens; otherwise lazy-load at dispatch time

### Reviewer Dispatches

Reviewer dispatches default to `[FULL READ]` for any doc whose compliance is part of the phase's review criteria — narrow excerpts that satisfied the executor can hide spec violations the executor missed. The reviewer's compliance role requires broader context than the executor's task-completion role.

### Self-Serve Fallback

If inlined excerpts don't cover what a sub-agent needs mid-task, the sub-agent MUST escalate via the doubt-escalation chain (Step 2: sonnet doc-reader). Sub-agents must NOT silently re-read the full source of an `[INLINED]` doc — that defeats the inlining and burns the token budget twice. The doc-reader is the only sanctioned path to additional context beyond what the orchestrator inlined.
