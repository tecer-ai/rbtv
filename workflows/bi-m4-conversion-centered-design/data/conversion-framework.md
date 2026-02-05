# Conversion-Centered Design Framework Knowledge

**Purpose:** Reference knowledge for Conversion-Centered Design (CCD) methodology applied to founder prototypes.

---

## Framework Overview

Conversion-Centered Design focuses every design decision on driving a single, clear action. Unlike general UX design, CCD ruthlessly eliminates anything that doesn't move users toward conversion.

### The Single Goal Principle

Every page/screen should have ONE conversion goal. Multiple CTAs competing for attention = reduced conversion.

**Examples of single goals:**
- Landing page: Sign up for waitlist
- Product page: Add to cart
- Pricing page: Start free trial
- Infographic: Share / Download

---

## The AIDA Funnel

Map content to the classic conversion funnel:

| Stage | Goal | Design Elements |
|-------|------|-----------------|
| **Attention** | Stop the scroll, capture interest | Hero headline, striking visuals, pattern interrupts |
| **Interest** | Build curiosity, establish relevance | Problem statement, empathy, "you" language |
| **Credibility** | Overcome skepticism | Social proof, testimonials, logos, data |
| **Action** | Drive conversion | CTA button, urgency, clear next step |

---

## 7 Conversion Principles

### 1. Attention Ratio
**Definition:** Ratio of interactive elements to conversion goal(s).
**Target:** 1:1 — one link per page goal.
**Problem:** Navigation menus, footer links, social icons all compete with CTA.
**Solution:** Remove or minimize non-essential links on conversion-focused pages.

### 2. Visual Hierarchy
**Rule:** CTA must be the most visually prominent element.
**Techniques:**
- Size: CTA button larger than other elements
- Color: High contrast against background (≥4.5:1)
- Whitespace: Breathing room around CTA
- Position: Above fold on all devices

### 3. Directional Cues
**Purpose:** Guide eye movement toward CTA.
**Types:**
- Explicit: Arrows, pointing fingers, lines
- Implicit: Eye gaze direction in photos, converging lines
- Content flow: Headlines → Subheads → CTA

### 4. Friction Reduction
**Definition:** Remove unnecessary steps, questions, or cognitive load.
**Common friction points:**
- Too many form fields
- Required registration before value
- Unclear pricing
- Missing information (what happens after click?)
- Slow load times

### 5. Urgency and Scarcity
**Legitimate urgency:** Limited time offers, countdown timers, limited availability.
**Warning:** Fake urgency destroys trust. Only use if real.
**Alternatives:** Social proof ("12 people viewing now"), progress indicators.

### 6. Encapsulation
**Technique:** Visually separate the CTA zone from other content.
**Methods:** Box, card, contrasting background, clear borders.
**Purpose:** Creates a "decision zone" that signals "act here."

### 7. Congruence
**Definition:** Message match between ad/link and landing page.
**Rule:** Headline must echo the promise that brought the user.
**Example:** Ad says "Free Trial" → Landing page headline includes "Free Trial."

---

## CTA Optimization Checklist

### Copy
- [ ] Action verb first ("Get," "Start," "Join," not "Submit")
- [ ] Benefit-oriented ("Get Free Access" not "Sign Up")
- [ ] Specific outcome ("Download the Guide" not "Learn More")
- [ ] First person can increase conversion ("Start My Free Trial")

### Visual
- [ ] High contrast color (test: squint test — CTA should still stand out)
- [ ] Minimum 44px touch target on mobile
- [ ] Adequate padding (button doesn't look cramped)
- [ ] Clear hover/focus states

### Placement
- [ ] Above fold on all devices (375px, 768px, 1200px+)
- [ ] Repeated at logical scroll points (after testimonials, after benefits)
- [ ] Not buried below secondary content

### Context
- [ ] Supporting microcopy addresses objections ("No credit card required")
- [ ] Trust signals near CTA (security badges, privacy note)
- [ ] Clear expectation of what happens next

---

## Distraction Audit Questions

For every element on the page, ask:

1. **Does this drive conversion?** If no, justify or remove.
2. **Does this answer a key objection?** If no, move lower or remove.
3. **Is this above the fold?** If yes, is it essential for first impression?
4. **Does this link away from the page?** If yes, consider removing.
5. **Would a first-time visitor understand this?** If no, simplify.

---

## Friction Analysis Framework

### Friction Categories

| Category | Examples | Severity |
|----------|----------|----------|
| **Cognitive** | Unclear value prop, jargon, too much text | High |
| **Mechanical** | Too many form fields, broken buttons, slow load | High |
| **Trust** | No social proof, missing contact info, sketchy design | Medium |
| **Value** | Unclear pricing, hidden costs, missing benefits | Medium |
| **Technical** | Mobile issues, browser compatibility, accessibility | Varies |

### Severity Rating

- **Critical (5):** Blocks conversion entirely (broken CTA, unclear what to do)
- **Major (4):** Significant barrier, many users will abandon
- **Moderate (3):** Noticeable friction, some users will hesitate
- **Minor (2):** Small annoyance, unlikely to cause abandonment
- **Cosmetic (1):** Polish issue, no conversion impact

---

## Hypothesis Template

```
IF we [change]
THEN we expect [metric] to [increase/decrease] by [amount]
BECAUSE [rationale based on principle/friction analysis]
```

**Example:**
```
IF we remove the navigation menu from the landing page
THEN we expect CTA clicks to increase by 15-25%
BECAUSE attention ratio improves from 12:1 to 1:1 (Principle 1)
```

---

## Impact vs. Effort Matrix

| Quadrant | Action |
|----------|--------|
| High Impact + Low Effort | Do first (quick wins) |
| High Impact + High Effort | Plan and schedule |
| Low Impact + Low Effort | Do if time permits |
| Low Impact + High Effort | Deprioritize or skip |

---

## Anti-Patterns to Avoid

1. **Multiple competing CTAs** — Pick one primary action per page
2. **Generic copy** — "Submit" tells users nothing
3. **Buried CTA** — If users have to scroll to find it, conversion drops
4. **Navigation on landing pages** — Every link is an exit
5. **Wall of text above CTA** — Users skim; get to the point
6. **No mobile optimization** — 50%+ traffic is mobile
7. **Fake urgency** — Users recognize manipulation
