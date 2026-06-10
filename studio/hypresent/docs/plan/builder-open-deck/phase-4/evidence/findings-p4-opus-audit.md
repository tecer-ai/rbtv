# FINDINGS AUDIT --- p4-checkpoint (B12) --- Opus cold-verification audit

**Auditor:** independent audit reviewer (no re-run of the headed exercise; evidence-chain + source audit)
**Date:** 2026-06-10
**Audited artifact:** findings-p4.md (cold verifier, 2 sessions) + all c1-* .. c7-* / c1-fix-* captures
**Method:** read every evidence file; read the load-bearing app source (builder-main.js,
file-controls.js, server/server.py, server/api.py, server/deck_api.py) to confirm the verdicts
hold against the contract, spec, and decisions in force; viewed the C1 thumbnail and editor
screenshots to rule on legibility.

---

## Audit verdict table

| Criterion | Audit verdict |
|-----------|---------------|
| 1 --- Round trip at the floor | CONFIRMED-WITH-CAVEAT (thumbnail-legibility; owner-facing) |
| 2 --- New-file guarantee | AUDIT-CONFIRMED |
| 3 --- Cancel semantics | AUDIT-CONFIRMED (incl. "no write", closed by code) |
| 4 --- Disabled states | AUDIT-CONFIRMED |
| 5 --- Editor regression | AUDIT-CONFIRMED (command deviation cosmetic-only) |
| 6 --- decisions.md audit | AUDIT-CONFIRMED |
| 7 --- Enable-on-ready latency | AUDIT-CONFIRMED (numbers sound; ACCEPTANCE = OWNER's call) |

**Overall ruling:** all 7 verifier PASS verdicts are upheld. No verdict overturned. ALL-PASS
holds for auto-pass purposes ONLY if the conductor surfaces the two owner-judgment items below
(they are pre-declared in the run decisions, not new defects): the C1 thumbnail-legibility
caveat and the C7 latency-acceptance call (D-bridge-runtime-ready). Both are owner-decides
items the done-gate flags as held-surprising / unexercisable-class surfaces, not failures.

---

## Per-criterion audit

### Criterion 1 --- Round trip at the floor --- CONFIRMED-WITH-CAVEAT

**What I checked:**
- c1-fix-conductor-order-check.txt + its generator c1-fix-conductor-order-check.py: the
  generator splits top-level <section> spans by depth-tracking (correct), normalizes text
  signatures, strips the marker, and computes order equality deterministically. Verdicts:
  crossing1_order_equals_deck_with_0_1_swapped = True, crossing2_order_equals_crossing1 = True,
  crossing2_order_differs_from_original_deck = True, marker_in_crossing2_section0 = True, marker
  count in crossing-2 = 1, marker anywhere in crossing-1 = False (expected). This is the
  load-bearing disk proof and it is sound.
- c1-fix-order.json assertions block: reorder_happened = true,
  order_matches_post_reorder_srcdoc = false (EXPECTED --- row-0 srcdoc carries the typed marker
  so it cannot byte-match the pre-edit srcdoc), marker_in_final_tray_dom = true,
  crossing2_bytes_contain_marker = true, crossing1_differs_from_deck_by_hash = true,
  owner_decks_unchanged = true. NOTE: the *_title / li_text-based assertions are VACUOUS (every
  slide shares one <title> "Tecer x GSMM...") --- correctly NOT relied on; the conductor order
  check supersedes them.
- c1-fix-thumbnail-dom.txt: marker present in final-tray row-0 srcdoc only (rows 1-9 do not
  contain it). Confirms the marker rode to the correct (reordered-to-front) slide.
- c1-fix-run-log.txt: real drag (mouse down/move/up on row body), real dblclick selection, real
  type [CV-B12], marker confirmed in iframe DOM immediately after typing; both crossings wrote
  distinct temp files; owner decks unchanged.
- Screenshots: c1-fix-03-edited.png --- the edit is pixel-legible in the EDITOR at edit time.
  c1-fix-05-thumbnail-zoom.png --- the row-0 thumbnail element; the marker text is NOT
  pixel-legible at thumbnail scale (blurred sub-pixel text), though the reordered slide layout
  ("Uma plataforma inteligente", DECK badge) is visible.

**Ruling.** The full round trip is exercised at the fidelity floor (headed Chromium, real
gestures, real server, real owner-deck copy) and the reorder + edit are proven end-to-end at DOM
and disk level. The chain genuinely supports PASS. The caveat: the criterion's literal words
"the thumbnail shows the edited text" are satisfied at the RENDER-SOURCE level (the final-tray
thumbnail's srcdoc carries [CV-B12]), NOT by pixel-legible text in the thumbnail itself. An owner
reading the criterion and looking at the thumbnail would not visually read the edited text --- it
is illegible at thumbnail scale (inherent to thumbnails, not a defect). This is an owner-lens
surprise the owner should judge; it does not invalidate the PASS because the thumbnail
demonstrably renders the edited content (it IS in the iframe that paints the thumbnail). Carried
as a held-surprising-class caveat for owner acceptance.

**Session-1 -> session-2 chain note:** session 1 verified the final tray COUNT-ONLY; the
conductor return-gate caught the count-only weakening and required content-level re-exercise.
Session 2 (the c1-fix-* chain audited above) supplies the content-level proofs. The chain is
legitimate --- the weakened session-1 C1 evidence is superseded, not relied upon.

### Criterion 2 --- New-file guarantee --- AUDIT-CONFIRMED

c2-hash-comparison.json: crossing1_wrote_new_distinct_file = true,
crossing2_wrote_new_distinct_file = true, source deck unchanged after both crossings, all 4
owner decks unchanged (pre == post SHA-256). Three distinct temp paths (source / crossing1 /
crossing2). c1-fix-owner-hashes.json independently re-confirms all 4 owner-deck hashes unchanged
in session 2. Verdict holds.

### Criterion 3 --- Cancel semantics --- AUDIT-CONFIRMED

Evidence (cv_driver.py run_c3, lines 568-636) injects null via set_dialog(base, None), clicks the
crossing button, waits 2.5s, asserts URL unchanged; screenshots c3-01..c3-04. The criterion also
requires "no write" --- I closed this by code-reading, since the evidence alone (URL +
screenshots) does not directly show absence of a write:
- Seam: set-dialog with path=null installs set_dialog_launcher(lambda kind: None)
  (server.py:148-151).
- STE cancel: handle_dialog_save_path() -> _launch_dialog("save") returns None ->
  if not path: return {cancelled:true} (deck_api.py:294-299). The path is returned BEFORE any
  /api/deck-save write; saveDeck client sees cancelled and returns before navigation
  (builder-main.js:543-545). No file written.
- OIB cancel: handle_dialog_save_as() -> _launch_dialog("save") returns None ->
  if not path: return {cancelled:true} (api.py:204-209) --- the handle_save_as write at
  api.py:210 is never reached. Client returns before navigation (file-controls.js:56-57). No
  file written.
The write happens ONLY after a non-null path is returned, so null injection guarantees no write.
Evidence + code together fully close "no write". Verdict holds.

### Criterion 4 --- Disabled states --- AUDIT-CONFIRMED

Four screenshots (empty-tray STE disabled, no-doc OIB disabled, deck-loaded STE enabled,
doc-open OIB enabled) + driver assertions all four boolean-true. Cross-checked against source:
STE disabled = !state.canSave where canSave = deck && trayTotal > 0 (builder-main.js:73-76);
OIB enable is gated on runtime-ready per D-bridge-runtime-ready. Verdict holds.

### Criterion 5 --- Editor regression --- AUDIT-CONFIRMED

c5-pytest-output.txt: EXIT: 0, 8 passed in 18.69s. The verifier appended --tb=short to the
contracted command (cv_driver.py:647-650). Confirmed cosmetic-only: --tb=short changes ONLY
traceback verbosity on failure; it does not change which tests run, the exit code, or pass/fail.
Exit code read off subprocess.run(...).returncode (un-piped process). Verdict holds.

### Criterion 6 --- decisions.md audit --- AUDIT-CONFIRMED

c6-decisions-audit.txt + generator (cv_driver.py run_c6): deterministic regex scan of the
"Decisions and Discoveries" section --- 5 entries (ADX-2, ADX-3, ADX-1, D-asset-colocation,
D-bridge-runtime-ready), each with Decision / Rationale / Scope (5/5/5), 0 file-change bullets,
0 N->M narratives. I independently read decisions.md and confirm: append-only discipline intact,
no prior-entry rewrites, all five entries decision+rationale+scope shaped. Verdict holds.

### Criterion 7 --- Enable-on-ready latency --- AUDIT-CONFIRMED (acceptance = OWNER)

c7-latency-log.json: dialog path gap 155 ms (total 233 ms), file-param path gap 187 ms (total
265 ms). Method (cv_driver.py:230-324) is poll-based and content-anchored: t_content_visible is
timestamped after wait_for_function confirms the doc-frame iframe body has rendered children
(content visible), then polls #open-in-builder-btn.disabled until false for t_enabled; gap =
t_enabled - t_content_visible. This is exactly the content-visible -> enabled measurement the
criterion specifies, on both editor open paths. PASS gate gap <= 1000ms correctly applied.
Numbers are plausible for idle Windows 11 / SSD / localhost. Per D-bridge-runtime-ready, the
residual disabled-button window is a visible no-op and the OWNER judges acceptance --- I do NOT
certify acceptance; I certify the measurement is sound and the numbers are real. Verdict holds;
acceptance is the owner's call.

---

## Edits made to findings-p4.md (in place)

All edits preserve the verifier's verdicts and voice; they fix the stale evidence pointer (the
disk_assertions in c1-fix-order.json block was never persisted --- worker drift; the real
deterministic disk proof is the conductor-authored c1-fix-conductor-order-check.txt) and tighten
the legibility wording to match what the screenshot actually shows.

1. C1 "Clarification --- final tray labels": repointed disk_assertions in c1-fix-order.json ->
   "conductor-computed deterministic section-order check in c1-fix-conductor-order-check.txt".
2. C1 "Observed result": repointed the disk-verification source to the conductor-computed
   section-text comparison file; changed "marker may not be pixel-legible" -> "marker is NOT
   pixel-legible at thumbnail scale (inherent to thumbnails)".
3. C1 "Evidence files (session 2)": removed "(with disk_assertions)" mis-attribution on
   c1-fix-order.json; added c1-fix-conductor-order-check.txt to the list with correct attribution.
4. Conductor Note 1: repointed disk_assertions in c1-fix-order.json -> the conductor-computed
   deterministic section-order check in c1-fix-conductor-order-check.txt.
5. Conductor Note 2 (marker legibility): changed "may not be pixel-legible" -> "is NOT
   pixel-legible" and added the owner-facing caveat that the criterion's phrase is satisfied at
   the render-source level, not by pixel-legible thumbnail text (cross-references this audit).

Verified post-edit: zero remaining disk_assertions references in findings-p4.md.

---

## Owner-surface list (what the owner must see / judge)

1. C1 thumbnail-legibility caveat (NEW owner-judgment): the round trip is proven, but "the
   thumbnail shows the edited text" is satisfied at the render-source level (the thumbnail's
   srcdoc/iframe carries the edit) --- the marker text is NOT pixel-legible in the thumbnail
   itself (it is legible in the editor at edit time). Owner decides whether render-source proof
   meets the criterion's intent. (held-surprising-class.)
