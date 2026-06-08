# Plan Creation Rules

Knowledge file for plan creation workflow. These rules ensure consistent, high-quality plans.

---

## Macro Workflow for Plan Creation

The process for creating any plan:

| Step | Action | Output |
|------|--------|--------|
| 1 | Gather requirements from user | Clear understanding of goals and constraints |
| 2 | Assess complexity (shared widened rubric) | Complexity band, door, and task sizing guidance |
| 3 | Draft plan structure | Phase breakdown with task IDs |
| 4 | Apply dependency ordering | Tasks ordered by prerequisites |
| 5 | Author specs for code work (conditional) | One behavior-spec + test-plan file per code feature, from the shared spec template (see Spec Authoring below) |
| 6 | Create plan file | `{plan-name}-plan.md` from template |
| 7 | Create or merge decisions.md | Check for existing decisions.md (from context preservation rule); merge planning context if exists, create from the decisions template if not |
| 8 | Create learnings.md | System improvement queue |
| 9 | Generate micro-step files | `.task.md` file per complex task and per checkpoint |
| 10 | Create deliverables.md | Artifact index — one `pending` row per task |

---

## Complexity Assessment

Score the plan with the **shared widened complexity rubric** — the single source for axes, bands, and doors: `{rbtv_path}/orchestration/workflows/_shared/authoring/complexity-rubric.md`. Read it and apply it directly; this section does NOT restate the axes or thresholds (they live in the rubric, and a second copy here would drift).

What the rubric gives you:

- Five axes (Context Size, Tool Usage, Human Review at 1-3; Dependencies at 1-4; Decision Density at 1-5), summed to a band over the 5-18 range.
- Bands map to doors: **5-8 Simple** → conductor-led prep / single-step tasks OK, fewer micro-step files; **9-13 Moderate** → standard granularity, full micro-step files; **14-18 Complex** → fine-grained tasks, research-first pattern, interactive planning.
- Doors are ALWAYS user-overrideable.

Task-sizing impact by band: Simple may skip micro-step files for trivial tasks; Moderate gets a standard micro-step file per task; Complex considers a research phase and splits large tasks (Context Budgeting below).

---

## Orchestration-Aware Modes

A plan MAY declare that it **will be orchestrated** — executed under an orchestration skill that dispatches its tasks to tiered workers rather than run interactively by one agent. The plan's frontmatter carries `orchestrated: true` when so. **The flag does NOT force orchestration** — the orchestration rule's own triggers decide whether a run is orchestrated; a flagged plan is one such trigger, not a command. A plan with no flag is a plain interactive plan and this whole section is skipped.

When `orchestrated: true`, ask the user ONE question at step-02: **DEEP or LIGHT pre-resolution.** The answer sets how much gets resolved WITH the user at planning time versus left to the workers' latitude.

| Mode | What gets resolved at planning time | When to choose |
|------|-------------------------------------|----------------|
| **DEEP** | EVERY foreseeable doubt is resolved WITH the user, up front — long, for complex/important plans. The plan emits the full pre-resolution set below in the form the router consumes. | High-stakes, irreversible, or decision-dense work; an all-night AFK run where a mid-run halt is expensive. |
| **LIGHT** | The user resolves only the CRITICAL questions; workers get latitude on the rest, halting to the user when they hit a hard question. | Lower-stakes or well-trodden work where over-resolution is wasted ceremony. |

**HALT discipline is mode-independent.** Even a fully DEEP-resolved plan halts to the user on hard questions outside full-auto — DEEP reduces the EXPECTED number of halts, it does not forbid them. A LIGHT plan halts more often by design. Neither mode removes the worker's obligation to halt rather than guess.

### DEEP-mode pre-resolution set (emit in router-consumable form)

