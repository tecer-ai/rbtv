# Card: Routing

Opened when a task is ready to dispatch — once per task (or per batch of like tasks), after intake has put a dispatchable work surface on disk. Routing answers ONE question: which worker — (model, variant, agent-type) — receives this task, under what role pins, in what topology. When it returns an assignment, open the dispatch-wrapper card to package the dispatch.

Iron rules it serves (from the core protocol): **the conductor never executes the work itself** (routing always produces a worker, never "I'll just do this one"), and **disk = truth** (routing honors the workspace election and reads the live manifests, never assumes a model is routable).

**The cross-strategy seam is the least-validated leg of this whole system.** The within-strategy mechanics below (which model for a bounded code task, reviewer pins, batching) are each pilot-validated; choosing BETWEEN whole strategies — CLI fleet vs sdd vs Agent-tool Claude vs a research worker — was never piloted end-to-end. Route it with the explicit judgment discipline in §9, not with false confidence. When the strategy choice is genuinely uncertain, halt and ask — a halt is cheaper than a wrong all-night run.

---

## Sequence

1. Read the elected manifests (what workers route here)
2. Walk the master tree (boundedness → stakes → budget)
3. Apply the pinned-role floor (roles that never route down)
4. Resolve topology (one Agent-tool level; CLI fleets below; depth cap; guidance-file check)
5. Take the right strategy leaf (sdd route · research leaf · haiku clause)
6. Size and batch the dispatch
7. Hand the assignment to the dispatch-wrapper card

---

## 1. Read the elected manifests first (D5)

Routing decides on workers ELECTED in this workspace — never on the full roster, and never on raw catalog-folder presence. Before the tree, resolve availability:

| Step | Action |
|------|--------|
| List the elected packages | The routable set is the workspace ELECTION (`rbtv.json` `model_packages`), NOT raw folder presence — `route.py` enumerates only elected packages. `{rbtv_path}/orchestration/models/` is the shippable CATALOG (a superset: every package the repo ships); a package present there but NOT elected does not route this run (it appears under **Not elected** in the baked line). Folder presence is still a necessary guard — an elected package whose folder or `manifest.yaml` is absent cannot route. **Skip underscore/known-infra dirs** (`_api/`, `_fixture/`, `mirror/`) and any dir carrying no `manifest.yaml` — never enumerated as a worker. A CONFIGURABLE package confined to a backend subset (`rbtv.json` `model_variants`, e.g. `{qwen-code-cli: [deepseek-flash, deepseek-pro]}`) enumerates ONLY its elected backends — `route.py` skips the rest at enumerate; an absent entry routes all that package's backends. |
| Test api-key availability for `auth.method: api-key` workers | For a package whose manifest declares `auth: {method: api-key}`, folder-presence alone does NOT make it routable — **availability = the key resolves**. Apply the key-resolution test per `models/manifest-schema.md` §4 (`auth.method: api-key` availability): OS environment variable first, then the `env_file` path in `rbtv.json`. Key absent in both → the package is unavailable for this dispatch; log it and degrade (next-capable / Agent-tool Claude fallback), never halt. This is distinct from `cli-login` workers (availability requires a USER-EXECUTED-ONLY login pre-flight); api-key availability is a key-resolution test the runner performs, never a human gesture. |
| Cross-check the baked line | The installer bakes the election into the loader ("Model packages installed: … — Not elected: …"); it reflects `rbtv.json` `model_packages`, the authority `route.py` reads. On any line-vs-catalog mismatch the ELECTION wins (extra folder packages are catalog, not routable); note the mismatch in `run-log.md`. In a multi-workspace repo the shared baked line may lag a given workspace's `rbtv.json` — `route.py` reads `rbtv.json` directly, so routing stays correct regardless. |
| Read only elected manifests | For each ELECTED package, read its manifest. Route on **(model, variant) pairs** — never on a bare model name. The manifest's reasoning tier, code competence, web access, parallel-safety, headless flags, resume support, cost class, and known failure modes are the routing inputs. Do NOT reproduce manifest contents here; read them at routing time. |
| Degrade gracefully | If the cheapest capable model for a leaf is not elected/available, route to the next capable ELECTED (model, variant) and log the substitution. Never block a run because a non-elected package would have been cheaper. |
| No routable packages | If NO packages are elected (or the `models/` folder is empty/absent entirely): the CLI leaves (kimi-code-cli / codex-cli / claude-code-cli / qwen-code-cli) are unavailable, and ONLY the Agent-tool Claude tiers (§4) are routable — and only if `claude-code-native` is elected. With it elected, the boundedness tree still runs, routing every leaf to an Agent-tool Claude variant; a task that genuinely REQUIRES a CLI worker (e.g., a sub-conductor via process boundary, or code execution Agent-tool cannot do) HALTS to the user. If even `claude-code-native` is not elected, routing halts. The skill is usable with a minimal election; it just has no CLI fleet until those packages are elected. |

