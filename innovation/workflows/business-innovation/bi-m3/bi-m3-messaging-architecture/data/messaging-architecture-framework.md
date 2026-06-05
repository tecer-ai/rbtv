# Messaging Architecture Framework

**Purpose:** Build a hierarchical messaging structure that ensures consistent, audience-specific communication across all touchpoints.

---

## Framework Overview

Messaging Architecture is a hierarchical communication structure that moves from a single brand promise at the top through key messages, proof points, and calls to action at the bottom. The core principle: every piece of communication a brand produces must trace upward to a single, unifying promise and downward to concrete evidence that makes the promise credible.

Most startups skip this step entirely and write ad hoc copy for each touchpoint. The result is fragmented messaging where the landing page says one thing, the investor deck says another, and the onboarding flow says a third. Messaging Architecture prevents this by defining the hierarchy once and then deriving all copy from it.

This framework matters because it bridges the gap between strategic brand identity (archetypes, prism, positioning) and tactical execution (prototype copy, sales scripts, marketing campaigns). Without it, the brand frameworks remain abstract concepts that never reach the customer. With it, every word the brand produces is intentional, traceable, and testable.

---

## The Four-Level Hierarchy

### Level 1: Brand Promise

A single sentence (max 15 words) that distills the Brand Positioning Statement into a customer-facing commitment. It combines:
- **Rational benefit** from positioning ("that [key benefit]" clause)
- **Emotional register** from Golden Circle Why

**Structure:** "[Emotional aspiration] through [rational mechanism]" or "[What changes for you] because [why we exist]"

**Filters:**
- **Customer-facing:** Would a real customer nod and say "yes, that is what I want"?
- **Emotionally resonant:** Does it connect to a feeling (confidence, relief, pride, control)?
- **Differentiated:** Could a competitor claim the exact same promise without changing a word?

### Level 2: Key Messages (3-5 per audience)

Audience-specific messages that support the brand promise. Each message must:
- Support the brand promise (trace upward)
- Address what that specific audience cares about
- Use language that audience actually uses (from JTBD interviews)
- Have documented traceability to framework output or validated assumption

**Primary Audiences:**
- **Early adopters:** First users who feel pain most acutely, tolerate rough edges
- **Mainstream customers:** Larger segment after early traction
- **Partners:** Technology, distribution, or integration partners
- **Investors:** Seed, Series A, or strategic investors

**Traceability annotation format:** `[Source: JTBD primary job]` or `[Source: M2 validated assumption #3]`

### Level 3: Proof Points (2-3 per message)

Evidence that makes each message credible:
- **Data points:** M2 validation results, survey percentages, experiment outcomes
- **Customer language:** Direct quotes from JTBD interviews (verbatim, not paraphrased)
- **Feature-as-benefit:** Product capability framed as what it enables ("reduces reporting time from 4 hours to 20 minutes")
- **Third-party validation:** Industry analyst citations, press coverage, advisor endorsements

Each proof point must document:
- The proof point itself (one sentence)
- The source (which framework, interview, or data set)
- The type (data, customer quote, feature-benefit, third-party)
- Status (validated/hypothetical)

### Level 4: Calls to Action (by journey stage)

Specific CTAs mapped to customer journey stages and distribution channels:

**Journey Stages:**
- **Awareness:** Customer recognizes problem but hasn't evaluated solutions
  - CTAs: "Learn more" (read blog, watch demo, download guide, attend webinar)
- **Consideration:** Customer actively comparing options
  - CTAs: "Try or compare" (start trial, request demo, view case studies, compare pricing)
- **Decision:** Customer ready to commit
  - CTAs: "Buy or sign up" (create account, start paid plan, schedule onboarding, sign contract)
- **Retention:** Customer using product, deciding whether to expand or refer
  - CTAs: "Expand or refer" (upgrade plan, invite team, leave review, refer colleague)

Each CTA specifies:
- The **channel** where it appears (from Lean Canvas Channels)
- The **key message** it connects to
- The **proof point** that supports it

---

## Messaging Consistency Checks

### Brand Prism Alignment

Every message and proof point must align with Brand Prism facets:
- **Culture:** Core values and beliefs
- **Personality:** Voice characteristics
- **Relationship:** How brand relates to customer

