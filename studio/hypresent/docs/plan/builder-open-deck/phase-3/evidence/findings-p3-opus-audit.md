# p3-checkpoint (B10) — Opus Findings Audit

> Conductor-folded record of the claude:opus findings audit of the claude:sonnet cold-verifier sheet (`findings-p3.md`). The opus reviewer was blocked from writing its own report file (harness); this is its verdict, folded by the conductor. 2026-06-10.

**ALL-PASS HOLDS: YES** — all six criteria audited to genuine PASS from disk evidence + source + spec.

| Criterion | Verifier verdict | Audited verdict | Reason |
|-----------|------------------|-----------------|--------|
| C1 Full loop at the floor (headed) | PASS | **PASS** | Captures show 10→reorder→remove(9)→dup(10,adjacent)→blank(11)→lib(12); saved NEW file reopens at 12 slides, duplicate adjacency survives round-trip (c1_02/c1_03). |
| C2 Overwrite + chooser every save | PASS | **PASS** | Overwrite and new-file are the SAME `/api/deck-save` recompose path (deck-save.js): both POST the live `tray.getItems()` restructure, differing only in target path. C1 already proved the restructured write end-to-end. Identity hash on an unmodified deck is the ADX-2 byte-for-byte consequence, not a defect. |
| C3 Saved output clean | PASS | **PASS** | deck-save-spec scopes asset-copy to library-fragment assets only (Behavior row 5 + Out-of-Scope). Source-deck own assets ride inside ADX-2 verbatim spans and are correctly NOT re-copied. No `hyp-`/`data-hyp-*` tokens; library fragment verbatim. |
| C4 Assemble regression | PASS | **PASS** | 13 passed, EXIT 0, 0 skipped (verifier + conductor both re-ran). |
| C5 Owner-data safety | PASS | **PASS** | 4 owner decks SHA-256 identical pre/post. |
| C6 decisions.md audit | PASS | **PASS** | Opus re-derived the regex: only N→M / "created file" hits are the exempt bottom guidance block; 3 ADX entries decision+rationale+scope shaped, no rewrite. |

## Forward finding surfaced (non-blocking, owner-relevant)

A deck saved to a NEW directory references its own `assets/*` that won't resolve there — only library-fragment assets travel on save. Spec-correct for p3; a usability cliff if owners relocate saved decks. Recorded as `D-asset-colocation` in `decisions.md` for the phase-4 bridge path. NOT a checkpoint failure.
