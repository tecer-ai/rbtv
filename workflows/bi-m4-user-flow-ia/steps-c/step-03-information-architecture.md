---
name: 'step-03-information-architecture'
description: 'Structure content hierarchy for conversion funnel'
nextStepFile: './step-04-synthesis.md'
outputFile: '{outputFolder}/user-flow-ia.md'
---

# Step 3: Information Architecture

**Progress: Step 3 of 4** — Next: Synthesis

---

## STEP GOAL

Structure content hierarchy following the AIDA funnel (Attention → Interest → Credibility → Action), mapping M1/M3 outputs to prototype sections.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor focused on conversion. Challenge content that doesn't move users toward action. Every element must earn its place on the page.

### Step-Specific Rules
- Every section must serve the conversion funnel (AIDA)
- Content hierarchy must be visually clear (primary > secondary > tertiary)
- Content density must match artifact type
- Remove anything that doesn't support conversion

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/user-flow-ia.md` for user flow from Step 2
2. Read `{outputFolder}/project-memo.md` for M1/M3 synthesis content
3. Review source frameworks for content:
   - Working Backwards: headlines, benefits
   - JTBD: job statements, outcomes
   - Lean Canvas: UVP, segments
   - Brand outputs: tone, messaging (if M3 complete)

---

## MANDATORY SEQUENCE

### 1. Content Inventory

Gather all available content from prior milestones:

> "Let's inventory the content we can use from M1/M3 frameworks:
>
> **From Working Backwards:**
> - Press release headline → Hero headline candidate
> - Target customer description → Audience targeting
> - Key benefits → Benefits section
>
> **From JTBD:**
> - Functional jobs → Feature descriptions
> - Emotional jobs → Benefit framing
> - Social jobs → Social proof selection
>
> **From Lean Canvas:**
> - UVP → Hero headline/subheadline
> - Customer Segments → Audience language
> - Unfair Advantage → Differentiation
>
> **From Brand (M3):**
> - Tone of Voice → Copy style
> - Messaging Architecture → Headline hierarchy
> - Brand Archetype → Imagery direction
>
> What content do we have from these frameworks?"

Create inventory table:

| Content Element | Source Framework | Section Mapping |
|-----------------|-----------------|-----------------|
| [content] | [framework] | [section] |

### 2. Map AIDA Funnel Sections

Guide content mapping to AIDA stages:

> "**AIDA Funnel for [artifact type]:**
>
> **ATTENTION (Hero Section)**
> Goal: Stop scroll, capture interest in 3 seconds
> - Headline: [Working Backwards press release / Lean Canvas UVP]
> - Subheadline: [Key benefit or credibility statement]
> - Hero visual: [Product screenshot / illustration / customer photo]
> - Primary CTA: [Conversion action button]
>
> **INTEREST (Benefits Section)**
> Goal: Build desire, show what they get
> - Benefit 1: [Functional job outcome]
> - Benefit 2: [Emotional job outcome]
> - Benefit 3: [Social job outcome]
> - (3-5 benefits total)
>
> **CREDIBILITY (Social Proof Section)**
> Goal: Overcome objections, build trust
> - Testimonials: [Customer quotes with outcomes]
> - Metrics: [Usage numbers, satisfaction rates]
> - Logos: [Customer/partner logos]
> - Trust badges: [Security, certifications]
>
> **ACTION (Final CTA Section)**
> Goal: Convert visitors who read through
> - Headline: [Restate or reframe value]
> - CTA button: [Same as hero CTA]
> - Urgency/scarcity: [If applicable]
>
> Let's map your content to these sections..."

### 3. Define Content Hierarchy Per Section

For each section, establish visual hierarchy:

> "For each section, what's the priority of elements?
>
> **Hierarchy Levels:**
> - **Primary:** Most important, largest, highest contrast
> - **Secondary:** Supporting, medium size, clear but subordinate
> - **Tertiary:** Details, smaller, less prominent
>
> Let's define hierarchy for each section..."

Document hierarchy per section:

| Section | Primary Element | Secondary Element | Tertiary Element |
|---------|-----------------|-------------------|------------------|
| Hero | Headline | Subheadline, CTA | Supporting text |
| Benefits | Benefit headlines | Descriptions | Icons |
| Social Proof | Testimonial quotes | Attribution | Logos |
| Final CTA | CTA button | Headline | Subtext |

### 4. Set Content Density

Based on artifact type, validate density:

| Artifact Type | Elements per Viewport | Validation |
|---------------|----------------------|------------|
| Landing Page | 1-2 focused elements | Is hero focused? |
| Website | 3-5 elements | Is navigation clear? |
| Infographic | Dense visuals, minimal text | Are visuals primary? |

> "For your [artifact type], content density should be [level].
>
> Let's check each section:
> - Hero: [element count] elements — [appropriate/too dense]
> - Benefits: [element count] elements — [appropriate/too dense]
> - Social Proof: [element count] elements — [appropriate/too dense]
> - Final CTA: [element count] elements — [appropriate/too dense]"

### 5. Plan CTA Placement

Document CTA strategy:

> "**CTA Placement Strategy:**
>
> | Location | CTA Type | Visibility |
> |----------|----------|------------|
> | Hero | Primary | Above fold (mandatory) |
> | After benefits | Secondary (optional) | Scroll depth ~50% |
> | Final section | Primary | After social proof |
>
> Is your primary CTA visible without scrolling on mobile (375px viewport)?"

### 6. Validate Content Pruning

Challenge every element:

> "**Content Pruning Check:**
>
> For each element, ask: Does this move users toward conversion?
>
> ❌ Remove if:
> - Decorative only (no information value)
> - Distracting from CTA
> - Duplicating other content
> - Answering questions nobody asked
>
> ✅ Keep if:
> - Captures attention (hero)
> - Builds desire (benefits)
> - Overcomes objections (social proof)
> - Enables action (CTA)
>
> What should we remove?"

### 7. Update Output Document

Update user-flow-ia.md with Information Architecture section:

```markdown
## Information Architecture

