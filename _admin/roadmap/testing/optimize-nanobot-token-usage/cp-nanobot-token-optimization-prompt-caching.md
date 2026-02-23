---
title: 'Compound: Nanobot Token Optimization — Prompt Caching and Model Routing'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments: []
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-14'
yoloMode: false
---

# Nanobot Token Optimization — Prompt Caching and Model Routing

**Type:** System File
**Priority:** High
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The Nanobot RBTV integration hits Anthropic's `claude-opus-4-6` rate limit (30,000 input tokens/minute) during simple two-message interactions ("mentor" → "N"). The bootstrap system sends ~7,250 tokens of system prompt on every API call, and Nanobot's tool-calling pattern requires 2+ API calls per user interaction, causing 4 API calls within a minute that aggregate to ~32k+ input tokens — exceeding the Tier 1 limit.

### Goals

1. Nanobot should handle normal multi-turn conversations without hitting rate limits.
2. Bootstrap content should be optimized for token efficiency without losing agent behavior fidelity.
3. The system should leverage Anthropic API features (prompt caching) to minimize fresh token consumption.
4. Model selection should match task complexity — routine routing doesn't need Opus.

### Constraints

- Nanobot runtime is third-party (`HKUDS/nanobot`) — changes must work within its configuration surface, not by forking.
- Bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) are loaded into the system prompt by Nanobot's `ContextBuilder` — this is not configurable per-file.
- LiteLLM is the provider layer — prompt caching support depends on LiteLLM's Anthropic integration.
- The Anthropic API tier is currently Tier 1 (30k input tokens/min for Opus).

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap

The bootstrap files (p5-1 through p5-5) were designed for behavioral correctness — ensuring RBTV agent personas, workflows, and state management work correctly through Nanobot. Token efficiency was never considered as a design constraint. No one estimated the per-request token cost or validated that the aggregate token load would stay within the API rate limit for the selected model.

**Expectation:** Simple interactions like "mentor" → "N" should work without errors.

**Actual:** The second message ("N") triggers a `litellm.RateLimitError` because the cumulative input tokens within a 1-minute window (~32k) exceed the 30k/min Tier 1 limit for `claude-opus-4-6`.

**Impact:** The Nanobot gateway is functionally unusable for multi-turn conversations on Opus Tier 1. Any interaction requiring 2+ exchanges within a minute will fail.

**Root cause breakdown:**
- System prompt (~7,250 tokens) is resent on every API call — no caching
- Tool-calling doubles API calls per interaction (one for tool decision, one for response)
- `TOOLS.md` contains ~112 lines of detailed workflow tables that repeat on every call but are rarely needed in the system prompt
- Model is `claude-opus-4-6` which has the most restrictive Tier 1 rate limits
- No token budget was established during bootstrap file design

### Context Source Evaluation

| File | Role | Issue |
|------|------|-------|
| `_mobile/AGENTS.md` (~875 tokens) | System prompt — agent routing | Contains full agent summaries that repeat every call. Summaries are informational but not required for routing — the model loads the full agent file on demand anyway. |
| `_mobile/SOUL.md` (~1,125 tokens) | System prompt — behavioral rules | Essential content, but some sections (Context Window Resilience, Security) are situational rather than per-call necessary. |
| `_mobile/TOOLS.md` (~1,375 tokens) | System prompt — command mapping | Largest bootstrap file. Contains detailed workflow tables for all 3 agents (lines 26–73) that are useful reference but not needed until a specific agent is activated. Only the top-level command routing table (3 rows) is needed per-call. |
| `_mobile/USER.md` (~450 tokens) | System prompt — user preferences | Compact. Reasonable per-call inclusion. |
| `_mobile/skills/*/SKILL.md` (3 files) | Auto-summarized into system prompt | Each skill adds ~100-200 tokens to the summary. Manageable. |
| Nanobot `config.json` | Model selection, workspace path | Sets `claude-opus-4-6` as default model. No prompt caching configuration. No model routing per agent. |
| `_mobile/ops/scripts/vps-sync-install.sh` | Deployment | Deploys bootstrap files but has no optimization or validation step for token budget. |
| Plan tasks p5-1 through p5-5 | Bootstrap file creation | Task descriptions focused on behavioral correctness. No acceptance criteria related to token efficiency or rate limit viability. |
| PRD (`_bmad-output/robotville-v4.0/bmad/prd.md`) | Requirements | Specifies "Nanobot bootstrap files" as must-have but does not specify token budget constraints. |

**Gaps identified:**
1. No token budget guideline for bootstrap files exists in any RBTV rule or constraint.
2. No guidance on configuring prompt caching in the deploy runbook or server env template.
3. No model routing capability — all interactions use the same model regardless of complexity.
4. No measurement of per-request token usage before deployment (no smoke test for token load).
5. `TOOLS.md` workflow detail tables are always-loaded content that should be on-demand.

### Improvement Options

