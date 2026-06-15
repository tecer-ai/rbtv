---
name: 'beat-03-generate'
description: 'Deck loop beat 3 (Designer) — HTML generation in three sub-beats: template trio (2 variants × cover/content/chart, pairwise pick → visual contract) → slice-by-slice generation by fresh-context workers resuming from design-state (surgical-patch iteration, HTML-native output) → fresh-eyes pass (fresh-context review against the chosen mini-brief + the flaw checklist → punch-list, before the owner ever looks).'
nextStepFile: ../beats/beat-04-human-gate.md
---

# Beat 03 — HTML Generation (Designer)

**Beat 3 of 4** — Prev: art-direction (Designer). Next: human gate (Designer). An optional **3·0 library probe** runs first (reuse an existing slide library when one fits); then three sub-beats in order: **3A template trio → 3B slice generation → 3C fresh-eyes pass.** The locked message is never altered here.

---

## BEAT GOAL

Produce the full HTML artifact under the chosen direction: first establish the visual contract via a pairwise-picked template trio (3A), then generate every slide slice-by-slice by fresh-context workers conforming to that contract (3B), then raise the floor with a fresh-eyes pass before the owner ever looks (3C). Output is HTML-native: full-screen browser + print-to-PDF CSS, no PPTX.

This beat implements `deck-loop-spec.md` behavior rows 3·0, 4, 5, 6, 7, 10. Read those rows + Edge Cases for the behavioral floor — this file never restates them.

---

## MANDATORY EXECUTION RULES

- READ this complete file before taking any action. Run sub-beats **3·0 → 3A → 3B → 3C** in order — do not skip or reorder. The owner's pick at 3·0 (library probe) MAY route to an assemble-from-library path that SKIPS 3A; every other sub-beat runs unchanged.
- You are The Designer (Vivian). Resume from design-state + the reference set + the content spec ALONE — zero conversation context (deck-loop-spec ⑨; schema §2). Make NO change to the locked message.
- Read `artifact`/`mode` from design-state FIRST (workflow.md fork rules); adapt the row noun (slide/page/screen). v1 ships the `deck` branch.
- Every artifact conforms to the chosen direction mini-brief AND the winning trio contract, and obeys the ban-list (`{rbtv_path}/studio/standards/ban-list.md`). A banned attractor is a defect.
- Charts are HAND-AUTHORED inline SVG/CSS — NO charting-library dependency. A library import in any slide is a defect.
- HTML-native output ONLY: full-screen browser deck + print-to-PDF CSS, mandatory `@media print` block (mining map G-2, P-1/P-3). NO PPTX affordance — any PPTX path is a defect.
- Render for review via the local-server pattern from `{rbtv_path}/studio/workflows/browser-automation/` (a local HTTP server). Direct `file://` opening is BLOCKED — never use it.
- Imagery is OPTIONAL and owner-gated — never auto-inserted. Any image is real-provenance only and comes via the image-gen capability (`{rbtv_path}/studio/capabilities/image-gen/`) and the craft guide (`{rbtv_path}/studio/capabilities/image-gen/image-craft.md`). A deck with no generated imagery is a valid outcome.

---

## SUB-BEAT 3·0 — Slide-Library Probe (optional reuse, owner-gated)

Runs ONCE at beat entry, before 3A. Purpose: when a spec-compliant slide library already covers part of this deck, reuse it instead of authoring every slide from scratch. The loop NEVER requires a library — absent one, skip straight to 3A, unchanged.

