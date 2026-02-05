---
name: 'step-03-examples'
description: 'Write do/don''t example pairs for each dimension'
nextStepFile: './step-04-adjustments.md'
outputFile: '{outputFolder}/tone-of-voice.md'
---

# Step 3: Do/Don't Examples

**Progress: Step 3 of 6** — Next: Context Adjustments

---

## STEP GOAL

For each tone dimension, produce 3 pairs of do/don't examples using real brand scenarios to show what the tone sounds like in practice.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject generic placeholder examples. Every example must use actual brand terminology and feel like real copy.

### Step-Specific Rules
- EXACTLY 3 do/don't pairs per dimension (not fewer)
- MUST use 4 brand scenarios: welcome email, error message, feature announcement, support response
- Each pair must have one-line explanation citing dimension position
- All 4 scenarios must appear at least twice across all examples

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tone-of-voice.md` with Tone Dimensions
2. Read `{outputFolder}/messaging-architecture.md` for key messages (if exists)
3. Have brand product/service name and terminology available

---

## MANDATORY SEQUENCE

### 1. Review Dimensions and Scenarios

Display dimensions with positions:

| Dimension | Position | Brief Meaning |
|-----------|----------|---------------|
| [1] | [N]/5 | [What this sounds like] |
| [2] | [N]/5 | [What this sounds like] |
| ... | | |

Display four brand scenarios:

| Scenario | Context | Reader State | Use For |
|----------|---------|--------------|---------|
| **Welcome Email** | First post-signup message | Hopeful, uncertain | Tone at its warmest |
| **Error Message** | Something went wrong | Frustrated, anxious | Tone under pressure |
| **Feature Announcement** | New capability shipped | Curious, busy | Tone showing enthusiasm |
| **Support Response** | Customer needs help | Seeking resolution | Tone being helpful |

### 2. Create Scenario Coverage Matrix

Plan which scenarios to use for which dimensions:

| Dimension | Pair 1 Scenario | Pair 2 Scenario | Pair 3 Scenario |
|-----------|-----------------|-----------------|-----------------|
| [Dimension 1] | [Scenario] | [Scenario] | [Scenario] |
| [Dimension 2] | [Scenario] | [Scenario] | [Scenario] |
| ... | | | |

> "Let me distribute scenarios across dimensions. Each scenario should appear at least twice total."

### 3. Write Examples for Dimension 1

For the first dimension:

```markdown
### [Dimension 1]: [Left Pole] ↔ [Right Pole] — Position: [N]/5

**Pair 1: [Scenario]**

✅ **DO:** "[Example copy that matches our position]"

❌ **DON'T:** "[Same content expressed at wrong position]"

*Why:* The DO version is [position characteristic], while the DON'T version [violates our position because].

---

**Pair 2: [Scenario]**

✅ **DO:** "[Example copy]"

❌ **DON'T:** "[Counter-example]"

*Why:* [Explanation citing dimension position]

---

**Pair 3: [Scenario]**

✅ **DO:** "[Example copy]"

❌ **DON'T:** "[Counter-example]"

*Why:* [Explanation citing dimension position]
```

Present and get feedback before proceeding to next dimension.

### 4. Write Examples for Remaining Dimensions

Repeat Sequence 3 for each dimension.

For each dimension, verify:
- 3 pairs created
- Different scenarios used than previous dimensions (when possible)
- Explanations reference dimension position specifically

### 5. Quality Check: Brand Specificity

Review all examples and ask:

> "Looking at your DO examples: Could these be copy for ANY brand, or are they specific to [Brand Name]?"

For any generic examples:
- Add brand product name
- Use brand-specific terminology
- Reference actual features or benefits

### 6. Quality Check: Scenario Coverage

Verify coverage:

| Scenario | Times Used | Dimensions |
|----------|------------|------------|
| Welcome Email | [N] | [List] |
| Error Message | [N] | [List] |
| Feature Announcement | [N] | [List] |
| Support Response | [N] | [List] |

Each scenario must appear at least 2 times. If not, revise distribution.

### 7. Quality Check: Trainability

Ask:

> "If a new writer read ONLY these examples (no other context), could they write on-brand copy for a different scenario?"

If no:
- Add more examples
- Sharpen explanations
- Include more variety within each dimension

### 8. Compile All Examples

Organize by dimension:

```markdown
## Do/Don't Examples

### Scenario Coverage

| Scenario | Appearances |
|----------|-------------|
| Welcome Email | [N] times |
| Error Message | [N] times |
| Feature Announcement | [N] times |
| Support Response | [N] times |

### [Dimension 1]: [Name]

[3 pairs with explanations]

### [Dimension 2]: [Name]

[3 pairs with explanations]

[Continue for all dimensions...]
```

### 9. Update Output Document

Add Do/Don't Examples section to tone-of-voice.md.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-dimensions', 'step-03-examples']
```

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — add more examples or refine existing ones
- **[C] Continue** — proceed to Context Adjustments

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify 3 pairs per dimension (exactly)
2. Verify all 4 scenarios appear at least twice
3. Verify examples use brand-specific language
4. Load `./step-04-adjustments.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 3 pairs per dimension, all scenarios used 2+ times, brand-specific copy, explanations cite positions, trainable by new writer

❌ **FAILURE:** Fewer than 3 pairs, missing scenarios, generic placeholder copy, no explanations, examples feel disconnected from brand
