---
stepNumber: 2
stepId: discover
nextStepFile: ./step-03-generate.md
---

# Step 2: Deep Discovery & Knowledge Application

**Goal:** Load relevant knowledge files and gather detailed requirements for prompt generation.

---

## MANDATORY SEQUENCE

### 1. Load Knowledge Files

Load the model and technique files identified in Step 1:

**For each file:**
- Read the full file
- Extract key patterns, pitfalls, and application guidance
- Note model-specific requirements

### 2. Present Key Insights

Share relevant insights from loaded knowledge:

> "From the {model_name} documentation, key points for your use case:
> - {insight_1}
> - {insight_2}
>
> From {technique_name}, the application pattern is:
> - {step_1}
> - {step_2}"

### 3. Deep Discovery Questions

Ask targeted questions based on loaded knowledge:

**Task-Specific Questions:**
- What input will you provide? (text, images, code, data?)
- What output format do you need? (prose, JSON, code, structured?)
- What constraints apply? (length, style, terminology?)

**Model-Specific Questions:**
- {Questions derived from model file's "When to Apply" section}

**Technique-Specific Questions:**
- {Questions derived from technique file's "Application Pattern" section}

### 4. Identify Anti-Patterns to Avoid

From the loaded knowledge, identify relevant pitfalls:

> "Based on your requirements, watch out for these common mistakes:
> - {pitfall_1} — {why it fails}
> - {pitfall_2} — {why it fails}"

### 5. Synthesize Requirements

Create a prompt specification:

```markdown
## Prompt Specification

**Target Model:** {model}
**Task Type:** {type}

### Input
- Format: {input format}
- Content: {what user will provide}

### Output
- Format: {output format}
- Structure: {any required structure}
- Constraints: {length, style, etc.}

### Techniques to Apply
1. {technique_1} — {how it will be used}
2. {technique_2} — {how it will be used}

### Pitfalls to Avoid
- {pitfall_1}
- {pitfall_2}
```

Present specification to user for confirmation.

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to generate the prompt |
| **[R] Revise** | Modify the specification |
| **[MK] More Knowledge** | Load additional technique files |
| **[E] Examples** | See examples from loaded technique files |
| **[Q] Questions** | User has questions |

---

## ON EXAMPLES

Extract and present examples from the loaded technique files' Examples section.

---

## ON CONTINUE

1. Confirm specification is complete
2. Load `./step-03-generate.md`
