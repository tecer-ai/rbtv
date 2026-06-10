# V4-T10 Blocking Bug Report

## Date
2026-06-05

## Summary
Four R14 tests fail due to **test-spec inconsistencies and a test fallback bug** that cannot be resolved from the product side without editing frozen test files or modifying out-of-allowlist server code.

## Product Changes Made (allowlist only)
- `runtime/js/comments.js`
  - `buildAgentBlock()` rewritten: per-thread `anchor:` line replaced with `target:` + `context:` lines.
  - Self-cleanup preamble added containing `remove the data-hyp-agent`.
  - `agentStampMap()` exported — high-confidence-only (levels 1/2), returns `Map<Element, string[]>`.
  - `matchAnchorHighConfidence()` added (levels 1/2 only; null on fall-through — G6).
- `runtime/js/serializer.js`
  - Imports `agentStampMap`.
  - `serialize()`: transient live-stamp wrapped in try/finally — clear stale → stamp current → clone → strip-exempt → finally unstamp live DOM.
  - `stripClone()`: exempts `data-hyp-agent` from Phase-B `data-hyp-*` removal (`attr.name !== "data-hyp-agent"`).

## Failing Tests

### 1. `test_e_r14_1_single_agent_thread_stamp_and_resolve`
**Failure:** `text1.count("data-hyp-agent")` returns 3, test expects 1.

**Root cause:** The saved file contains three occurrences of the substring `data-hyp-agent`:
1. The actual stamp attribute on the element: `data-hyp-agent="1"`
2. The `target:` selector in the head block: `[data-hyp-agent~="1"]`
3. The self-cleanup directive: `remove the data-hyp-agent`

All three are **required** by the V4-T10 spec and by other passing tests (`test_e_r14_5`, `test_g_r14_legibility_2`).
The test uses `str.count()` as a blunt substring check, which also counts occurrences inside the HTML comment block. The test message says "Expected exactly one data-hyp-agent stamp" (singular), confirming the author intended to count stamp *attributes*, not all substrings.

**Impact:** Blocking — the spec requires `data-hyp-agent` in both the block text and the attribute, making `count == 1` impossible.

### 2. `test_e_r14_6_stamping_idempotence`
**Failure:** Same `count("data-hyp-agent")` issue (3 vs 1) on both first and second save.

**Root cause:** Identical to test 1. After reopening a stamped file, `serialize()` clears stale stamps before cloning (step 1) and re-applies current stamps (step 2), so the second save is structurally identical to the first. Count remains 3.

**Impact:** Blocking — same impossible constraint as test 1.

### 3. `test_e_r14_8_non_first_element_with_markers_live`
**Failure:** After reopening a saved file, `doc.querySelectorAll('[data-hyp-agent]').length` returns 2, test expects 0.

**Root cause:** The test contains **contradictory assertions** in the same DOM state:
- Step A: `querySelectorAll('[data-hyp-agent~="id0"]')` and `~="id1"` both return 1 element (passes).
- Step B (immediately after, no DOM mutation): `querySelectorAll('[data-hyp-agent]')` expected to return 0 elements.

If elements carry `data-hyp-agent~="id0"`, they necessarily carry `data-hyp-agent`, so Step B can never be 0 while Step A is 1. No product change can satisfy both assertions simultaneously.

**Impact:** Blocking — logical contradiction in test assertions.

### 4. `test_g_r14_legibility_1_targets_resolvable_via_head_block`
**Failure:** Selector `[data-hyp-agent~="1"]` resolves to 0 elements on a fresh page (`n=0`).

**Root cause:** The test attempts to load the saved file via two routes:
1. `/doc/<basename>` — returns 404 because `doc_root` was never updated to the temp directory (it still points to the synthetic fixtures directory from `setUp`).
2. `file://<abspath>` — fallback that should work, but **never executes** because Playwright's `page.goto()` does **not** throw on HTTP 404; it loads the 404 response as a page.

The 404 page is a JSON response (`{"error": "Not found"}`) with no `data-hyp-agent` stamps, so the selector returns 0.

`test_g_r14_legibility_2` passes because it goes **directly** to `file://` without the broken `/doc/` attempt.

**Impact:** Blocking — the test's 404-detection logic is flawed. Fixing it requires either:
- Editing the frozen test file, OR
- Modifying `server/api.py` to update `doc_root` on save (outside allowlist).

## Regression verification
- `node --check` passes on both modified files.
- R13 + g2 regression suite (`test_r13_comment_edit_delete.py` + `test_g2_save_with_comments.py`): **13/13 passed**.
- R14 targeted suite: **6/10 passed**, **4/10 failed** (detailed above).

## Why the product implementation is correct
- `test_e_r14_2`, `3`, `4`, `5`, `7`, and `test_g_r14_legibility_2` all pass, confirming:
  - Multi-thread stamping works.
  - Resolved/deleted threads don't stamp.
  - Live DOM is clean after `serialize()` returns.
  - Block format is complete (sentinel, target, context, instruction, reply, author, date, self-cleanup).
  - Node-count guard is safe.
  - Target selectors resolve correctly on a fresh page when loaded via `file://`.
- The acceptance criteria in the task spec are fully implemented.

## Resolution
RESOLVED by ADX-7 (changelog row 221). The four failing tests were RED-task defects (test-spec inconsistencies / flawed fallback logic). Test-side fixes applied per orchestrator allowlist extension:
- E-R14-1 / E-R14-6: replaced blunt `text.count("data-hyp-agent")` with DOM-scoped assertions (load saved file in fresh page, `querySelectorAll('[data-hyp-agent]').length`).
- E-R14-8: split the conflated saved-vs-live assertions. Live-DOM-clean check moved to immediately post-save; reopen assertions retained.
- Legibility-1: removed broken `/doc/` → fallback logic; navigate directly via `file://` with a page-load assertion.

## Recommendations
1. **Test 1 & 2:** Replace `text.count("data-hyp-agent")` with a regex that counts only actual HTML attributes, e.g. `len(re.findall(r'data-hyp-agent="', text))`.
2. **Test 3:** Remove the contradictory `assertEqual(count, 0)` or move it to verify the *live DOM immediately after save* (not after reopening).
3. **Test 4:** Fix the fallback logic by checking the response status (`fresh.goto(...).status()`) or by going directly to `file://` as `test_g_r14_legibility_2` does.
