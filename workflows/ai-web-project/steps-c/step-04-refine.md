---
stepNumber: 4
stepId: refine
nextStepFile: null
outputFile: '{output_folder}/ai-web-projects/{projectName}/project-brief.md'
---

# Step 4: Refine

**Goal:** Review, test, and iterate on the generated project until the user is satisfied.

---

## MANDATORY SEQUENCE

### 1. Present Review Checklist

Show the user this checklist for their `instructions.md`:

| # | Check | Question |
|---|-------|----------|
| 1 | **Identity** | Does the assistant know who it is? Is the personality clear? |
| 2 | **Core task** | Is the primary function unambiguous? |
| 3 | **Guardrails** | Are there explicit "NEVER" rules for common failures? |
| 4 | **Output format** | Does it know HOW to respond? (length, structure, tone) |
| 5 | **Edge cases** | What happens with off-topic requests, ambiguous input, missing data? |
| 6 | **Examples** | Are there example interactions for nuanced behavior? |
| 7 | **Platform fit** | Does the prompt reference platform files correctly? (Length is not a concern — instructions.md is uploaded as a companion file.) |

### 2. Solicit Feedback

Ask: "Read through the checklist. Anything you want to change, add, or test?"

### 3. Iterate

For each change requested:
1. Discuss the change — why and how
2. Apply the edit to the relevant file
3. Show the updated section (not the full file unless asked)
4. Ask: "Anything else, or are we good?"

Loop until the user confirms satisfaction.

### 4. Finalize

When the user is satisfied:

1. Update `{outputFile}` frontmatter:
   - `status: complete`
   - Add `"step-04-refine"` to `stepsCompleted`

2. Present deployment instructions based on platform:

**Universal step (all platforms):** Upload `instructions.md` as a companion/knowledge file. In the platform's native Instructions field, enter only: "Follow instructions.md for all behavior, rules, and workflow logic."

**ChatGPT:**
> 1. Go to chatgpt.com → Projects (or Custom GPTs)
> 2. Create new project/GPT
> 3. In the Instructions field, enter: "Follow instructions.md for all behavior, rules, and workflow logic."
> 4. Upload `instructions.md` and any other companion files
> 5. Test with a sample conversation

**Claude:**
> 1. Go to claude.ai → Projects
> 2. Create new project
> 3. In Project Instructions, enter: "Follow instructions.md for all behavior, rules, and workflow logic."
> 4. Upload `instructions.md` and any other companion files to Project Knowledge
> 5. Test with a sample conversation

**Gemini:**
> 1. Go to gemini.google.com → Gems
> 2. Create new Gem
> 3. In the Instructions field, enter: "Follow instructions.md for all behavior, rules, and workflow logic."
> 4. Upload `instructions.md` and any other companion files
> 5. Test with a sample conversation

**Manus:**
> 1. Go to manus.im → Projects
> 2. Create new project
> 3. In master instructions, enter: "Follow instructions.md for all behavior, rules, and workflow logic."
> 4. Upload `instructions.md` and any other companion files to the project knowledge base
> 5. Create a test task to verify behavior

3. Remind the user:

> "Your project files are at `{output_folder}/ai-web-projects/{projectName}/`. Move them to your preferred permanent location if needed."

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[E] Edit** | Make another change to any file |
| **[D] Done** | Finalize and exit workflow |
| **[X] Exit** | Save state without finalizing (can resume later) |

## ON EDIT

Ask which file and what change. Apply, show diff. Redisplay this menu.
