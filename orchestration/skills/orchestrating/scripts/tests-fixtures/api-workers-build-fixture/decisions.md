# Decisions - API Workers Build

> **Purpose:** This document captures shaping decisions, discoveries, constraints, and references that future agents need. The Original Shaping section is immutable. Other sections are append-only during routine execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- Adds an **API-worker class** to `rbtv-orchestrating`: text/synthesis tasks routed to non-CLI models via one provider-agnostic runner.
- Ships **three chat text-workers** (DeepSeek, Gemini, OpenAI) — text-in/text-out, JSON-envelope output — behind a single `models/_api/run.py`.
- Adds **Manus** as a distinct **agentic worker** (task-create → poll → raw-dump) riding the same runner — NOT a chat worker.
- Makes the orchestrator's worker selection **deterministic and per-`(model, variant)`**: multi-variant manifests + an enumerate→filter→rank selector that never collapses a provider to a single entity.
- **Models the Agent-tool Claude tiers** (`opus`/`sonnet`) as a manifest package so they are enumerated like every other worker.
- Wires all of this into the conductor (routing / dispatch-wrapper / verification / intake / core-protocol / manifest-schema cards), `install.py` (the API-key `env_file`), and the docs-sync surfaces.

**What this does NOT include:**
- **Code execution** by API workers — a chat/agentic API cannot write to the repo, run tests, or commit. Code stays with kimi/codex.
- The Manus **master-script router** (`detect_strategy`, fallback chains) — dropped; the Claude conductor is the router.
- Rigorous multi-source **web research** — except Gemini grounding (light) and Manus autonomy. Real research stays on `rbtv-web-searching` / qwen.
- Building an **agentic tool-execution loop** for the chat clients (their tool-calls are not executed).
- **Cohere** and **anthropic-api** providers — deferred. (Cohere is an easy chat add later; anthropic-api is redundant with Claude.)
- A **universal CLI+API dispatch script** (Options B/C) — the shared runner covers API workers only; CLI and Agent-tool keep their surfaces. The uniform *contract* (one task file + five-field return) is the unifier, not one script.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| New worker class | API worker = text-in/text-out chat-completion worker | Lets the conductor route text/synthesis to cheaper/specialized non-CLI models |
| Architecture | ONE shared runner (`run.py`) + per-provider clients + routing-only model packages | Single agent-facing script; provider complexity hidden behind `base.py` |
| Chat providers | DeepSeek, Gemini, OpenAI | OpenAI-ish shapes + JSON mode; adapted from the Manus source clients |
| Manus | Separate **agentic** worker (task-create+poll+raw-dump), own slot on `run.py` | Manus's API is an autonomous-agent task API, NOT chat-completion — forcing it into the chat envelope would cripple it (permanent raw-dump) or misrepresent its value |
| Cohere | **Deferred** | Non-OpenAI-compatible; most likely unused; easy to add later as a chat client |
| Web access | Gemini grounding (light) + Manus autonomy (browser); rigorous research stays on `rbtv-web-searching`/qwen | Only Gemini carries native `web_access` among the chat workers; Manus is the autonomous-web leaf |
| API-key discovery | `env_file` in `rbtv.json`, found by walking up to the workspace root; **OS-env first**, file fallback | Mirrors the vault's existing convention; same anchor mechanism as `sb-os.json` |
| Execution surface | API-only shared script (Option A) | Agent-tool isn't scriptable; CLI failure-recovery is deliberately conductor judgment a wrapper can't own |
| Schema fit (CLI-shaped required fields) | **(a) Repurpose** `headless`/`tool_surface`/`confinement`/`swarm_support` with API-meaningful values | No schema churn; repurposed values are honest routing signal. `transport:` discriminator is the documented escalation if the pilot shows the router misled |
| Engine namespace | `models/_api/` | Matches existing infra-dir precedent (`models/mirror/`, `models/_fixture/`); routing folder-scan skips underscore dirs |
| Output location | **Deliverable-scoped** — conductor points `--output-folder` at the content's final destination | Reconciliation is against the runner's `landed` list (not "folder non-empty"), since the destination may already hold files |
| Provider phasing | Ship 3 chat + Manus; Cohere deferred; the DeepSeek pilot validates mechanically (not a hard build-gate) | Keeps the chat class coherent; Manus is its own gated phase |
| Manifests are multi-variant | Each provider's distinct routing-relevant models/modes are separate `(model, variant)` rows, capped to variants that change a routing decision | "Treat each model/mode as its own agent"; avoids variant explosion (field-count discipline applies to variants) |
| Deterministic selection | Enumerate all installed `(model, variant)` → filter to leaf-capable → rank by total order (`cost_class` → `evidence_status` → `reasoning_tier` fit → name); name the chosen pair, never collapse a provider | Makes worker selection a pure function once the leaf's requirements are scored; only requirement-scoring + stakes stay judgment |
| Claude-tier modeling | New `models/claude/` package (Agent-tool `opus`/`sonnet`; haiku excluded by the sonnet floor), **sibling to** `models/claude-cli/` (process) | The Agent-tool tiers had NO manifest — that absence IS the intake-summary collapse. Modeled like every other worker; the two Claude carriers stay distinct (in-session vs process) |
| Run mode | Orchestrated, **DEEP** pre-resolution | High-stakes (edits the live orchestration cards every dispatch depends on); decision-dense; AFK-capable |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Build in the **rbtv source repo** (`3-resources/tools/rbtv/orchestration/`); never edit `.claude/` | rbtv `CLAUDE.md` source-of-truth rule | Worker work-dir is the rbtv repo; allowlist paths are rbtv-repo-relative |
| Docs-sync hard rule: any component add updates `README.md` + `modules/` + `admin/install/module-manifest.json` in the SAME change | rbtv `CLAUDE.md` | Each new component (runner, clients, packages, reference doc) carries a docs-sync task |
| Re-render manuals after `dispatch-wrapper.md` / any `delta.md` edit | `render-manuals.py` (manuals are generated) | Render runs are tasks; zero-diff expected for unchanged manuals |
| Runner resolves its client by provider name dynamically (`clients/{provider}.py`) | This plan (architectural constraint) | Adding a provider = add a client + a package; NEVER edit `run.py` — keeps provider adds parallel-safe |
| Keys never inlined into prompts, dispatches, run-logs, or commits | design §9/§12 | The runner loads its own key; the conductor never handles keys |
| Done-gate governed: pilots ARE the exercises; a cold verifier re-exercises | `rbtv-done-gate`, design §0.5 | Each pilot captures evidence files; builder/verifier mismatch fails the dispatch |
| Cross-repo: one vault-side file (`.user/config/env/.env.example`) | this plan | That task's work-dir is the vault, not the rbtv repo |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Output location | "Deliverable-scoped" | Conductor points `--output-folder` at the final destination; reconcile against `landed` |
| 2 | Manus | "Ship 3 (as in option 2) and also Manus AI (manus AI has API too)" | Surfaced that Manus is an agentic task API → modeled as a separate agentic worker, not a chat provider |
| 3 | Manus (after explanation) | "lets also consider manus" | Manus added as its own "assign-a-job" slot riding `run.py` |
| 4 | Multi-variant routing | "Different models of same provider should be treated as different agents, totally… the orchestrator should have clear rules on how to use each" / "can we make this evaluation deterministic?" | Multi-variant manifests + a deterministic enumerate→filter→rank selector (total tiebreak order) |
| 5 | Claude collapse scope | "Expand this plan to also fix Claude" | New `models/claude/` Agent-tool package + intake-summary enumeration fix |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Manus as a provider | Include Manus alongside the 3 chat providers ("has an API too") | Manus's API is autonomous-agent (task-create → poll 5 min → retrieve), not chat-completion; forcing it into the chat envelope cripples it | Manus added as a **distinct agentic worker** with task/poll/raw-dump transport, its own manifest + verification path + routing leaf — riding the same `run.py` |
| 2 | Fixing the Claude "single entity" collapse | The orchestrator must evaluate each model/mode as a distinct agent, deterministically | Root cause: the **Agent-tool Claude tiers have no manifest** (only `claude-cli` does); the deterministic selector + a `models/claude/` package fixes it | Expand the plan: new `models/claude/` (Agent-tool tiers), deterministic selector + "never collapse a provider" in routing, intake-summary enumerates `(model,variant)` |
| 3 | Determinism of selection | Wants deterministic evaluation | Selection is a pure function (enumerate→filter→rank) ONLY with a **total tiebreak order** + **variants capped to routing-distinct** | Selector defined with a total order; variant lists capped — see `specs/deterministic-routing-spec.md` |

