# Card: Routing

Opened when a task is ready to dispatch — once per task (or per batch of like tasks), after intake has put a dispatchable work surface on disk. Routing answers ONE question: which worker — (model, variant, agent-type) — receives this task, under what role pins, in what topology. When it returns an assignment, open the dispatch-wrapper card to package the dispatch.

Iron rules it serves (from the core protocol): **the conductor never executes the work itself** (routing always produces a worker, never "I'll just do this one"), and **disk = truth** (routing reads installed manifests and the live models folder, never assumes a model is present).

**The cross-strategy seam is the least-validated leg of this whole system.** The within-strategy mechanics below (which model for a bounded code task, reviewer pins, batching) are each pilot-validated; choosing BETWEEN whole strategies — CLI fleet vs sdd vs Agent-tool Claude vs a research worker — was never piloted end-to-end. Route it with the explicit judgment discipline in §9, not with false confidence. When the strategy choice is genuinely uncertain, halt and ask — a halt is cheaper than a wrong all-night run.

---

## Sequence

1. Read the installed manifests (what workers exist)
2. Walk the master tree (boundedness → stakes → budget)
3. Apply the pinned-role floor (roles that never route down)
4. Resolve topology (one Agent-tool level; CLI fleets below; depth cap; guidance-file check)
5. Take the right strategy leaf (sdd route · research leaf · haiku clause)
6. Size and batch the dispatch
7. Hand the assignment to the dispatch-wrapper card

---

## 1. Read the installed manifests first (D5)

Routing decides on workers that ACTUALLY exist in this workspace — never on the full roster. Before the tree, resolve availability:

| Step | Action |
|------|--------|
| List the models folder | Presence of `{rbtv_path}/orchestration/models/{model}/` = that package is installed and routable. An absent folder = an absent row; that model is simply not a choice this run. |
| Cross-check the baked line | The installer bakes an availability line into the installed loader ("Model packages installed: … — absent: …"). Cross-check it against the folder listing; trust the FOLDER on any mismatch (disk = truth) and note the mismatch in `run-log.md`. |
| Read only installed manifests | For each installed package, read its manifest. Route on **(model, variant) pairs** — never on a bare model name. The manifest's reasoning tier, code competence, web access, parallel-safety, headless flags, resume support, cost class, and known failure modes are the routing inputs. Do NOT reproduce manifest contents here; read them at routing time. |
| Degrade gracefully | If the cheapest capable model for a leaf is not installed, route to the next capable installed (model, variant) and log the substitution. Never block a run because a preferred package is absent. |

Absent the manifests, routing has no inputs. This step is the gate; the tree below assumes it has run.

---

## 2. The master tree — boundedness first (D4)

The master cut is **"how fully is this task pre-specified?"** — not work-type, not cost. Score boundedness from the task artifact (a self-contained task file with exact anchors, allowlist, and self-verifiable acceptance is fully bounded; a goal with open judgment calls is unbounded).

| Boundedness | Route to | Doubt policy |
|-------------|----------|--------------|
| **Fully bounded** — every interface, edge case, and decision is inlined; acceptance is self-verifiable | The **cheapest capable (model, variant)** per the manifests (e.g., a bounded code slice → Kimi; a mechanical batch → the cheapest capable Claude variant) | Worker halts on any ambiguity it hits (the task should contain none) |
| **Partially bounded** — shape is clear but some calls need judgment mid-task | A **mid-tier Claude** with `doubt_policy: halt` — it executes the clear parts and halts precisely at each judgment point rather than guessing | `halt` — every judgment point becomes a halt-and-ask |
| **Unbounded / judgment-dense** — the deliverable IS the judgment (architecture, ambiguous spec, cross-artifact coherence) | A **top-tier Claude**, or back to planning/intake if the task is too unformed to dispatch at all | Conductor-grade reasoning; this is keystone work — never split it for coherence's sake (validated: the spec/plan/tasks role kept 4 artifact layers coherent in one opus dispatch) |

Then apply two filters, in order, to the tree's output:

| Filter | Rule |
|--------|------|
| **STAKES** | Irreversible or cross-cutting work (touches many files, hard-to-undo effects, shared contracts) → tier UP one level from what boundedness chose, AND add halts at the irreversible steps. Stakes override cheapness — a "bounded" task with irreversible blast radius does not go to the cheapest worker. |
| **BUDGET** | Apply the run's budget answer from intake (`state-capsule.md` Run Configuration). If the user approved a model swap to save spend, that swap is the standing delegation map — honor it here, EXCEPT where a pinned-role floor (§3) or a HARD stakes halt forbids the downgrade. Budget never lowers a reviewer below sonnet and never sends irreversible work to a too-weak worker; surface the conflict instead of silently violating a pin. |