1. **New Rule**: Token budget constraint for Nanobot bootstrap files
   - **Rationale:** Establish a measurable ceiling (e.g., 4,000 tokens total for all bootstrap files) that forces compact design. Future bootstrap edits would be validated against this budget. Prevents the same problem from recurring as more agents or skills are added.
   - **Location:** New rule file `_mobile/rules/token-budget.md` or section in existing `_mobile/README.md`

2. **Modify Existing Rule**: Update deploy runbook and server env template with prompt caching configuration
   - **Rationale:** Anthropic's prompt caching makes cached input tokens count against a separate, higher rate limit bucket. If the ~7k system prompt is cached, only new conversation content counts as fresh tokens — reducing fresh token usage from ~32k/min to ~10k/min. LiteLLM supports this via `cache_control` on system messages.
   - **Location:** `_mobile/_docs/deploy-runbook.md` (add caching config section), `_mobile/_docs/server-env-template.md` (add LiteLLM/Anthropic cache settings)

3. **Update System File**: Slim `TOOLS.md` by moving per-agent workflow tables to on-demand loading
   - **Rationale:** `TOOLS.md` is the largest bootstrap file (~1,375 tokens). Lines 26–73 contain detailed workflow tables for mentor, domcobb, and doc agents. These are only useful after an agent is activated — and at that point the full agent file is loaded anyway. Moving them out saves ~800 tokens per call (~11% of total system prompt).
   - **Location:** `_mobile/TOOLS.md` — keep only the 3-row command routing table and skill references; move workflow details into agent files or a separate reference file loaded on demand.

4. **Add Constraint**: Smoke test for token budget validation before deployment
   - **Rationale:** The rate limit failure was only discovered in production after deployment (p5-8 validation). A pre-deployment check that estimates total system prompt size and validates it against the target model's rate limit would catch this class of issue before it reaches users.
   - **Location:** Add to `_mobile/_docs/smoke-checklist.md` as a new checklist item; optionally script it in `vps-sync-install.sh` as a character count / token estimate warning.

5. **Alternative Approach**: Implement model routing — Sonnet for routine interactions, Opus reserved for complex reasoning
   - **Rationale:** `claude-sonnet-4-20250514` has significantly higher Tier 1 rate limits and costs ~5x less than Opus. Menu routing ("mentor", "N", "C"), state management, and framework step execution are well within Sonnet's capability. Opus could be reserved for tasks that genuinely need deep reasoning (e.g., competitive analysis, market sizing). This approach eliminates the rate limit issue entirely for normal usage while keeping Opus available when needed.
   - **Location:** Nanobot `config.json` on VPS — change `agents.defaults.model` to Sonnet; add per-agent or per-skill model overrides if Nanobot supports them. Document in `_mobile/_docs/server-env-template.md`.

---

## Proposed Solution

Comprehensive three-part fix addressing token volume, caching, and model selection.

### Part A: Switch Default Model to Sonnet (immediate unblock)

Change the default model in Nanobot's `config.json` from `anthropic/claude-opus-4-6` to `anthropic/claude-sonnet-4-20250514`. This immediately resolves the rate limit issue because:

- Sonnet's Tier 1 rate limits are significantly higher than Opus
- Menu routing, state management, and framework step execution are well within Sonnet's capability
- Cost drops ~5x per token

If Nanobot's `config.json` supports per-agent or per-skill model overrides, configure Opus as an optional override for tasks that genuinely require deep reasoning (e.g., competitive analysis synthesis, complex market sizing). Research required to confirm override support.

**Config change (on VPS):**

```json
{
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-20250514"
    }
  }
}
```

### Part B: Enable Anthropic Prompt Caching (systemic fix)

Research and configure prompt caching via LiteLLM's Anthropic integration. When enabled:

- The ~7,250-token system prompt is cached after the first call in a session
- Subsequent calls use cached tokens (separate, higher rate limit bucket + 90% cost reduction)
- Fresh token usage per call drops from ~7,250 to ~500-2,000 (conversation-only)

**Research tasks:**
1. Check if Nanobot exposes LiteLLM provider configuration for `cache_control` headers
2. Check if LiteLLM auto-applies caching for Anthropic system messages when configured
3. If manual configuration required, identify the exact config surface (environment variable, config.json field, or LiteLLM config file)

**Expected config (if supported):**

LiteLLM supports Anthropic prompt caching via `cache_control` on system messages. Nanobot would need to either:
- Pass `extra_headers` or `cache_control` in its LiteLLM completion calls
- Or configure LiteLLM to auto-cache system messages for Anthropic providers

### Part C: Slim TOOLS.md (bootstrap optimization)

Reduce `_mobile/TOOLS.md` from ~1,375 tokens to ~500 tokens by moving per-agent workflow detail tables to on-demand loading.

**Keep in TOOLS.md (always-loaded system prompt):**
- Top-level command routing table (3 rows: mentor, domcobb, doc)
- Routing rules (case-insensitive, leading `/` strip)
- Skills reference table
- Nanobot tool reference table

