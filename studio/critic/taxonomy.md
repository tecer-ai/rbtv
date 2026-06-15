---
type: knowledge
module: studio
created: 2026-06-10
status: active
---

# Studio Critic — Structural Flaw Taxonomy

The explicit flaw taxonomy the critic cites — the dataset that makes critique taxonomy-driven rather than open-ended ("tell me what's wrong"). Evidence: open-ended critique is weak (F1 0.33–0.66) while taxonomy-guided critique detects and remediates better [S3]. Every structural finding the critic emits names a taxonomy item ID below and the offending element.

This is a **module-internal knowledge file** — not a `.claude/` rule. Read `studio/critic/critic.md` for how the critic consults it.

## Relationship to ban-list / flaw-checklist (BORROW, never duplicate)

This taxonomy **borrows by citation** from two existing standards — it does not restate their rows:

- `studio/standards/ban-list.md` — the per-artifact attractor catalogue (what a single output must avoid). Taxonomy items below carry a `Borrowed from` column pointing at the ban-list/mining-map IDs they generalize.
- `studio/standards/flaw-checklist.md` — the fresh-eyes single-deck punch-list. **DISTINCT mechanism (architecture §1.4, critic-spec Context Snapshot):** fresh-eyes is a prompt-file review in a fresh session producing a per-slide punch-list — no taxonomy IDs, no comparison, no scoring. This taxonomy is the critic's COMPARATIVE dataset: each item carries a `Comparative cue` (how the item discriminates A-vs-B), which fresh-eyes' checklist deliberately lacks. The two never merge: a worker may run fresh-eyes (single deck, punch-list) AND the critic (comparison, taxonomy-cited) on the same run; neither replaces the other.

A flaw genuinely structural but not in this taxonomy is still reported, tagged `T-UNCAT` with a one-line spotting cue (mirrors the flaw-checklist Reviewer-note discipline) — and named in the critic's output so the taxonomy can grow.

## How the critic uses an item

For each item: the critic determines, per artifact, the **direction and degree** of the flaw, then states which artifact is **stronger on that axis** with the cited item ID and the offending element. NEVER an absolute score (no 1–10, no %, no grade) — only A-vs-B / rank per axis. The `Comparative cue` column is the discriminator.

---

## Axis 1 — Hierarchy & Message

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-H1 | A slide carries more than one idea | Two competing focal elements; eye cannot land on one point in 1s | Which artifact lands ONE point per slide more cleanly across the set | flaw-checklist 1; ban H2; PR-4/SL-1 |
| T-H2 | Title labels the topic instead of stating the takeaway | A title reads "Market" not "$4.2B SAM, bottom-up" | Which artifact's titles state takeaways vs labels on more slides | ban H3; ML-4 |
| T-H3 | Narrative arc not legible from the slide order | Slides do not build to a thesis; order feels arbitrary | Which ordering advances a clearer argument | beat-01 arc floor |

## Axis 2 — Contrast & Legibility

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-C1 | Low contrast or undersized type | Body <15px, nodes <14px, cells <13px; any text strains to read at full-screen | Which artifact holds the legibility floor on more elements | flaw-checklist 2; ban E-1; T-1 |
| T-C2 | Key content not at the top of the slide | Primary message buried mid/low; reader scans to find it | Which artifact front-loads the point more consistently | flaw-checklist 2; PR-4 |

## Axis 3 — Alignment & Spacing

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-A1 | Title position drifts slide-to-slide | Title vertical anchor jumps; content slides mix centered + top-aligned | Which artifact anchors titles at one position across the set | flaw-checklist 3; ban B-1; V-1 |
| T-A2 | Spacing rhythm sparse or uneven | Header-to-content gap >40px; whitespace accidental not intentional (<~15%) | Which artifact's rhythm reads intentional vs dead | flaw-checklist 4; AD-4/L-4 |

## Axis 4 — Overflow & Density

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-D1 | Content overruns the slide / clipping | A block pushed past ~70vh or clipped at the slide edge | Which artifact avoids overflow on more slides | flaw-checklist 5; ban D-1; L-2/L-4 |
| T-D2 | Too many content zones / undifferentiated zones | >3 zones per slide; zones with no `.zone-label` that merge visually | Which artifact respects the ≤3-zone ceiling | flaw-checklist 5; ban D-2; L-3 |
| T-D3 | Grid card-count exceeded | `.grid-3` >6 cards / 2 rows; grids switched mid-deck without a visual reason | Which artifact respects grid ceilings | ban D-1; L-2 |
| T-D4 | DOM layout fragment — element outside its containing block | A flow/grid element rendered as a loose direct child of `.slide`, outside its intended containing block (its zone/grid wrapper) | Which artifact keeps every flow/grid element nested inside its containing block | cold-verify finding |

