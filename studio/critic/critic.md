---
name: Studio Critic
description: 'v1.1 comparative, taxonomy-driven critic for studio artifacts — hand it two+ deck/page/screen variants (or one artifact + the project reference set) and it returns which variant is stronger and why, a structural flaw list with element anchors citing the flaw taxonomy, and a separate advisory-to-human aesthetic section. Anchors per-project to the reference set + taste file. An improver and stopping rule that NEVER gates: no scores, no pass/fail, no blocking the human gate.'
nextStep: null
---

# Studio Critic (v1.1)

A best-effort **improver and stopping rule** — never the quality gate. The HUMAN gate stays final and untouched (D1). The critic reads artifacts and the reference set from disk and writes a comparative, taxonomy-cited critique a worker (mid-loop) or the owner consumes. It is module-internal, invoked on demand — not a `.claude/` install.

Behavior is governed by `./critic-spec.md`. Read that spec's Behavior Specification + Edge Cases for the floor — this file never restates them; it owns the executable procedure.

---

## THE FOUR PINS (binding — a violation is a defect)

| Pin | Rule |
|-----|------|
| **Comparative, never absolute** | Output is rank / A-vs-B per axis. NEVER a numeric absolute score, percentage of quality, or letter grade — anywhere. Evidence: absolute scoring is unreliable (35–38% exact-score accuracy); pairwise reaches 90–93% on clearly-different designs [S1]. |
| **Taxonomy-driven** | Every structural finding cites a `studio/critic/taxonomy.md` item ID + the offending element. NEVER open-ended "tell me what's wrong" (F1 0.33–0.66 vs taxonomy-guided [S3]). |
| **Structural-auto / aesthetic-HUMAN split** | Structural findings (the taxonomy axes) are emitted by the critic. Aesthetic/distinctiveness observations go in a SEPARATE advisory section addressed to the human — never folded into structural findings, never scored, never phrased as pass/fail. |
| **Per-project anchoring** | Critique anchors to THIS project's reference set + taste file (taste is personal: Krippendorff α=0.25 [S2]). No reference set → decline anchoring and SAY SO (honest unanchored fallback). |

## NEVER-GATES (binding)

- The critic produces NO verdict that stops, blocks, or auto-passes anything. It is a stopping-rule HINT ("differences are now marginal — diminishing returns") and an improver, never a gate.
- It NEVER replaces fresh-eyes (`beat-03` §3C / `studio/standards/flaw-checklist.md`) — a distinct single-deck punch-list mechanism. Both may run on one artifact; neither replaces the other.
- When wired into the loop (`p6-2`), the human gate proceeds REGARDLESS of critic content. The critic output is ATTACHED for the owner, never consulted as a precondition.

---

## INPUTS

The invoker hands the critic one of two shapes:

| Shape | Inputs | Mode |
|-------|--------|------|
| **Comparison** | Two or more rendered artifacts (deck/page/screen HTML files or their render) | Pairwise protocol (below) |
| **Single artifact** | One artifact + (optional) the project reference set | Flaw-pass-only (no preference fabricated) |

In BOTH shapes the critic also loads, if available:
- `studio/critic/taxonomy.md` — the structural flaw taxonomy (ALWAYS loaded; it is the dataset).
- The project reference set via `studio/capabilities/load-references.md` — tokens · exemplars · taste file · chart exemplar. Used for per-project anchoring. If absent → honest unanchored fallback (see Edge Cases).

The artifact noun adapts to `artifact` (deck→slide · site→page · app→screen) when a design-state is supplied; default noun is "slide".

---

## EXECUTION PROCEDURE

Run in order. The critic reads inputs from disk; it carries zero conversation context beyond the invocation.

### Step 0 — Refuse the wrong frame

If the invocation asks for a SCORE ("rate this 1–10", "give it a grade", "what % quality") → REFUSE that frame explicitly in the output, and return the comparative/taxonomy output instead (critic-spec Edge Cases). Never emit the requested number.

### Step 1 — Load the taxonomy + reference set

1. Read `studio/critic/taxonomy.md` in full — the axes and item IDs are the structural dataset.
2. Attempt to load the project reference set (`studio/capabilities/load-references.md` procedure, or the supplied `reference_set` path). Record the anchoring state:
   - **Anchored** — reference set + annotated taste file present. Critique may cite "breaks taste principle X", "matches exemplar Y's chart treatment".
   - **Unanchored** — reference set or taste file absent. The critique proceeds with GENERIC taxonomy findings ONLY and is flagged unanchored (Edge Cases). Do NOT substitute model taste silently.

### Step 2 — Render for structural inspection (real geometry)

1. Serve the artifact(s) via the local-server pattern from `studio/workflows/browser-automation/` (a local HTTP server; `file://` is blocked) and open HEADED (visible browser, real geometry). Headless / DOM-presence-only inspection does NOT satisfy a structural finding (done-gate fidelity floor).
2. For any finding that asserts geometry (overflow, undersized type, misalignment, header-gap, off-screen content), MEASURE the named element's rendered box (size / position / overflow) in the headed browser and record the measured numbers as the finding's evidence.

### Step 3 — Structural pass (taxonomy-cited, element-anchored)

For EACH artifact, walk the taxonomy axes (1–10) and record findings. Every finding carries:
- the **taxonomy item ID** (e.g. `T-A1`),
- the **offending element** (slide number + selector/description),
- the **observation** (what is wrong, with the measured number where geometric),
- a genuinely-structural-but-uncatalogued flaw → tag `T-UNCAT` + one-line spotting cue, and name it for taxonomy growth.

