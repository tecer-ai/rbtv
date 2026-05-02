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

For each batch, run this decision tree IN ORDER. Stop at the first match. When in doubt at any tier boundary, bump to the next tier — silent flawed work costs more than expensive tokens.

**Step 1 — Haiku.** Assign `haiku` ONLY if ALL of these hold:

| Criterion | Required |
|-----------|----------|
| Input | Explicit list, fully enumerated upfront — no discovery required |
| Transformation | Deterministic — renames from a convention, find/replace from explicit map, frontmatter add/remove from known schema, ref rewrite from a known map, index regen from a directory listing, checkbox/status flips |
| Verifiability | Success is verifiable by diff or a script |
| Judgment | NO design, routing, naming, or categorization judgment |
| Rule chains | Mechanical multi-skill chains are allowed when prescribed (e.g., `sb-vault-ops` edit + `sb-vault-integrity` post-op sweep). Chains involving routing, design, or naming judgment disqualify haiku. |

If any criterion fails, do NOT assign haiku — drop to Step 2.

**Haiku failure modes — bump to sonnet if ANY apply:**

| Failure mode | When it bites |
|--------------|---------------|
| Markdown edge cases | Paths in code blocks, escaped chars, nested quotes, `<details>` tags, glob patterns that look like paths |
| Cross-platform quoting | PowerShell heredocs, Unicode in commit messages, escape sequences, stdin piping |
| Cross-file inference | Determining "what counts as related" across multiple files |
| Reviewer role | Haiku reviewing haiku is too tight a feedback loop — reviewer floor is sonnet |
| Partial-input risk | Input list might be incomplete and missing items would not be flagged |
| Long-context multi-file coordination | Context drift across many files in one batch |

**Step 2 — Sonnet.** Assign `sonnet` ONLY if the batch matches one of the enumerated cases AND passes ALL THREE eligibility gates.

Enumerated cases:

| # | Case | Notes |
|---|------|-------|
| a | Doc-reader sub-agent | Pure extraction role, no decisions (already locked in step-03's doubt-escalation chain — orchestrator does not assign this directly) |
| b | Reviewer for a haiku-executor batch | One tier above haiku; mechanical work doesn't need opus review (assigned automatically in step-03 — orchestrator does not list this in the delegation map) |
| c | Bulk per-item content work | Explicit pattern + explicit input list + per-item judgment is local (item N doesn't depend on item N-1) + no cross-item design |
| d | Naming APPLICATION from explicit glossary/convention | Applying naming rules — NOT designing new naming systems |

Eligibility gates — ALL THREE must hold (any fail → opus):

1. **Verification is cheaper than production.** A reviewer can confirm correctness in less work than the executor did. If verification needs the same judgment as production, opus.
2. **Silent error is bounded and reversible.** A bad outcome shows up in diff/test/lint, not as quiet drift across files. If silent error is irreversible or invisible, opus.
3. **Input is fully enumerated OR enumeration is itself trivially verifiable.** No "find all the X" where missing one is dangerous. If discovery is part of the work, opus — or split into a haiku-discovery + sonnet-action two-batch sequence.

If no case matches OR any gate fails, drop to Step 3.

**Sonnet failure modes — bump to opus if ANY apply:**

| Failure mode | When it bites |
|--------------|---------------|
| Irreversible categorization | Archive vs. delete, "user content vs. sb-os content", "is this a learning or a discovery" |
| Cross-batch coordination | Batch N's choice constrains batch M — each batch looks fine in isolation, system is broken |
| Plan-flagged uncertainty | "TBD", "decide later", "judgment call needed" — sonnet resolves silently rather than escalating |
| Novel naming SYSTEMS | Inventing conventions vs. applying them — sonnet picks plausible-sounding without seeing tradeoffs |
| Schema design | Frontmatter schemas, manifest schemas |
| Marker-block content | What belongs inside vs. outside, canonical wording — touches sb-os contract |
| Reviewer of a sonnet or opus batch | Reviewer needs equal-or-greater capability than executor |
| Ambiguous-input disambiguation with high stakes | Sonnet picks one valid reading without flagging the choice |
| Long multi-file refactor where step N depends on subtle insight from step N-3 | Context drift; mistakes compound silently |

**Step 3 — Opus.** Default. Assign `opus` for everything else, including:

- Design judgment, structural decisions, novel naming systems
- Multi-file refactors with undefined boundaries
- Plan-flagged uncertainty (anywhere the plan/shape says "TBD", "decide later", or similar)
- Cross-cutting work where one batch's choices constrain another
- Any batch flagged by the haiku or sonnet failure-mode tables above

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
