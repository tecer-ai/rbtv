---
stepNumber: 1
stepId: init
nextStepFile: './step-02-discover.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{output_folder}/ai-web-projects/{projectName}/project-brief.md'
templateFile: '../templates/ai-web-project-template.md'
---

# Step 1: Initialize

**Goal:** Check for existing project or create a new project brief.

---

## MANDATORY SEQUENCE

### 1. Check for Existing Project

Ask the user: "Do you have an existing AI Web Project you want to continue working on, or are we starting fresh?"

- If **continuing**: Load `{continueStepFile}` immediately. Do NOT proceed with the rest of this step.
- If **starting fresh**: Continue to step 2.

### 2. Gather Minimum Context

Ask the user for a project name — this will be used as the folder name.

- Must be lowercase, kebab-case (e.g., `daily-journal`, `investment-analyst`, `meeting-summarizer`)
- If the user provides a natural language name, convert it to kebab-case and confirm

### 3. Create Output Directory and Brief

1. Create folder: `{output_folder}/ai-web-projects/{projectName}/`
2. Copy `{templateFile}` to `{output_folder}/ai-web-projects/{projectName}/project-brief.md`
3. Update frontmatter:
   - `projectName: {user's project name}`
   - `created: {current date}`
   - `stepsCompleted: ["step-01-init"]`

### 4. Confirm and Present Menu

> "Project **{projectName}** initialized. I've created your project brief at `{outputFile}`. Next, we'll discover what this assistant needs to do and pick the right platform."

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 2: Discover |
| **[X] Exit** | Save state, exit workflow |