DEEP mode generalizes the validated Kimi-aware pre-resolution list (`1-projects/rbtv-evolution/orchestration/kimi/cp-workflow-rbtv-kimi-planning-orchestration.md` §B3, M1/M2) to any worker. Resolve each item WITH the user and emit it so the router reads FIELDS, never re-derives them. The consuming interface is the routing card (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md`) — match what it reads:

| Pre-resolution item | Where it lands | Router/orchestrator consumes it as |
|---------------------|----------------|------------------------------------|
| **Per-task executor (model, variant)** | Task frontmatter | The routing card's boundedness leaf is pre-answered — the router reads the assigned (model, variant) rather than scoring it |
| **Per-task reviewer pin** | Task frontmatter | The reviewer-floor pin (routing §3) is pre-named; orchestrator enforces, does not pick |
| **File allowlist per task** | Task frontmatter + body (✚ create / ✎ modify / ✗ delete) | The dispatcher's post-run diff-vs-allowlist contract (task-file-contract §4) |
| **Validation commands per task** | Task body (exact command + expected EXIT) | The return-gate tripwire checks (verification card §1b) |
| **Batching / serialization order** | Plan body — per shared file (`fileX: T5→T7`) and parallel-wave grouping | The routing card's batching + shared-file serialization (routing §8); dependency-ordering's serialization check |
| **Hard-halt registry** | Plan body — the checkpoints non-overridable in autonomous mode | The orchestrator reads the list directly; autonomous mode never overrides them |

LIGHT mode emits only the critical subset the user chooses to resolve; the rest are left model-bound-at-routing-time (the task is authored to the generic contract and the router scores boundedness as usual). Both modes still author every task to the **shared task-file contract** (`{rbtv_path}/orchestration/workflows/_shared/authoring/task-file-contract.md`) — orchestration-awareness adds the pre-resolution fields, it does not replace the contract.

---

## Spec Authoring (code work)

**Code-work plans produce a spec before any executor builds.** A spec is a behavior specification with an embedded test plan — authored from the shared spec template, never invented inline here:

> Spec template (the single source): `{rbtv_path}/orchestration/workflows/_shared/authoring/spec-template.md`. Read it and fill it; this section does NOT restate the template's structure.

| Rule | Detail |
|------|--------|
| When to author a spec | The plan (or any phase of it) delivers CODE or executable behavior. A docs-only / vault-content / research plan authors no spec. |
| One spec per feature | A **feature** = one bounded owner-observable behavior. One spec can back several task files; each backing task REFERENCES its spec rather than restating it. |
| Where it lands | Alongside the plan's other artifacts (e.g., `specs/{feature}-spec.md` in the plan folder, or the path the plan's own structure sets) — a deliverables.md row records it. |
| Reference, never copy | The spec is the behavior + acceptance source of truth; task files point at it. Never paste the spec body into a task file. |

The spec template's Test Plan section IS the test plan (D2b unified them — there is no separate test-plan file). Its Fidelity Floor + Evidence Plausibility rules bind every criterion; fill them as the template states.

---

## Task Granularity

| Rule | Description | Example |
|------|-------------|---------|
| WHAT, not HOW | Describe WHAT to achieve; only include HOW if user explicitly decided | ✅ "Implement login form with validation" ❌ "Add email field, then password field, then validation" |
| Single action per task | Each task = one discrete, independently completable action | ✅ "Create component" ✅ "Write tests" ❌ "Create and test component" |
| No compound tasks | Never combine actions with "and" | ✅ Two tasks ❌ "Create file and update imports" |
| Room for judgment | Leave implementation decisions to executing agent unless user specified | ✅ "Implement caching" ❌ "Implement Redis caching with 5-minute TTL" (unless user specified) |
| Explicit file operations | Use CREATE/UPDATE/DELETE/MOVE verbs for file tasks | ✅ "CREATE src/auth.ts with login logic" ❌ "Add authentication" |
| Canonical source only | Tasks must write to canonical source of truth only — replication to workspace locations is an installer responsibility | ✅ "CREATE `_config/claude/rules/rule.md`" ❌ "CREATE rule in both `_config/` and `.claude/rules/`" |

---

## Explicit File Operations

**MANDATORY:** Task descriptions involving files MUST use explicit operation verbs.

| Verb | When to Use | Example |
|------|-------------|---------|
| CREATE | New file that doesn't exist | `CREATE src/components/Button.tsx with props interface and styled component` |
| UPDATE | Modify existing file | `UPDATE src/api/auth.ts to add token refresh logic` |
| DELETE | Remove file | `DELETE src/legacy/oldAuth.ts (replaced by new auth module)` |
| MOVE | Relocate or rename file | `MOVE src/utils/helpers.ts to src/shared/helpers.ts` |

**Format:** `[ACTION] [file-path] [with/to/containing] [content description]`

---

## Plan Linking Standard

**MANDATORY:** All references within plan artifacts follow a linking contract to ensure plan folders can be moved without breaking links.

### Internal Links (within plan folder)

References between files inside the same plan folder MUST use file-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Use `./` or `../` relative to the referencing file | `../decisions.md`, `./phase-1/p1-1.task.md` | ❌ Absolute or root-relative path to own plan folder |
| Task file path references are relative to the plan folder | `phase-1/p1-1.task.md` | ❌ Full path from project root |
| NEVER embed the plan folder's absolute or root-relative path | `../learnings.md` | ❌ `{project-root}/plans/my-plan/learnings.md` |

### External Links (from plan files to outside)

References from plan files to files outside the plan folder MUST use project-root-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Path from project root, no leading `./` | `orchestration/workflows/planning/workflow.md` | ❌ `../../../orchestration/workflows/planning/workflow.md` |
| NEVER traverse up out of the plan folder | `orchestration/workflows/planning/workflow.md` | ❌ `../../../../orchestration/workflows/planning/workflow.md` |

### Inbound Links (from outside referencing a plan)

Documents outside a plan folder that reference plan files MUST use root-relative paths to the plan's current location. When a plan folder moves, update these references via search-and-replace on the old path.

### Validation (pN-refs task)

The `pN-refs` task in every plan's final phase MUST verify:
1. No file inside the plan folder contains a self-reference using an absolute or root-relative path to the plan folder
2. All internal links use `./` or `../` relative paths
3. All external links from plan files use project-root-relative paths

---

## Micro-step File Generation

Rules for creating task files during plan creation.

### When to Generate

| Scenario | Generate Micro-step File? | Instead |
|----------|---------------------------|---------|
| **Complex task:** multi-step, needs context loading, phased execution | **YES** — full microstep file | — |
| **Standard task:** clear scope, single action, no special context | **NO** — inline description is sufficient | Markdown task line contains complete instructions |
| **Checkpoint** | **YES** — contains review criteria and gate instructions | — |

### Decision Criteria

Generate a micro-step file when ANY of these apply:
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (skills, sub-agents)
- Task has 3+ distinct substeps
- Task requires a phased execution flow (understand → execute → validate)
- Task is a checkpoint (review criteria must be documented)

Use inline Markdown task description when ALL of these apply:
- Task is self-explanatory from its description
- Single action, completable in one step
- No special context files or tools needed
- No phased execution flow required

### File Location

```
{output-path}/{plan-name}/phase-{N}/{task-id}.task.md
```

### Generation Rules

1. One file per complex non-checkpoint task (per decision criteria above)
2. One file per checkpoint (contains review criteria)
3. Use `plan-task-microstep-template.md` as base
4. Fill required sections: Goal, Context Files, Execution Flow, Output Requirements
5. Include Tools section ONLY if task requires specialized RBTV skills/sub-agents (not for basic Read/Write/Bash)
6. Include revolving plan rules section
7. Set appropriate complexity_score in frontmatter
8. Link the task file from the Markdown task list: `→ phase-N/task-id.task.md`

---

## Task Ordering

| Rule | Description |
|------|-------------|
| High-value first | Complex, critical tasks at beginning |
| Low-value last | Routine, administrative tasks at end |
| Critical path first | Blocking tasks before non-blocking |
| Dependencies respected | Task B depending on A means A comes first |

---

## Task IDs

| Rule | Description |
|------|-------------|
| Format | `p[phase]-[number]` or `p[phase]-[name]` (e.g., `p1-3`, `p2-auth`) |
| Sync with body | Task IDs in task list must match section headers in plan body |
| Checkpoints | Use `p[N]-checkpoint` with description prefix `CHECKPOINT —` |
| Final tasks | Use `pN-refs`, `pN-compound`, `pN-checkpoint` for final phase |

---

## Plan Body Minimalism

**MANDATORY:** The plan body must not repeat content from decisions.md, micro-step files, or the task list. Reference companion files; do not duplicate them.

| Principle | Enforcement |
|-----------|-------------|
| No content repetition | Context, decisions, constraints live in decisions.md — not the plan body |
| Task list is the execution index | Phase sections state phase goal; task details are in the task list with `→ path` for micro-step files |
| Per-task context in microsteps | Files-to-load tables belong in `.task.md` files, not the plan body |
| Folder structure is discoverable | Agents navigate the filesystem — no need to diagram it in the plan |

## Plan Structure

The plan file uses minimal YAML frontmatter (`name`, `overview`) and a Markdown body:

1. **YAML Frontmatter**: `name`, `overview` only
2. **Reference directive**: Pointers to decisions.md and task files
3. **Architectural Constraints**: Plan-specific patterns and inviolable rules
4. **Revolving Plan Rules**: Discovery handling, task modification (keep brief)
5. **Execution Workflow** *(conditional)*: Mermaid diagram — only for non-linear plans (branching or parallel phases)
6. **Tasks**: Markdown checkbox list grouped by phase, with `→ path` suffix for tasks with micro-step files

---

## Revolving Plan Rules

Plans adapt during execution based on discoveries.

### Discovery Categories

| Type | Action |
|------|--------|
| Simple discovery (<5 min) | Resolve immediately, document in decisions.md |
| Complex discovery (>5 min) | Add new task to plan, document in decisions.md |
| Contradiction with shaping | Document in decisions.md Execution Discoveries, proceed with resolution |

### Task Addition

When adding a task during execution:

1. Choose appropriate phase and task ID
2. Add to the task list in the plan body
3. Create micro-step file in correct phase folder if needed
4. Append discovery entry to decisions.md
5. Add a `pending` row to deliverables.md in the matching phase table
6. Notify user: `PLAN MODIFIED: Added: {task-id} - {description}`

### Task Removal

When removing a task during execution:

1. Mark task with ~~strikethrough~~ in the task list (don't delete)
2. Strike the task's row in deliverables.md (don't delete)
3. Append discovery entry explaining removal
4. Notify user: `PLAN MODIFIED: Removed: {task-id} - {reason}`

---

## Zero-Context Plans

Plans executed by different agents must be self-contained:

| Rule | Description |
|------|-------------|
| No references to "as discussed" | Another agent won't know what was discussed |
| Include all context | Everything needed is in the plan + decisions.md + deliverables.md + microstep files |
| Per-task file references | Each `.task.md` lists its own Context Files table |
| Explain WHY | Document rationale for significant decisions in decisions.md |

---

## Checkpoint Rules

- **Quantity:** 3-6 checkpoints total
- **Placement:** At phase transitions, critical decisions, major deliverables
- **Format:** `p[N]-checkpoint` → `CHECKPOINT — [Description]`
- **Behavior:** Agent evaluates work against review criteria in checkpoint task file, presents findings, then STOPS for human approval
- **Task files:** Every checkpoint gets a `.task.md` file containing specific review criteria composed during planning

### Checkpoint Task File Content

Each checkpoint task file contains:
- **Review criteria** — 3-7 specific criteria derived from the phase's task descriptions, architectural constraints, and acceptance criteria
- **Work to evaluate** — summary of what the phase produced (files created/modified, artifacts delivered)
- **Gate behavior** — present evaluation findings to user, HALT for human approval, do not advance if user rejects
- **decisions.md audit** — audit `decisions.md` against the entry-shape discipline (Decisions-File Discipline below): every checkpoint's review criteria include the audit checklist, and any failure is a finding

The plan creator composes these review criteria at plan creation time, when full phase context is available.

---

## Decisions-File Discipline

The plan's worker-facing `decisions.md` carries SIGNAL that changes future work — never an execution log. The entry-shape rules, the size floor, the reminder line, and the reviewer audit checklist are the single source in the shared authoring core; the planning workflow CARRIES them, it does not re-derive them:

> `{rbtv_path}/orchestration/workflows/_shared/authoring/decisions-discipline.md` — entry-shape rules (decision/rationale/scope only; never file-lists; never N→M narratives; UPDATE-not-REWRITE; routine completions excluded), the ≥50% size floor on rewrites, the Reminder Line, and the reviewer Audit Checklist.

Two surfaces the planning workflow wires:

| Surface | What the plan creator does |
|---------|----------------------------|
| **Reminder line** (generated plans + task files) | Every generated plan and `.task.md` carries the Reminder Line VERBATIM (the microstep template and plan template already embed the `decisions.md` reminder pattern). It reads: `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite. |
| **Checkpoint / review audit** (UPDATE-not-REWRITE + ≥50% size floor) | Every checkpoint task's review criteria include the Audit Checklist above. The checkpoint enforces append-only maintenance: a full-file `decisions.md` rewrite is NOT routine — it requires explicit user sanction AND must retain ≥50% of the prior file's size, preserving all decisions, findings, constraints, open questions, and references. A rewrite below the floor is rejected and the original kept. |

---

## Dependency Ordering

**MANDATORY:** Tasks must be ordered so dependencies complete before dependents. The ordering rules, shared-file serialization, and validity checks are the single source in the shared authoring core — apply them directly:

> `{rbtv_path}/orchestration/workflows/_shared/authoring/dependency-ordering.md` — ordering rules (dependencies first, CREATE before UPDATE, layer by depth, critical-path first, shared-dependencies grouped), shared-file serialization orders, and the four validity checks run before finalizing.

Run those validity checks during step-03; flag and resolve any violation before the structure is confirmed.

---

## Context Budgeting

**Guidance for task sizing:**

| Context Size | Action |
|--------------|--------|
| < 50k tokens | Single task, proceed normally |
| 50-100k tokens | Consider splitting, document reasoning |
| > 100k tokens | MUST split into research + execution phases |

**Research-First Pattern:**
1. Research phase produces summary (~10-20k tokens)
2. Downstream tasks consume summary, not raw sources
3. Reduces context load from ~200k+ to ~20k

---

## Final Phase Tasks

Every plan includes these final phase tasks:

| Task ID | Purpose |
|---------|---------|
| `pN-refs` | File reference review - verify all markdown links resolve and comply with Plan Linking Standard (internal = file-relative, external = root-relative) |
| `pN-compound` | Compound learnings - process learnings.md entries into actionable changes |
| `pN-checkpoint` | Final checkpoint - user approval to complete plan |

---

## Human Review Flag Criteria

Read `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md`.
