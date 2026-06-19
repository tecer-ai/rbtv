# Orchestration Planning (JIT)

Orchestration-only planning knowledge. Loaded ONLY when a plan is `orchestrated: true` — read at the first orchestration touchpoint (step-02 §4a) and held in context for step-03 §6c and step-04. A plain interactive plan never loads this file. The authoring core that every plan needs is `plan-creation-rules.md`; this file carries the layer that fires only under orchestration.

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

DEEP mode generalizes the validated Kimi-aware pre-resolution list (`4-archives/executed/rbtv/orchestration-build/plan-design/kimi/cp-workflow-rbtv-kimi-planning-orchestration.md` §B3, M1/M2) to any worker. Resolve each item WITH the user and emit it so the router reads FIELDS, never re-derives them. The consuming interface is the routing card (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md`) — match what it reads:

| Pre-resolution item | Where it lands | Router/orchestrator consumes it as |
|---------------------|----------------|------------------------------------|
| **Per-task executor (model, variant)** | Task frontmatter | The pin is resolved by CALLING `route.py` (routing card §2a) over the task's profile — the SAME router the conductor calls at run time, so plan-time and run-time routing can never disagree (locked: ONE script, NO LLM middleman). A `halt_seam` verdict is resolved WITH the user. The orchestrator then reads the assigned (model, variant) rather than re-scoring it |
| **Per-task reviewer pin** | Task frontmatter | The reviewer-floor pin (routing §3) is pre-named; orchestrator enforces, does not pick |
| **File allowlist per task** | Task frontmatter + body (✚ create / ✎ modify / ✗ delete) | The dispatcher's post-run diff-vs-allowlist contract (task-file-contract §4) |
| **Validation commands per task** | Task body (exact command + expected EXIT) | The return-gate tripwire checks (verification card §1b) |
| **Batching / serialization order** | Plan body — per shared file (`fileX: T5→T7`) and parallel-wave grouping | The routing card's batching + shared-file serialization (routing §8); dependency-ordering's serialization check |
| **Hard-halt registry** | Plan body — the checkpoints non-overridable in autonomous mode | The orchestrator reads the list directly; autonomous mode never overrides them |

LIGHT mode emits only the critical subset the user chooses to resolve; the rest are left model-bound-at-routing-time (the task is authored to the generic contract and the router scores boundedness as usual). Both modes still author every task to the **shared task-file contract** (`{rbtv_path}/orchestration/workflows/_shared/authoring/task-file-contract.md`) — orchestration-awareness adds the pre-resolution fields, it does not replace the contract.

**Worker-contract frontmatter for a pinned executor.** When the router pins an executor whose model ships a per-model contract delta (kimi, claude-cli, codex, qwen, …), the generated task file's frontmatter + body MUST satisfy that model's contract. The operative procedure — dispatch-scaffold skeleton mode, pre-flight STOP on an uninstalled model package, merge of the derived skeleton — is owned by § Worker-Contract Frontmatter for a Pinned Executor (step-04 body) below; follow it there, it is not restated here.

---

## DEEP-Mode Pre-Resolution (step-03 §6c body)

If step-02 set `orchestrated: true` with **DEEP** mode, resolve the pre-resolution set WITH the user and plan where each field lands so the router reads fields, never re-derives them (§ Orchestration-Aware Modes — DEEP-mode pre-resolution set):

- Per-task **executor (model, variant)** and **reviewer pin** → task frontmatter
- Per-task **file allowlist** (✚/✎/✗) and **validation commands** (+ expected EXIT) → task frontmatter/body
- **Batching / serialization order** per shared file and parallel-wave grouping → plan body
- **Hard-halt registry** (checkpoints non-overridable in autonomous mode) → plan body

**Pin the per-task executor by CALLING the router — never reason it WITH the user.** The executor `(model, variant)` is a deterministic pure function of the task's profile, NOT a judgment pick. For EACH task: assemble its JSON task profile (`boundedness`, `task_type`, `inlined_context_size`, plus the optional fields the leaf needs — `stakes`/`stakes_tier`, `cross_strategy`, `needs_process_boundary`, `reviews_external_cli_code`, `delegation_map_allows_haiku`) and call `route.py` — the SAME router the conductor calls at run time, so plan-time and run-time routing can never disagree (locked: ONE script, NO LLM middleman). The router CLI, profile field set, and verdict shapes are in the routing card (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md` §2a) — call it as that card names; do NOT restate the algorithm here. Record the returned `(model, variant)` as the task's `executor` pin; the reviewer pin (router-derivable too — floor sonnet, ≥ executor+1) lands the same way. A `halt_seam` verdict (`stakes` or `cross-strategy`) is a genuine judgment seam — resolve it WITH the user, as today, then re-run; never let the script decide it.

**Emit `known_input_size` for known-corpus tasks.** When a task's required read-set is an enumerable `[FULL READ]` allowlist (every file to be read is named up front — a known corpus), the planner MUST measure that read-set and emit `known_input_size` in the task-profile JSON alongside `inlined_context_size`, so the router GATE (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md` §2a) receives the total known input and can size the worker correctly.

Measurement procedure (MUST follow exactly):

