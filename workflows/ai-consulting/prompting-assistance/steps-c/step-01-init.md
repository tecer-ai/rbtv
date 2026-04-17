---
stepNumber: 1
stepId: init
nextStepFile: ./step-02-discover.md
---

# Step 1: Initialize Prompting Assistance

**Goal:** Understand the user's prompting goal and identify relevant knowledge to load.

---

## MANDATORY SEQUENCE

### 1. Load Knowledge Index

Load `data/knowledge-index.csv` to understand available knowledge.

### 2. Context Capture

Ask the user about their prompting needs:

> "What are you trying to accomplish with your prompt? Tell me about:
> - **The task:** What should the AI do?
> - **The model (if known):** Which AI will execute this?
> - **Current challenges:** What's not working with existing attempts?"

### 3. Initial Assessment

After user responds, assess:

| Dimension | Question | Note |
|-----------|----------|------|
| **Task Type** | Code generation, analysis, creative, structured output, etc.? | Guides technique selection |
| **Model** | Specific model or model family? | Determines which ai_model file to load |
| **Problem Type** | Context management, reasoning, structure, safety, iteration? | Guides technique selection |
| **Complexity** | Simple prompt or multi-turn/agentic? | Affects approach |

### 4. Identify Knowledge to Load

Based on assessment, identify which files to load in Step 2:

**Model File Selection:**
- If user specifies model → load that model's file
- If model unknown → recommend based on task type

**Platform Knowledge Selection:**
- If user will use Claude Projects → load claude_projects
- If user will use ChatGPT Projects → load chatgpt_projects
- If setting up persistent workspace → recommend platform knowledge

**Technique Selection:**
Match problem type to techniques:

| Problem Type | Recommended Techniques |
|--------------|------------------------|
| Reasoning/Logic | chain_of_thought, task_decomposition |
| Format/Structure | structured_outputs, xml_tag_structure |
| Context/Memory | context_management, rag_context |
| Safety | safety_guardrails |
| Iteration | iterative_refinement |
| Examples needed | few_shot_learning |
| Agent/Multi-step | multi_agent, task_decomposition |
| Platform setup | (load relevant platform_knowledge) |

### 5. Present Recommendations

> "Based on what you've shared, I recommend loading:
>
> **Model Knowledge:**
> - {model_name} — {reason}
>
> **Platform Knowledge:** (if applicable)
> - {platform_name} — {reason}
>
> **Techniques:**
> - {technique_1} — {reason}
> - {technique_2} — {reason}
>
> Should I proceed with these, or would you like to add/change anything?"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Load selected knowledge and proceed to deep discovery |
| **[M] Change Model** | Select different AI model |
| **[P] Add Platform** | Add platform knowledge (Claude Projects, ChatGPT Projects) |
| **[T] Add Technique** | Add additional prompting technique |
| **[L] List All** | Show all available models, platforms, and techniques |
| **[Q] Questions** | User has questions about the options |

---

## ON LIST ALL

Display contents of knowledge-index.csv organized by type:

**Available AI Models:**
{list from index where type=ai_model}

**Available Platform Knowledge:**
{list from index where type=platform}

**Available Prompting Techniques:**
{list from index where type=technique, grouped by tags}

---

## ON CONTINUE

1. Note which model and technique files to load in Step 2
2. Load `./step-02-discover.md`