---

## 3. Pinned roles — never route down (D4)

Some roles carry a floor that boundedness, budget, and cheapness CANNOT lower. Pin them before finalizing any assignment:

| Role | Floor | Why (evidence) |
|------|-------|----------------|
| **Reviewer** | ≥ executor tier + 1, floor **sonnet**, **never haiku**. **Opus reviews ALL external-CLI code.** | Review+fix out-ROI'd authoring across all three hypresent sessions; a sonnet reviewer caught 7 blockers pre-build in one pass. Opus review of CLI-worker output caught inverted contracts and over-generalizations a cheaper reviewer would miss. |
| **Cold verifier** | Independent worker, fidelity-floor capable; receives ONLY the contract criteria + running artifact (never the builder's tests/claims/sheet) | Mandatory for development dispatches (verification card owns the firing schedule). Not a cost-optimization target. |
| **Debug roles** | Top-tier (opus) — DEBUG-AGENT and live-debug-with-owner | Live-validated fix specs landed first-try across 6+ dispatches; debugging interaction bugs is judgment-dense by nature. Never let a CLI worker root-cause. |
| **Commits** | Routed through a worker invoking `rbtv-commit` — never folded into an executor's own run | Commit hygiene, message quality, exclusion lists, and no-push guarantees require the skill; CLI workers are kept OFF commits deliberately. |

A pinned role that the boundedness tree or budget filter would have sent lower is RAISED to its floor here. Pins win over every other routing input.

---

## 4. Topology — one Agent-tool level, CLI fleets below (D7)

The delegation shape is fixed by a hard environmental wall, encoded honestly:

| Rule | Detail |
|------|--------|
| **One Agent-tool level** | Agent-tool sub-agents CANNOT spawn sub-agents (the nesting wall — documented 4× across pilots). The conductor's own Agent-tool dispatches are a single level; never design a routing that asks a sub-agent to dispatch its own sub-agents. |
| **Sub-conductors via process boundary** | A second conductor level is achieved ONLY through CLI workers — a Claude helper drives `kimi`, `codex exec`, or `claude -p` as separate OS processes (a process is not an Agent-tool sub-agent, so the wall does not apply). CLI workers natively load the workspace `CLAUDE.md`/rules; Agent-tool helpers do not. |
| **Depth cap ≤ 2 conductor levels** | The top conductor plus at most one CLI-driven sub-conductor. Do not stack deeper. |
| **Pre-dispatch guidance-file check** | Before routing code work to a CLI worker, confirm the target workspace carries that worker's guidance file (`AGENTS.md`, the agent file, etc. — per the model's manifest convention). If it is MISSING: flag the user and offer to create it via the package's mirror machinery. Do not silently dispatch a CLI worker into a workspace that lacks its guidance file. |

---

## 5. The sdd route (D20)

For code work whose backend was set to **sdd** at intake (`superpowers:subagent-driven-development`), routing treats sdd as **ONE composite dispatch wrapped by the outer gates** — not as a fleet to micro-route:

| Rule | Detail |
|------|--------|
| Backend is already chosen | Intake asked once per run (CLI fleet vs sdd). Routing does not re-ask; it reads the choice from `state-capsule.md`. |
| One composite dispatch | sdd runs its own internal TDD loop and sub-structure. Route the whole code body to it as a single wrapped dispatch; the same outer gates apply (return verification; cold verifier at feature commit boundaries — verification card owns these). |
| Never replicate its internals | Do NOT decompose sdd's TDD cycle, its own sub-agent structure, or its test discipline into routing decisions here. The outer gates wrap it; its inside is its own. |
| sdd absent | If sdd was not installable, intake already fell back to the CLI/native path silently — this leaf is simply not taken. |

---

## 6. The research leaf (D15)

When a task's deliverable is **web research** (a self-contained research brief → findings), route it to a web-capable worker:

| Rule | Detail |
|------|--------|
| Route by manifest | Send the brief to an installed worker whose manifest declares web access (e.g., the qwen package's research contract, or another web-capable model). Match the brief to a worker that can actually reach the web. |
| Carry the sources manifest | If the user or workspace provides a curated preferred/banned-sources file, the dispatch carries a **pointer** to it; the web-searching skill loads it when pointed and skips gracefully when absent. rbtv ships only the generic mechanism — the sources file itself stays user/workspace-side. |
| Name the web skill in the dispatch | The dispatch MUST carry the `rbtv-web-searching` directive in imperative form ("invoke `rbtv-web-searching` before any web work and follow it exactly") — the rbtv-sub-agents mandate. The dispatch-wrapper card packages this; routing's job is to mark the task as a research leaf so the wrapper includes the directive. |
| Self-contained brief | The brief carries its own question, scope, and integration target — the worker reads nothing from conversation history. |

---

## 7. The haiku clause (D4)

> **Haiku is routable ONLY for mechanical batches under a user-approved delegation map.** The user's approval of that map IS the "explicit request" the sub-agents rule requires before haiku may be used — no separate per-dispatch permission is needed once the map is approved. Absent an approved delegation map naming haiku for specific mechanical batches, haiku is never routed: the boundedness tree's "cheapest capable" defaults to the cheapest **non-haiku** capable (model, variant), and every pinned role floors at sonnet regardless.

Mechanical = no judgment: disjoint-allowlist file ops, format conversions, deterministic batch edits with self-verifiable acceptance. The moment a batch carries a judgment call, it is not mechanical and haiku is off the table.

(This clause is the workflow-side resolution of the haiku conflict; the rule-side clause in `core/rules/sub-agents.md` is updated separately to match this exact wording.)

---

## 8. Batching and parallelism (D21)

Once a worker is chosen, size and group the dispatch:

| Heuristic | Rule |
|-----------|------|
| **Batch sizing** | One bounded dispatch = one module or one coherent slice, sized to roughly **30–90 minutes** of work. Micro-batching (a single tight change) and macro-batching (a coherent multi-file slice) both apply; never bundle unrelated work into one dispatch. |
| **Disjoint allowlists** | Parallel workers in the same work-dir are safe **iff their file allowlists are disjoint** (validated 3-, 4-, and 6-wide). Each task declares an explicit allowlist (✚ create / ✎ modify / ✗ delete). |
| **Shared-file serialization** | When tasks touch the same file, declare the serialization order in the plan (e.g., `commands.js: T5→T7`) and build parallel waves strictly from that order. Never parallelize two tasks that write the same file. |
| **Wave commits** | Parallel uncommitted waves make per-task diffs inseparable. Commit at **wave boundaries** to restore git-diff resolution (wave commits double as rollback points); between commits, gate by file-set + symbol greps. |
| **Worktree isolation** | Default to **worktree isolation for parallel CODE workers** — each parallel code worker gets its own worktree so their changes never collide on disk. |

**Cross-workdir file access** (when a task needs files outside the worker's work-dir): default to **orchestrator pre-staging** (Path A) for mechanical ops — the conductor copies/moves/generates the file INTO the work-dir before dispatch and annotates the task body to skip the create step, keeping the worker's surface minimal. Use **`--add-dir`** (Path B) ONLY when the worker must exercise judgment over the external files (decide which to read, merge/transform). Frozen-doc or credentials paths NEVER use `--add-dir` — pre-stage the excerpt instead.

---

## 9. The cross-strategy seam is judgment-guided — UNVALIDATED

Everything above routes WITHIN a chosen strategy on validated evidence. Choosing BETWEEN whole strategies — CLI fleet vs sdd vs an Agent-tool Claude tier vs a research worker — **was never piloted end-to-end**. Treat it as judgment, not as a settled algorithm:

| Discipline | Rule |
|------------|------|
| Default to the most-validated leg | For code, the CLI fleet (Kimi executes + Claude reviews) is the validated default; sdd is the deliberately-chosen alternative set at intake, not a router guess. Do not auto-route a run onto the least-validated leg. |
| Halt on genuine strategy uncertainty | When two strategies are both plausible and the choice is non-obvious, **halt and ask the user** — present the options with tradeoffs (cost, validation status, fit). A halt costs minutes; a wrong strategy costs the run. Never paper over the uncertainty with a confident-sounding pick. |
| Label it honestly in the run-log | Record strategy-level routing choices in `run-log.md` as decisions with their rationale, flagged as operating on the unvalidated seam, so the first real long-horizon run becomes evidence for this leg. |

This section is the card telling the truth about its own weakest point — keep it; do not let a future edit quietly upgrade the seam to false confidence.

---

## Hand off to the dispatch-wrapper

Routing's output is an assignment: the chosen (model, variant, agent-type), the role pins applied, the topology, the strategy leaf, and the batch/allowlist shape. Open the **dispatch-wrapper card** to package it into an actual dispatch (binding addenda, unified return schema, evidence paths). Do not dispatch from here — the situation table in the core protocol points to the wrapper; follow the situation, not a hardcoded chain.
