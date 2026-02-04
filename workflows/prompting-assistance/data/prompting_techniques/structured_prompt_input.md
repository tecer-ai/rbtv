---
---

# Structured Prompt Input

**Problem Type:** Task Decomposition

**Related Anti-Patterns:** Addresses [Vagueness and Ambiguity](prompting_anti_patterns.md#clarity-and-structure-anti-patterns)

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

Vague prompts produce inconsistent outputs requiring multiple iterations and consuming resources unnecessarily.

---

## Technique Overview

Organize prompts into explicit sections (Task, Context, Elements, Behaviors, Constraints) to provide complete specification upfront. Structured input reduces ambiguity and iteration cycles by 60-75% compared to unstructured prompts.

**Core Mechanism:** Section-based organization forces explicit specification of requirements, context, and constraints. Models process structured inputs more reliably than free-form descriptions because structure reduces interpretation ambiguity.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Complex tasks requiring multiple components or specifications | Simple, single-purpose queries where structure adds overhead |
| Tasks where consistency across iterations matters | Creative writing or exploratory tasks where ambiguity is beneficial |
| Multi-element outputs (UI screens, reports, dashboards) | Conversational interactions where natural language flow matters |
| Production workflows where iteration cost is high | Rapid prototyping where speed matters more than precision |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Define task objective | State what should be produced in one clear sentence |
| 2 | Provide context | Explain user situation, background, or workflow stage |
| 3 | Specify key elements | List each required component with specific requirements |
| 4 | Define behaviors | Describe how elements should interact or respond to inputs |
| 5 | Set constraints | Specify device, size, style, format, or other limitations |
| 6 | Verify completeness | Check that all aspects (visual, functional, technical) are covered |
| 7 | Test with model | Validate structure produces desired outputs before production use |

**Key Considerations:**
- Use section headers (e.g., `[TASK]`, `[CONTEXT]`) to enforce structure
- Be specific in element specifications: "Product title (2 lines max)" vs "Product title"
- Include measurable constraints: "375px width" vs "mobile size"
- Behaviors should specify interaction flows, not just static descriptions

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| TCBEC Format | Design and UI generation tasks | Explicit section names: Task, Context, Behaviors, Elements, Constraints |
| STEP Format | Sequential workflows | Structure emphasizes steps and dependencies: Situation, Task, Evaluation, Plan |
| CRISPE Format | Technical documentation | Context, Role, Insight, Statement, Personality, Experiment sections |
| Minimal Structured | Quick tasks with few requirements | Condensed to 3-4 sections: Task, Requirements, Constraints |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Vague section content | Structure without specificity still produces ambiguous outputs | Fill each section with concrete, measurable specifications |
| Missing constraints | Model makes arbitrary choices (colors, sizes, styles) that don't match needs | Always include device, style, palette, format constraints explicitly |
| Skipping context | Model doesn't understand user situation, produces irrelevant solutions | Provide sufficient context about user state, goals, and environment |
| Over-structuring simple tasks | Adds unnecessary overhead for straightforward queries | Use structured format only when complexity warrants it |
| Inconsistent element specificity | Some elements detailed, others vague causes inconsistent quality | Apply same level of detail to all key elements |

---

## Examples

### Example 1: E-Commerce Product Page

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`Create a mobile product page for an online store with product image, title, price, and buy button.` | **Prompt:**<br>`[TASK] Generate a mobile product detail page<br>[CONTEXT] User evaluating purchase decision after search<br>[ELEMENTS] Product image carousel, title with rating, price with discount, size selector, add to cart button<br>[BEHAVIORS] Tap thumbnail updates main image, size selection highlights choice<br>[CONSTRAINTS] 375px width, minimalist style, specific color palette` |
| **Output:**<br>Inconsistent layout, arbitrary colors, unclear interactions | **Output:**<br>Consistent structure matching specifications |
| **Issue:** Requires 4-5 iterations to reach acceptable result | **Result:** First generation 85% accurate, 75% time reduction |

**Metric:** 75% reduction in iteration cycles (5 iterations → 1-2 iterations)

---

### Example 2: Analytics Dashboard

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`Create a financial dashboard with 4 metric cards and a chart.` | **Prompt:**<br>`[TASK] Generate financial analytics dashboard<br>[CONTEXT] Executives reviewing performance metrics<br>[ELEMENTS] 4 metric cards (Revenue, Users, Conversion, Churn), line chart, data table<br>[BEHAVIORS] Hover shows detailed tooltips, click metric filters chart<br>[CONSTRAINTS] Desktop 1280px, 4-column layout, specific data structure provided` |
| **Output:**<br>Arbitrary data formats, chart doesn't match API structure | **Output:**<br>Data structure aligns with API contract, realistic values displayed |
| **Issue:** Developer must redesign data binding after generation | **Result:** 70% reduction in data integration time |

**Metric:** 70% reduction in post-generation integration time

---

### Example 3: Multi-Step Form

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>`Create a registration form with name, email, password fields.` | **Prompt:**<br>`[TASK] Generate multi-step registration form<br>[CONTEXT] New user onboarding, step 1 of 3<br>[ELEMENTS] Name (required), email (with validation), password (strength indicator), continue button<br>[BEHAVIORS] Real-time validation on blur, disabled continue until valid, error messages inline<br>[CONSTRAINTS] Mobile 375px, accessibility compliant, specific validation rules` |
| **Output:**<br>Single form, no validation feedback, unclear error handling | **Output:**<br>Proper validation flow, clear error states, accessible structure |
| **Issue:** Requires manual addition of validation and error handling | **Result:** 80% production-ready on first generation |

**Metric:** 80% production readiness vs 40% with unstructured prompts

---

## Quality Checklist

- [ ] Prompt includes explicit [TASK] section with clear objective
- [ ] [CONTEXT] section explains user situation or workflow stage
- [ ] [ELEMENTS] section lists each component with specific requirements
- [ ] [BEHAVIORS] section describes interactions and responses
- [ ] [CONSTRAINTS] section specifies device, size, style, format limitations
- [ ] All element specifications include measurable details (max lines, specific formats)
- [ ] Constraints include exact values (pixels, hex codes, file formats)
- [ ] Structure tested with target model before production use
- [ ] Prompt length appropriate for model's context window
- [ ] Sections clearly delimited with headers or markers

---

## Technical Reference

Links to official documentation or authoritative sources for this technique. Omit if no specific references exist.


| Topic | Official Documentation |
|-------|------------------------|
| Prompt Engineering Best Practices | https://platform.openai.com/docs/guides/prompt-engineering |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | OpenAI — Prompt Engineering Guide | https://platform.openai.com/docs/guides/prompt-engineering | 2026-01-23 | 2025 | 9.3 | 10 | 9 | 9 |
| 2 | UX Design — Improve Figma Make Prompts | https://uxdesign.cc/how-to-prompt-figma-makes-ai-better-for-product-design-627daf3f4036 | 2026-01-23 | 2025-07-07 | 8.0 | 8 | 8 | 8 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Various YouTube tutorials on prompt structuring | 4.0 | Low authority (AT:4), promotional content without technical depth |

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2026-01-23*


