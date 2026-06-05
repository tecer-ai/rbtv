---
name: meeting-summarizer
description: Summarize a meeting or document transcript — classify, route, fix filename, and output a structured summary using type-specific or universal prompts
---

# Meeting Summarizer Workflow

**CRITICAL — Execute these steps in order. Do not respond conversationally until Step 7 completes.**

## Mode Handling — Batched Validation vs Clarifying Questions

Session-level instructions like "work without stopping for clarifying questions", "no stops", "autonomous mode", or voice-mode reminders that say "make the reasonable call and continue" apply ONLY to mid-flow clarifying questions (single open-ended prompts like "which folder?", "what date?"). They do NOT waive the batched validation and approval tables in this workflow.

| Pattern | Affected by no-stop / voice mode? |
|---------|-----------------------------------|
| Single open-ended question mid-flow | YES — make a reasonable call, continue, surface the call in your response |
| Phase 1 validation tables (Step 5 sub-phase) | NO — always present in one batch |
| Step 3 classification confirmation | NO — always present, but combine with Phase 1 in a single approval block under no-stop mode |
| Step 4 filename/location proposal | NO — always present |
| Propagation proposal table (Step 7 / collection CLAUDE.md gates) | NO — always present, requires per-row approval |

Under no-stop / voice mode, consolidate all approval tables into ONE end-of-turn approval block per natural break (after reading the transcript, after writing the summary). The user replies once, you execute the approved rows. Skipping these tables is a workflow violation, not a "reasonable call."

A clarifying question is a STOPPAGE waiting for input. A batched table is a SINGLE round-trip the user can answer in one reply — it is the mechanism that lets the user retain control without per-item interruption.

## Step 1 — Read Transcript(s) & Load Glossary

1. Read every referenced transcript/document file completely. If no file was provided, STOP and ask the user for the path.
2. Load the glossary declared in the operating scope's CLAUDE.md (under `## Name Glossary` heading). If no glossary is declared, skip silently.
3. Track glossary corrections (matched name → canonical form) for write-back in Step 5.5. Do not modify the file yet.
4. If 2+ files were provided, execute Step 1.5 before continuing.

## Step 1.5 — Multi-File Cross-Reference (when 2+ files of the same meeting)

**Trigger:** User provided 2+ files that refer to the same meeting (same date + overlapping participants/topic, or same filename stem with different sources/extensions, or files explicitly named as alt-versions like `-gemini`, `-google`, `-zoom`, `-otter`).

If files refer to DIFFERENT meetings, treat them as independent runs of the workflow — do NOT cross-reference.

### Source-of-truth hierarchy

Classify each file:

| File type | Cues | Role |
|-----------|------|------|
| Gemini summary | Gemini-generated narrative summary (NOT a verbatim transcript) — prose paragraphs, named sections, bullet decisions, no speaker timestamps, often labeled "Notes by Gemini" / "Resumo da reunião" / `-gemini` in filename | **Source of truth** for words, names, terms, decisions |
| Verbatim transcript | Speaker-tagged lines, timestamps, raw spoken text — Google Meet transcript, Otter, Zoom transcript, manual transcription | Substrate to be corrected |
| Other artifacts (chat log, agenda, slides) | Non-transcript supporting docs | Tertiary reference only |

**Rules:**

1. If a Gemini summary is present, it is the **source of truth**. Use its spelling of names, companies, terms, decisions, and numbers to overwrite garbled equivalents in the verbatim transcript(s). The Gemini summary's wording wins on every conflict regarding factual content (names, terms, numbers, decisions). The verbatim transcript still wins on conversational nuance, emotional content, and exact quotes the Gemini summary did not capture.
2. If NO Gemini summary is present and 2+ verbatim transcripts exist, cross-reference them: where one transcript is garbled/inaudible and another transcribes the same span clearly, adopt the clearer version. Track each substitution.
3. The chosen primary substrate for the summary in Step 5 is the verbatim transcript with the most coverage (longest, most complete). The Gemini summary is NOT the substrate — it is the corrections oracle.

### Process

1. Build a `corrections[]` list: for each garbled/uncertain span in the primary verbatim transcript, find the corresponding span in the source-of-truth file and record `{location, original, replacement, source_file}`.
2. Pass this list into the prompt's Phase 1 validation (Step 5) as pre-resolved corrections — present them to the user in the validation table marked `auto-resolved via cross-reference: {source_file}`, so the user can confirm or override in one batch.
3. Apply confirmed corrections in Step 5.5 to the primary verbatim transcript only. Do NOT modify the Gemini summary or other source files.
4. Report in Step 7: number of cross-reference corrections applied, and which file served as source of truth.

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

1. **Built-in type prompt:** `{rbtv_path}/office/workflows/summarization/prompts/{type}-summary-prompt.md` — if a prompt exists for the classified meeting type.
2. **Universal fallback:** `{rbtv_path}/office/workflows/summarization/universal-prompt.md` — for any content without a type-specific prompt.

**Workspace hint augmentation:** After selecting the base prompt, look for a `## Summarization hints` section in the CLAUDE.md governing the output folder (the collection CLAUDE.md — e.g., `investors/CLAUDE.md`, `clients/CLAUDE.md`, `prospects/CLAUDE.md` — or the nearest CLAUDE.md up the tree). If found, append its content verbatim to the base prompt as an additional phase the agent must execute. If no such section exists, proceed with the base prompt alone.

Process the transcript following every instruction in the resulting prompt — all phases, the anti-bias protocol, every section the prompt defines, and any appended workspace hints. Apply all glossary corrections throughout.

Save the output as `{output_folder}/YYYY-MM-DD-{slug}-summary.md` (or the type-specific suffix if the workspace conventions define one, e.g., `-debrief.md` for investor meetings).

## Step 5.5 — Write Corrections Back to Transcript

Applies to ALL meeting types. Skip in autonomous/sub-agent invocations.

After the prompt's Phase 1 validation completes and the user has confirmed corrections, overwrite the original transcript file in place with:

- Confirmed transcription doubt fixes (garbled words, mistranscribed terms)
- Name normalizations from the glossary (Step 1) and any new names confirmed during validation
- Domain-specific term corrections confirmed in Phase 1

Do NOT edit:
- Self-corrections by the speaker ("no, I mean...") — preserve natural speech
- Frontmatter, structure, headings, or any unflagged content
- Any passage the user did not confirm

The transcript path is the post-rename path from Step 4. Use the Edit tool with targeted replacements — never rewrite the whole file.

## Step 6 — Update Glossary

If a glossary was loaded in Step 1 and the prompt included Phase 1 validation:

1. **New entries:** Append newly confirmed corrections (people, companies, terms) not yet in the glossary.
2. **Existing entries:** If a known term appeared with a new transcription variation not yet listed, add the variation to the existing entry.
3. Do NOT add entries for one-off garbled passages unlikely to recur.

Skip this step in autonomous mode.

## Step 7 — Confirm

Report to user:
- Transcript final location (after any rename/move)
- Whether transcript was edited in place with confirmed corrections (and how many)
- Summary location
- Glossary entries added or updated (if any)
- Any ambiguity flags from the summary that need human review
