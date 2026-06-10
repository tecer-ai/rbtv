# Design-State Schema — the Studio Loop's Working Memory

> The schema for `design-state.md`: the module-level state file every studio run (deck / site / app) maintains. It carries everything a fresh agent — or an incoming worker after a Strategist↔Designer switch — needs to resume the loop mid-flight from **design-state + the reference set ALONE**, with zero conversation history (deck-loop-spec behavior ⑨). Authored at `p1-5`; slot fixed by `architecture.md` §8. Behavior specs in the plan folder (`deck-loop-spec.md`) own the *what* the loop does; this doc owns the *shape* of the state it carries.

---

## 0. What design-state IS — and is NOT

| Fact | Value |
|------|-------|
| What it is | The loop's **mutable working memory** — one file per run, living with the run's output |
| Where it lives | `{output_folder}/artifacts/design-state.md` — the same `{output_folder}` the content spec resolves to (`architecture.md` §5), back-pointed by the content spec's `design_state:` frontmatter |
| Who maintains it | The active worker (Strategist in beats 1–2, Designer in beats 2–4) overwrites the fields it owns as the loop advances |
| Who reads it | Any loop worker, on dispatch — ALONGSIDE its own task file and the run's `decisions.md`. A fresh agent resuming the run reads it FIRST |
| Mutability | Mutable (overwritten in place); it is a live snapshot, not an append-only log. The append-only audit is the spine's `run-log.md`, which design-state never duplicates |

**Binding boundary (architecture §8 + the orchestration state card §1/§5):** design-state is a **fourth ARTIFACT, never a fourth SPINE FILE.** It RIDES the orchestration three-file state spine (`run-log.md` · `state-capsule.md` · `decisions.md`); it does not replace, extend, or join it.

| Spine file | design-state's relation |
|------------|-------------------------|
| `decisions.md` (worker-facing, append-only) | A worker reads design-state ALONGSIDE the run's `decisions.md`. Design-state is the loop's working memory; `decisions.md` is the run's forward-affecting decision log. A loop decision that changes FUTURE work (e.g. a bounce-cap escalation) is recorded in BOTH: the working state here, the forward signal in `decisions.md` (deck-loop-spec Edge Cases). |
| `state-capsule.md` (mutable resume, conductor-facing) | The conductor's capsule POINTS AT the active design-state file (its path is the resume handle); the per-slide status and bounce notes live HERE, not in the capsule. Workers NEVER read the capsule. |
| `run-log.md` (append-only audit, owner-facing) | A worker NEVER reads it. design-state carries NONE of its audit role — no event rows, no files-changed lists, no dispatch ledger. |

> Restate of the iron rule a worker must honor: **a loop worker reads its task file + the run's `decisions.md` + this design-state file. It NEVER reads `run-log.md` or `state-capsule.md`.** Those are conductor/owner surfaces.

---

## 1. The Payload — full schema

design-state is a single markdown file: YAML frontmatter for the stable, machine-keyable facts, then markdown body sections for the evolving per-slide detail. The eight payload groups (deck-loop-spec Context Snapshot; architecture §8) map as follows.

| # | Payload group | Lives in | Owner who writes it |
|---|---------------|----------|---------------------|
| 1 | Project meta | frontmatter | Strategist (init) |
| 2 | Artifact + mode | frontmatter | Strategist (init) |
| 3 | Active phase/beat + who-acts-next | frontmatter | the worker that just finished a beat |
| 4 | Content-spec reference | frontmatter (path, NOT inlined) | Strategist (beat 1) |
| 5 | Chosen art direction | frontmatter ref + `## Art Direction` body | Designer (beat 2) |
| 6 | Per-slide HTML status | `## Slide Status` table | Designer (beat 3) |
| 7 | Accept/bounce notes + per-slide bounce COUNT | `## Slide Status` table + `## Bounce Log` | Designer (beat 4 / human gate) |
| 8 | Fresh-eyes punch-lists | `## Fresh-Eyes Punch-List` | Designer (beat 3 fresh-eyes pass) |

