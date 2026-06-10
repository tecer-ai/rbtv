---
name: 'site-fork'
description: 'Studio loop SITE fork — the artifact: site branch. Adds the linear-led multi-page STRUCTURE beat (the genuine fork point) and the responsive multi-page HTML output contract, then rides the deck loop''s art-direction / template / slice / fresh-eyes / human-gate beats parameterized for PAGES. The structure beat is site-only; everything downstream of structure reuses the deck beats unchanged.'
nextStepFile: ../beats/beat-02-art-direction.md
outputFile: content-spec.md
---

# Site Fork — `artifact: site`

The studio loop is artifact-general: `artifact` is a design-state parameter each beat reads, never a top-level branch (workflow.md fork rules). This file is the `artifact: site` branch. It exists because sites genuinely fork from decks at exactly ONE point — the **structure** phase: a deck is slide-led (one linear slide sequence); a site is **linear-led but multi-page** (a sitemap of pages, each with its own communication goal, navigable in any order). After structure, a site rides the deck loop's beats 2–4 with `slide` read as `page`.

Read `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/site-path-spec.md` (vault-root-relative) for the behavior floor and `{rbtv_path}/studio/architecture.md` §1.1/§3 for the subsystem map and landing paths. This file never restates them.

---

## When This Fork Activates

A beat reads `artifact` from the active design-state frontmatter FIRST (workflow.md fork rules). `artifact: site` routes message-lock through the **site structure beat** below instead of the deck slide-narrative path; beats 2–4 then run their existing files with the page-noun substitution recorded in design-state (schema §4 noun handling). `artifact: deck` is unaffected by this file.

| Loop position | `artifact: deck` (proven) | `artifact: site` (this fork) |
|---------------|---------------------------|------------------------------|
| Beat 1 — message-lock (Strategist) | slide-by-slide narrative arc → content spec | **§A site structure beat** below: sitemap + per-page narrative → content spec (one communication goal per page) |
| Beats 2–4 (Designer) | run unchanged on slides | run unchanged on **pages** (§C downstream reuse), honoring the **§B site output contract** |

The Strategist runs beat 1 in the **site-marketing** `{audience_mode}` (`{rbtv_path}/studio/personas/strategist.md` `<mode id="site-marketing">`); the structure beat below is that mode's beat-1 shape.

---

## §A — Site Structure Beat (Strategist; the genuine fork)

The site fork's only NEW beat. Linear-led, multi-page: the Strategist turns a brief into a **sitemap + per-page narrative** — one communication goal per page — with ZERO design decisions, exactly as the deck message-lock makes zero design decisions. This beat REPLACES the deck slide-narrative step (§2 of `beat-01-message-lock.md`) for `artifact: site`; every other part of `beat-01-message-lock.md` (discovery intake, owner-sourced-numbers rule, content-spec emission, design-state init, handoff) applies unchanged. Read `beat-01-message-lock.md` for those shared parts — this file states ONLY the structure fork.

### A.1 Discovery — shared with the deck beat

Run `beat-01-message-lock.md` MANDATORY SEQUENCE step 1 (discovery — brief intake) as written: confirm `{project_name}` + `{audience_mode}` (here `site-marketing`), resolve and HALT on `{output_folder}`, read the brief / project-memo / entity root-level `.md` files, ingest any prior site as CONTENT INPUT ONLY (H1 — never a restyling base). Build the data wishlist; every gap becomes an Open Data Gap. This file does not restate that step.

### A.2 Structure — sitemap + per-page narrative (site-only)

