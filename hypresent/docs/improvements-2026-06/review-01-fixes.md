# Hypresent v2 — Review-01 Fix Log (review-01-fixes.md)

Maps every finding in `review-01-spec-plan.md` → status → artifacts touched → one-line change. Severity counts (per the review's own table): 7 BLOCKER, 6 MAJOR, 6 MINOR. (The review's "Counts by Severity" labels say 7/5/5 but its own ID lists enumerate 6 MAJOR and 6 MINOR — the lists are authoritative here.)

Artifact keys: **spec** = `docs/improvements-2026-06/spec.md` · **test-plan** = `docs/improvements-2026-06/test-plan.md` · **plan** = `docs/plan/hypresent-v2/hypresent-v2-plan.md` · **Tnn** = `docs/plan/hypresent-v2/tasks/V2-Tnn.md`.

## BLOCKERS

| ID | Status | Artifacts touched | Change |
|----|--------|-------------------|--------|
| R01 | FIXED (reclassified by reviewer to "see R02/R03") | — | The reviewer's own analysis walks R01 back to "not a blocker" and redirects to R02/R03; no independent defect remained. The concrete sub-concerns it raised (Phase A2 placement, sentinel `includes`, head-vs-body island) are all satisfied by the V2-T2 design as written and by the R04 fix. No separate edit needed beyond R02/R03/R04. |
| R02 | FIXED | spec, T3, T12, test-plan | Dialog launcher tries `pwsh` then falls back to `powershell.exe` on `FileNotFoundError`, both via `_ps_args` = `[exe,"-STA","-NoProfile","-NonInteractive","-Command",script]`; empty stdout = cancel; raises only if neither exists. Identical contract stated in spec §F1 (S23a), T3 `_run_ps_dialog_default`, and unit test U-DLG-9. |
| R03 | FIXED | T2,T3,T4,T5,T6,T7,T8,T9,T10,T11 | No task instructs edits by line number. T3 (do_POST) and T8 (PARTS D/E/F) fully rewritten to content anchors; every other edit task gained a binding "Edit-anchoring rule" stating line citations are non-binding hints and edits LOCATE the quoted exact code, with a per-task note proving each anchor survives the tasks scheduled before it in the serialization order. |
| R04 | FIXED | spec, T2 | `getCommentJson()` treats the in-memory store as authoritative: when the store exists and `toJson()` returns `[]`, it returns `null` (no island re-embed) instead of falling through to the stale DOM island; the pre-existing island was already stripped in Phase A and counted, so guard math stays exact. (T2 Change 0; spec §G2 "Residual scope part 1" + edge case.) |
| R05 | FIXED | spec, T8, test-plan, T15 | Drop is a no-op below a 3px cumulative Euclidean drag distance, accumulated in `onDrag` (`dragDist = Math.hypot(dx,dy)`) and checked in `onDragEnd` (restores pre-drag translate, no classify/commit). Spec §F3 onDragEnd pseudocode + edge case (S27); new test E-F3-12. |
| R06 | FIXED | spec, T9 | Single `escapeAgentBlock(s)` applied to EVERY interpolated value in the agent block — including `anchor.path` and `anchor.nativeId` (the actual defect) plus id/context/body/author/reply body+author; only the ISO `createdAt` is exempt. Signature stated once in spec §F5 and identically in T9. |
| R07 | FIXED | test-plan, T12, T13 (+ T14–T20 via preamble) | Tests FAIL LOUD on a missing fixture: every suite guards `H.FIXTURE`/`FIXTURE` in `setUpClass` and raises `AssertionError` naming the path — never `skipTest`. The sample stays the canonical fixture (read-only, copied per test). |
| R08 | FIXED | test-plan, T13, T14, T15, T16, T17, T18, T19, T20 | ONE import mechanism: a 3-line `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` bootstrap above `import conftest_helpers` in EVERY e2e file, added by each creating task (T13–T20), not deferred to T20. Works under `discover -s tests`, `-s tests/e2e`, and direct module run. |

## MAJORS