### 1.1 Frontmatter (groups 1–5 stable keys)

```yaml
---
type: design-state
schema_version: 1

# ── Group 1: Project meta ─────────────────────────────
project: '{project_name}'              # human-readable project name
owner: '{owner}'                       # the human final gate (D1)
reference_set: '{vault-root-relative path to the workspace reference set}'
                                       # e.g. 5-workbench/tecer-biz/brand/studio-references/
                                       # the FOUR-layer set the run loads (tokens · exemplars · taste · chart exemplar)

# ── Group 2: Artifact + mode ──────────────────────────
artifact: deck                         # deck | site | app  — the PROCESS parameter
mode: blank-slate                      # blank-slate (audit/improve-existing deferred)
audience_mode: investor                # investor | client | site-marketing | app-product (Strategist mode)

# ── Group 3: Active phase/beat + who-acts-next ────────
active_beat: beat-03-generate          # beat-01-message-lock | beat-02-art-direction
                                       #   | beat-03-generate | beat-04-human-gate
beat_status: in-progress               # not-started | in-progress | awaiting-owner | complete
who_acts_next: Designer                # Strategist | Designer | owner   ← THE single resume cursor
next_action: 'Generate slides 4–7 slice-by-slice under the chosen trio contract'
                                       # one plain sentence: the exact next gesture the run is waiting on

# ── Group 4: Content-spec reference (path, NEVER inlined) ──
content_spec: ./content-spec.md        # the Strategist→Designer contract (architecture §5);
                                       # design language lives HERE in design-state, never in the content spec

# ── Group 5: Chosen art direction (ref + rationale) ───
art_direction_brief: '{path to the picked mini-brief}'   # e.g. ./art-direction/brief-b.md
art_direction_pick_rationale: 'Owner picked B: editorial serif + restrained palette best carries the
                               "credible challenger" thesis; rejected A (too playful) and C (too corporate).'
trio_contract: ./art-direction/trio-winning.md           # the pairwise-picked template trio = the deck's visual contract (H5)

last_updated: '{YYYY-MM-DDTHH:MMZ}'    # set on every overwrite — the freshness stamp a resumer checks
---
```

> **Path-not-payload rule (groups 4–5):** the content spec and the art-direction mini-brief are referenced **by path**, never copied in. design-state points; it does not duplicate. This keeps the content spec the single source of the *message* and the mini-brief the single source of the *direction*, with design-state as the cursor over both.

### 1.2 Body sections (groups 5–8 evolving detail)

````markdown
# Design-State — {project_name}

## Art Direction
{1–3 sentence record of the chosen direction in the owner's terms — the same direction the `art_direction_brief`
 frontmatter points at, summarized so a resumer needn't open the brief to know the lane. The authoritative
 detail (type pairing · palette · grid principle · signature motif · chart style · cover treatment) lives in
 the referenced mini-brief; this section is the at-a-glance pin, not a copy.}

## Slide Status
> One row per slide (or page / screen for site / app). Group 6 (HTML status) + Group 7 (accept/bounce + COUNT).
> `bounce_count` is the field the **H8 ≈3-per-slide cap reads** (deck-loop-spec ⑧).

| # | Slide title | HTML status        | Owner verdict | bounce_count | Last bounce note (ref) |
|---|-------------|--------------------|---------------|-------------|------------------------|
| 1 | {title}     | accepted           | accepted      | 0           | —                      |
| 2 | {title}     | rendered           | bounced       | 2           | see Bounce Log ↓       |
| 3 | {title}     | generating         | —             | 0           | —                      |
| 4 | {title}     | blocked            | —             | 0           | BLOCKED: datum lacks owner source (deck-loop-spec ②) |

