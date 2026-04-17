---
---

# Context and Token Management

**Problem Type:** Context Management

**Related Anti-Patterns:** Addresses [Kitchen Sink Prompts](prompting_anti_patterns.md#scope-and-complexity-anti-patterns), [Ignoring Context Window Limitations](prompting_anti_patterns.md#context-management-anti-patterns)

---

## Table of Contents

1. [Problem Solved](#problem-solved)
2. [Technique Overview](#technique-overview)
3. [When to Apply](#when-to-apply)
4. [Application Pattern](#application-pattern)
5. [Variations](#variations)
6. [Pitfalls](#pitfalls)
7. [Examples](#examples)
8. [Quality Checklist](#quality-checklist)
9. [Technical Reference](#technical-reference)
10. [Sources](#sources)
11. [Discarded Sources](#discarded-sources)

---

## Problem Solved

As LLM applications scale, context windows fill quickly while costs rise exponentially—requiring systematic token budgeting, caching, and compression.

---

## Technique Overview

Context and token management treats context as a finite resource requiring strategic allocation. Modern approaches combine multi-level caching (KV-cache, prompt caching, semantic caching), hierarchical summarization, RAG for external knowledge, and systematic token budgeting across prompt components.

**Core Mechanism:** By structuring prompts for cache reuse, aggressively filtering low-signal information, and compressing verbose context, applications achieve 50-90% cost reduction while maintaining or improving response quality. Context optimization addresses both performance (latency) and economics (cost per request).

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Multi-turn conversations that accumulate history over time | Single-turn, short prompts where optimization overhead exceeds gains |
| RAG systems retrieving multiple document chunks per query | Applications with minimal or static context requirements |
| High-volume production applications processing thousands of requests daily | Low-volume prototypes where engineering cost outweighs savings |
| Applications approaching context window limits (>50% utilization) | Queries consistently under 1K tokens with no growth trajectory |
| Systems processing untrusted or verbose external data | Fully controlled, pre-optimized content with known token efficiency |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Establish baseline and goals | Measure current token usage (input/output), latency, and quality metrics. Set specific targets: e.g., "reduce cost 20% without dropping quality below 88%". Document baseline before optimization. |
| 2 | Apply manual optimization | Remove unnecessary words, use direct language, replace verbose phrases. Apply antipattern detection. Re-run evaluation suite. This is free and often yields 30-40% savings immediately. |
| 3 | Structure for caching | Separate static content (system prompt, rules, examples) from dynamic content (user query, session data). Place static content first. Every changed character breaks cache prefix. |
| 4 | Implement token budgeting | Allocate percentage of context to each component: e.g., 40% user query/system, 50% retrieved docs, 10% history. Truncate or summarize less critical parts to stay within budget. |
| 5 | Add RAG pipeline | For external documents: chunk, embed, store in vector DB. At query time, retrieve only top-k most relevant chunks. Don't stuff entire knowledge base into context. |
| 6 | Enable advanced caching | Use provider-side prompt caching (OpenAI, Anthropic) for long static prefixes. Add client-side semantic caching for frequently similar queries. Track cache hit rates. |
| 7 | Implement context compression | For very long contexts, use summarization (for history) or selective pruning tools like LLMLingua (for documents). Start conservative (10-20% compression), increase while monitoring quality. |

**Key Considerations:**
- KV-cache optimization with stable prompts can reduce latency by 65% and costs by 71%
- "Lost-in-the-middle" problem: models under-attend to information in the middle of long contexts; place critical content at beginning or end
- Output tokens typically cost 2-4x more than input tokens; optimize both ends

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Hierarchical Summarization | Extremely long documents (books, contracts, reports) that far exceed context window | Split into chunks, summarize each chunk, then summarize the summaries. Multi-level compression for documents that would be 10-100x too large. |
| Adaptive Token Budgeting | Variable-length inputs where components compete for limited context space | Dynamic allocation: if retrieved docs are short, give more space to history; if history is long, compress aggressively to preserve doc space. Per-component budget adjusts based on actual needs. |
| Map-Reduce Context Processing | Tasks requiring analysis of many independent documents | Process chunks in parallel (map), then synthesize results (reduce). Avoids stuffing all docs into single context. Can be hierarchical for 100K+ token inputs. |
| Semantic Caching | High-volume systems with similar but not identical queries | Cache by embedding similarity, not exact match. If query is 95%+ similar to cached query, return cached response. Requires semantic search infrastructure. |
| Gist Tokens (Advanced) | Extremely high-volume, highly repetitive prompt structures where fine-tuning is feasible | Fine-tune model to compress long prompts into virtual "gist tokens". Compress 5K token system prompt into 100 tokens. Requires significant engineering investment; only ROI-positive at massive scale. |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Ignoring cache invalidation | Underlying data changes, but cached responses serve stale information | Implement TTL (time-to-live) for cache entries (1-24 hours typical). Add event-driven invalidation when source data updates. Include version hash in cache keys. |
| Overly aggressive compression | High compression ratios remove critical details; model can't answer accurately | Start with conservative compression (10-20%). Run evaluation suite after each adjustment. Use "protected keywords" features in compression tools to preserve key terms. |
| Lost-in-the-middle | Critical information buried in middle of long context is ignored by model | Place most important content at beginning or end (models over-attend first 10-20% and last 10-20%). Use re-ranking to move relevant docs to edges. |
| Treating all context equally | Different context types have different importance, but all concatenated uniformly | Use structural tags (`<documents>`, `<history>`, `<query>`) to help model differentiate. Implement token budget with explicit priority per context type. |
| Implementing only one strategy | Relying solely on RAG or truncation when a combination would be far more effective | Think in layers: RAG to retrieve, compression to shrink, caching to speed up. Combine strategies to address multiple challenges (cost, latency, accuracy). |
| Optimizing without baseline | Starting optimization without measuring current performance; can't prove improvement or detect regressions | Always establish baseline first: cost per request, quality scores, latency. Document metrics before and after each change. Use evaluation suite consistently. |
| Ignoring output token costs | Focusing only on input optimization while allowing verbose outputs that consume 2-4x more expensive output tokens | Add conciseness instructions ("Be brief in your response"). Use structured outputs (JSON Mode). Set appropriate max_tokens limits based on actual need. |
| Over-optimizing for readability | Making prompts so cryptic they become unmaintainable, sacrificing long-term usability for token savings | Balance optimization with clarity. Prompts should still be human-readable. Add comments if optimization makes structure dense. Maintainability matters. |
| Not calculating ROI | Implementing expensive techniques (APO, gist tokens) without verifying investment will be offset by production savings | Calculate ROI: engineering cost vs. expected monthly savings. Break-even period should be <3 months. Advanced techniques only cost-effective for high-volume use cases. |

---

## Examples

### Example 1: Conversation History — From Naive to Summarized

**Problem:** A chatbot accumulates long conversation history; full history included in every prompt, quickly exhausting context limit.

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Entire conversation history (2500 tokens)<br>`User: Tell me about project A.`<br>`Bot: Project A is about X.`<br>`...`<br>(Many turns later)<br>`...`<br>`User: What were the risks we discussed for it?` | **Prompt:**<br>Condensed history (450 tokens)<br>`System: The user and AI have discussed Project A, its goals (X), and timeline (Y).`<br>`User: What were the risks we discussed for it?` |
| **Output:**<br>Response based on full history | **Output:**<br>Response based on summary (same quality) |
| **Issue:** 2500 tokens consumed by verbose history; approaching context limit quickly | **Result:** 82% token savings (2500 → 450) while preserving key entities and topics. Context budget freed for other uses. |

**Metric:** 82% reduction in history tokens, 0% quality degradation on follow-up questions

---

### Example 2: Cache-Friendly Structure — Product Description Generator

**Problem:** Application generates product descriptions; prompt mixes static instructions with dynamic details, preventing effective caching.

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`Generate a product description.`<br>`Product: "Wireless Headphones"`<br>`Use a fun and energetic tone.`<br>`Details: "Bluetooth 5.3, 40-hour battery, noise-cancelling"`<br>`Mention target audience is young professionals.` | **Prompt:**<br>`<system_prompt>`<br>`You are a marketing copywriter. Generate product descriptions using fun and energetic tone for young professionals.`<br>`</system_prompt>`<br><br>`Product: "Wireless Headphones"`<br>`Details: "Bluetooth 5.3, 40-hour battery, noise-cancelling"` |
| **Output:**<br>Product description (quality ok) | **Output:**<br>Product description (same quality, faster, cheaper) |
| **Issue:** Mixed static/dynamic structure prevents caching; every request processes full prompt from scratch | **Result:** Static prefix cached; 80% lower latency on cache hits, 90% lower input token costs. Consistent prefix enables provider-side caching. |

**Metric:** Up to 80% latency reduction, 90% input cost reduction on cached requests (OpenAI prompt caching data)

---

### Example 3: RAG with Compression — Document Analysis

**Problem:** RAG system retrieves several large documents; stuffing all into context is expensive and risks lost-in-the-middle.

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Total retrieved context: 3 documents, 4000 tokens<br>`<documents>`<br>`[Full text of Document 1]`<br>`[Full text of Document 2]`<br>`[Full text of Document 3]`<br>`</documents>`<br><br>`<user_query>`<br>`Summarize key Q3 findings.`<br>`</user_query>` | **Prompt:**<br>Compressed context: 1600 tokens<br>`<documents>`<br>`[Compressed text of Document 1, 2, and 3 using LLMLingua]`<br>`</documents>`<br><br>`<user_query>`<br>`Summarize key Q3 findings.`<br>`</user_query>` |
| **Output:**<br>Summary (may miss middle doc details) | **Output:**<br>Summary with better coverage (denser context) |
| **Issue:** 4000 tokens expensive; middle document often under-attended | **Result:** 60% token reduction (4000 → 1600); denser context helps mitigate lost-in-the-middle; lower cost and latency. |

**Metric:** 60% input token savings, improved middle-document attention, 30% cost reduction per request

---

### Example 4: Manual Prompt Optimization — Simple Text Compression

**Problem:** Verbose prompt increases token costs without adding value.

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`"Considering all the information that has been provided to you, could you please generate a concise summary of the main document in approximately 50 words?"`<br>(26 tokens) | **Prompt:**<br>`"Summarize the document in 50 words."`<br>(7 tokens) |
| **Output:**<br>50-word summary | **Output:**<br>50-word summary (identical quality) |
| **Issue:** Filler words inflate token count without improving output | **Result:** 73% token savings (26 → 7) with zero loss of meaning. Free optimization requiring no tools. |

**Metric:** 73% token reduction, 0% quality change, 0 engineering cost (manual edit)

---

### Example 5: Selective Context with Re-Ranking — RAG Quality Improvement

**Problem:** RAG retrieves 10 chunks, but not all equally relevant; sending all is expensive and introduces noise.

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Top 10 chunks retrieved (4000 tokens)<br>`<documents>`<br>`[Chunk 1 - highly relevant]`<br>`[Chunk 2 - moderately relevant]`<br>`...`<br>`[Chunk 10 - barely relevant]`<br>`</documents>` | **Prompt:**<br>Top 3 re-ranked chunks (1200 tokens)<br>`<documents>`<br>`[Chunk 1 - highly relevant]`<br>`[Chunk 2 - highly relevant]`<br>`[Chunk 3 - highly relevant]`<br>`</documents>` |
| **Output:**<br>Answer (may use low-quality chunks) | **Output:**<br>Answer (higher quality, less noise) |
| **Issue:** Low-relevance chunks waste tokens and add noise | **Result:** 70% token reduction (4000 → 1200); improved quality by removing noise; lower cost. Re-ranker selects highest-signal chunks. |

**Metric:** 70% token savings, measurable quality improvement from noise reduction, 50% cost reduction

---

## Quality Checklist

Before deploying context management strategies to production:

- [ ] **Baseline established:** Current token usage (input/output), latency, quality metrics documented before optimization begins
- [ ] **Manual optimization applied:** Verbose phrasing removed, direct language used, antipatterns checked; low-hanging fruit captured (typically 30-40% savings)
- [ ] **Static/dynamic separation:** Prompt structured with static content (system, rules, examples) first, dynamic content (query, session) last for caching
- [ ] **Token budget defined:** Explicit percentage allocation to each context component (history, docs, query); enforcement logic implemented
- [ ] **RAG pipeline (if applicable):** Documents chunked, embedded, stored in vector DB; retrieval returns top-k relevant chunks, not entire corpus
- [ ] **Caching configured:** Provider-side prompt caching enabled for long static prefixes; cache hit rate monitoring in place
- [ ] **Compression tested:** If using context compression, evaluated against quality baseline; compression ratio tuned to maintain target quality (typically start 10-20%)
- [ ] **Lost-in-the-middle addressed:** Critical information placed at beginning or end; re-ranking applied if using multi-document RAG
- [ ] **Output optimization:** Conciseness instructions added; structured outputs used where applicable; max_tokens set based on actual need
- [ ] **ROI calculated:** For advanced techniques (APO, gist tokens), engineering cost vs. expected production savings verified; break-even <3 months

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Prompt Caching (OpenAI) | https://platform.openai.com/docs/guides/prompt-caching |
| Prompt Caching (Anthropic) | https://www.anthropic.com/blog/prompt-caching |
| KV-Caching Explained | https://huggingface.co/blog/not-lain/kv-caching |
| Context Engineering (Anthropic) | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| Token Budgeting Strategies | https://dev.co/ai/token-budgeting-strategies-for-long-context-llm-apps |
| LLMLingua (Compression) | https://arxiv.org/abs/2310.05736 |
| Prompt Versioning | https://launchdarkly.com/blog/prompt-versioning-and-management/ |
| RAG Best Practices (Agenta) | https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | OpenAI — Prompt Caching | https://platform.openai.com/docs/guides/prompt-caching | 2025-11-21 | n.a | 9.7 | 10 | 10 | 9 |
| 2 | Anthropic — Effective context engineering for AI agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2025-11-21 | 2025-09-29 | 9.3 | 10 | 9 | 9 |
| 3 | Hugging Face — KV Caching Explained | https://huggingface.co/blog/not-lain/kv-caching | 2025-11-21 | n.a | 9.0 | 9 | 9 | 9 |
| 4 | arXiv — LLMLingua: Compressing Prompts | https://arxiv.org/abs/2310.05736 | 2025-11-21 | 2023-10-09 | 8.7 | 10 | 9 | 7 |
| 5 | Agenta — Top 6 Techniques to Manage Context Length | https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms | 2025-11-21 | n.a | 8.0 | 8 | 8 | 8 |
| 6 | Dev.co — Token Budgeting Strategies | https://dev.co/ai/token-budgeting-strategies-for-long-context-llm-apps | 2025-11-21 | n.a | 7.7 | 8 | 8 | 7 |
| 7 | LaunchDarkly — Prompt Versioning Guide | https://launchdarkly.com/blog/prompt-versioning-and-management/ | 2025-11-21 | 2025-03-28 | 7.3 | 8 | 7 | 7 |
| 8 | Latitude — Production-Grade Prompt Engineering | https://latitude-blog.ghost.io/blog/10-best-practices-for-production-grade-llm-prompt-engineering/ | 2025-11-21 | n.a | 7.0 | 7 | 7 | 7 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| [DataCamp: Prompt Compression Tutorial](https://www.datacamp.com/tutorial/prompt-compression) | 5.7 | Educational site focus (AT:6), Some promotional content (TR: 7→5), Basic coverage (TM:6) |
| [Medium: My Context Management Strategy](https://medium.com/example) | 4.3 | Personal blog (AT:4), Anecdotal only (TR:5), Narrow scope (TM:4) |

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2026-01-20*