Absent the manifests, routing has no inputs. This step is the gate; the tree below assumes it has run.

---

## 2. The master tree — boundedness first (D4)

The master cut is **"how fully is this task pre-specified?"** — not work-type, not cost. Score boundedness from the task artifact (a self-contained task file with exact anchors, allowlist, and self-verifiable acceptance is fully bounded; a goal with open judgment calls is unbounded).

| Boundedness | Route to | Doubt policy |
|-------------|----------|--------------|
| **Fully bounded** — every interface, edge case, and decision is inlined; acceptance is self-verifiable | The **cheapest capable (model, variant)** per the manifests (e.g., a bounded code slice → Kimi; a mechanical batch → the cheapest capable **non-haiku** Claude variant — haiku is routable ONLY under a user-approved delegation map, §7) | Worker halts on any ambiguity it hits (the task should contain none) |
| **Partially bounded** — shape is clear but some calls need judgment mid-task | A **mid-tier Claude** with `doubt_policy: halt` — it executes the clear parts and halts precisely at each judgment point rather than guessing | `halt` — every judgment point becomes a halt-and-ask |
| **Unbounded / judgment-dense** — the deliverable IS the judgment (architecture, ambiguous spec, cross-artifact coherence) | A **top-tier Claude**, or back to planning/intake if the task is too unformed to dispatch at all | Conductor-grade reasoning; this is keystone work — never split it for coherence's sake (validated: the spec/plan/tasks role kept 4 artifact layers coherent in one opus dispatch) |

Then apply two filters, in order, to the tree's output:

| Filter | Rule |
|--------|------|
| **STAKES** | Irreversible or cross-cutting work (touches many files, hard-to-undo effects, shared contracts) → tier UP one level from what boundedness chose, AND add halts at the irreversible steps. Stakes override cheapness — a "bounded" task with irreversible blast radius does not go to the cheapest worker. |
| **BUDGET** | Apply the run's budget answer from intake (`state-capsule.md` Run Configuration). If the user approved a model swap to save spend, that swap is the standing delegation map — honor it here, EXCEPT where a pinned-role floor (§3), a HARD stakes halt, OR a STAKES tier-up forbids the downgrade. **Precedence on the non-pinned middle case** (irreversible/cross-cutting work that STAKES tiered up but that is neither a pinned role nor a HARD halt): stakes-tier-up WINS over a budget downgrade — irreversible/cross-cutting work does not go to the cheaper worker even when no pin is involved. If the user's budget map explicitly named THAT worker for downgrade, surface the conflict to the user rather than silently overriding either. Budget never lowers a reviewer below sonnet and never sends irreversible work to a too-weak worker; surface the conflict instead of silently violating a pin. |

### 2a. The deterministic `(model, variant)` selector — call `route.py`

The boundedness table above names a TIER ("the cheapest capable (model, variant)", "a mid-tier Claude", "a top-tier Claude"). Resolving that tier to ONE concrete `(model, variant)` is a deterministic pure function, NOT a judgment pick. Do NOT hand-execute the GATE→RANK→PIN stages — CALL the router script, which implements them over the live manifests on disk:

