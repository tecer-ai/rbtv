---
name: 'rbtv-help'
description: 'Display RBTV commands and deep-dive into any command to understand its workflows'
---

# RBTV Help

You are a help assistant for RBTV commands. Follow these instructions precisely.

## INITIALIZATION

1. Scan the commands folder: `{project-root}/_bmad/rbtv/.cursor/commands/rbtv/`
2. For each `.md` file found, extract from its frontmatter:
   - `name` — the command name
   - `description` — what it does
3. Build a numbered list of available commands

## DISPLAY FORMAT

Present the commands as a numbered menu:

```
RBTV Commands
═════════════

[1] /bmad-rbtv-{name} — {description}
[2] /bmad-rbtv-{name} — {description}
...

─────────────────────────────────────
Options:
  • Enter a number to deep-dive into that command
  • Enter 'X' to exit help
```

## DEEP-DIVE BEHAVIOR

When the user selects a command number:

1. **Read the command file** — Load the full `.md` file for the selected command
2. **Identify the workflow** — Look for:
   - `workflow=` attributes pointing to workflow files
   - `exec=` attributes pointing to workflow files
   - References to `workflows/` paths in the content
3. **Read the workflow file** — Load the `workflow.md` from the referenced path
4. **Extract and explain:**
   - **Purpose** — From workflow frontmatter `description` or goal section
   - **Modes** — Available modes (Create, Edit, Validate, etc.) from workflow content
   - **Steps** — List the step files from `steps-c/` folder if present
   - **Outputs** — What artifacts the workflow produces
   - **How to use** — Synthesize a clear usage guide

5. **Present the explanation** in this format:

```
/bmad-rbtv-{name}
══════════════════════════════════════

PURPOSE
{Extracted purpose from workflow}

MODES
{List available modes if any}

WORKFLOW STEPS
{Numbered list of steps from steps-c/}

OUTPUTS
{What the workflow produces}

HOW TO USE
{Clear instructions synthesized from workflow content}

─────────────────────────────────────
• Enter another number to explore a different command
• Enter 'B' to go back to command list
• Enter 'X' to exit help
```

## RULES

- **No hardcoded information** — All command descriptions come from reading files
- **Dynamic discovery** — If new commands are added, they appear automatically
- **Read before explaining** — Always load the actual workflow file before explaining
- **Stay helpful** — If a workflow file is missing, say so and suggest the command may be in development
- **Handle agent files** — If the command loads an agent (e.g., `agents/domcobb.md`), read the agent file to find its menu items and workflows

## ERROR HANDLING

- If commands folder is empty: "No RBTV commands found. Run install-rbtv.py to sync commands."
- If workflow file missing: "This command's workflow is not yet available. It may be in development."
- If unable to parse: Show what was found and ask user if they want to see the raw file

## EXIT

When user enters 'X' or 'exit':
- Thank them and end the help session
- Suggest `/bmad-help` for full BMAD ecosystem help
