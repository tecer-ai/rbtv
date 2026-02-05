---
name: 'step-04-adjustments'
description: 'Create context-specific tone adjustment matrix'
nextStepFile: './step-05-samples.md'
outputFile: '{outputFolder}/tone-of-voice.md'
---

# Step 4: Context Adjustments

**Progress: Step 4 of 6** — Next: Sample Copy

---

## STEP GOAL

Define how tone shifts by communication context while the core personality stays constant. The personality does not change — the intensity adjusts.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Ensure error/support context gets special attention — this is where brands most often fail. Same playful tone in error messages as marketing destroys trust.

### Step-Specific Rules
- All 5 contexts MUST have defined adjustments
- No adjustment can exceed +/- 1 from baseline
- 1-2 non-negotiable core dimensions MUST be identified
- Error/support context MUST address empathy and directness

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tone-of-voice.md` with Dimensions and Examples
2. Read `{outputFolder}/brand-prism.md` for Relationship facet (if exists)

---

## MANDATORY SEQUENCE

### 1. Present Five Communication Contexts

Define each context and reader's emotional state:

| Context | What It Includes | Reader Emotional State |
|---------|------------------|------------------------|
| **Marketing** | Website, ads, social posts | Distracted, skeptical — deciding whether to pay attention |
| **Onboarding** | Welcome flows, setup guides | Hopeful but uncertain — just committed, learning |
| **Error/Support** | Error messages, support responses | Frustrated, anxious — something went wrong |
| **Documentation** | Help docs, technical guides | Task-focused, impatient — needs specific info |
| **Social Media** | Posts, replies, community | Casual, open — in social environment |

### 2. Define Adjustment Principles

Explain adjustment approach:

> "For each context, we'll adjust dimensions +/- 1 from baseline. The personality doesn't transform — it modulates.
>
> - **+1** = Move one point toward right pole
> - **-1** = Move one point toward left pole
> - **0** = No change from baseline
>
> Maximum adjustment is +/- 1. Any more and you've changed who you are."

### 3. Create Context: Marketing

```markdown
### Context: Marketing (Website, Ads, Social Posts)

**Reader State:** Distracted, skeptical — earning attention is the goal

**Dimension Adjustments:**

| Dimension | Baseline | Adjustment | Context Position | Rationale |
|-----------|----------|------------|------------------|-----------|
| [Dim 1] | [N] | [+1/0/-1] | [Result] | [Why this shift] |
| [Dim 2] | [N] | [+1/0/-1] | [Result] | [Why this shift] |
| ... | | | | |

**Summary:** In marketing, we [1-sentence tone summary for this context].
```

### 4. Create Context: Onboarding

```markdown
### Context: Onboarding (Welcome Flows, Setup Guides)

**Reader State:** Hopeful but uncertain — building confidence

**Dimension Adjustments:**

| Dimension | Baseline | Adjustment | Context Position | Rationale |
|-----------|----------|------------|------------------|-----------|
| [Dim 1] | [N] | [+1/0/-1] | [Result] | [Why] |
| ... | | | | |

**Summary:** In onboarding, we [1-sentence tone summary].
```

### 5. Create Context: Error/Support (CRITICAL)

This context requires special attention:

```markdown
### Context: Error/Support (Error Messages, Help Responses)

**Reader State:** Frustrated, anxious — trust is at stake

**⚠️ CRITICAL CONTEXT: This is where brands most often fail. Same playful tone as marketing destroys trust.**

**Dimension Adjustments:**

| Dimension | Baseline | Adjustment | Context Position | Rationale |
|-----------|----------|------------|------------------|-----------|
| [Dim 1] | [N] | [+1/0/-1] | [Result] | [Why] |
| ... | | | | |

**Error/Support Specifics:**
- Empathy: [How we show we understand the frustration]
- Directness: [How we state what happened and what to do]
- Personality: [How much brand personality to retain vs. dial down]

**Summary:** In error/support, we [1-sentence summary emphasizing empathy + clarity].
```

### 6. Create Context: Documentation

```markdown
### Context: Documentation (Help Docs, Technical Guides)

**Reader State:** Task-focused, impatient — needs information fast

**Dimension Adjustments:**

| Dimension | Baseline | Adjustment | Context Position | Rationale |
|-----------|----------|------------|------------------|-----------|
| [Dim 1] | [N] | [+1/0/-1] | [Result] | [Why] |
| ... | | | | |

**Summary:** In documentation, we [1-sentence tone summary].
```

### 7. Create Context: Social Media

```markdown
### Context: Social Media (Posts, Replies, Community)

**Reader State:** Casual, open — social environment allows more personality

**Dimension Adjustments:**

| Dimension | Baseline | Adjustment | Context Position | Rationale |
|-----------|----------|------------|------------------|-----------|
| [Dim 1] | [N] | [+1/0/-1] | [Result] | [Why] |
| ... | | | | |

**Summary:** In social media, we [1-sentence tone summary].
```

### 8. Identify Non-Negotiable Core

Ask:

> "Which 1-2 dimensions should NEVER shift, regardless of context? These are your most defining traits."

```markdown
### Non-Negotiable Core

The following dimension(s) never adjust:

| Dimension | Position | Why Non-Negotiable |
|-----------|----------|-------------------|
| [Dimension] | [N] | [This is our most defining characteristic because...] |
| [Dimension] | [N] | [This is essential to who we are because...] |

Even in error messages and technical docs, we maintain [these dimensions] because [rationale].
```

### 9. Verify Relationship Facet Alignment

If Brand Prism exists, check Relationship facet:

> "Your Brand Prism defines the relationship as '[Relationship type]'. Do all context adjustments preserve this dynamic?"

For each context:
- Does the adjustment honor the relationship?
- Especially error/support — if relationship is "trusted advisor," does error tone maintain trust?

### 10. Compile Context Matrix

Create overview matrix:

```markdown
## Context-Tone Adjustment Matrix

### Overview

| Context | [Dim 1] | [Dim 2] | [Dim 3] | Summary |
|---------|---------|---------|---------|---------|
| Baseline | [N] | [N] | [N] | — |
| Marketing | [N+adj] | [N+adj] | [N+adj] | [Brief] |
| Onboarding | [N+adj] | [N+adj] | [N+adj] | [Brief] |
| Error/Support | [N+adj] | [N+adj] | [N+adj] | [Brief] |
| Documentation | [N+adj] | [N+adj] | [N+adj] | [Brief] |
| Social Media | [N+adj] | [N+adj] | [N+adj] | [Brief] |

### Non-Negotiable Core

[List dimensions that never shift]

### Context Details

[Full details from Sequences 3-7]
```

### 11. Update Output Document

Add Context Adjustments section to tone-of-voice.md.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-dimensions', 'step-03-examples', 'step-04-adjustments']
```

### 12. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine adjustments or add custom contexts
- **[C] Continue** — proceed to Sample Copy

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all 5 contexts have adjustments
2. Verify no adjustment exceeds +/- 1
3. Verify 1-2 non-negotiable core dimensions identified
4. Verify error/support explicitly addresses empathy and directness
5. Load `./step-05-samples.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 5 contexts defined, adjustments within +/- 1, non-negotiable core identified, error/support has empathy/directness guidance, relationship facet preserved

❌ **FAILURE:** Missing contexts, excessive adjustments, no core identified, error/support treated same as marketing, relationship broken by adjustments
