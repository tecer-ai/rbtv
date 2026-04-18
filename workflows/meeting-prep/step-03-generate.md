---
name: step-03-generate
description: Produce the cheat sheet using type-specific output skeleton and all gathered context
nextStepFile: null
---

# Step 3: Generate

**Progress: Step 3 of 3** — Final step

---

## STEP GOAL

Produce the cheat sheet using the type-specific output skeleton, all context from discovery, and any research performed. Present for review and resolve the output path.

---

## MANDATORY EXECUTION RULES

- NEVER generate without having completed discovery — if discovery feels incomplete, go back and ask
- ALWAYS use the output skeleton from the type data file as the structural guide
- ALWAYS write in the language the user has been using in the conversation
- NEVER pad sections with generic advice — every line must be specific to THIS meeting
- ALWAYS present the draft before writing to a file

---

## MANDATORY SEQUENCE

### 1. Generate the Cheat Sheet

Using the output skeleton from the type data file loaded in Step 1, produce the complete cheat sheet.

**Generation rules:**

| Rule | Detail |
|------|--------|
| Specificity | Every item must be specific to this meeting, this party, this context. No generic business advice. |
| Language match | Write in the language the user has been speaking. If the conversation was in Portuguese, the cheat sheet is in Portuguese. |
| Actionable | Every section must help the user DO something — prepare, say, avoid, decide. No background essays. |
| Honest calibration | The "what NOT to say" and calibration sections must be brutally honest. If the user is tempted to oversell, say so. |
| Skeleton adaptation | Include all sections from the output skeleton that have relevant content. Skip sections that don't apply (e.g., skip "Bad News Framing" in advisory if there's no bad news). Add sections not in the skeleton if the discovery revealed something that needs its own section. |
| Print-ready | The cheat sheet should work as a glance reference during the meeting — tables over paragraphs, direct language, no fluff. |

### 2. Present Draft

Present the complete cheat sheet draft in chat. Do NOT write to a file yet.

> Here's the draft cheat sheet. Review it — I'll adjust before saving.
>
> {complete cheat sheet}
>
> **Questions:**
> - Anything to add, remove, or change?
> - Any section that feels wrong or missing?

HALT. Wait for user feedback. Iterate until the user approves.

### 3. Resolve Output Path

After the user approves the content, determine where to save it.

Follow the `rbtv-output-resolution` rule:
1. Use conversation context to determine the destination — the meeting's project, area, and entity usually make the path obvious.
2. Read relevant CLAUDE.md files to understand folder structure and naming conventions.
3. Propose the full resolved path with reasoning.
4. Wait for confirmation.

**Filename convention:** `YYYY-MM-DD-{topic}-cheatsheet.md` — use the meeting date, not today's date. Inside entity folders (where the folder carries context), drop the entity name from the filename.

### 4. Write and Confirm

Write the approved cheat sheet to the confirmed path.

Report:

> **Cheat sheet saved:** `{full path}`
> **Meeting date:** {date}
> **Type:** {type}

---

## Step Menu

| Option | Action |
|--------|--------|
| [D] Done | Workflow complete |
| [X] Exit | Stop workflow |

HALT and WAIT for user input.
