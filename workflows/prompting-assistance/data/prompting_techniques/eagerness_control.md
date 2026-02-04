---
---

# Eagerness Control

**Problem Type:** Iteration & Refinement | Task Decomposition

**Related Anti-Patterns:** Addresses [Premature Stopping](prompting_anti_patterns.md#scope-and-complexity-anti-patterns), [Over-Engineering](prompting_anti_patterns.md#scope-and-complexity-anti-patterns)

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

Agents either act too quickly (missing important steps) or too cautiously (asking for confirmation unnecessarily), creating efficiency vs depth tradeoffs.

---

## Technique Overview

Eagerness control adjusts agent behavior along the efficiency-depth spectrum by explicitly instructing confidence thresholds and action-taking behavior. Less eagerness: "Solve with minimum tool calls. If 70% confident, proceed." More eagerness: "Research or deduce and act. Never ask to confirm assumptions."

**Core Mechanism:** By setting explicit confidence thresholds and action-taking rules, the model adjusts its default behavior to match task requirements—prioritizing speed for simple tasks or depth for complex investigations.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Tasks requiring efficiency-speed tradeoff calibration | Simple single-step tasks with no tradeoff |
| Agentic workflows where action frequency matters | Tasks with fixed, predetermined steps |
| Scenarios where confidence thresholds affect outcomes | High-risk decisions requiring human approval |
| Multi-step workflows with varying complexity per step | Single-turn queries without tool use |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Assess task requirements | Determine if task needs efficiency (fewer steps, faster) or depth (more research, thoroughness) |
| 2 | Choose eagerness level | Select "less eagerness" for efficiency or "more eagerness" for depth |
| 3 | Add explicit instruction | Less: "Solve with minimum tool calls. If 70% confident, proceed." More: "Research or deduce and act. Never ask to confirm assumptions." |
| 4 | Set confidence thresholds | Specify numeric thresholds (e.g., 70%, 80%) for action-taking decisions |
| 5 | Define action rules | Specify when to proceed vs when to research further |
| 6 | Monitor behavior | Track tool call frequency and confirmation requests to validate eagerness calibration |

**Key Considerations:**
- Less eagerness reduces tool calls and latency but may miss edge cases
- More eagerness increases thoroughness but may waste resources on simple tasks
- Confidence thresholds should match task risk level (higher risk = higher threshold)

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| **Confidence-Based Eagerness** | Tasks with clear confidence metrics | Use numeric thresholds: "If confidence > 80%, act; if < 80%, research further" |
| **Step-Specific Eagerness** | Multi-step workflows with varying requirements | Apply different eagerness levels per step: "Step 1: high eagerness, Step 2: low eagerness" |
| **Adaptive Eagerness** | Tasks where requirements change dynamically | "Start with high eagerness; if errors occur, switch to low eagerness" |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| **Conflicting instructions** | Eagerness control conflicts with persistence prompts | Align instructions: eagerness controls action-taking speed, persistence controls task completion |
| **Inappropriate thresholds** | 70% threshold too low for high-risk tasks | Match confidence threshold to task risk: 90%+ for critical decisions, 70% for routine tasks |
| **No monitoring** | Cannot verify if eagerness calibration is working | Track metrics: tool calls per task, confirmation requests, error rates |
| **Static eagerness** | Same eagerness level for all task types | Adjust eagerness per task complexity: high for simple, low for complex |

---

## Examples

### Example 1: Less Eagerness — Quick Data Lookup

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Find the population of Paris."<br><br>**Output:**<br>Agent makes 3 tool calls: search("Paris"), search("Paris population"), search("Paris France population 2025")<br><br>**Issue:** Over-researching simple query, high latency | **Prompt:**<br>"Find the population of Paris. Solve with minimum tool calls. If 70% confident, proceed."<br><br>**Output:**<br>Agent makes 1 tool call: search("Paris population"), returns result immediately |
| **Issue:** 3x more tool calls than needed, 3x latency | **Result:** Single tool call, 66% latency reduction |

**Metric:** 66% reduction in tool calls (3 → 1), 66% latency reduction (900ms → 300ms)

---

### Example 2: More Eagerness — Deep Research Task

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Research quantum computing advances in 2025."<br><br>**Output:**<br>Agent finds one article, summarizes it, asks: "Should I research more sources?"<br><br>**Issue:** Stops prematurely, requires human confirmation | **Prompt:**<br>"Research quantum computing advances in 2025. Research or deduce and act. Never ask to confirm assumptions."<br><br>**Output:**<br>Agent researches multiple sources, synthesizes findings, provides comprehensive analysis without stopping |
| **Issue:** Incomplete research, requires follow-up | **Result:** Complete research delivered autonomously |

**Metric:** 3x more sources researched (1 → 3), 100% autonomous completion vs 40% with standard prompting

---

## Quality Checklist

Before deploying eagerness control, verify:

- [ ] Eagerness level matches task requirements (less for efficiency, more for depth)
- [ ] Confidence thresholds are explicitly stated (e.g., "70% confident")
- [ ] Action-taking rules are clear ("proceed" vs "research further")
- [ ] Eagerness instructions don't conflict with persistence or safety prompts
- [ ] Monitoring in place to track tool call frequency and confirmation requests
- [ ] Eagerness level adjusted per task complexity (not one-size-fits-all)

---

## Technical Reference

> **Link Verification:** All links verified as of 2026-01-23.

| Topic | Official Documentation |
|-------|------------------------|
| Agent Efficiency Patterns | Read [prompt_engineering.md](prompt_engineering.md) for ReAct patterns |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | GPT-5 Prompting Guide | https://cookbook.openai.com/examples/gpt-5/gpt-5_prompting_guide | 2026-01-23 | 2025 | 8.7 | 10 | 8 | 9 |

---

## Discarded Sources

*No sources were discarded during research.*

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2026-01-23*





