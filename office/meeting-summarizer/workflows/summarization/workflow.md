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

**Unattended mode is a THIRD mode, and it is not the no-stop mode above.** No-stop / voice mode still has a user on the other end, which is why it keeps the tables. Unattended mode has nobody: it is entered only by the explicit trigger in `## Unattended Mode` at the end of this file, and there every table above becomes a decision this workflow makes and records, never a table it presents. That is a defined mode with its own rules, not a "reasonable call" waiving the tables — the paragraph above is about voice mode and is unchanged.

## Step 1 — Read Transcript(s) & Load Glossary

1. Read every referenced transcript/document file completely. If no file was provided, STOP and ask the user for the path.
2. Load the glossary declared in the operating scope's CLAUDE.md (under `## Name Glossary` heading). If no glossary is declared, skip silently.
   Record how many terms the load returned as `glossary-terms-loaded`. **Unattended mode reports that number and treats 0 as a hard failure** (`## Unattended Mode`, step 1) — because "skip silently" above means an unloaded glossary otherwise passes "the corrections were applied" without any correction having been possible. Interactive mode is unchanged by this: it neither reports nor checks the number.
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

1. **Built-in type prompt:** `.rbtv/mirror/office/meeting-summarizer/workflows/summarization/prompts/{type}-summary-prompt.md` — if a prompt exists for the classified meeting type.
2. **Universal fallback:** `.rbtv/mirror/office/meeting-summarizer/workflows/summarization/universal-prompt.md` — for any content without a type-specific prompt.

**Workspace hint augmentation:** After selecting the base prompt, look for a `## Summarization hints` section in the CLAUDE.md governing the output folder (the collection CLAUDE.md — e.g., `investors/CLAUDE.md`, `clients/CLAUDE.md`, `prospects/CLAUDE.md` — or the nearest CLAUDE.md up the tree). If found, append its content verbatim to the base prompt as an additional phase the agent must execute. If no such section exists, proceed with the base prompt alone.

Process the transcript following every instruction in the resulting prompt — all phases, the anti-bias protocol, every section the prompt defines, and any appended workspace hints. Apply all glossary corrections throughout.

Save the output as `{output_folder}/YYYY-MM-DD-{slug}-summary.md` (or the type-specific suffix if the workspace conventions define one, e.g., `-debrief.md` for investor meetings).

## Step 5.5 — Write Corrections Back to Transcript

Applies to ALL meeting types, in EVERY mode — interactive, no-stop and unattended alike. Unattended mode does not skip this step; it reads "the user has confirmed corrections" below as "the glossary settled the correction", and writes back exactly the same way. A correction still carrying a doubt marker is NOT written back, in any mode.

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

This step runs in EVERY mode, unattended included. In unattended mode "newly confirmed" means "settled by the glossary or by an owner answer already in hand"; a term still under a doubt marker is not confirmed and is not added — `## Amendment Mode` adds it when the owner answers.

## Step 7 — Confirm

Report to user:
- Transcript final location (after any rename/move)
- Whether transcript was edited in place with confirmed corrections (and how many)
- Summary location
- Glossary entries added or updated (if any)
- Any ambiguity flags from the summary that need human review

---

## Unattended Mode

The unattended contract. Every step above still applies — this section says only how each of that
workflow's gates is resolved when there is nobody to ask. **There is one copy of the summarization
logic and it is Steps 1–7 above.** Unattended mode adds no summarization of its own, and no copy of
this workflow exists anywhere else for a caller to use instead.

**Trigger.** The prompt carries "Execute in **unattended mode**."

**The standing rule.** Nothing on standard input, ever. Never emit a question, a confirmation, a
proposal awaiting approval, or any variant of "Correct?", "Proceed?", "STOP and ask" or "HALT" —
and never wait after emitting anything. Each gate below is DECIDED and the decision reported; a
gate that cannot be decided ends the job with `OUTCOME: failed`, never with a wait.

| Gate above | Interactive | Unattended |
|------------|-------------|------------|
| Step 1.1 — no file provided | STOP and ask for the path | take the path(s) from the invocation; with none, `OUTCOME: failed` |
| Step 2.4 — ambiguous context | ask the user | take the context from the invocation, else from the transcript and the routing config; if still ambiguous, classify `general` and record it |
| Step 3 — "Correct?" + HALT | present and wait | decide the type from the same cues, report it under `CLASSIFIED:`, continue |
| Step 4 — "Proceed? (y/n)" + HALT | present and wait | take the destination the invocation supplies; with none, resolve it as Step 4 says, report it under `DESTINATION:`, continue. If no destination resolves, `OUTCOME: failed` — **never default a route** |
| Step 5 Phase 1 validation tables | present in one batch and wait | auto-resolve against the glossary; everything unsettled gets a doubt marker (below) |
| Step 7 / collection CLAUDE.md `propagate?` | per-row approval | **accept every row and complete it** |