---

<!-- BEGIN PLAN-SPECIFIC -->
## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| `rbtv-done-gate` | Each provider pilot + the live orchestrated pilot are the contracted exercises; evidence sheets cite captures; a cold verifier re-exercises at the fidelity floor (real API call, real files) |
| `rbtv-build-for-agent-testability` | Drivability check at Contract: the API call IS agent-drivable (a real call writing real files to a real output folder), so the pilots are the seam — no native-dialog seam needed |
| `rbtv-atomic-files` | Manifests, cards, and deltas stay self-contained; references are functional-only |
| `rbtv-source-of-truth` | All components built in the rbtv source repo; installed `.claude/` copies are never edited |
| `rbtv-sub-agents` | Orchestrated dispatches name matching skills (`rbtv-commit` for commit tasks); CLI workers kept off commits |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Runner never edited per provider | `p3`/`p2` client tasks add `clients/{provider}.py` only; a `run.py` diff touching provider dispatch (other than the agentic flag in p5-3) is a review finding |
| Repurposed schema fields, not a `transport:` enum | Manifest tasks fill the CLI-shaped fields with API-meaningful values; a schema-enum change is out of scope unless the pilot proves the router misled |
| Keys never surfaced | Any key value appearing in a prompt/dispatch/run-log/commit is a hard review failure |
| Deterministic selector is a total order | The selector spec's Test Plan exercises that no two enumerated variants tie under the full order |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |
<!-- END PLAN-SPECIFIC -->

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

<!-- Decisions and discovery entries will be appended below this line -->

