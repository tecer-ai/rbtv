> **Reference data — NOT a router.** This is a within-tier TIEBREAKER the conductor may consult; it is NEVER the master routing cut (boundedness-first stays the cut, per `cards/routing.md`). Model ids and prices are 2026 estimates harvested from a prior research doc — **re-verify against provider docs before relying on any specific id/price.**

# AI Provider Routing Matrix — Reference

## 1. Anthropic Claude

| Model | Context | Max Output | Price (input/output) | Thinking | Knowledge Cutoff |
|-------|---------|------------|----------------------|----------|------------------|
| Claude Opus 4.8 | 1M tokens | 128k | $5/$25 per MTok | Adaptive | Jan 2026 |
| Claude Sonnet 4.6 | 1M tokens | 64k | $3/$15 per MTok | Extended | Aug 2025 |
| Claude Haiku 4.5 | 200k tokens | 64k | $1/$5 per MTok | Extended | Feb 2025 |

**Capability:** Opus 4.8 = deepest reasoning + long agentic; Sonnet 4.6 = balanced; Haiku 4.5 = fast/cheap volume.

## 2. DeepSeek

| Model | Context | Max Output | Price (input/output) | Thinking Mode | Features |
|-------|---------|------------|----------------------|---------------|----------|
| deepseek-v4-pro | 1M tokens | 384k | $0.435/$0.87 per MTok | Yes | Tool calls, JSON |
| deepseek-v4-flash | 1M tokens | 384k | $0.14/$0.28 per MTok | Yes (default) | Tool calls, JSON |

**Capability:** V4-Pro = max reasoning quality; V4-Flash = best cost/benefit. Both: Thinking Mode + Tool Calling + JSON output.

## 3. Kimi (Moonshot AI)

| Model | Context | Multimodal | Thinking | Agent Mode | API |
|-------|---------|------------|----------|------------|-----|
| kimi-k2.6 | 256k tokens | Text + Image | Yes | Yes | OpenAI-compatible |
| kimi-k2.5 | 256k tokens | Text + Image | Yes | Yes | OpenAI-compatible |

**Capability:** 256k context; multimodal (text+image); Thinking + Agent Mode; OpenAI-compatible API. (Note: kimi runs as a CLI code-executor in this workspace.)

## 4. Gemini (Google)

| Model | Price (input/output) | Thinking | Search Grounding | Batch API |
|-------|----------------------|----------|------------------|-----------|
| Gemini 3.5 Flash | $1.50/$9.00 per MTok | Yes | Yes | 50% discount |
| Gemini 3.1 Pro | $2.00/$12.00 per MTok | Yes | Yes | 50% discount |
| Gemini 3.1 Flash-Lite | $0.25/$1.50 per MTok | Yes | Yes | 50% discount |

**Capability:** Thinking tokens (in output price); Search Grounding (real-time web); Batch API 50% off. 3.5 Flash = smartest; 3.1 Flash-Lite = cheapest.

## 5. OpenAI

| Model | Context | Specialty | Coding | Agentic |
|-------|---------|-----------|--------|---------|
| GPT-5.5 | ~200k | General | Advanced | Yes |
| GPT-5.4 mini | ~200k | Light | Good | Yes |
| GPT-5.4 nano | ~200k | Ultra-light | Basic | Yes |

**Capability:** GPT-5.5 = top reasoning + coding; mini/nano = lighter/cheaper.

> **Note:** Routed via the `codex` CLI (code execution) in this workspace — NOT built as an API chat worker (dropped per build decision D1). Listed here as reference only.

## 6. Cohere

| Model | Vision | Native RAG | Tool Calling | Reranking |
|-------|--------|------------|--------------|-----------|
| Command A+ | Yes | Yes | Yes | Integrated |
| Command R | No | Yes | Yes | Integrated |

**Capability:** Command A+ = vision + native RAG + reranking; Command R = lighter RAG.

## 7. Manus

| Aspect | Description |
|--------|-------------|
| Autonomy | Browser navigation, clicks, interactions |
| API | RESTful |
| Timeout | Up to 5 minutes |
| Cost | Per task |
| Integration | Multiple tools and APIs |

**Capability:** real autonomy — browser navigation, clicks, form-fill, full workflows; RESTful task API; per-task cost; ~5-min timeout. Complement to LLMs, not a substitute.

## 8. Qwen (Alibaba)

| Model | Multimodal | Agent | Context | API |
|-------|------------|-------|---------|-----|
| Qwen3.7 | Text, image, video | Yes | Not specified | OpenAI-compatible |
| Qwen3.5-Plus | Text, image, video | Yes | Not specified | OpenAI-compatible |

**Capability:** multimodal (text/image/video); Agent Mode; OpenAI-compatible.

## Quick-Decision Matrix

