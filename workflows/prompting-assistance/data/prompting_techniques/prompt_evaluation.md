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
11. [Discarded Sources](#discarded-sources)

---

## Problem Solved

LLM outputs vary unpredictably; without systematic evaluation, teams cannot measure improvements, detect regressions, or ensure production quality.

---

## Technique Overview

Prompt evaluation combines code-based metrics, LLM-as-a-Judge, and human review to quantify output quality. Creates feedback loops for evidence-based prompt iteration.

**Core Mechanism:** Define success criteria upfront, test against golden datasets, use automated metrics for consistency, and validate with human judgment for nuance.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Production prompts requiring quality assurance | One-off exploratory prompts |
| A/B testing prompt versions | Simple, deterministic tasks |
| Detecting regressions after model updates | Tasks with no measurable success criteria |
| RAG systems needing faithfulness verification | Low-stakes internal tools |
| High-stakes applications (customer-facing, financial) | Prototyping phase before requirements are clear |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Define SMART success criteria | Specific, Measurable, Achievable, Relevant, Time-bound metrics before prompting |
| 2 | Create golden test set | Include typical cases, edge cases, and adversarial inputs with expected outputs |
| 3 | Select evaluation metrics | Choose code-based (exact match, ROUGE), LLM-as-a-Judge (relevance, coherence), or human review |
| 4 | Implement automated tests | Use frameworks like DeepEval to create assertions; integrate with CI/CD |
| 5 | Configure LLM-as-a-Judge | Provide detailed rubrics, scoring scales, and examples; validate with human reviewers |
| 6 | Run A/B tests in production | Split traffic between prompt versions; measure business metrics (conversion, CSAT) |
| 7 | Monitor and iterate | Track production metrics, collect user feedback, expand golden set with failure cases |

**Key Considerations:**
- LLM-as-a-Judge requires calibration: invert response order (A/B and B/A) to mitigate position bias
- Golden sets should cover 80% typical cases, 20% edge cases and adversarial inputs
- Definition of Done should include both technical metrics and peer review

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Offline evaluation only | Pre-production validation, CI/CD gates | No live traffic; uses static golden datasets exclusively |
| LLM-as-a-Judge cascade | High-volume evaluation with cost constraints | Uses cheaper model for initial scoring, expensive model for borderline cases |
| Human-in-the-loop evaluation | Subjective quality dimensions, safety-critical | Human reviewers score subset; calibrates automated metrics |
| Real-time production monitoring | Post-deployment quality tracking | Continuous metrics (latency, cost, user feedback) rather than batch evaluation |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Vague success criteria | Cannot measure progress; decisions become subjective | Define SMART criteria: "reduce hallucination rate by 15%" not "improve quality" |
| Offline-only evaluation | Prompt may fail with real user traffic patterns | Validate with A/B tests on production traffic |
| Blind trust in LLM-as-a-Judge | Judge has biases (position, agreement, style) | Calibrate with human reviewers; invert comparison order |
| Ignoring edge cases | System vulnerable to unexpected inputs, prompt injection | Include adversarial cases in golden set (10-20% of test cases) |
| One-time evaluation | Performance drifts with model updates and user behavior | Implement continuous monitoring and periodic re-evaluation |
| Metrics disconnected from business | Technical improvements don't translate to user value | Link evaluation metrics to business KPIs (CSAT, conversion, resolution time) |

---

## Examples

### Example 1: Email Generation A/B Test

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Write a short email for a customer who hasn't purchased in 90 days. | **Prompt:**<br>You are a retention specialist. Write a persuasive, friendly email (max 150 words) for {{customer_name}} who hasn't visited in 90 days. Include 15% discount code VOLTA15, valid 7 days. |
| **Output:**<br>Generic email, no personalization | **Output:**<br>Personalized, actionable email with clear CTA |
| **Issue:** No way to know if prompt works | **Result:** Open rate 12%→18%, CTR 1.5%→4.2% |

**Metric:** 50% improvement in open rate, 180% improvement in click-through rate via A/B test

---

### Example 2: RAG Faithfulness Evaluation

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>Answer the question based on the context. | **Prompt:**<br>Answer based ONLY on the provided context. If information is not in context, say "I don't know." |
| **Output:**<br>"To reset your password, click 'Reset Password'" (hallucinated) | **Output:**<br>"Password reset requires admin. For password change, go to Settings > Security." |
| **Issue:** Undetected hallucination in production | **Result:** Faithfulness score 50%→95% via LLM-as-a-Judge |

**Metric:** 45 percentage point improvement in faithfulness using FaithfulnessMetric with statement decomposition

---

### Example 3: Production Quality Gate

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Process:**<br>Manual review before deployment | **Process:**<br>Automated CI/CD with DeepEval assertions |
| **Output:**<br>Inconsistent quality, delayed releases | **Output:**<br>Every PR evaluated against golden set |
| **Issue:** Human bottleneck, missed regressions | **Result:** 100% regression test coverage, 3x faster releases |

**Metric:** Zero production regressions in 6 months, deployment time reduced from 2 weeks to 2 days

---

## Quality Checklist

- [ ] Success criteria defined as SMART metrics before prompt development
- [ ] Golden test set includes typical cases, edge cases, and adversarial inputs
- [ ] Evaluation uses hybrid approach (code metrics + LLM-as-a-Judge + human review)
- [ ] LLM-as-a-Judge rubric includes explicit criteria, scoring scale, and examples
- [ ] Position bias mitigation implemented (A/B and B/A comparison)
- [ ] Evaluation integrated into CI/CD pipeline
- [ ] A/B tests measure business metrics, not just model metrics
- [ ] Production monitoring tracks latency, cost, and user feedback
- [ ] Failure cases from production added to golden test set
- [ ] Definition of Done documented and enforced

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| DeepEval Framework | [deepeval.confident-ai.com](https://deepeval.confident-ai.com/) |
| Langfuse Observability | [langfuse.com/docs](https://langfuse.com/docs) |
| MT-Bench and Chatbot Arena | [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685) |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | [arxiv.org/abs/2306.05685](https://arxiv.org/abs/2306.05685) | 2025-11-21 | 2023-06-09 | 9.0 | 10 | 9 | 8 |
| 2 | Confident AI — LLM Evaluation Metrics | [confident-ai.com/blog/llm-evaluation-metrics](https://www.confident-ai.com/blog/llm-evaluation-metrics-everything-you-need-for-llm-evaluation) | 2025-11-21 | 2025 | 7.7 | 7 | 7 | 9 |
| 3 | Datadog — Building an LLM Evaluation Framework | [datadoghq.com/blog/llm-evaluation-framework](https://www.datadoghq.com/blog/llm-evaluation-framework-best-practices/) | 2025-11-21 | 2025 | 7.3 | 8 | 6 | 8 |
| 4 | Braintrust — A Practical Guide to A/B Testing LLM Prompts | [braintrust.dev/articles/ab-testing](https://www.braintrust.dev/articles/ab-testing-llm-prompts) | 2025-11-21 | 2025 | 7.0 | 7 | 6 | 8 |
| 5 | PromptHub — Success criteria, test cases, evals | [prompthub.us/blog/everything-you-need](https://www.prompthub.us/blog/everything-you-need-to-do-before-prompting-success-criteria-test-cases-evals) | 2025-11-21 | 2025 | 6.7 | 6 | 6 | 8 |
| 6 | Comet — LLM Evaluation Frameworks Comparison | [comet.com/site/blog/llm-evaluation-frameworks](https://www.comet.com/site/blog/llm-evaluation-frameworks/) | 2025-11-21 | 2025 | 6.3 | 7 | 5 | 7 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Traceloop — A/B Testing LLM Models | 5.7 | Marketing language penalty (TR: 7→5), lower authority (AT: 6) |
| Evidently AI — LLM-as-a-Judge guide | 5.3 | Marketing language penalty (TR: 7→4), commercial focus |

---

*Last updated: 2026-01-20*