1. **Glossary precondition.** Report `GLOSSARY-LOADED: <glossary-terms-loaded>` from Step 1.
   If that number is **0**, stop with `OUTCOME: failed` and the reason, and write nothing.
   Do not proceed as if corrections had been applied: with no glossary loaded, none could have been.
2. **Doubt markers.** A term the glossary cannot settle is not a reason to stop and not a reason to
   guess silently. Write it into the summary at the place it occurs as
   `{{doubt|term=<term>|guess=<best-guess>}}` — `<term>` the transcribed form, `<best-guess>` the
   best reading available. The summary ships with the best guess rendered in place and is corrected
   later by `## Amendment Mode`, never withheld.
   When — and only when — the finished summary carries at least one doubt marker, the first line
   under the summary's title heading is the notation explanation line below, copied VERBATIM: one
   line, every character exactly as written, with nothing reworded, abbreviated, translated, wrapped
   or re-composed. This line is a fixed template, not prose to author — the notation inside it is
   the marker shape itself, exactly as defined above, and it is the ONLY place the summary explains
   its notation. A summary with no doubt marker carries no explanation line at all.

   ```
   > Termos que o glossario nao resolveu estao marcados como `{{doubt|term=<term>|guess=<best-guess>}}` e serao corrigidos no lugar quando o owner responder.
   ```

3. **Both writebacks.** Step 5.5 (transcript) and Step 6 (glossary) run. They are the half of this
   workflow an unattended run used to drop; a run that reports a summary and no writeback has
   failed even if the summary is good.
4. **Propagation gates — accepted and COMPLETED.** After the summary is written, read the CLAUDE.md
   governing the output folder. Where it asks to propagate facts into a collection or entity record
   (a `propagate?` table, or any per-row approval gate), accept **every** row and perform the write
   it proposes, then report the count. Accepting is not skipping: a gate reported as "skipped",
   "deferred" or "left for the owner" is a failure of this step. This gate lives in the destination
   repo's CLAUDE.md, not in this workflow, which is why it is named here explicitly.
5. **Re-run safety.** If the summary file already exists, amend it in place (`## Amendment Mode`)
   rather than writing a second file.
6. **Report**, as the last thing emitted, replacing Step 7's conversational report:

   ```
   GLOSSARY-LOADED: <n>
   CLASSIFIED: <type> (<confidence>)
   DESTINATION: <output folder>
   SUMMARY: <path written>
   TRANSCRIPT-WRITEBACK: <n corrections> -> <path(s)>
   GLOSSARY-WRITEBACK: <n rows added or amended> -> <glossary path>
   DOUBTS: <n>
   PROPAGATED: <n rows accepted and completed>
   OWNER-TURNS: 0
   OUTCOME: filed|amended|failed
   ```

## Amendment Mode

The re-entry point: the owner answers a term **after** the summary was already filed, and the
answer is applied with no further owner action. Unattended by the same standing rule as
`## Unattended Mode` — nothing on standard input, no prompt, no wait.

**Trigger.** The prompt carries "Execute in **amendment mode**." plus the summary path and one or
more answered terms — each a "Term in doubt:" line followed by its "Owner's answer:" line. Steps 3–5
apply to EVERY answered term the prompt lists, in one pass over the files.

1. Report `GLOSSARY-LOADED: <n>` from Step 1. Zero is a hard failure, as above.
2. Read the named summary. If it does not exist, stop with `OUTCOME: failed` — never write a new
   summary from amendment mode.
3. **Amend in place.** In that same file, replace every `{{doubt|term=<term>|guess=<guess>}}` marker
   whose `<term>` matches the answered term with the settled term. Change nothing else: no heading,
   no section, no ordering, no wording beyond the term itself. **Never create a second file** — not
   a copy, not a `-v2`, not a dated sibling. The amendment is an edit to the existing path.
4. **Glossary row.** Add the settled term to the glossary loaded in Step 1, by Step 6's rules: a new
   variation on an existing entry when the canonical name is already there, otherwise a new row
   carrying the transcribed form as its variation and the answer's context.
5. **Transcript.** Apply the same correction to the transcript file(s), by Step 5.5's rules.
6. **Report:**

   ```
   GLOSSARY-LOADED: <n>
   AMENDED: <summary path>
   MARKERS-RESOLVED: <n>
   GLOSSARY-WRITEBACK: <n rows added or amended> -> <glossary path>
   FILES-CREATED: 0
   OWNER-TURNS: 0
   OUTCOME: amended
   ```