**Move to on-demand (loaded via `read_file` after agent activation):**
- Mentor Agent Workflows table (lines 26–36)
- DomCobb Agent Workflows table (lines 40–51)
- Doc Agent Workflows table (lines 55–73)

These tables duplicate information already present in each agent's `.md` file, which is loaded during agent activation anyway. Removing them from the system prompt saves ~800 tokens per API call without losing any functionality.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | VPS: `/srv/nanobot/.nanobot/config.json` (model + caching), Repo: `_mobile/TOOLS.md` (slimming), Docs: `_mobile/_docs/deploy-runbook.md`, `_mobile/_docs/server-env-template.md` |
| Scope of change | Comprehensive — config change on VPS, bootstrap file edit in repo, documentation updates |
| Related files | `_mobile/AGENTS.md` (may also benefit from slimming agent summaries), `_mobile/ops/scripts/vps-sync-install.sh` (re-deploy after TOOLS.md change), `_mobile/_docs/smoke-checklist.md` (add token budget validation item) |

---

## Rationale

The root cause is a mismatch between system design assumptions and API operational constraints. The bootstrap files were built for behavioral fidelity without token accounting, while the selected model (Opus) has the most restrictive rate limits in the Anthropic lineup.

Part A (Sonnet) is the immediate unblock — it fixes the problem right now with a single config change. Part B (prompt caching) is the systemic fix — it makes the architecture sustainable regardless of model choice by ensuring the static system prompt is cached. Part C (TOOLS.md slimming) is good hygiene — it removes redundant always-loaded content that belongs in on-demand files, reducing baseline token cost for every future interaction.

Together, these three changes transform token usage from ~32k fresh tokens/minute (broken) to an estimated ~6-8k fresh tokens/minute (well within limits for any model tier).

---

## Acceptance Criteria

- [ ] Default model changed to Sonnet in Nanobot `config.json` on VPS
- [ ] Multi-turn "mentor" → "N" → framework step conversation completes without rate limit errors
- [ ] Prompt caching research completed: documented whether Nanobot/LiteLLM supports cache_control configuration
- [ ] If caching is supported: configured and validated (check API response headers for `cache_read_input_tokens`)
- [ ] `TOOLS.md` reduced to command routing table + skills + tool reference only (~500 tokens); per-agent workflow tables removed
- [ ] `TOOLS.md` change deployed to VPS via `vps-sync-install.sh` and validated
- [ ] Deploy runbook updated with model selection and caching configuration guidance
- [ ] Server env template updated with recommended model and caching settings
- [ ] Smoke checklist updated with token budget validation item

---

## Related Files

| File | Relationship |
|------|--------------|
| `_mobile/TOOLS.md` | Primary file to slim — remove per-agent workflow tables |
| `_mobile/AGENTS.md` | Secondary candidate for slimming — agent summaries repeat info from agent files |
| `_mobile/SOUL.md` | Review for situational sections that could be on-demand |
| `_mobile/USER.md` | Already compact, no changes needed |
| VPS: `/srv/nanobot/.nanobot/config.json` | Model selection and potential caching configuration |
| `_mobile/_docs/deploy-runbook.md` | Update with model + caching config guidance |
| `_mobile/_docs/server-env-template.md` | Update with recommended settings |
| `_mobile/_docs/smoke-checklist.md` | Add token budget validation item |
| `_mobile/ops/scripts/vps-sync-install.sh` | Re-deploy after TOOLS.md change |
| `agents/mentor.md` | Already contains workflow details — confirms TOOLS.md tables are redundant |

---

## References

- [Anthropic Prompt Caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Anthropic Rate Limits](https://docs.anthropic.com/en/api/rate-limits)
- [LiteLLM Anthropic Provider — Prompt Caching](https://docs.litellm.ai/docs/providers/anthropic#prompt-caching)
- Plan: `.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md` (p5-8 validation task)
- Error observed: `litellm.RateLimitError` on `claude-opus-4-6`, org rate limit 30,000 input tokens/min

---

## Discussion Notes

### Selected Improvement Options

All three high-impact options selected — comprehensive solution:

1. **Option 2 — Prompt caching** (modify deploy config / Nanobot LiteLLM settings)
2. **Option 5 — Model routing** (Sonnet default, Opus reserved for complex reasoning)
3. **Option 3 — Slim TOOLS.md** (move per-agent workflow tables to on-demand loading)

### Implementation Preferences

- **File Locations:** Nanobot `config.json` on VPS (caching + model), `_mobile/TOOLS.md` in repo (slimming), deploy docs (`deploy-runbook.md`, `server-env-template.md`)
- **Scope:** Comprehensive — all three changes
- **Priority:** High — gateway is functionally broken on Opus Tier 1 for multi-turn conversations

### Additional Context

- Prompt caching and model routing require research into Nanobot/LiteLLM configuration surface — scope as prerequisite tasks in the PRD
- Per-agent model overrides (Nanobot `config.json`) — unknown if supported; scope research
- TOOLS.md slimming is straightforward and can be implemented immediately in the RBTV repo
- User agrees this is High priority given the gateway is unusable for normal interactions