**HTML status values:** `not-started` → `generating` → `rendered` (in headed browser, awaiting owner) → `accepted`.
Plus two off-path states: `bounced` (owner returned it with a note — re-enters `generating` for a surgical patch)
and `blocked` (a claim lacks an owner-supplied source; the slide halts, never fabricated — deck-loop-spec ②).

**`bounce_count` discipline:** increment by exactly 1 each time the owner bounces THIS slide (group 7). When any
slide's `bounce_count` reaches ≈3, the loop STOPS polishing it and escalates to a message-level rethink — back to
beat 1 (H8 / deck-loop-spec ⑧). The escalation is recorded in `## Bounce Log` below AND in the run's `decisions.md`
(deck-loop-spec Edge Cases). The cap is tunable from v1 runs.

## Bounce Log
> Append-within-this-file accept/bounce notes (group 7). Each bounce the owner makes lands here verbatim so the
> surgical-patch worker (beat 4) and any resumer see exactly what to change. A patch changes ONLY the flagged
> slide — all others stay byte-identical (deck-loop-spec ④/⑦).

- **Slide {n} — bounce {k} ({YYYY-MM-DD}):** "{owner's note, verbatim}" → patch: {what changed, one line}.
- **Slide {n} — CAP TRIPPED (bounce 3, {YYYY-MM-DD}):** escalated to message-level rethink (beat 1); logged to `decisions.md`.

## Fresh-Eyes Punch-List
> Group 8. The output of the fresh-eyes pass (beat 3, H6): a fresh-context review of the full pass against the
> chosen mini-brief + the ~10-item flaw checklist, BEFORE the owner ever looks. This is NOT the v1.1 critic —
> no scoring, no gating, no taxonomy (deck-loop-spec ⑥). One punch-list per full pass.

- **Pass {p} ({YYYY-MM-DD}):**
  - [ ] Slide {n}: {flaw, referencing the checklist item} → {patch} — open
  - [x] Slide {n}: {flaw} → {patch} — applied
````

---

## 2. Resume Protocol — a fresh agent picks up mid-loop

The contract that makes deck-loop-spec behavior ⑨ true: **any fresh agent resumes the loop from design-state + the reference set ALONE — zero conversation history.** A worker resuming runs these steps before touching the work.

| Step | Action | Answers |
|------|--------|---------|
| 1 | Read `design-state.md` (this file) at the path the conductor's dispatch hands you. | — |
| 2 | Read the **frontmatter** top-to-bottom. `active_beat` + `beat_status` + `who_acts_next` + `next_action` tell you **WHERE the run is and WHAT it is waiting on**; `who_acts_next` tells you **WHO acts** (and therefore whether YOU are that worker). | **where am I · what is next · who acts** |
| 3 | Load the **reference set** at the `reference_set` path (the four layers: tokens · exemplars · taste · chart exemplar). HALT with the named missing layer if any layer is absent — never proceed on training-mean defaults (deck-loop-spec Edge Cases). | the taste/token ground the loop enforces |
| 4 | Read the **content spec** at `content_spec` (the message — thesis, one point per slide, arc, per-datum intent) and, if past beat 2, the **art-direction brief** at `art_direction_brief` + the `trio_contract` (the visual contract). | the locked message + chosen direction |
| 5 | Read the **body sections** for live detail: `## Slide Status` (which slides are done / generating / bounced / blocked), `## Bounce Log` (outstanding owner notes to apply), `## Fresh-Eyes Punch-List` (open items). | the exact per-slide state |
| 6 | Read the run's `decisions.md` (the conductor's dispatch carries its pointer) for any forward-affecting ruling — e.g. a logged bounce-cap escalation. **NEVER read `run-log.md` or `state-capsule.md`.** | rulings in force |
| 7 | Execute `next_action`. On finishing the beat, OVERWRITE the frontmatter cursor (`active_beat` / `beat_status` / `who_acts_next` / `next_action`) and `last_updated`, and update the body sections you changed. | the run advances, not restarts |

**The three resume questions, each answerable from this file alone:**