1. For each file in the named read-set, run: `python {rbtv_path}/orchestration/workflows/source-mining/scripts/slice.py --inspect --source <file>` — the first output line prints `total_chars: <N>`. Sum `total_chars` across all files.
2. Add the dispatch-prompt character count to that sum.
3. Convert to tokens: `known_input_size = ceil(total_chars / 3)` — divide by 3, round UP (ceiling). The result MUST be a clean positive integer.
4. Emit `known_input_size` in the task-profile JSON at the same location as `inlined_context_size`. The router reads it via `.get` (it is optional, not a required field).

An **open-ended** task — one whose read-set is NOT enumerable up front — MUST NOT emit `known_input_size`. The existing boundedness scope already routes open-ended tasks to the largest worker; there is no `footprint_class` sentinel.

**LIGHT** mode resolves only the critical subset the user chooses; the rest stay model-bound-at-routing-time. The router call is available in LIGHT for any task the user elects to pre-pin. A plain (non-orchestrated) plan — or a workspace without the orchestration module installed — skips this step and the router call entirely; the task is authored to the generic contract and bound to a worker at routing time. HALT discipline is mode-independent in every case.

---

## Task-Frontmatter Pre-Resolution (step-04 body)

**Orchestration pre-resolution frontmatter (conditional).** When the plan is `orchestrated: true` and step-03 §6c resolved the pre-resolution fields for this task (DEEP mode, or the critical subset under LIGHT), add them to the task frontmatter so the router reads fields rather than re-deriving them: `executor: {model, variant}`, `reviewer: {pin}`, and the file allowlist (✚ create / ✎ modify / ✗ delete — repeated in the body per the task-file contract). A plain (non-orchestrated) plan omits these — the task is bound to a worker at routing time. See § Orchestration-Aware Modes.

---

## Worker-Contract Frontmatter for a Pinned Executor (step-04 body)

**Worker-contract frontmatter for a pinned executor (conditional).** When a task's `executor` pin names a model that ships a per-model contract delta (kimi, claude-cli, codex, qwen, …), the generated frontmatter AND body MUST satisfy that model's Required-frontmatter and Required-body-sections — so a plan-time pin and the run-time dispatch can never disagree about the contract the worker is held to. Do NOT hand-copy a model's skeleton: obtain it by calling the dispatch-scaffold generator in **skeleton mode** (the run with NO `--instructions`), which DERIVES the per-model frontmatter keys + body-section headers from that model's delta on disk. The scaffold CLI, its skeleton-vs-complete modes, and its pre-flight gates live in its spec — call it as the spec names; do NOT restate the contract here. Merge the scaffold's derived skeleton into this task file, then fill the task-specific values (Goal/Context/Implementation/allowlist). A pin whose model package is NOT installed → the scaffold's pre-flight fails: flag it at generation time and STOP; NEVER silently emit generic frontmatter for a worker whose real contract you could not derive. A workspace without the orchestration module installed has no scaffold and no per-model deltas — such a plan carries no executor pin (step-03 §6c skipped), so this step does not fire.

---

## Orchestration Pre-Resolution Frontmatter Shape (microstep template)

```yaml
# Orchestration pre-resolution fields (ONLY when orchestrated: true and step-03 §6c resolved them — DEEP, or the LIGHT critical subset). Omitted on a plain interactive plan.
executor: { model: {model}, variant: {variant}, carrier: {carrier} }   # router-pinned (route.py) — NOT reasoned with the user
reviewer: { model: {model}, variant: {variant} }                       # reviewer pin: ≥ executor+1, floor sonnet, never haiku
allowlist:
  create: []
  modify: []
  delete: []
```

**Orchestration pre-resolution shape:** `executor`/`reviewer`/`allowlist` are the standing pre-resolution frontmatter the planner emits for an orchestrated DEEP plan (and the LIGHT critical subset). `executor.{model, variant, carrier}` is the router pin (resolved by calling `route.py`, never reasoned with the user); `reviewer.{model, variant}` is the reviewer-floor pin; `allowlist.{create, modify, delete}` is the file-operation allowlist (✚/✎/✗ — also restated in the body per the task-file contract). When the executor pin names a model that ships a per-model contract delta, the model-specific frontmatter keys + body sections are DERIVED from that delta via the dispatch-scaffold in skeleton mode — see § Worker-Contract Frontmatter for a Pinned Executor (step-04 body). A plain (non-orchestrated) plan omits all three blocks.

---

## Create-Coverage Validation (step-04 §8d body)

**Orchestrated plans only.** Before plan handoff, reconcile what the plan DECLARES it will create against what the task allowlists ACTUALLY create — so a file intended-but-unscoped surfaces here at plan time, not at a wave boundary during execution.

1. Build `INTENDED_CREATE` — every file the plan declares it will create:
   - deliverables.md rows whose artifact is a newly-created file, AND
   - every create-annotation carried by any design/architecture doc the plan references (a file marked create-for-`taskN`, e.g. `✚ CREATE (taskN)`), when such a doc exists.
2. Build `ALLOWLIST_CREATE` — the union of every task's `allowlist.create`.
3. Assert `INTENDED_CREATE ⊆ ALLOWLIST_CREATE`. Any file in `INTENDED_CREATE` absent from `ALLOWLIST_CREATE` is a **coverage gap** — a validation error surfaced before handoff, never deferred to execution.
4. For each create-annotation that names a SPECIFIC task (`✚ CREATE (taskN)`), assert that task's OWN `allowlist.create` includes the file — not merely some task's.
5. Reconcile every gap before the plan is handed off: add the file to the owning task's allowlist, or add/re-scope the task that creates it.
