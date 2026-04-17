---
stepNumber: 4
stepId: refine
nextStepFile: null
---

# Step 4: Refine & Finalize

**Goal:** Iterate on the prompt based on feedback and deliver final version.

---

## MANDATORY SEQUENCE

### 1. Refinement Loop

If user has tested the prompt:

> "Based on your feedback, I'll adjust the prompt. What specifically needs to change?
> - Output format issues?
> - Missing context?
> - Wrong tone/style?
> - Not following instructions?"

Apply targeted fixes based on feedback.

### 2. Iteration Best Practices

When refining, follow iterative_refinement principles:

| Issue Type | Refinement Approach |
|------------|---------------------|
| Output format wrong | Add explicit format specification, use structured_outputs |
| Missing details | Add more context or examples (few_shot) |
| Over-verbose | Add length constraints, "be concise" |
| Under-verbose | Remove constraints, ask for "detailed" |
| Wrong tone | Add explicit tone guidance in system prompt |
| Hallucinations | Add grounding, citations requirements |
| Not following instructions | Strengthen instruction language, add emphasis |

### 3. Final Version

Present the refined prompt:

```markdown
## Final Prompt

### System Prompt
```
{final system prompt}
```

### User Prompt Template
```
{final user prompt template}
```

### Usage Notes
- **Model:** {target model}
- **Techniques Applied:** {list}
- **Key Constraints:** {list}

### Tips for Use
- {tip_1}
- {tip_2}
```

### 4. Deliver Summary

> "**Prompting Assistance Complete**
>
> **Your prompt uses:**
> - {technique_1} for {purpose}
> - {technique_2} for {purpose}
>
> **Optimized for:** {model}
>
> **Copy the prompt above and use it with {model}. Remember:**
> - {key reminder}
> - {key reminder}"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[I] Iterate** | Continue refining based on new test results |
| **[E] Export** | Copy final prompt to clipboard |
| **[S] Save** | Save prompt to a file |
| **[AK] Add Knowledge** | Document this as a new technique |
| **[N] New Prompt** | Start fresh with a different task |
| **[D] Done** | Return to domcobb agent menu |

---

## ON ADD KNOWLEDGE

If the user discovered a useful pattern worth documenting:

> "If you've discovered a reusable prompting pattern, we can document it. I'll route you to the Add Knowledge workflow."

Route to: `{project-root}/_bmad/rbtv/agents/ana/agents/ana/workflows/add-prompting-knowledge/workflow.md`

---

## ON DONE

Return control to the domcobb agent menu.