1. State the site's SINGLE controlling thesis — one sentence: what the whole site must make the target audience believe or do, landing the site-marketing arc (audience pain → "WOW I need it" — site-path-spec Quality bar; strategist `<mode id="site-marketing">`).
2. Propose the **sitemap**: the ordered set of pages the site needs (e.g. home / problem / solution / proof / pricing / contact — adapt to the brief, never a reflexive template). The order is the linear-led spine — the argument a first-time visitor walks even though pages are independently navigable.
3. For EACH page, define its **one communication goal** (exactly one per page — a page carrying two goals splits or is rethought, mirroring one-point-per-slide) and its **role in the site arc** (how it advances pain → desire). Give each page a goal-stating working title that states the POINT, not a label (mining map ML-4): "Cut reconciliation from days to minutes" passes; "Features" fails.
4. Identify, per page, WHAT each section must prove and WHERE the owner's verified number for it lives (conceptual data discussion — never present specific numbers unless owner-supplied, mining map ML-5). Imagery needs are noted as a per-page note (what the page must SHOW), not sourced here — sourcing is the §B output contract's job at generation.
5. Challenge every page inline from the site visitor's seat (strategist `<mode id="site-marketing">` enforced craft); for each, assess whether the page earns the next scroll/click and, if not, propose a concrete alternative — NEVER rubber-stamp (mining map SC-1/SI-3). Close with the mode's narrative assessment.
6. Iterate with the owner until the structure is "solid" per the site-marketing lock definition (strategist `<mode id="site-marketing">` `<lock_definition>`). Do NOT proceed to the content spec until the owner and Strategist agree (mining map ML-1).

### A.3 Content spec — emit in the contract format (page-keyed)

1. Write the content spec to `{output_folder}/artifacts/content-spec.md` in the EXACT architecture §5.1 format, with `artifact: site` and `audience_mode: site-marketing` in the frontmatter. Read `beat-01-message-lock.md` step 3 + architecture §5 for the format — this file never restates it. The ONLY substitution: each `### Slide {n}` section is a `### Page {n} — {goal-stating title}` section carrying the page's **one communication goal** (the Point), its **Role in arc**, its per-datum data table (Datum / Value / Communication intent / Source), and its per-page imagery note. `## Narrative Arc` is the sitemap's linear spine.
2. Fill every datum's **Communication intent** (what it must make the visitor feel/conclude) and **Source** (owner-supplied). Any datum lacking an owner source → that page is BLOCKED in its Blocking note AND listed under `## Open Data Gaps`. Never fabricate to unblock (deck-loop-spec ②).
3. Verify against the §5.2 floor-completeness checklist (thesis · one point/goal per page · arc · per-datum intent · owner-sourced numbers · zero design language). A spec failing any row is INCOMPLETE — fix before handoff.

### A.4 Initialize design-state — shared, with the site parameters

Run `beat-01-message-lock.md` step 4 as written, with `artifact: site`, `mode: blank-slate`, `audience_mode: site-marketing` in the frontmatter, and `## Slide Status` seeded one row per PAGE (the schema §4 noun handling renders the row label as page). Set the Strategist→Designer cursor (`active_beat: beat-02-art-direction`, `who_acts_next: Designer`) exactly as the deck beat does. This file does not restate the schema.

---

## §B — Site Output Contract (what the Designer beats produce)

The deck output contract is a full-screen browser deck + print-to-PDF CSS (`beat-03-generate.md` SUB-BEAT 3B). For `artifact: site`, that contract is REPLACED by the responsive multi-page web contract below; every OTHER `beat-03-generate.md` rule (hand-authored charts, ban-list, fresh contexts, surgical patch, local-server render, no `file://`) applies unchanged.