### D-exec-1: `env_file` pre-seeded into vault-root `rbtv.json` at intake (before p4-4)

- **Decision:** The conductor recorded `env_file: .user/config/env/.env` in the vault-root `rbtv.json` and seeded that `.env` with 4 empty key placeholders (DEEPSEEK/GEMINI/OPENAI/MANUS_API_KEY) at intake, so Phase 1's DeepSeek pilot can resolve a key via the file-fallback path before the install.py change (p4-4) exists.
- **Rationale:** p4-4 (install.py `env_file` prompt) runs in Phase 4, but the first paid pilot is p1-checkpoint in Phase 1 — the runner's key discovery needs `env_file` present earlier. Seeding the value at intake unblocks the load-bearing pilot without reordering the plan.
- **Scope:** Affects **p4-4** — it builds the install.py PROMPT mechanism and must be **idempotent**: detect an already-present `env_file` and not duplicate, overwrite-without-confirm, or error on it. Affects the runner (p1-4) only in that the file-fallback path is exercised from Phase 1.

### D-exec-2: OpenAI chat-API worker DROPPED (deferred like Cohere)

- **Decision:** The OpenAI chat-API text worker (**p2-3** `openai.py`, **p2-4** `models/openai/`) is dropped from this build, deferred like Cohere. Phase 2 ships **Gemini only**; the "chat trio" becomes a **chat duo** (DeepSeek + Gemini). `OPENAI_API_KEY` is NOT required and is not in `.env`.
- **Rationale:** User decision — `codex` CLI already covers OpenAI-for-CODE via its own auth (not an API key), and Claude (premium text) + DeepSeek (cheap text) + Gemini (web text) already span text-synthesis. A GPT text worker is the least-differentiated slot; the design's own risk note flags API workers "may sit unused." Re-addable later at low cost (same OpenAI-compatible shape as DeepSeek). User: "drop it, codex orchestration goes through CLI."
- **Scope:** Do NOT build **p2-3, p2-4** (marked ⏸ deferred). Amends **p2-checkpoint** → chat-**duo** (DeepSeek + Gemini), not trio. Affects **p4-5** (`.env.example` adds 3 key names, not 4), **p1-6** (routing-matrix-reference notes OpenAI is codex-CLI-routed, not an API worker), **p4-3/p4-7** (no openai package to enumerate/sync). `codex` remains the routable CLI code executor.

### D-exec-3: Manus agentic-web manifest needs a THIRD §2a repurposed-values block (schema gap surfaced at p1-1 review)

- **Decision/Discovery:** The opus review of p1-1 confirmed `manifest-schema.md` §2a covers TWO repurposed-value blocks — API chat workers AND Agent-tool Claude (`models/claude/`). It does NOT yet canonically cover an **agentic-web** worker (Manus: `structured_output: false` + `web_access: true` + task-create/poll transport). Filling a Manus manifest from the current §2a would require guessing.
- **Rationale:** p1-1 scoped the repurpose for the chat workers + Claude tiers; Manus's agentic profile differs (no structured output, browser autonomy, per-task cost).
- **Scope:** Before or at **p5-2** (Manus package), add a third §2a repurposed-values block for the agentic-web class to `manifest-schema.md` (or fold the schema amendment into p5-2). Does NOT block Phase 1 (DeepSeek uses the unambiguous API-chat-worker block). Carried from the p1-1 opus review.

### D-exec-4: DeepSeek stays the API text worker; qwen-code (deepseek/glm/qwen3.6) is a separate CLI capability

- **Decision:** DeepSeek remains an **API chat (text-synthesis) worker** as planned (p1-3/p1-5 proceed). It is NOT moved to the qwen-code CLI. User chose this (option A) after weighing it.
- **Rationale:** qwen-code is a code/agentic executor (a DIFFERENT role than text-synthesis — it writes files/runs commands, it is not a clean text→JSON endpoint). DeepSeek-API is the cheapest text model ($0.14/$0.28) AND the runner's simplest OpenAI-compatible load-bearing proof; its client wasn't built yet, so keeping it wastes nothing.
- **Discovery (forward / follow-on):** User authed `qwen` (Qwen Code CLI), which can invoke `deepseek-v4-pro/flash`, `glm-5.1`, `qwen3.6-plus` via ModelStudio (OpenAI-compatible) — making qwen-code a viable MULTI-MODEL CLI code-executor (model diversity + GLM access). NOT built in this plan (out of scope: this plan ships API text/agentic workers). Follow-on: enable/validate the `qwen` package (already in the roster, probe-pending) as a CLI code worker with model selection.
- **Scope:** Phase 1 unchanged. The "does DeepSeek-API earn its keep vs qwen-deepseek" redundancy judgment folds into **p6-1**'s earn-their-keep test. qwen-code enablement = separate future work.

### D-exec-5: Gemini model ids are unverified estimates — the client is id-agnostic; verify live before the paid pilot

