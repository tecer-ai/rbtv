---
name: add-prompting-knowledge
description: Create new AI model or prompting technique documentation
nextStep: null
---

# Add Prompting Knowledge

**Goal:** Route to the RBTV Builder to create a new AI model guide or prompting technique document.

---

## WORKFLOW OVERVIEW

This is a thin routing workflow that:
1. Asks user what type of knowledge to create (ai_model or prompting_technique)
2. Routes to the RBTV Builder with the appropriate template pre-selected

---

## MANDATORY SEQUENCE

### 1. Determine Knowledge Type

Ask the user:

> "What type of prompting knowledge do you want to document?
>
> **[M] AI Model Guide** — Document model-specific prompting deltas (e.g., Claude, GPT-5, Gemini)
> - When to use: You've learned how a specific model behaves differently and want to capture that knowledge
>
> **[T] Prompting Technique** — Document a reusable prompting pattern (e.g., chain-of-thought, few-shot)
> - When to use: You've discovered a technique that solves a specific problem across models
>
> **[P] Platform Knowledge** — Document platform interface guidance (e.g., Claude Projects, ChatGPT Projects)
> - When to use: You need to guide users through a specific platform's features and workflows
>
> Which would you like to create?"

### 2. Present Template Preview

Based on selection, show template structure:

**For AI Model:**
> "An AI Model guide documents **prompting deltas** — how to adjust techniques for a specific model. It includes:
> - Characteristics (context window, strengths, weaknesses)
> - Use cases (ideal for / avoid for)
> - Model-specific techniques
> - Pitfalls unique to this model
> - Examples showing model-specific behavior
>
> Ready to create?"

**For Prompting Technique:**
> "A Prompting Technique documents a **reusable pattern** for structuring prompts. It includes:
> - Problem it solves (140 chars)
> - When to apply / when to avoid
> - Application pattern (step-by-step)
> - Pitfalls and solutions
> - Before/after examples with measurable results
>
> Ready to create?"

**For Platform Knowledge:**
> "A Platform Knowledge document guides users through **platform interface features**. It includes:
> - Interface overview (UI components, navigation)
> - Core capabilities and use cases
> - Integrated tools (file sources, external connections)
> - User actions (step-by-step procedures)
> - AI agent guidance patterns
> - Limitations and context management
> - Common pitfalls
>
> Ready to create?"

### 3. Route to Builder

Load the RBTV Builder agent with context:

```
Route to: {project-root}/_bmad/rbtv/agents/god.md

Pre-select: [CK] Create Knowledge

Context to pass:
- Knowledge type: {ai_model | prompting_technique | platform_knowledge}
- Template source: {robotville template path}
- Output location: {project-root}/_bmad/rbtv/workflows/prompting-assistance/data/{ai_models|prompting_techniques|platform_knowledge}/
```

**Template Sources:**
- AI Model: `{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/ai_model.md`
- Prompting Technique: `{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/prompting_technique.md`
- Platform Knowledge: `{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/platform_knowledge.md`

### 4. Update Knowledge Index

After Builder creates the document, remind user:

> "Don't forget to update the knowledge index! Add a row to:
> `{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/knowledge-index.csv`
>
> Format:
> `{id},{type},{name},{path},{tags},{description}`"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[M] AI Model** | Create AI model guide |
| **[T] Technique** | Create prompting technique |
| **[P] Platform** | Create platform knowledge |
| **[B] Back** | Return to domcobb agent menu |

---

## ON SELECTION

Route to Builder with appropriate context.
