# findings-p5-opus-audit.md - Findings Auditor (claude:opus), B15 final checkpoint

**Auditor:** Independent findings auditor (claude:opus), adversarial re-derivation pass over the cold verifier's B15 sheet
**Date:** 2026-06-10
**Under audit:** findings-p5.md (cold verifier claude:sonnet, 6 criteria, claimed ALL 6 HELD) + the vault done-gate sheet 1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-10-builder-open-deck.md
**Method:** Did NOT trust the verifier's JSON proofs. Re-computed every load-bearing assertion from persisted artifacts on disk; where the disk artifact was overwritten, reproduced save-time content from FIRST PRINCIPLES by driving the real server/deck_api.py::handle_deck_save against the confirmed owner source deck with the intercepted payload.

---

## Verdict summary

| # | Criterion | Verifier | Audit verdict |
|---|-----------|----------|---------------|
| C1 | v1 success criteria end-to-end | held | CONFIRMED-WITH-CAVEAT |
| C2 | All deliverables landed | held | CONFIRMED |
| C3 | No marker leakage | held | CONFIRMED |
| C4 | Full regression green (escape clause) | held | CONFIRMED |
| C5 | p5-refs passed | held | CONFIRMED |
| C6 | decisions.md audit | held | CONFIRMED |

All 6 HELD verdicts stand. None overturned. One caveat on C1 (a stale on-disk artifact, fully reconciled); one in-place fix applied.

---

## C1 - CONFIRMED-WITH-CAVEAT

Independently re-derived (NOT from the verifier JSON):

1. Source deck identity. Computed 10 top-level <section> SHA-256[:12] hashes of all 4 root decks. Exactly ONE matches the session orig_hashes - tecer-gsmm-introduction.html (owner's real deck): [26f116db4326, 30861d0ea7a6, 987d1214b487, d5a7ad0b90da, 3a5c95f25f3f, 62221bfaaed7, 25d0bb9645dd, ae3d66d0bb35, 4c9d440a0f15, 7cbdf4a2fa55]. Grounds the orig->saved index mapping.

2. Save-#1 reproduced from first principles. On-disk c1-s2-r2-saved.html was OVERWRITTEN by the editor crossback autosave (JSON saved_hashes_note discloses; my own hash of the on-disk file = [30861d,30861d,30861d,...] = 3xsec1 post-overwrite state, NOT save-#1). To verify independently, I drove the REAL handle_deck_save (deck_api -> recompose) with the intercepted save-#1 payload [{idx:1},{idx:1},{idx:0},{idx:3..9},{blank},{library:cover-e2e.pt}] against the confirmed source deck:
   - Output byte size 92048 - exact match to log "saved file size=92048".
   - Section hashes [30861d0ea7a6, 30861d0ea7a6, 26f116db4326, d5a7ad0b90da, 3a5c95f25f3f, 62221bfaaed7, 25d0bb9645dd, ae3d66d0bb35, 4c9d440a0f15, 7cbdf4a2fa55, 2ff924b54510, 09986792fffd] - 12/12 identical to the log's immediate-content-verification set (run2-log lines 60-72).
   - pos0,1 = orig1 (reorder swap + duplicate); pos2 = orig0; orig2/987d1214b487 ABSENT (removal); pos10 = blank 2ff924b54510; pos11 = library 09986792fffd (cover-e2e.pt) verbatim {{COVER_TITLE}} {{COVER_SUBTITLE}} {{COVER_DATE}}.
   - 0 hyp-/0 data-hyp tokens in the reproduced output.

3. Intended-arrangement consistency. Traced gestures against c1-s2-r2-model-dumps.json: open -> swap0<->1 (after_reorder=sec1,sec0) -> remove deck-section-2 (after_remove drops uid3) -> duplicate uid2/deck-section-1 (after_dup=sec1,sec1,sec0) -> blank (blank-12) -> lib (cover-e2e.pt at pos11). Resulting index list [1,1,0,3..9,blank,lib] = EXACTLY the intercepted payload. Gesture sequence SHOULD produce that payload, and did.

4. Crossback marker. Read c1-s2-r2-crossback.html bytes directly: " [CV-B15-S2]" present exactly once, embedded in real deck text (...lideranca gasta&nbsp; [CV-B15-S2]tempo...). Round-trip proven. 0 hyp-/data-hyp leakage.

5. Owner-data safety. Re-hashed all 4 root decks live: SHA-256 identical to both pre/post brackets and c0. Owner decks untouched.

Caveat (does not overturn): the verifier's automated disk-assertion pass re-read the OVERWRITTEN on-disk saved.html AFTER crossback and printed "=== VERDICT: failed ===" (run2-log L108, lib_sig_found:False, payload==intended:False); the final JSON was hand-corrected to held. The override is JUSTIFIED, not gamed: the failed was (a) the autosave overwriting the file between save-time and the late re-read, and (b) two driver bugs in the assertion script (lib signature check looked for the wrong slide's text; intended array built without the lib item). Neither is a product defect. Authoritative evidence = save-time immediate verification, reproduced byte-for-byte by me. The on-disk c1-s2-r2-saved.html no longer holds save-#1 bytes (holds post-crossback 3xsec1); anyone re-hashing it directly is misled. Save-#1 correctness rests on the in-session log + my deterministic reproduction - both independent, both PASS. HELD; owner should know the final-state file on disk is not the proof artifact.

