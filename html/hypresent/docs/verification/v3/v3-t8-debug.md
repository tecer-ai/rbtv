# V3-T8 R3 Delete — Live Debug Report + FIX SPEC v4

Debug Agent #4 · boundary C4 (R3 element delete) · branch `hypresent-v2` (no commits)
Date: 2026-06-04 · Method: `superpowers:systematic-debugging` + `rbtv-playwright-cli`, runtime-only instrumentation (zero product/test edits), headless Playwright, real mouse input, server :8791.

## Verdict (one line per failure)

| # | Test | True mechanism | Fix surface |
|---|------|----------------|-------------|
| 1 | `test_delete_then_undo` | **Nested-selection target mismatch in the TEST harness** — delete works; it deletes the wrong element vs the assertion. | TEST (`test_r3_delete.py`). No product bug. |
| 2 | `test_delete_blocked_while_editing` | **Blur-commit race** — the toolbar `mousedown` blurs the iframe editable → `text-edit.commit()` exits edit ~3.4 ms BEFORE `delete-element` arrives; the runtime `document.activeElement` guard sees `body` and passes. | PRODUCT: `text-edit.js` + `main.js`. |
| 3 | `test_thread_unanchored_on_delete_and_reanchor_on_undo` | **No reanchor on undo** (statically known) **+ panel not refreshed on undo** (live-found). | PRODUCT: `runtime-main.js` + `main.js`. |

Baseline reproduced: `python -m unittest tests.e2e.test_r3_delete -v` → **3 failed, 4 passed** (FAIL at local lines 75, 182, 115 — same assertions/messages as `v3-t8-BUG.md`).

---

## Scenario 1 — plain delete (`test_delete_then_undo`)

### Instrumented evidence (verbatim)

`.research-card` rendered rect `{x:80, y:193.9, w:198, h:250}`. The test's `_real_select` clicks at `x = left + min(w/2, 40)` = `left + 40`, `y = top + h/2`. `w/2 = 99 > 40`, so the click lands 40 px from the card's left edge, vertical center.

```
element AT click point (elementFromPoint): {"tag":"div","cls":"research-card-body","hyp":"hyp-136"}
.research-card data-hyp-id (what the test queries):           hyp-132
selection ring geometry best-match (the SELECTED element):   {"cls":"research-card-body","hyp":"hyp-136","d":0}
iframe.cmd[get-selection]  -> result {"hypId":"hyp-136", ...}
iframe.cmd[delete-element] payload {"hypId":"hyp-136"} -> result {"deleted":"hyp-136"}, ok:true
#shell-status:             ["Element deleted."]
.research-card exists  before=True  after=True
SELECTED-id (hyp-136) exists after:  False
```

`.research-card` registered subtree (every node tagged by `element-registry.tag()`):

```
PARENT(grid)  hyp-131  div.research-grid
CARD          hyp-132  div.research-card        ← what the test asserts on
  desc        hyp-133  div.research-card-header
  desc        hyp-134  i.research-card-icon
  desc        hyp-135  div.research-card-title
  desc        hyp-136  div.research-card-body   ← what the click actually selects (covers lower 169px)
```

Control (leaf element) — proves the delete command is correct:

```
.kicker rect {x:80,y:310,w:846,h:17}; click lands on .kicker itself (hyp-12)
iframe.cmd[delete-element] {"hypId":"hyp-12"} -> {"deleted":"hyp-12"}
.kicker exists  before=True  after=False        ← deletes correctly
```

Even a 3 px top-left-corner click on the card selected `hyp-131` (the `.research-grid`), never `hyp-132` — the card's entire box is covered by registered descendants.

### Mechanism (named)