| ID | Status | Artifacts touched | Change |
|----|--------|-------------------|--------|
| R09 | FIXED | spec, T8, plan | Import cycle broken: `interaction.js` no longer imports `selection.js` and no longer self-registers; `selection.js` owns the `onSelectionChange` registry (zero imports from interaction/text-edit); `runtime-main.js` `boot()` wires the observer to `interaction.mount/remount/unmount/isActive` after all modules evaluate. Final import graph stated in T8 + spec §F2. |
| R10 | FIXED | spec, T8 | FLIP `affected` set excludes `dragEl` (`.filter(e => e !== dragEl)`); the dragged element lands instantly, only displaced siblings animate. Spec §F3 commitDrop + edge case. |
| R11 | FIXED | spec, T8, T9, plan | `reanchorAfterMove` moved ENTIRELY into V2-T9; `comments.js` removed from T8's allowlist (T8 only CALLS it). Serialization order fixed T9→T8; plan graph + note + rows updated. |
| R12 | FIXED | T3 | T3 now shows the COMPLETE restructured `do_POST` as one `if/elif/else` chain (test seam first with its own `return`, then `/api/open`, `/api/save-as`, the three new routes, final `else`) — no second standalone `if`. |
| R13 | FALSE POSITIVE (reviewer-retracted) | — | The reviewer wrote "Already correct. Strike R13." `reanchorAfterMove`/`buildAnchorKey` read the live post-mutation DOM, so reanchoring is correct. No change; R14 covers the genuine adjacent concern. |
| R14 | FIXED | spec, T9 | `reanchorAfterMove` iterates ALL threads, re-resolves via the multi-signal `matchAnchor`, and on success REGENERATES `path`+`siblingIndex` from the element's CURRENT position (fixing unmoved-sibling index drift, not just the moved element); unresolved threads keep their anchor and show as unanchored — NEVER deleted. Spec §F3 (S12) + T9 Change 5. |
| R15 | FIXED | test-plan, T12 | U-SAVE-2 is now an HTTP-level test against its OWN fresh server subprocess on a dedicated port (8790): one `POST /api/save` with no prior `/api/open` asserts `(200,{no_open_file:true})`. No longer skipped; in-process U-DLG-6 retained as the fast mirror. |

## MINORS

| ID | Status | Artifacts touched | Change |
|----|--------|-------------------|--------|
| R16 | DEFERRED (no-op) | — | Reviewer's own fix column: "No action required." The Save→SaveAs fallback path is already correct; nothing to change. |
| R17 | DEFERRED (no-op) | — | Reviewer: "No action required." Playwright click→runtime-ready timing is within the 8s poll; low risk, no change. |
| R18 | FIXED (precision) | spec | Reviewer: "No action required" (Kimi matches by content). Tightened the spec §0 G1 evidence citation from a stale exact line range to a content-anchored locator; T1 already contains no line-numbered edit instruction. |
| R19 | DEFERRED (no-op) | — | Reviewer: "No action required." The guideline-candidate `set.delete(targetEl)`/`parent !== targetEl` redundancy is harmless; correct per S5. No change. |
| R20 | FIXED | spec | Clarified S20 + F5 edge case: replies carry no individual `resolved` flag; "unresolved replies" means "replies under unresolved threads", and all of them are emitted in full. |
| R21 | DEFERRED (no-op) | — | Reviewer: "No action required for v2." The redundant parent-side `moveable.min.js` load in `app/index.html` is pre-existing and out of v2 scope (and editing index.html for it would exceed the surgical fence). Noted only. |

## Coherence re-verification (post-edit)

- **(a) tecer-gsmm-introduction.html** — no task stages/commits/mutates it. T0 explicitly forbids staging (`git add`/`-f`). T12/T13 and all e2e suites only `shutil.copy`/`H.copy_fixture()` it into tempdirs and operate on the copy; the `FIXTURE` constant is read-only. (U10a honored.)
- **(b) allowlists ↔ instructions** — re-aligned: T8 allowlist drops `comments.js` (no longer touched); T20 allowlist drops the `tests/e2e/*.py` shim-edit permission (shims now added by creating tasks). All other task allowlists match their instructions.
- **(c) plan graph + serialization note ↔ task contents** — updated: dependency graph now shows V2-T8 depends on V2-T7 AND V2-T9; the shared-file note reflects comments.js = V2-T9 only, runtime-main.js = T5→T9→T8, selection.js/text-edit.js = T8 only, index.html = T4 only.

## Net result
All 7 BLOCKERS and all 6 MAJORS are FIXED (R13 was reviewer-retracted as a false positive). Of 6 MINORS: 2 FIXED (R18, R20), 4 DEFERRED as no-ops per the review's own "no action required" verdict (R16, R17, R19, R21). New spec decisions added: S23a (pwsh fallback), S26 (head sentinel sweep), S27 (drag/FLIP/observer). The NO-GO verdict's "Minimal Fix List to Reach GO" (items 1–9) is fully satisfied.
