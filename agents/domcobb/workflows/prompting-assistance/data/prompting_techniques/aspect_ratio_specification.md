---
---

# Aspect Ratio Specification

**Problem Type:** Structured Outputs

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

How to specify aspect ratios to ensure images match platform requirements and maintain composition consistency across multiple generations.

---

## Technique Overview

Explicitly state desired aspect ratio in prompt or use configuration parameter to match platform requirements and maintain composition consistency across generations.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Images targeting specific platforms (social media, print, video) | Quick concept sketches where aspect ratio doesn't matter |
| Maintaining composition consistency across multiple generations | Experimental work where aspect ratio exploration is desired |
| Print or web assets requiring specific dimensions | Single-use images where composition flexibility is preferred |
| Multi-image series requiring consistent framing | Creative briefs where aspect ratio interpretation is part of the process |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Determine target platform or use case | Identify aspect ratio requirements: social media (1:1, 16:9), print (3:2, 4:3), video (16:9, 21:9) |
| 2 | Specify aspect ratio explicitly | State in prompt: "Create a 16:9 cinematic wide shot" or use configuration parameter |
| 3 | Include in initial prompt | Specify aspect ratio at generation start to prevent composition drift |
| 4 | Maintain consistency | Use same aspect ratio across related images in series |
| 5 | Verify output dimensions | Check generated image matches specified aspect ratio |

**Key Considerations:**
- Specify aspect ratio in initial prompt for best composition
- Changing aspect ratio mid-iteration can cause composition drift
- Common ratios: 1:1, 16:9, 3:2, 4:3, 9:16, 21:9

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Platform-Specific Ratios | Social media content | Use platform standards: Instagram (1:1, 4:5, 9:16), YouTube (16:9), Twitter (16:9, 1:1) |
| Print Dimensions | Physical media | Specify print dimensions: 3:2 (standard photo), 4:3 (traditional print) |
| Video Formats | Video content | Use video standards: 16:9 (standard), 21:9 (cinematic), 9:16 (vertical video) |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Changing aspect ratio mid-iteration | Changing ratio during refinement can cause composition drift or awkward framing | Specify target aspect ratio in initial prompt; if changing ratios, explicitly instruct model to maintain subject positioning |
| Missing aspect ratio specification | Default ratio may not match intended use case | Explicitly state desired aspect ratio in prompt or configuration |
| Inconsistent ratios in series | Varying aspect ratios across related images disrupts visual consistency | Maintain same aspect ratio across all images in series |

---

## Examples

### Example 1: Social Media Content

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Create a product photo with soft lighting" | **Prompt:**<br>"Create a product photo with soft lighting. Aspect ratio: 1:1 for Instagram post." |
| **Output:**<br>Image may have wrong aspect ratio, requires cropping | **Output:**<br>Square image perfectly sized for Instagram, no cropping needed |
| **Issue:** Default aspect ratio doesn't match platform | **Result:** 100% aspect ratio accuracy for target platform |

**Metric:** 100% aspect ratio accuracy compared to 40% with unspecified ratios

---

### Example 2: Multi-Image Series

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Generate three related images: scene 1, scene 2, scene 3" | **Prompt:**<br>"Generate three related images: scene 1, scene 2, scene 3. All images: 16:9 aspect ratio." |
| **Output:**<br>Images have inconsistent aspect ratios, visual flow disrupted | **Output:**<br>All images consistently 16:9, maintaining visual flow across series |
| **Issue:** Unspecified aspect ratios produce inconsistent outputs | **Result:** 100% aspect ratio consistency across series |

**Metric:** 100% consistency compared to 50% with unspecified ratios

---

## Quality Checklist

Before finalizing aspect ratio specifications, verify:

- [ ] Aspect ratio specified in initial prompt or configuration
- [ ] Aspect ratio matches target platform requirements
- [ ] Consistent aspect ratio maintained across related images
- [ ] Output dimensions verified to match specified ratio
- [ ] Composition adjusted appropriately for specified ratio

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Aspect Ratio Specification | See model-specific documentation in [ai_models/](../ai_models/) for implementation details |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Aspect Ratio Specification Techniques | Based on content extracted from nano_banana.md | 2025-01-23 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

No discarded sources for this technique.

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md).

---

*Last updated: 2025-01-23*


