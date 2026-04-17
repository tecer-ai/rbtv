---
---

# Prompt Evaluation

**Problem Type:** Iteration & Refinement

**Related Anti-Patterns:** Addresses [Lack of Testing and Evaluation](prompting_anti_patterns.md#detection-methods)

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

---

## Problem Solved

LLM outputs vary across models, versions, and context conditions. Without systematic evaluation, you cannot measure improvements, detect regressions after model updates, or ensure consistent quality in production systems.

---

## Technique Overview

Prompt evaluation measures output quality through three complementary methods: automated metrics, LLM-as-a-Judge, and human review. The goal is evidence-based prompt iteration — knowing WHAT improved and WHY, not guessing.

**Core principle:** Define what "good" looks like BEFORE prompting. Test against that definition. Iterate based on measured gaps.

**2026 landscape shift:** Modern frontier models (Claude 4.x, GPT-5.x, Gemini 2.x) are significantly better at self-evaluation than their predecessors. LLM-as-a-Judge is now the dominant evaluation method for most use cases, with human review reserved for subjective quality and safety-critical applications.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Production prompts (customer-facing, financial, high-stakes) | One-off exploratory prompts |
| Agent workflows where output feeds into next step | Simple single-turn queries |
| Detecting regressions after model version upgrades | Prototyping phase before requirements are clear |
| RAG systems needing faithfulness verification | Low-stakes internal tools |
| Comparing prompt strategies across models | Tasks with no measurable success criteria |
| Workflow steps where quality gates block progression | Casual conversational use |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Define success criteria | What does a good output look like? Be specific: format, accuracy, tone, completeness, constraints. Not SMART-framework overhead — just clear pass/fail conditions. |
| 2 | Create test cases | Include typical inputs, edge cases, and adversarial inputs. 10-20 well-chosen cases beat 100 generic ones. Include expected outputs or evaluation rubrics. |
| 3 | Select evaluation method | **Automated metrics** (exact match, format validation) for structured outputs. **LLM-as-a-Judge** for open-ended quality. **Human review** for subjective dimensions or safety. |
| 4 | Run evaluation | Test prompt versions against the same test cases. Record scores, failures, and patterns. |
| 5 | Analyze failure modes | Don't just look at scores — understand WHY failures happen. Is it context? Instruction clarity? Model limitation? |
| 6 | Iterate on the prompt | Fix identified failure modes. Re-evaluate. Repeat until quality meets criteria. |
| 7 | Monitor in production | Track output quality over time. Model updates, data drift, and edge cases in real traffic will surface new failures. |

**Key considerations:**
- LLM-as-a-Judge requires calibration: test the judge itself against known-good/known-bad examples
- Position bias exists in pairwise comparison — invert order (A/B and B/A) to mitigate
- Golden test sets should grow from production failures — every bug becomes a test case

---

## Variations

| Variation | When to Use | Approach |
|-----------|-------------|----------|
| Quick A/B comparison | Choosing between 2-3 prompt versions | Run both against same inputs, compare outputs side-by-side or via LLM-as-a-Judge |
| Regression testing | After model version upgrade | Run existing golden set against new model, compare scores to baseline |
| Continuous monitoring | Production systems | Sample outputs periodically, evaluate via automated pipeline, alert on quality drops |
| Agent workflow gates | Multi-step agent systems | Evaluate output at each step before passing to the next — prevents error propagation |
| Self-evaluation | Single-turn quality check | Ask the model to evaluate its own output against criteria. Works surprisingly well with frontier models, but don't rely on it exclusively. |

---

## Pitfalls

| Pitfall | Why It Fails | Fix |
|---------|--------------|-----|
| No success criteria defined | Cannot measure progress — every output feels "okay" or "not quite right" | Write down what good looks like before prompting. Even rough criteria beat none. |
| Over-engineering evaluation | Spending more time evaluating than improving | Match evaluation effort to stakes. High-stakes production? Invest heavily. Internal tool? Quick A/B is enough. |
| Blind trust in LLM-as-a-Judge | Judge models have biases (verbosity preference, position bias, style bias) | Calibrate with human review on a subset. Verify the judge agrees with your judgment. |
| Ignoring failure analysis | Scores improve but you don't know why — fragile optimization | Analyze individual failures. Understand root causes. Fix the cause, not the symptom. |
| One-time evaluation | Prompt quality drifts with model updates and changing inputs | Implement periodic re-evaluation, especially after model upgrades. |
| Evaluating the wrong thing | Technical metrics improve but user satisfaction doesn't | Link evaluation to what actually matters — user value, task completion, downstream effects. |

---

## Examples

### Example 1: Agent Workflow Quality Gate

| Without Evaluation | With Evaluation |
|--------------------|-----------------|
| Agent step 1 produces mediocre research summary | Research summary evaluated against criteria: completeness, source coverage, factual grounding |
| Step 2 (analysis) builds on flawed summary | Gate blocks progression until summary meets quality threshold |
| Final output has compounded errors | Each step verified before handoff — errors caught at source |

**Key insight:** In multi-step agent workflows, evaluation at each step prevents error propagation. A bad input to step N+1 cannot be fixed by a better prompt at step N+1.

### Example 2: Prompt Version Comparison

| Prompt A (baseline) | Prompt B (candidate) |
|---------------------|---------------------|
| "Summarize this document." | "Summarize this document in 3-5 bullet points. Each bullet must cite a specific section. Flag any claims that lack supporting evidence." |
| Generic paragraph summary, no structure | Structured bullets with citations, explicit uncertainty flagging |
| LLM-as-a-Judge scores: Completeness 6/10, Actionability 4/10 | Completeness 8/10, Actionability 9/10 |

**Result:** Prompt B wins on both dimensions. The improvement came from specificity (format, citations, uncertainty) — not from prompt "tricks."

### Example 3: Regression Detection After Model Update

| Before Model Update | After Model Update |
|--------------------|--------------------|
| Golden set: 50 test cases, baseline scores recorded | Same 50 test cases, same prompts, new model version |
| Average faithfulness: 92% | Average faithfulness: 87% — regression detected |
| Investigation: new model is more concise, omitting qualifying statements | Fix: add explicit instruction to preserve caveats and qualifications |

**Key insight:** Model updates can silently degrade prompt performance. Automated regression testing catches what manual review misses.

---

## Quality Checklist

- [ ] Success criteria defined before prompt development
- [ ] Test cases cover typical inputs, edge cases, and adversarial inputs
- [ ] Evaluation method matches the stakes (automated for structured, LLM-as-a-Judge for open-ended, human for safety-critical)
- [ ] LLM-as-a-Judge calibrated against human judgment on a subset
- [ ] Failure analysis performed — root causes identified, not just scores tracked
- [ ] Evaluation integrated into development workflow (not an afterthought)
- [ ] Production monitoring in place for high-stakes applications
- [ ] Golden test set updated with real-world failure cases

---

## Technical Reference

| Topic | Resource |
|-------|----------|
| DeepEval Framework | [deepeval.confident-ai.com](https://deepeval.confident-ai.com/) |
| Langfuse Observability | [langfuse.com/docs](https://langfuse.com/docs) |
| Braintrust Evals | [braintrust.dev](https://www.braintrust.dev/) |
| MT-Bench and Chatbot Arena | [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685) |
| Anthropic Eval Guide | [docs.anthropic.com/en/docs/build-with-claude/develop-tests](https://docs.anthropic.com/en/docs/build-with-claude/develop-tests) |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685) | 2025-11-21 | 2023-06-09 | 9.0 | 10 | 9 | 8 |
| 2 | Confident AI — LLM Evaluation Metrics | [confident-ai.com/blog/llm-evaluation-metrics](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation) | 2025-11-21 | 2025 | 7.7 | 7 | 7 | 9 |
| 3 | Datadog — Building an LLM Evaluation Framework | [datadoghq.com/blog/llm-evaluation-framework](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/) | 2025-11-21 | 2025 | 7.3 | 8 | 6 | 8 |
| 4 | Braintrust — A Practical Guide to A/B Testing LLM Prompts | [braintrust.dev/articles/ab-testing](https://www.braintrust.dev/articles/ab-testing-llm-prompts) | 2025-11-21 | 2025 | 7.0 | 7 | 6 | 8 |

---

*Last updated: 2026-03-16*
