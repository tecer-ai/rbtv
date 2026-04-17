# User Flow & Information Architecture Framework

## Overview

User Flow Mapping and Information Architecture work together to optimize the path from first contact to conversion. User Flow defines the journey; IA defines the content structure at each point.

---

## User Flow Mapping Principles

### Entry Points

How users arrive at your prototype:

| Entry Type | Context | Design Implication |
|------------|---------|-------------------|
| Paid Ad | Problem-aware, solution-seeking | Hero must match ad promise |
| Organic Search | Researching, comparing | Must establish credibility fast |
| Social Media | Curious, distracted | Must hook attention in 3 seconds |
| Email | Already engaged | Can skip awareness, go to action |
| Direct/Referral | Pre-sold by referrer | Validation focus, easy conversion |

### Flow Elements

| Element | Purpose | Design |
|---------|---------|--------|
| Screen | Single state/viewport user sees | Bounded content block |
| Decision Point | User chooses between actions | Limited options (2-3 max) |
| Conversion Goal | Primary action we want | Single CTA, highly visible |
| Exit Point | Where users leave | Track for optimization |

### Anti-Patterns

- Multiple competing CTAs (decision paralysis)
- Navigation menus on landing pages (escape routes)
- Conversion goal below fold (invisible)
- More than 3 clicks to conversion (friction)

---

## Information Architecture Principles

### AIDA Funnel Structure

| Stage | Goal | Content Type |
|-------|------|--------------|
| **Attention** | Stop scroll, capture interest | Hero headline, key visual |
| **Interest** | Build desire, show benefits | Benefit blocks, use cases |
| **Credibility** | Overcome objections | Social proof, testimonials |
| **Action** | Convert | CTA, form, next step |

### Content Hierarchy Per Section

| Level | Purpose | Visual Treatment |
|-------|---------|-----------------|
| Primary | Most important element | Largest, highest contrast |
| Secondary | Supporting information | Medium size, clear but subordinate |
| Tertiary | Details, context | Smaller, less prominent |

### Content Density Rules

| Artifact Type | Density | Rationale |
|---------------|---------|-----------|
| Landing Page | Low (1-2 elements per viewport) | Focus on single action |
| Website | Medium (3-5 elements) | Navigation and exploration |
| Infographic | High (visual-dense) | Data communication |

---

## Artifact Types

### Landing Page

**Purpose:** Single conversion goal
**Structure:** Hero → Benefits → Social Proof → CTA
**Rules:**
- No navigation menu
- One primary CTA repeated
- CTA above fold mandatory

### Website (Multi-page)

**Purpose:** Multiple journeys, exploration
**Structure:** Home → Category pages → Detail pages → Conversion
**Rules:**
- Clear navigation
- Consistent header/footer
- Multiple CTAs appropriate

### Infographic

**Purpose:** Data communication, vertical scroll
**Structure:** Hero → Section 1 → Section 2 → ... → Footer
**Rules:**
- Visual-first (icons, charts, large numbers)
- Section-based with distinct backgrounds
- Statistics prominent (72px+ font)

### One-Pager

**Purpose:** Document summary
**Structure:** Header → Key sections → Contact
**Rules:**
- Text-forward with supporting visuals
- Scannable headings
- Single page (print-friendly)

---

## Conversion Goal Types

| Goal | Form Required | Friction Level |
|------|--------------|----------------|
| Email Signup | Email only | Very Low |
| Content Download | Name + Email | Low |
| Demo Request | Name + Email + Company | Medium |
| Purchase | Payment details | High |
| Quote Request | Detailed form | High |

**Rule:** Lower friction = higher conversion rate. Only ask for what you need.

---

## Content Mapping from M1/M3

### From Working Backwards (M1)
- Target customer description → Hero subheadline
- Press release headline → Hero headline candidate
- Key benefits → Benefits section

### From JTBD (M1)
- Functional jobs → Feature descriptions
- Emotional jobs → Benefit framing
- Social jobs → Social proof selection

### From Lean Canvas (M1)
- UVP → Hero headline
- Customer Segments → Audience targeting
- Unfair Advantage → Differentiation messaging

### From Brand (M3)
- Brand Archetype → Tone and imagery
- Tone of Voice → Copy style
- Messaging Architecture → Headline hierarchy

---

## Validation Questions

### User Flow Validation
- [ ] Can a user reach conversion in 3 clicks or less?
- [ ] Is the primary CTA visible without scrolling on mobile?
- [ ] Are there competing CTAs that create confusion?
- [ ] Are exit points documented with drop-off risks?

### IA Validation
- [ ] Does content follow AIDA sequence?
- [ ] Is hierarchy clear (what's most important is most prominent)?
- [ ] Does every section move user toward conversion?
- [ ] Is content density appropriate for artifact type?