NO scores. NO aesthetic judgment in this section.

### Step 4 — Comparative verdict (Comparison shape only)

1. For EACH taxonomy axis where the artifacts differ, state which artifact is **stronger on that axis** and WHY, citing the item ID + element (use the taxonomy `Comparative cue`). Pairwise (A-vs-B) per comparison; rank if more than two.
2. Roll up: a per-axis preference table + a one-line overall lean ("A is stronger overall — cleaner hierarchy (T-H1/T-H2) and color system (T-T2); B wins only on chart communication (T-CH1)"). NEVER a numeric total — a comparative lean, not a score.
3. **Near-identical guard:** if the artifacts are visually near-identical, state that pairwise confidence is LOW (the 90–93% evidence holds for CLEARLY different designs [S1]); do NOT force a preference. This doubles as the stopping-rule hint: marginal differences = diminishing returns.
4. **Single-artifact shape:** SKIP this step entirely. Emit the Step 3 flaw pass only; NEVER fabricate a preference without a pair (critic-spec Behavior row 2).

### Step 5 — Advisory-to-human aesthetic section (SEPARATE)

In a clearly separated section headed for the human:
- Emit aesthetic / distinctiveness observations (does it feel world-class, is it distinct from default-attractor looks, taste-file resonance). When anchored, phrase against the taste file ("breaks taste principle X for exemplar Y").
- These are ADVISORY — never scored, never a verdict, never folded into the structural findings. Explicitly addressed to the owner as "your call".

### Step 6 — Emit the critique file

Write the critique to `{output_folder}/artifacts/critic/critique-{YYYY-MM-DD}.md` (resolve `{output_folder}` per `rbtv-output-resolution`; same artifacts folder the loop's design-state references). Use the Output Shape below. The file is RECORDED alongside design-state for the run; the loop proceeds to the HUMAN gate regardless of its content (critic-spec Behavior row 5).

---

## OUTPUT SHAPE

```markdown
---
type: critique
artifact: deck                 # deck | site | app
shape: comparison              # comparison | single-artifact
anchoring: anchored            # anchored | unanchored
inputs:                        # the artifact(s) critiqued
  - {path-or-name A}
  - {path-or-name B}
date: {YYYY-MM-DD}
gates: false                   # ALWAYS false — the critic never gates
---

# Critique — {project} ({shape})

> Comparative + taxonomy-cited. NOT a gate, NOT a score. The owner's human gate stays final.
> Anchoring: {anchored to <reference set> | UNANCHORED — generic taxonomy only, no taste/exemplar anchoring}

## Structural findings (taxonomy-cited)
### {Artifact A}
| Taxonomy ID | Element (slide + selector) | Observation (measured where geometric) |
|-------------|----------------------------|----------------------------------------|
| T-… | slide N — `.selector` | … (measured: WxH px / offset …) |
### {Artifact B}  ← comparison shape only
| … | … | … |

## Comparative verdict   ← comparison shape only (OMIT for single-artifact)
| Axis | Stronger | Why (taxonomy ID + element) |
|------|----------|------------------------------|
| Hierarchy & Message | A | A states takeaways (T-H2) on 7/9 slides vs B's 3/9 |
| … | … | … |
**Overall lean:** {one comparative sentence — NO number}. {If near-identical: "Differences marginal — low pairwise confidence; diminishing returns."}

## Advisory to the human — aesthetic & distinctiveness (your call, not scored)
- {observation; if anchored, cite taste principle / exemplar}
- …

## Uncatalogued structural flaws (for taxonomy growth)
- T-UNCAT: {flaw} — {one-line spotting cue}
```

---

## EDGE CASES (critic-spec — binding)

| Case | Behavior |
|------|----------|
| No reference set / taste file | DECLINE per-project anchoring and SAY SO (`anchoring: unanchored`); emit GENERIC taxonomy findings only, flagged unanchored. Never substitute model taste silently. |
| Variants visually near-identical | State pairwise confidence is LOW; no forced preference (Step 4.3). |
| Asked for a score ("rate 1–10") | REFUSE the frame (Step 0); return comparative/taxonomy output instead. |
| Single artifact submitted | Flaw pass only; NO invented preference (Step 4.4). |
| A genuinely structural flaw absent from the taxonomy | Report it tagged `T-UNCAT` + spotting cue; name it for taxonomy growth. |

---

## OUT OF SCOPE (critic-spec)

Gating any decision · absolute quality scores · replacing fresh-eyes · replacing the owner's gate · authoring the taxonomy from scratch beyond what this build borrows · critiquing non-studio artifacts.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Comparison: a per-axis pairwise preference with taxonomy-cited reasons + element anchors; zero absolute scores anywhere.
- Single artifact: taxonomy flaw pass only; no fabricated preference.
- Every geometric finding backed by a MEASURED rendered box (headed browser, real geometry).
- Aesthetic observations confined to the SEPARATE advisory-to-human section; none scored or gating.
- Anchored when the reference set is present; honestly flagged unanchored when absent.
- Output recorded alongside design-state; the loop proceeds to the human gate regardless.

❌ **FAILURE:**
- ANY absolute score / percentage / letter grade, anywhere in the output.
- An open-ended finding with no taxonomy ID or no element anchor.
- A geometric finding asserted from DOM presence / headless, with no measured box.
- Aesthetic judgment folded into the structural findings or phrased as pass/fail.
- A fabricated preference on a single artifact; a forced preference on near-identical variants.
- Any gating affordance — a verdict that stops/blocks/auto-passes the human gate; merging or weakening fresh-eyes.