- **Discovery:** The Gemini model ids in `routing-matrix-reference.md` / the source `gemini_client.py` (`gemini-3.5-flash`, `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite`) are 2026 ESTIMATES, not confirmed-live ids. `gemini.py` hardcodes NO id — it requires `--model` (raises `ValueError` if absent) — so the client is id-agnostic and the stale-id risk lives entirely in what the conductor passes at `--model` during the pilot. A wrong id yields a clean `BLOCKED` (4xx → status BLOCKED, no key leak), not a silent failure.
- **Rationale:** Opus review of p2-1 confirmed the id is supplied at call time; the builder's offhand `gemini-1.5-*` guess is not in the code.
- **Scope:** **p2-2** (Gemini manifest) lists variants with `evidence_status: probe-pending` — do NOT imply id confidence. **p2-checkpoint** MUST verify a CURRENT Gemini model id + endpoint live AND the key's free-tier-vs-metered quota BEFORE the first real call. Reusable learning: API-worker model ids in the routing-matrix reference are estimates → manifests mark them probe-pending → verify live before spend.
- **Discovery 2 (grounding ↔ JSON-mode):** Gemini rejects search-grounding + JSON mode in one request; `gemini.py` correctly omits `responseMimeType` when grounding is requested, so a grounded dispatch returns a raw-dump (`DONE_WITH_NOTES`, `raw-output.md`) rather than parsed envelope files — output is never dropped. p2-checkpoint criterion 2 ("grounding works when requested") should EXPECT a raw-dump for the grounded call and parsed files for the default (non-grounded) call.

### D-exec-6 (= D3): Gemini grounding DEFERRED to Phase 5 — client-capable, NOT run.py-wired in Phase 2

- **Decision:** Gemini search-grounding is DEFERRED to Phase 5. `gemini.py` supports grounding via `RequestOptions.extra_params["grounding"]`, but the shared `run.py` runner has NO grounding switch and passes no `extra_params` (grep-confirmed: run.py argparse = provider/model/prompt-file/output-folder/target-file only) — so grounding is NOT reachable through the runner in Phase 2. Per the architectural rule "adding a provider NEVER edits run.py", Phase 2 ships NO grounding wiring. The run mode halted on the p2-2 worker's open question about a non-existent `--grounded` flag; user chose **defer to Phase 5**.
- **Rationale:** Phase 5 already edits run.py for web/agentic handling (p5-3) and builds the web-research / autonomous-web routing leaf (p5-4) — grounding wiring belongs there as the generic "light web" counterpart to Manus autonomy. Ship Gemini's proven JSON-text path now; keep the architectural core untouched in Phase 2.
- **Scope:**
  - **p2-2 `delta.md`** MUST be corrected (opus-review binding fix): the `--grounded` flag does NOT exist in run.py — document grounding as a client capability that is NOT yet CLI-reachable (deferred to Phase 5), never as a working invocation/flag.
  - **p2-checkpoint** criterion 2 grounding clause DROPPED — the pilot proves the default JSON-mode Gemini call only.
  - **p5-3** (run.py edit) ALSO wires a GENERIC grounding/extra-params pass-through (`--grounded` and/or `--extra-params <json>` → `RequestOptions.extra_params`); gemini.py already reads `extra_params["grounding"]`. Generic (flag→extra_params), never provider-specific. See ADX-1.
  - **p5-4** (web-leaf routing) routes Gemini-grounded as the light web-research leaf once wired.
  - **manifest.yaml** keeps `web_access: true` — the capability IS present; only the runner wiring is deferred.

### D-exec-7: parallel install.py clobbered `env_file` in rbtv.json — p4-4 idempotency is load-bearing (CONFIRMED)

- **Discovery:** the p2-checkpoint Gemini pilot first failed `missing API key GEMINI_API_KEY`. Root cause: a parallel session re-ran `install.py`, which REGENERATED the vault-root `rbtv.json` (installed_at 2026-06-09T01:05:06) and DROPPED the `env_file` field D-exec-1 added at intake (it was present + working at the p1 DeepSeek pilot). The GEMINI key was in `.env` the whole time (54 chars); the runner simply could not locate `.env` without `env_file`.
- **Rationale/impact:** the runner's key discovery depends entirely on `rbtv.json`'s `env_file`; an `install.py` run that does not preserve it silently breaks ALL file-based key resolution (every API worker, not just Gemini). D-exec-1 flagged p4-4 idempotency as precautionary; this CONFIRMS it is load-bearing.
- **Scope:** **p4-4** (install.py `env_file` prompt) MUST be idempotent AND PRESERVE an existing `env_file` across re-installs (detect-and-keep; NEVER clobber). Until p4-4 ships, the conductor re-restores `env_file` before any paid pilot if a parallel install drops it — restoring the PATH only, never the key value. Reusable learning: a regenerated config file silently drops manually-added fields → re-verify `env_file` before each paid pilot.

### D-exec-8: selector 4-key order is deterministic for all CURRENT manifests but not provably total for legal FUTURE same-model variants — Key-5 tiebreak recommended (flagged for p3-checkpoint ruling)

