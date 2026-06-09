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

## Source Citations

- Anthropic: https://platform.claude.com/docs/en/about-claude/models/overview
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing , https://api-docs.deepseek.com/guides/thinking_mode
- Kimi: https://platform.kimi.ai/docs/models , https://platform.kimi.ai/docs/api
- Gemini: https://ai.google.dev/gemini-api/docs/models , https://ai.google.dev/gemini-api/docs/pricing
- OpenAI: https://platform.openai.com/docs/models
- Cohere: https://docs.cohere.com/docs/models , https://docs.cohere.com/docs/rag
- Qwen: https://dashscope.aliyuncs.com/docs
- Manus: https://api.manus.im/docs