If a message contradicts the Prism, revise the message (not the Prism).

### Traceability Requirements

Every element must trace to validated sources:
- Key messages → JTBD jobs, M2 validated assumptions, Lean Canvas
- Proof points → M2 validation data, JTBD customer quotes, framework outputs
- CTAs → Lean Canvas Channels, JTBD job map stages

Messages without traceability are opinions, not strategy.

---

## Audience Message Cards

One-page quick-reference summaries per audience containing:
- Audience name and description (who they are, what they care about)
- Their 3-5 key messages
- Top proof points for each message
- Primary CTAs and channels

These cards are the operational tools that anyone writing copy will use.

---

## Downstream Integration

### Tone of Voice (M3 Step 7)
Key messages and proof points become raw material for tone application. Tone defines how messages sound; Messaging Architecture defines what they say.

### M4 Prototypation
Prototype copy (landing page headlines, onboarding text, CTA buttons) must pull directly from this architecture. Reference specific messages and CTAs by ID.

### M5 Market Validation
A/B test messaging variants, SPIN selling scripts, and smoke test copy must use messages from this architecture. This ensures validation tests are testing brand-consistent messaging.

### M6 MVP
Production marketing copy, onboarding flows, and support templates inherit from this architecture.

---

## Common Pitfalls

### Writing Slogans Instead Of Strategy
A brand promise is not a tagline for an ad campaign. Slogans are creative executions; the brand promise is a strategic commitment. If your promise sounds like something a copywriter would put on a billboard, it is too superficial.

### Treating All Audiences The Same
Early adopters, mainstream customers, partners, and investors have fundamentally different concerns, risk tolerances, and vocabularies. A single set of messages produces communications that are vaguely relevant to everyone and deeply compelling to no one.

### Proof Points Without Sources
Unattributed proof points are opinions, not evidence. Claiming "customers love our product" without a specific quote, metric, or data point trains the audience to distrust your claims.

### Feature-Stuffing The Message Layer
Key messages describe outcomes, beliefs, and emotional shifts — not product capabilities. "We offer real-time collaboration" is a feature. "Your team ships decisions in hours, not weeks" is a message.

### Skipping The Journey Stage Mapping
Defining messages without CTAs and journey context produces a beautiful document that nobody knows how to use. Messages need activation: who sees them, when, and what do we ask them to do next?

### Ignoring M2 Validation Data
Building messaging on assumptions rather than validated data produces messages that sound good internally but fail with real customers. If M2 has validated (or invalidated) specific claims, the messaging architecture must reflect that evidence.

---

## Prerequisites

**MUST complete before starting:**
- Brand Positioning Statement (M3 framework)
- Golden Circle (M3 framework)
- Brand Prism (M3 framework)
- Jobs-to-be-Done (M1 framework)
- Working Backwards (M1 framework)
- Lean Canvas (M1 framework)
- At least 3 M2 validation frameworks

**Builds on:**
- Brand Positioning Statement → Rational foundation of brand promise
- Golden Circle Why → Emotional register for brand promise
- Brand Prism → Message consistency across brand identity
- Brand Archetypes → Storytelling patterns and thematic emphasis
- Jobs-to-be-Done → Customer vocabulary and journey stage mapping
- Working Backwards → Customer-facing narrative to distill
- Lean Canvas → Audience definitions, message content, CTA channels
- M2 Validation → Evidence for proof points

---

## Success Criteria

Framework is complete when:

- [ ] Brand promise exists as single sentence (max 15 words) with documented rationale
- [ ] 3-5 key messages exist per audience with traceability annotations
- [ ] Proof Point Library exists with 2-3 proof points per message, each attributed to source
- [ ] CTA Matrix maps CTAs to journey stages with channel/message/proof links
- [ ] Audience Message Cards exist as one-page summaries per audience
- [ ] Every message traces upward to promise and downward to proof points
- [ ] Messages with insufficient proof flagged for M5 validation
- [ ] Messaging Architecture document references downstream frameworks (ToV, M4, M5, M6)
- [ ] M3 founder diary contains messaging decision entries
- [ ] project-memo.md updated with Messaging Architecture synthesis