| Need | Provider | Model | Reason |
|------|----------|-------|--------|
| Maximum reasoning | Anthropic | Opus 4.8 | Adaptive Thinking |
| Cost/benefit | Anthropic | Sonnet 4.6 | Ideal balance |
| High volume | Anthropic | Haiku 4.5 | Most economical |
| Logical reasoning | DeepSeek | V4-Pro | Thinking Mode |
| Optimized cost | DeepSeek | V4-Flash | Very cheap |
| Giant context | Kimi | K2.6 | 256k tokens |
| Vision + context | Kimi | K2.6 | Native multimodal |
| Volume processing | Gemini | 3.1 Flash-Lite | Very cheap |
| Integrated search | Gemini | 3.5 Flash | Search Grounding |
| Corporate RAG | Cohere | Command A+ | Native RAG |
| Autonomy | Manus | API | Browser automation |
| Advanced multimodal | Qwen | 3.7 | Video + image |

## Overlap Disambiguation — within-tier "use X when / use Y when"

These rows resolve the specific worker overlaps the owner cares about. They are **within-tier tiebreakers only** — boundedness-first (per `cards/routing.md` §2) stays the master cut; consult a row below ONLY to break a tie between workers the boundedness tree already placed in the same tier. Each variant's positive "best at" line lives in its manifest `specialty` field; these rows state the BOUNDARY between two overlapping choices.

### DeepSeek-API vs codex-CLI

| Use… | When |
|------|------|
| **DeepSeek API** (`deepseek:v4-flash` / `v4-pro`) | The leaf is **text synthesis / logic over inlined sources** — no code execution. DeepSeek carries `code_competence: none`, so the §2a `code_competence ≥ needed` filter already removes it from every code leaf; it wins on a TEXT leaf as the cheapest capable. Cheapest text worker (v4-flash); cheapest top-reasoning-tier text (v4-pro). |
| **codex CLI** (`codex:default` / `high-reasoning`) | The leaf **executes code** — edits a work-dir, runs commands, needs a sandboxed separate process. codex is a code-specialized agent (`code_competence: strong`); DeepSeek cannot do this leaf at all. |

Boundary: the cut is **text-synthesis vs code-execution**, enforced mechanically by `code_competence` — never route code to DeepSeek, never route pure text-synthesis to a costlier code-executing process when a text worker suffices. (api-workers-build D2: DeepSeek stays the API text worker; the code/agentic role is a CLI worker.)

### Gemini-grounding vs rbtv-web-searching vs manus

| Use… | When |
|------|------|
| **Gemini** (`gemini:3.5-flash` / `3.1-flash-lite`) | A **single grounded lookup** — one search-grounded call, light not rigorous. The ONLY `web_access: true` API chat worker. (Grounding pending run.py wiring — p5-3/p5-4; until then Gemini runs default JSON-envelope mode only.) |
| **`rbtv-web-searching`** (Agent-tool path) | **Rigorous multi-source research** — source evaluation, citations, cross-checking across many sources. The in-session web path, always available even when no web-capable model package is installed (routing §6 degrade). NEVER an API chat worker for this tier. |
| **Manus** (`manus:manus-autonomous`) | **Autonomous multi-step browser work** — the agent must navigate, click, fill, and synthesize across pages on its OWN (multi-step data collection), not a single lookup. Per-task cost, minutes-scale latency, raw-dump return. |

Boundary: **single grounded call (Gemini) → rigorous cited multi-source (rbtv-web-searching) → autonomous multi-step browser agent (Manus)** — three distinct web tiers differing in autonomy, rigor, and cost (routing §6). Match the tier the task needs; do not pay Manus's per-task autonomy for a single lookup, and do not ask Gemini's single grounded call to do rigorous multi-source research.

### claude-cli (process) vs Agent-tool Claude

| Use… | When |
|------|------|
| **Agent-tool Claude** (`claude:opus` / `claude:sonnet`) | The **default** Claude carrier — an in-session sub-agent via the Agent tool. No process overhead, no auth pre-flight, no guidance-file dependency. Use for normal in-session dispatches. It does NOT natively load workspace `CLAUDE.md`/rules (the parent inlines them) and CANNOT spawn sub-agents (the nesting wall). |
| **claude-cli** (`claude-cli:opus` / `claude-cli:sonnet`) | A **process-boundary sub-conductor** is needed (the worker must itself drive CLI workers — the nesting wall forces a separate process), OR **native workspace-rule loading** is required (a `claude -p` process natively auto-loads the cwd `CLAUDE.md`/rules; the Agent-tool carrier does not). |

Boundary: **default to Agent-tool Claude; escalate to claude-cli ONLY for a process boundary (sub-conducting) or native workspace-rule loading.** Both are enumerated as distinct `(model, variant)` pairs by §2a — NEVER collapse the two Claude carriers into one entity (routing §4 "Two distinct Claude carriers"). Same Claude budget either way — neither is cost arbitrage.

## Source Citations

- Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode
- Kimi: https://platform.kimi.ai/docs/models , https://platform.kimi.ai/docs/api
- Gemini: https://ai.google.dev/gemini-api/docs/models , https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://platform.openai.com/docs/models
- Cohere: https://docs.cohere.com/docs/models , https://docs.cohere.com/docs/rag
- Qwen: https://dashscope.aliyuncs.com/docs
- Manus: https://api.manus.im/docs
