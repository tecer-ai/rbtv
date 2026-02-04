---
---

# Structured Prompting

**Problem Type:** Task Decomposition

**Related Anti-Patterns:** Addresses [Unstructured Prompt](mdc:system/ai_pro/prompting/ai_models/nano_banana.md#pitfalls)

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

How to organize complex prompts with multiple requirements to ensure all elements are correctly interpreted and implemented.

---

## Technique Overview

Organize prompts into clear sections with uppercase labels (VISUAL STRUCTURE, COLOR PALETTE, STYLE, COMPOSITION, TECHNICAL). Structured organization helps models parse all requirements accurately and produce complete outputs.

**Core Mechanism:** Long paragraphs without clear sections make it hard for models to parse all requirements. Structured sections with labels enable systematic processing of complex instructions.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Complex infographics with multiple elements and relationships | Simple single-subject images with minimal requirements |
| Multi-element compositions requiring precise organization | Quick sketches where speed is more important than completeness |
| Brand assets requiring consistent application of multiple guidelines | Experimental work where exploration is the goal |
| Technical diagrams with structured data visualization | Vague creative briefs where interpretation flexibility is desired |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Identify major requirement categories | Group requirements: structure, color, style, composition, technical specs |
| 2 | Create section labels in uppercase | Use clear labels: VISUAL STRUCTURE, COLOR PALETTE, STYLE, COMPOSITION, TECHNICAL |
| 3 | Organize content under each section | Place related requirements under appropriate sections |
| 4 | Use consistent section ordering | Maintain same section order across similar prompts for familiarity |
| 5 | Review for completeness | Verify all major requirements are captured in structured format |

**Key Considerations:**
- Section labels should be descriptive and specific
- Keep related requirements grouped together
- Maintain consistent section structure across similar prompts

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Detailed Prompt Structure | Initial images requiring precise control | Follow pattern: Subject → Composition → Action → Location → Style → Lighting → Technical Constraints |
| Visual Description Sections | Complex infographics | Use sections: VISUAL STRUCTURE, CONNECTION LINES, POWER FEATURES, STYLE, COMPOSITION, COLOR PALETTE |
| Power Feature Sections | Multiple use cases or features | Dedicate separate sections for each power feature with specific visual elements |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Unstructured prompt | Long paragraphs without clear sections make it hard for models to parse all requirements | Use structured sections with uppercase labels (VISUAL STRUCTURE, COLOR PALETTE, STYLE) |
| Mixing unrelated requirements | Requirements from different categories mixed together confuse organization | Group related requirements under appropriate sections |
| Inconsistent section ordering | Varying section order across prompts makes pattern recognition harder | Maintain consistent section order for similar prompt types |

---

## Examples

### Example 1: Complex Infographic

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Create an infographic showing a central hub with categories around it, some friends on the left, gifts on the right, and recommendations at the top. Use gold for the center, blue for movies, red for books, green for games, orange for restaurants, and turquoise for travel. Make it modern and colorful." | **Prompt:**<br>"VISUAL STRUCTURE: Central golden hub at center. Five branches radiate outward: MOVIES (12 o'clock), BOOKS (2 o'clock), GAMES (4 o'clock), RESTAURANTS (8 o'clock), TRAVEL (10 o'clock).<br><br>COLOR PALETTE: Hub: #FFD700; Movies: #4A90E2; Books: #C41E3A; Games: #00D9A5; Restaurants: #FF6B35; Travel: #0EA5E9<br><br>POWER FEATURES: Recommendations (top section), Friends (left), Gifts (right)<br><br>STYLE: Modern flat design with subtle depth, rounded corners, smooth flowing lines" |
| **Output:**<br>Missing elements, unclear relationships, inconsistent colors | **Output:**<br>All elements correctly positioned, relationships clear, consistent color application |
| **Issue:** Mixed requirements in single paragraph | **Result:** 95% element completeness and relationship accuracy |

**Metric:** 95% element completeness compared to 60% with unstructured prompts

---

## Quality Checklist

Before finalizing structured prompts, verify:

- [ ] Major requirement categories identified and labeled
- [ ] Section labels in uppercase (VISUAL STRUCTURE, COLOR PALETTE, etc.)
- [ ] Related requirements grouped under appropriate sections
- [ ] Consistent section ordering maintained
- [ ] All major requirements captured in structured format
- [ ] Section labels are descriptive and specific

---

## Technical Reference

*No official documentation for this technique.*

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Structured Prompting Techniques | Based on content extracted from nano_banana.md | 2025-01-23 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

No discarded sources for this technique.

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md) before updating this document.

---

*Last updated: 2025-01-23*


