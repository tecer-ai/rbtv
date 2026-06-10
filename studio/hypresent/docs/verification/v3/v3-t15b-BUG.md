# V3-T15b — BUG REPORT

**Date:** 2026-06-04  
**Task:** KIMI TASK V3-T15b — R7 test-side fixes + green re-run  
**Agent:** Executor (boundary C7)  
**File modified (allowlist):** `tests/e2e/test_r7_alignment.py`  
**Product files modified:** None  

## 1. What was executed

Both edits from **FIX SPEC v5** were applied exactly to `tests/e2e/test_r7_alignment.py`:

1. **EDIT 1** — `_ensure_target()` now pins `id='r7-target'` on the first `.research-card` (or `.kicker`) match and sets `self.TARGET = "#r7-target"`, so `querySelector`, `_restyle`, `_computed`, and `_select` all address the same DOM node.
2. **EDIT 2** — Removed the dead `const win` redeclaration line in `test_align_caps_payload` (E-R7-10 SyntaxError).

No assertions were changed. No product files were modified.

## 2. Re-run result — NOT GREEN

```
python -m unittest discover -s tests/e2e -p "test_r7_*.py" -v
```

| Metric | Value |
|--------|-------|
| WALL_MS | 78951 |
| EXIT | 1 |
| SKIPPED_LINES_COUNT | 0 |
| Passed | 3 / 9 |
| Failed | 6 / 9 |

**Passing:**
- `test_align_caps_payload` (E-R7-10)
- `test_no_console_errors` (E-R7-11)
- `test_plain_block_vertical_disabled` (E-R7-8)

**Failing:**
- `test_h_block_center_and_undo` (E-R7-1/2) — `text-align` is `start`, not `center`
- `test_flex_row` (E-R7-3/4) — `align-items` is `normal`, not `center`
- `test_flex_column` (E-R7-5) — `align-items` is `normal`, not `flex-end`
- `test_grid` (E-R7-6) — `justify-items` is `normal`, not `center`
- `test_table_cell` (E-R7-7) — `#align-bottom` **disabled** → TimeoutError
- `test_fixed_height_block_vertical` (E-R7-9) — `#align-middle` **disabled** → TimeoutError

## 3. Root cause — SECOND-LEVEL query/select mismatch (test-side)

EDIT 1 successfully eliminated the **first-level** mismatch (`.research-card` class selector matching 7 different elements). However, a **second-level** mismatch remains:

The first `.research-card` in the fixture has nested child elements that are **independently registered** by the runtime's `element-registry.js::tag()`:

```html
<div class="research-card" id="r7-target">          <!-- target we query -->
  <div class="research-card-header">                  <!-- REGISTERED by tag() -->
    <i class="fa-solid fa-file-contract research-card-icon"></i>  <!-- REGISTERED -->
    <div class="research-card-title">Contratos</div>  <!-- REGISTERED -->
  </div>
  <div class="research-card-body">                    <!-- REGISTERED by tag() -->
    Parceria agrícola e arrendamento...
  </div>
</div>
```

The runtime's click handler (`runtime/js/selection.js:194-220`) walks **up** from `event.target` and stops at the **nearest registered element**:

```js
document.addEventListener("click", (event) => {
  let node = event.target;
  // ...
  while (node && node.nodeType === Node.ELEMENT_NODE && node !== document.body) {
    const hypId = idOf(node);
    if (hypId) { select(hypId); return; }
    node = node.parentElement;
  }
  clear();
});
```

Because `_select()` clicks at the element's rect-center (`origin + rect + min(w/2,40), h/2`), the coordinate lands on a child (e.g., `.research-card-body`, `.research-card-title`, or the icon). That child **has its own `data-hyp-id`** (assigned by `tag()`), so the click handler selects the **child**, not the parent `#r7-target`.

### Consequence per failure mode

| Test | Expected selected | Actually selected | Result |
|------|-------------------|-------------------|--------|
| Block H-center | `#r7-target` (block) | Child block | `text-align:center` written to child; parent query returns `start` |
| Flex-row/col, Grid | `#r7-target` (flex/grid) | Child plain block | Style written to child; parent query returns `normal` |
| Table-cell | `#r7-target` (table-cell) | Child plain block | `vertical-align` capability false → button disabled → timeout |
| Fixed-height block | `#r7-target` (fixed block) | Child plain block | `__flexColumn` capability false → button disabled → timeout |

### Why the 3 tests still pass

- `test_plain_block_vertical_disabled`: Even if a child plain block is selected, vertical buttons are still disabled → assertion matches.
- `test_align_caps_payload`: The first check (flex → vertical enabled) somehow passes, likely because the first `.research-card` in this specific fresh page load happens to receive the click on a non-registered surface or the timing/interaction lands differently. The second check (plain block → disabled) also passes for the same reason as above. This test is not robust enough to detect the child-selection bug.
- `test_no_console_errors`: Only checks for console errors, not computed styles or button states after a meaningful alignment.

## 4. Why FIX SPEC v5 claimed sufficiency

The debug report's live matrix used "a single top-level region tagged with a unique id, restyled and real-mouse-selected." That test element likely had **no child elements that were independently registered** by `tag()`. The actual fixture's `.research-card` is a composite component with nested registered children — a condition the debug agent did not replicate.

## 5. Verdict

- **Product code:** CORRECT. No product file needs modification.
- **Test code:** The two edits from FIX SPEC v5 are **necessary but not sufficient**. `_select()` must be made robust against child registered elements.

## 6. Proposed test-only fixes (do not touch product)

Any of the following (test-side only) would resolve the issue:

1. **Bypass mouse click — use runtime API directly:**  
   In `_select()`, instead of `page.mouse.click(...)`, call `H.doc_eval(self.page, "win.hyp.select(win.hyp.byId(...))")` or inject a direct `select(hypId)` call through the iframe. This eliminates coordinate ambiguity entirely.

2. **Click on the parent's border/padding:**  
   Modify `_select()` to click at `(rect.x + 1, rect.y + 1)` (top-left corner inside the element) or at a coordinate explicitly on the parent's padding/border, avoiding child content. Alternatively, temporarily set `pointer-events: none` on all children of `#r7-target` before clicking, then restore.

3. **Choose a target class with no registered children:**  
   `.kicker` is a flat `<div>` with only text nodes. However, clicking on a text node causes `event.target` to be a `TEXT_NODE`, which the click handler skips, leading to `clear()`. So `.kicker` would need fix #1 or a synthetic click dispatch on the element itself.

**Recommendation:** Implement option #1 (direct runtime selection) in `_select()`. It is the most reliable and fixture-agnostic approach.

## 7. Evidence

See `docs/verification/v3/v3-t15b-run.txt` for the full verbatim unittest output, wall-clock metrics, exit code, skipped-lines count, and git-diff file list.
