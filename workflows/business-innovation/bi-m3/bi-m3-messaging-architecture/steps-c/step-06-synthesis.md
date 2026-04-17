---
name: 'step-06-synthesis'
description: 'Validate, compile final document, and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Create Audience Message Cards, validate hierarchy traceability, compile final Messaging Architecture document, and UPDATE project-memo.md with synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the clarity achieved. Note what was learned. Be honest about which messages are validated versus hypothetical. This architecture is a living document that evolves as M5 validation data accumulates.

### Step-Specific Rules
- project-memo.md MUST be updated with Messaging Architecture synthesis
- Audience Message Cards are REQUIRED (one per audience)
- Hierarchy traceability validation is REQUIRED
- Downstream integration notes are REQUIRED

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/messaging-architecture.md` from Steps 1-5
2. Read `{outputFolder}/project-memo.md` for update
3. Read `{outputFolder}/brand-prism.md` for final consistency check
4. Read `{outputFolder}/brand-archetypes.md` for thematic alignment check (if exists)

---

## MANDATORY SEQUENCE

### 1. Create Audience Message Cards

For each audience (Early Adopters, Mainstream Customers, Partners, Investors), create a one-page summary:

```markdown
## Audience Message Cards

### Early Adopters Message Card

**Audience Description:**
[Who they are, what they care about — from JTBD and Lean Canvas]

**Key Messages:**
1. [Message 1] `[Source]`
2. [Message 2] `[Source]`
3. [Message 3] `[Source]`
4. [Message 4] `[Source]` (if applicable)
5. [Message 5] `[Source]` (if applicable)

**Top Proof Points:**
- [Message 1]: [Proof 1], [Proof 2]
- [Message 2]: [Proof 1], [Proof 2]
- [Message 3]: [Proof 1], [Proof 2]
- [etc.]

**Primary CTAs and Channels:**
- Awareness: [CTA] via [Channel]
- Consideration: [CTA] via [Channel]
- Decision: [CTA] via [Channel]
- Retention: [CTA] via [Channel]

---

### Mainstream Customers Message Card

[Same structure as Early Adopters]

---

### Partners Message Card

[Same structure as Early Adopters]

---

### Investors Message Card

[Same structure as Early Adopters]
```

Present cards to founder:

> "Here are your Audience Message Cards — quick-reference tools for anyone writing copy. Each card shows:
> - Who the audience is and what they care about
> - Their 3-5 key messages with traceability
> - Top proof points per message
> - Primary CTAs by journey stage and channel
>
> These cards are what your team will use when writing landing pages, sales decks, email campaigns, or onboarding flows."

### 2. Validate Hierarchy Traceability

Test that every element traces correctly:

**Upward Traceability (CTAs → Messages → Promise):**

For each CTA, verify:
> "CTA '[CTA]' links to Message '[Message]'. Does this message support the brand promise '[Promise]'?"

If any CTA is orphaned (doesn't link to a message), flag for revision.

**Downward Traceability (Promise → Messages → Proof):**

For each message, verify:
> "Message '[Message]' supports brand promise '[Promise]'. Does this message have 2-3 proof points with documented sources?"

If any message lacks proof, it should already be flagged from Step 4.

Present validation summary:

> "**Hierarchy Traceability Validation:**
>
> - ✅ All CTAs link to supporting messages
> - ✅ All messages support brand promise
> - ✅ All messages have 2-3 proof points with sources
> - ⚠️ [N] messages flagged for M5 validation (insufficient proof)
>
> Your messaging hierarchy is complete and traceable."

### 3. Prepare Downstream Integration Notes

Document how Messaging Architecture feeds into downstream frameworks:

```markdown
## Downstream Integration

### Tone of Voice (M3 Next)
The key messages and proof points from this architecture become the raw material for tone application. Tone of Voice will define HOW these messages sound; Messaging Architecture defines WHAT they say.

**Handoff:**
- Use Audience Message Cards as input for tone examples
- Apply voice dimensions to each message type
- Ensure tone consistency across all four audiences

### M4 Prototypation
Prototype copy (landing page headlines, onboarding text, CTA buttons) must pull directly from this architecture. Reference specific messages and CTAs by ID.

**Handoff:**
- Landing page headlines: Use Early Adopter messages
- CTA buttons: Use exact CTA text from CTA Matrix
- Onboarding flow: Use Decision/Retention stage messages
- Proof points: Display as testimonials, data callouts, or feature benefits

### M5 Market Validation
A/B test messaging variants, SPIN selling scripts, and smoke test copy must use messages from this architecture. This ensures validation tests are testing brand-consistent messaging, not random copywriting.

