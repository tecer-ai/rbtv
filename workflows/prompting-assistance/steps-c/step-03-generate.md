---
stepNumber: 3
stepId: generate
nextStepFile: ./step-04-refine.md
---

# Step 3: Generate Prompt

**Goal:** Create the prompt applying all gathered knowledge and requirements.

---

## MANDATORY SEQUENCE

### 1. Apply Technique Patterns

For each technique in the specification, apply its "Application Pattern":

| Technique | Application |
|-----------|-------------|
| {technique_1} | {how it shapes the prompt} |
| {technique_2} | {how it shapes the prompt} |

### 2. Draft Prompt

Generate the complete prompt, structured appropriately:

**For system prompts:**
```
[Role/Identity section]
[Task description]
[Constraints and requirements]
[Output format specification]
[Examples if using few-shot]
```

**For user prompts:**
```
[Context/background]
[Specific request]
[Input data/content]
[Output expectations]
```

### 3. Annotate the Prompt

Add inline annotations explaining WHY each section exists:

```markdown
## Generated Prompt

### System Prompt
```
{prompt text}
```

**Annotations:**
- Lines 1-3: {purpose — e.g., "Role definition using identity-locking technique"}
- Lines 4-6: {purpose — e.g., "Task specification with explicit constraints"}
- Lines 7-10: {purpose — e.g., "Output format using structured_outputs pattern"}

### User Prompt Template
```
{prompt template with placeholders}
```

**Placeholders:**
- `{input}`: {what goes here}
- `{context}`: {what goes here}
```

### 4. Apply Quality Checklist

Run through the quality checklist from each loaded technique:

| Check | Status | Notes |
|-------|--------|-------|
| {check from technique_1} | ✅/❌ | {notes} |
| {check from technique_2} | ✅/❌ | {notes} |
| {model-specific check} | ✅/❌ | {notes} |

### 5. Present Draft

> "Here's your generated prompt with annotations:
>
> {formatted prompt with annotations}
>
> **Quality Check Results:**
> - {summary of checklist}
>
> Would you like to test it, refine it, or proceed to finalization?"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to refinement options |
| **[T] Test** | User will test the prompt and report back |
| **[R] Revise** | Modify specific sections |
| **[V] Variations** | Generate alternative versions |
| **[S] Simplify** | Remove complexity, make more concise |

---

## ON TEST

> "Go ahead and test the prompt. When you return, tell me:
> - What worked well?
> - What didn't work as expected?
> - Any specific issues to address?"

Wait for user to return with feedback, then offer refinement options.

---

## ON VARIATIONS

Generate 2-3 alternative versions with different approaches:
- Version A: More concise
- Version B: More detailed/explicit
- Version C: Different technique emphasis

---

## ON CONTINUE

1. Confirm prompt is ready for finalization
2. Load `./step-04-refine.md`