## C2 - CONFIRMED
Read deliverables.md end-to-end. Phases 1-4 all marked done with paths. Phase 5: p5-refs done, p5-compound done, p5-checkpoint in-progress. No done-claimed row with unresolved path. Matches sheet.

## C3 - CONFIRMED (covers BOTH sessions)
Independent regex over persisted session-2 files: c1-s2-r2-saved.html=0/0, c1-s2-r2-crossback.html=0/0, reproduced save-#1=0/0. Session-1 cite c1-disk-content-check.json records 0 hyp tokens for deck-cv-b15-saved.html. Note: that session-1 file holds BROKEN-gesture content (3x "Uma plataforma inteligente", marker false) but leakage is orthogonal to gesture correctness - leakage-clean regardless. C3 spans both sessions' saved files.

## C4 - CONFIRMED (escape clause satisfied)
- git log -- tests/e2e/test_f5_comments.py returns ONLY 9288ede (the repo-wide html->studio rename) - exactly the predicted single entry. F5-comments feature outside plan scope.
- 11dcb38 is a legitimate PRE-PLAN baseline: 11dcb38 == cff2be0^ confirmed; ancestor of HEAD with 35 commits between; every builder-open-deck build commit is a descendant of 11dcb38.
- Literal escape "or failures are pre-existing, evidenced by a pre-plan baseline run" satisfied. Baseline flake: HEAD x3=FAILED/FAILED/passed; 11dcb38 x5=passed/FAILED/FAILED/FAILED/FAILED. Flaky at BOTH HEAD and pre-plan baseline -> not a regression. Suite: 213 passed, 2 skipped, 1 flaky-fail.

## C5 - CONFIRMED (new flags not live broken links)
Re-ran p5-refs-link-check.py: VIOLATIONS=9 (up from adjudicated 7) because the scanner now reads the new evidence docs (findings-p5.md, p5-refs-link-check.md itself). Every new flag is: (a) the report/findings sheet quoting the paths it adjudicates (self-referential evidence-doc scan); (b) a temp deck path mentioned in prose (findings-p5.md | .../tmpies2f29w/deck.html); or (c) already-adjudicated classes (assets/ prose, /doc/ routes, orchestration/... tolerated variants, {evidence_root} vault-root refs, historical html/hypresent). decisions.md | ./evidence/ and phase-N/evidence/ rows are path tokens INSIDE the D-link-standard-adjudication entry text - prose, not links. No new flag is a genuine broken link in a live consumed document. The one real fix (p5-checkpoint.task.md evidence path) remains corrected. C5 holds per D-link-standard-adjudication.

## C6 - CONFIRMED
Read decisions.md end-to-end. Original Shaping intact/immutable. 6 entries (ADX-1, ADX-2, ADX-3, D-asset-colocation, D-bridge-runtime-ready, D-link-standard-adjudication), each decision+rationale+scope. No file-list/N->M narrative entries. Git history of the file is additive only. Append-only holds.

## In-place fixes applied
1. findings-p5.md C1 Evidence column - appended a one-clause note that c1-s2-r2-saved.html on disk holds the post-crossback overwrite (not save-#1 bytes), and that save-#1 proof rests on the in-session immediate-verification log (reproduced byte-for-byte by this audit). Verifier voice preserved; verdict unchanged.
No verdicts changed. No other edits.

## Owner-surface list - audit adds/removes NOTHING
Confirmed complete and unchanged: (1) carried p4 - C1 thumbnail legibility (held-surprising-class); (2) carried p4 - C7 enable latency 155/187 ms; (3) compound proposals G1/G2/G3 (learnings.md, approval pending); (4) pre-existing flaky F5 test; (5) D-asset-colocation accepted limitation (relocated saved deck has unresolved image refs for its own non-library slides - out of v1 scope).