2. C7 latency-acceptance (pre-declared, D-bridge-runtime-ready): 155 ms / 187 ms content ->
   enabled on this machine; the residual window is a visible disabled-button no-op. Acceptance is
   the OWNER's call, not the verifier's or auditor's.
3. D-asset-colocation (pre-declared, accepted limitation): a deck saved to a directory different
   from its source carries unresolved own-assets/* refs for its non-library slides. I confirmed
   NO verdict wrongly FAILs on this, and NO verdict papers over a real defect with it --- the
   bridge crossings in this checkpoint use self-contained owner-deck copies, so no
   asset-resolution path was exercised or masked. Surface only as a phase-4/5 follow-up if owner
   relocation of saved decks becomes a target.
4. Evidence-pointer correction (FYI): the findings sheet originally cited a disk_assertions block
   that was never written to disk; corrected in place to the real conductor-authored proof. No
   verdict depended on the missing block.

---

## Auditor's bottom line

All seven verifier PASS verdicts are genuine and upheld; none overturned. The C1 evidence chain
(session 1 count-only -> conductor return-gate -> session 2 content-level) is legitimate and the
deterministic disk proof holds. ALL-PASS stands for auto-pass purposes, conditioned on the
conductor surfacing items 1-2 of the owner-surface list (both pre-declared owner-judgment calls,
not defects) in the done message.
