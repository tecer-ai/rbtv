# Complexity Rubric

Scores a body of work to pick its entry door and task sizing. Consumed by `rbtv-planning` (door + granularity) and by orchestration intake (which door: conductor-led prep / ask / interactive planning — D2a).

Score each axis, sum, read the band. Bands map to doors; doors are ALWAYS user-overrideable.

---

## Axes

Three axes score 1–3; two are widened (1–4 and 1–5) because the corpus shows real, routing-changing distinctions the 1–3 scale collapsed (see Widening Justification).

| Axis | 1 | 2 | 3 | 4 | 5 |
|------|---|---|---|---|---|
| Context Size | <50k tokens | 50–100k | >100k | — | — |
| Tool Usage | 0–2 tools | 3–5 tools | 6+ tools | — | — |
| Human Review | none needed | optional checkpoints | required approvals | — | — |
| **Dependencies** | linear, clear | some branching | complex graph | parallel waves + shared-file serialization + active-red-set tracking | — |
| **Decision Density** | few decisions | moderate decisions | many design decisions | architecture-dense (cross-cutting tradeoffs) | debate-dense (interdependent reversible decisions needing user resolution) |

Score range: min 5, max 18.

## Bands and doors

| Total | Band | Door (D2a) | Task sizing |
|-------|------|------------|-------------|
| 5–8 | Simple | Conductor-led prep (standard) | Single-step tasks OK; fewer micro-step files |
| 9–13 | Moderate | ASK the user which door | Standard task granularity; full micro-step files |
| 14–18 | Complex | Interactive `rbtv-planning` with the user (standard) | Fine-grained tasks; research-first pattern |

Band-to-door semantics are preserved from the original three-door model: simple = least ceremony, complex/decision-dense = most. The widened axes shift a body of work UP into the door its true coordination/decision load warrants, instead of saturating at the old ceiling.

---

## Widening Justification (validated-evidence-only)

Each change traces to the evidence corpus. Axes NOT widened are listed with the reason they stay 1–3.

| Axis | Change | Corpus evidence forcing the change |
|------|--------|-------------------------------------|
| Dependencies | 1–3 → **1–4** | The Kimi sessions ran 3-, 4-, and 6-wide parallel waves gated by explicit shared-file serialization orders (`commands.js: T5→T7`, `runtime-main.js: T5→T9→T8`) and an active-red-sets registry that self-expires at GREEN commits (`learnings-kimi-worker.md` §3, §8, §S3.3). "Complex graph" (3) cannot distinguish a branching-but-serial plan from a parallel-wave plan that needs a serialization registry and red-set tracking — a materially harder coordination class. The new level 4 names it. |
| Decision Density | 1–3 → **1–5** | This very plan carries 21 numbered design decisions (D1–D21) plus emergent build inputs and mid-stream collaborative reversals (shape.md Collaborative Decisions #5: handoff sequencing reversed by the user). "Many architectural decisions" (3) collapses ordinary architecture work and a debate this dense into one bucket, yet they route to different doors — architecture-dense work can take conductor-led prep, debate-dense work MUST go to interactive planning (D2a). Levels 4 and 5 separate them. |
| Context Size | unchanged (1–3) | The three buckets already key to a concrete mechanic — the >100k tier (3) is exactly where the research-first split becomes MANDATORY (`plan-creation-rules.md` Context Budgeting). No corpus case shows a 4th bucket changing the routing decision. |
| Tool Usage | unchanged (1–3) | Tool count is routing-neutral above "many"; 6+ (3) already triggers the same handling. No evidence a finer scale changes a door. |
| Human Review | unchanged (1–3) | none / optional / required is exhaustive for review gating; nothing between or beyond. |

## Total-band recomputation

Old: 5 axes × max 3 = 15; bands 5–7 / 8–11 / 12–15 (roughly thirds with a 5-floor).
New: max 18 (two axes gained +1 and +2 of headroom); bands re-derived as APPROXIMATELY equal thirds of the 5–18 span — 5–8 / 9–13 / 14–18 (widths 4 / 5 / 5; the 14-wide span does not divide evenly, so the lowest band is one narrower) — so the proportional position of each door is preserved. A body of work scoring "moderate" under the old scale still lands "moderate" unless one of the widened axes legitimately pushes it up.
