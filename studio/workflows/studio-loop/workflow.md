---
name: Studio Loop
description: The artifact-general phase spine for the studio module — one resumable HTML design+communication pipeline (message-lock → art-direction → generate → human-gate). Artifact (deck/site/app) and mode (blank-slate) are PARAMETERS each beat adapts to, never top-level branches. Replaces deck-design.
nextStep: ./beats/beat-01-message-lock.md
artifact: deck
mode: blank-slate
---

# Studio Loop — the Phase Spine

The four-beat HTML pipeline that turns an owner's brief + this project's reference set into an owner-accepted artifact. Two worker classes drive it: the **Strategist** (beat 1 — what to say) hands a content spec to the **Designer** (beats 2–4 — making it awesome and distinct). Behavior is governed by the deck-loop-spec; this entry owns sequencing and the fork parameters, never the behavior.

Read `{rbtv_path}/studio/deck-loop-spec.md` for the behavior floor and `{rbtv_path}/studio/architecture.md` for the subsystem map. This file never restates them.

---

## Intake Routing Gate (run FIRST, before beat 1)

Before entering any beat, classify the request against the table below. A request that hands an EXISTING built artifact plus comments/targeted fixes is NOT a blank-slate run — routing it into beat-01 discards the existing structure and locks a fresh narrative (the 2026-06-18 mis-route: 17 targeted fixes became a 9-slide ground-up rebuild, deleted by the owner). The signal MUST be detected here and routed, never silently run as blank-slate.

| Signal | `mode` | Route |
|--------|--------|-------|
| Brief + verified numbers, NO existing artifact to revise (a prior deck supplied as content input ONLY is still this row) | `blank-slate` | Beat 1 → 4 as written. |
| An EXISTING artifact file (a built deck/site/app `.html`) + review comments OR targeted fixes to apply on it (owner says "apply these comments", "implement this feedback", "address the review notes", "make these edits to the deck") | `audit` | TWO-PHASE SURGICAL REVISION below. |

**Two-phase surgical revision (`mode: audit`):**

`mode: audit` is the improve-existing path and is DEFERRED — no audit beat is built in v1. On detecting the signal you MUST HALT with `audit mode deferred — blank-slate only in v1` AND route the owner to the two-phase surgical flow (the route is built; the wired-into-beats audit mode is not):

