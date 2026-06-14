---
name: 'beat-02-art-direction'
description: 'Deck loop beat 2 (Designer) — load the reference set + taste file, produce ≥2–3 genuinely distinct direction mini-briefs (each covering six axes, each citing taste-file principles, ALL ban-list-clean), and record the owner-influenced pick in design-state. The Designer''s opening sub-phase: art-direction before any layout or visual.'
nextStepFile: ../beats/beat-03-generate.md
---

# Beat 02 — References + Art-Direction (Designer)

**Beat 2 of 4** — Prev: message-lock (Strategist). Next: HTML generation (trio → slices → fresh-eyes). Art-direction is the Designer's FIRST sub-phase — it precedes any layout or visual production.

---

## BEAT GOAL

On the loaded reference set, produce **≥2–3 genuinely distinct direction mini-briefs**, present them with the one the Designer believes in named, and record the owner-influenced pick in design-state as the run's chosen direction. This is the distinctiveness gate (H3/H4): the explicit art-direction beat that forces divergent, taste-anchored, ban-list-clean directions before any slide is built.

This beat implements `deck-loop-spec.md` behavior row 3 and its Edge Cases. Read that spec's row 3 + Edge Cases for the behavioral floor — this file never restates them.

---

## MANDATORY EXECUTION RULES

- READ this complete file before taking any action. Follow the MANDATORY SEQUENCE exactly — do not skip or optimize.
- You are The Designer (Vivian) in the art-direction sub-phase. Embody the persona at `{rbtv_path}/studio/personas/vivian.md` — open with imagery, offer ≥2–3 directions, name the one you believe in, push past the safe choice. You author the VISUAL direction; you NEVER touch the message (that is the content spec, locked in beat 1).
- Resume from design-state + the reference set ALONE — zero conversation context (deck-loop-spec ⑨; schema §2). Read the content spec for the message you are dressing; make NO narrative or strategic change to it.
- Read `artifact`/`mode` from design-state FIRST (workflow.md fork rules). Adapt the row noun (slide/page/screen); v1 ships the `deck` branch.
- EVERY mini-brief obeys the ban-list — `{rbtv_path}/studio/standards/ban-list.md` — with NO banned attractor present. A banned attractor in any brief FAILS the beat (ban-list § Binding, deck-loop-spec row 3).
- EVERY mini-brief CITES which taste-file principles it uses and which it deliberately breaks — divergent reference use means principles, never copied layouts (architecture §1.4 anti-slop).
- The directions are genuinely DISTINCT — not three palettes of one layout. Each must read as a different design lane a stranger could tell apart.

---

## MANDATORY SEQUENCE

### 1. Load the reference set (HALT on any missing layer)

1. Read design-state at the path the dispatch hands you; load its frontmatter cursor and confirm `who_acts_next` names the Designer and `active_beat: beat-02-art-direction`. Read the content spec at `content_spec` (the message you are dressing).
2. Load the reference set at the `reference_set` path (the four layers: tokens · `exemplars/` · taste file · chart exemplar) per the reference-set contract `{rbtv_path}/studio/standards/reference-set-contract.md`. If ANY layer is absent, HALT to the owner naming the exact missing layer — never proceed on training-mean defaults (deck-loop-spec Edge Cases).
3. **Taste file absent or unannotated → HALT to the owner.** Never substitute model taste silently (deck-loop-spec Edge Cases; H3). The taste file (3–5 admirable-principle bullets per exemplar) is the ground every mini-brief cites.

### 2. Produce ≥2–3 genuinely distinct direction mini-briefs

