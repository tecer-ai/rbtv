# Orchestration

## Purpose

The long-horizon work module — creating structured plans, executing them through tiered sub-agents, keeping plan context lean, and mining long sources the orchestrator can't read directly. These components make multi-session, multi-agent work repeatable: a plan written today runs without the original conversation, and execution is delegated with per-phase review instead of done in one fragile context.

---

## Components

### `rbtv-orchestrating`

- **What**: The general orchestration capability — one skill that routes any body of multi-agent work, of any work type (code included), to the right worker; dispatches each task as a self-contained artifact with a three-file state spine; verifies every return against disk (the message is a hint, the repo is the truth); and recovers from halts, worker deaths, and return drift without losing work or improvising decisions. Shaped as a thin `SKILL.md` loader → an always-loaded `core-protocol.md` (the invariants, the situation table, and the installed-model capability summary) → JIT `cards/` opened only when their situation arises. It is the single front door for orchestration: from an all-night multi-agent build down to one minimal-ceremony dispatch to a named CLI model. Model packages are doc packages it loads (see `models/` once populated), never separate skills.
  - **Core protocol** (`core-protocol.md`, always loaded): the invariants every run obeys (never execute the work yourself; no dispatch without a self-contained task artifact + state spine; disk = truth, verify every return; halts are the loop, never blind-retry; evidence must be plausible; budget question at every intake; ask-the-user taxonomy; adaptive brain floor; depth cap ≤ 2), the situation table that maps each run situation to its card, and a one-line capability summary per installed model package (with an installer-baked availability line).
  - **Cards** (`cards/`, opened JIT per the situation table): `intake.md` (entry door selection, spine init, the one pre-AFK question round — budget, code-backend, run mode), `routing.md` (boundedness → stakes → budget tree, pinned-role floors, topology + depth cap, sdd/research/haiku leaves, batching), `dispatch-wrapper.md` (header+payload packaging, binding addendum, the unified five-field return schema, tripwire field checks — also the generated-source template rendered into each model's CLI manual), `halt-recovery.md` (Halt→Decide→Resume, the L1/L2/L3 recovery ladder, doubt-escalation chain, red-sets, precondition override, USER-EXECUTED-ONLY handover), `verification.md` (return gate, review gates with pre-flagged briefs, the cold verifier at feature boundaries, debug roles, conductor-executed exit probes, and run finalization — the exit scorecard, honest completion status, and verbatim surfacing of every Human Review block), `state.md` (the three-file spine semantics, registrar discipline, propagation, the dual-write rule).
  - **Templates** (`templates/`): `run-log-template.md` (the append-only audit log instantiated at spine init) and `state-capsule-template.md` (the mutable, atomic-overwrite resume state).
  - **Model packages** (`models/`, read JIT — not installed, resolved from `{rbtv_path}`): the capability-manifest schema (`models/manifest-schema.md`) defining the machine-readable manifest every model package ships and how the routing card consumes it (installed-manifests-only, folder presence = availability, routes on `(model, variant)` pairs), plus its fill-in template (`models/manifest-template.yaml`). Manifests are YAML (agent-read, like the cards) — the routing card's data interface. Per-model packages (`models/{model}/` with manifest, `delta.md`, rendered manual, mirror config) populate this folder during the model-package build — **`models/kimi/`** is the first real package (the validated bounded-code executor; it also carries the runtime Kimi contract that the M3 mandate's never-built `_shared/kimi-code-execution/` was to hold — task spec, invocation shapes, exit-75 recovery, guardrails, swarm — so a runtime orchestrator reads the package, never the human-facing kimi-cli-reference). Each manual is GENERATED, never hand-edited: `models/render-manuals.py` composes the generic dispatch contract (`cards/dispatch-wrapper.md` RENDER blocks) with each package's `delta.md` into `models/{model}/manual.md`, stamped with a DO-NOT-EDIT banner (`python orchestration/models/render-manuals.py`; `--check` reports drift). A protocol change is edited in the template or a delta and re-rendered — re-render with no input change is zero-diff. The mirror machinery (`models/mirror/mirror.py`, vault-agnostic; convention in `models/mirror/mirror-config.md`) generates/refreshes a model's per-workspace guidance file (`AGENTS.md` for kimi/codex, `CLAUDE.md` for claude-cli) in a target workspace from a per-package `models/{model}/mirror-config.yaml`, stamped with a DO-NOT-EDIT banner; idempotent, with `--check` reporting create/in-sync/stale — the capability the routing card's pre-dispatch guidance-file check offers to invoke when a target workspace lacks the worker's guidance file.
- **When to use**: Any work that needs coordinated dispatches — executing a multi-step plan through workers, running a goal end-to-end, a long-horizon/AFK build, multi-worker or cross-repo coordination, or dispatching a CLI model (kimi, codex, claude-cli, qwen). Also the front door for a single standalone dispatch to a named model ("use kimi for X"). The orchestration module rule owns the discoverability trigger bar and mid-task escalation.
- **How to invoke**: Say "orchestrate this", "run this end-to-end with workers", "use kimi/codex/claude-cli/qwen for X", or `rbtv-orchestrating` directly. The skill loads its core protocol and follows the situation table from there.
- **Inputs / outputs**:
  - Input: a plan (with its companion artifacts) OR a goal prompt; the run's budget answer, code-backend choice, and run mode (gathered in one pre-AFK round at intake)
  - Output: coordinated worker dispatches with per-return verification and per-boundary review/cold-verification, a three-file state spine (`run-log.md` / `state-capsule.md` / `decisions.md`) that makes the run resumable across sessions, and the delivered work itself

---

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

## Shared Components

### Shared Authoring Core

- **What**: A single source of artifact-authoring knowledge at `orchestration/workflows/_shared/authoring/`, consumed by BOTH the interactive `rbtv-planning` workflow and orchestration intake writer agents so both doors produce identical artifact contracts. It owns: the task-file contract (zero-context self-containedness, file-operation verbs, allowlists, context budgets, owner-observable acceptance criteria, and the per-model contract plug-in seam), a behavior-spec + embedded test-plan template for code work, a complexity rubric (Dependencies and Decision Density widened beyond the 1–3 scale to match observed coordination/decision load) that routes a body of work to its entry door, dependency-ordering rules with shared-file serialization, and the worker-facing `decisions.md` entry discipline (decision/rationale/scope only; append-don't-rewrite; size floor on rewrites).
- **When to use**: Read by planning and intake when authoring task files, specs, and dependency-ordered plans — not invoked directly by users. It is authoring KNOWLEDGE (what an artifact must contain, how to size/order/discipline it), distinct from workflow MECHANICS (step sequencing, plan-document structure), which stay in the consuming workflow.
- **Inputs / outputs**: Input — a body of work to author artifacts for. Output — task files, specs, and orderings that satisfy one shared contract regardless of which workflow or which executor model produced or runs them.

---

## How They Fit Together

`rbtv-orchestrating` is the general front door for long-horizon, multi-agent work — it ingests a plan or a goal, routes each task to the right worker, and gates every return; `rbtv-planning` writes the plans it ingests. `rbtv-plan-orchestration` is the earlier non-code plan executor (tiered sub-agents, per-phase review) that the general skill supersedes; it remains installed while the general capability's surgery completes. `/rbtv-plan-shape-compact` keeps a plan's shape lean between sessions, and `/rbtv-digest` mines the long conversations that planning and execution produce, folding decisions back into the plan or PRD.