| Step | Action |
|------|--------|
| **1. Build the task profile** | Assemble a JSON task profile carrying the selector inputs: `boundedness` (`fully-bounded` / `partially-bounded` / `unbounded`), `task_type` (`code` / `text`), `inlined_context_size` (required); plus optional `stakes` / `stakes_tier` (caller's already-made stakes call — §2 STAKES filter), `cross_strategy` (§9 multiplicity signal), `self_execute` (triviality flag — intake light path), `needs_process_boundary`, `reviews_external_cli_code` (true when reviewing external-CLI output — floors the reviewer at opus, §3), `delegation_map_allows_haiku` (§7). The profile is the SAME structured field set the planner emits to task frontmatter — plan-time and run-time call one script (locked: NO LLM middleman). |
| **2. Call the router** | `echo '{…profile…}' \| python {rbtv_path}/orchestration/models/route.py` (or `--profile {file}`); add `--explain` to print the GATE→RANK→PIN trace for the run-log. Stdlib only — no network, clock, or randomness. |
| **3. Act on the verdict** | The script emits ONE machine-readable verdict. `{"verdict": "route", "model", "variant", "carrier"}` → take that worker; hand off to the dispatch-wrapper (§4 names the carrier). `{"verdict": "self_execute"}` → the triviality light path (the conductor self-executes per intake's light-mode bar + owner approval — NOT a `route`). `{"verdict": "halt_seam", "seam": "stakes"|"cross-strategy"}` → STOP and ask the owner (§9); the script NEVER decides a seam. An `error` key + non-zero exit (`malformed_profile`, `zero_candidates`, `no_available_variants`, `no_models`) → resolve the named gap, then re-run; on `zero_candidates` degrade per §1, never silently pick an incapable variant. |

**Specification of record — the algorithm the script implements (authority lives here).** `route.py` is the mechanization; THIS card is the source of truth for the algorithm it runs. On any script-vs-card divergence the CARD TEXT WINS and a defect is filed against the script — never hand-edit a verdict to match the card, and never let a script behavior silently redefine the algorithm. Selector fields per `models/manifest-schema.md` §2: `reasoning` (int 1–7), `coding` (int 1–7), `cost` (int 1–7), `context_window`, `web_access`, `routable_for`, `evidence_status`. The full behavior + acceptance contract is `specs/router-script-spec.md` in the token-efficiency-refactor plan folder (the spec is the build contract; this card is the algorithm authority).

| Stage | Rule (the contract `route.py` implements) |
|-------|------|
| **1. Enumerate** | List every ELECTED `(model, variant)` — `route.py` filters the live `models/` folder to the workspace election (`rbtv.json` `model_packages`), so non-elected catalog packages never appear; the elected set may include Claude (Agent-tool, §4), claude-code-cli, kimi-code-cli, codex-cli, the API packages — never a bare provider name. A model with one operating profile still contributes one variant. |
| **2. GATE** | Drop any variant failing a hard requirement: `reasoning ≥ floor` (integer 1–7; floors by band — fully-bounded 1, partially-bounded 6, unbounded 7) · `coding ≥ floor` (code leaves only; floors — fully-bounded 1, partially-bounded 4, unbounded 5; floor 0 = inert on text leaves) · `context_window ≥ inlined_context_size` (AFTER plan cap) · `web_access` if the leaf needs web · `routable_for` allows this leaf-kind role (D13 code-eligibility: a variant whose non-empty `routable_for` omits both `bounded-code` and `unbounded-code` is dropped from every code leaf regardless of its `coding` integer — capability score never re-enables an ineligible code route). |
| **3. RANK survivors** | Order by, in strict priority: (1) `cost` integer ascending (1=cheapest first; 7=priciest, never auto-picked on a cost tie); (2) `evidence_status` (`validated` before `probe-pending`); (3) capability score — `coding` 1–7 orders code-leaf survivors directly (higher score ranks first; no separate sub-rank step); `reasoning` 1–7 orders text-leaf survivors; (4) carrier tiebreak — `claude-code-native` before `claude-code-cli`; (5) model-name lexical (ascending); (6) variant-name lexical (ascending). Pick the top. |
| **4. PIN/STAKES apply AFTER** | Stakes tier-up and the §3 pinned-role floors apply ONLY after the cheapest pick — they may raise it UPWARD (reviewer ≥ sonnet; conductor → opus; etc.), never below the floor. Pinned-role floors read the `executor_reasoning` INTEGER from the profile. Effort = f(boundedness) is set from `reasoning_modes` AFTER the pin (`_resolve_effort`): fully-bounded → `low`; partially-bounded → `medium`; unbounded → `high`/`max`; single-mode workers are a no-op. |

**`other`-routing audit (D4).** When `leaf_role == other` (the catch-all role), `route.py` records the specific task instructions/arguments in the verdict's `other_routing_audit` field so under-served task types surface and get promoted to first-class roles. The profile builder sets `leaf_role` explicitly; the closed `routable_for` vocabulary is `{bounded-code, unbounded-code, reasoning, web-research, text-synthesis, other}` (D12 — `judgment` removed).

**Total order — never collapses.** The six RANK keys break every tie in sequence, and Key 6 closes it absolutely: every enumerated `(model, variant)` row carries a distinct variant name within its model, so two distinct survivors ALWAYS differ on Key 5 or Key 6. The selector is NEVER non-deterministic for any legal manifest set. If zero variants survive the GATE, degrade per §1 (next-capable / Agent-tool Claude fallback) or HALT — NEVER silently pick an incapable variant.

**Name the chosen pair — never a bare provider.** Every logged or summarized assignment names the chosen `(model, variant)` — e.g. `claude-code-native:sonnet`, `deepseek-api:v4-flash` — NEVER just "Claude" or "DeepSeek". A bare-provider label in the run-log or intake budget summary is the collapse this selector exists to prevent.

**Text-leaf clause — where API chat workers compete.** API chat workers carry a `routable_for` list that omits the code roles, so §2a's GATE (D13) drops them from EVERY code leaf. They survive ONLY on TEXT leaves — partially-bounded text synthesis, mechanical text transforms, desk-research synthesis over inlined sources — where they compete on `cost` (integer 1–7) against the Claude tiers. NEVER route a code leaf to an API chat worker; the GATE already bars it, and a manual override is a routing defect.

---

## 3. Pinned roles — never route down (D4)

Some roles carry a floor that boundedness, budget, and cheapness CANNOT lower. Pin them before finalizing any assignment:

| Role | Floor | Why (evidence) |
|------|-------|----------------|
| **Conductor / orchestrator** | **opus** — the pair `claude-code-native:opus` (carrier-resolved per §4). The default conductor tier. The most senior available Claude conducts; it never routes down to a worker tier. | D15 (2026-06-17): the `fable` variant was dropped from both Claude worker manifests (access-gated with no restore path); conductor pin targets **opus**, the senior available Claude. Re-pin to fable if the variant is re-added with `available: true`. Conducting is the highest-judgment seat in the run. |
| **Final-plan reviewer** | **opus** — the pair `claude-code-native:opus` — the default pin for the cold review of a generated plan before execution. | D15 (2026-06-17): same fable-drop rationale as conductor above. Opus cold-reviews the generated plan before any execution begins. |
| **Reviewer** | ≥ executor tier + 1, floor **sonnet**, **never haiku**. **Opus reviews ALL external-CLI code.** | Review+fix out-ROI'd authoring across all three hypresent sessions; a sonnet reviewer caught 7 blockers pre-build in one pass. Opus review of CLI-worker output caught inverted contracts and over-generalizations a cheaper reviewer would miss. |
| **Cold verifier** | Independent worker, fidelity-floor capable; receives ONLY the contract criteria + running artifact (never the builder's tests/claims/sheet) | Mandatory for development dispatches (verification card owns the firing schedule). Not a cost-optimization target. |
| **Debug roles** | Any **reasoning-7 code-eligible executor** (D17) — opus **and** `codex-cli:gpt-5.5`; **opus is the default on cost**. DEBUG-AGENT and live-debug-with-owner. | Live-validated fix specs landed first-try across 6+ dispatches; debugging interaction bugs is judgment-dense by nature. D17 de-carrier-locks the floor: gpt-5.5 is reasoning 7 / coding 7 (a peer top-tier executor), so an opus-exclusive pin wrongly excluded it; the floor now keys on the reasoning integer ≥ 7, not Claude membership. Opus (cost 6) still outranks gpt-5.5 (cost 7), so the observable default is unchanged — gpt-5.5 wins debug only when opus is unavailable/capped. |
| **Commits** | Routed through a worker invoking `rbtv-commit` — never folded into an executor's own run. Carrier: an **Agent-tool Claude** (sonnet floor) invoking `rbtv-commit`; CLI executors are not the commit worker. **When NO Claude is available**, fall back to the **strongest available reasoner** (the `reasoning` integer ranked DESCENDING, cost ignored) — never the cheapest non-Claude worker, never an error (see the dated note below). | Commit hygiene, message quality, exclusion lists, and no-push guarantees require the skill; CLI workers are kept OFF commits deliberately — relaxed ONLY when Claude is entirely unavailable, where the strongest reasoner beats both a cheapest-by-cost pick and a hard block. |

A pinned role that the boundedness tree or budget filter would have sent lower is RAISED to its floor here. Pins win over every other routing input.

> **⚠ Fable 5 dropped (D15, 2026-06-17).** The `fable` variant was removed from both Claude worker manifests — access-gated since 2026-06-14 with no restore in sight; the retained-but-unavailable variant added maintenance surface with no board-sourced 1–7 data. **Both conductor and final-plan-reviewer pins now target opus** (`claude-code-native:opus`). Re-add the `fable` variant with `available: true` and re-pin these roles to fable if Fable 5 access opens.

> **⚠ Debug floor de-carrier-locked (D17, 2026-06-17).** The `debug` pin no longer requires Claude membership — it admits any elected, available, code-eligible executor with **reasoning ≥ 7**. With the current catalog that is exactly `{claude-code-native:opus, claude-code-cli:opus, codex-cli:gpt-5.5}`; reasoning-6 workers (sonnet, kimi, gpt-5.4) and non-code API workers (deepseek/gemini/manus) stay barred. **Observable default unchanged:** opus (cost 6) outranks gpt-5.5 (cost 7) under the §2a cost-ascending RANK, so a standard debug task still picks `claude-code-native:opus`; gpt-5.5 wins debug only when opus is unavailable/capped.

> **⚠ Commit pin Claude-unavailable fallback (2026-06-17).** The `commit` pin no longer keeps the cheapest non-Claude `chosen` (its old normal-path `floor_not_found`) and no longer errors (the p4-0b empty-pipeline behavior) when no Claude is available — BOTH paths now fall back to the **strongest available reasoner**: the `reasoning` integer ranked **DESCENDING, cost ignored** (haiku excluded; ties broken by the §2a cost-ascending house order). With the current catalog and Claude excluded that is `codex-cli:gpt-5.5` (reasoning 7) over `kimi` / `gpt-5.4` (reasoning 6). **Claude-available behavior is unchanged** (commit → `claude-code-native:sonnet`). Commit is the SOLE Claude-floor pin with a non-Claude fallback — reviewer / conductor / final-plan-reviewer stay Claude-only-or-error. Rationale: commit-message/hygiene quality outweighs cost, and a strongest-reasoner safety net beats both a silent cheapest-worker pick and a hard block when Claude is (rarely) unavailable.

**Within the top Claude tier — opus.** Opus is the top-tier Claude for all senior roles: conductor, final-plan reviewer, debug, and cost-sensitive high-judgment WORKER dispatches (architecture spec, rule edit, judgment-dense leaf). (Debug, since D17, also admits the non-Claude `codex-cli:gpt-5.5` — opus remains its default on cost; conductor and final-plan-reviewer stay Claude-pinned.) Opus carries `cost: 6` (integer 1–7 scale, D11) — the §2a RANK therefore never auto-picks opus for a cheap fully-bounded leaf (cost-ascending rank routes cheapest-capable first). For the finer within-tier "best at" disambiguation between any two same-tier variants, consult each `(model, variant)`'s `specialty` manifest field and the overlap rows in `orchestration/docs/routing-matrix-reference.md` — a within-tier tiebreaker, never a new master cut.

---

## 4. Topology — one Agent-tool level, CLI fleets below (D7)

The delegation shape is fixed by a hard environmental wall, encoded honestly:

| Rule | Detail |
|------|--------|
| **One Agent-tool level** | Agent-tool sub-agents CANNOT spawn sub-agents (the nesting wall — documented 4× across pilots). The conductor's own Agent-tool dispatches are a single level; never design a routing that asks a sub-agent to dispatch its own sub-agents. |
| **Sub-conductors via process boundary** | A second conductor level is achieved ONLY through CLI workers — a Claude helper drives `kimi`, `codex exec`, or `claude -p` as separate OS processes (a process is not an Agent-tool sub-agent, so the wall does not apply). CLI workers natively load the workspace `CLAUDE.md`/rules; Agent-tool helpers do not. |
| **Depth cap ≤ 2 conductor levels** | The top conductor plus at most one CLI-driven sub-conductor. Do not stack deeper. |
| **Launch-root confinement (G1)** | Every CLI worker launches with its guidance-root = the **orchestrator root** and the work-target passed via the model's add-dir flag — follow the dispatch-wrapper card §1 launch-root row (the policy lives there). Routing's obligation: record the launch-root and work-target as SEPARATE values in the assignment it hands the wrapper — never collapse them into one "work-dir", and never assign a nested-repo work-target as a worker's launch root. |
| **Pre-dispatch guidance-file check** | Before routing code work to a CLI worker, confirm the **LAUNCH ROOT** (the orchestrator root the worker's guidance keys to — NOT the work-target) carries that worker's guidance file (`AGENTS.md`, the agent file, etc. — per the model's manifest convention). The work-target needs NO guidance file or mirror of its own — the mirror skips nested git repos BY DESIGN because workers never root there. **Defer condition:** if `.agents/behavior-rules/` exists at the launch root, the driver owns the guidance file — do NOT create or refresh it; STILL verify the worker's guidance file is present, but NEVER overwrite it (the driver, not this check, regenerates a driver-owned file). If `.agents/behavior-rules/` is present but the worker's guidance file is MISSING, do NOT create it here — flag the user to re-run the mirror driver (it owns that file). Only when `.agents/behavior-rules/` is absent: if the guidance file is MISSING, flag the user and offer to create it via the package's mirror machinery. Never silently dispatch a CLI worker from a launch root that lacks its guidance file. |
| **Pre-dispatch pinned-flag check** | Before dispatching ANY CLI worker, run the pinned-flag-existence gate from that worker's delta Pre-flight: every non-trivial flag the dispatch pins (approval / sandbox / permission / output-path) MUST be verified present in the live `<cli> <subcommand> --help` — EVERY dispatch, not only on a version mismatch, and against the EXACT subcommand the dispatch uses (`codex exec --help`, not `codex --help`). A pinned flag absent from live `--help` → STOP, do not dispatch; re-resolve the flag at the delta source, re-render the manual, re-run the gate — never hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard arg-parse error (exit 2) pre-spend if dispatched. (codex 0.137.0 dropped `--ask-for-approval` from `exec` at the same version family the manual pinned — caught at p5-2.) |
| **In-session spawn permission (D17)** | A CLI worker spawned from inside a Claude session is permitted by installer-managed PREFIX allowlist rules (the package manifest's `permission_rules`, synced into the target's `.claude/settings.local.json` on install) — and a prefix rule matches ONLY a command line that BEGINS with the worker binary. Compose every in-session CLI dispatch per dispatch-wrapper §1's D17 row (no leading `cd`/env-assignment/stdin-pipe). A spawn denied DESPITE a matching binary-first rule (a session-mode classifier denial — observed once, token-efficiency-refactor D17) → do not retry shaping tweaks: degrade the carrier per this card, or hand the exact command to the owner as a `!`-typed dispatch. A worker package elected but missing its allowlist entries → re-run `install.py` (the sync is install-time, not runtime). |

**Resolving the agent-type axis (which the boundedness tree leaves open).** The tree picks a tier (cheapest-capable / mid / top); this step picks the CARRIER for it.

**Two distinct Claude carriers — both enumerated as separate `(model, variant)`.** Claude is enumerable through TWO packages, NOT one: `models/claude-code-native/` (the **Agent-tool** in-session carrier, dispatched via the Agent tool — `claude-code-native:opus` / `claude-code-native:sonnet`) and `models/claude-code-cli/` (the **`claude -p` process** carrier — `claude-code-cli:opus` / `claude-code-cli:sonnet`). The §2a selector enumerates BOTH as distinct pairs; they differ in routing-relevant properties (the Agent-tool carrier does NOT natively load workspace `CLAUDE.md`/rules and cannot spawn sub-agents — the nesting wall; the process carrier loads workspace rules natively and clears the nesting wall as a separate OS process). NEVER collapse the two Claude carriers into one entity.

| Tier the tree chose | Carrier |
|---------------------|---------|
| A Claude tier (mid or top) | Default to **`claude-code-native`** — the **Agent-tool** in-session carrier (`models/claude-code-native/`; no guidance-file dependency, no process overhead). Use **`claude-code-cli`** (the `claude -p` process carrier, `models/claude-code-cli/`) instead ONLY when a process-boundary sub-conductor is needed (the worker must itself drive CLI workers — the nesting wall forces a process) or when native workspace-rule loading is required. Both are enumerated distinctly by §2a; this row picks BETWEEN the two carriers for the chosen tier. |
| A code-executing CLI leaf | Choose **kimi-code-cli vs codex-cli** by manifest fit, not preference: kimi-code-cli is the validated bounded-code executor (default for bounded code); codex-cli is the live-proven-once alternative — pick on the manifest's code-competence / OS-quirk / cost-class fields for the specific task. Absent a distinguishing manifest reason, default to the validated worker (kimi-code-cli) and log the choice. **Windows capability-run / live-call caveat:** codex-cli's `workspace-write` sandbox DOES spawn subprocesses on Windows — `git`/`node`/`pwsh`/`cmd` all run (TESTED 2026-06-14, codex-cli manifest `os_quirks.windows` + delta sandbox-grammar). The boundary is codex's APPROVAL ROUTER, which declines `python`/`python -c` (so python/pytest-based validation fails under `approval_policy="never"`), NOT a spawn-capability limit. A **live/network API call also WORKS** under `workspace-write` when dispatched with `-c sandbox_workspace_write.network_access=true` through an auto-approved client (TESTED 2026-06-14: `node` fetch → HTTP 200; without the flag, egress is refused; `danger-full-access` not required). So codex CAN self-validate a leaf whose check is `git`/`node`/`pwsh`/`cmd`-based, AND can make a granted live call. Route to **kimi-code-cli** OR split the dispatch (codex authors the edit, conductor runs the validation as an exit-probe) ONLY for a leaf whose acceptance needs a **python/pytest** run, or a **live/network call** that cannot be granted egress or must run through `python` — do NOT blanket-split every codex capability-run or every live-call on Windows. |

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

When a task's deliverable touches the **web**, route it by which of THREE distinct web tiers the task needs — the tiers differ in autonomy, rigor, and cost, and the §2a selector already enumerates every `web_access: true` worker for the leaf. Honor each named worker's manifest `evidence_status` (the §1 manifest-read surfaces it): a `probe-pending` tier worker routes only with the unvalidated-seam discipline of §9, never as a settled choice.

| Web tier | When it fits | Route to |
|----------|--------------|----------|
| **Autonomous-web** | The agent must navigate, click, fill, and synthesize across pages on its OWN — multi-step browser-driven data collection, not a single lookup | The **manus-api `manus-autonomous`** agentic worker (`web_access: true`, per-task cost, minutes-scale latency, raw-dump return). manus-api's `routable_for: [web-research]` omits the code roles, so §2a's GATE already drops it from every code leaf (D13) — never route code here. |
| **Light grounding** | A single grounded lookup — one search-grounded call, light not rigorous | The **Gemini** API worker (the only `web_access: true` chat worker). |
| **Rigorous multi-source research** | Source evaluation, citations, cross-checking across many sources | The `rbtv-web-searching` Agent-tool path, or an installed `web_access: true` CLI worker that §2a enumerates for the leaf — NEVER an API chat worker. |

For a rigorous-multi-source brief (a self-contained research brief → findings), apply the rows below:

| Rule | Detail |
|------|--------|
| Route by manifest | Send the brief to an installed worker whose manifest declares `web_access: true`. Match the brief to a worker that can actually reach the web. (NOTE: qwen-code-cli is `web_access: false` — NOT a web worker; route web research to a web-declaring CLI or the Agent-tool path, never qwen. D-exec-11, 2026-06-10.) |
| API web access is Gemini grounding only — light | Among the API workers, ONLY gemini-api carries `web_access: true` (search grounding), and it is **light web** — a grounded single-call lookup, NOT rigorous multi-source research. If an API worker must reach live web, it MUST be gemini-api. For rigorous multi-source research (source evaluation, citations, cross-checking) prefer the `rbtv-web-searching` Agent-tool path (or an installed CLI worker whose manifest declares `web_access: true`) — never an API chat worker. |
| Degrade when no web-capable package | If NO installed model package declares web access, route the research brief to an **Agent-tool sub-agent carrying the `rbtv-web-searching` directive** (the in-session web path — always available). If even that is unavailable, HALT and surface — never dead-end the research leaf. |
| Carry the sources manifest | If the user or workspace provides a curated preferred/banned-sources file, the dispatch carries a **pointer** to it; the web-searching skill loads it when pointed and skips gracefully when absent. rbtv ships only the generic mechanism — the sources file itself stays user/workspace-side. |
| Name the web skill in the dispatch | The dispatch MUST carry the `rbtv-web-searching` directive in imperative form ("invoke `rbtv-web-searching` before any web work and follow it exactly") — the rbtv-sub-agents mandate. The dispatch-wrapper card packages this; routing's job is to mark the task as a research leaf so the wrapper includes the directive. |
| Self-contained brief | The brief carries its own question, scope, and integration target — the worker reads nothing from conversation history. |

---

## 7. The haiku clause (D4)

Haiku eligibility is routing policy and is owned HERE (moved from `core/rules/sub-agents.md` — that rule no longer carries model policy). Default model posture: sub-agent dispatches default to `sonnet`; haiku is NEVER routed without the explicit ask below.

| Condition | Haiku eligibility |
|-----------|-------------------|
| User-approved delegation map names haiku for a specific mechanical batch | Routable for THAT batch — the map approval IS the required explicit ask; no separate per-dispatch permission needed once the map is approved |
| No approved delegation map naming haiku for the batch | NEVER routed — default to the cheapest **non-haiku** capable variant; every pinned role (§3) floors at **sonnet** regardless |
| Batch carries any judgment call | NOT mechanical — haiku is off the table even under an approved map |

**Mechanical = no judgment:** disjoint-allowlist file ops, format conversions, deterministic batch edits with self-verifiable acceptance. The moment a batch requires a judgment call, it is no longer mechanical. A standalone haiku dispatch outside an approved delegation map requires an explicit user ask.

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
| **Hot-zone detection** | Before dispatching a task, check whether its target files overlap a CONCURRENT session's in-flight work. Detection is deterministic: run `git status --porcelain` on the task's EXACT target paths — a dirty target NOT owned by this run is a hot zone. On a hot zone, the conductor either worktree-isolates that task or serializes it behind the foreign work; it NEVER dispatches a task whose targets a parallel session is actively editing. |

**Cross-workdir file access** (when a task needs EXTRA files beyond the work-target — distinct from the work-target itself, which ALWAYS rides the add-dir flag per the §4 launch-root row): default to **orchestrator pre-staging** (Path A) for mechanical ops — the conductor copies/moves/generates the file INTO the work-dir before dispatch and annotates the task body to skip the create step, keeping the worker's surface minimal. Use **`--add-dir`** (Path B) ONLY when the worker must exercise judgment over the external files (decide which to read, merge/transform). Frozen-doc or credentials paths NEVER use `--add-dir` — pre-stage the excerpt instead.

---

## 9. The cross-strategy seam is judgment-guided — UNVALIDATED

Everything above routes WITHIN a chosen strategy on validated evidence. Choosing BETWEEN whole strategies — CLI fleet vs sdd vs an Agent-tool Claude tier vs a research worker — **was never piloted end-to-end**. Treat it as judgment, not as a settled algorithm:

| Discipline | Rule |
|------------|------|
| Default to the most-validated leg | For code, the CLI fleet (Kimi executes + Claude reviews) is the validated default; sdd is the deliberately-chosen alternative set at intake, not a router guess. Do not auto-route a run onto the least-validated leg. |
| Halt on strategy uncertainty — only when undetermined | This halt fires ONLY when the strategy is NOT already determined upstream: the code backend set at intake (CLI fleet vs sdd), an automatic strategy leaf (§5 sdd, §6 research), and a single strategy surviving the boundedness tree + filters are all already-determined — take them, do NOT halt. The halt is for the residual case. **Concrete test:** if the boundedness tree + STAKES/BUDGET filters yield exactly ONE strategy, take it. Halt ONLY when ≥2 whole strategies survive the filters AND they differ materially in cost OR validation status — present the options with tradeoffs (cost, validation status, fit) and let the user pick. A downgraded conductor (D9) halts on ANY surviving multiplicity. A halt costs minutes; a wrong strategy costs the run. Never paper over a genuine multiplicity with a confident-sounding pick. |
| Label it honestly in the run-log | Record strategy-level routing choices in `run-log.md` as decisions with their rationale, flagged as operating on the unvalidated seam, so the first real long-horizon run becomes evidence for this leg. |

This section is the card telling the truth about its own weakest point — keep it; do not let a future edit quietly upgrade the seam to false confidence.

---

## Hand off to the dispatch-wrapper

Routing's output is an assignment: the chosen (model, variant, agent-type), the role pins applied, the topology, the strategy leaf, and the batch/allowlist shape. Open the **dispatch-wrapper card** to package it into an actual dispatch (binding addenda, unified return schema, evidence paths). Do not dispatch from here — the situation table in the core protocol points to the wrapper; follow the situation, not a hardcoded chain.