## Axis 5 — Type & Color System

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-T1 | Type-pairing inconsistency | >2 fonts; type scale arbitrary per slide; mixed icon libraries on one semantic set | Which artifact holds 1–2 fonts + one icon library more consistently | flaw-checklist 6; ban A-3/A-4/E-2; T-3 |
| T-T2 | Color-system incoherence | Stat colors mixed within a semantic group; `var(--danger)` on non-negative values; colored borders random/diagonal | Which artifact's color logic is more systematic | flaw-checklist 7; ban E-4/E-5; C-2/C-4 |
| T-T3 | Training-mean / placeholder palette | Purple-blue gradient; stock `:root` values | Which artifact reads brand-grounded vs default-attractor | ban A-1/E-3; C-1 |
| T-T4 | Client logo recolored | Logo white/black knockout, inverted, tinted, or hue-shifted to fit a slide instead of shown in its original brand colors | Which artifact preserves the logo's true colors (recolored = flaw) | flaw-checklist 14; ban E-6 |
| T-T5 | Source citations inline / mid-text | A `(Source: …)` or reference beside the claim in the body instead of a footnote at the slide bottom | Which artifact anchors source citations as bottom footnotes | flaw-checklist 13; ban F-5 |

## Axis 6 — Component Weight

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-W1 | Comparison grid rendered equal-weight | Competitor cards identical to the product card (no winner emphasis) | Which artifact emphasizes the product card vs flat comparison | flaw-checklist 8; ban F-1; CP-1 |
| T-W2 | Before/after columns equal-weight | Both sides identical; transformation not shown | Which artifact weights "after" over "before" | flaw-checklist 8; ban F-4; CP-5 |
| T-W3 | Risk / decision-gate statements as footnotes | Failure modes / kill criteria buried, not first-class callouts | Which artifact treats risk/gates as first-class content | flaw-checklist 8; ban F-2; CP-3 |

## Axis 7 — Chart Communication

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-CH1 | Chart labels axes instead of the takeaway | Chart title is an axis name, not "Revenue up 340% YoY" | Which artifact's charts state takeaways | flaw-checklist 9; ban H3; AD-3 |
| T-CH2 | Chart unreadable / connectors vanish | Scatter <500×380px or labels <13px; flow connectors 1px gray (disappear in PDF) | Which artifact's charts stay readable | flaw-checklist 9; ban F-3; CP-4 |

## Axis 8 — Cover/Closing & Parity

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-P1 | Overloaded cover / mismatched bookends | Cover carries product defs/multi-sentence text; cover ≠ closing in bg/type/layout | Which artifact's bookends are cleaner + matched | flaw-checklist 10; ban B-3/B-4; V-3/V-4 |
| T-P2 | Team/card parity broken | Differential card styling (one accented); uneven bio depth across cards | Which artifact holds card parity | flaw-checklist 11; ban B-2/B-5; V-2/SR-2 |

## Axis 9 — Data Integrity (credibility)

> Critique surfaces these where DETECTABLE from the rendered artifact (e.g. a bare SAM/TAM, a nickname, a relabeled stat visible on the slide). The critic flags the tension; it NEVER fabricates the correct value — that is owner/Strategist territory (beat-01).

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-DI1 | Unexplained / bare market figures | SAM/TAM unspelled; a market number with no one-line context | Which artifact makes numbers self-explanatory | ban C-5; D-5 |
| T-DI2 | Informal names / fabricated-looking titles visible | Nicknames in a formal deck; a title that looks inferred | Which artifact reads more credible (flag only; never invent) | ban C-1/C-2; D-1/D-2 |

## Axis 10 — Print/PDF Safety

| ID | Flaw | How to spot it (per artifact) | Comparative cue (A-vs-B) | Borrowed from |
|----|------|-------------------------------|--------------------------|---------------|
| T-PR1 | Print-unsafe construction on render-to-PDF elements | `aspect-ratio`, transforms on positioned elements, pseudo-element structural content, complex `clip-path`; no `@media print` block | Which artifact is more PDF-safe (diagram slides are highest risk — flag first) | flaw-checklist 12; ban G-1/G-2; P-1/P-3 |

---

## What this taxonomy is NOT

- **NOT aesthetic.** Distinctiveness, taste, "does it feel world-class" are NOT taxonomy items — they route to the critic's advisory-to-human section, never scored, never compared as a verdict (critic-spec Behavior row 3).
- **NOT a gate.** No item produces a pass/fail. A taxonomy citation is a comparative observation, never a stop condition (critic-spec Out of Scope).
- **NOT fresh-eyes.** Fresh-eyes runs the flaw-checklist on ONE deck for a punch-list with no taxonomy/comparison; this taxonomy powers the critic's COMPARATIVE pass. Both exist; neither replaces the other.
