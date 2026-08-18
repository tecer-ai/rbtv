# Card: Routing

Opened when a task is ready to dispatch — once per task (or per batch of like tasks), after intake has put a dispatchable work surface on disk. Routing answers ONE question: which worker — `(harness, model)` plus `effort` plus `carrier` — receives this task, under what role pins, in what topology. When it returns an assignment, open the dispatch-wrapper card to package the dispatch.

Iron rules it serves (from the core protocol): **the conductor never executes the work itself** (routing always produces a worker, never "I'll just do this one"), and **disk = truth** (routing honors the live catalog ∩ availability, never assumes a model is routable).

**The cross-strategy seam is the least-validated leg of this whole system.** The within-strategy mechanics below (which model for a bounded code task, reviewer pins, batching) are each pilot-validated; choosing BETWEEN whole strategies — CLI fleet vs sdd vs Agent-tool Claude vs a research worker — was never piloted end-to-end. Route it with the explicit judgment discipline in §9, not with false confidence. When the strategy choice is genuinely uncertain, halt and ask — a halt is cheaper than a wrong all-night run.

---

## Sequence

1. Read the catalog ∩ availability (what workers route here)
2. Walk the master tree (boundedness → stakes → budget)
3. Apply the pinned-role floor (roles that never route down)
4. Resolve topology (one Agent-tool level; CLI fleets below; depth cap; guidance-file check)
5. Take the right strategy leaf (sdd route · research leaf · haiku clause)
6. Size and batch the dispatch
7. Hand the assignment to the dispatch-wrapper card

---

## 1. Read the catalog ∩ availability

Routing decides on workers that are **in the cast catalog AND available now** — never on a workspace election, and never on folder presence under a models tree. Before the tree, resolve the routable set:

| Step | Action |
|------|--------|
| Recall the catalog | The catalog is `cast route --catalog` (add `--json` for the machine-readable roster). That command IS the `--availability` equivalent. It lists every row `cast route` may pick, including non-launchable carriers. Nothing about the roster is baked into this card; the live read is the source. |
| Routable set | **Routable set = catalog ∩ availability.** Catalog = every row `cast route --catalog` emits. Availability-now = binary installed per `cast doctor` logic, plus API-key resolution for `carrier: api` rows (OS env first, then the `env_file` path in `rbtv.json`, then a stored CLI login when the row names a credential store). A row marked `available: false` in the catalog, or an `auth.method: api-key` row whose key does not resolve, is not routable. Key absent → log it and degrade (next-capable / Agent-tool Claude fallback), never halt. `rbtv.json` `model_packages` / `model_variants` election is RETIRED — do not walk an election, a picker, or a `not_elected` list. |
| Selector fields | Live on the **catalog schema** (not a models-tree manifest). Surviving axes: `reasoning`, `coding`, `cost` (ints 1–7), `context_window`, `web_access`, `routable_for`, `evidence_status`, `available`, `auth.*`, `reasoning_modes.depths`, plus `carrier`. Route on catalog rows — never on a bare provider name. |
| Non-launchable rows | Two carriers are legal to PICK and illegal to LAUNCH via `cast <harness> …`: `carrier: agent-tool` (Agent-tool Claude tiers) and `carrier: api` (API workers). `cast` refuses to launch them; `cast route` may pick them. Hand an API pick to `cast api`. Dispatch an Agent-tool pick via the Agent tool, not via `cast`. |
| kimi-code-cli | RETIRED (owner 2026-08-18). Do not list it as a routable worker. Kimi models route only via opencode. |
| Degrade gracefully | If the cheapest capable row for a leaf is not available, route to the next capable catalog ∩ availability row and log the substitution. Never block a run because an unavailable row would have been cheaper. |
| No routable rows | If the catalog is empty or every row fails availability: CLI leaves (codex / claude-cli / opencode) are unavailable, and ONLY the Agent-tool Claude tiers (§4) are routable — and only if a `carrier: agent-tool` Claude row is available. With it available, the boundedness tree still runs, routing every leaf to an Agent-tool Claude row; a task that genuinely REQUIRES a CLI worker (e.g., a sub-conductor via process boundary, or code execution Agent-tool cannot do) HALTS to the user. If no Agent-tool Claude row is available either, routing halts. |

Absent the catalog, routing has no inputs. This step is the gate; the tree below assumes it has run.

---

## 2. The master tree — boundedness first (D4)

