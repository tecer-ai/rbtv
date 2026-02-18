# Shape - optimize-nanobot-token-usage

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Switch the Nanobot default model from `claude-opus-4-6` to `claude-sonnet-4-20250514` to resolve rate limit errors
- Enable Anthropic prompt caching via LiteLLM's `cache_control_injection_points` to reduce cost and latency
- Slim bootstrap files (`TOOLS.md`, `AGENTS.md`) to reduce per-call token consumption by ~1,000 tokens
- Reduce Nanobot's `memory_window` from 50 to 20 to limit conversation history token load
- Add LiteLLM retry logic for transient rate limit errors
- Update operational documentation (deploy-runbook, server-env-template, smoke-checklist)
- Document all Nanobot source patches in `_mobile/README.md` and `_mobile/HOW-IT-WORKS.md`
- Move the companion compound document into the plan folder

**What this plan does NOT include:**
- Forking Nanobot or making permanent upstream changes
- Per-agent model routing (Nanobot doesn't support it; Sonnet is sufficient for all workflows)
- Removing the "Reflect on results" message from Nanobot's agent loop (poor risk/benefit ratio)
- Building a custom API proxy for caching
- Token budget enforcement tooling (future work, documented in learnings.md)
- Changes to RBTV agent files (`agents/mentor.md`, `agents/domcobb.md`, `agents/ana.md`) beyond what's needed for TOOLS.md deduplication

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Default model | `anthropic/claude-sonnet-4-20250514` | Much higher rate limits, 5x cheaper, capable enough for all RBTV structured workflows (menu routing, state management, framework execution) |
| Prompt caching mechanism | LiteLLM `cache_control_injection_points` on system messages | Native LiteLLM support, no custom proxy needed. Caches ~5,000-7,000 token system prompt for 90% cost reduction |
| TOOLS.md strategy | Remove per-agent workflow tables, keep command routing + skills + tool reference | Tables are redundant — each agent file already contains its own workflow details, loaded on demand during activation |
| AGENTS.md strategy | Remove verbose agent summaries, keep dispatch table with one-line descriptions | Full agent summaries repeat every call but are informational only; the model loads the full agent file via `read_file` on command |
| Memory window | Reduce from 50 to 20 via `config.json` | Project-memo contract ensures workflow state survives. Deep conversation history is unnecessary and costs 5,000-15,000+ tokens |
| Retry logic | Add `litellm.num_retries = 3` as module-level setting in Nanobot's `litellm_provider.py` | Prevents user-facing errors on transient rate limits. Follows existing pattern of module-level litellm settings |
| Nanobot source patches | Accepted, documented in `_mobile/README.md` and `_mobile/HOW-IT-WORKS.md` | Patches are fragile across Nanobot upgrades but acceptable with documentation for re-application |
| "Reflect" message | Excluded from scope | Core Nanobot design pattern affecting all tool-calling. ~15 tokens/iteration is not worth the risk of breaking tool execution behavior |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Nanobot is third-party (`HKUDS/nanobot`) | External dependency | Config changes preferred; source patches accepted but documented for upgrade resilience |
| Bootstrap files loaded by `ContextBuilder` as single system prompt | Nanobot architecture | Cannot selectively load/unload bootstrap files per-agent; must optimize content within existing loading mechanism |
| Anthropic Tier 1 rate limit: 30,000 input tokens/min (Opus) | API constraint | Immediate driver for model switch; Sonnet has much higher limits |
| `{project-root}` placeholders must be preserved | RBTV architecture | When editing bootstrap files, never replace placeholders with hardcoded paths |
| Agent behavioral fidelity must not degrade | Quality requirement | Slimming must preserve all routing logic and behavioral rules; only remove genuinely redundant content |
| LiteLLM is the provider layer | Nanobot dependency | All API-level optimizations (caching, retries) must work through LiteLLM's interfaces |
| `memory_window` is configurable in `config.json` | Confirmed from Nanobot `config/schema.py` — `agents.defaults.memory_window` field | No source patch needed for this change |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Rate limit error | "Error calling LLM: litellm.RateLimitError: AnthropicException - rate_limit_error, 30,000 input tokens per minute, claude-opus-4-6" | Root cause analysis: ~7,250 token system prompt × 4+ API calls/min = 32k+ tokens exceeding 30k limit |
| 2 | Optimization direction | "I believe there is a lot of room for optimizing how the nanobot utilizes the API... reducing the input tokens... reducing the prompts it always uses, the system prompt... and surely by prompt caching" | Three-part solution: model switch (Sonnet), prompt caching (LiteLLM cache_control), bootstrap slimming (TOOLS.md + AGENTS.md) |
| 3 | Model upgrade intent | "I could simply buy more credits on Claude platform, which I will do, and also change the model to a higher limit one (haiku and sonnet), which I will also do" | Default model switch to Sonnet as Phase 1 immediate unblock |
| 4 | Nanobot patching acceptance | "yes, we can accept nanobot source patches, but keep them documented in _mobile/README.md and _mobile/HOW-IT-WORKS.md so we can updated upon new nanobot releases" | Source patches in scope with documentation requirement. Affects: litellm_provider.py (caching + retries) |
| 5 | Compound document integration | "also consider the changes of cp-nanobot-token-optimization-prompt-caching.md in this plan u are creating and move the cp to the plan folder after creation" | Compound doc is foundational analysis; contents absorbed into plan context. File to be moved to plan folder as a plan task |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Scope of Nanobot modifications | User open to patches with documentation | AI analyzed Nanobot source (`context.py`, `loop.py`, `litellm_provider.py`, `config/schema.py`) to identify which changes need source patches vs. config-only. Discovered `memory_window` is config-surface. | Config changes: model, memory_window. Source patches: prompt caching, retry logic. All documented in _mobile/ docs |
| 2 | "Reflect" message removal | Not explicitly discussed by user | AI identified the "Reflect on results and decide next steps" message in `loop.py` as a potential optimization but assessed risk/benefit as poor (~15 tokens/iteration, core Nanobot pattern). | Excluded from scope — too risky for too little gain |
| 3 | SOUL.md optimization | Not explicitly discussed | AI reviewed SOUL.md and found most content essential. Slack formatting table (~100 tokens) could be compacted but savings are marginal. | Defer SOUL.md changes — review during execution for opportunistic compaction only |
| 4 | Plan name | AI suggested `optimize-nanobot-token-usage` | User confirmed | `optimize-nanobot-token-usage` |

---

## Standards Applied

### RBTV Mobile Harness Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Non-duplication rule (`_mobile/README.md`) | Nanobot source patches must not duplicate Nanobot transport or runtime responsibilities. Patches are targeted injections, not reimplementations. |
| Responsibility split (`_mobile/README.md`) | Changes respect the boundary: Nanobot owns transport/AI provider/lifecycle; `_mobile/` owns routing/policy/state/bootstrap. |
| `{project-root}` placeholder preservation | All bootstrap file edits must preserve placeholders as-is |

### Micro Commits (from CLAUDE.md)

| Rule | Application |
|------|-------------|
| Plan first | Commit groups planned before code changes |
| Commit immediately | After each coherent group of changes |
| Push after each commit | Never batch pushes |
| Conventional Commits | `type(scope): P{phase}-{task-id} description` |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Nanobot patches documented | Every source patch must be reflected in `_mobile/README.md` (boundary/scope section) and `_mobile/HOW-IT-WORKS.md` (new "Nanobot Source Patches" section) |
| Token budget validation | After bootstrap slimming, estimate new token counts and document in smoke-checklist |
| No behavioral regression | After TOOLS.md/AGENTS.md slimming, verify all agent activation paths still work (documented in acceptance criteria) |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

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

**Decision Entry Format:** `### Decision [N] (from task [id])` — Date, Decision, Rationale, Impact.

**Discovery Entry Format:** `### Discovery [N] (from task [id])` — Date, Finding, Contradicts (ref to original shaping), Resolution (simple fix or new task added), Propagation Checklist (table: Status, Task/File, Action Taken), Details. When a discovery changes a prior decision: annotate affected completed tasks with "SUPERSEDED — See Discovery N", update affected pending tasks, fill propagation checklist.

<!-- Decisions and discovery entries will be appended below this line -->

### 2026-02-18 - p4-5 Added — Multi-Turn Validation Migrated from robotville Plan

- **Decision:** Add p4-5 "VALIDATE multi-turn mentor conversation completes without rate limit errors" to Phase 4 of this plan. This task was originally p8-5 in `robotville-vps-nanobot-rbtv-integration.plan.md` (Phase 8), which has been cancelled in full because all token optimization work now lives here. The validation belongs in this plan since it proves the optimization's effect.
- **Position:** After p4-4 (smoke-checklist update), before p4-refs (link review). Requires human approval — live Slack validation cannot be automated.
- **Micro-step file:** `phase-4/p4-5.task.md` created.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_admin/roadmap/todos/cp-nanobot-token-optimization-prompt-caching.md` | Compound analysis: root cause (token budget mismatch), three-part solution (Sonnet + caching + slimming), acceptance criteria, related files inventory |
| `_mobile/README.md` | Non-duplication rules, responsibility split between Nanobot and `_mobile/` harness |
| `_mobile/HOW-IT-WORKS.md` | Bootstrap system (4 files loaded every call), VPS deployment model, agent system, project-memo contract |
| `_mobile/AGENTS.md` (~68 lines, ~875 tokens) | Agent dispatch table + verbose summaries. Summaries are redundant with agent files loaded on demand. |
| `_mobile/SOUL.md` (~117 lines, ~1,125 tokens) | Core behavioral contract. Most content essential. Slack formatting (~20 lines) could be compacted marginally. |
| `_mobile/TOOLS.md` (~132 lines, ~1,375 tokens) | Largest bootstrap file. Per-agent workflow tables (lines 26-73, ~800 tokens) are redundant with agent files. Command routing table (3 rows) + skills + tool reference are essential. |
| `_mobile/USER.md` (~40 lines, ~450 tokens) | Already compact. No changes needed. |
| Nanobot `context.py` (GitHub) | `ContextBuilder` loads `AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md` from workspace root. Builds single system prompt concatenating all files + memory + skills summary. No caching. |
| Nanobot `loop.py` (GitHub) | `AgentLoop` with `memory_window=50` default. After each tool call adds "Reflect on the results and decide next steps" user message. Consolidation at `memory_window` threshold. |
| Nanobot `litellm_provider.py` (GitHub) | Calls `acompletion()` without `cache_control_injection_points` or `num_retries`. Sets `litellm.suppress_debug_info = True` and `litellm.drop_params = True` as module-level settings. Error returns as string content (no retry). |
| Nanobot `config/schema.py` (GitHub) | `AgentDefaults`: `memory_window: int = 50`, `model: str = "anthropic/claude-opus-4-5"`, `max_tool_iterations: int = 20`. All configurable via `config.json`. |
| Nanobot `providers/registry.py` (GitHub) | Anthropic provider uses no litellm_prefix (LiteLLM recognizes "claude-*" natively). No caching configuration. |
| LiteLLM prompt caching docs | `cache_control_injection_points=[{"location": "message", "role": "system"}]` auto-injects `cache_control: {"type": "ephemeral"}` on system messages. Up to 4 cache control blocks per request. |
| `_mobile/ops/patches/update-nanobot-model.py` | Existing patch pattern: reads config.json, modifies specific field, writes back. Template for new patches. |
| `_mobile/_docs/server-env-template.md` | Current config template uses `anthropic/claude-opus-4-5` as default model. No caching settings. |

### Token Budget Analysis (from conversation)

| Component | Est. Tokens | Frequency | Notes |
|-----------|-------------|-----------|-------|
| Nanobot identity section | ~300 | Every call | Upstream, not modifiable |
| `AGENTS.md` | ~875 | Every call | Can trim ~200 by removing summaries |
| `SOUL.md` | ~1,125 | Every call | Mostly essential; ~100 marginal savings |
| `TOOLS.md` | ~1,375 | Every call | Can trim ~800 by removing per-agent tables |
| `USER.md` | ~450 | Every call | Already compact |
| `MEMORY.md` contents | ~200-1,000 | Every call | Variable |
| Skills summary | ~200-500 | Every call | Managed by Nanobot |
| Tool definitions (8 tools JSON) | ~1,500-2,000 | Every call | Upstream, not modifiable |
| **System prompt subtotal** | **~5,000-7,250** | **Every call** | **After optimization: ~4,000-5,250** |
| Conversation history (50 msgs) | ~5,000-25,000 | Growing | After optimization (20 msgs): ~2,000-10,000 |
| Current message | ~50-500 | Once | — |

**Before optimization:** ~12,000-32,000+ tokens/call, 4+ calls/min = rate limit exceeded
**After optimization (all changes):** ~6,000-15,000 tokens/call, well within Sonnet limits

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `_mobile/TOOLS.md` | Primary slimming target | Bootstrap optimization phase |
| `_mobile/AGENTS.md` | Secondary slimming target | Bootstrap optimization phase |
| `_mobile/SOUL.md` | Review for opportunistic compaction | Bootstrap optimization phase |
| `_mobile/README.md` | Add Nanobot patches section | Patch documentation phase |
| `_mobile/HOW-IT-WORKS.md` | Add Nanobot patches section | Patch documentation phase |
| `_mobile/_docs/server-env-template.md` | Update model + caching config | Documentation update phase |
| `_mobile/_docs/deploy-runbook.md` | Update with optimization steps | Documentation update phase |
| `_mobile/_docs/smoke-checklist.md` | Add token budget validation | Documentation update phase |
| `_mobile/ops/patches/update-nanobot-model.py` | Reference for patch script pattern | Patch creation phase |
| Nanobot `litellm_provider.py` (GitHub: `https://raw.githubusercontent.com/HKUDS/nanobot/main/nanobot/providers/litellm_provider.py`) | Source for caching + retry patches | Patch creation phase |
| Nanobot `config/schema.py` (GitHub: `https://raw.githubusercontent.com/HKUDS/nanobot/main/nanobot/config/schema.py`) | Config surface reference | Config change phase |
| `.cursor/plans/optimize-nanobot-token-usage/cp-nanobot-token-optimization-prompt-caching.md` | Foundational compound analysis | All phases (reference) |

### Change Categories

| Category | Changes | Mechanism |
|----------|---------|-----------|
| **Config-surface (safe)** | Model switch to Sonnet, memory_window reduction to 20 | `config.json` on VPS |
| **RBTV-owned files (safe)** | TOOLS.md slimming, AGENTS.md slimming, SOUL.md review, documentation updates | Direct file edits in repo, deployed via `vps-sync-install.sh` |
| **Nanobot source patches (fragile)** | Prompt caching (`litellm_provider.py`), retry logic (`litellm_provider.py`) | Python patch scripts in `ops/patches/`, documented in `_mobile/` docs |
| **Housekeeping** | Move compound doc to plan folder, update smoke-checklist | File operations |

### Acceptance Criteria (from compound document + conversation)

- [ ] Default model changed to `anthropic/claude-sonnet-4-20250514` in Nanobot `config.json`
- [ ] `memory_window` reduced to 20 in Nanobot `config.json`
- [ ] Multi-turn "mentor" → "N" → framework step conversation completes without rate limit errors
- [ ] Prompt caching patch created and documented: adds `cache_control_injection_points` to `litellm_provider.py`
- [ ] Retry logic patch created and documented: adds `litellm.num_retries = 3` to `litellm_provider.py`
- [ ] `TOOLS.md` reduced to command routing table + skills + tool reference only (~500-600 tokens)
- [ ] `AGENTS.md` reduced to dispatch table with one-line descriptions only (~400-500 tokens)
- [ ] All Nanobot source patches documented in `_mobile/README.md` and `_mobile/HOW-IT-WORKS.md`
- [ ] Server env template updated with recommended model and caching settings
- [ ] Deploy runbook updated with optimization deployment steps
- [ ] Smoke checklist updated with token budget validation item
- [ ] Compound document moved to plan folder
