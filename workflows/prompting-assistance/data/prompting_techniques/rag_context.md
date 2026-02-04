---
---

# RAG Context

**Problem Type:** Context Management

**Related Anti-Patterns:** Addresses [Context Overload](prompting_anti_patterns.md#context-anti-patterns)

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

LLMs lack knowledge of recent events and private data; stuffing entire documents into context is expensive and degrades accuracy ("lost in the middle").

---

## Technique Overview

RAG retrieves relevant document chunks at query time and injects them into the prompt, grounding responses in external knowledge with source citations.

**Core Mechanism:** Convert documents to embeddings, store in vector database, retrieve similar chunks via semantic search, and inject only relevant context into the prompt.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Q&A over large knowledge bases (10k+ documents) | Tasks requiring holistic document understanding |
| Applications needing up-to-date information | Small, static document sets that fit in context |
| Systems requiring source citations | Creative tasks where grounding limits output |
| Cost-sensitive applications with large corpora | Highly interconnected documents (legal contracts) |
| Domain-specific knowledge (support, docs, research) | Real-time streaming data without indexing |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Choose chunking strategy | Semantic chunking for narrative text; recursive for code; fixed-size with overlap as baseline |
| 2 | Enrich chunks with metadata | Add source URL, document name, page number, date for citation capability |
| 3 | Select embedding model | Evaluate on MTEB benchmark; BGE and E5 are strong open-source options |
| 4 | Implement hybrid retrieval | Combine dense (vector) + sparse (BM25/keyword) search for best recall |
| 5 | Add re-ranking layer | Use cross-encoder to re-rank top 10-20 results; select top 3-5 for prompt |
| 6 | Design prompt with citations | Instruct LLM to cite sources; include "say I don't know if not in context" |
| 7 | Evaluate with RAG metrics | Measure faithfulness, answer relevancy, context precision/recall |

**Key Considerations:**
- Chunk size baseline: 512 tokens with 10% overlap; adjust based on evaluation
- Metadata is essential for citations—chunks without source info cannot be traced
- Re-ranking is the highest-impact optimization for retrieval precision

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Long Context Model (LCM) | Holistic document analysis, highly interconnected text | Entire document in context instead of retrieval; higher cost, avoids chunking loss |
| Hybrid RAG + LCM | Variable query complexity, mixed workloads | RAG for specific queries; LCM for summarization or cross-document reasoning |
| Cache-Augmented Generation (CAG) | Frequent repeated queries | Pre-compute and cache responses for common questions; reduce latency and cost |
| Query expansion | Low recall, ambiguous user queries | LLM rewrites query or generates variants before retrieval |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Single chunking strategy for all content | Code broken mid-function; tables split across chunks | Match strategy to content type: semantic for prose, recursive for code |
| No metadata on chunks | Cannot implement citations; no filtering capability | Enrich every chunk with source, page, date at ingestion time |
| Vector-only search | Misses exact matches (acronyms, product IDs, proper names) | Implement hybrid retrieval: vector + BM25 keyword search |
| No re-ranking step | Top-k results include irrelevant noise | Add cross-encoder re-ranker between retrieval and generation |
| Assuming longer context is always better | High cost, latency, and "needle in haystack" degradation | Use RAG for most queries; reserve LCM for holistic tasks |
| No RAG-specific evaluation | Cannot identify if problem is retrieval or generation | Evaluate separately: context precision/recall for retrieval, faithfulness for generation |

---

## Examples

### Example 1: Customer Support Chatbot

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Setup:**<br>10k KB articles loaded into prompt context | **Setup:**<br>Articles chunked, indexed with metadata; hybrid retrieval |
| **Output:**<br>Exceeds token limit; slow; misses relevant articles | **Output:**<br>Fast retrieval; cites specific article with URL |
| **Issue:** Unsustainable cost; poor accuracy | **Result:** 80% cost reduction; response time <2s; traceable citations |

**Metric:** Cost per query reduced from $0.50 to $0.10; latency from 15s to 1.5s; user trust increased via citations

---

### Example 2: RAG Faithfulness Improvement

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Answer based on context. (no re-ranking) | **Prompt:**<br>Re-ranked top 5 chunks + "cite sources, say I don't know if not in context" |
| **Output:**<br>"Click Reset Password" (hallucinated—context says "Change Password") | **Output:**<br>"Go to Settings > Security, click Change Password. [Source: Article #123]" |
| **Issue:** 50% faithfulness score | **Result:** 95% faithfulness score via re-ranking + explicit instruction |

**Metric:** 45 percentage point improvement in faithfulness; hallucination rate reduced by 90%

---

### Example 3: Hybrid Architecture for Analytics

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Approach:**<br>RAG for all queries | **Approach:**<br>RAG for specific queries; LCM for monthly summaries |
| **Output:**<br>Summaries miss cross-document patterns | **Output:**<br>Specific queries: precise RAG answers. Summaries: comprehensive LCM analysis |
| **Issue:** RAG cannot synthesize across 1000s of feedback items | **Result:** Specific query cost low; summary quality high |

**Metric:** 70% queries handled by RAG at $0.05/query; 30% summaries via LCM at $0.50/query; overall cost optimized

---

## Quality Checklist

- [ ] Chunking strategy matched to content type (semantic for prose, recursive for code)
- [ ] All chunks enriched with source metadata (URL, page, date)
- [ ] Hybrid retrieval implemented (vector + keyword search)
- [ ] Re-ranking layer filters top-k results before prompt injection
- [ ] Prompt instructs LLM to cite sources and refuse if answer not in context
- [ ] RAG pipeline evaluated with faithfulness and context precision metrics
- [ ] Chunk size and overlap tuned based on evaluation results
- [ ] Cache layer implemented for frequent queries
- [ ] Production monitoring tracks retrieval quality and generation faithfulness

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| LangChain RAG | [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag/) |
| Pinecone RAG Guide | [pinecone.io/learn/retrieval-augmented-generation](https://www.pinecone.io/learn/retrieval-augmented-generation/) |
| MTEB Embedding Benchmark | [huggingface.co/spaces/mteb/leaderboard](https://huggingface.co/spaces/mteb/leaderboard) |
| RAG Paper (Lewis et al.) | [arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401) |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al.) | [arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401) | 2025-11-21 | 2020-05-22 | 9.7 | 10 | 10 | 9 |
| 2 | Searching for Best Practices in RAG (Wang et al.) | [arxiv.org/abs/2407.01219](https://arxiv.org/abs/2407.01219) | 2025-11-21 | 2024-07-01 | 9.0 | 10 | 9 | 8 |
| 3 | Elastic — Why RAG Still Matters | [elastic.co/search-labs/blog/rag-vs-long-context](https://www.elastic.co/search-labs/blog/rag-vs-long-context-model-llm) | 2025-11-21 | 2025 | 7.3 | 8 | 6 | 8 |
| 4 | Databricks — Ultimate Guide to Chunking Strategies | [community.databricks.com/.../chunking-strategies](https://community.databricks.com/t5/technical-blog/the-ultimate-guide-to-chunking-strategies-for-rag-applications/ba-p/113089) | 2025-11-21 | 2025 | 7.0 | 8 | 6 | 7 |
| 5 | Pinecone — What is RAG? | [pinecone.io/learn/retrieval-augmented-generation](https://www.pinecone.io/learn/retrieval-augmented-generation/) | 2025-11-21 | n.a. | 6.7 | 7 | 5 | 8 |
| 6 | LangChain — RAG Documentation | [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag/) | 2025-11-21 | n.a. | 6.3 | 7 | 5 | 7 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Chitika — Source Tracking in RAG | 5.3 | Low authority (AT: 5), commercial focus |
| Medium — Hybrid Architectures (Ganesh) | 5.7 | Platform authority penalty (AT: 5), marketing tone |
| Superannotate — RAG vs Long-context LLMs | 5.7 | Marketing language penalty (TR: 6→4) |

---

*Last updated: 2026-01-20*