The master cut is **"how fully is this task pre-specified?"** — not work-type, not cost. Score boundedness from the task artifact (a self-contained task file with exact anchors, allowlist, and self-verifiable acceptance is fully bounded; a goal with open judgment calls is unbounded).

| Boundedness | Route to | Doubt policy |
|-------------|----------|--------------|
| **Fully bounded** — every interface, edge case, and decision is inlined; acceptance is self-verifiable | The **cheapest capable catalog row** (e.g., a bounded code slice → a cheap opencode/codex row; a mechanical batch → the cheapest capable **non-haiku** Claude row — haiku is routable ONLY under a user-approved delegation map, §7) | Worker halts on any ambiguity it hits (the task should contain none) |
| **Partially bounded** — shape is clear but some calls need judgment mid-task | A **mid-tier Claude** with `doubt_policy: halt` — it executes the clear parts and halts precisely at each judgment point rather than guessing | `halt` — every judgment point becomes a halt-and-ask |
| **Unbounded / judgment-dense** — the deliverable IS the judgment (architecture, ambiguous spec, cross-artifact coherence) | A **top-tier Claude**, or back to planning/intake if the task is too unformed to dispatch at all | Conductor-grade reasoning; this is keystone work — never split it for coherence's sake (validated: the spec/plan/tasks role kept 4 artifact layers coherent in one opus dispatch) |

Then apply two filters, in order, to the tree's output:

| Filter | Rule |
|--------|------|
| **STAKES** | Irreversible or cross-cutting work (touches many files, hard-to-undo effects, shared contracts) → tier UP one level from what boundedness chose, AND add halts at the irreversible steps. Stakes override cheapness — a "bounded" task with irreversible blast radius does not go to the cheapest worker. |
| **BUDGET** | Apply the run's budget answer from intake (`state-capsule.md` Run Configuration). If the user approved a model swap to save spend, that swap is the standing delegation map — honor it here, EXCEPT where a pinned-role floor (§3), a HARD stakes halt, OR a STAKES tier-up forbids the downgrade. **Precedence on the non-pinned middle case** (irreversible/cross-cutting work that STAKES tiered up but that is neither a pinned role nor a HARD halt): stakes-tier-up WINS over a budget downgrade — irreversible/cross-cutting work does not go to the cheaper worker even when no pin is involved. If the user's budget map explicitly named THAT worker for downgrade, surface the conflict to the user rather than silently overriding either. Budget never lowers a reviewer below sonnet and never sends irreversible work to a too-weak worker; surface the conflict instead of silently violating a pin. |

### 2a. The deterministic selector — call `cast route`

The boundedness table above names a TIER ("the cheapest capable catalog row", "a mid-tier Claude", "a top-tier Claude"). Resolving that tier to ONE concrete `(harness, model)` plus `effort` plus `carrier` is a deterministic pure function, NOT a judgment pick. Do NOT hand-execute the GATE→RANK→PIN stages — CALL `cast route`, which implements them over the live catalog ∩ availability:

