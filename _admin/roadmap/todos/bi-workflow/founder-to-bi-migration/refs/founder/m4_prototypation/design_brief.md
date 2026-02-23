---
---

# Template Instructions: design_brief

**Purpose:** Create a `design_brief.md` for each project that captures the subjective, narrative design direction — visual identity, brand tone, imagery style, and creative interpretation. This file contains **no code, no concrete values, no component specifications**. Optimized for creative consultation with lavoisier agent.

> **Companion File:** Read `design.json`

---

## Table of Contents

### Template Instructions

- [Design Principles](#design-principles)
- [What Belongs Here vs design.json](#what-belongs-here-vs-designjson)
- [Section Guidelines](#section-guidelines)
- [How to Use This Template](#how-to-use-this-template)

### Document Content

- [Design Brief: [Project Name]](#design-brief-project-name)

---

## Design Principles

| Principle | Instruction |
|----------|-------------|
| Narrative only | Pure creative interpretation; no code snippets, no concrete values (colors/fonts), no implementation details |
| Subjective nuances | Capture what only a creative director can articulate after visual analysis |
| Brand essence | Focus on feeling, tone, archetype, atmosphere — not technical specifications |
| Inspiration-driven | Created through iterative discovery with lavoisier agent (Playwright visual analysis) |
| Complementary to schema | Works with design.json (structure/tokens) and project-specific design-[artifact].json files |

---

## What Belongs Here vs design.json

| Content Type | design_brief.md | design.json |
|---|---|---|
| Visual identity narrative | ✅ Yes | ❌ No |
| Brand direction & tone | ✅ Yes | ❌ No |
| Imagery style guidance | ✅ Yes | ❌ No |
| Creative interpretation | ✅ Yes | ❌ No |
| Feeling & atmosphere | ✅ Yes | ❌ No |
| Token definitions (schema) | ❌ No | ✅ Yes |
| Component structure | ❌ No | ✅ Yes |
| Layout specifications | ❌ No | ✅ Yes |
| Concrete color/font values | ❌ No | ❌ No |

**Decision rule:** Narrative prose describing subjective qualities belongs in design_brief.md. Structure, schema, or implementation belongs in design.json.

---

## Section Guidelines

| Section | Required | Notes |
|---------|----------|-------|
| Visual Identity Overview | Required | High-level brand essence; archetype; visual personality |
| Brand Direction | Required | Strategic positioning; differentiation; emotional goals |
| Tone & Atmosphere | Required | How the brand should feel; emotional resonance; energy level |
| Typography Philosophy | Required | Type personality (not specific fonts); hierarchy approach; readability priorities |
| Color Philosophy | Required | Color psychology; palette mood; contrast approach (not hex values) |
| Imagery Style | Required | Photography style, illustration approach, iconography personality |
| Layout Philosophy | Required | Spatial rhythm, density preferences, grid personality |
| Motion & Interaction Feel | Recommended | Animation personality, transition style, interaction feedback philosophy |
| Material & Texture | Recommended | Surface quality, depth approach, tactile qualities |
| Creative Interpretation Notes | Required | Lavoisier's subjective observations from visual analysis; nuances that inform implementation |
| Inspiration References | Recommended | URLs to inspiration sources analyzed via Playwright; key takeaways from each |
| Do / Don't (Creative) | Recommended | Qualitative guardrails (e.g., "Do: Embrace whitespace" not "Do: Use 24px padding") |
| Last Updated | Required | Footer date in `YYYY-MM-DD` |

---

## How to Use This Template

1. Invoke lavoisier agent
2. Lavoisier creates design_brief.md + design.json as paired outputs
3. Project file MUST be at `[project]/docs/product/design_brief.md` or `[project]/docs/founder/design_brief.md`

**Critical:** NEVER copy template skeleton. ALWAYS create through creative consultation.

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# Design Brief: [Project Name]

**Created through creative discovery with lavoisier agent.**

> **Companion Files:** Read `design.json` and `design-[artifact_type].json`

---

## For AI Agents

**Template reference:** This document was created from [`design_brief.md`](../../../system/founder/m4_prototypation/design_brief.md). Agents MUST read the template before making updates.

---

## Visual Identity Overview

### Brand Archetype

[Describe the brand archetype. Examples: "Trusted advisor with quiet confidence," "Bold innovator with playful edge," "Timeless craftsperson with meticulous care."]

### Visual Personality

[Describe the visual personality in narrative form. What does this brand look/feel like? What similar brands or design languages inspire it?]

---

## Brand Direction

### Strategic Positioning

[How should this brand be perceived relative to competitors? What space does it own?]

### Differentiation

[What makes this brand's visual language distinctive? What visual cues set it apart?]

### Emotional Goals

[What should users/viewers feel when encountering this brand? Examples: "Inspired and capable," "Reassured and understood," "Excited and curious."]

---

## Tone & Atmosphere

### Overall Feel

[Describe the atmosphere. Examples: "Calm and spacious," "Energetic and dense," "Warm and approachable," "Cool and professional."]

### Energy Level

[Is this brand quiet or loud? Restrained or expressive? Minimal or abundant?]

### Cultural References

[Any cultural, artistic, or design movement references that inform the tone? Examples: "Swiss modernism," "Japanese minimalism," "American optimism."]

---

## Typography Philosophy

### Type Personality

[Describe the personality of type usage. Examples: "Confident and geometric," "Warm and humanist," "Technical and precise," "Elegant and refined."]

### Hierarchy Approach

[How should hierarchy be expressed? Examples: "Bold contrast between levels," "Subtle modulation with spacing," "Scale-driven with consistent weight."]

### Readability Priorities

[What matters most for legibility and reading experience? Examples: "Generous line-height for calm reading," "Tight tracking for impact," "Clear distinction between UI and content text."]

---

## Color Philosophy

### Color Psychology

[What emotions/associations should the color palette evoke? Examples: "Trust and stability (blues)," "Energy and optimism (warm tones)," "Sophistication and restraint (monochrome with accent)."]

### Palette Mood

[Describe the overall color mood. Examples: "Light and airy," "Rich and grounded," "Vibrant and saturated," "Muted and sophisticated."]

### Contrast Approach

[How should contrast be used? Examples: "High contrast for clarity," "Low contrast for subtlety," "Strategic pops against neutral base."]

---

## Imagery Style

### Photography Style

[If using photography, describe the style. Examples: "Natural light, candid moments," "Studio-lit product shots with clean backgrounds," "Abstract close-ups emphasizing texture."]

### Illustration Approach

[If using illustrations, describe the style. Examples: "Line-based with minimal color," "Flat geometric shapes," "Hand-drawn organic forms."]

### Iconography Personality

[Describe icon style. Examples: "Simple line icons with consistent stroke," "Filled geometric shapes," "Playful rounded forms," "Technical precision with sharp angles."]

### Image Treatment

[How should images be treated? Examples: "Full-bleed immersive," "Framed with generous whitespace," "Overlaid with subtle gradients," "Black-and-white for timelessness."]

---

## Layout Philosophy

### Spatial Rhythm

[Describe the rhythm of space. Examples: "Generous whitespace creating breathing room," "Tight grid with efficient density," "Asymmetric layouts with intentional imbalance."]

### Density Preferences

[How much content per screen/page? Examples: "Minimal content with focus," "Information-rich with clear hierarchy," "Moderate density balancing clarity and efficiency."]

### Grid Personality

[How should the grid feel? Examples: "Strict modular grid for consistency," "Flexible asymmetric layouts," "Centered single-column for focus."]

---

## Motion & Interaction Feel

### Animation Personality

[Describe how motion should feel. Examples: "Subtle and refined," "Playful and bouncy," "Fast and efficient," "Slow and deliberate."]

### Transition Style

[How should transitions behave? Examples: "Smooth fades for elegance," "Snappy cuts for efficiency," "Sliding panels for spatial awareness."]

### Interaction Feedback Philosophy

[How should interactions feel? Examples: "Immediate and responsive," "Delicate with micro-interactions," "Bold state changes for clarity."]

---

## Material & Texture

### Surface Quality

[Describe surface treatment. Examples: "Flat and matte," "Subtle gradients suggesting depth," "Glassy with transparency," "Textured with grain."]

### Depth Approach

[How is depth/layering expressed? Examples: "Flat with color differentiation," "Subtle shadows suggesting elevation," "Strong shadows for dramatic depth," "No depth — pure flatness."]

### Tactile Qualities

[What physical qualities should the design suggest? Examples: "Soft and approachable," "Crisp and precise," "Warm and organic," "Cool and technical."]

---

## Creative Interpretation Notes

[This section is written by lavoisier after visual analysis via Playwright. Capture subjective observations, nuances, and insights that inform implementation but can't be reduced to tokens or rules.]

### Key Observations

[Bullet list of creative insights from inspiration analysis]

- [Observation 1]
- [Observation 2]
- [Observation 3]

### Unstated Needs Discovered

[Notes from iterative discovery flow — design directions the user didn't initially articulate but emerged through questioning]

- [Need 1]
- [Need 2]

### Implementation Implications

[How should these creative interpretations inform the technical implementation?]

---

## Inspiration References

[URLs analyzed via Playwright during design discovery, with key takeaways]

| Source | URL | Key Takeaways |
|------|-----|---------------|
| [Source Name] | [URL] | [What was inspiring about this example] |

**Screenshots:** See `inspiration_assets/` folder for visual reference.

---

## Do / Don't (Creative Guardrails)

| Do | Don't |
|----|-------|
| [Qualitative guidance] | [Qualitative anti-pattern] |
| Embrace generous whitespace | Fill every space with decoration |
| Use imagery to support narrative | Use generic stock photos for filler |
| Let brand personality guide decisions | Follow trends without strategic rationale |

---