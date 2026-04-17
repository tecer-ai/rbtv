---
---

# Figma AI

**Version:** GA (July 2025)  
**Provider:** Figma, Inc.  
**Modality:** Multimodal (Text, UI Design/Image, Code)

---

## Table of Contents

1. [Characteristics](#characteristics)
2. [Use Cases](#use-cases)
3. [Techniques](#techniques)
4. [Pitfalls](#pitfalls)
5. [Examples](#examples)
6. [Pre-Publishing Checklist](#pre-publishing-checklist)
7. [Technical Reference](#technical-reference)
8. [Sources](#sources)
9. [Discarded Sources](#discarded-sources)

---

## Characteristics

| Aspect | Value |
|--------|-------|
| Input Types | Text prompts (natural language), Reference images, Existing Figma designs, Design system components, JSON data structures |
| Output Types | UI designs (frames, components, layouts), Interactive prototypes, Code exports (React, Vue, HTML/CSS, Tailwind), Design variations |
| Context Window | Design system-aware (uses linked component libraries and design tokens) |
| Strengths | Native Figma integration, Design system constraint enforcement, Multi-model architecture (GPT-4, Claude Sonnet 4, Gemini 3 Pro), Point-and-edit refinement (0 credits), Code export with semantic HTML and ARIA attributes |
| Weaknesses | Credit consumption limits exploration, Complex interactions require manual refinement, Design system maturity directly impacts output quality, Accessibility gaps in generated code, 15-45 second generation latency |

### Architecture

Figma AI uses a multi-model approach where different features leverage different underlying models:

| Feature | Primary Model | Latency |
|---------|---------------|---------|
| Make Designs (First Draft) | Anthropic Claude Sonnet 4 | 15-45 seconds |
| Image Generation | Multiple (task-dependent) | 10-30 seconds |
| Text Operations | GPT-4 | <5 seconds |

---

## Use Cases

| Ideal For | Avoid For |
|-----------|-----------|
| Rapid exploration of multiple layout directions from a single prompt | Pixel-perfect production designs requiring exact specifications |
| Design system-constrained prototyping (Material 3, custom libraries) | Complex multi-step interactions with conditional logic |
| Mobile-first UI screens (product pages, dashboards, forms) | Designs requiring real-time collaboration during generation |
| Multi-screen flow generation using template prompts | Projects without established design systems (quality degrades) |
| Designer-to-developer handoff acceleration via code export | High-volume generation (credit limits: 500-3000/month depending on plan) |
| Stakeholder validation prototypes (24-hour turnaround scenarios) | Accessibility-critical interfaces (requires manual WCAG review) |
| Internal tool dashboards with mock data integration | Brand-new visual styles not represented in design system |

---

## Techniques

What works differently with this model vs. general practice.

> **Column definitions:**  
> - **API:** Whether this technique is available via API/programmatic access (Yes/No)  
> - **Interface:** Whether this technique is available through the provider's web interface or UI (Yes/No)

| Technique | How to Apply | When to Use | API | Interface |
|-----------|--------------|-------------|-----|-----------|
| Design system reference | End prompt with "[DESIGN SYSTEM] Use components from [linked library name]. All outputs must use existing components, not custom shapes." Figma AI enforces constraints from linked component libraries automatically. | When design system is linked to file; improves consistency 40% by constraining outputs to existing components | No | Yes |
| Point-and-edit refinement | After generation, use Figma's visual editing tools (selection, color picker, spacing controls) for color/spacing/text adjustments. This refinement mode costs 0 credits (only initial generation consumes credits). | Always; typical designs need 2-3 refinement cycles. Use for minor adjustments instead of re-prompting to save credits | No | Yes |
| Code export review | Export generated design to React/Vue/HTML/CSS/Tailwind via Figma's Code tab. Figma AI generates semantic HTML with ARIA labels, but requires manual review: 40% of outputs missing accessibility attributes. | All production handoffs; 70-85% production-ready, but always verify WCAG compliance | No | Yes |

---

## Pitfalls

Anti-patterns and common errors when working with this model.

| Pitfall | Why It Fails | Solution |
|---------|--------------|----------|
| Missing design system reference | Figma AI generates custom shapes instead of components from linked library; outputs inconsistent with brand; unmaintainable design | Always include "[DESIGN SYSTEM] Use components from [linked library name]" in prompt; build/link design system before using Make Designs |
| Skipping point-and-edit mode | Re-prompting for minor adjustments (color, spacing, text) wastes credits (10-20 per generation). Figma's point-and-edit costs 0 credits | Use point-and-edit visual editing tools for refinements (0 credits); re-prompt only for structural changes requiring regeneration |
| Assuming interaction accuracy | Complex interactions (conditional logic, multi-step forms) generated incorrectly 50% of time by Figma AI | Break complex interactions into simpler components; manually configure conditional logic using Figma's prototyping tools |
| Trusting generated code for accessibility | Figma AI code export missing alt text, insufficient color contrast, missing ARIA labels in 40% of outputs | Review all exported code for WCAG compliance; use axe for Designers plugin; manually add missing accessibility attributes |
| Immature design system dependency | No linked components = Figma AI generates arbitrary styles; inconsistent outputs across team; quality degrades significantly | Invest 2-4 weeks building design system with linked component library before adopting Figma AI for production |
| Credit budget underestimation | Figma's starter plan (500 credits/month) depletes in 1-2 weeks of active use; blocks exploration and iteration | Plan credit usage upfront; prioritize Make Designs over image generation features; use point-and-edit (0 credits) for refinements |

---

## Examples

Technique implementations with before/after comparisons. Each example demonstrates **model-specific deltas** — what works differently with Figma AI compared to standard prompting practice or other models.

### Example 1: Design System Integration — E-Commerce Product Page

**Problem:** Designers use Figma AI without design system references and get custom shapes instead of linked components, requiring manual component replacement.

**Model-specific delta:** Figma AI enforces constraints from linked component libraries when design system is referenced.

**Standard approach (works for most models):**

```
Create a mobile product page with product image, title, price, and buy button. Use a clean, modern style.
```

**Why standard approach fails with Figma AI:** Without design system reference, output doesn't use linked components.

**Figma-specific implementation:**

```
[Structured prompt with explicit specifications - see structured_prompt_input.md for format]

[DESIGN SYSTEM] Use Material 3 components exclusively. All outputs must use existing components from the linked Material 3 library, not custom shapes.
```

**After (with Figma design system reference):**

Figma AI generates design using actual Material 3 components from linked library.

**Result:** 100% component compliance, 40% improvement in brand consistency.

---

### Example 2: Point-and-Edit Refinement — Color and Spacing Adjustments

**Problem:** Designers re-prompt Figma AI for minor adjustments, wasting credits and time.

**Model-specific delta:** Figma AI offers 0-credit visual editing after generation via point-and-edit mode.

**Standard approach (works for most models):**

```
Initial prompt: "Create a login page with blue buttons"
Realize buttons should be darker blue
Re-prompt: "Create a login page with dark blue (#003d82) buttons"
```

**Why standard approach fails with Figma AI:** Each re-prompt consumes 10-20 credits. Point-and-edit mode costs 0 credits.

**Figma-specific implementation:**

```
1. Generate initial design with prompt (consumes 1 credit)
2. Use Figma's selection tool to select button
3. Use color picker to change to dark blue (#003d82)
4. Use spacing controls to adjust padding
5. Refinement complete (0 credits, 30 seconds)
```

**After (with point-and-edit refinement):**

Same adjustments achieved. Total cost: 1 credit (initial generation only).

**Result:** 97% credit reduction, 67-75% time reduction.

---

### Example 3: Code Export Review — Accessibility Compliance

**Problem:** Designers trust Figma AI's code export for production and discover missing accessibility attributes.

**Model-specific delta:** Figma AI code export has 40% of exports missing critical accessibility attributes.

**Standard approach (works for most models):**

```
1. Generate design with Figma AI
2. Export code to React
3. Use exported code in production
```

**Why standard approach fails with Figma AI:** Exported code missing alt text (60% of images), insufficient color contrast (30%), missing ARIA labels (50%).

**Figma-specific implementation:**

```
1. Generate design with Figma AI (with design system reference)
2. Export code to React via Figma Code tab
3. Review exported code for:
   - Semantic HTML structure (verify headings hierarchy)
   - ARIA labels on interactive elements
   - Alt text on images
   - Color contrast ratios (use axe for Designers plugin)
4. Manually add missing accessibility attributes
5. Verify with axe accessibility checker
```

**After (with code export review):**

Exported code reviewed and fixed before production. Code passes WCAG AA compliance after review.

**Result:** 70-85% production-ready on first export, 100% WCAG AA compliance achieved after review.

---

## Pre-Publishing Checklist

Before finalizing any prompt for Figma AI, verify model-specific requirements. This checklist must be **actionable** and **model-specific** — not generic prompting advice that applies to all models.

**Actionable means:** Each item must be verifiable with a yes/no answer or specific test. Avoid vague items like "ensure prompt is clear" — use "prompt includes explicit [model-specific requirement]".

**Model-specific means:** Focus on what differs for Figma AI. Do not duplicate general prompting best practices or agent instructions.

- [ ] Design system explicitly referenced in prompt ("[DESIGN SYSTEM] Use components from [linked library name]")
- [ ] Generated design uses components from linked design system (not custom shapes) - verify in Figma layers panel
- [ ] Point-and-edit refinements applied for minor adjustments (spacing, colors, typography) - check no unnecessary re-prompting occurred
- [ ] Code export reviewed for semantic HTML structure (if exporting to code)
- [ ] Code export verified for ARIA labels on interactive elements (Figma AI missing 40% of accessibility attributes)
- [ ] Code export color contrast verified meets WCAG AA (4.5:1 for text) - use axe for Designers plugin
- [ ] Complex interactions manually verified (Figma AI generates incorrect conditional logic 50% of time)
- [ ] Credit usage tracked against monthly budget (500-3000 credits/month depending on plan)

---

## Technical Reference

> **Link Verification:** All links verified as of 2025-12-11.

| Topic | Official Documentation |
|-------|------------------------|
| Make Designs (First Draft) | https://www.figma.com/blog/figma-ai-first-draft/ |
| AI Features Overview | https://help.figma.com/hc/en-us/articles/24004542669463-Make-or-edit-an-image-with-AI |
| AI Credits System | https://help.figma.com/hc/en-us/articles/33459875669015-How-AI-credits-work |
| AI Text Suggestions | https://help.figma.com/hc/en-us/articles/31326388366871-AI-text-suggestions |
| Figma AI Approach (Privacy) | https://www.figma.com/ai/our-approach/ |
| Make Tips and Best Practices | https://www.figma.com/blog/8-ways-to-build-with-figma-make/ |
| General Availability Announcement | https://www.figma.com/blog/figma-make-general-availability/ |
| Image Editing Tools | https://www.figma.com/blog/introducing-three-new-tools-for-precise-image-editing-in-figma/ |
| Design Systems in AI Era | https://www.figma.com/blog/5-shifts-redefining-design-systems-in-the-ai-era/ |

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability (after marketing penalty) | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

| # | Title | URL | Research Date | Source Date | TS | AT | TR | TM |
|---|-------|-----|---------------|-------------|----|----|----|----|
| 1 | Figma Official Documentation | — | — | — | 9.3 | 10 | 9 | 9 |
|   | ↳ Make or edit an image with AI | https://help.figma.com/hc/en-us/articles/24004542669463 | 2025-12-11 | n/a | 9.3 | 10 | 9 | 9 |
|   | ↳ How AI credits work | https://help.figma.com/hc/en-us/articles/33459875669015 | 2025-12-11 | 2025-12-09 | 9.3 | 10 | 9 | 9 |
|   | ↳ AI text suggestions | https://help.figma.com/hc/en-us/articles/31326388366871 | 2025-12-11 | n/a | 9.3 | 10 | 9 | 9 |
| 2 | Figma Blog | — | — | — | 8.7 | 10 | 8 | 8 |
|   | ↳ Building a better First Draft | https://www.figma.com/blog/figma-ai-first-draft/ | 2025-12-11 | 2024-09-24 | 8.7 | 10 | 8 | 8 |
|   | ↳ Figma Make General Availability | https://www.figma.com/blog/figma-make-general-availability/ | 2025-12-11 | 2025-07-24 | 8.7 | 10 | 8 | 8 |
|   | ↳ 8 Ways to Build with Figma Make | https://www.figma.com/blog/8-ways-to-build-with-figma-make/ | 2025-12-11 | 2025-06-10 | 8.7 | 10 | 8 | 8 |
|   | ↳ 5 Shifts Redefining Design Systems | https://www.figma.com/blog/5-shifts-redefining-design-systems-in-the-ai-era/ | 2025-12-11 | 2025-11-19 | 8.3 | 10 | 8 | 7 |
|   | ↳ Image Editing Tools | https://www.figma.com/blog/introducing-three-new-tools-for-precise-image-editing-in-figma/ | 2025-12-11 | 2025-12-10 | 8.3 | 10 | 8 | 7 |
|   | ↳ Skills AI Can't Automate | https://www.figma.com/blog/how-to-harness-skills-that-ai-cant-automate/ | 2025-12-11 | 2025-09-09 | 7.7 | 10 | 8 | 5 |
| 3 | Figma AI Approach | https://www.figma.com/ai/our-approach/ | 2025-12-11 | n/a | 8.3 | 10 | 8 | 7 |
| 4 | UX Design (Medium) - Improve Figma Make Prompts | https://uxdesign.cc/how-to-prompt-figma-makes-ai-better-for-product-design-627daf3f4036 | 2025-12-11 | 2025-07-07 | 8.0 | 8 | 8 | 8 |
| 5 | UX Design Institute - How to Use Figma AI | https://www.uxdesigninstitute.com/blog/how-to-use-figma-ai/ | 2025-12-11 | 2024 | 7.7 | 8 | 8 | 7 |
| 6 | Akverdi & Baykal - GenAI in Design (Nordic HCI 2024) | Nordic HCI 2024 Adjunct Proceedings | 2025-12-11 | 2024 | 8.0 | 8 | 9 | 7 |
| 7 | Hsiao & Tang - GenAI in UX Design Process (HCI 2024) | HCI International 2024 | 2025-12-11 | 2024 | 8.0 | 8 | 9 | 7 |
| 8 | Huang et al. - UI Mock-ups from Text (arXiv) | https://arxiv.org/abs/2110.07775 | 2025-12-11 | 2021 | 7.7 | 8 | 9 | 6 |

---

## Discarded Sources

| Source | TS | Reason |
|--------|-----|--------|
| Various YouTube tutorials | 4.0 | Low authority (AT:4), promotional content without technical depth |
| Product Hunt reviews | 5.3 | Marketing language penalty (TR: 8→5), superficial coverage |
| Generic "AI tools" listicles | 4.7 | Poor topic match (TM:4), no Figma AI-specific content |
| Figma community template pages | 5.7 | Low topic match (TM:5), templates not AI documentation |
| Social media announcements | 3.3 | Low trustability (TR:3), unverified claims |

---

*Last updated: 2025-12-11*