| Question | Answered by |
|----------|-------------|
| **Where am I?** | `active_beat` + `beat_status` (frontmatter), refined by `## Slide Status` |
| **What is next?** | `next_action` (frontmatter), with open items in `## Bounce Log` + `## Fresh-Eyes Punch-List` |
| **Who acts?** | `who_acts_next` ∈ {Strategist, Designer, owner} (frontmatter) |

---

## 3. Worker-Switch Protocol — Strategist ↔ Designer handoff

The two worker classes (architecture §1.2): the **Strategist** (discover → narrative → content spec) hands to the **Designer** (art-direction → layout → visual). The switch happens ON DISK through design-state + the content spec — never through conversation. design-state's `who_acts_next` field IS the handoff token.

### 3.1 Strategist → Designer (the primary handoff — end of beat 1)

| Gate | Requirement |
|------|-------------|
| **What must be COMPLETE before the switch** | The content spec at `content_spec` meets its floor (architecture §5.2): deck thesis · exactly one point per slide · narrative arc · per-datum communication intent · every external-facing claim owner-sourced. Any claim missing a source → that slide is `blocked` in `## Slide Status` and listed in the content spec's Open Data Gaps; the switch may proceed but those slides stay blocked (deck-loop-spec ②). `## Art Direction` is still empty — the Designer fills it. |
| **What the Strategist WRITES at the switch** | Frontmatter: `content_spec` (path set), `active_beat: beat-02-art-direction`, `beat_status: not-started`, **`who_acts_next: Designer`**, `next_action` (e.g. "Run art-direction on the reference set: ≥2–3 distinct mini-briefs, owner-picked"), `last_updated`. `## Slide Status` seeded with one row per content-spec slide at `not-started`. |
| **What the incoming Designer READS** | This design-state file (frontmatter cursor + `## Slide Status`), then the `content_spec` from disk (the message — zero design language in it, by §5.2 rule 6), then the `reference_set`. The Designer carries NO conversation context; the content spec + reference set are the entire input (architecture §5). |

### 3.2 Designer → Strategist (the reverse handoff — bounce-cap escalation)

| Gate | Requirement |
|------|-------------|
| **When it fires** | A slide's `bounce_count` reaches ≈3 (H8 / deck-loop-spec ⑧): the loop stops polishing and kicks the message back to beat 1 for a rethink. |
| **What the Designer WRITES at the switch** | `## Bounce Log` "CAP TRIPPED" entry for the slide; frontmatter `active_beat: beat-01-message-lock`, `beat_status: not-started`, **`who_acts_next: Strategist`**, `next_action` (e.g. "Rethink the message for slide {n} — 3 bounces exhausted the design lane"), `last_updated`. The escalation is ALSO appended to the run's `decisions.md` (forward-affecting; deck-loop-spec Edge Cases). |
| **What the incoming Strategist READS** | This file (the cursor + `## Bounce Log` for WHY the message failed), the `content_spec` (to revise), the run's `decisions.md`. It revises the content spec, then hands back to the Designer via §3.1 with the bounced slide reset. |

### 3.3 Owner as `who_acts_next`

When a beat reaches a human checkpoint — art-direction pick (beat 2), trio pairwise pick (beat 2), headed accept/bounce (beat 4) — set `beat_status: awaiting-owner` and `who_acts_next: owner`, with `next_action` naming the exact decision the owner must make. The human is the irreducible final gate (D1); a resuming agent that reads `who_acts_next: owner` knows to surface the decision, not to act past it.

---

## 4. Cross-artifact note (site / app)

For `artifact: site` or `app`, the schema is unchanged — only the row noun in `## Slide Status` shifts (slide → page for site, slide → screen for app), and the per-row HTML status applies per page/screen. The frontmatter cursor, resume protocol, and worker-switch protocol are artifact-general. The site/app forks themselves are sketched, not built in v1 (architecture §1.1); they are concretized or dropped at `p3-checkpoint`. This schema already carries them as a parameter so the forks need no separate state shape.
