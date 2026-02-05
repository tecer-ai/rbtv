---
name: 'step-02-brand-promise'
description: 'Distill positioning into single customer-facing brand promise'
nextStepFile: './step-03-key-messages.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 2: Define Brand Promise

**Progress: Step 2 of 6** — Next: Create Key Messages

---

## STEP GOAL

Distill the Brand Positioning Statement into a single, customer-facing brand promise (max 15 words) that combines emotional aspiration with rational mechanism.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The promise is NOT a tagline. It's the strategic anchor for all messaging. Reject anything that sounds like ad copy.

### Step-Specific Rules
- Promise MUST be one sentence, max 15 words
- Promise MUST connect to Golden Circle Why (emotional) AND Positioning benefit (rational)
- Promise MUST be customer-facing — not an internal strategy statement
- A competitor CANNOT claim the identical promise without modification

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/messaging-architecture.md` from Step 1
2. Load upstream framework outputs:
   - Brand Positioning Statement (the "that [benefit]" clause)
   - Golden Circle Why statement
   - Working Backwards PR headline and customer quote

---

## MANDATORY SEQUENCE

### 1. Extract Promise Ingredients

From Brand Positioning:
- Identify the **core benefit claim** — the "that [key benefit]" clause
- This is the rational foundation

From Golden Circle:
- Identify the **Why statement**
- Note the emotional register: what belief or cause does the brand champion?
- This is the emotional foundation

Present both:
> "**Rational foundation (Positioning benefit):**
> [benefit clause]
>
> **Emotional foundation (Golden Circle Why):**
> [Why statement]"

### 2. Draft Brand Promise

Combine rational and emotional into a single sentence using one of these structures:

**Structure A:** "[Emotional aspiration] through [rational mechanism]"
**Structure B:** "[What changes for you] because [why we exist]"

Draft 2-3 variations:

```markdown
**Draft Variations:**

1. "[Draft 1]"
   - Emotional hook: [Which part]
   - Rational mechanism: [Which part]

2. "[Draft 2]"
   - Emotional hook: [Which part]
   - Rational mechanism: [Which part]

3. "[Draft 3]"
   - Emotional hook: [Which part]
   - Rational mechanism: [Which part]
```

Present drafts to user for feedback.

### 3. Apply Quality Filters

Test each draft against three filters:

**Filter 1: Customer-facing**
- Would a real customer nod and say "yes, that's what I want"?
- If it sounds like an internal strategy statement, FAIL

**Filter 2: Emotionally resonant**
- Does it connect to a feeling (confidence, relief, pride, control)?
- If it reads like a spec sheet, FAIL

**Filter 3: Differentiated**
- Could a competitor claim the exact same promise without changing a word?
- If yes, sharpen using positioning's competitive frame

Present filter results:

```markdown
| Draft | Customer-facing | Emotionally Resonant | Differentiated | Pass/Fail |
|-------|-----------------|---------------------|----------------|-----------|
| 1 | [Yes/No + why] | [Yes/No + why] | [Yes/No + why] | [Pass/Fail] |
| 2 | [Yes/No + why] | [Yes/No + why] | [Yes/No + why] | [Pass/Fail] |
| 3 | [Yes/No + why] | [Yes/No + why] | [Yes/No + why] | [Pass/Fail] |
```

### 4. Cross-Check Against Working Backwards

Compare best draft(s) to:
- Working Backwards PR headline
- Working Backwards customer quote

> "**Consistency check:**
> - PR headline: [headline]
> - Customer quote: [quote]
> - Draft promise: [promise]
>
> Do they reinforce each other? [Yes/No + analysis]"

If contradiction found, reconcile before proceeding.

### 5. Select and Document Final Promise

With user confirmation, select the final promise:

```markdown
## Brand Promise

**Promise:** "[Final promise statement — max 15 words]"

### Rationale

**Emotional connection (from Golden Circle Why):**
[How promise connects to Why]

**Rational foundation (from Positioning):**
[How promise connects to benefit clause]

**Differentiation:**
[Why competitor cannot claim this verbatim]

**Working Backwards alignment:**
- PR headline reinforces: [How]
- Customer quote echoes: [How]
```

Update messaging-architecture.md with this section.

### 6. Update Output Document

Update messaging-architecture.md frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise']
```

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine promise further
- **[C] Continue** — proceed to Create Key Messages

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Brand Promise section is complete
2. Verify frontmatter updated
3. Load `./step-03-key-messages.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Promise is one sentence ≤15 words, connects to both Why and Positioning, passes all 3 filters, aligns with Working Backwards

❌ **FAILURE:** Promise is vague tagline, exceeds 15 words, sounds like internal strategy, competitor could claim verbatim
