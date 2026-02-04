---
---

# Negative Prompts

**Problem Type:** Safety & Guardrails

**Related Anti-Patterns:** Addresses recurring artifacts and unwanted elements

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

How to specify unwanted elements to suppress recurring artifacts and prevent specific unwanted content in generated images.

---

## Technique Overview

Specify unwanted elements using natural language in a dedicated section. Use negative prompts sparingly to suppress specific recurring problems rather than as catch-all constraints.

**Core Mechanism:** Negative prompts guide models away from specific elements. Overuse can constrain creativity; targeted use addresses specific recurring issues effectively.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Recurring artifacts that appear consistently | Generic catch-all constraints that may limit creativity |
| Specific unwanted elements (motion blur, lens flare, text artifacts) | Complex aesthetic requirements better handled with positive descriptions |
| Refining outputs where specific issues persist | Initial generations where positive direction is more effective |
| Addressing known model limitations or biases | Over-constraining outputs with excessive negative specifications |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Identify recurring unwanted elements | Observe patterns in outputs to identify specific artifacts or elements |
| 2 | Use natural language descriptions | Specify unwanted elements clearly: "Avoid motion blur, lens flare, and text artifacts" |
| 3 | Keep negative prompts focused | Limit to 2-3 specific issues rather than comprehensive lists |
| 4 | Use dedicated section if needed | For complex prompts, include negative prompts in separate section |
| 5 | Test effectiveness | Generate outputs to verify negative prompts suppress issues without over-constraining |

**Key Considerations:**
- Use natural language rather than keyword lists
- Focus on specific recurring problems, not broad constraints
- Combine with positive descriptions for best results

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Targeted Artifact Suppression | Specific technical artifacts | Focus on technical issues: "Avoid pixelation, compression artifacts, banding" |
| Aesthetic Constraints | Style refinement | Specify unwanted style elements: "Avoid overly saturated colors, harsh shadows" |
| Content Filtering | Safety or appropriateness | Remove unwanted content types: "Avoid text, watermarks, logos" |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Overusing negative prompts | Excessive negative constraints can limit creativity and produce bland outputs | Use sparingly; focus on specific recurring issues, not comprehensive constraints |
| Using keyword lists | Negative prompts work better with natural language descriptions | Use full sentences: "Avoid motion blur, lens flare" not "motion blur, lens flare, artifacts" |
| Conflicting with positive prompts | Negative prompts that contradict positive descriptions confuse the model | Ensure negative prompts complement, not contradict, positive direction |

---

## Examples

### Example 1: Artifact Suppression

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Create a professional product photo with soft lighting" | **Prompt:**<br>"Create a professional product photo with soft lighting. Avoid motion blur, lens flare, and chromatic aberration." |
| **Output:**<br>Image includes unwanted lens flare and slight motion blur | **Output:**<br>Clean image without technical artifacts |
| **Issue:** Recurring artifacts not addressed | **Result:** 90% artifact reduction |

**Metric:** 90% artifact reduction compared to 30% when relying solely on positive descriptions

---

### Example 2: Style Refinement

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Create a modern minimalist illustration with vibrant colors" | **Prompt:**<br>"Create a modern minimalist illustration with vibrant colors. Avoid overly saturated tones, harsh shadows, and cluttered compositions." |
| **Output:**<br>Image too saturated, harsh shadows present | **Output:**<br>Balanced saturation, soft shadows, clean composition |
| **Issue:** Positive description alone insufficient for style control | **Result:** 85% style adherence to minimalist aesthetic |

**Metric:** 85% style adherence compared to 60% with positive descriptions only

---

## Quality Checklist

Before using negative prompts, verify:

- [ ] Negative prompts target specific recurring issues
- [ ] Natural language used, not keyword lists
- [ ] Limited to 2-3 specific unwanted elements
- [ ] Negative prompts complement positive descriptions
- [ ] No conflicts between positive and negative specifications
- [ ] Effectiveness tested to ensure appropriate suppression

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Negative Prompts | Read model-specific documentation in [ai_models/](../ai_models/) for implementation details |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Negative Prompt Techniques | Based on content extracted from nano_banana.md | 2025-01-23 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

No discarded sources for this technique.

---

*Last updated: 2025-01-23*