`selection.js`'s click handler walks UP from the clicked node to the **nearest registered element** (innermost). The test's click point (40 px in, vertical center) sits on `.research-card-body` (`hyp-136`), a registered child. The runtime correctly selects and deletes `hyp-136`; the test then asserts on `.research-card` (`hyp-132`), which is the parent and is untouched → `assertFalse(exists(hyp-132))` fails. **The delete command is NOT failing silently** (bug-report assumption #1 is wrong) — it deletes a *different* element than the assertion targets.

### Ruling — TEST is wrong, product is correct (do NOT weaken the outcome assertion)

The product behaviour matches the spec: "Wire `#delete-btn`: `get-selection` → … `delete-element {hypId}`" (spec.md V3-S5/§main.js). Selecting the innermost registered descendant is `selection.js`'s documented contract and is required for editing/styling nested elements; no product change can make `.research-card` selectable at the test's click point without breaking nested selection (a regression on the whole editor). The defect is the **test harness selecting the wrong target**, not a wrong outcome assertion. The assertion "element removed after delete" is correct and MUST stand. The fix is in `tests/e2e/test_r3_delete.py` (out of this mission's product allowlist):

- **Required test change (E-R3-1/2):** select a LEAF, not a container. Replace the `.research-card` target with `.kicker` (or `.research-card-body`), OR select `.research-card` and assert on the actually-selected id (read it from selection), OR click a point guaranteed over no registered child (none exists for `.research-card` — so use a leaf). Recommendation: change `sel = ".research-card"` → `sel = ".kicker"` in `test_delete_then_undo` (the leaf path already passes live). This does **not** weaken any assertion — same DOM-removed + undo-restored + same-previous-sibling checks, on a target the click can actually select.

Note: `test_thread_unanchored_…` also uses `.research-card`, but its delete step still works **because the comment is added to the SAME selected child (`hyp-136`) that delete then removes** — so its delete/unanchor sub-assertions pass; only its undo-reanchor assertion fails (Failure 3). It needs no target change.

---

## Scenario 2 — delete while editing (`test_delete_blocked_while_editing`)

### Instrumented evidence (verbatim)

```
POST-DBLCLICK edit state: {"ce_attr":"true","ce_prop":true,"is_active":true,"active_tag":"div","active_hyp":"hyp-13"}
.slide-title exists before=True after=False     ← element WAS deleted (guard failed)
iframe.cmd[delete-element] {"hypId":"hyp-13"} active={"tag":"body","ce_attr":null,"ce_prop":false} ce_count=0 -> {"deleted":"hyp-13"}
#shell-status: ["Element deleted."]
```

High-resolution event timeline (single gesture, ms from delete press):

```
   3.90ms  parent.delete.mousedown        ← toolbar button receives mousedown
   4.10ms  iframe.blur target=hyp-13       ← blur fires (synchronous)
   4.60ms  iframe.blur (commit() runs: contenteditable removed, edit exits)
   4.70ms  parent.delete.click             ← shell click handler starts (sends get-selection)
   7.00ms  iframe.cmd[get-selection] active=body ce=0
   7.50ms  iframe.cmd[delete-element] active=body ce=0  ← guard sees body → PASSES → deletes
```

### Mechanism (named) — blur-commit race

Pressing the parent toolbar `#delete-btn` moves focus out of the iframe → the editable element blurs → `text-edit.js` one-shot `blur` listener (`:115`) fires `commit()` (`:118-124,:126-149`), which removes `contenteditable` and clears `activeHypId` at **4.10–4.60 ms**, BEFORE the `click` event (4.70 ms) and long before the async `delete-element` command reaches the iframe handler (7.50 ms). The spec's detection — `document.activeElement.getAttribute('contenteditable')==='true'` (runtime-main `:83-85`) — is evaluated ~3.4 ms too late, always sees `body`, and the delete proceeds.

### Owner-policy note (spec'd behaviour quoted)

The spec is unambiguous that this must be a **no-op**:

> spec.md V3-S10: "R3 edit-active guard = `delete-element` is a no-op returning `{blocked:"editing"}` when a text edit is active. … The button handler in the shell is also gated, but the runtime command re-checks (defense in depth)."
> spec.md §Edge cases: "Delete while text-editing | No-op, `{blocked:"editing"}` (V3-S10). The button is gated in the shell AND the runtime re-checks."
> V3-T8 E-R3-6: `assertTrue(self._exists(hyp), "element must NOT be deleted while a text edit is active (V3-S10)")`.

**Ruling: the TEST is correct; this is a PRODUCT spec-implementation gap, not a test error.** The intended UX (no-op) is encoded correctly by the test. What is broken is the *detection signal/timing*: the spec specified the SHELL gate as the primary ("the button is gated in the shell") and the runtime as backstop — but the shipped shell handler (main.js `:457-491`) has **no editing gate at all**, and the runtime `activeElement` check is defeated by the blur race. Recommendation = implement the spec-intended shell gate, captured at **mousedown** (the only event preceding the blur-commit), driven by an `edit-state` event the runtime emits. The async-bridge variant was tested and FAILS (below); the event-cached variant works.

### Live validation of fix design

- Async-bridge probe (`is-editing` dispatched at mousedown, awaited at click) — **FAILS**: `{"is_editing_snapshot_from_mousedown":{"editing":false}}`. postMessage is async; by the time the iframe processes it the blur-commit already cleared the state. → rejected.
- **Event-cached shell gate (Design D, ADOPTED)** — **PASSES**: runtime emits `edit-state{editing}` on enter/commit; shell caches `isEditingNow`; `#delete-btn` mousedown snapshots it BEFORE the `edit-ended` macrotask lands; click blocks.
  ```
  cached_editing_after_dblclick: true
  element_exists_after_delete:   true        (expected true — BLOCKED)
  status: "Finish editing before deleting the element."
  after Esc-commit -> cached false; subsequent delete succeeds (no false-positive)
  ```

---

## Scenario 3 — reanchor on undo (`test_thread_unanchored_on_delete_and_reanchor_on_undo`)

### Instrumented evidence (verbatim)

```
anchored_before_delete: 1
unanchored_after_delete: 1                    ← delete path correctly unanchors the thread
After Undo (runtime undo only, no fix):
  store_threads_after_undo:  unanchored=false, hypId="hyp-136"   ← (with runtime reanchor) store re-anchors
  panel_unanchored_after_undo: 1   panel_anchored_after_undo: 0  ← PANEL still stale → TEST FAILS
```

### Mechanism (named) — two defects

1. **No reanchor on undo (static + live).** `delete-element` (runtime-main `:100-101`) calls `reanchorComments()` only after `historyPush` (the `do`). The Undo button → `register("undo")` (`:47-50`) → `history.undo()` (`:55-61`) runs only `cmd.undo()` = `place()` (commands.js `:325-327`). No reanchor ever runs on undo, so threads stay unanchored after the element returns.
2. **Panel not refreshed on undo (live-only, would survive a runtime-only fix).** The Undo handler (main.js `:538-545`) calls `bridge.command("undo")` and **never** `refreshCommentPanel()`. Even after the runtime store re-anchors, the `#comment-unanchored` / `#comment-threads` DOM the test reads is not re-rendered → `unanchored_after == 1` → assertion `unanchored_after == 0` fails. A runtime-only fix is insufficient.

### Live validation of fix design (real FIX SPEC shape)

Re-registered `delete-element` with the wrapped command (REAL modules) + shell panel refresh on undo:

```
reregister_ok: true
unanchored_after_delete (panel): 1     (do() reanchor still unanchors)
After Undo + panel refresh:
  panel_unanchored_after_undo: 0        panel_anchored_after_undo: 1     element_restored: true
PASS_delete_unanchors: true            PASS_undo_reanchors: true
```

---

## Regression — 4 passing scenarios under all fixes (live)

| Scenario | Result |
|----------|--------|
| E-R3-5 last-region block | PASS — survivor exists, status "Cannot delete the last remaining region." |
| E-R3-7 no-keyboard | PASS — Delete/Backspace leave the selected element intact |
| E-R3-8 Moveable teardown | PASS — `#hyp-interaction-wrapper` present before, gone after delete |
| E-R3-9 no console errors | PASS — `errors: []` |

Fixes are additive (edit-state events; an extra reanchor on undo; a panel refresh on undo; a shell mousedown gate that only fires while editing). None touch these paths.

All proposed code blocks pass `node --check` (text-edit.js, main.js, runtime-main.js additions).

---

# FIX SPEC v4

Files (allowlist): `runtime/js/text-edit.js`, `runtime/js/runtime-main.js`, `app/js/main.js`. `commands.js` is **not** needed. Anchors quoted verbatim from the current shipped code.

## Edit 1 — `runtime/js/text-edit.js` — emit `edit-state` on enter and commit

Import `emit`. Current top import block:

```js
import { byId, idOf } from "./element-registry.js";
import { text } from "./commands.js";
import { push } from "./history.js";
import { suspend as suspendInteraction, resume as resumeInteraction } from "./interaction.js";
import { clearFontState } from "./text-format.js";
```

Replace with (adds `emit`):

```js
import { byId, idOf } from "./element-registry.js";
import { text } from "./commands.js";
import { push } from "./history.js";
import { suspend as suspendInteraction, resume as resumeInteraction } from "./interaction.js";
import { clearFontState } from "./text-format.js";
import { emit } from "./bridge-iframe.js";
```

**1a — emit on enter.** Current (`enterEdit`, after focus + suspend, before the blur listener):

```js
  el.setAttribute("contenteditable", "true");
  el.focus();
  suspendInteraction();

  // One-shot blur listener; guarded by activeHypId so manual commit is safe
  el.addEventListener("blur", onBlur, { once: true });
```

Replace with (insert the `emit` line after `suspendInteraction();`):

```js
  el.setAttribute("contenteditable", "true");
  el.focus();
  suspendInteraction();
  emit("edit-state", { editing: true, hypId });

  // One-shot blur listener; guarded by activeHypId so manual commit is safe
  el.addEventListener("blur", onBlur, { once: true });
```

**1b — emit on commit.** Current end of `commit()`:

```js
  activeHypId = null;
  beforeHtml = null;
  priorContenteditable = null;
  resumeInteraction();
  clearFontState();
}
```

Replace with (append the `emit` line before the closing brace):

```js
  activeHypId = null;
  beforeHtml = null;
  priorContenteditable = null;
  resumeInteraction();
  clearFontState();
  emit("edit-state", { editing: false });
}
```

## Edit 2 — `runtime/js/runtime-main.js` — reanchor on undo (wrap the pushed command)

Current `delete-element` success tail (V3-S8 says reanchor after BOTH `do()` and `undo()`):

```js
    historyPush(makeDeleteCommand(payload.hypId));
    reanchorComments();   // threads on the deleted element go unanchored (kept, never lost)
    clear();              // selection cleared → the observer unmounts the Moveable (V3-S9)
    return { deleted: payload.hypId };
```

Replace with:

```js
    // V3-S8: reanchor after BOTH do() and undo() so deleted-element threads go unanchored
    // on delete AND re-anchor on undo (the Undo path runs cmd.undo() only).
    const cmd = makeDeleteCommand(payload.hypId);
    historyPush({
      do() { cmd.do(); reanchorComments(); },
      undo() { cmd.undo(); reanchorComments(); },
      label: cmd.label,
    });
    clear();              // selection cleared → the observer unmounts the Moveable (V3-S9)
    return { deleted: payload.hypId };
```

(`makeDeleteCommand`'s `do`/`undo` are closures over the captured node — no `this`/binding — so calling `cmd.do()`/`cmd.undo()` from the wrapper is safe. `historyPush` validates only that `do`/`undo` are functions.)

> The runtime `document.activeElement` editing check at the top of the handler (`:82-86`) is left in place as the spec'd defense-in-depth backstop. It is a no-op for the toolbar path (blur-commit precedes the handler — see Scenario 2) but is harmless and still blocks any future synchronous caller.

## Edit 3 — `app/js/main.js` — (a) cache edit-state, (b) gate delete at mousedown, (c) refresh panel on undo

**3a — module flag.** Current:

```js
let bridge = null;
let isDirty = false;
```

Replace with:

```js
let bridge = null;
let isDirty = false;
let isEditingNow = false;   // R3 edit-guard: cached from runtime 'edit-state' events
```

**3b — cache the event in `ensureBridge`.** Current (inside `ensureBridge`, the `dirty-changed` handler block):

```js
  bridge.on("dirty-changed", (payload) => {
    isDirty = payload && payload.dirty ? true : false;
    document.title = isDirty ? "hypresent *" : "hypresent";
  });
```

Replace with (add the `edit-state` listener after it):

```js
  bridge.on("dirty-changed", (payload) => {
    isDirty = payload && payload.dirty ? true : false;
    document.title = isDirty ? "hypresent *" : "hypresent";
  });

  bridge.on("edit-state", (payload) => {
    isEditingNow = !!(payload && payload.editing);
  });
```

**3c — gate the delete button at mousedown (the spec-primary shell gate).** Current `#delete-btn` wiring head:

```js
  // Wire toolbar delete button (R3): toolbar-only trigger (U14 — NO keyboard path).
  const deleteBtn = document.getElementById("delete-btn");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async () => {
      if (!bridge) return;
      let sel;
```

Replace with (add a mousedown snapshot + an early editing gate in click):

```js
  // Wire toolbar delete button (R3): toolbar-only trigger (U14 — NO keyboard path).
  const deleteBtn = document.getElementById("delete-btn");
  if (deleteBtn) {
    // V3-S10 edit-active gate (shell-primary): snapshot editing state on mousedown,
    // BEFORE focus leaves the iframe and text-edit commits/exits on blur. The runtime
    // activeElement check cannot see this (blur fires first) — the mousedown snapshot can.
    let editingAtPress = false;
    deleteBtn.addEventListener("mousedown", () => {
      editingAtPress = isEditingNow;
    });
    deleteBtn.addEventListener("click", async () => {
      if (!bridge) return;
      if (editingAtPress) {
        editingAtPress = false;
        setStatus("Finish editing before deleting the element.", "error");
        return;
      }
      let sel;
```

(The rest of the click handler — `get-selection`, `delete-element`, `{blocked}` branches incl. the existing `blocked === "editing"` runtime backstop, `refreshCommentPanel()` on success — is UNCHANGED.)

**3d — refresh the comment panel on Undo (so re-anchored threads re-render).** Current:

```js
  if (undoBtn) {
    undoBtn.addEventListener("click", () => {
      if (!bridge) return;
      bridge.command("undo").catch((err) => {
        console.error("Undo failed:", err.message);
      });
    });
  }
```

Replace with:

```js
  if (undoBtn) {
    undoBtn.addEventListener("click", async () => {
      if (!bridge) return;
      try {
        await bridge.command("undo");
        await refreshCommentPanel(); // undo may re-anchor threads (R3/V3-S8) → re-render panel
      } catch (err) {
        console.error("Undo failed:", err.message);
      }
    });
  }
```

> Optional symmetry (NOT required for the tests): apply the same `await … ; await refreshCommentPanel();` to the Redo handler (main.js `:546-553`) so a redo of a delete re-unanchors the panel. The R3 suite does not assert redo; omit unless desired.

## Test changes required (outside the product allowlist)

| Test | Change | Weakens outcome? |
|------|--------|------------------|
| `test_delete_then_undo` (E-R3-1/2) | Change `sel = ".research-card"` → `sel = ".kicker"` (a leaf the click can actually select). All four checks (removed-after-delete, restored-after-undo, same-previous-sibling) stay identical. | No — same assertions, correct target. |

No other test changes. `test_thread_unanchored_…`, `test_delete_blocked_while_editing`, and the 4 passing tests are correct as written; their outcome assertions MUST stand.

## Provably-wrong assertions vs spec

None of the **outcome** assertions are wrong. The only provably-wrong element is the **selection target** in `test_delete_then_undo` (selects a container that the click cannot land on, then asserts on it) — a harness/setup defect, fixed by selecting a leaf, not by weakening any assertion.
