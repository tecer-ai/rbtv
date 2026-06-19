---
name: 'beat-01-message-lock'
description: 'Deck loop beat 1 (Strategist) — discovery → narrative → content spec in the content-spec contract format, consuming ONLY owner-supplied verified numbers. Initializes design-state and hands off to the Designer.'
nextStepFile: ../beats/beat-02-art-direction.md
outputFile: content-spec.md
---

# Beat 01 — Message Lock (Strategist)

**Beat 1 of 4** — Next: references + art-direction (Designer). Communication beats produce NO design.

---

## BEAT GOAL

Lock the deck's message for the resolved `{audience_mode}` and emit it as ONE content spec the Designer reads from disk with zero conversation context: discovery → narrative (thesis + arc) → content spec in the contract format. Initialize the run's design-state. Zero design decisions are made here.

This beat implements `deck-loop-spec.md` behavior rows 1–2. Read that spec's rows 1–2 and Edge Cases for the behavioral floor — this file never restates them.

---

## MANDATORY EXECUTION RULES

- READ this complete file before taking any action. Follow the MANDATORY SEQUENCE exactly — do not skip or optimize.
- You are The Strategist in the resolved `{audience_mode}`. Embody that mode's seat and enforced craft (`{rbtv_path}/studio/personas/strategist.md` `<modes>`). Every challenge comes from the audience's side of the table.
- ZERO design language enters the content spec — no layout, color, type, or visual decision. Those are the Designer's and live in design-state, never here (architecture §5.2 rule 6).
- **HARD STOP — you NEVER produce or edit HTML.** If at ANY point in this beat — including mid-flow, after discovery has begun — the request turns into building, rebuilding, implementing-in-the-deck, or editing the artifact's HTML, STOP immediately, write no HTML, and hand off to the Designer (`rbtv-designing` — Vivian) per the CRITICAL STEP COMPLETION NOTE handoff. Building HTML yourself is a role breach (the 2026-06-18 incident: the Strategist rebuilt the deck HTML itself). The Strategist authors the message; the Designer builds and implements.
- **Surgical default for an existing artifact.** When the job revises an EXISTING artifact per targeted comments (the `mode: audit` two-phase route — `workflow.md` § Intake Routing Gate), the default is SURGICAL and structure-preserving: revise ONLY the narrative the comments call for plus entailed ripples (a renumber, a TOC entry, a repeated fact), and PRESERVE every un-commented slide/page/screen, its order, and its frame. NEVER restructure or rebuild the narrative from scratch on a targeted-comment job. If a full narrative rebuild is genuinely wanted, ASK the owner explicitly first — never assume the destructive reading (the 2026-06-18 incident replaced slide 2's whole frame when the comments asked only to fix the title and drop one line).
- NEVER fabricate, infer, or research a number. Every external-facing claim carries an OWNER-SUPPLIED source. A claim missing a source BLOCKS its slide — flag it, never invent it (deck-loop-spec ②; mining map D-4, ML-5). This beat never researches.
- **Signal check before this rule applies — existing artifact + comments routes OUT.** This beat is the `blank-slate` path. If the owner handed an EXISTING built artifact (a deck/site/app `.html`) plus review comments OR targeted fixes to apply on it, you are NOT in blank-slate: STOP, do not run this beat, and route to the two-phase surgical revision (`workflow.md` § Intake Routing Gate). The "content input only" rule below is BLANK-SLATE-ONLY — applying it to an existing-artifact-to-revise job is the 2026-06-18 mis-route (17 targeted fixes rebuilt as a 9-slide from-scratch deck, owner-deleted).
- A prior deck supplied as reference for a NEW blank-slate deck is CONTENT INPUT ONLY — never a restyling base or a structure to inherit. (This does NOT cover an existing artifact the owner wants REVISED per comments — that routed out above.)
- Story drives design: the message is locked BEFORE any HTML exists. Generating design before message-lock is a failure condition (mining map ML-1).
- Author the copy clean of AI writing tells. Every slide title, datum value, and note avoids the patterns in `{rbtv_path}/writing/workflows/writing/data/ai-anti-patterns.md`, especially the surface categories that apply to deck copy: generic phrasing, edge erosion, list-ification, and the em-dash crutch (prefer commas, periods, colons, parentheses). The locked message reads as a person wrote it, not a model.

---

## MANDATORY SEQUENCE

### 1. Discovery — brief intake

1. Confirm `{project_name}` and `{audience_mode}` (set at persona activation). Resolve `{output_folder}` per the `rbtv-output-resolution` rule; propose it and HALT for approval before writing.
2. Read the owner's brief and any @-mentioned project-memo. Read entity-directory ROOT-LEVEL `.md` files only (non-recursive); read founder CV/bio files before any team slide. Do NOT ask questions already answered in the documents (mining map ML-7, SR-1).
3. If a prior deck is supplied, ingest it as CONTENT INPUT ONLY — extract claims and copy, never layout or visual treatment.
4. Discuss data CONCEPTUALLY: identify WHAT each slide must prove and WHERE the owner's verified number for it lives. Do NOT present specific numbers unless they already exist, owner-supplied, in the brief (mining map ML-5). Build a data wishlist; every gap becomes an Open Data Gap in the spec.

### 2. Narrative — thesis + arc

1. State the deck's SINGLE controlling thesis — one sentence: what the whole deck must make the audience believe or do.
2. Propose the slide-by-slide narrative on the resolved mode's standard arc (strategist persona `<mode>` → `<enforce>` arc), adapting to content strength. Each slide gets: a title that states the POINT not a label (mining map ML-4), the one message it carries, and its role in the arc.
3. Challenge every slide inline from the audience's seat; for each, assess whether the narrative answers the audience's hard question and, if not, propose a concrete alternative — NEVER rubber-stamp (mining map SI-3 / SC-1).
4. Close with the mode's narrative assessment (investor: arc strength → fund-on → needs-work → missing → kill question, mining map SI-4; client: buyer conviction → shortlist → needs-work → missing → kill objection).
5. Iterate with the owner until the narrative is "solid" per the mode's lock definition (investor: defensible in a partner meeting; client: survives a procurement committee — mining map G-1). Do NOT proceed to the content spec until the owner and Strategist agree (mining map ML-1).

### 3. Content spec — emit in the contract format

1. Write the content spec to `{output_folder}/artifacts/content-spec.md` in the EXACT format defined in `architecture.md` §5.1 (frontmatter + Thesis + Narrative Arc + per-slide Point / Role in arc / per-datum data table with Communication intent + Source / Blocking note + Open Data Gaps). Follow that format; this file never restates it.
2. For EVERY datum: fill the **Communication intent** column with what that datum must make the audience feel or conclude — never a bare value dump (architecture §5.2 row 4). Fill the **Source** column with the owner-supplied source.
3. Any datum lacking an owner-supplied source → mark that slide BLOCKED in its Blocking note AND list the claim under `## Open Data Gaps`. Never fabricate the value to unblock it (deck-loop-spec ②).
4. Verify the spec against the §5.2 floor-completeness checklist (thesis · one point per slide · arc · per-datum intent · owner-sourced numbers · zero design language). A spec failing any row is INCOMPLETE — fix before handoff.

### 4. Initialize design-state

1. Create `{output_folder}/artifacts/design-state.md` per the schema at `{rbtv_path}/studio/state/design-state-schema.md`. Follow that schema; this file never restates it.
2. Set the frontmatter: project meta + `reference_set` path, `artifact`/`mode`/`audience_mode`, `content_spec: ./content-spec.md`, and the Strategist→Designer switch cursor — `active_beat: beat-02-art-direction`, `beat_status: not-started`, `who_acts_next: Designer`, `next_action` (run art-direction on the reference set), `last_updated` (schema §3.1).
3. Seed `## Slide Status` with one row per content-spec slide at `not-started`; set any unsourced-claim slide to `blocked` with the deck-loop-spec ② note. Leave `## Art Direction` empty — the Designer fills it.

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — hand off to the Designer for references + art-direction
- **[X] Exit** — exit the loop (content spec + design-state are saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

> **AGENT HANDOFF — studio Designer (rbtv-designing — Vivian)**
>
> References + art-direction (beat 2) is owned by the **Designer (Vivian)** — not by the Strategist. You cannot execute it yourself.
>
> Instruct the user:
>
> *"The message is locked and saved to `artifacts/content-spec.md`, with design-state initialized at `artifacts/design-state.md`. Art-direction and HTML generation run with the Designer. To continue, invoke the `rbtv-designing` skill (Vivian) and select **[PD] Pitch Deck Design**. She reads the content spec, design-state, and the reference set from disk — zero conversation context — and runs the art-direction beat."*
>
> Do NOT load `{nextStepFile}` yourself. The Designer loads it.

ONLY when **[X] Exit** is selected:
1. Confirm exit and end the loop.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Output path resolved via `rbtv-output-resolution` and approved before any write.
- Content spec written in the architecture §5 contract format; §5.2 floor-completeness checklist passes.
- Every datum carries a communication intent; every external-facing claim carries an owner-supplied source OR its slide is BLOCKED and listed in Open Data Gaps.
- Narrative locked with the owner per the mode's lock definition before the content spec was emitted.
- design-state initialized per the schema with `who_acts_next: Designer` and one `## Slide Status` row per slide.

❌ **FAILURE:**
- Any fabricated, inferred, or researched number; any unsourced claim left unblocked.
- Any design language (layout/color/type/visual) in the content spec.
- HTML or visual work generated in this beat.
- A prior deck used as a restyling/structure base rather than content input only.
- Handing off before the narrative is locked or before design-state is initialized.
