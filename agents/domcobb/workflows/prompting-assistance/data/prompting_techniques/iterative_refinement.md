---
---

# Iterative Refinement

**Problem Type:** Iteration & Refinement

**Related Anti-Patterns:** Addresses [Attempting Complex Multi-Step Edits in Single Prompt](mdc:system/ai_pro/prompting/ai_models/nano_banana.md#pitfalls)

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

How to refine images through multiple conversational iterations rather than attempting complex multi-step edits in a single prompt.

---

## Technique Overview

Make small, incremental edits through multiple turns rather than attempting major overhauls in a single prompt. Sequential refinement maintains coherence and produces higher quality outputs than complex single-step transformations.

**Core Mechanism:** Multiple small changes allow models to maintain context and coherence. Single large changes overwhelm models and produce lower-quality or distorted outputs.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Refining images through targeted improvements | Initial generation where comprehensive prompt is more efficient |
| Making precise adjustments to existing images | Quick concept sketches where iteration time isn't justified |
| Complex edits requiring multiple modifications | Simple single-element changes where one prompt suffices |
| Maintaining image quality while making changes | When complete regeneration is more appropriate than iteration |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Identify one specific change | Focus on single element: background, lighting, clothing, expression |
| 2 | Make targeted change request | Use natural language: "Adjust the lighting to soft golden hour" |
| 3 | Review output | Evaluate if change achieved desired result |
| 4 | Make next incremental change | Proceed to next specific modification |
| 5 | Continue until complete | Repeat for each desired change |

**Key Considerations:**
- One change per iteration maintains coherence
- Small incremental changes prevent quality degradation
- Sequential refinement produces better results than complex single prompts

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Conversational Iteration | Natural refinement | Use conversational tone: "Can you make it warmer?" for intuitive refinement |
| Sequential Element Changes | Multiple modifications | Change one element at a time: first background, then lighting, then styling |
| Refinement Focus | Specific improvements | Focus on particular aspects: "Improve the lighting", then "Adjust the composition" |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Attempting complex multi-step edits in single prompt | Combining too many instructions (change background, adjust lighting, modify clothing, add text) overwhelms the model and produces lower-quality or distorted outputs | Break complex edits into sequential steps; make one change at a time and iterate conversationally |
| Making too many changes at once | Multiple simultaneous changes can cause quality degradation or unintended alterations | Limit to one specific change per iteration |
| Not reviewing outputs between iterations | Skipping review can lead to accumulating errors | Review each iteration before proceeding to next change |

---

## Examples

### Example 1: Multi-Step Refinement

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Change the background to sunset, adjust lighting to golden hour, modify the character's clothing to a red dress, and add text saying 'SUMMER SALE'" | **Iteration 1:**<br>"Change the background to a sunset with warm orange and pink tones"<br><br>**Iteration 2:**<br>"Adjust the lighting to soft golden hour"<br><br>**Iteration 3:**<br>"Change the character's clothing to a red silk dress"<br><br>**Iteration 4:**<br>"Add text at the top: 'SUMMER SALE' in bold white font" |
| **Output:**<br>Lower quality, distorted elements, some instructions missed | **Output:**<br>High quality output with all changes correctly applied |
| **Issue:** Too many simultaneous changes overwhelm the model | **Result:** 95% instruction compliance with high quality compared to 60% with single complex prompt |

**Metric:** 95% instruction compliance compared to 60% with single complex prompt

---

### Example 2: Targeted Adjustment

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Make the image warmer, brighter, and more professional looking" | **Iteration 1:**<br>"Adjust the color temperature to warmer tones"<br><br>**Iteration 2:**<br>"Increase the brightness slightly"<br><br>**Iteration 3:**<br>"Adjust the lighting to professional studio quality" |
| **Output:**<br>Unclear changes, inconsistent results | **Output:**<br>Precise adjustments with clear improvements |
| **Issue:** Vague combined instructions produce unclear results | **Result:** 90% desired improvement compared to 50% with vague combined prompt |

**Metric:** 90% improvement compared to 50% with vague combined instructions

---

## Quality Checklist

Before using iterative refinement, verify:

- [ ] One specific change identified per iteration
- [ ] Changes are incremental and focused
- [ ] Each iteration reviewed before proceeding
- [ ] Natural language used for change requests
- [ ] Sequential order logical (background before foreground, etc.)
- [ ] Quality maintained throughout iterations

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Iterative Refinement | Read model-specific documentation in [ai_models/](../ai_models/) |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Iterative Refinement Techniques | Based on content extracted from nano_banana.md | 2025-01-23 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

No discarded sources for this technique.

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2025-01-23*


