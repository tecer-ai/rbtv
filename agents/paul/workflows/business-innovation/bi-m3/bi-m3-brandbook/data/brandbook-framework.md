# Brandbook Framework

**Purpose:** Synthesize all M3 brand framework outputs into a single, comprehensive brandbook document that serves as the canonical reference for brand representation across all touchpoints.

---

## Framework Overview

A brandbook (brand guide / style guide) consolidates brand identity, visual guidelines, and messaging into one authoritative document. It is the manual that ensures every team member, partner, and external collaborator represents the brand consistently.

This framework differs from the other 6 M3 frameworks: it does not discover new brand elements. It **compiles, extends, and operationalizes** the outputs of Brand Archetypes, Brand Prism, Golden Circle, Brand Positioning, Messaging Architecture, and Tone of Voice into a production-ready reference document — adding visual identity specifications (logo, color palette, typography, imagery, iconography) that the earlier frameworks defined conceptually but never materialized.

---

## Brandbook Structure

### Section 1: Brand Identity

Compiled from existing M3 frameworks:

| Element | Source |
|---------|--------|
| Mission Statement | Golden Circle (Why) |
| Vision Statement | Golden Circle (What — aspirational future) |
| Brand Persona | Brand Archetypes (primary archetype, IS/NOT traits) + Brand Prism (personality facet) |
| Target Audience | M1 JTBD (buyer personas, jobs, emotional drivers) + Lean Canvas (customer segments) |
| Brand Values | Brand Prism (culture facet) + Golden Circle (How) |
| Brand Story | Working Backwards (PR narrative) + Golden Circle (Why/How/What arc) |

### Section 2: Visual Guidelines

Created fresh in this framework with founder collaboration:

| Element | Description |
|---------|-------------|
| **Logo** | Primary, secondary, monochromatic variations. Clear space rules. Do's/don'ts. Generated via AI image prompts. |
| **Color Palette** | Primary colors (1-3), secondary colors (2-4), accent colors. HEX, RGB, CMYK values. Usage guidelines. |
| **Typography** | Primary typeface (headings), secondary typeface (body). Hierarchy: H1-H3, body, caption with sizes, weights, line heights. |
| **Imagery & Photography** | Photographic style (subject matter, composition, lighting, color treatment). Do's/don'ts. Generated via AI image prompts for reference examples. |
| **Iconography** | Icon style (line weight, fill, corner style, detail level). Usage rules. Do's/don'ts. |

### Section 3: Messaging & Tone

Compiled from existing M3 frameworks:

| Element | Source |
|---------|--------|
| Brand Voice | Tone of Voice (dimensions, voice summary) |
| Tone Guidelines | Tone of Voice (do/don't examples, context adjustments) |
| Tagline | New — crafted from Brand Promise (Messaging Architecture) |
| Value Proposition | Lean Canvas UVP + Brand Positioning statement |
| Key Messaging | Messaging Architecture (brand promise, key messages per audience) |

### Section 4: Quick Reference Sheet

One-page summary containing:
- Primary + secondary logo thumbnails (file references)
- Color palette with HEX codes
- Primary + secondary typefaces
- Brand voice summary (2-3 sentences)
- Tagline
- Core do's/don'ts

---

## AI Image Generation Integration

This framework generates images (logos, imagery examples) through AI image generation tools. The process:

1. **Ask** the founder which AI image generation tool they prefer
2. **Record** the preference in project-memo.md
3. **Load** model/platform knowledge from DomCobb's prompting knowledge index at `{rbtv_path}/agents/domcobb/agents/domcobb/workflows/prompting-assistance/data/knowledge-index.csv`
4. **Generate prompts** optimized for the selected model/platform, incorporating brand context (archetype, colors, personality, positioning)
5. **Present prompts** to the founder for generation in their preferred tool
6. **Instruct** the founder where to save generated images
7. **Iterate** until the founder approves each image
8. **Continue** workflow once images are saved

### Image Assets to Generate

| Asset | Count | Purpose |
|-------|-------|---------|
| Primary logo | 1+ variations | Main brand mark |
| Secondary logo | 1+ variations | Simplified version (logomark, stacked) |
| Monochromatic logo | 1-2 | Single-color for colored/busy backgrounds |
| Brand imagery examples | 2-3 | Reference photographs showing approved style |
| Icon style examples | 1-2 | Reference showing approved icon aesthetic |

### Prompt Requirements

Each image prompt must include:
- Brand context (archetype personality, color palette, positioning category)
- Specific style direction (derived from Brand Prism physique facet)
- Negative prompts (what to avoid)
- Technical specifications (dimensions, format, background)
- Filename for saving

---

## Color Specification Standards

All colors must be specified in multiple formats:

| Format | Use Case |
|--------|----------|
| HEX | Web, digital design |
| RGB | Screen displays |
| CMYK | Print materials |
| Pantone | Professional printing (optional, recommend closest match) |

---

## Typography Specification Standards

| Specification | Required |
|---------------|----------|
| Typeface name | Yes |
| Weight/style variants | Yes (Regular, Bold, Italic at minimum) |
| Use cases | Yes (headings, body, captions, CTAs) |
| Size hierarchy | Yes (px or pt for each heading level, body, caption) |
| Line height | Yes (ratio for each use case) |
| Letter spacing | Optional |
| Maximum line length | Recommended (45-75 characters) |
| Web fallback | Recommended (system font stack) |
| Accessibility | Required (minimum contrast ratio, legibility notes) |

---

## Do's and Don'ts Pattern

Every visual element section must include explicit do's and don'ts:

**Logo Do's/Don'ts Example:**
- DO: Use primary logo when space allows
- DO: Maintain minimum clear space
- DO: Use monochromatic on colored backgrounds
- DON'T: Stretch or distort proportions
- DON'T: Change brand colors
- DON'T: Place on busy/illegible backgrounds
- DON'T: Add effects (shadows, glows, outlines)

Apply this pattern to: Logo, Color Palette, Typography, Imagery, Iconography.

---

## Prerequisites

**ALL 6 M3 frameworks must be completed:**
- Brand Archetypes (`bi-m3-brand-archetypes`)
- Brand Prism (`bi-m3-brand-prism`)
- Golden Circle (`bi-m3-golden-circle`)
- Brand Positioning (`bi-m3-brand-positioning`)
- Messaging Architecture (`bi-m3-messaging-architecture`)
- Tone of Voice (`bi-m3-tone-of-voice`)

**Also required:**
- M1 frameworks (Working Backwards, JTBD, Lean Canvas)
- M2 frameworks (3+ completed)

---

## Success Criteria

Brandbook is complete when:

- [ ] Brand Identity section compiled from all 6 M3 frameworks
- [ ] Color palette defined with HEX, RGB, CMYK values and usage guidelines
- [ ] Typography hierarchy defined with typefaces, sizes, weights, line heights
- [ ] Logo variations generated, approved by founder, and saved with clear space/usage rules
- [ ] Imagery guidelines defined with approved reference examples
- [ ] Iconography style defined with usage rules
- [ ] Messaging & Tone section compiled from Messaging Architecture + Tone of Voice
- [ ] Tagline crafted from Brand Promise
- [ ] Quick Reference Sheet generated as one-page summary
- [ ] All do's/don'ts defined for every visual element
- [ ] project-memo.md updated with Brandbook synthesis
- [ ] M3 Brand marked as COMPLETE
