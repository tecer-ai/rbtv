---
name: 'step-02-brand-promise'
description: 'Distill positioning into single customer-facing brand promise'
nextStepFile: './step-03-key-messages.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 2: Define Brand Promise

**Progress: Step 2 of 6** — Next: Key Messages

---

## STEP GOAL

Distill the Brand Positioning Statement into a single, customer-facing brand promise (max 15 words) that combines rational benefit and emotional register.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The brand promise is not a clever tagline — it's a strategic commitment. Reject vague aspirations. Demand emotional resonance grounded in customer evidence.

### Step-Specific Rules
- Brand promise MUST be max 15 words
- MUST connect explicitly to both Positioning (rational) and Golden Circle Why (emotional)
- MUST pass all three filters: customer-facing, emotionally resonant, differentiated
- Do NOT write multiple promise options — guide founder to ONE through questioning

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/messaging-architecture.md` for current state
2. Read `{outputFolder}/brand-positioning.md` for positioning statement
3. Read `{outputFolder}/golden-circle.md` for Why statement
4. Read `{outputFolder}/working-backwards.md` for PR headline and customer quote
5. Read `{outputFolder}/brand-prism.md` for Culture and Relationship facets

---

## MANDATORY SEQUENCE

### 1. Extract Rational Foundation

From Brand Positioning Statement, identify:
- The "that [key benefit]" clause — this is the rational foundation
- The competitive frame — what makes this benefit differentiated

Ask:
> "Your positioning says: '[positioning statement]'
>
> What is the core benefit claim in the 'that [key benefit]' clause? In one phrase, what changes for the customer?"

Wait for response. Record the rational benefit phrase.

### 2. Extract Emotional Register

From Golden Circle Why, identify:
- The belief or cause the brand champions
- The emotional territory (confidence, relief, pride, control, freedom, etc.)

Ask:
> "Your Golden Circle Why is: '[Why statement]'
>
> What emotion or aspiration does this Why connect to? When a customer engages with this brand, what should they FEEL?"

Wait for response. Record the emotional register.

### 3. Draft Brand Promise

Combine rational benefit and emotional register using one of these structures:
- "[Emotional aspiration] through [rational mechanism]"
- "[What changes for you] because [why we exist]"

Present draft:
> "Let's combine these. Draft brand promise:
>
> '[Draft promise]'
>
> This is [N] words. Max is 15."

If over 15 words, work with founder to compress without losing meaning.

### 4. Apply Three Filters

Test the draft against each filter:

**Filter 1: Customer-Facing**

Ask:
> "If a customer read this with NO context about your company, would they nod and say 'yes, that is what I want'?
>
> Or does it sound like an internal strategy statement?"

If internal-sounding, revise to use customer language from JTBD interviews.

**Filter 2: Emotionally Resonant**

Ask:
> "Does this connect to a FEELING (confidence, relief, pride, control), not just a feature?
>
> Read it out loud. Do you feel something, or is it just information?"

If purely informational, strengthen the emotional register using Golden Circle Why.

**Filter 3: Differentiated**

Ask:
> "Could [Top Competitor] claim the exact same promise without changing a word?
>
> If yes, what makes YOUR version of this promise unique?"

If not differentiated, sharpen using the competitive frame from positioning.

### 5. Cross-Check Against Working Backwards

Compare draft promise to Working Backwards PR headline and customer quote.

Ask:
> "Your Working Backwards PR headline was: '[headline]'
>
> Your customer quote was: '[quote]'
>
> Does your brand promise feel like the distilled essence of both? Or does it contradict either?"

If contradictory, reconcile by adjusting promise to align with customer evidence.

### 6. Document Rationale

Record how the promise connects to upstream frameworks:

```markdown
## Brand Promise

**Promise:** [Final brand promise — max 15 words]

**Rationale:**
- **Rational Foundation (Positioning):** [How promise connects to "that [key benefit]" clause]
- **Emotional Register (Golden Circle Why):** [How promise connects to Why statement and emotional territory]
- **Differentiation:** [How promise distinguishes from competitors using competitive frame]

**Filter Validation:**
- ✅ Customer-Facing: [Brief note on why this passes]
- ✅ Emotionally Resonant: [Brief note on emotional connection]
- ✅ Differentiated: [Brief note on competitive distinction]

**Working Backwards Alignment:**
- PR Headline: [How promise aligns]
- Customer Quote: [How promise aligns]
```

### 7. Update Output Document

Update messaging-architecture.md Brand Promise section with the documented promise and rationale.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Key Messages definition
- **[R] Refine** — revise brand promise with additional elicitation
- **[A] Advanced Elicitation** — deeper exploration of promise options

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure Brand Promise section is complete with rationale
2. Verify `step-02-brand-promise` is in `stepsCompleted`
3. Load `./step-03-key-messages.md` and follow its instructions

When **[R] Refine** is selected:
- Return to Section 3 (Draft Brand Promise) with current draft as starting point
- Re-apply filters and cross-checks
- Redisplay menu

When **[A] Advanced Elicitation** is selected:
- Ask deeper questions about emotional territory, customer language, or competitive distinction
- After elicitation, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Brand promise is max 15 words, passes all three filters, has documented rationale connecting to positioning and Golden Circle Why, aligns with Working Backwards

❌ **FAILURE:** Promise over 15 words, fails any filter, no documented rationale, contradicts Working Backwards PR headline or customer quote, sounds like tagline instead of strategic commitment
