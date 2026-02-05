---
name: 'step-05-ctas-journey'
description: 'Map calls-to-action to customer journey stages'
nextStepFile: './step-06-synthesis.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 5: Define CTAs & Journey Mapping

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Map specific CTAs to customer journey stages (Awareness, Consideration, Decision, Retention) and distribution channels, ensuring the right ask appears at the right moment. Link each CTA to supporting messages and proof points.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. CTAs without journey context produce a beautiful document that nobody knows how to use. Messages need activation: who sees them, when, and what do we ask them to do next?

### Step-Specific Rules
- Work through journey stages ONE AT A TIME (Awareness → Consideration → Decision → Retention)
- Each CTA MUST specify: channel, supporting message, supporting proof point
- CTAs must use channels from Lean Canvas Channels block
- CTA commitment level must match journey stage (don't ask for purchase at Awareness)
- Check for journey gaps (stages with no CTA)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/messaging-architecture.md` for key messages and proof points
2. Read `{outputFolder}/lean-canvas.md` for Channels block
3. Read `{outputFolder}/jobs-to-be-done.md` for job map (stages of progress)
4. Optional: Read `{outputFolder}/problem-solution-fit.md` for constraints, adoption barriers

---

## MANDATORY SEQUENCE

### 1. Define Journey Stages and Mindsets

Present the four journey stages:

> "We'll map CTAs to four customer journey stages. Each stage has a different mindset and requires a different level of commitment:
>
> 1. **Awareness** — Customer recognizes the problem but hasn't evaluated solutions
>    - Mindset: Curious, skeptical, time-constrained
>    - Appropriate CTAs: 'Learn more' actions (read blog, watch demo video, download guide, attend webinar)
>
> 2. **Consideration** — Customer actively comparing options
>    - Mindset: Analytical, risk-aware, looking for proof
>    - Appropriate CTAs: 'Try or compare' actions (start free trial, request demo, view case studies, compare pricing)
>
> 3. **Decision** — Customer ready to commit
>    - Mindset: Needs final reassurance, wants to minimize switching cost
>    - Appropriate CTAs: 'Buy or sign up' actions (create account, start paid plan, schedule onboarding, sign contract)
>
> 4. **Retention** — Customer using product, deciding whether to expand or refer
>    - Mindset: Evaluating ROI, looking for deeper value
>    - Appropriate CTAs: 'Expand or refer' actions (upgrade plan, invite team members, leave review, refer colleague)
>
> We'll define CTAs for each stage, linked to your Lean Canvas Channels: [list channels]"

### 2. Map Awareness Stage CTAs

From Lean Canvas Channels, identify awareness-appropriate channels (content marketing, social media, SEO, partnerships, events).

Ask:
> "At the Awareness stage, customers are curious but skeptical. They need low-commitment 'learn more' actions.
>
> Looking at your channels: [channels]
>
> What CTAs would you use at Awareness? Examples:
> - Read a blog post about [problem]
> - Watch a 2-minute demo video
> - Download a guide on [topic]
> - Attend a webinar about [solution category]"

For each CTA proposed, ask:

**Which channel?**
> "Where would this CTA appear? [List Lean Canvas Channels]"

**Which key message supports it?**
> "Which message from Step 3 sets up this CTA? The message should address the customer's awareness-stage concerns."

**Which proof point supports it?**
> "Which proof point from Step 4 removes the barrier at this stage? At Awareness, proof points should establish credibility, not push for commitment."

Document in format:
```
CTA: [Action]
Channel: [Channel from Lean Canvas]
Supporting Message: [Audience] - [Message text]
Supporting Proof Point: [Proof point text]
```

Repeat for 2-4 Awareness CTAs across different channels.

### 3. Map Consideration Stage CTAs

From Lean Canvas Channels, identify consideration-appropriate channels (website, email, sales conversations, partner referrals).

Ask:
> "At the Consideration stage, customers are comparing options. They need 'try or compare' actions that provide hands-on experience or detailed comparisons.
>
> What CTAs would you use at Consideration? Examples:
> - Start a 14-day free trial
> - Request a personalized demo
> - View case studies from [industry]
> - Compare pricing and features"

For each CTA, document:
- Channel (from Lean Canvas)
- Supporting Message (which message sets this up)
- Supporting Proof Point (which proof removes hesitation)

Repeat for 2-4 Consideration CTAs.

### 4. Map Decision Stage CTAs

From Lean Canvas Channels, identify decision-appropriate channels (website, sales conversations, email, onboarding).

Ask:
> "At the Decision stage, customers are ready to commit but need final reassurance. They need 'buy or sign up' actions with minimal friction.
>
> What CTAs would you use at Decision? Examples:
> - Create your account (no credit card required)
> - Start your paid plan
> - Schedule onboarding call
> - Sign contract with [guarantee]"

For each CTA, document:
- Channel (from Lean Canvas)
- Supporting Message (which message provides final reassurance)
- Supporting Proof Point (which proof reduces switching cost anxiety)

Repeat for 2-4 Decision CTAs.

### 5. Map Retention Stage CTAs

From Lean Canvas Channels, identify retention-appropriate channels (in-app, email, customer success, community).

Ask:
> "At the Retention stage, customers are evaluating ROI and deciding whether to expand or refer. They need 'expand or refer' actions that deepen engagement.
>
> What CTAs would you use at Retention? Examples:
> - Upgrade to [higher tier plan]
> - Invite team members (get [benefit])
> - Leave a review on [platform]
> - Refer a colleague (get [referral bonus])"

For each CTA, document:
- Channel (from Lean Canvas)
- Supporting Message (which message shows deeper value)
- Supporting Proof Point (which proof demonstrates ROI)

Repeat for 2-4 Retention CTAs.

### 6. Cross-Reference Against JTBD Job Map

If JTBD job map exists, verify CTAs align with job progression stages (Define, Locate, Prepare, Execute, Confirm, Evolve).

Ask:
> "Looking at your JTBD job map stages: [stages]
>
> Do your CTAs align with where customers are in their job progression? Any gaps where you have no CTA for a critical job stage?"

If gaps identified, create missing CTAs or flag for M4/M5 development.

### 7. Create CTA Matrix

Compile all CTAs into a table:

```markdown
## CTA Matrix

| Journey Stage | CTA | Channel | Supporting Message | Supporting Proof Point |
|---------------|-----|---------|-------------------|------------------------|
| Awareness | [CTA 1] | [Channel] | [Audience] - [Message] | [Proof point] |
| Awareness | [CTA 2] | [Channel] | [Audience] - [Message] | [Proof point] |
| Consideration | [CTA 1] | [Channel] | [Audience] - [Message] | [Proof point] |
| Consideration | [CTA 2] | [Channel] | [Audience] - [Message] | [Proof point] |
| Decision | [CTA 1] | [Channel] | [Audience] - [Message] | [Proof point] |
| Decision | [CTA 2] | [Channel] | [Audience] - [Message] | [Proof point] |
| Retention | [CTA 1] | [Channel] | [Audience] - [Message] | [Proof point] |
| Retention | [CTA 2] | [Channel] | [Audience] - [Message] | [Proof point] |

### Journey Gap Analysis

Stages or channels lacking CTAs (require M4 prototype planning or M5 experiment design):

1. [Stage/Channel] - [Description of gap]
   - **Impact:** [Why this gap matters]
   - **Recommendation:** [Suggested CTA or experiment]

2. [Next gap if any]
```

### 8. Validate CTA Progression

Check that CTAs represent increasing commitment:

> "Reading your CTAs from Awareness → Retention, do they represent a natural progression of increasing commitment?
>
> - Awareness: Low commitment (learn, watch, download)
> - Consideration: Medium commitment (try, compare, demo)
> - Decision: High commitment (buy, sign up, contract)
> - Retention: Expansion commitment (upgrade, invite, refer)
>
> Any CTAs asking for too much too soon?"

If progression is broken (e.g., asking for purchase at Awareness), revise CTAs.

### 9. Update Output Document

Update messaging-architecture.md CTA Matrix section with the table and journey gap analysis.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise', 'step-03-key-messages', 'step-04-proof-points', 'step-05-ctas-journey']
```

### 10. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis
- **[R] Refine** — revise CTAs for specific journey stage
- **[A] Advanced Elicitation** — deeper exploration of CTA options

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure CTA Matrix is complete with CTAs for all four journey stages
2. Ensure journey gap analysis is documented
3. Verify `step-05-ctas-journey` is in `stepsCompleted`
4. Load `./step-06-synthesis.md` and follow its instructions

When **[R] Refine** is selected:
- Ask which journey stage to refine
- Return to that stage's CTA section and re-elicit CTAs
- Redisplay menu

When **[A] Advanced Elicitation** is selected:
- Ask deeper questions about channel strategy, CTA friction points, or journey stage gaps
- After elicitation, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Every journey stage has 2-4 CTAs, every CTA specifies channel/message/proof, CTAs use Lean Canvas Channels, CTA progression represents increasing commitment, journey gaps documented with recommendations

❌ **FAILURE:** Journey stages missing CTAs, CTAs without channel/message/proof links, CTAs use channels not in Lean Canvas, CTA commitment level doesn't match journey stage (e.g., asking for purchase at Awareness), journey gaps not documented
