---
stepNumber: 3
stepId: generate
nextStepFile: './step-04-refine.md'
outputFile: '{output_folder}/ai-web-projects/{projectName}/project-brief.md'
promptingKnowledgePath: '{project-root}/_bmad/rbtv/workflows/prompting-assistance/data'
---

# Step 3: Generate

**Goal:** Generate the project's `instructions.md` and any companion files identified in Step 2.

---

## MANDATORY SEQUENCE

### 1. Load Platform and Model Knowledge

From `{promptingKnowledgePath}`:

1. Read `knowledge-index.csv` to find relevant files
2. Load the platform knowledge file matching the selected platform:
   - ChatGPT → `platform_knowledge/chatgpt_projects.md`
   - Claude → `platform_knowledge/claude_projects.md`
   - Gemini → skip if file doesn't exist (use framework knowledge from Step 2)
3. Load the AI model knowledge file for the platform's default model (if available)
4. Load 1-3 relevant prompting technique files based on the use case:
   - Conversational assistant → `identity_locking.md`, `eagerness_control.md`
   - Data/analysis → `structured_outputs.md`, `structured_prompting.md`
   - Teaching/coaching → `chain_of_thought.md`, `few_shot_learning.md`
   - Creative/writing → `system_prompting.md`, `scope_delimitation.md`

### 2. Generate `instructions.md`

Craft the system prompt following these principles:

**Structure:**
1. **Identity** — Who is this assistant? Role, personality, communication style
2. **Core task** — What does it DO? Primary function in one sentence
3. **Behavior rules** — Mandatory constraints, guardrails, output format
4. **Knowledge context** — What it knows, what it references, what it must NOT assume
5. **Interaction pattern** — How it handles conversation flow (greetings, follow-ups, edge cases)

**Platform-specific adaptations:**
- **ChatGPT**: Respect 8K char limit for Custom GPTs; use concise, direct language; leverage memory references
- **Claude**: Can be longer and more structured; use XML tags for section boundaries; reference project files explicitly
- **Gemini**: Keep instructions focused; note Google Search grounding availability; reference uploaded files
- **Manus**: Frame instructions as task goals and expected deliverables; specify autonomous behavior; define what "done" looks like; include quality criteria for self-verification

**Quality criteria:**
- Every instruction must be unambiguous — the AI will follow it literally
- Include explicit "NEVER" rules for common failure modes
- Include at least one example interaction if the behavior is nuanced
- Match the tone/personality discovered in Step 2

Write `instructions.md` to `{output_folder}/ai-web-projects/{projectName}/instructions.md`.

### 3. Generate Companion Files

For each companion file identified in Step 2:

1. Discuss the file's content with the user — what goes in it?
2. Generate the file with appropriate structure
3. Write to `{output_folder}/ai-web-projects/{projectName}/{filename}`

If the user needs to provide source data (e.g., meeting transcripts, financial data), create a placeholder file with clear instructions on what to paste.

### 4. Update Project Brief

Update `{outputFile}`:
- Update the **Generated Files** table with all files created (name + purpose)
- Update `stepsCompleted` — add `"step-03-generate"`

### 5. Present Output Summary

> "Here's what I've created for **{projectName}**:"

List each file with a one-line description and its path.

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 4: Refine |
| **[V] View** | Display the full contents of any generated file |
| **[X] Exit** | Save state, exit workflow |

## ON VIEW

Ask which file to display. Show its full contents. Redisplay this menu.
