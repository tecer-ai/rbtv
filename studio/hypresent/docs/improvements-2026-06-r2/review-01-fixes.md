# Hypresent v3 — Review-01 Fix Map (Session 2)

Resolution of every finding in `review-01.md` (RV01–RV15) plus the two orchestrator-mandated additions. Applied to the Session-2 planning document set ONLY (spec.md, test-plan.md, hypresent-v3-plan.md, tasks/V3-T1..T19.md). ZERO product/code files touched; zero git writes.

**Status legend:** FIXED (reviewer fix applied as written) · FIXED-WITH-DIRECTION (orchestrator direction overrode/extended the reviewer's required fix) · N-A (ruled not-applicable).

Orchestrator binding directions are in `changelog.md` log row 77.

---

## Findings

| RV | Severity | Status | What changed | Where (doc · section) |
|----|----------|--------|--------------|------------------------|
| RV01 | BLOCKER | FIXED-WITH-DIRECTION | E-R3-5 (last-region block, D20) is now IMPLEMENTED (was OMITTED) via `doc_eval` DOM surgery on the TEMP fixture copy: reduce the body to ONE tagged region (remove every body-level `[data-hyp-id]` sibling but the first — survivor keeps its boot registry entry), fail-loud preconditions (≥2 before, ==1 after), attempt a toolbar delete, assert the survivor STILL exists and `#shell-status` contains "Cannot delete the last remaining region." | `tasks/V3-T8.md` (new `test_last_region_block` method, goal, acceptance 3a, bottom note) · `test-plan.md` (E-R3-5 row + setup note) |
| RV02 | BLOCKER | FIXED-WITH-DIRECTION | V3-T14 Change 6B's ambiguous NOTE became a BINDING DO-NOT: the `selection-changed` handler output MUST keep BOTH the `setActiveOutline(...)` line and the `__hypUpdateAlignButtons` block; pre-removal is forbidden (V3-T16 depends on the both-lines block as its verbatim anchor). | `tasks/V3-T14.md` (Change 6B BINDING note + new DO NOT entry) |
| RV03 | BLOCKER | FIXED-WITH-DIRECTION | V3-T16 acceptance grep rewritten to match EXACT removed identifiers ONLY — `outline-list`, `renderOutline`, `outlineRegions`, `setActiveOutline`, `regions(`, `sections`, and CSS selectors via `^\s*\.outline-` regex (selector-anchored). The bare substring `outline` is NEVER a failure condition; the `outline:` CSS PROPERTY is explicitly allowed and stated as such. | `tasks/V3-T16.md` (acceptance 2 regex + intro) · `spec.md` (R9 acceptance criteria) |
| RV04 | BLOCKER | FIXED-WITH-DIRECTION | REPLACED the conditional-restore design with SNAPSHOT-ALWAYS-WINS. On any font op, if a mousedown snapshot exists AND is valid (`startContainer`/`endContainer` `isConnected` AND active editable `contains` its `commonAncestorContainer`), restore it UNCONDITIONALLY — the live post-toolbar-click selection is focus-shift garbage by construction. No valid snapshot → live selection; neither usable → tracked-span fallback (bump `currentFontSpan`). Removed EVERY `commonAncestorContainer === el` / `liveCollapsedAtRoot` check; the fallback "no usable range" test is `sel.rangeCount === 0` only. Added a `snapshotIsValid(el)` helper. | `spec.md` (V3-S22 row + R8 exact-algorithm) · `tasks/V3-T3.md` (goal, Change 1A `snapshotIsValid`, Change 1B both blocks, acceptance 2, DO NOT) · `test-plan.md` (E-R8 rationale) |
| RV05 | MAJOR | FIXED-WITH-DIRECTION | Hardcoded empty-click `(fb.x+3, fb.y+3)` replaced with DYNAMIC discovery: a `doc_eval` probe sweeps candidate iframe points (right/bottom margins, corners, a coarse grid) and accepts the first whose `elementFromPoint` has NO `[data-hyp-id]` ancestor (html/body/null), then real-clicks it; FAILs (not skips) if no empty point exists. | `tasks/V3-T2.md` (F2.3 replacement) · `test-plan.md` (E-F2-7 row) |
| RV06 | MAJOR | FIXED | Added `"justify-self"` and `"align-self"` to the PROPS capture array in V3-T14 Change 2A (now the full 10-entry V3-S15 capture-all set). Reconciled the spec's `commands.js` align-capture line to the same full list (it had been short). | `tasks/V3-T14.md` (Change 2A PROPS, acceptance 3) · `spec.md` (R7 `commands.js` module-design row) |
| RV07 | MAJOR | FIXED-WITH-DIRECTION | **Branch taken: SKIP-CONFIRMED (no toggle extension).** KEPT `.moveable-area` in the injected `pointer-events:auto` rule (body-drag MOVE shares R2's root cause and must revive). READ `reorder.js` `classifyDrop`: its only `elementsFromPoint` consumer, `elementUnderPointerSkippingHypChrome`, skips every element whose `closest('[id^="hyp-"], [class^="hyp-"], [class*=" hyp-"]')` matches. Moveable's controls are light-DOM children of `#hyp-interaction-wrapper` (Moveable is built on `wrapper`), so `closest('[id^="hyp-"]…')` matches the wrapper ancestor → they ARE already skipped. No onDragEnd toggle extension needed. Documented the quoted skipping code as evidence in V3-T1. | `tasks/V3-T1.md` (new "Why `.moveable-area` STAYS" evidence section + DO NOT entries) · `spec.md` (V3-S4 rationale) |
| RV08 | MAJOR | FIXED-WITH-DIRECTION | V3-T16 Anchor 2D's conditional fallback DELETED and replaced with: if the both-lines block is not found verbatim, STOP and write a bug report under `docs/verification/v3/` (e.g. `v3-t16-anchor2d-BUG.md`) — do not guess an alternative, do not substitute an empty-body handler, do not drop the align wiring. | `tasks/V3-T16.md` (Change 2D BINDING note) |
| RV09 | MAJOR | FIXED | Eliminated the only `frame_locator(...).bounding_box()` usage (V3-T18 Edit 2's `box_t = title.bounding_box()`); standardized that R8 dblclick on the `iframe_origin + doc_eval getBoundingClientRect` pattern used by the v2 suites. Added a DO-NOT and a test-plan note. | `tasks/V3-T18.md` (Edit 2 rewrite + DO NOT) · `test-plan.md` (E-EXIT-2 row) |
| RV10 | MAJOR | FIXED | After undo re-anchor, the thread test now asserts `#comment-unanchored .comment-thread` count `== 0` (re-anchored, not merely still-present) AND anchored count ≥ 1, alongside the existing "never lost" total. | `tasks/V3-T8.md` (`test_thread_unanchored…` undo assertions) · `test-plan.md` (E-R3-4 row) |
| RV11 | MINOR | FIXED | `_hexProbe` is now APPENDED to `document.body` hidden (`visibility:hidden; position:absolute; pointer-events:none`) at module init (with a DOMContentLoaded fallback + lazy re-attach), so CSS `var()` token chains resolve through the document `:root` cascade. Documented the var()-token behavior in V3-T11 acceptance + a spec edge-case row. | `tasks/V3-T11.md` (Change 1 probe init, acceptance 4) · `spec.md` (V3-S14 algorithm + R6 edge-case `var()` row) |
| RV12 | MINOR | FIXED | V3-T19 now READS the live `docs/decision-log.md` FIRST (Step 3.0, with a content-anchored `re.findall` to print existing D-numbers + the next four) and uses the next-available consecutive numbers. On the current source the highest is D7 → the appended rows stay D8–D11 (verified: live decision-log ends at D7, so no collision). Explicit renumber-and-note instruction if the log changed. | `tasks/V3-T19.md` (new Step 3.0, acceptance 3) |
| RV13 | MINOR | FIXED | Added `preset_author(page)` to the helper lists of every task that USES it (V3-T8 calls it pre-`goto`; V3-T17 calls it in setUp), with the "init script before goto" usage note. Also added it to the canonical test-plan helper inventory. (V3-T18's edited code does not call it — not added there.) | `tasks/V3-T8.md` (helper list) · `tasks/V3-T17.md` (new Helpers section) · `test-plan.md` (helper inventory) |
| RV14 | MINOR | FIXED | V3-T2's post-`scrollIntoView` fixed `wait_for_timeout(300)` replaced with an event-driven `page.wait_for_function` viewport check (new `_scroll_into_view` helper; `_real_click` calls it). | `tasks/V3-T2.md` (`_scroll_into_view`/`_real_click`) · `test-plan.md` (E-R2 note) |
| RV15 | MINOR | FIXED | Added module-map update anchors 2F (`selection.js` + `alignCaps` on the `selection-changed` payload, R7) and 2G (`color.js` + `rgbToHex` exported/`normalizeHex`/`token.hex`, R6) to V3-T19, per the spec's cross-feature module-map delta. Updated acceptance 2 to require all six modules. | `tasks/V3-T19.md` (File 2 Anchors 2F/2G, acceptance 2) |

---

## Orchestrator additions (beyond the reviewer's findings)

| Addition | Status | What changed | Where (doc · section) |
|----------|--------|--------------|------------------------|
| R2 MOVE + REORDER real-input coverage | FIXED-WITH-DIRECTION | The R2 test task gained TWO new real-input, fail-loud, measured assertions: (a) E-R2-4 MOVE — a real body-drag ≥40px changes `style.translate` by ~the drag delta (±15px tolerance), not mere non-emptiness; (b) E-R2-5 REORDER — one real drag of a `[data-hyp-id]` sibling over its adjacent sibling changes the dragged element's DOM child-index (the v2 F3 behavior, now under real input). The prior console-error test renumbered to E-R2-6. No skips. | `tasks/V3-T2.md` (E-R2-4/5/6 methods, goal, acceptance 4) · `test-plan.md` (E-R2 table + orchestrator-add note) · `spec.md` (R2 Move/Reorder acceptance) · `hypresent-v3-plan.md` (C1 row + graph) |
| `!important` alignment edge-case (out of scope) | FIXED | Added ONE edge-case row to spec R7: alignment properties carrying inline `!important` are OUT OF SCOPE — `el.style.<prop> = value` (CSSOM assignment) cannot override an existing `!important` declaration, so the write silently has no effect; documented limitation, NO code. | `spec.md` (R7 edge-cases table) |

---

## N-A (ruled not-applicable)

| Item | Ruling |
|------|--------|
| Module-manifest / `modules/` edits (reviewer checklist-13 tail) | N-A — verified by the orchestrator (log row 77): hypresent is absent from rbtv `modules/` and `admin/` (not an installable component). NO `modules/` or `module-manifest.json` edits were added to any task. |

---

## Self-verification performed

- Every NEW/CHANGED quoted code-anchor re-checked verbatim against live files: `reorder.js` `elementUnderPointerSkippingHypChrome` (V3-T1 evidence) ✓; `main.js` `selection-changed` handler L273-275 (V3-T14 6B / V3-T16 2D chain) ✓; `main.js` `formatButtons` L420 (V3-T3 4A) ✓; `main.js` `setStatus`/`#shell-status` L18-22 (V3-T8 E-R3-5) ✓; `conftest_helpers.py` `preset_author`/`doc_eval`/`FIXTURE` ✓; `03-module-map.md` `selection.js` L42 + `color.js` L51 tree comments (V3-T19 2F/2G) ✓; live `docs/decision-log.md` ends at D7 (RV12 D8–D11 no collision) ✓.
- Grep confirms NO `commonAncestorContainer === el` or `liveCollapsedAtRoot` survives as a code instruction anywhere in the doc set (only in prohibitive "do NOT" / "there is NO" context).
- Fix-interaction chain reconciled: V3-T14 Change 6B output (both-lines handler) === V3-T16 Anchor 2D quoted anchor (whitespace-exact). V3-T3's RV04 edits are confined to `text-format.js`; the `format-snapshot` registration (runtime-main.js, V3-T3 Change 2B) is untouched, so V3-T14 Anchor 4B remains valid.
- Plan updated where content shifted: C1 boundary V3-T2 row, dependency graph C1 line (E-R2-1..6, RV07 skip-confirmed note).
