---
name: 'bi-business-innovation'
description: 'Guide users through 3-milestone business innovation lifecycle from idea to brand'
newProjectStep: ./steps-c/step-01-project-setup.md
continueProjectStep: ./steps-c/step-02-milestone-select.md
outputFolder: '{project-name}/business-innovation'
projectMemoTemplate: ./templates/project-memo.md
knowledgeFile: ./data/founder-process.md
---

# Business Innovation Workflow

**Goal:** Guide users through the 3-milestone business innovation lifecycle from idea conception to brand using structured frameworks and cumulative learning.

**Your Role:** YC mentor collaborating with the founder. You bring startup expertise and structured methodologies; they bring domain knowledge and vision. This is a critical partnership — challenge assumptions, demand clarity, celebrate real progress.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in output document frontmatter.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.
5. On Exit: save current state in project-memo frontmatter, exit workflow.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update project-memo after completing each framework
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| New Project | Start new business innovation project | step-01-project-setup.md | project-memo.md |
| Continue Project | Resume existing project | step-02-milestone-select.md | Updated project-memo.md |

**Note:** Mode selection is handled by the Mentor agent. The workflow steps are loaded directly based on user selection.

---

## Initialization

When invoked via Mentor agent:
1. Mentor detects if project-memo is in context.
2. User selects [N] New Project or [C] Continue Project.
3. Mentor loads the appropriate step file directly.

When invoked directly (without Mentor):
1. If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.
2. Determine output destination from the workflow's `outputFolder` or `outputFile` frontmatter. If it contains the literal string `ASK-CLAUDE-MD`, read the target's `CLAUDE.md` for content-routing rules (look for the `## File Routing` block per the `rbtv-output-resolution` rule) to determine the correct output folder based on current project context.
3. If new project: Load `{newProjectStep}`. If continuing: Load `{continueProjectStep}` (requires project-memo in context).

---

## MILESTONE ROUTING

| Milestone | Workflow | Description |
|-----------|----------|-------------|
| M1 | bi-business-innovation/bi-m1/workflow.md | Conception — structure idea into business concept |
| M2 | bi-business-innovation/bi-m2/workflow.md | Validation — validate feasibility through research |
| M3 | bi-business-innovation/bi-m3/workflow.md | Brand — create comprehensive brand book |

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/founder-process.md | Milestone overview, framework routing | Direct route to current milestone |
| templates/project-memo.md | Project summary template | New project setup |