### Content Inventory
| Content Element | Source Framework | Section Mapping |
|-----------------|-----------------|-----------------|
| [content] | [framework] | [section] |

### AIDA Funnel Structure

#### Attention (Hero)
- **Headline:** [text]
- **Subheadline:** [text]
- **Hero Visual:** [description]
- **Primary CTA:** [button text]

#### Interest (Benefits)
| # | Benefit Headline | Description | Source |
|---|------------------|-------------|--------|
| 1 | [headline] | [description] | [framework] |
| 2 | [headline] | [description] | [framework] |
| 3 | [headline] | [description] | [framework] |

#### Credibility (Social Proof)
- **Testimonials:** [list]
- **Metrics:** [list]
- **Logos:** [list]
- **Trust Badges:** [list]

#### Action (Final CTA)
- **Headline:** [text]
- **CTA Button:** [text]
- **Supporting Text:** [text]

### Content Hierarchy
| Section | Primary | Secondary | Tertiary |
|---------|---------|-----------|----------|
| [section] | [element] | [element] | [element] |

### CTA Placement
| Location | CTA Type | Visibility |
|----------|----------|------------|
| [location] | [type] | [visibility] |

### Content Density Validation
- [x] Density appropriate for [artifact type]
- [x] Hero focused (1-2 elements)
- [x] No decorative-only elements
- [x] Every element supports conversion
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-user-flow', 'step-03-information-architecture']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis
- **[R] Revise** — modify information architecture

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure user-flow-ia.md has Information Architecture section complete
2. Verify `step-03-information-architecture` is in `stepsCompleted`
3. Load `./step-04-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Content inventoried from M1/M3, AIDA sections mapped, hierarchy defined, density appropriate, all content supports conversion

❌ **FAILURE:** Missing content inventory, no clear hierarchy, decorative elements retained, CTA not above fold, density inappropriate for artifact type