1. **Detect (deterministic).** Glob `**/library.json` from the vault root. You are launched from the vault and the library lives in a client repo's `slide-library/` (e.g. `<client-repo>/slide-library/library.json`), NOT under the deck's output folder — so a vault-wide glob is the correct, only reliable root; `library.json` is a rare filename. Read each hit; KEEP it only if it parses as JSON carrying a `convention_version` (a real RBTV slide-library — `{rbtv_path}/studio/slide-library/docs/convention-spec.md` § 7). DISCARD any hit whose path contains `slide-library/tests/` — that is the convention's synthetic fixture, never a deck source.
2. **Select (judgment).** From the validated libraries, pick the ONE whose owning repo/brand fits THIS deck — the content spec names the audience; the output path names the client. Disambiguate per `rbtv-output-resolution` (conversation context + the repo's CLAUDE.md decide). On a genuine tie or no fit, conclude "no fitting library" — NEVER force one.
3. **Branch + HALT.**
   - **No fitting library** → state "no slide library found — building bespoke" and proceed to 3A (today's path).
   - **A fitting library** → read its `CLAUDE.md` + `manifest.md`, map each content-spec slide to a manifest fragment by `section`/`summary`/`lang` (covered vs uncovered), set design-state `beat_status: awaiting-owner` / `who_acts_next: owner`, and offer the owner:
     - **[L] Assemble from library** — follow the library's `CLAUDE.md` cold-agent path: pick a preset or compose an id order, run its `assemble.py`, then do the creative token-fill pass. On this path the library's `theme.css` IS the deck's design system; **3A is SKIPPED**, and any uncovered content-spec slide is authored as a new fragment conforming to that same `theme.css` (coherence beats a fresh trio). NEVER edit the library's `slides/`/`manifest.md`/`presets.md` in place — the engine appends its own as-built entry. Then continue to 3C (fresh-eyes still runs).
     - **[B] Build bespoke** — ignore the library; proceed to 3A. Every slide authored fresh under the owner-picked direction.

The owner gate is the safety net: even if Select mis-picks, the owner sees the offer and can choose [B].

---

## SUB-BEAT 3A — Template Trio (pairwise → visual contract)

Implements deck-loop-spec row 4. SKIPPED when the owner picked **[L] Assemble from library** at 3·0 (the library's `theme.css` is the deck's design system on that path). Runs as written for the bespoke path ([B] or no library).

1. Under the owner-picked direction (design-state `art_direction_brief`), generate **2 variants each** of three slide types — **cover · content slide · chart slide** — = six trio artifacts. Each variant honors all six direction axes (type pairing · palette within tokens · grid principle · signature motif · chart style · cover treatment) and the ban-list.
2. The **chart-slide** variants are hand-authored inline SVG/CSS with an action-title (the takeaway, not an axis name) — NO charting library (mining map PR-5, AD-3).
3. **Render HEADED** via the local-server pattern (a visible browser, real geometry) — never headless, never `file://`.
4. Present the variants **PAIRWISE** to the owner: A-vs-B per slide type (comparative judgment is where the owner is reliable; mining map DP-2). HALT for the owner's three picks (set design-state `beat_status: awaiting-owner`, `who_acts_next: owner`).
5. Record the winning trio as the deck's **visual contract** in design-state: write it to `{output_folder}/artifacts/art-direction/trio-winning.md`, set the `trio_contract` frontmatter path. Every subsequent slide conforms to it.
6. **Edge cases (deck-loop-spec):** both variants of a slide type rejected → new variants under the SAME direction. The direction itself is the problem → re-run the pick as beat 2, recorded as a bounce against the DIRECTION, not a slide.

**OPTIONAL critic hook (default OFF — never gates).** If design-state frontmatter carries `critic: on` (the toggle; default `off` / absent = skip), then BEFORE presenting the trio pairwise (step 4): invoke `{rbtv_path}/studio/critic/critic.md` on the two variants of each slide type (comparison shape — variants are an ideal pairwise input). ATTACH its critique to the owner's pairwise-pick packet as advisory input. The owner's pick proceeds REGARDLESS of critic content — the critic NEVER selects the variant, NEVER blocks or auto-confirms a pick (critic-spec Behavior row 5; never-gates pin). The critic is DISTINCT from the fresh-eyes pass (§3C) and does not replace it. When `critic: off` or absent, skip this hook entirely — the default loop is unchanged.

---

## SUB-BEAT 3B — Slice Generation (fresh contexts, surgical patch, HTML-native)

Implements deck-loop-spec rows 5, 7, 10.

1. Build a **slice plan** from the content spec: one slice per content-spec slide, each carrying its Point, role-in-arc, and per-datum communication intent. A slide whose datum is `blocked` (no owner source) stays blocked — never fabricate to unblock (deck-loop-spec ②).
2. Generate the deck **slice-by-slice**. Each slice is produced by a **fresh-context worker** that reads ONLY design-state + the reference set + the content spec + the trio contract — zero conversation history (context hygiene, schema §2; deck-loop-spec ⑨). The worker resumes from the design-state cursor, generates its slide conforming to the trio contract, and writes a per-slide HTML status update to design-state `## Slide Status` (`generating` → `rendered`).
3. Apply the slice structural craft: each slide expresses ONE idea with a point-stating title; 15–20% min whitespace; layout typed by slide purpose (hero/data/comparison/story/action); enforce at generation time, not QA time (mining map SL-1, SL-2/SL-3, SL-4). Slices with charts follow the hand-authored SVG/CSS decision.
4. **Surgical-patch iteration:** a bounce or punch-list item patches ONLY the flagged slide — all other slides stay BYTE-IDENTICAL (deck-loop-spec ④/⑦). Inline SVG/CSS makes byte-stable patches native; never regenerate the whole deck to fix one slide.
5. **Optional imagery (owner-gated).** For a slide the chosen direction marked for imagery (beat-02 row 7): if the owner did not already approve it at art-direction, the Designer PROPOSES it now (purpose + style); on owner-yes, GENERATE it via the image-gen capability into the deck's OWN `assets/` folder and PLACE it (full-bleed background with a legibility scrim / inline `<img>` / cover treatment) per the image-craft guide (`{rbtv_path}/studio/capabilities/image-gen/image-craft.md`). Imagery is print-safe, real-provenance only, and respects availability — degrade to the `fixture` placeholder when Gemini is absent. Imagery NEVER alters the locked message.
6. **Output contract — deck authoring standard (default, website/pitch output):** a full-screen browser deck with print-to-PDF CSS. Every top-level slide is `<section class="slide …">` carrying the full `data-hyp-*` export-metadata attribute set defined in `{rbtv_path}/studio/slide-library/docs/convention-spec.md` § 10.1 (eight attributes: `data-hyp-slide-id`, `-section`, `-title`, `-audience`, `-lang`, `-summary`, `-kind`, `-provenance`). Every slide is sized **1280×720** (§ 10.2). The mandatory `@media print` block follows G-2 (`-webkit-print-color-adjust: exact`, `.slide { page-break-inside: avoid; }`) with `@page { size: 1280px 720px; margin: 0; }` replacing G-2's `@page { size: landscape }` for decks — one `@page` rule, not two (§ 10.3). Render-for-review via the local-server pattern; `file://` is blocked. NO PPTX.
   **Dashboard / non-deck escape:** when the output is a dashboard or app (neither a website nor a pitch deck), the deck authoring standard is consciously SKIPPED — no export-metadata attributes, no 1280×720, no print block — and this must be stated explicitly in the output (§ 10.5).

---

## SUB-BEAT 3C — Fresh-Eyes Pass (before the owner looks)

Implements deck-loop-spec row 6. **BOUNDARY (verbatim): this is a prompt-file review in a fresh session — NO scoring, NO gating, NO taxonomy dataset.** Those are the v1.1 critic (`studio/critic/critic.md`); building any of them here is a defect. The optional critic hook (§3A) and this fresh-eyes pass are DISTINCT, always-separate mechanisms — fresh-eyes ALWAYS runs (single-deck punch-list, no taxonomy/comparison); the critic is OPT-IN (`critic: on`) and comparative. The critic NEVER replaces, merges into, or weakens fresh-eyes, regardless of the toggle.

1. A **fresh-context** agent (zero generation context — it did NOT build the deck) loads ONLY: the chosen direction mini-brief (`art_direction_brief`) + the flaw checklist (`{rbtv_path}/studio/standards/flaw-checklist.md`) + the rendered deck. Freshness is mandatory — the builder's eyes cannot run this pass.
2. It reviews the deck **HEADED** (visible browser, real geometry) against the two anchors: every flaw-checklist item AND every clause of the chosen mini-brief.
3. It emits a **punch-list**: per-slide findings, each citing the flaw-checklist item OR the mini-brief clause it violates. A genuinely structural flaw not on the checklist is still reported with a one-line spotting cue (flaw-checklist Reviewer note). NO scores, NO pass/fail gate, NO taxonomy.
4. The punch-list lands in design-state `## Fresh-Eyes Punch-List`.
5. **Sequencing (binding):** the fresh-eyes pass runs BEFORE any full pass reaches the owner. Its punch-list items are patched SURGICALLY (sub-beat 3B patch loop — only flagged slides change) BEFORE the human gate (beat 4). The owner sees the floor-raised deck, never the raw first pass.

---

## Present Menu

**Select an Option:**
- **[C] Continue** — full deck generated, fresh-eyes punch-list patched → proceed to the human gate (headed owner review)
- **[T] Re-pick Trio** — owner wants a different trio variant → re-run sub-beat 3A (or beat 2 if the direction is wrong)
- **[X] Exit** — exit the loop (design-state saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected: confirm the fresh-eyes punch-list is patched (no open items in design-state `## Fresh-Eyes Punch-List`), advance design-state (`active_beat: beat-04-human-gate`, `beat_status: not-started`, `who_acts_next: Designer`, `next_action`: headed owner review), then load `{nextStepFile}` — same Designer, no handoff.

ONLY when **[T] Re-pick Trio** is selected: re-run sub-beat 3A; if the direction is the problem, return to beat 2 (recorded as a direction bounce).

ONLY when **[X] Exit** is selected: confirm exit; design-state is saved.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Library probe: ran before 3A; a `convention_version`-valid library fitting the deck's client was offered to the owner ([L]/[B]); the `slide-library/tests/` fixture was never offered; absent a fit, the deck built bespoke and said so.
- Trio: 2 variants × cover/content/chart, rendered HEADED, picked PAIRWISE, winning trio recorded as the visual contract in design-state.
- Slices: every content-spec slide generated by a fresh-context worker resuming from design-state ALONE; every slide conforms to the trio contract; per-slide status tracked; charts hand-authored SVG/CSS.
- Surgical patch: a bounce/punch-list item changes only the flagged slide; all others byte-identical.
- Output (deck): every slide a `<section class="slide …">` with the full `data-hyp-*` export-metadata attribute set (§ 10.1), sized 1280×720 (§ 10.2), mandatory `@media print` block with `@page { size: 1280px 720px; margin: 0 }` (§ 10.3, replaces G-2's `landscape` for decks); rendered via local server, never `file://`; no PPTX. Dashboard/app outputs: deck standard explicitly skipped and stated (§ 10.5).
- Imagery (if any): owner-gated, generated via the image-gen capability into the deck's own `assets/`, placed print-safe (full-bleed scrim / inline / cover) per the craft guide, real-provenance only; absent Gemini, degraded to the fixture placeholder; the locked message unaltered. A deck with no imagery is a valid pass.
- Fresh-eyes: a fresh-context (non-builder) agent reviewed headed against mini-brief + flaw checklist; punch-list (citing items) landed in design-state and was patched BEFORE the owner gate. No scoring/gating/taxonomy.

❌ **FAILURE:**
- The probe offered the `slide-library/tests/` fixture as a real library, forced a non-fitting library, or skipped the owner gate; an [L] run that mixed the library's design system with a fresh trio, or edited the library's `slides/`/`manifest.md`/`presets.md` in place.
- A trio variant rendered headless or via `file://`; a non-pairwise trio presentation.
- A slice worker carrying conversation context instead of resuming from design-state; a slide not conforming to the trio contract.
- A whole-deck regeneration to fix one slide (must be a surgical patch).
- Any charting-library dependency; any PPTX affordance; a missing `@media print` block; a deck output missing the `data-hyp-*` export-metadata attribute set or 1280×720 sizing (§ 10.1–10.3); a dashboard output that incorrectly carries the deck standard without stating the escape.
- A fresh-eyes pass run by the builder (not fresh-context), or one that scores/gates/builds a taxonomy.
- The owner shown the raw first pass before the fresh-eyes punch-list was patched.