| Step | Action |
|------|--------|
| **1. Build the task profile** | Assemble a JSON task profile carrying the selector inputs: `boundedness` (`fully-bounded` / `partially-bounded` / `unbounded`), `task_type` (`code` / `text`), `inlined_context_size` (required); plus optional `known_input_size` (the task's KNOWN INPUT in tokens = dispatch prompt + required reads; drives the footprint GATE — §2b), `stakes` / `stakes_tier` (caller's already-made stakes call — §2 STAKES filter; the router acts on the `stakes` VALUE directly — `irreversible` or `cross-cutting` normalizes into `stakes_tier: tier_up` so irreversible/cross-cutting work never routes to the cheapest worker, while `unresolved` is the halt-seam and any other value is a no-op), `cross_strategy` (§9 multiplicity signal), `self_execute` (triviality flag — intake light path), `needs_process_boundary`, `reviews_external_cli_code` (true when reviewing external-CLI output — floors the reviewer at opus, §3), `delegation_map_allows_haiku` (§7), `pinned_role`. The profile is the SAME structured field set the planner emits to task frontmatter — plan-time and run-time call one command (locked: NO LLM middleman). |
| **2. Call the router** | `echo '{…profile…}' \| cast route` (or `cast route --profile {file}`); add `--explain` to print the GATE→RANK→PIN trace for the run-log. No network, clock, or randomness. |
| **3. Act on the verdict** | The command emits ONE machine-readable verdict. `{"verdict": "route", "harness", "model", "effort", "carrier"}` → take that worker; `effort` is the 1–5 integer; hand off to the dispatch-wrapper (§4 names the carrier). `{"verdict": "self_execute"}` → the triviality light path (the conductor self-executes per intake's light-mode bar + owner approval — NOT a `route`). `{"verdict": "halt_seam", "seam": "stakes"|"cross-strategy"}` → STOP and ask the owner (§9); the command NEVER decides a seam. An `error` key + non-zero exit (`malformed_profile`, `zero_candidates`, `no_available_variants`, `no_models`) → resolve the named gap, then re-run; on `zero_candidates` degrade per §1, never silently pick an incapable row. |

**Specification of record — the algorithm `cast route` implements (authority lives here).** `cast route` is the mechanization; THIS card is the source of truth for the algorithm it runs. On any `cast route`-vs-card divergence the CARD TEXT WINS and a defect is filed against `cast` — never hand-edit a verdict to match the card, never let `cast` behavior silently redefine the algorithm, and never file the defect the other way around. Selector fields live on the catalog schema: `reasoning` (int 1–7), `coding` (int 1–7), `cost` (int 1–7), `context_window`, `web_access`, `routable_for`, `evidence_status`, `available`, `auth.*`, `reasoning_modes.depths`, plus `carrier`. The identity key is the pair `(harness, model)` plus `effort` plus `carrier` — `variant` is not an identity key.

| Stage | Rule (the contract `cast route` implements) |
|-------|------|
| **1. Enumerate** | List every catalog ∩ availability row — including `carrier: agent-tool` and `carrier: api` rows. No election filter. Never a bare provider name. A model with one operating profile still contributes one row per carrier it is published under (Claude sonnet exists as both `carrier: agent-tool` and `carrier: cli`). |
| **2. GATE** | Drop any row failing a hard requirement: `reasoning ≥ floor` (integer 1–7; floors by band — fully-bounded 1, partially-bounded 6, unbounded 7) · `coding ≥ floor` (code leaves only; floors — fully-bounded 1, partially-bounded 4, unbounded 5; floor 0 = inert on text leaves) · `context_window` window check (AFTER plan cap) — when the profile carries `known_input_size` the check is the FOOTPRINT cap `context_window ≥ ceil(known_input_size / window_utilization_cap)` (a worker fits only if the known input is at most `window_utilization_cap` of its window — default 0.20 ⇒ window ≥ 5× input; §2b); when absent it is the back-compat `context_window ≥ inlined_context_size` · `web_access` if the leaf needs web · `routable_for` allows this leaf-kind role (D13 code-eligibility: a row whose non-empty `routable_for` omits both `bounded-code` and `unbounded-code` is dropped from every code leaf regardless of its `coding` integer — capability score never re-enables an ineligible code route). Partially-bounded and unbounded bands additionally **scope** the eligible set to Claude rows at the band's reasoning floor before GATE (partially-bounded → Claude reasoning ≥ 6; unbounded → Claude reasoning ≥ 7). Pins and the footprint fallback reach over the FULL available set, not this scoped set. |
| **3. RANK survivors** | Order by, in strict priority: (1) `cost` integer ascending (1=cheapest first; 7=priciest, never auto-picked on a cost tie); (2) `evidence_status` (`validated` before `probe-pending`); (3) capability score — `coding` 1–7 orders code-leaf survivors directly (higher score ranks first); `reasoning` 1–7 orders text-leaf survivors; (4) carrier tiebreak — `agent-tool` before `cli` before `api`; (5) harness lexical (ascending); (6) model lexical (ascending). Pick the top. |
| **4. PIN/STAKES apply AFTER** | Stakes tier-up and the §3 pinned-role floors apply ONLY after the cheapest pick — they may raise it UPWARD (reviewer ≥ sonnet; conductor → fable, opus fallback; etc.), never below the floor. Pinned-role floors reach over the **full available enumeration**, not the band-scoped set. Effort = f(boundedness) is set from `reasoning_modes.depths` AFTER the pin: fully-bounded → 1; partially-bounded → 2 (or 3 on a single-mode ladder); unbounded → 4/5. The verdict `effort` is always the 1–5 integer (an inert ladder still takes the number; `cast` emits no effort argv for it). |

**`other`-routing audit (D4).** When `leaf_role == other` (the catch-all role), `cast route` records the specific task instructions/arguments in the verdict's `other_routing_audit` field so under-served task types surface and get promoted to first-class roles. The profile builder sets `leaf_role` explicitly; the closed `routable_for` vocabulary is `{bounded-code, unbounded-code, reasoning, web-research, text-synthesis, other}` (D12 — `judgment` removed).

**Total order — never collapses.** The six RANK keys break every tie in sequence, and Key 6 closes it absolutely: every enumerated `(harness, model, carrier)` row is distinct, so two distinct survivors ALWAYS differ on Key 4, 5, or 6. The selector is NEVER non-deterministic for any legal catalog. If zero rows survive the GATE, degrade per §1 (next-capable / Agent-tool Claude fallback) or HALT — NEVER silently pick an incapable row.

**Name the chosen pair — never a bare provider.** Every logged or summarized assignment names the chosen `(harness, model)` plus `effort` plus `carrier` — e.g. `claude/sonnet-5` `effort=2` `carrier=agent-tool`, `api/deepseek-v4-flash` `effort=1` `carrier=api` — NEVER just "Claude" or "DeepSeek". A bare-provider label in the run-log or intake budget summary is the collapse this selector exists to prevent.

**Text-leaf clause — where API chat workers compete.** API chat workers carry a `routable_for` list that omits the code roles, so §2a's GATE (D13) drops them from EVERY code leaf. They survive ONLY on TEXT leaves — partially-bounded text synthesis, mechanical text transforms, desk-research synthesis over inlined sources — where they compete on `cost` (integer 1–7) against the Claude tiers. NEVER route a code leaf to an API chat worker; the GATE already bars it, and a manual override is a routing defect. An API pick hands off to `cast api`, not `cast <harness>`.

### 2b. The footprint axis — size the worker to the known input

A task declares its **known input** — `known_input_size` (tokens) = the dispatch prompt + the files the task is required to read — and the §2a GATE refuses any worker whose window is too small to hold it comfortably, so a large-footprint task never lands on a worker that overflows mid-run (Claude auto-compaction; Codex `"ran out of room"` crash). The router CONSUMES `known_input_size`; the PLANNER produces it (measure the read-set, chars→tokens ÷3 round up) — never measured here.

| Rule | Detail |
|------|--------|
| **Footprint GATE** | When `known_input_size` is present, §2a's window check becomes the utilization cap: a worker passes only if `context_window ≥ ceil(known_input_size / window_utilization_cap)` (default cap 0.20 ⇒ window ≥ 5× input). This REPLACES the `inlined_context_size` check for that worker (the known input ⊇ the inlined prompt). |
| **Cap config** | `window_utilization_cap` reads from `rbtv.json` — tunable without a code change. Absent or outside `(0, 1]` → default `0.20`, logged. One workspace-global value, never a per-task field. |
| **Biggest-capable fallback** | When NO worker clears the cap, route to the worker with the LARGEST effective `context_window` among those passing every non-window gate (reasoning / coding / web / `routable_for`; haiku excluded) — over the FULL enumeration so Opus/1M is reachable. This deliberately exceeds the cap: the accepted last resort for an input above `cap × largest_window`. No eligible worker (a non-window gate barred all) → the existing `zero_candidates` path, unchanged. Pinned-role floors (§3) still apply to the fallback pick — they only raise. |
| **Back-compat** | A profile with NO `known_input_size` routes byte-identically to pre-footprint behavior: the GATE uses `context_window ≥ inlined_context_size`, the cap is inert, and the fallback never fires. |

Out of scope here: no `split` verdict (no corpus slicing across workers); no over-1M halt (the tail is deliberately not engineered — the fallback routes to the biggest worker regardless).

---

## 3. Pinned roles — never route down (D4)

Some roles carry a floor that boundedness, budget, and cheapness CANNOT lower. Pin them before finalizing any assignment:

| Role | Floor | Why (evidence) |
|------|-------|----------------|
| **Conductor / orchestrator** | **fable** — `claude` / `fable-5` (carrier-resolved per §4), falling back to **opus** (`claude` / `opus-5`) when fable is unavailable. The default conductor tier. The most senior available Claude conducts; it never routes down to a worker tier. | The conductor pin is fable, with opus as fallback when fable is unavailable. Conducting is the highest-judgment seat in the run. **This pin is live** — `cast route` searches the full available set for those Claude rows and raises to them. |
| **Final-plan reviewer** | **fable** — `claude` / `fable-5`, falling back to **opus** (`claude` / `opus-5`) when fable is unavailable — the default pin for the cold review of a generated plan before execution. | Fable cold-reviews the generated plan before any execution begins; opus reviews when fable is unavailable. **This pin is live** — same full-set search as the conductor pin. |
| **Reviewer** | ≥ executor tier + 1, floor **sonnet**, **never haiku**. **Opus reviews ALL external-CLI code.** | Review+fix out-ROI'd authoring across all three hypresent sessions; a sonnet reviewer caught 7 blockers pre-build in one pass. Opus review of CLI-worker output caught inverted contracts and over-generalizations a cheaper reviewer would miss. |
| **Cold verifier** | Independent worker, fidelity-floor capable; receives ONLY the contract criteria + running artifact (never the builder's tests/claims/sheet) | Mandatory for development dispatches (verification card owns the firing schedule). Not a cost-optimization target. |
| **Debug roles** | Any **reasoning-7 code-eligible executor** — fable, opus, **and** `codex` / `gpt-5.5`; **opus is the default on cost**. DEBUG-AGENT and live-debug-with-owner. | Live-validated fix specs landed first-try across 6+ dispatches; debugging interaction bugs is judgment-dense by nature. D17 de-carrier-locks the floor: gpt-5.5 is reasoning 7 / coding 7 (a peer top-tier executor), so an opus-exclusive pin wrongly excluded it; the floor now keys on the reasoning integer ≥ 7, not Claude membership. Opus (cost 6) still outranks the cost-7 peers (fable, gpt-5.5), so the observable default is unchanged — a cost-7 peer wins debug only when opus is unavailable/capped. |
| **Commits** | Routed through a worker invoking `rbtv-commit` — never folded into an executor's own run. Carrier: an **Agent-tool Claude** (sonnet floor) invoking `rbtv-commit`; CLI executors are not the commit worker. **When NO Claude is available**, fall back to the **strongest available reasoner** (the `reasoning` integer ranked DESCENDING, cost ignored) — never the cheapest non-Claude worker, never an error. | Commit hygiene, message quality, exclusion lists, and no-push guarantees require the skill; CLI workers are kept OFF commits deliberately — relaxed ONLY when Claude is entirely unavailable, where the strongest reasoner beats both a cheapest-by-cost pick and a hard block. **The pin searches the full available set for `claude` / `sonnet-5` / `carrier: agent-tool` directly** — it does not first scope the eligible set by boundedness. An unbounded profile therefore still floors at agent-tool sonnet, not at the strongest-reasoner fallback. |

A pinned role that the boundedness tree or budget filter would have sent lower is RAISED to its floor here. Pins win over every other routing input.

> Fable is available for the conductor / final-plan-reviewer pins, with opus as fallback when unavailable. Both pins are real and tested — they are not no-ops.

> **Debug floor is reasoning-≥7, carrier-agnostic.** The `debug` pin no longer requires Claude membership — it admits any available, code-eligible executor with **reasoning ≥ 7**. Reasoning-6 workers and non-code API workers stay barred. **Observable default unchanged:** opus (cost 6) outranks the cost-7 peers (fable, gpt-5.5) under the §2a cost-ascending RANK, so a standard debug task still picks `claude` / `opus-5` / `carrier: agent-tool`; a cost-7 peer wins debug only when opus is unavailable/capped.

> **Commit pin, Claude-unavailable fallback.** The `commit` pin searches the full available set for `claude` / `sonnet-5` / `carrier: agent-tool` directly. When that row is absent it falls back to the **strongest available reasoner**: the `reasoning` integer ranked **DESCENDING, cost ignored** (haiku excluded; ties broken by the §2a cost-ascending house order). **Claude-available behavior:** commit → `claude` / `sonnet-5` / `carrier: agent-tool`. Commit is the SOLE Claude-floor pin with a non-Claude fallback — reviewer / conductor / final-plan-reviewer stay Claude-only-or-error.

**Within the top Claude tier — opus.** Opus is the top-tier Claude for senior roles: debug, and cost-sensitive high-judgment WORKER dispatches (architecture spec, rule edit, judgment-dense leaf) — plus the fallback for conductor and final-plan reviewer when fable is unavailable (those two roles pin to **fable** first). (Debug, since D17, also admits the non-Claude `codex` / `gpt-5.5` — opus remains its default on cost; conductor and final-plan-reviewer stay Claude-pinned.) Opus carries `cost: 6` (integer 1–7 scale) — the §2a RANK therefore never auto-picks opus for a cheap fully-bounded leaf (cost-ascending rank routes cheapest-capable first). For the finer within-tier "best at" disambiguation between any two same-tier rows, consult each row's catalog `specialty` when present — a within-tier tiebreaker, never a new master cut.

---

## 4. Topology — one Agent-tool level, CLI fleets below (D7)

The delegation shape is fixed by a hard environmental wall, encoded honestly:

| Rule | Detail |
|------|--------|
| **One Agent-tool level** | Agent-tool sub-agents CANNOT spawn sub-agents (the nesting wall — documented 4× across pilots). The conductor's own Agent-tool dispatches are a single level; never design a routing that asks a sub-agent to dispatch its own sub-agents. |
| **Sub-conductors via process boundary** | A second conductor level is achieved ONLY through CLI workers — a Claude helper drives `cast` (codex / claude-cli / opencode) as separate OS processes (a process is not an Agent-tool sub-agent, so the wall does not apply). CLI workers natively load the workspace `CLAUDE.md`/rules; Agent-tool helpers do not. |
| **Depth cap ≤ 2 conductor levels** | The top conductor plus at most one CLI-driven sub-conductor. Do not stack deeper. |
| **Launch-root confinement (G1)** | Every CLI worker launches with its launch-folder = the **orchestrator root** and the work-target passed separately — follow the dispatch-wrapper card §1 G1 row (the policy lives there; mapped onto cast launch-folder semantics). Routing's obligation: record the launch-root and work-target as SEPARATE values in the assignment it hands the wrapper — never collapse them into one "work-dir", and never assign a nested-repo work-target as a worker's launch root. |
| **Pre-dispatch guidance-file check** | Before routing code work to a CLI worker, confirm the **LAUNCH ROOT** (the orchestrator root the worker's guidance keys to — NOT the work-target) carries that worker's guidance file (`AGENTS.md`, the agent file, etc.). The work-target needs NO guidance file or mirror of its own — the mirror skips nested git repos BY DESIGN because workers never root there. **Defer condition:** if `.agents/behavior-rules/` exists at the launch root, the driver owns the guidance file — do NOT create or refresh it; STILL verify the worker's guidance file is present, but NEVER overwrite it (the driver, not this check, regenerates a driver-owned file). If `.agents/behavior-rules/` is present but the worker's guidance file is MISSING, do NOT create it here — flag the user to re-run the mirror driver (it owns that file). Only when `.agents/behavior-rules/` is absent: if the guidance file is MISSING, flag the user and offer to create it via the workspace mirror. Never silently dispatch a CLI worker from a launch root that lacks its guidance file. |
| **Pre-dispatch mirror REFRESH** | Presence is not currency. The worker's RULES LIBRARY (`.agents/behavior-rules/`, `.agents/skills/`) refreshes ONLY when the installer runs and is gitignored — so a skill or rule edited since the last run reaches a claude worker and NOT the codex/opencode worker beside it, with nothing in git ever revealing the drift. ⚠ This refresh covers the `.agents/` library and the per-harness config dirs ONLY: `install.py --mirror` no longer renders any `AGENTS.md` (retired, `d-hard-guard-retire-model-mirror`, 2026-08-10). A stale or missing GUIDANCE file is refreshed by the modern installer instead: `python <rbtv_path>/install2.py install --target <launch-root> --guidance-basis CLAUDE.md`. Before the FIRST CLI-worker dispatch of a run, refresh the mirror at the launch root: `python <rbtv_path>/install.py --mirror --non-interactive --target <launch-root>` (`rbtv_path` from the launch root's `rbtv.json`; it is idempotent write-if-changed, ~2-3s steady-state). Refresh ONCE per distinct launch root per run, not per dispatch. **NEVER pass `--exclude`** — it is inert since the guidance retirement, but passing it still REPLACES the workspace's recorded exclusion list in `rbtv.json`. A refresh that fails does NOT block the dispatch: report it and dispatch anyway (a stale mirror still carries the previous render's rules; a blocked run carries none), but say so in the run's state. Skip entirely when the launch root has no `rbtv.json` — that workspace has no mirror by design. A team-kit run needs no manual step: `coord.py launch` and `close-seat --renew` already refresh every non-claude seat's root before the pane opens. |
| **Composition check** | `cast` owns and tests its argv. The conductor's composition check is `cast --dry-run` (dispatch-wrapper card) — not a per-dispatch `--help` scrape, not a delta Pre-flight, not a profile resolve. A dry-run that refuses → STOP, do not dispatch. |
| **In-session spawn permission (D17)** | A CLI worker spawned from inside a Claude session is permitted by installer-managed PREFIX allowlist rules — and a prefix rule matches ONLY a command line that BEGINS with the worker binary. Compose every in-session CLI dispatch per dispatch-wrapper §1's D17 row: the line begins with `cast`. A spawn denied DESPITE a matching binary-first rule (a session-mode classifier denial — observed once) → do not retry shaping tweaks: degrade the carrier per this card, or hand the exact command to the owner as a `!`-typed dispatch. |

**Resolving the agent-type axis (which the boundedness tree leaves open).** The tree picks a tier (cheapest-capable / mid / top); this step picks the CARRIER for it.

**Two distinct Claude carriers — both enumerated as separate catalog rows.** Claude is enumerable through TWO carriers, NOT one: `carrier: agent-tool` (the **Agent-tool** in-session carrier, dispatched via the Agent tool — `claude` / `opus-5` / `agent-tool`, `claude` / `sonnet-5` / `agent-tool`) and `carrier: cli` (the **`cast claude …` process** carrier). The §2a selector enumerates BOTH as distinct rows; they differ in routing-relevant properties (the Agent-tool carrier does NOT natively load workspace `CLAUDE.md`/rules and cannot spawn sub-agents — the nesting wall; the process carrier loads workspace rules natively and clears the nesting wall as a separate OS process). NEVER collapse the two Claude carriers into one entity. `cast` refuses to launch `carrier: agent-tool` rows; dispatch those via the Agent tool.

| Tier the tree chose | Carrier |
|---------------------|---------|
| A Claude tier (mid or top) | Default to **`carrier: agent-tool`** — the **Agent-tool** in-session carrier (no guidance-file dependency, no process overhead). Use **`carrier: cli`** (`cast claude …`) instead ONLY when a process-boundary sub-conductor is needed (the worker must itself drive CLI workers — the nesting wall forces a process) or when native workspace-rule loading is required. Both are enumerated distinctly by §2a; this row picks BETWEEN the two carriers for the chosen tier. |
| A code-executing CLI leaf | Choose among catalog `carrier: cli` rows by catalog fit, not preference: opencode (including kimi models — kimi-code-cli is retired) and codex are the live CLI executors. Pick on the catalog's `coding` / `cost` / `web_access` / quirk fields for the specific task. Absent a distinguishing catalog reason, take the §2a cheapest-capable pick and log the choice. **Windows capability-run / live-call caveat:** codex's `workspace-write` sandbox DOES spawn subprocesses on Windows — `git`/`node`/`pwsh`/`cmd` all run (TESTED 2026-06-14). The boundary is codex's APPROVAL ROUTER, which declines `python`/`python -c` (so python/pytest-based validation fails under `approval_policy="never"`), NOT a spawn-capability limit. A **live/network API call also WORKS** under `workspace-write` when dispatched with `-c sandbox_workspace_write.network_access=true` through an auto-approved client (TESTED 2026-06-14: `node` fetch → HTTP 200; without the flag, egress is refused; `danger-full-access` not required). So codex CAN self-validate a leaf whose check is `git`/`node`/`pwsh`/`cmd`-based, AND can make a granted live call. Route to another catalog CLI row OR split the dispatch (codex authors the edit, conductor runs the validation as an exit-probe) ONLY for a leaf whose acceptance needs a **python/pytest** run, or a **live/network call** that cannot be granted egress or must run through `python` — do NOT blanket-split every codex capability-run or every live-call on Windows. |

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

When a task's deliverable touches the **web**, route it by which of THREE distinct web tiers the task needs — the tiers differ in autonomy, rigor, and cost, and the §2a selector already enumerates every `web_access: true` worker for the leaf. Honor each named worker's catalog `evidence_status`: a `probe-pending` tier worker routes only with the unvalidated-seam discipline of §9, never as a settled choice.

| Web tier | When it fits | Route to |
|----------|--------------|----------|
| **Autonomous-web** | The agent must navigate, click, fill, and synthesize across pages on its OWN — multi-step browser-driven data collection, not a single lookup | The **manus-api `manus-autonomous`** agentic worker (`web_access: true`, per-task cost, minutes-scale latency, raw-dump return). manus-api's `routable_for: [web-research]` omits the code roles, so §2a's GATE already drops it from every code leaf (D13) — never route code here. Hand off via `cast api`. |
| **Light grounding** | A single grounded lookup — one search-grounded call, light not rigorous | The **Gemini** API worker (the only `web_access: true` chat worker). Hand off via `cast api --grounded`. |
| **Rigorous multi-source research** | Source evaluation, citations, cross-checking across many sources | The `rbtv-web-searching` Agent-tool path, or an available `web_access: true` CLI worker that §2a enumerates for the leaf — NEVER an API chat worker. |

For a rigorous-multi-source brief (a self-contained research brief → findings), apply the rows below:

| Rule | Detail |
|------|--------|
| Route by catalog | Send the brief to an available worker whose catalog row declares `web_access: true`. Match the brief to a worker that can actually reach the web. (NOTE: most code-CLI rows are NOT web workers — opencode is `web_access: false` (webfetch only, no search); route web research to a web-declaring worker or the Agent-tool path.) |
| API web access is Gemini grounding only — light | Among the API workers, ONLY gemini carries `web_access: true` (search grounding), and it is **light web** — a grounded single-call lookup, NOT rigorous multi-source research. If an API worker must reach live web, it MUST be gemini. For rigorous multi-source research (source evaluation, citations, cross-checking) prefer the `rbtv-web-searching` Agent-tool path (or an available CLI worker whose catalog row declares `web_access: true`) — never an API chat worker. |
| Degrade when no web-capable row | If NO available catalog row declares web access, route the research brief to an **Agent-tool sub-agent carrying the `rbtv-web-searching` directive** (the in-session web path — always available). If even that is unavailable, HALT and surface — never dead-end the research leaf. |
| Carry the sources manifest | If the user or workspace provides a curated preferred/banned-sources file, the dispatch carries a **pointer** to it; the web-searching skill loads it when pointed and skips gracefully when absent. rbtv ships only the generic mechanism — the sources file itself stays user/workspace-side. |
| Name the web skill in the dispatch | The dispatch MUST carry the `rbtv-web-searching` directive in imperative form ("invoke `rbtv-web-searching` before any web work and follow it exactly") — the rbtv-sub-agents mandate. The dispatch-wrapper card packages this; routing's job is to mark the task as a research leaf so the wrapper includes the directive. |
| Self-contained brief | The brief carries its own question, scope, and integration target — the worker reads nothing from conversation history. |

---

## 7. The haiku clause (D4)

Haiku eligibility is routing policy and is owned HERE (moved from `core/rules/sub-agents.md` — that rule no longer carries model policy). Default model posture: sub-agent dispatches default to `sonnet`; haiku is NEVER routed without the explicit ask below.

| Condition | Haiku eligibility |
|-----------|-------------------|
| User-approved delegation map names haiku for a specific mechanical batch | Routable for THAT batch — the map approval IS the required explicit ask; no separate per-dispatch permission needed once the map is approved |
| No approved delegation map naming haiku for the batch | NEVER routed — default to the cheapest **non-haiku** capable row; every pinned role (§3) floors at **sonnet** regardless |
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
| Default to the most-validated leg | For code, the CLI fleet (a catalog CLI executor + Claude reviews) is the validated default; sdd is the deliberately-chosen alternative set at intake, not a router guess. Do not auto-route a run onto the least-validated leg. |
| Halt on strategy uncertainty — only when undetermined | This halt fires ONLY when the strategy is NOT already determined upstream: the code backend set at intake (CLI fleet vs sdd), an automatic strategy leaf (§5 sdd, §6 research), and a single strategy surviving the boundedness tree + filters are all already-determined — take them, do NOT halt. The halt is for the residual case. **Concrete test:** if the boundedness tree + STAKES/BUDGET filters yield exactly ONE strategy, take it. Halt ONLY when ≥2 whole strategies survive the filters AND they differ materially in cost OR validation status — present the options with tradeoffs (cost, validation status, fit) and let the user pick. A downgraded conductor (D9) halts on ANY surviving multiplicity. A halt costs minutes; a wrong strategy costs the run. Never paper over a genuine multiplicity with a confident-sounding pick. |
| Label it honestly in the run-log | Record strategy-level routing choices in `run-log.md` as decisions with their rationale, flagged as operating on the unvalidated seam, so the first real long-horizon run becomes evidence for this leg. |

This section is the card telling the truth about its own weakest point — keep it; do not let a future edit quietly upgrade the seam to false confidence.

---

## Hand off to the dispatch-wrapper

Routing's output is an assignment: the chosen `(harness, model)` plus `effort` plus `carrier`, the role pins applied, the topology, the strategy leaf, and the batch/allowlist shape. Open the **dispatch-wrapper card** to package it into an actual dispatch (binding addenda, unified return schema, evidence paths). Do not dispatch from here — the situation table in the core protocol points to the wrapper; follow the situation, not a hardcoded chain.