- **Discovery:** The p3-2 opus review proved the selector's 4-key total order (`cost_class` → `evidence_status` → `reasoning_tier` fit → model-name lexical) is deterministic for ALL currently-installed manifests (8 traces over the real 13-variant set; zero ties survive all 4 keys; every same-model variant pair separates at Key-1 `cost_class`). BUT the spec's claim that the variant field-count discipline "forbids an all-four-key tie" is incomplete: that discipline only guarantees a distinct variant differs on SOME routing-relevant field, NOT necessarily a RANK key. A legal FUTURE same-model variant pair differing ONLY on a non-rank field (e.g. `context_window` or `resume_support`) where both clear a leaf's filter would tie on all 4 rank keys → non-deterministic pick.
- **Rationale:** Unreachable on today's manifests, so p3-checkpoint criterion 2 ("deterministic") PASSES as-built. But the feature's CORE property is determinism (user: "can we make this evaluation deterministic?"), and the spec asserts a totality its own order does not enforce — an internal inconsistency worth resolving for a determinism feature.
- **Recommended fix (conductor):** Add a final **Key 5 = variant-name lexical**. Two distinct rows of one model always carry different variant names, so the `(model-name, variant-name)` pair is unique by construction → provably total for ALL legal manifests. Additive; changes NO current pick (fires only when all 4 prior keys tie, which never happens today).
- **Scope:** FLAGGED for the **p3-checkpoint** ruling — NOT resolved silently mid-phase (end-to-end run; this is not a worker-doubt halt). If approved → a small erratum to `specs/deterministic-routing-spec.md` (Behavior #3 + Edge Cases) + `cards/routing.md` §2a wording, re-committed before Phase 4. If declined → reword the spec/§2a totality claim to scope it honestly ("deterministic for the installed manifest set") + log the latent edge as a known limitation. Either way, decided at p3-checkpoint.

### D-exec-9: p3-checkpoint user rulings — Key-5 hardening APPLIED + cost-first routing CONFIRMED + keystone-via-prose safeguard

- **Decision:** At p3-checkpoint (all 7 criteria HELD; builder + independent cold-verifier agree) the user approved Phase 3 with two rulings: (a) APPLY the D-exec-8 Key-5 hardening; (b) KEEP the cost-first routing policy.
- **(a) Key-5 — RESOLVES D-exec-8 (supersedes its "flagged for ruling"):** add **variant-name lexical as the selector's 5th tiebreak** (after model-name). Two distinct enumerated rows of one model always carry different variant names, so the `(model-name, variant-name)` pair is unique by construction → the order is **provably total for ALL legal manifests**, not only today's. Edits `cards/routing.md` §2a (Stage 3 + the "never collapses" paragraph: totality now rests on the unique pair, not on the field-count-discipline argument) + `specs/deterministic-routing-spec.md` (Behavior #3 + Edge Cases). Additive; changes NO current pick (fires only when keys 1-4 all tie, which never happens today).
- **(b) Cost-first CONFIRMED:** cheap text/research leaves route to the cheapest capable `(model, variant)` — today the `probe-pending` DeepSeek/Gemini API workers; keystone/judgment + review work is raised to Claude. User ruled this is intended (the purpose of adding cheaper API workers).
- **(c) Keystone-protection SAFEGUARD (cold-verifier concern):** keystone→Claude routing is enforced by **§2's explicit "a top-tier Claude" NAMING in the boundedness tree, NOT by the §2a cost-ranked selector** (which alone picks the cheapest top-tier worker, e.g. `deepseek:v4-pro` over `claude:opus`). **Any future "run §2a everywhere" simplification MUST preserve §2's keystone-Claude naming**, or it will silently route judgment-dense work to a cheaper probe-pending API worker. Standing constraint on all future routing-card edits (p5-4 web-leaf, any selector refactor). Also noted (non-blocking): `claude:sonnet` vs `claude-cli:sonnet` tiebreak is alphabetical not carrier-aware (§4 prose decides real carrier choice); Gemini `web_access` is capability not runner-wired until P5 (D-exec-6).

### D-exec-10: `deepseek.py` carries the identical `last_error` unbound latent bug (consistency follow-on, DEFERRED — not actioned in P5)

- **Discovery:** The p5-1 opus review of `manus.py` fixed a real `UnboundLocalError`-on-`retries=0` bug — `last_error: Exception` annotated but never assigned, then a bare `raise last_error` after the retry loop. The reviewer flagged that **`clients/deepseek.py` (~line 73) carries the IDENTICAL pattern**; `gemini.py` already has the correct guarded form. Post-p5-1: `manus.py` ✅ + `gemini.py` ✅ correct; `deepseek.py` ❌ still latent.
- **Rationale / severity:** UNREACHABLE today — `run.py` exposes no `--retries` flag, so `config.retries` is always `None` → the client default (3); `retries=0` is never passed. A latent consistency defect, not a live bug. `deepseek.py` is committed (d4d6e498) + Phase-1 cold-verified (passed at the floor). Fixing it now would expand p5-1's surgical scope for an unreachable path.
- **Scope (follow-on):** A tiny consistency fix to `clients/deepseek.py` — `last_error: Optional[Exception] = None` + guarded `raise` + an explicit fallback (verbatim the `manus.py`/`gemini.py` pattern). Batch it into **p6 cleanup** (p6-1 already reviews the API workers' earn-their-keep) or a standalone 1-line kimi dispatch. Out of P5 scope; captured here so it is not lost.

### D-exec-11: `qwen` is `web_access: false` in its manifest — the research-leaf's CLI web-worker naming is wrong (qwen vs codex/claude-cli); roster⇄manifest contradiction + a pre-existing §6 line inaccuracy (follow-on, DEFERRED)

- **Discovery (p5-4 opus review):** The p5-4 §6 table originally hard-named **qwen** as the rigorous-multi-source web CLI worker (following the task + D3/D-exec-6 + the `core-protocol.md` capability roster, which calls qwen "the research-leaf executor"). But **qwen's `manifest.yaml` declares `web_access: false`** — so the §2a web-filter would DROP qwen from any web leaf, making the naming self-contradictory. The p5-4 review FIXED the table row to the generic "an installed `web_access: true` CLI worker that §2a enumerates." The genuinely web-capable CLI workers per the reviewer are **codex (`--search`)** and **claude-cli (native WebSearch/WebFetch)**, NOT qwen.
- **Contradiction surfaced (needs resolution):** the `core-protocol.md` capability roster ("**qwen** — Web-capable CLI worker — the research-leaf executor") CONTRADICTS qwen's manifest (`web_access: false`). One is wrong: either qwen IS web-capable (manifest → `web_access: true`) or qwen is NOT the research-leaf executor (roster + design wrong). Resolve before relying on the rigorous-web CLI leaf.
- **Pre-existing inaccuracy (left UNFIXED — surgical, outside p5-4's additive hunk):** the existing §6 rule row "API web access is Gemini grounding only" (routing.md ~line 134, at HEAD since p3-2) still says "prefer the `rbtv-web-searching` Agent-tool path or the **qwen** CLI worker" for rigorous research — the same mismatch. It FAILS SAFE (the §2a filter drops qwen → degrades to `rbtv-web-searching`, always available), so it is a doc inaccuracy, not a routing break.
- **Scope (follow-on):** (1) resolve the qwen `web_access` truth — verify qwen's real web capability, then fix EITHER the manifest OR the roster so they agree; (2) align routing.md §6 line ~134 with the corrected table (name codex/claude-cli or the generic `web_access: true` CLI worker, not qwen). Batch into **p6 cleanup** or a dedicated routing/manifest touch-up. NOT blocking P5 — Manus (the Phase-5 autonomous-web leaf) is correctly wired; this concerns only the rigorous-research CLI leaf.

### D-exec-12: the provided `MANUS_API_KEY` is not a valid Manus `/v1` Bearer JWT — p5-checkpoint pilot BLOCKED on the credential (owner fix); the worker's auth-failure path is validated

- **Discovery (p5-checkpoint real paid call, 2026-06-09):** the first real Manus call BLOCKED at `POST /tasks` with **401 "invalid token: token is malformed: token contains an invalid number of segments"**. The `MANUS_API_KEY` in `.env` is a **95-char SINGLE-segment token** (a valid JWT has 3 dot-separated segments; the key has no `eyJ` prefix), so Manus's `/v1` API rejected it. **No task was created → NO per-task charge.**
- **Assessment — NOT a worker defect.** `manus.py` correctly sent `Authorization: Bearer <key>`; Manus parsed the Bearer header, tried to validate the token as a JWT, and rejected it as malformed — so the endpoint + header are right, and the TOKEN provided is the wrong type (a 95-char non-JWT, likely a Manus *API key* / placeholder rather than the Bearer JWT / session token the `/v1` API expects). The worker's auth-failure handling is VALIDATED at the real-API floor: 401 → `status: BLOCKED` + the HTTP error in `open_questions` + `return.json` + exit 1 + "BLOCKED | 0 files" (the spec edge "creation POST fails → BLOCKED"); the key was NOT leaked (grep clean).
- **Scope (owner action, then re-exercise — does NOT block the rest of Phase 5):** (1) the owner provides a valid Manus credential for `api.manus.im/v1` — a Bearer JWT (3 segments) — OR confirms the correct auth from `https://api.manus.im/docs`; (2) IF Manus's auth differs from `Authorization: Bearer <JWT>` (e.g. an API-key→JWT exchange, or a different header), `manus.py`'s auth needs a small adjustment (confirm vs the docs); (3) re-run the pilot → on a real task completing, flip the manus manifest `evidence_status` `probe-pending`→`validated` + capture the success evidence. Criterion 2 + the timeout sub-criterion stay unexercised until then. The Manus worker's client/runner/cards/docs/manual are all built + committed; only the live-task validation is gated on the credential.

### D-exec-13: ROOT CAUSE — the Manus client targets a WRONG/OUTDATED API; the real Manus developer API is v2 (`api.manus.ai/v2`, `x-manus-api-key`). Supersedes D-exec-12's "credential" framing — the fix is a CLIENT REWRITE, not a new key.

- **Discovery (p5-checkpoint web research, 2026-06-09, official Manus docs `open.manus.ai/docs/v2/`):** `manus.py` (built p5-1 from the source `manus-orchestation-scripts/providers/manus_client.py`, and the spec/manifest that followed it) targets an OUTDATED/INCORRECT Manus API. The 401 came from `api.manus.im` — Manus's WEB backend (which expects a JWT session token) — NOT the developer API. The REAL Manus developer API differs on EVERY axis:

| Aspect | Our client (WRONG) | Real Manus API v2 (official) |
|--------|--------------------|------------------------------|
| Base URL | `https://api.manus.im/v1` | `https://api.manus.ai/v2` |
| Auth header | `Authorization: Bearer <key>` | `x-manus-api-key: <key>` (Bearer is OAuth2-only) |
| Create task | `POST /tasks` → `201` + `{task_id}` | `POST /v2/task.create` (opt. `structured_output_schema`) |
| Poll / result | `GET /tasks/{id}` | `GET /v2/task.listMessages?task_id=…` (`status_update` events / `agent_status`) + `GET /v2/task.detail` |
| "completed" | `status == "completed"` | `agent_status == "stopped"` |
| "failed" | `status == "failed"` | `agent_status == "error"`; also `"waiting"` (needs input), `"running"` |

- **Implication:** the 95-char `MANUS_API_KEY` is very LIKELY a VALID Manus API key (webapp → Settings → Integration → "Build with Manus API" → Create API Key — custom format, no `eyJ` prefix). It was rejected only because the client used the wrong host + the wrong header. **This is a CLIENT FIX, not a credential swap** (corrects/supersedes D-exec-12). The probe-pending status + the manifest's "re-verify the API contract before the pilot" flag did exactly their job — the paid pilot surfaced the mismatch before trusting the worker.
- **Pricing (per docs):** ~$0.01/credit; a typical task ≈ 150 credits ≈ **~$1.50/task**.
- **Fix scope (follow-up dev task before re-test):** rewrite `manus.py`'s API integration to the v2 contract — base URL `https://api.manus.ai/v2`, `x-manus-api-key` header, `task.create` + `task.listMessages`/`task.detail` endpoints, the `running`/`stopped`/`waiting`/`error` → completed/failed/poll mapping, the v2 request body + response shapes (re-verify the exact `task.create` body + `task.detail` response at `open.manus.ai/docs/v2/task.create.md` + `task.detail.md`). Update the spec + the `models/manus/{manifest.yaml,delta.md}` (base_url, auth, endpoints; the ~5-min timeout still applies). Then re-run the pilot with the existing key. Sources: `open.manus.ai/docs/v2/{authentication,task-lifecycle,task.create,task.detail,task.listMessages}`.

### D-exec-14: v2 re-test HELD-SURPRISING — the worker captures the agent's NARRATION (`assistant_message.content`), not Manus FILE ARTIFACTS; enhancement to fetch attachments for substantive output

- **Discovery (p5-checkpoint v2 re-test, 2026-06-09):** the v2 `manus.py` WORKED against the live Manus API — a real task created → polled to `stopped` → output written; `return.json DONE_WITH_NOTES`, `landed: [raw-output.md]`, key NOT leaked. BUT the captured output (`assistant_message.content`, joined) was the agent's PROGRESS NARRATION (`"Fetching current USD to BRL exchange rate from a reliable source. Exchange rate report generated successfully."`), NOT the substantive deliverable (the actual rate + source + timestamp). The pilot task asked the agent to "write a report TO A FILE"; Manus produced a FILE ARTIFACT and narrated in its messages, so the message text is narration.
- **Assessment:** the v2 worker MECHANICS are VALIDATED at the live-API floor (create → poll → raw-dump works, key-safe). This is a CONTENT-RICHNESS gap, not a mechanics defect. For tasks where the agent answers IN the message text, the worker captures it; for file-deliverable tasks, the substantive output is in an artifact the client does not yet fetch.
- **Scope (enhancement follow-on, owner-prioritized):** enhance `manus.py` to ALSO fetch Manus file artifacts/attachments (via `task.listMessages?verbose=true` file/attachment events, or a Manus files/attachments endpoint — verify at `open.manus.ai/docs/v2`) and include them in the raw-dump, so the agent's substantive deliverables (not just narration) reach the owner. Optionally support `structured_output_schema` for structured tasks. Does NOT block the worker's mechanical validation; owner decides whether to do it now or as a follow-on.

### D-exec-15: routing-matrix ids/prices LIVE-CONFIRMED by two independent paid workers; `deepseek-chat`/`deepseek-reasoner` deprecate 2026-07-24 — future DeepSeek dispatches use the v4 ids; Gemini manifest variant names ARE the current live ids

- **Discovery (p6-1 live orchestrated pilot, 2026-06-09):** the Manus autonomous-web verification (3 official pages, timestamped) and the independent Gemini grounded lookup (different official surface) AGREE on every checked dimension: ALL FIVE recorded routing-matrix rows are live-CONFIRMED (`deepseek-v4-pro` $0.435/$0.87 · `deepseek-v4-flash` $0.14/$0.28 · `gemini-3.5-flash` $1.50/$9.00 · `gemini-3.1-pro-preview` $2.00/$12.00 ≤200k, $4/$18 >200k · `gemini-3.1-flash-lite` $0.25/$1.50; DeepSeek cache-hit $0.0028/$0.003625). D-exec-5's stale-id fear resolves INVERTED: the reference doc's "estimates" are the CURRENT live reality, and the pilot-era "verified" ids are the stale ones — **`deepseek-chat` + `deepseek-reasoner` are compatibility aliases being REMOVED 2026-07-24 15:59 UTC** (this very pilot dispatched on `deepseek-chat`), and `gemini-2.5-flash` (the p2-verified id this pilot reused) is previous-generation (`gemini-3.5-flash` is the live flagship; `gemini-3-flash` preview $0.50/$3.00 and `gemini-2.5-pro` also exist, absent from our table).
- **Rationale:** two paid workers, two source paths (search-grounding vs page navigation), two distinct official hosts, byte-identical data = strong corroboration; the in-review limitation (the opus reviewer could not re-verify live) is covered by that independence.
- **Scope (forward-affecting):** (1) ALL future DeepSeek dispatches use `deepseek-v4-flash`/`deepseek-v4-pro` as `--model` — NEVER `deepseek-chat`/`deepseek-reasoner` (hard-deprecated 2026-07-24); (2) future Gemini dispatches may use the manifest variant names as live ids (`gemini-3.5-flash`, `gemini-3.1-flash-lite`) — the D-exec-5 "verify before spend" discipline is now SATISFIED for these ids by this pilot's corroborated evidence; (3) cleanup-batch candidates (owner decides at p6-checkpoint): update the deepseek `delta.md`/manual + `routing-matrix-reference.md` alias/deprecation note, and flip `deepseek` + `gemini` manifest `evidence_status` probe-pending→validated (both live-validated end-to-end this pilot); (4) the Manus report's "Missing from Your Table" section is QUARANTINED (failed content review — 3 of 5 rows already recorded); only `gemini-3-flash` + `gemini-2.5-pro` are genuinely-new candidates, and any manifest variant additions stay capped by the variant field-count discipline.

### D-exec-16 (FINAL): p6-checkpoint APPROVED — plan COMPLETE PENDING USER ACTION (owner chose close-now; cleanup batch deferred to a dated task)

- **Decision (owner, 2026-06-09):** at the p6-checkpoint final gate the owner approved completion (option A — close now, cleanup later). All 6 checkpoint criteria PASS; exit scorecard filled in `run-log.md`; honest status **COMPLETE PENDING USER ACTION** (the crit-7 USER-EXECUTED `install.py` run remains with the owner).
- **Rationale:** everything is delivered + certified (6 phases, 6 pilots, all evidence sheets held; the p6-1 live pilot validated the cross-strategy seam end-to-end on real paid calls); the remaining items are captured durably — running the cleanup batch immediately was declined in favor of a dated task (the rbtv repo is concurrently receiving a parallel session's commits; a clean later session is safer).
- **Scope (where everything lives now):** follow-ons → `1-projects/rbtv-evolution/rbtv-evolution-tasks.md` (Must: owner install run; Should 📅 2026-07-15: cleanup batch D-exec-10/11/15; Could: D-exec-14 artifact fetch, D-exec-4 qwen-code). Compound PRDs → `.user/compounds/rbtv-orchestrating/` (4 new, tracked in `2-areas/compounds/compounds-tasks.md`). The plan, this decisions file, `run-log.md` (incl. the exit scorecard), `learnings.md`, `deliverables.md`, and the 6 evidence sheets are the run's durable record. rbtv deliverable commits end at `11dcb38` (verified ancestor of the parallel-session-advanced HEAD).

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `1-projects/rbtv-evolution/orchestration/api-workers/api-workers-design.md` | The full design — purpose, scope, single-runner architecture, worker semantics, routing integration, key mechanism, deltas, risks |
| `1-projects/rbtv-evolution/orchestration/api-workers/manus-orchestation-scripts/providers/` | `base.py` + `{deepseek,gemini,openai,manus}_client.py` — the clients to adapt; `manus_client.py` confirmed Manus's task/poll/agentic shape |
| `1-projects/rbtv-evolution/orchestration/api-workers/manus-orchestation-scripts/docs/routing_matrix.md` | Per-provider models, prices, modes → seeds multi-variant manifests + the reference doc |
| `3-resources/tools/rbtv/orchestration/models/manifest-schema.md` | `(model, variant)` routing; the CLI-shaped required fields needing the schema-fit decision |
| `3-resources/tools/rbtv/orchestration/models/kimi/manifest.yaml` + `claude-cli/manifest.yaml` | Reference packages; `claude-cli` already models opus/sonnet variants — Agent-tool Claude does not |
| `3-resources/tools/rbtv/orchestration/skills/orchestrating/cards/{routing,dispatch-wrapper,verification,state,intake}.md` + `core-protocol.md` | The surfaces this plan edits |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `./specs/api-text-worker-spec.md` | Behavior contract for the runner + chat clients | p1-2..p1-5, p2-* |
| `./specs/manus-worker-spec.md` | Behavior contract for the Manus agentic worker | p5-* |
| `./specs/deterministic-routing-spec.md` | The selector + Claude-tier modeling behavior + test plan | p3-* |
| `1-projects/rbtv-evolution/orchestration/api-workers/api-workers-design.md` | Ground-truth design context | all build tasks |
