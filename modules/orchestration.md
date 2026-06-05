# Orchestration

## Purpose

The long-horizon work module — creating structured plans, executing them through tiered sub-agents, keeping plan context lean, and mining long sources the orchestrator can't read directly. These components make multi-session, multi-agent work repeatable: a plan written today runs without the original conversation, and execution is delegated with per-phase review instead of done in one fragile context.

> A general orchestration skill (long-horizon work + model routing, with plan orchestration as a sub-case) is planned for this module — see the rbtv-evolution backlog. The components below move in as-is; their redesign lands with that task.

---

## Components

### `rbtv-planning`

- **What**: Interactive workflow that produces a complete, self-executing plan — a main plan file, a scope document (`shape.md`), a learnings log, an artifact index (`deliverables.md`), and individual micro-step task files for each action. Each micro-step file contains complete execution instructions so the plan runs without the original conversation context. Tasks set to `human_review: required` (and every checkpoint task) instruct the executor to emit a Human Review Presentation block at completion: a list of evidence-anchored items the user should review first, plus red and yellow flags drawn from concrete criteria — never free-associated, with an explicit "None identified" affirmation when no flag triggers fire.
- **When to use**: Any multi-step task where you want a structured output you can hand off to another agent session, delegate to a teammate, or return to later. Good for projects, feature builds, operational rollouts, or anything with more than 3–4 sequential decisions.
- **How to invoke**: Say "create a plan for X" or "let's plan this out" — Claude picks up the trigger automatically. You can also say `rbtv-planning` directly.
- **Inputs / outputs**:
  - Input: task description, gathered conversationally across 4 guided steps
  - Output: `{plan-name}-plan.md`, `shape.md`, `learnings.md`, `deliverables.md`, and `phase-N/pN-X.task.md` micro-step files in a folder at the confirmed output path
- **Example**: "Create a plan for migrating our CRM to HubSpot" → Claude walks through scope, phases, and task granularity, then writes all files.

---

### `rbtv-plan-orchestration`

- **What**: Orchestrates execution of a multi-step **non-code** plan by delegating phases to tiered sub-agents, dispatching a reviewer per phase that fixes issues in place, and routing sub-agent doubts through a chain (re-read shape → sonnet doc-reader on referenced docs → halt to user). Per-batch executor model is assigned by a decision tree: **haiku** for mechanical work (explicit list, deterministic transformation, diff-verifiable, no judgment, single-skill rule chain); **sonnet** for enumerated cases — doc-reader role, reviewer of haiku batches, bulk per-item content work with local judgment, and naming judgment; **opus** by default for everything else. Reviewer model is one tier above the highest executor in the phase, floor `sonnet`, never haiku. The orchestrator never executes plan tasks itself — it only reads the plan, batches tasks, assigns models, dispatches agents, surfaces escalations, and optionally suggests clean phase-boundary context refreshes that resume from `orchestration-state.md`.
- **When to use**: A written multi-step plan exists for non-code work — vault refactors, content migrations, doc workflows, structural reorganizations. **Not for code work** — use `superpowers:subagent-driven-development` for code plans (it provides per-task spec/quality review, TDD, and git worktree integration this skill does not). Not for single-step tasks.
- **How to invoke**: "Orchestrate this plan", "execute this plan with sub-agents", or `rbtv-plan-orchestration` directly. Pre-flight asks two questions: (a) confirm orchestration vs direct execution, (b) run mode — `halt`, `end-to-end`, or `autonomous`. Step-02 presents the full delegation map, model assignments, reviewer timing, and refresh candidates. Default context refresh mode is `suggest`: the orchestrator asks only at approved clean phase boundaries whether to continue or pause for a fresh orchestrator. User MAY disable refresh prompts or override model assignments by explicit instruction.
- **Inputs / outputs**:
  - Input: path to a multi-step plan, optional shape.md, run-mode preference, context-refresh preference, optional explicit model overrides
  - Output: in-place execution of the plan via sub-agents, `orchestration-state.md` as the mutable orchestration log/resume artifact, plus a final message per `templates/finalization-message-template.md`
- **Example**: "Orchestrate `1. Projects/second-brain-evolution/sb-os-cleanup/`" → pre-flight gate confirms scope and checkpoint mode → orchestrator batches each phase's tasks and assigns model tiers → executors run batches sequentially at their assigned tier → reviewer audits and fixes each phase at one tier above → final summary on completion.

---

### `/rbtv-plan-shape-compact`

- **What**: Reviews a plan `shape.md` and compacts it in place so it contains only decisions, findings, constraints, unresolved questions, and required references for future execution agents. It removes routine work logs, stale progress notes, duplicate context, and process chatter.
- **When to use**: A plan shape has grown context-heavy or mixes "what happened" with information that actually changes future execution.
- **How to invoke**: `/rbtv-plan-shape-compact` — provide a `shape.md` path or a plan directory.
- **Inputs / outputs**:
  - Input: path to `shape.md` or a plan directory containing `shape.md`
  - Output: approved in-place rewrite of the shape document, after a review summary and user confirmation
- **Example**: `/rbtv-plan-shape-compact 1-projects/my-plan/shape.md` → Claude classifies entries as keep/drop/rewrite, presents compaction risk, then applies the approved compacted shape.

---

### `/rbtv-digest`

- **What**: Processes a long source (conversation export, transcript, book chapter, long document) that the orchestrator Claude cannot read directly due to context limits. It chunks the source, dispatches sub-agents to extract decisions or concepts from each chunk, groups the results, and synthesizes them into either a **reconciled document** (updates an existing doc with session decisions + user line-comments) or a **study note**. The orchestrator never reads the source — only sub-agents do.
- **When to use**: You have a long conversation or document you want to mine for decisions, incorporate into an existing spec, or turn into study notes. Especially useful after long planning sessions where you want to update a PRD or plan with what was decided.
- **How to invoke**: `/rbtv-digest` — Claude asks for source path, mode (reconcile or study), and target document.
- **Inputs / outputs**:
  - Input: source file path, mode selection, target document(s) for reconcile or destination for study
  - Output (reconcile): target document(s) updated in place + a delta document per target showing what changed
  - Output (study): new study note at confirmed destination
- **Example**: `/rbtv-digest` → "reconcile" → point to a long strategy conversation → point to your current strategy doc → Claude mines the conversation and updates the doc with decisions made, showing a diff.

---

## How They Fit Together

`rbtv-planning` writes the plan → `rbtv-plan-orchestration` executes it through tiered sub-agents with per-phase review → `/rbtv-plan-shape-compact` keeps the plan's shape.md lean between sessions → `/rbtv-digest` mines the long conversations that planning and execution produce, folding decisions back into the plan or PRD.
