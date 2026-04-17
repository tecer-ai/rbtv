---
name: meeting-summarizer
description: 'Summarize meeting transcripts for any project - detects project and meeting type, routes to the appropriate prompt, fixes filenames, and saves output. Use when processing any meeting transcript.'
---

# Meeting Summarizer

**Purpose:** Process a meeting transcript end-to-end: detect project, classify type, rename, move, and summarize using the appropriate prompt.

**When to use:**
- User references a meeting transcript and wants it summarized
- User has a new transcript to process
- User mentions meeting debrief, meeting summary, or meeting notes

---

## Step 1 - Read Transcript

Read the referenced transcript file completely.

## Step 2 - Detect Project

Determine which project this transcript belongs to:

1. **From file path** - if the file is inside `{project-root}/projects/{project}/`, use that project.
2. **From content** - look for company names, participant names, or context clues.
3. **Ask user** - if ambiguous.

Once the project is identified:
- Read `memory-{project}.md` at the project root for context (participant names, conventions, meeting types).
- Read the project's `meetings/` folder structure to discover available meeting types: `ls {project-root}/projects/{project}/meetings/`.

## Step 3 - Classify & Confirm

Analyze the transcript content and determine the meeting type based on:
- Available subfolders in the project's `meetings/` directory
- Content cues (participants, topics, tone)
- Project memory context

Present to user:

> **Project:** {project}
> **Meeting type detected:** {type}
> **Confidence:** {high/medium/low}
> **Key cues:** {2-3 signals that led to this classification}
>
> Correct? (or specify the right type)

HALT. Wait for user confirmation.

## Step 4 - Fix Filename & Location

After user confirms type, determine the correct filename and folder.

**Naming convention:** `YYYY-MM-DD-{slug}.{ext}`
- `{ext}` - preserve the original file extension
- `{slug}` - kebab-case, derived from the CONTENT of the meeting, not the original file title. The slug must answer "who was in this meeting and what was it about?"
  - Pattern: `{participants}-{topic}` - e.g., `yuri-kenu-budget-review`, `machado-tax-filing`, `team-q1-financials`
  - Bad slugs (too generic): `weekly`, `team-sync`, `meeting-notes`
  - Good slugs (content-derived): `yuri-kenu-runway-planning`, `machado-corporate-restructuring`
- Extract the date from the transcript content (meeting date, not file creation date). If ambiguous, ask user.

**Determine correct folder:** `{project-root}/projects/{project}/meetings/{type}/`

**If the file needs renaming or moving**, present the proposed changes:

> **Current:** `{current_path}/{current_filename}`
> **Proposed:** `{correct_folder}/YYYY-MM-DD-{slug}.{ext}`
>
> Proceed? (y/n)

HALT. Wait for user confirmation.

**Execute file operations:**
- If inside a git repo: use `git mv` to preserve history.
- If the file is outside the repo: copy to the correct location (leave original untouched, inform user).

## Step 5 - Summarize

1. Look for a type-specific prompt: `{project-root}/projects/{project}/meetings/{type}/_summary-prompt.md`
   - If the type has nested subfolders (e.g., `internal/founders/`), check the deepest matching folder first.
2. If no type-specific prompt exists, use the universal fallback: `{rbtv_path}/workflows/meeting-summarizer/universal-prompt.md`
3. Process the transcript following every instruction in the prompt - all three layers, the anti-bias protocol, and every section defined.
4. Save the output as `{correct_folder}/YYYY-MM-DD-{slug}-summary.md`

## Step 6 - Confirm

Report to user:
- Transcript location (final path after any rename/move)
- Summary location
- Any ambiguity flags from the summary that need human review
