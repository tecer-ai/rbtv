---
name: meeting-summarizer
description: Summarize a meeting transcript, fix filename + location, and output a structured summary
---

# Meeting Summarizer Workflow

**CRITICAL — Execute these steps in order. Do not respond conversationally until Step 6 completes.**

## Step 1 — Read Transcript

Read the referenced transcript file completely. If no transcript was provided, STOP and ask the user for the transcript path.

## Step 2 — Determine context

Determine the meeting's context (participants, topic, project). Look at:

1. **The transcript's path** — if the file lives in a project-specific folder (e.g., `<some_path>/meetings/<type>/`), use that as the project context.
2. **The transcript content** — participants, company names, topics.
3. **CLAUDE.md routing** — if the workspace has a CLAUDE.md with content-routing rules, read it to determine which area/project the meeting belongs to.
4. **Ask the user** — if ambiguous, ask directly. Do NOT assume.

Once project context is determined, look for local memory files (e.g., `memory-<project>.md`, a project index, or an area CLAUDE.md) and read them for participant names and conventions.

## Step 3 — Classify and confirm

Analyze the transcript content to classify the meeting type. Typical categories: client, investor, internal, discovery, therapy, other.

If the project's folder has a `meetings/` subdirectory with type-named sub-folders, use those as the type vocabulary. Otherwise use the generic categories above.

Present to user:

> **Project context:** {what you determined}
> **Meeting type detected:** {type}
> **Confidence:** {high/medium/low}
> **Key cues:** {2-3 signals that led to this classification}
>
> Correct? (or specify the right type)

HALT. Wait for user confirmation.

## Step 4 — Fix filename and location

After user confirms, determine the correct filename and output folder.

**Naming convention:** `YYYY-MM-DD-{slug}.{ext}`
- `{ext}` — preserve original extension
- `{slug}` — kebab-case, content-derived (who was in it, what was it about)
  - Pattern: `{participants}-{topic}` — e.g., `yuri-kenu-budget-review`
  - Bad slugs (too generic): `weekly`, `team-sync`, `meeting-notes`
  - Good slugs: `yuri-kenu-runway-planning`, `machado-corporate-restructuring`
- Extract the meeting date from the transcript CONTENT (not file creation date). If ambiguous, ask.

**Determine output folder:**
Follow the `rbtv-output-resolution` rule (installed as `.claude/rules/rbtv-output-resolution.md`). In short: read the workspace CLAUDE.md's `## File Routing` block, match output type `meeting-summary`, descend into sub-project CLAUDE.mds if needed, infer the `{project}` variable from conversation context (which client / which meeting this is), and propose the full path to the user before writing. If no routing exists yet, inform the user that `/rbtv-output-routing` has not been run and ask once for this meeting's folder.

If the file needs renaming or moving, present the proposed change:

> **Current:** `{current_path}/{current_filename}`
> **Proposed:** `{output_folder}/YYYY-MM-DD-{slug}.{ext}`
>
> Proceed? (y/n)

HALT. Wait for user confirmation.

**Execute file ops:**
- If inside a git repo, use `git mv` to preserve history.
- If outside, copy to the correct location and leave the original (inform the user).

## Step 5 — Summarize

1. Look for a type-specific prompt at `{output_folder}/_summary-prompt.md` (if the meeting's folder has a nested `_summary-prompt.md`, use it).
2. If none, use the universal fallback at `{rbtv_path}/workflows/summarization/universal-prompt.md`.
3. Process the transcript following every instruction in the chosen prompt — all analytical layers, the anti-bias protocol, and every section the prompt defines.
4. Save the output as `{output_folder}/YYYY-MM-DD-{slug}-summary.md`.

## Step 6 — Confirm

Report to user:
- Transcript final location (after any rename/move)
- Summary location
- Any ambiguity flags from the summary that need human review
