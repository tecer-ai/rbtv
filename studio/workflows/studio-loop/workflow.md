---
name: Studio Loop
description: The artifact-general phase spine for the studio module — one resumable HTML design+communication pipeline (message-lock → art-direction → generate → human-gate). Artifact (deck/site/app) and mode (blank-slate) are PARAMETERS each beat adapts to, never top-level branches. Replaces deck-design.
nextStep: ./beats/beat-01-message-lock.md
artifact: deck
mode: blank-slate
---

# Studio Loop — the Phase Spine

The four-beat HTML pipeline that turns an owner's brief + this project's reference set into an owner-accepted artifact. Two worker classes drive it: the **Strategist** (beat 1 — what to say) hands a content spec to the **Designer** (beats 2–4 — making it awesome and distinct). Behavior is governed by the deck-loop-spec; this entry owns sequencing and the fork parameters, never the behavior.

Read `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/deck-loop-spec.md` (vault-root-relative) for the behavior floor and `{rbtv_path}/studio/architecture.md` for the subsystem map. This file never restates them.

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

**Fork conditional rules (binding on every beat):**

- A beat reads `artifact`/`mode` from design-state FIRST; it NEVER hardcodes `deck`. The deck behavior is the `artifact: deck` branch of each beat's conditional, not the beat's only behavior.
- `artifact: site` or `app` → the beat follows the built fork (`forks/site.md` or `forks/app.md`). If a beat reads an artifact value with no matching fork file present, it HALTS and surfaces "artifact fork file missing — check `forks/`" rather than improvising.
- `mode: audit` → not built in v1; a beat that reads `mode: audit` HALTS with "audit mode deferred — blank-slate only in v1." No beat improvises an audit flow.
- The artifact noun shift (`slide` → `page` for site, `slide` → `screen` for app) is design-state-schema-handled (schema §4); beats use the resolved noun, never a hardcoded "slide" in artifact-general logic.

---

## Resume / Worker-Switch

Any fresh agent — or an incoming worker after a Strategist↔Designer switch — resumes the loop from **design-state + the reference set ALONE**, with zero conversation history (deck-loop-spec ⑨). The mechanism is the resume protocol in `{rbtv_path}/studio/state/design-state-schema.md` §2–3: read design-state's frontmatter cursor (`active_beat` · `beat_status` · `who_acts_next` · `next_action`), load the reference set (HALT on a missing layer), read the content spec and — past beat 2 — the art-direction brief + trio contract, then execute `next_action`. Follow that schema; this file never restates the protocol.

A worker NEVER reads `run-log.md` or `state-capsule.md` — those are conductor/owner surfaces (schema §0).

---

## Entry

The owner reaches the loop through `/rbtv-strategist` (studio), which opens the Strategist persona directly. The Strategist runs beat 1; the Designer (`rbtv-designing` — Vivian) runs beats 2–4. Vivian can also be invoked directly via the `rbtv-designing` skill to resume from a design-state path. The loop does NOT depend on `hypresent/` or `slide-library/`; it renders via the `browser-automation` infra (local HTTP server + headed browser; `file://` is blocked).