| # | Site output rule | Detail |
|---|------------------|--------|
| 1 | Responsive multi-page HTML | One HTML page per content-spec page, cross-linked per the sitemap. Each page is responsive — readable and intact at desktop AND mobile viewports (site-path-spec behavior row 3). NO print-to-PDF / `@media print` block is required (that is the deck contract); a site targets the screen at multiple widths, not a printed page. |
| 2 | Imagery — real provenance only | Imagery comes via the image-gen capability (`{rbtv_path}/studio/capabilities/image-gen/`) OR owner-supplied assets. NEVER fabricate stock-lookalike photos passed as real photos of real things, people, or places (site-path-spec Output contract; D4 imagery ruling). A page needing an image whose asset is absent HALTS to the owner naming the missing asset — never an invented "real" photo. (The image-gen capability's FIXTURE provider is the quota-independent path — the contract may invoke the capability without assuming live image-gen quota.) |
| 3 | Motion within the direction's character | Animation/motion stays within the chosen direction mini-brief's character (its signature motif + the reference set's motion tokens / subtle-refs report — `extract-subtle-refs` capability). Motion is never decorative noise bolted on; it serves the page's communication goal. **Reduced-motion:** honor `prefers-reduced-motion` — motion degrades gracefully to a static, intact page when the visitor requests reduced motion (site-path-spec Edge Cases). |
| 4 | Charts — unchanged from the deck | Any chart is hand-authored inline SVG/CSS with an action-title — NO charting library (decisions.md p2-2). A library import is a defect, same as the deck. |
| 5 | Render-for-review — unchanged | Render via the local-server pattern (`{rbtv_path}/studio/workflows/browser-automation/`); `file://` is blocked. Review is HEADED at desktop AND mobile viewports (§C / site-path-spec row 3). |

---

## §C — Downstream Reuse (pages ride the deck beats — do NOT duplicate them)

After §A emits the page-keyed content spec and initializes design-state, the run hands off to the Designer and rides the deck loop's beats 2, 3, 4 AS WRITTEN — the site fork builds NO new designer beats. Each beat reads `artifact: site` from design-state and substitutes the page noun. Read each beat file for its mechanics; the table states ONLY the per-page parameterization.

| Beat (reused as-is) | Runs for a site by | Site-specific note |
|---------------------|--------------------|--------------------|
| `beat-02-art-direction.md` | Loading the reference set + taste file; producing ≥2–3 distinct direction mini-briefs (six axes) on the site's references; owner-influenced pick → design-state. | The six axes apply to pages unchanged; the **motion** dimension of the chosen direction is what §B rule 3 then binds. The mini-brief's signature motif governs page-level motion character. |
| `beat-03-generate.md` (3A trio → 3B slices → 3C fresh-eyes) | 3A: a page-template trio (cover/home · content/section · chart) pairwise-picked → visual contract. 3B: each PAGE generated slice-by-slice by a fresh-context worker resuming from design-state ALONE, conforming to the trio contract + the §B output contract. 3C: fresh-eyes pass (non-builder) against the mini-brief + flaw checklist before the owner looks. | "slice" reads as "page". Surgical patch is per-PAGE: a bounce changes only the flagged page; other pages stay byte-identical (deck-loop-spec ④/⑦). The output is §B's responsive multi-page contract, NOT the deck's print-to-PDF contract. |
| `beat-04-human-gate.md` | Headed owner review; accept/bounce-with-notes per page → design-state; surgical per-page patch; bounce-cap (≈3/page) → message-level rethink back to §A (site structure), routed through the Strategist. | **Review at BOTH viewports** (desktop + mobile) — measured geometry sane at each (site-path-spec rows 2–3; fidelity floor). On full accept the loop completes; there is NO print-to-PDF step (that is deck-only) — the accepted artifact is the rendered responsive site itself. A bounce demanding a MESSAGE change routes back to the Strategist (§A), never edited by the Designer. |

**Binding reuse rules:**

- The site fork adds EXACTLY ONE new beat (§A structure) and ONE replaced contract (§B output). Beats 2–4 are the deck beats, parameterized — never copies. Any divergence a future run discovers (a genuine page-only beat need) is a DISCOVERY to surface (PLAN MODIFIED), not a license to fork beats 2–4 here.
- Every beat in the chain has a defined input artifact: §A reads the brief + reference set → emits content-spec + design-state; beat 2 reads content-spec + design-state + reference set → emits art-direction brief + design-state; beat 3 reads those + the trio contract → emits per-page HTML + design-state; beat 4 reads the rendered site + design-state → emits accept/bounce + the accepted site. A fresh agent resumes any point from design-state + the reference set alone (deck-loop-spec ⑨; schema §2).

---

## Resume / Worker-Switch

Identical to the deck path: a fresh agent or a Strategist↔Designer switch resumes from **design-state + the reference set ALONE**, zero conversation history (workflow.md Resume; schema §2–3). The design-state `artifact: site` parameter routes the resuming worker through this fork's structure beat (if pre-beat-2) or straight into the reused designer beats (beat 2+). A worker NEVER reads `run-log.md` or `state-capsule.md`.

---

## Roadmap Boundary

This fork concretizes the `artifact: site` structure beat + output contract + downstream wiring (`p5-5`). It does NOT build: the app fork (`forks/app.md`, separate); production code wiring (coding agents own it); CMS/deployment; SEO copy beyond §A's narrative (site-path-spec Out of Scope). The owner entry surface and any standalone site command are install-set decisions deferred to `p6-3`/`p6-checkpoint` (architecture §2), not built here.
