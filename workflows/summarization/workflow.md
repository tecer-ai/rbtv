---
name: meeting-summarizer
description: Summarize a meeting or document transcript — classify, route, fix filename, and output a structured summary using type-specific or universal prompts
---

# Meeting Summarizer Workflow

**CRITICAL — Execute these steps in order. Do not respond conversationally until Step 7 completes.**

## Step 1 — Read Transcript & Load Glossary

1. Read the referenced transcript file completely. If no transcript was provided, STOP and ask the user for the transcript path.
2. Load the glossary declared in the operating scope's CLAUDE.md (under `## Name Glossary` heading). If no glossary is declared, skip silently.
3. Apply glossary corrections silently while reading the transcript.

## Step 2 — Determine Context

Determine the meeting's context (participants, topic, project). Look at:

1. **The transcript's path** — if the file lives in a project-specific folder (e.g., `<some_path>/meetings/<type>/`), use that as the project context.
2. **The transcript content** — participants, company names, topics.
3. **CLAUDE.md routing** — if the workspace has a CLAUDE.md with content-routing rules, read it to determine which area/project the meeting belongs to.
4. **Ask the user** — if ambiguous, ask directly. Do NOT assume.

Once project context is determined, look for local memory files (e.g., `memory-<project>.md`, a project index, or an area CLAUDE.md) and read them for participant names and conventions.

## Step 3 — Classify and Confirm

Analyze the transcript content to classify the meeting type. Use these cues:

| Type | Cues in transcript |
|------|-------------------|
| Client | Client company, product demo, pricing, implementation, onboarding, business needs, service review |
| Investor | Fund names, investment terms, round/valuation, pitch dynamics, due diligence |
| Internal | Team members only, sprint planning, strategy, product specs, team sync |
| Product interview | User research, discovery questions, feature feedback, workflow walkthrough, pain points — contact is NOT a current client or prospect |

If the project's folder has a `meetings/` subdirectory with type-named sub-folders, use those as the type vocabulary. Otherwise use the generic categories above. For content that does not match any specific type, classify as `general`.

Present to user:

> **Project context:** {what you determined}
> **Meeting type detected:** {type}
> **Confidence:** {high/medium/low}
> **Key cues:** {2-3 signals that led to this classification}
>
> Correct? (or specify the right type)

HALT. Wait for user confirmation.

## Step 4 — Fix Filename and Location

After user confirms, determine the correct filename and output folder.

**Naming convention:** `YYYY-MM-DD-{slug}.{ext}`
- `{ext}` — preserve original extension
- `{slug}` — kebab-case, content-derived (who was in it, what was it about)
  - Inside entity folders (where the folder name carries context): drop the entity name from the slug. Keep date + topic: `YYYY-MM-DD-{topic}.{ext}`
  - Outside entity folders: keep the full descriptive slug since no entity context is carried by the folder
  - Bad slugs (too generic): `weekly`, `team-sync`, `meeting-notes`
  - Good slugs: `yuri-kenu-runway-planning`, `invoice-automation-demo`, `tam-deep-dive`
- Extract the meeting date from the transcript CONTENT (not file creation date). If ambiguous, ask.

**Determine output folder:**
Follow the `rbtv-output-resolution` rule. In short: read the workspace CLAUDE.md's `## File Routing` block, match output type `meeting-summary`, descend into sub-project CLAUDE.mds if needed, infer variables from conversation context, and propose the full path to the user before writing. If no routing exists, inform the user and ask once for this write's output path.

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

Select the summary prompt in this priority order:

1. **Built-in type prompt:** `{rbtv_path}/workflows/summarization/prompts/{type}-summary-prompt.md` — if a prompt exists for the classified meeting type.
2. **Universal fallback:** `{rbtv_path}/workflows/summarization/universal-prompt.md` — for any content without a type-specific prompt.

**Workspace hint augmentation:** After selecting the base prompt, look for a `## Summarization hints` section in the CLAUDE.md governing the output folder (the collection CLAUDE.md — e.g., `investors/CLAUDE.md`, `clients/CLAUDE.md`, `prospects/CLAUDE.md` — or the nearest CLAUDE.md up the tree). If found, append its content verbatim to the base prompt as an additional phase the agent must execute. If no such section exists, proceed with the base prompt alone.

Process the transcript following every instruction in the resulting prompt — all phases, the anti-bias protocol, every section the prompt defines, and any appended workspace hints. Apply all glossary corrections throughout.

Save the output as `{output_folder}/YYYY-MM-DD-{slug}-summary.md` (or the type-specific suffix if the workspace conventions define one, e.g., `-debrief.md` for investor meetings).

## Step 6 — Update Glossary

If a glossary was loaded in Step 1 and the prompt included Phase 1 validation:

1. **New entries:** Append newly confirmed corrections (people, companies, terms) not yet in the glossary.
2. **Existing entries:** If a known term appeared with a new transcription variation not yet listed, add the variation to the existing entry.
3. Do NOT add entries for one-off garbled passages unlikely to recur.

Skip this step in autonomous mode.

## Step 7 — Confirm

Report to user:
- Transcript final location (after any rename/move)
- Summary location
- Glossary entries added or updated (if any)
- Any ambiguity flags from the summary that need human review