- **PHASE 1 — Strategist (message/narrative, surgical).** Revise the message working FROM the existing artifact and its comments. This is NOT blank-slate beat-01: the existing structure is the base, NOT content input to discard. Read the existing artifact and its comments (deck comments live in the file's `#hyp-comments` island + agent-instruction block per `{rbtv_path}/studio/workflows/hypresent-comments/comment-implementation.md` § Locate the Comments First). Change ONLY the narrative the comments call for; preserve every un-commented slide/page/screen, its order, and its frame. Produce NO HTML. If the existing structure has no comments and no narrative change is implied, Phase 1 is a no-op — go straight to Phase 2.
- **PHASE 2 — Designer (implementation).** The Designer (`rbtv-designing` — Vivian) implements the revision into a versioned copy via `{rbtv_path}/studio/workflows/hypresent-comments/comment-implementation.md` (the surgical comment-implementation workflow — version-never-overwrite, change only flagged elements + entailed ripples, preserve all other structure).

NEVER skip Phase 1 by routing straight to the Designer (the narrative revision is the Strategist's, and the Designer never re-derives it). NEVER improvise a blank-slate build on this signal. If the owner genuinely wants a from-scratch rebuild of an existing artifact, that is a `blank-slate` run — confirm it EXPLICITLY with the owner first (the default on an existing-artifact + comments signal is always surgical).

---

## The Four Beats (sequential — each beat ends at a menu and HALTS)

| Beat | File | Worker | Produces |
|------|------|--------|----------|
| 1 — message-lock | `./beats/beat-01-message-lock.md` | Strategist | Content spec (architecture §5) + initialized design-state. Zero design decisions. |
| 2 — art-direction | `./beats/beat-02-art-direction.md` | Designer | ≥2–3 distinct direction mini-briefs on the loaded reference set; owner-picked direction recorded in design-state. |
| 3 — generate | `./beats/beat-03-generate.md` | Designer | Template trio (pairwise pick) → full deck slice-by-slice via fresh contexts → fresh-eyes pass. |
| 4 — human-gate | `./beats/beat-04-human-gate.md` | Designer | Headed accept/bounce; surgical patch; bounce-cap ≈3/slide → message rethink (back to beat 1). |

Communication beats (1) produce NO design; design beats (2–4) NEVER alter the locked message. The Strategist↔Designer switch happens ON DISK through design-state — never through conversation (schema §3).

---

## Fork Parameters — `artifact` and `mode` (keyed like the office pitch `{pitch_type}` conditional)

The spine is artifact-general. Each beat reads two parameters from the active design-state frontmatter and adapts — there is NO per-artifact workflow branch. Resolution order: the beat reads `artifact` and `mode` from design-state; if design-state does not yet exist (beat 1, run start), the Strategist sets them at init from the owner's brief.

| Parameter | Values | What it adapts | Resolved by |
|-----------|--------|----------------|-------------|
| `artifact` | `deck` · `site` · `app` | The row noun and discovery shape: `deck` → slides; `site` → pages (multi-page, image/animation-led; see `forks/site.md`); `app` → screens (discovery forks to goal→user-flow; output = plain HTML UI + UX companion docs; see `forks/app.md`). All three forks are built; site/app forks live at `forks/site.md` and `forks/app.md`. | design-state `artifact`; default `deck` (this file's frontmatter) |
| `mode` | `blank-slate` · `audit` (deferred) | Whether the run starts from nothing (blank-slate) or audits an existing artifact (audit/improve-existing — deferred to a future plan, never built in v1). | design-state `mode`; default `blank-slate` |
| `critic` | `on` · `off` | Whether the v1.1 structural critic runs its comparative taxonomy pass at the design beats. Advisory only — it NEVER gates the loop. | design-state `critic`; default `off` |

**Fork conditional rules (binding on every beat):**

- A beat reads `artifact`/`mode` from design-state FIRST; it NEVER hardcodes `deck`. The deck behavior is the `artifact: deck` branch of each beat's conditional, not the beat's only behavior.
- `artifact: site` or `app` → the beat follows the built fork (`forks/site.md` or `forks/app.md`). If a beat reads an artifact value with no matching fork file present, it HALTS and surfaces "artifact fork file missing — check `forks/`" rather than improvising.
- `mode: audit` → the improve-existing path; the wired-into-beats audit mode is not built in v1. A beat that reads `mode: audit` HALTS with "audit mode deferred — blank-slate only in v1" and routes to the two-phase surgical revision (§ Intake Routing Gate) — it NEVER improvises a blank-slate build and NEVER skips the Strategist's Phase 1 by going straight to the Designer.
- The artifact noun shift (`slide` → `page` for site, `slide` → `screen` for app) is design-state-schema-handled (schema §4); beats use the resolved noun, never a hardcoded "slide" in artifact-general logic.

---

## Resume / Worker-Switch

Any fresh agent — or an incoming worker after a Strategist↔Designer switch — resumes the loop from **design-state + the reference set ALONE**, with zero conversation history (deck-loop-spec ⑨). The mechanism is the resume protocol in `{rbtv_path}/studio/state/design-state-schema.md` §2–3: read design-state's frontmatter cursor (`active_beat` · `beat_status` · `who_acts_next` · `next_action`), load the reference set (HALT on a missing layer), read the content spec and — past beat 2 — the art-direction brief + trio contract, then execute `next_action`. Follow that schema; this file never restates the protocol.

A worker NEVER reads `run-log.md` or `state-capsule.md` — those are conductor/owner surfaces (schema §0).

---

## Entry

The owner reaches the loop through `/rbtv-strategist` (studio), which opens the Strategist persona directly. The Strategist runs beat 1; the Designer (`rbtv-designing` — Vivian) runs beats 2–4. Vivian can also be invoked directly via the `rbtv-designing` skill to resume from a design-state path. The loop does NOT *require* `hypresent/` or `slide-library/`; it renders via the `browser-automation` infra (local HTTP server + headed browser; `file://` is blocked). Beat 3 MAY *optionally* reuse a spec-compliant slide library found in the working repo when one fits the deck (owner-gated — beat-03 § 3·0); absent one, it builds bespoke and never writes into the convention's `slide-library/`.
