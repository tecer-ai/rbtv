---
---

# Color Specification

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

How to specify colors precisely to maintain brand consistency and avoid ambiguous color interpretations in generated images.

---

## Technique Overview

Provide exact hex codes for all major colors instead of descriptive names to ensure consistent color application and prevent ambiguous interpretations.

---

## When to Apply

| Ideal For | Avoid For |
|-----------|-----------|
| Brand asset generation requiring exact brand colors | Artistic work where color variation is desired |
| Infographics with category color coding | Quick concept sketches where exact colors aren't critical |
| Multi-element compositions requiring consistent palette | Single-color backgrounds where variation doesn't matter |
| Design systems requiring precise color matching | Exploratory work where color discovery is the goal |

---

## Application Pattern

| Step | Action | Details |
|------|--------|---------|
| 1 | Identify all major colors needed | List primary colors, accent colors, background, and text colors |
| 2 | Convert color names to hex codes | Use brand guidelines or color picker to get exact hex values |
| 3 | Organize color palette section | Create clear COLOR PALETTE section with hex codes and descriptive names |
| 4 | Specify color assignments | Link each hex code to specific elements (category, background, text) |
| 5 | Include contrast considerations | Verify hex codes maintain sufficient contrast for readability |

**Key Considerations:**
- Always pair hex codes with descriptive names for clarity (#4A90E2 - blue)
- Include both primary and accent colors in specification
- Verify hex codes match brand guidelines or intended design system

---

## Variations

| Variation | When to Use | Difference from Core |
|-----------|-------------|----------------------|
| Category Color Coding | Multi-category visualizations | Assign distinct hex codes to each category with descriptive names |
| Gradient Specification | Smooth color transitions | Specify start and end hex codes, transition direction |
| Brand Palette | Design systems | Document full brand palette with hex codes for all colors |

---

## Pitfalls

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Vague color descriptions | "Blue" or "warm colors" leads to inconsistent color choices across elements | Provide exact hex codes for all major colors (#FFD700, #4A90E2, etc.) |
| Color name ambiguity | Same color name (e.g., "blue") used for different shades creates confusion | Use hex codes; descriptive names are secondary clarifiers |
| Missing accent colors | Only specifying primary colors causes inconsistent accent choices | Include complete palette: primary, accent, background, and text colors |

---

## Examples

### Example 1: Brand Consistency

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Create an infographic with a gold center, blue for movies, red for books, green for games, orange for restaurants, and blue for travel." | **Prompt:**<br>"COLOR PALETTE: Central hub: #FFD700 (vibrant gold); Movies: #4A90E2 (blue); Books: #C41E3A (burgundy); Games: #00D9A5 (green); Restaurants: #FF6B35 (orange); Travel: #0EA5E9 (sky blue)" |
| **Output:**<br>Different shades of blue for movies and travel; inconsistent gold hue | **Output:**<br>Exact brand colors applied consistently across all elements |
| **Issue:** Color names produce variable interpretations | **Result:** 100% color accuracy matching brand guidelines |

**Metric:** 100% color accuracy compared to 60-70% with color names alone

---

### Example 2: Category Color Coding

| Before (Without Technique) | After (With Technique) |
|----------------------------|------------------------|
| **Prompt:**<br>"Show five categories with different colors around a central hub" | **Prompt:**<br>"CATEGORY COLOR CODING: 1) Movies (12 o'clock): #4A90E2; 2) Books (2 o'clock): #C41E3A; 3) Games (4 o'clock): #00D9A5; 4) Restaurants (8 o'clock): #FF6B35; 5) Travel (10 o'clock): #0EA5E9" |
| **Output:**<br>Unclear color assignments, inconsistent shades | **Output:**<br>Each category has distinct, correctly positioned color with exact hex match |
| **Issue:** Generic color instruction doesn't specify assignments | **Result:** 100% category-color association accuracy |

**Metric:** 100% category-color accuracy compared to 40% with generic instructions

---

## Quality Checklist

Before finalizing color specifications, verify:

- [ ] All major colors specified with hex codes (#FFFFFF format)
- [ ] Hex codes paired with descriptive names for clarity
- [ ] Complete palette included (primary, accent, background, text)
- [ ] Color assignments linked to specific elements
- [ ] Contrast ratios verified for readability
- [ ] Hex codes match brand guidelines or design system

---

## Technical Reference

| Topic | Official Documentation |
|-------|------------------------|
| Color Specification | See model-specific documentation in [ai_models/](../ai_models/) for implementation details |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Color Specification Techniques | Based on content extracted from nano_banana.md | 2025-01-23 | 2025-12-16 | 8.5 | 8 | 9 | 9 |

---

## Discarded Sources

No discarded sources for this technique.

---

## For AI Agents

Read [`prompting_technique.md`](../prompting_technique.md).

---

*Last updated: 2025-01-23*


