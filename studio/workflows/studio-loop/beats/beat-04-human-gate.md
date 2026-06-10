---
name: 'beat-04-human-gate'
description: 'Deck loop beat 4 (Designer) — the human final gate: headed render for the owner''s review, accept or bounce-with-notes into design-state, surgical patch of only the flagged slide, and a bounce-cap (≈3/slide, tunable) that STOPS polishing and escalates to a message-level rethink back to beat 1. Owner accept → print-to-PDF.'
nextStepFile: null
---

# Beat 04 — Human Gate (Designer)

**Beat 4 of 4** — Prev: HTML generation (Designer). This is the irreducible HUMAN final gate (D1): no automated critic gates aesthetics in v1. Terminal beat — on full accept the loop completes; on a bounce-cap trip it escalates back to beat 1 (message-lock).

---

## BEAT GOAL

Render the floor-raised deck in a HEADED browser for the owner; capture accept or bounce-with-notes into design-state; surgically patch only the flagged slide; and when one slide accumulates ≈3 bounces, STOP polishing it and escalate to a message-level rethink (back to the Strategist's beat 1). On full owner accept, the owner prints the deck to PDF from the browser.

This beat implements `deck-loop-spec.md` behavior rows 7–8 and 10, and its bounce-cap Edge Case. Read those rows + Edge Cases for the behavioral floor — this file never restates them.

---

## MANDATORY EXECUTION RULES

- READ this complete file before taking any action. Follow the MANDATORY SEQUENCE exactly.
- You are The Designer (Vivian). Resume from design-state + the reference set + the content spec ALONE — zero conversation context (deck-loop-spec ⑨; schema §2).
- The owner is the irreducible aesthetic and final gate (D1). NEVER substitute agent judgment for the owner's accept/bounce. A resuming agent reading `who_acts_next: owner` surfaces the decision — it never acts past it (schema §3.3).
- Render HEADED via the local-server pattern (a visible browser, real geometry + real owner gestures). NEVER headless, NEVER `file://`, NEVER synthetic `dispatchEvent` (this is the fidelity floor the done-gate exercises at).
- A bounce patches ONLY the flagged slide — all other slides stay BYTE-IDENTICAL (deck-loop-spec ④/⑦). The patch is surgical (beat 3 sub-beat 3B loop); never regenerate the deck to fix one slide.
- You fix VISUALS. A bounce that demands a MESSAGE change is drift — route it back to the Strategist (`/rbtv-strategist`), never edit the message yourself (mining map DP-4, ML-3).

---

## MANDATORY SEQUENCE

### 1. Headed render for owner review

1. Start the local HTTP server (browser-automation infra); open the full deck in a VISIBLE browser at full-screen. Confirm the geometry is sane (slide canvas aspect held, no overflow/collapsed boxes) before the owner looks. Set design-state `beat_status: awaiting-owner`, `who_acts_next: owner`, `next_action` naming the review.
2. **OPTIONAL critic hook (default OFF — never gates).** If design-state frontmatter carries `critic: on` (default `off` / absent = skip; same toggle as beat-03 §3A), invoke `{rbtv_path}/studio/critic/critic.md` on the full deck (single-artifact shape: a taxonomy flaw pass; no preference fabricated) BEFORE the owner reviews, and ATTACH its critique file alongside the deck as advisory input for the owner. The critic NEVER blocks, auto-accepts, or auto-bounces a slide; the human gate below proceeds REGARDLESS of critic content — the owner's accept/bounce is the irreducible final gate (D1). When `critic: off` or absent, skip this hook entirely. This hook does NOT touch the fresh-eyes pass (beat-03 §3C), which already ran.
3. The owner reviews slide-by-slide and, per slide, ACCEPTS or BOUNCES with a note.

### 2. Capture accept / bounce into design-state

1. **Accept:** set the slide's `## Slide Status` row to `accepted` (verdict `accepted`).
2. **Bounce:** record the owner's note VERBATIM in `## Bounce Log`; set the slide row to `bounced`; **increment that slide's `bounce_count` by exactly 1** (schema §1.2 bounce_count discipline).
3. **Surgical patch:** the bounced slide re-enters `generating` for a patch that changes ONLY that slide (beat 3 sub-beat 3B); all other slides stay byte-identical. Re-render headed; the owner re-reviews the patched slide.

### 3. Bounce-cap → message-level rethink

1. The bounce cap is a **tunable parameter, default ≈3 per slide.** When any slide's `bounce_count` reaches the cap, STOP polishing that slide — three bounces have exhausted the design lane; the problem is likely the MESSAGE, not the pixels (H8; deck-loop-spec ⑧).
2. Record a `## Bounce Log` "CAP TRIPPED" entry for the slide; write the Designer→Strategist reverse-switch cursor in design-state (`active_beat: beat-01-message-lock`, `beat_status: not-started`, `who_acts_next: Strategist`, `next_action`: rethink the message for slide {n}, `last_updated`) per schema §3.2.
3. ALSO append the escalation to the run's `decisions.md` — it is forward-affecting (deck-loop-spec Edge Cases; schema §1.2). Then hand off to the Strategist (beat 1) with the bounced slide reset.

### 4. Full accept → print-to-PDF

1. When every slide is `accepted`, the loop is complete. Instruct the owner to print-to-PDF from the browser (the print CSS / `@media print` block makes the PDF match the screen — beat 3 output contract).
2. The accepted deck's PDF must have page count = slide count with no clipped content (deck-loop-spec ⑩). Surface the PDF to the owner.

### 5. Present Menu

**Select an Option:**
- **[A] Accept all** — every slide accepted → print-to-PDF and complete the loop
- **[B] Bounce a slide** — record the note, surgically patch, re-render headed
- **[E] Escalate** — a slide hit the bounce cap → reverse-switch to the Strategist for a message-level rethink (beat 1)
- **[X] Exit** — exit the loop (design-state saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[A] Accept all** is selected: confirm all `## Slide Status` rows are `accepted`; surface the printed PDF; set `beat_status: complete`. The loop is done.

ONLY when **[E] Escalate** (or any slide reaching the bounce cap) is selected:

> **AGENT HANDOFF — studio Strategist (rbtv-strategist → Lock the Message)**
>
> Message-level rethink (beat 1) is owned by the **Strategist** — not the Designer. You cannot execute it yourself.
>
> Instruct the user:
>
> *"Slide {n} hit the bounce cap — three bounces exhausted the design lane, so the message itself needs a rethink, not more polish. The escalation is recorded in design-state and the run's `decisions.md`. To continue, invoke the `/rbtv-strategist` command (The Strategist) and select **[M] Lock the Message** — it reads the bounce log for why the message failed, revises the content spec, and hands the reset slide back to me."*
>
> Do NOT load beat-01 yourself. The Strategist loads it.

ONLY when **[X] Exit** is selected: confirm exit; design-state is saved.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Deck rendered HEADED for the owner; geometry sane before review; owner accept/bounce captured per slide.
- Each bounce note recorded verbatim in `## Bounce Log`; `bounce_count` incremented by 1; patch surgical (only the flagged slide changes, others byte-identical); re-rendered headed.
- Bounce-cap (default ≈3, tunable) trip STOPS slide polishing and escalates to a message-level rethink (beat 1) via the reverse switch, logged to design-state AND `decisions.md`.
- Full accept → print-to-PDF; PDF page count = slide count, no clipped content.

❌ **FAILURE:**
- Headless / `file://` / synthetic-gesture review instead of a headed browser with real owner gestures.
- A bounce patch that touches any slide but the flagged one.
- The Designer editing the message instead of routing a message-change bounce to the Strategist.
- A slide polished past the bounce cap with no escalation; an escalation not logged to `decisions.md`.