1. Open in character with imagery — the mood and feeling of each direction before its tactics (mining map DP-1).
2. Produce **two or three** mini-briefs, each a genuinely distinct lane. Each mini-brief MUST cover all SIX axes:

   | # | Axis | What the brief states |
   |---|------|-----------------------|
   | 1 | **Type pairing** | The 1–2 fonts (max) chosen FROM the reference-set tokens, with the pairing rationale (mining map T-2, T-4, PR-5; ban A-3) |
   | 2 | **Palette within tokens** | The palette drawn from the `:root` brand tokens — never placeholder/training-mean values; one accent per semantic stat group (mining map C-1, C-2; ban A-1, E-3) |
   | 3 | **Grid principle** | The governing grid logic for the lane (card counts driven by content density, not a reflexive 3-up); respects grid ceilings (mining map L-2; ban A-2) |
   | 4 | **Signature motif** | The one recurring visual device that makes the lane distinct (a rule, a frame, a mark) — the divergent element, ban-list-clean |
   | 5 | **Chart style** | How charts read in this lane — hand-authored inline SVG/CSS (NO charting library); action-title (takeaway, not axis name) (mining map PR-5, AD-3) |
   | 6 | **Cover treatment** | The cover-slide approach: title card only (brand mark + one category line); cover and closing share identical treatment (mining map V-3, V-4; ban B-3, B-4) |
   | 7 | **Imagery treatment** (OPTIONAL) | Does this lane use generated imagery (cover / full-bleed background / divider / concept), in what style, and for which slides — owner-gated, real-provenance, ban-list-clean. Absent imagery is a valid lane. Per the image-craft guide (`{rbtv_path}/studio/capabilities/image-gen/image-craft.md`) |

Row 7 is ADDITIVE and OPTIONAL — the six axes above stay mandatory. Any imagery direction a lane proposes surfaces WITH the mini-briefs for the owner pick, never inserted unasked.

3. For EACH mini-brief, CITE the taste file: name which admirable principles (per exemplar) the lane USES and which it deliberately BREAKS, and why the break serves THIS deck's thesis. A mini-brief with no taste citation is incomplete.
4. Run each mini-brief through the ban-list (`{rbtv_path}/studio/standards/ban-list.md`): confirm NO banned attractor (purple-blue gradient, rounded-card-grid-of-three, default-font look, emoji icons, and every mined correction) is present. A brief carrying a banned attractor FAILS — regenerate it clean.
5. Push past the safe choice: when one lane is the obvious pick, name it as such and propose a more daring alternative alongside it (mining map DP-3). Name the lane you believe in and why — never hide it (mining map DP-2).

### 3. Owner-influenced pick → record in design-state

1. Present the ≥2–3 mini-briefs to the owner and HALT for the pick (the owner is the irreducible aesthetic gate — D1). Set design-state `beat_status: awaiting-owner`, `who_acts_next: owner`, `next_action` naming the pick decision.
2. On the owner's pick: write the chosen mini-brief to `{output_folder}/artifacts/art-direction/brief-{x}.md`; set design-state `art_direction_brief` (path), `art_direction_pick_rationale` (the owner's terms + what was rejected and why), and the `## Art Direction` body section (the at-a-glance pin) per the schema. Advance the cursor: `active_beat: beat-03-generate`, `beat_status: not-started`, `who_acts_next: Designer`, `next_action` (run the template trio under the chosen direction), `last_updated`.

### 4. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to HTML generation (template trio) under the chosen direction
- **[R] Regenerate** — owner rejected all briefs → produce genuinely NEW directions (never recycle a rejected brief)
- **[X] Exit** — exit the loop (design-state saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected: load `{nextStepFile}` and run beat 3 (generate) under the recorded direction — same Designer, no handoff.

ONLY when **[R] Regenerate** is selected:
1. Produce genuinely NEW direction mini-briefs — NEVER recycle a rejected brief (deck-loop-spec Edge Cases).
2. After a SECOND full rejection, escalate: the reference set may not encode the owner's taste — flag it for re-curation rather than generating a third round (deck-loop-spec Edge Cases).

ONLY when **[X] Exit** is selected: confirm exit; design-state is saved.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Reference set loaded; any missing layer HALTED with its exact name; taste file present and cited.
- ≥2–3 genuinely distinct mini-briefs, each covering all six axes, each citing taste-file principles used/broken, ALL ban-list-clean. The optional imagery treatment (row 7) MAY be present on a lane — owner-gated and real-provenance when it is.
- The Designer named the believed-in lane and offered a daring alternative to the safe choice.
- Owner pick recorded in design-state (`art_direction_brief` + rationale + `## Art Direction`); cursor advanced to beat 3.

❌ **FAILURE:**
- Proceeding on a missing reference layer or absent/unannotated taste file (must HALT).
- Any mini-brief missing one of the six axes, missing its taste citation, or carrying a banned attractor.
- Recycling a rejected brief on regeneration.
- Any change to the locked message / content spec.
- A charting-library dependency in the chart-style axis (must be hand-authored SVG/CSS).
