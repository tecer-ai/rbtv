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
- Locate any docs the plan references (e.g., architecture docs, requirements docs, specs). Note their paths and approximate sizes (read sizes via file-system query, not by reading content). The orchestrator may load referenced docs lazily during dispatch (step-03) to inline excerpts per the Inlining Reference Document Context rule; otherwise sub-agents consult them via the doubt-escalation doc-reader chain.

If no shape exists, note that. Doubt escalation will skip the "re-read shape" step and go directly to sonnet doc-read.

After reading the plan, scan its Architectural Constraints / Execution Rules section for any rule that contradicts current executor-prompt rules — most commonly: a plan rule instructing executors to append per-task outcomes to shape.md (legacy from before the orchestration-state.md split). If a contradiction is found, STOP. Surface the offending plan text to the user verbatim and ask: (a) update the plan in-place to match current executor-prompt rules, (b) proceed with the plan's rules taking precedence (executor-prompt rules suppressed for this run), or (c) abort. Never silently dispatch under contradictory rules.

### 2. Initialize or Resume Orchestration State

Look for `orchestration-state.md` in the plan's directory. Three cases:

- **If it exists AND conforms to the template** (has Resume Point + Completed Batches sections per `{rbtv_path}/workflows/plan-orchestration/templates/orchestration-state-template.md`): read it. The Resume Point and Completed Batches table tell you where to pick up. Use this to skip already-done work in batching (next step) and dispatch (step-03).
- **If it exists BUT does NOT conform** (different structure, custom hand-curated content, missing required sections, or a `.tmp` sibling exists indicating an interrupted prior write): STOP. Surface the file to the user verbatim and ask: (a) migrate this file's content into the template structure, (b) leave as-is and skip resume logic for this run, or (c) move the existing file aside (rename to `orchestration-state.legacy.md`) and initialize fresh. Wait for user choice. NEVER overwrite a non-conforming file silently.
- **If it does not exist:** copy the template body from `{rbtv_path}/workflows/plan-orchestration/templates/orchestration-state-template.md` to `{plan_dir}/orchestration-state.md`. Fill in the plan name + initial timestamp. Leave Resume Point empty until the first batch dispatches.

This file is the orchestrator's mutable state. NEVER write orchestration state into shape.md (shape is append-only and reserved for planning decisions per the shape template).

### 3. Map Phases to Tasks

Build a private delegation map (in working memory only — do not write to disk):

| Phase | Tasks | Estimated complexity |
|-------|-------|---------------------|
| Phase 1 | task 1.1, 1.2, 1.3 | low / medium / high |
| Phase 2 | task 2.1, 2.2 | ... |

### 4. Batch Tasks (Avoid Micro/Macro Delegation)

For each phase, group tasks into executor batches:

**Avoid micro-delegation:** if 2+ adjacent tasks are small, related, and share context, group them into ONE batch for ONE executor sub-agent.

**Avoid macro-delegation:** if a single task is large, multi-faceted, or touches unrelated areas, split it across multiple batches.

Heuristic:
- 1 batch = 1 sub-agent dispatch
- Batch size target: 30-90 minutes of equivalent human work
- Same batch only if the executor needs the same context to complete the tasks

### 5. Assign Executor Model per Batch

For each batch, run this decision tree IN ORDER. Stop at the first match.

**Step 1 — Haiku.** Assign `haiku` ONLY if ALL of these hold:

| Criterion | Required |
|-----------|----------|
| Input | Explicit list (no discovery required) |
| Transformation | Deterministic — renames, find/replace, frontmatter add/remove, ref rewrite from a known map, index regen from a directory listing |
| Verifiability | Success is verifiable by diff or a script |
| Judgment | NO design, naming, or routing judgment |
| Rule chains | No rule chains beyond a single named skill |

If any criterion fails, do NOT assign haiku — drop to Step 2.

**Step 2 — Sonnet.** Assign `sonnet` ONLY if the batch matches ONE of these enumerated cases:

| # | Case | Notes |
|---|------|-------|
| a | Doc-reader sub-agent | Pure extraction role, no decisions (already locked in step-03's doubt-escalation chain — orchestrator does not assign this directly) |
| b | Reviewer for a haiku-executor batch | One tier above haiku; mechanical work doesn't need opus review (assigned automatically in step-03 — orchestrator does not list this in the delegation map) |
| c | Bulk per-item content work | Explicit pattern + explicit input list + per-item judgment is local (item N doesn't depend on item N-1) + no cross-item design. Loose match — orchestrator may classify as case (c) when the batch fits the spirit of "high volume × local judgment". |
| d | Naming judgment | Batch's main work is choosing names from a convention or glossary, applying naming rules, or selecting identifiers — but NOT designing new naming systems |

If no case matches, drop to Step 3.

**Step 3 — Opus.** Default. Assign `opus` for everything else, including:

- Design judgment, structural decisions, novel naming systems
- Multi-file refactors with undefined boundaries
- Plan-flagged uncertainty (anywhere the plan/shape says "TBD", "decide later", or similar)
- Cross-cutting work where one batch's choices constrain another

### 6. Present Delegation Plan to User

Show a summary table:

| Phase | Batches | Executor model | Reviewer dispatch |
|-------|---------|----------------|-------------------|
| Phase 1 | [N] batches: [brief list] | [model per batch] | After all Phase 1 batches complete |
| Phase 2 | [N] batches: [brief list] | [model per batch] | After all Phase 2 batches complete |
| ... | ... | ... | ... |

Add: "Doubts at any point will halt and surface to you. Confirm to proceed?"

The Model column is for transparency — the approval gate is on batching only, not on model assignments. The user MAY override model assignments by explicit instruction (e.g., "use haiku for the rename phase"); honor the override without re-asking per batch. If the user adjusts batching, update the map and re-present.

Wait for user approval.

### 7. Proceed

On approval, load `./step-03-orchestrate-loop.md`.