**Handoff:**
- A/B tests: Test message variants from same audience (e.g., Early Adopter Message 1 vs. Message 2)
- SPIN selling: Use Investor messages for pitch scripts
- Smoke tests: Use Awareness CTAs for landing page tests
- Flagged gaps: Design experiments to generate missing proof points

### M6 MVP
Production marketing copy, onboarding flows, and support templates inherit from this architecture.

**Handoff:**
- Marketing site: Use all Awareness/Consideration messages and CTAs
- In-app copy: Use Decision/Retention messages
- Support docs: Use proof points as FAQ answers
- Email campaigns: Use Audience Message Cards for segmentation
```

### 4. Document Key Messaging Decisions

Reflect on what was learned during this framework:

Ask:
> "Reflecting on this messaging work:
> - Which audiences were easiest to message? Hardest?
> - Which messages were hardest to prove?
> - Which gaps need M5 validation most urgently?
> - What surprised you about the hierarchy?"

Record responses in a "Key Decisions and Learnings" section:

```markdown
## Key Decisions and Learnings

**Audience Prioritization:**
[Which audience is primary focus, which are secondary]

**Messaging Challenges:**
[Which messages were hardest to prove, which required most iteration]

**Validation Gaps:**
[Which proof points are hypothetical and need M5 experiments]

**Surprises:**
[What was unexpected about the messaging hierarchy or audience differences]
```

### 5. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{rbtv_path}/workflows/business-innovation/data/founder-process.md` for M3.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 6. Compile Final Document

Ensure messaging-architecture.md contains all sections in correct order:

1. Brand Promise (with rationale)
2. Key Messages by Audience (with traceability annotations)
3. Proof Point Library (with source/type/status)
4. Flagged Gaps (messages needing M5 validation)
5. CTA Matrix (with channel/message/proof links)
6. Journey Gap Analysis
7. Audience Message Cards (all four audiences)
8. Hierarchy Traceability Validation
9. Downstream Integration notes
10. Key Decisions and Learnings

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise', 'step-03-key-messages', 'step-04-proof-points', 'step-05-ctas-journey', 'step-06-synthesis']
status: completed
```

### 7. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-messaging-architecture` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Messaging Architecture

**Status:** Completed

**Brand Promise:** "[Brand promise text]"

**Key Findings:**
- Audiences: [N] audiences defined (Early Adopters, Mainstream, Partners, Investors)
- Messages: [N] total key messages across all audiences, all with traceability
- Proof Points: [N] validated proof points, [N] hypothetical (flagged for M5)
- CTAs: [N] CTAs mapped across 4 journey stages

**Validation Gaps:** [N] messages flagged for M5 validation due to insufficient proof

**Downstream Wiring:** Feeds into Tone of Voice (M3), M4 Prototypation, M5 Market Validation, M6 MVP

**Output:** [Link to messaging-architecture.md]
```

### 8. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 9. Completion Summary

Present to founder:

> "Messaging Architecture framework complete!
>
> **What we achieved:**
> - Distilled brand promise from positioning + Golden Circle Why
> - Built [N] key messages across 4 audiences, all traceable to validated data
> - Attached [N] proof points with documented sources
> - Mapped [N] CTAs to customer journey stages and channels
> - Created 4 Audience Message Cards for operational use
> - Validated complete hierarchy traceability
>
> **Brand Promise:**
> '[Promise]'
>
> **Validation Status:**
> - [N] messages fully validated with M2 proof
> - [N] messages flagged for M5 validation (insufficient proof)
>
> **What feeds forward:**
> - Tone of Voice: Messages become tone application examples
> - M4 Prototypation: Prototype copy pulls from this architecture
> - M5 Market Validation: A/B tests and experiments use these messages
> - M6 MVP: Production copy inherits from this architecture
>
> **Next recommended framework:** Tone of Voice (if not yet complete)
>
> **Note:** This is the final M3 Brand framework. After completing any remaining M3 frameworks, you can proceed to M4 Prototypation.
>
> **Return path:** To continue other M3 frameworks, return to bi-m3 milestone workflow."

### 10. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M3.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M3 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 11. Present Menu Options

**Select an Option:**
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify messaging-architecture.md has status: completed
2. Verify project-memo.md has Messaging Architecture entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

- Ask deeper questions about synthesis, downstream integration, or validation gaps
- After elicitation, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Audience Message Cards created for all 4 audiences, hierarchy traceability validated (CTAs→Messages→Promise, Messages→Proof), downstream integration notes prepared, key decisions documented, messaging-architecture.md complete with all 10 sections, project-memo.md updated with framework entry

❌ **FAILURE:** project-memo.md not updated, Audience Message Cards missing, hierarchy traceability not validated, downstream integration notes missing, key decisions not documented, framework not marked complete
