# Done-Gate Evidence — `add_comment.py` (hypresent comment authoring tool)

**Feature:** A CLI an agent invokes with a CSS selector + comment text to add a hypresent review comment to a deck, so agents never read or re-implement runtime anchor code.
**Date:** 2026-06-16 · **Tier:** Full (visual criterion → screenshot capture).

## Contract — criterion (owner-confirmed)

> An agent adds a comment to an HTML deck by running ONE command (CSS selector + comment text); the comment then appears in hypresent as a real review comment — a clickable marker + thread anchored to that element — and the agent never reads or re-implements any runtime anchor code.

## Drivability

| Criterion | Surface | Verdict | Seam built |
|-----------|---------|---------|------------|
| One-command comment renders an anchored marker | Hypresent app (Python server + browser runtime) | `drivable` | none — the tool drives the real runtime headlessly; exercise verified in a headed browser |

## Exercise (Fidelity Floor)

| Criterion | Gesture performed | Observed result | Evidence file | Verdict |
|-----------|-------------------|-----------------|---------------|---------|
| Selector must be unambiguous | Ran tool with `--selector ".slide-title"` (8 matches) on the fixture deck | Refused: `selector matched 8 elements — it must be unique` (exit 2) | inline (stderr) | `held` |
| One-command comment, anchored, on the owner's real file | Ran `add_comment.py --file <copy of dashboard-prototype.html> --selector "#screen-overview .screen-title" --body "…" --author "Vivian (designer agent)"` (headless, no code read) | exit 0; printed `ok`, `comment_id: 8`, runtime-computed `anchor {path: div:1/div:1/h1:1, nativeId: screen-overview, contentHash: 25225961}`, `marker_rendered: true`, `contextText: "Status / Overview"`; saved file has exactly ONE `#hyp-comments` island (appended, not duplicated) with the comment body present | inline (tool JSON) | `held` |
| Comment is visible as a marker in hypresent | Opened the saved copy in the hypresent app in a HEADED browser; waited for `.hyp-comment-marker` in the deck | 8 markers rendered (7 prior + the new one); comments side-panel populated; new thread on "Status / Overview" visible | `2026-06-16-add-comment-tool/marker-rendered.png` | `held` |

## Notes

- Exercised against a COPY of the owner's real file `1-projects/fin-ops-harness/steps/step-4/dashboard-prototype.html` — the original was NOT modified (owner instruction). The copy already carried 7 comment threads (added by a separate session); the tool appended #8 cleanly.
- Correctness engine: the tool runs the actual hypresent runtime (anchor computed by `comments.js`'s real `buildAnchorKey`) and saves through the app's own save handler — zero drift, no hand-written island, no runtime changes.

**Verdict summary:** all rows `held`. No `failed`, `unexercisable`, or `held-surprising` rows.
