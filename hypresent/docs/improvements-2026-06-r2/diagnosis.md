# Hypresent Session 2 — Diagnosis (R1–R9)

**Date:** 2026-06-04
**Agent:** Diagnosis agent (read-only; ZERO product-file edits — this is the sole write)
**Branch:** `hypresent-v2` (verified; no git writes performed)
**Repro environment:** server `python server/server.py 127.0.0.1 8791` with `HYP_TEST_DIALOG=1`; Chromium via Python Playwright 1.60.0 (headless); sample deck `tecer-gsmm-introduction.html` opened through the `/api/_test/set-dialog` seam + `#open-btn` (the same path the e2e suite uses). All real-input repros used `page.mouse.down()/move()/up()` and `page.mouse.dblclick()` — never `element.dispatchEvent`. Scratch scripts ran from `$env:TEMP` and were deleted; server + browser killed before finishing.

Line/column references are 1-based against the files as they exist on `hypresent-v2` at diagnosis time.

---

## R1 — Open/Save dialog opens BEHIND the browser window

**Static diagnosis (per mission: real OS dialog NOT opened in automation — it blocks; static evidence + research-01 is conclusive).**

### Root cause

`server/api.py:45-65` builds the native dialog and `server/api.py:73-96` runs it. The PowerShell scripts create the WinForms dialog and call `$d.ShowDialog()` **with no owner window argument and no `TopMost` owner form**:

```powershell
# api.py:45-53  (_OPEN_PS)
Add-Type -AssemblyName System.Windows.Forms
$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Filter = 'HTML files (*.html;*.htm)|*.html;*.htm|All files (*.*)|*.*'
$d.Title = 'Open Presentation'
$d.ShowHelp = $true
if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }
```

`$d.ShowDialog()` (no args) gives the COM file dialog **no owner `HWND`**. Windows therefore assigns z-order relative to the *spawning process's* foreground state — a `powershell.exe`/`pwsh` child launched headless by `subprocess.run` from a `ThreadingHTTPServer` worker thread (`api.py:86-89`) has **no visible top-level window and never holds the foreground activation token**. The focused window stays Chrome, so the ownerless dialog renders behind it. This is exactly the owner's report ("clicked many times… until I minimized the browser and saw the modal in the back").

The only foreground nudge present is `$d.ShowHelp = $true` (api.py:51, 63). research-01-file-access.md §B2 itself flags this as a **legacy/unreliable** hack ("works on most Windows versions", "legacy workaround"); on Windows 11 with .NET it does **not** reliably force the dialog to the foreground. There is no `TopMost`, no owner form, no `SetForegroundWindow`/`AppActivate` call anywhere in `api.py`. The changelog's row-62 caveat confirms the real dialog was "exercised via seam only" — so this z-order defect was never actually observed before the owner hit it.

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — Create a hidden owner Form with `TopMost=$true` and pass it to `ShowDialog($owner)`. In the PS script: `$owner = New-Object System.Windows.Forms.Form; $owner.TopMost=$true; $owner.ShowInTaskbar=$false; $owner.WindowState='Minimized'; ... $d.ShowDialog($owner); $owner.Dispose()`. A `TopMost` owner forces the dialog above all normal-z windows including Chrome, deterministically, because the dialog inherits the owner's top-most band. | S | Low — owner form is invisible (minimized, no taskbar); disposed after. Pure-PS, no new deps. Keep `-STA` (already present, api.py:70). |
| B | Programmatically foreground the dialog: after `ShowDialog`, or via a brief timer, call `[Microsoft.VisualBasic.Interaction]::AppActivate($pid)` or P/Invoke `SetForegroundWindow`. | M | Medium — `AppActivate` is racy (must fire after the dialog HWND exists); SetForegroundWindow is subject to Windows foreground-lock rules and can flash the taskbar instead of focusing. |
| C | Keep `$d.ShowHelp=$true` only and document the limitation. | S | High — this is the current code; it is what fails. Not acceptable given the owner explicitly requires "on top of the focused Chrome window". |

Option A is the standard, deterministic WinForms fix and is the one to implement. It applies identically to both `_OPEN_PS` and `_SAVE_PS`.

### Owner-decisions

`OWNER-DECISION` — none required for the mechanism. (Optional polish only: whether the dialog should also steal focus/flash taskbar if the user has clicked away mid-open — default A behavior is "appear on top, focused", which matches the request.)

---

## R2 — Resize does not work under real handle drag

**Reproduced with REAL pointer input. This is the headline finding.**

### Repro

1. Open the sample deck (seam + `#open-btn`).
2. Scroll `.research-card` into view; real `page.mouse.click()` at its center → element selects. Verified handles render:
   - `hyp-interaction-wrapper` exists ✓, `.moveable-control-box` exists ✓, **12** `.moveable-direction` handles ✓, `.hyp-selection-ring` exists ✓.
   - SE handle located at iframe-rect `(x:249, y:3266, w:14, h:14)`, class `moveable-control moveable-direction moveable-se moveable-resizable`.
3. Real drag of the SE handle: `mouse.move(handle)` → `mouse.down()` → 12× `mouse.move(+5px, +3.3px)` → `mouse.up()`.

**Observed:**
- `BEFORE`: computed `width:198px height:250px`, no inline width/height/flex-basis.
- `AFTER`: computed `width:198px height:250px`, still no inline sizing. **Geometry UNCHANGED.**
- A real body-drag (move) on the same element also produced **no** `translate` (`(none)`).
- **Console during drag: empty** (no error, no warning). Only the document's own `assets/*` 404s appear in the session (expected — the deck's images are absent per README).

So: handles render, but pointer input to them does nothing and throws nothing.

### Root cause — `runtime/js/interaction.js:150-157` + Moveable's shadow-DOM-only pointer-events CSS

`mount()` (interaction.js:316-329) builds the Moveable on a full-viewport overlay `wrapper` created by `createWrapper()`:

```js
// interaction.js:150-157
function createWrapper() {
  const w = document.createElement("div");
  w.className = "hyp-interaction-wrapper";
  w.id = "hyp-interaction-wrapper";
  Object.assign(w.style, { position: "fixed", top: "0", left: "0", width: "100%", height: "100%", pointerEvents: "none", zIndex: "999998" });
  document.body.appendChild(w);
  return w;
}
```

and `buildMoveable(el)` (interaction.js:294-305) constructs `new window.Moveable(wrapper, {...})` — i.e. the Moveable container **is** this `pointer-events:none` div.

Live pointer-events chain (measured in-browser at the live handle):

| Element | computed `pointer-events` |
|---------|---------------------------|
| `#hyp-interaction-wrapper` | `none` (set explicitly above) |
| `.moveable-control-box` | **`none`** (inherited from wrapper) |
| `.moveable-se` handle | **`none`** (inherited) |
| `document.elementFromPoint(handleCenter)` | **`null`** — nothing is hittable there |

During a real `mouse.down()` on the handle: `.moveable-dragging`/`.moveable-resizing` never appear, card width stays `198px`. The handle never receives the pointer.

**Why Moveable doesn't fix its own pointer-events here:** the vendored `app/js/vendor/moveable.min.js` ships its handle CSS inside `:host { … }` shadow-DOM rules (grep confirms 5 `pointer-events` declarations, all inside `:host`-scoped stylesheets; the lone `pointer-events: auto` is `:host[data-able-origindraggable] .control.origin`). Moveable's pointer-events management assumes its control box lives in a **shadow root / custom element**. In this build the control box is a plain light-DOM `<div class="moveable-control-box">` parented directly under the `pointer-events:none` wrapper (live ancestry: `.moveable-control-box div < #hyp-interaction-wrapper div < body < html`). Light-DOM divs do not match `:host` rules, so Moveable's compensating pointer-events styles never apply, and the elements simply **inherit `pointer-events:none` from the wrapper**. The individual handle's own base rule is even explicitly `pointer-events: none` (the 12×12 control rule). Net: visually present, pointer-transparent → every drag/resize is dead.

This is a pure light-DOM-vs-shadow-DOM pointer-events mismatch, not a missing mount, not a bridge failure, not a JS exception.

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — Stop forcing the wrapper to `pointer-events:none`. Set the wrapper to `pointer-events:none` **but re-enable it on the Moveable control elements**: add a `hyp-`scoped style rule `#hyp-interaction-wrapper .moveable-control-box, #hyp-interaction-wrapper .moveable-control, #hyp-interaction-wrapper .moveable-line, #hyp-interaction-wrapper .moveable-area { pointer-events: auto; }` (injected once into the iframe). Wrapper stays click-through for empty regions; handles become hittable. | S | Low — surgical; the only elements made interactive are Moveable's own controls. Must inject the rule into the iframe document (where the control box lives), not the parent. |
| B | Render Moveable into its own container that is NOT `pointer-events:none` and is sized/positioned to not block the document, OR pass Moveable a `dragContainer`/use its default `document.body` mount instead of the overlay. | M | Medium — changing the mount target risks the snapping/guideline container math (`snapContainer: wrapper`, interaction.js:299) and the FLIP overlay assumptions. |
| C | Verify whether the vendored Moveable supports a `portalContainer`/shadow option and enable shadow rendering so `:host` rules apply. | M-L | Medium-High — depends on vendored version capabilities; research forbidden this session; may require lib config not present. |

Option A is minimal and directly removes the defect with no change to the interaction/snapping architecture.

### CRITICAL — did the 8 green F2 tests ever perform a real handle drag? **NO (for the load-bearing assertion).**

`tests/e2e/test_f2_select_guides.py` (all 8 tests read):

- **E-F2-1/2/3/6/7/8** assert only **presence** of `.moveable-control-box`, `.moveable-direction`, `#hyp-interaction-wrapper`, and `.hyp-selection-ring`, or selection/edit lifecycle. **None measure element geometry.** Several even select via `c.dispatchEvent(new MouseEvent('click'))` (synthetic — e.g. E-F2-4 line 117, E-F2-5 line 158), which D15 now forbids.
- **E-F2-4** (`test_drag_shows_guidelines`, lines 107-145) and **E-F2-5** (`test_resize_shows_guidelines`, lines 148-197) DO use real `mouse.down()/move()/up()`. **But:**
  1. They assert only that a `.moveable-line` guideline appears — **never that width/height/translate changed**.
  2. Both end with `if not found_line: self.skipTest("guideline render requires interactive drag; covered by manual smoke")` (lines 143-144, 195-196). So if the drag produces no effect (exactly the R2 bug), the test **skips → counts green**, it does not fail.
  3. E-F2-5 also `skipTest`s if the resize handle isn't found at all (line 169-170).

**Gap:** the F2 suite verified that Moveable *renders* and (conditionally, skippably) that guidelines *might* appear. It **never asserted that a real handle drag mutates the target's computed size or position.** A resize that renders handles but moves nothing passes the suite. This is precisely how 8/8 green coexisted with a 100%-dead resize.

---

## R3 — Element deletion (missing) — no repro needed

Confirmed absent: a full grep of `runtime/js/` and `app/js/` shows **no element-delete command, no `delete-element` bridge command, and no Delete/Backspace key handler for elements.** Every `removeChild`/`delete` hit is unrelated (comment markers `comments.js:329,364`; selection ring `selection.js:121`; interaction wrapper `interaction.js:159`; serializer chrome-strip `serializer.js:142,163`; Map bookkeeping).

### Where deletion must land (full map)

| Concern | File:line anchor | What to add |
|---------|------------------|-------------|
| **Command + inverse (undo)** | `runtime/js/commands.js` (alongside `reorder` at :148-184) | New `deleteElement(hypId)` factory. `do()`: capture parent + nextSibling (by `data-hyp-id`) + the detached node, then `parent.removeChild(el)`. `undo()`: re-insert before the captured next-sibling anchor (mirror `reorder`'s `place()` helper, commands.js:157-166). Must capture the node ref so undo restores the exact subtree. |
| **History** | `runtime/js/history.js` via `push()` (imported as `historyPush`) | No change — same unified stack; the new command flows through `push`. |
| **Selection cleanup** | `runtime/js/selection.js` — `clear()` (:170-176); `byId` already self-heals (element-registry.js:144-151) | After delete, call `clear()` so the ring (which polls `byId`→null in `updateRing` :126-140) drops. `byId` already returns null for detached nodes (`document.body.contains` guard, :146), so a stale ring auto-clears on next `updateRing`, but an explicit `clear()` is cleaner. |
| **Moveable teardown** | `runtime/js/interaction.js` — `unmount()` (:339) | The selection observer (runtime-main.js:29-36) calls `interactionUnmount()` when selection goes null — so if delete clears selection, teardown happens for free. If delete keeps selection logic separate, call `unmount()` explicitly to destroy the Moveable bound to the now-removed target (`moveable.target` would dangle otherwise). |
| **Comment-thread fate** | `runtime/js/comments.js` — `matchAnchor` (:181), `threads()` (:571-583), `reanchorAfterMove` (:558-569) | A thread anchored to the deleted element: `matchAnchor` returns null → `threads()` marks it `unanchored:true` (:578), shown in the panel's "Unanchored" section (main.js:204-212). **Thread is never lost** — consistent with the existing reorder behavior (comments.js:565 "never deleted"). For undo symmetry, call `reanchorAfterMove()` after both `do()` and `undo()` so anchors recompute. `OWNER-DECISION`: should deleting an element also delete its anchored threads, or leave them in "Unanchored"? Default (leave unanchored) matches current move semantics. |
| **Bridge command registration** | iframe: `runtime/js/runtime-main.js` (register block, e.g. next to `select`/`clear-selection` :60-75); parent: `app/js/bridge/bridge-parent.js` is generic (`command(type,…)`) — no change | Add `register("delete-element", (payload) => { … historyPush(deleteCmd); clear(); return …; })`. Parent calls `bridge.command("delete-element", {hypId})`. |
| **Shell affordance — toolbar button** | `app/index.html` (toolbar groups :12-33) + `app/js/main.js` (button wiring pattern at :436-448 for `#color-btn`) | Add a `🗑`/"Delete" `tool-btn`; on click, `bridge.command("get-selection")` → if `hypId`, `bridge.command("delete-element",{hypId})` then `refresh`. Mirror the `#comment-btn` guard (main.js:451-485) that alerts if nothing is selected. |
| **Shell affordance — keyboard Delete** | **iframe document** (where focus lives when an element is selected). See focus note below. | A `keydown` Delete/Backspace handler. **Must be registered on the iframe `document`** (like `selection.js`'s click handler :192 and `text-edit.js`'s keydown :180), NOT the parent — see split below. |

### Iframe/parent focus split — which document receives keydown

When an element is **selected** (not text-editing): the click that selected it landed inside the **iframe** (selection.js click listener, iframe document), so the iframe document/body holds focus. A Delete keypress is delivered to the **iframe document**. Therefore the Delete handler belongs in a runtime module (iframe side), exactly like the existing `Escape` handler in `text-edit.js:180-184` and the Ctrl+Z handler in `history.js`. The parent shell only sees keydown when focus is on a toolbar control. → **Register the element-delete keydown in the iframe runtime.**

### Edge cases (must handle)

| Case | Required behavior |
|------|-------------------|
| Delete while **text-editing** (`contenteditable` active) | MUST NOT delete the element. `text-edit.js` tracks `activeHypId` (:48). The Delete handler must no-op (let the browser delete a character) when an edit is active OR when `document.activeElement` is contenteditable. Mirror the guard in `text-format.js:22-28`. |
| Delete the **body / last region** | Deleting `body` is already impossible (`shouldTag` excludes body, element-registry.js:67). Guard against deleting the only remaining top-level region (would leave an empty document) — `OWNER-DECISION` whether to allow or block. |
| Delete an element with **descendants that have threads** | Same as above: those threads go "Unanchored", not lost. |
| Delete then **Save** | Serializer (`serializer.js`) clones the live DOM, so a deleted element is simply absent — no special handling. Node-count guard already tolerates the live tree. |
| **Undo** after delete | Re-inserts the captured subtree at the captured anchor; then re-`tag()` is unnecessary because the node kept its `data-hyp-id` (delete detaches, doesn't strip). `byId` will resolve again once re-attached (`document.body.contains` true). |

### Owner-decisions

- `OWNER-DECISION` UX trigger set: toolbar button only, Delete key only, or both (recommend both).
- `OWNER-DECISION` Anchored-thread fate on delete: leave "Unanchored" (default, matches move) vs cascade-delete threads.
- `OWNER-DECISION` Allow deleting the last top-level region? (recommend block with a status message.)

---

## R4 — `#color-btn` 🎨 purpose — verified live

### What it does today (traced + verified in browser)

Chain: `app/index.html:20` (`<button … id="color-btn" title="Color picker">🎨</button>`) → `app/js/main.js:436-448`:

```js
// main.js:436-448
const colorBtn = document.getElementById("color-btn");
if (colorBtn) {
  colorBtn.addEventListener("click", () => {
    const panel = document.querySelector(".shell-panel");
    if (!panel) return;
    // Open the first color input in the panel (triggers Coloris)
    const firstInput = panel.querySelector(".hyp-coloris-input");
    if (firstInput) {
      firstInput.click();
      firstInput.focus();
    }
  });
}
```

It finds the **first** `.hyp-coloris-input` in the side panel and programmatically clicks+focuses it, which opens that input's Coloris picker. The first such input is the **first Palette Token row** (rendered first by `color-popover.js:124-149`, before the Selected-Element rows at :151-181).

**Live verification (no selection):** clicking `#color-btn` opened the Coloris picker (`clr-picker.clr-open` went `false → true`); the targeted input was `{scope:"token", target:"--primary"}` — i.e. the `--primary` palette token. With a selection, the first input is still the first **token** row (tokens render above the element rows), so it opens the same token picker regardless of selection — it does NOT target the selected element's color.

### Is it redundant? **Yes.**

Everything `#color-btn` reaches is reachable directly: the user can click the `--primary` token's color swatch in the always-visible Palette Tokens list (`color-popover.js` token rows) to open the exact same Coloris picker. The button is just a shortcut to "open the first palette token's picker", which has no unique capability and an arbitrary target (whichever token sorts first). It does not open per-element color, does not open a general palette, does not scope to selection.

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED (pending owner)** — Remove `#color-btn` (index.html:20 + its `toolbar-group` wrapper :19-21, and main.js:436-448). The palette/element color UI in the side panel fully covers its function. | S | Low — no capability lost; verify the side panel is always visible (it is, `index.html:41-55`). |
| B | Repurpose it into a real toggle that shows/hides the color section or focuses the **selected element's** Text color input (scope it to selection instead of the first token). | M | Medium — requires the panel to expose a stable per-element anchor; changes behavior the owner may not want. |
| C | Keep as-is. | — | The owner explicitly flagged it as apparently functionless; keeping it is the status quo complaint. |

### Owner-decisions

`OWNER-DECISION` (embedded question #1): keep or delete `#color-btn`. Diagnosis recommends **delete** — it is redundant and its target is arbitrary.

---

## R5 — Palette token tooltip — no repro needed

### Insertion point

Token rows are built in `app/js/shell/color-popover.js:132-149`:

```js
// color-popover.js:132-146
for (const token of tokens) {
  const row = document.createElement("div");
  row.className = "hyp-token-row";
  row.innerHTML = `
    <span class="hyp-token-name" title="${token.name}">${token.name}</span>
    <input type="text" class="hyp-coloris-input" data-coloris data-scope="token"
           data-target="${token.name}" value="${escapeHtml(token.value)}" aria-label="Color for ${token.name}">
  `;
  tokenListEl.appendChild(row);
}
```

A tooltip explaining doc-wide recolor goes either: (a) on the **section header** "Palette Tokens" (`color-popover.js:107`, the `.hyp-color-header` div) as a `title=` or a small info icon — one tooltip for the whole group; or (b) per-row on `.hyp-token-name`. The section-level header (a) is the natural home for "Editing a token recolors **every** element bound to that `:root` variable across the whole document." The data model backs this: `applyToken` mutates `documentElement.style.setProperty(name,…)` (color.js:156-159, commands.js:190-205), which is genuinely document-wide. Implementation is a static string — no logic. The header already exists at color-popover.js:107 inside the injected `container.innerHTML` (:105-119).

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — Add an info affordance next to the "Palette Tokens" header (color-popover.js:107): a small `ⓘ` `<span class="hyp-token-info" title="…doc-wide…">` or an inline helper line under the header. | S | Low — static markup in the existing injected block. |
| B | Per-row `title` on each `.hyp-token-name`. | S | Low, but noisier (repeats the same message per row). |

### Owner-decisions

`OWNER-DECISION` wording of the tooltip (suggested: "Changing a palette token recolors every element using that color across the whole document.") and whether it lives on the header (A) or per-row (B). Recommend A.

---

## R6 — Per-token discreet copy-HEX button — no repro needed

### Insertion point

Same loop, `color-popover.js:132-146`. Each row already holds the hex in `token.value`. Add a discreet copy button to the `.hyp-token-row` template (after the `.hyp-token-name`, before/after the Coloris input), e.g. `<button type="button" class="hyp-token-copy" data-hex="${escapeHtml(token.value)}" title="Copy HEX" aria-label="Copy ${token.name} hex">⧉</button>`, then a `click` handler that calls `navigator.clipboard.writeText(hex)`. Wire it in the existing `container.addEventListener("change", …)` block region (color-popover.js:221) by adding a sibling `container.addEventListener("click", …)` that matches `.hyp-token-copy`. Styling: a tiny low-contrast icon button (the CSS block at :29-104 is the place to add `.hyp-token-copy`).

Note the value to copy: `token.value` is the raw `:root` value (e.g. `#1a2b3c` or possibly an `rgb()`/named color). For "apply that color in another component" the raw token value is what the user wants; if normalization to `#rrggbb` is desired, `color.js:169-175` already has `rgbToHex()` (not exported — would need exporting or a small inline copy). `OWNER-DECISION`: copy raw token value vs normalized hex.

### Clipboard availability — TESTED LIVE, works

Page is served over `http://127.0.0.1:8791`. Live test in the running editor:

```json
{"hasClipboard": true, "hasWrite": true, "isSecureContext": true, "wrote": true, "readback": "#123456"}
```

`navigator.clipboard.writeText` **succeeds** on `http://127.0.0.1` — Chrome treats `127.0.0.1`/`localhost` as a secure context (`window.isSecureContext === true`), so the localhost secure-context exemption applies and **no HTTPS is needed**. (The Playwright context was granted clipboard permissions for the readback assertion; the *write* itself does not require a permission grant on a secure context and the secure-context gate — the actual blocker for clipboard — is satisfied.) The copy must still be invoked from a user-gesture click handler (it will be — it's a button click).

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — Add `.hyp-token-copy` button per token row + a delegated click handler calling `navigator.clipboard.writeText(hex)`; brief "copied" affordance (title swap or transient class). | S | Low — clipboard verified working; gesture present. |

### Owner-decisions

- `OWNER-DECISION` copy raw token value vs normalized `#rrggbb`.
- `OWNER-DECISION` icon/affordance style ("discreto") and copied-confirmation treatment.

---

## R7 — Text alignment controls — no repro needed

### Mechanism

`runtime/js/text-format.js` currently does bold/italic/font-size only (`apply(op)`, :113-147; ops `bold|italic|fontInc|fontDec`). Alignment is a **new operation class** that targets the **selected element's content box**, not a text Selection. There is no existing alignment code; `commands.js` has no align factory.

**Terminology fact (state plainly):** "text box" is **not** an HTML term. The real target is the **selected element's content box** — i.e. the element currently selected in `selection.js` (`current().hypId`). Horizontal alignment of inline text is `text-align` on that block element; "vertical alignment" has no single CSS property and depends on the element's computed `display`.

### Decision table — what "align top/middle/bottom" should write per computed `display`

| Computed `display` of selected element | Horizontal (left/center/right) | Vertical (top/middle/bottom) |
|----------------------------------------|--------------------------------|------------------------------|
| `block` / `inline-block` / `list-item` (normal flow text) | `text-align: left\|center\|right` | **No reliable vertical alignment** unless the element has a fixed height. If `height`/`min-height` is set: set `display:flex; flex-direction:column; justify-content: flex-start\|center\|flex-end` (converts to flex — see risk) OR leave vertical disabled. Recommend: vertical writes nothing for plain block without a height; surface a hint. |
| `flex` (element IS a flex container) | main-axis vs cross-axis depends on `flex-direction`. For `row`: horizontal = `justify-content`, vertical = `align-items`. For `column`: horizontal = `align-items`, vertical = `justify-content`. | (same — mapped by `flex-direction`) |
| `grid` (element IS a grid container) | horizontal = `justify-items` (or `justify-content` for track alignment) | vertical = `align-items` (or `align-content`) |
| `flex-child` / `grid-child` (element is an ITEM in a flex/grid parent) | Self-alignment: `align-self` (cross axis) + `justify-self` (grid) — aligns the element within its track, not text within it. For text *inside* the child, fall back to the `block` row (`text-align` + height rule). | as above |
| `table-cell` | `text-align` | `vertical-align: top\|middle\|bottom` (this is the one display type where `vertical-align` actually works) |

Key truths to encode: `vertical-align` only affects inline-level boxes and table cells — it is **not** a general vertical-centering tool. Real vertical centering of block content requires flex/grid (`align-items`/`justify-content`/`align-content`) or a fixed-height container. The command must branch on `getComputedStyle(el).display` (and `flex-direction` when flex) — `roleOf()` (element-registry.js:163-180) already distinguishes `absolute|flex-child|grid-child|block` and is a good starting signal, though it reports the *child* role, not whether the element is itself a flex/grid *container* — the align command needs to also check the element's **own** `display` for the container cases.

### Where it integrates

- **New command** in `runtime/js/commands.js` (alongside `colorElement`, :211): `align(hypId, axis, value)` capturing prior inline values of the affected properties (`text-align`, or the flex/grid props, or `vertical-align`) for undo — same capture pattern as `colorBorder` (:242-288).
- **Apply logic** in `runtime/js/text-format.js` (or a new `align.js`): compute display → choose property per table → `historyPush`.
- **Bridge command** `register("align", …)` in `runtime-main.js` (next to `format`, :77-83).
- **Toolbar group** in `app/index.html` (new `toolbar-group` near the format group :13-18) with 6 buttons (L/C/R, top/middle/bottom) + wiring in `app/js/main.js` (mirror the `formatButtons` loop :413-433). Buttons should reflect/disable per the selected element's display (e.g. vertical disabled for plain block without height).

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — `align(hypId, axis, value)` command that branches on computed `display`/`flex-direction` per the table; never converts a plain block to flex silently. Horizontal always available (`text-align`); vertical enabled only where a real mechanism exists (flex/grid container, table-cell, or fixed-height block). | M | Medium — display branching must be correct; the "block without height" vertical case is the trap. |
| B | Horizontal-only now (`text-align`), defer vertical. | S | Low — but only half the request. |
| C | Vertical via auto-converting blocks to flex (set `display:flex` + justify/align). | M | Higher — mutates layout model of the user's element; can break responsive flow (violates the project's flow-preservation ethos, cf. D1/resize). |

### Owner-decisions

`OWNER-DECISION` (embedded question #2): terminology ("text box" → "selected element's content box") AND vertical-alignment semantics — specifically the plain-block-without-height case: (a) disable vertical there, (b) auto-add `min-height` + flex, or (c) only offer vertical on flex/grid/table-cell/fixed-height. Recommend (a)/(c) to avoid silent layout conversion. The mission's extra question round for R7 should settle this.

---

## R8 — Font-size A+/A− single-fire per selection

**Reproduced with REAL input. Root cause precisely traced.**

### Repro

1. Open deck; real `mouse.dblclick()` on `.slide-title` → enters edit; native double-click selects the word "financeiras " (`selText:"financeiras ", collapsed:false`).
2. Click `#fmt-font-inc` (A+) once.
3. Click `#fmt-font-inc` again **without re-selecting**.

**Observed:**
- After press 1: `<span style="font-size: 34px;">financeiras </span>` created. Selection is now **collapsed** (`collapsed:true, selText:""`), and the range's `commonAncestorContainer` is **`DIV.slide-title`** (the editable root) — `walkUpFinds: null`.
- After press 2: a **new empty** `<span style="font-size: 34px;"></span>` is inserted at the **start** of the element; the original "financeiras " span stays 34px. Span sizes: `["34px","34px"]`.
- After press 3: `["34px","34px","34px"]` — each press adds another empty 34px span at the front.

So the owner's symptom ("only one increase per selection") = press 2+ never bumps the existing span; it spawns a same-size sibling span (the README "sibling-span artifact"). The font visually stops growing.

### Root cause — `runtime/js/text-format.js:49-104` (`adjustFontSize`) + lost selection across the toolbar click

Two compounding causes, both confirmed by the trace:

1. **Selection does not survive the toolbar-click round-trip.** `adjustFontSize` reselects the new span at the end of press 1 (`text-format.js:99-103`):
   ```js
   sel.removeAllRanges();
   const newRange = document.createRange();
   newRange.selectNodeContents(span);
   sel.addRange(newRange);
   ```
   But by the time press 2's handler runs, the live selection is **collapsed to a caret at the editable root** (measured: `collapsed:true`, `commonAncestorContainer = DIV.slide-title`, not the span). The toolbar button's own `mousedown` handler (`app/js/main.js:423-426`) does `e.preventDefault()` + `iframe.contentWindow.focus()`; the focus/blur cycle around clicking a parent-document button collapses and relocates the iframe's selection to offset 0 of the editable. The reselect from press 1 is therefore gone.

2. **The walk-up can't find the existing span, and `expandToWord` can't re-expand a non-text caret.** On press 2, `expandToWord` (`text-format.js:30-47`) receives a collapsed range whose `startContainer` is the DIV (an element node), so it bails immediately:
   ```js
   const node = range.startContainer;
   if (node.nodeType !== Node.TEXT_NODE) return range;   // :33 — element node → no expansion
   ```
   The range stays collapsed and empty. The walk-up loop (`text-format.js:70-81`) starts from the DIV and never reaches the existing 34px span (it's a sibling/descendant, not an ancestor of the caret). So the "update existing span" branch (`:71-80`) is skipped, and the code falls to `surroundContents(span)` on an **empty** range → `<span style="font-size:34px;"></span>` inserted at the caret (front of the element). Same size because `computedSize` (`:86`) reads the editable's base size again.

This matches the README "font-size caret artifact" note exactly, now root-caused to (1) selection loss across the toolbar click and (2) `adjustFontSize` having no fallback when the stored selection is gone.

### Fix options (must allow UNLIMITED repeat presses on one selection)

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED** — Preserve and restore the *actual* selection range across the toolbar click. Snapshot the iframe Selection range on the button's `mousedown` (before focus moves) or keep a module-level "last font-size span + range" in `text-format.js`; on `apply('fontInc')`, if the live selection is collapsed/empty, restore the saved range (or operate directly on the last-edited span). Then the walk-up finds the span and bumps it (`+2px` each press) — verified target behavior: one span, growing. | M | Medium — must capture the range at the right moment (mousedown, before `focus()`), and re-validate the saved range still points into the live editable. |
| B | Make `adjustFontSize` idempotent on the element/word: instead of relying on the live Selection, re-derive the target word-span from a stored anchor (the span created last press) and increment its `font-size`. Track "current font-size span for this edit" in module state, cleared on edit commit (`text-edit.js:125-147`). | M | Medium — needs lifecycle coupling with `text-edit.js` (clear on commit); robust against focus loss because it doesn't depend on `getSelection()`. |
| C | Prevent the selection collapse: change the toolbar button handler so it never blurs the iframe selection (e.g. operate via the bridge without `iframe.contentWindow.focus()`, or restore the saved range inside `apply`). | S-M | Medium — `execCommand` for bold/italic needs focus in the editable, so removing the focus call may break B/I; safer to *restore* the range than to drop the focus call. |

Option A (snapshot+restore the range) is the most direct and fixes the root (selection survival) for all font ops; combine with B's span-tracking as a fallback for maximum robustness.

### Owner-decisions

`OWNER-DECISION` none required — this is a straight bug fix. (Only a UX nicety to confirm: whether A+/A− should keep the word visually selected/highlighted between presses; recommend yes, since restoring the range naturally does this.)

---

## R9 — Outline "no regions detected"

**Reproduced. Root cause + realistic-deck assessment below.**

### Repro

Open the sample deck; the Outline panel (`app/index.html:42-47`, `#outline-list`) renders **"No regions detected"** (the empty state, `app/js/main.js:232-238`). Live:

```json
OUTLINE PANEL: {"items": [], "empty": "No regions detected"}
```

The outline is fed by the `ready` event's `sections` (runtime-main.js:203 → `regions()`), rendered in `main.js:225-253`. `regions()` returned an empty array for this deck.

### Root cause — `runtime/js/element-registry.js:201-253` (`regions()` heuristic fallback)

The deck has **no** `data-hyp-region` hints, so the H3-priority branch (element-registry.js:188-198) is skipped and the heuristic fallback runs. Live structural diagnosis:

```json
REGIONS DIAG: {"bodyChildCount": 10, "bodyChildTags": ["section.slide","section.slide","section.slide"],
               "contentRoot": "section.slide", "contentRootTextCount": 32, "contentRootChildCount": 3}
```

The heuristic:
```js
// element-registry.js:207-226  — candidate pool = body children + their grandchildren
const candidates = [];
for (const child of bodyChildren) { candidates.push(child); for (const grandchild of child.children) candidates.push(grandchild); }
let contentRoot = null; let maxTextCount = -1;
for (const cand of candidates) {                       // pick the SINGLE densest candidate
  const count = countTextDescendants(cand);
  if (count > maxTextCount) { maxTextCount = count; contentRoot = cand; }
}
if (!contentRoot) return [];
const directChildren = Array.from(contentRoot.children)…   // only THIS node's children become region candidates
```
Then (element-registry.js:238-251) it emits a region only for a `contentRoot` **direct child** that is sectioning (`section/article/header/footer/main/aside/nav`, :33-35) OR has a repeated class+tag signature among its siblings (:242-244):
```js
const isRepeated = sigCounts.get(sig) > 1;
const isSectioning = SECTIONING_TAGS.has(tag);
if (isSectioning || isRepeated) { … result.push(…) }
```

**Why it fails for this deck:** the 10 sibling `<section class="slide">` are body children, but the algorithm does not treat body children as the region set. It picks **one** `contentRoot` = the single text-densest node among {body children + grandchildren} → that is **one** `section.slide` (text count 32), and then looks only at **that one slide's 3 children** (its inner divs). Those 3 children are neither sectioning nor repeated-3+-signature, so **zero** regions are emitted. The 10 slides — the obvious regions — are never the list examined, because the predicate descends into the densest single slide instead of recognizing the sibling-section run at body level.

The failing predicate is the `contentRoot` selection itself: it assumes a single dense content container (the "report" fixture shape) and is wrong for a slide deck where the regions ARE the top-level sibling sections.

### Would it detect regions on ANY realistic AI-generated deck? **Largely no.**

It only succeeds when the densest single container's direct children happen to be sectioning tags or a 2+ repeated class signature. Requirements that make it brittle:
- It needs the regions to be **direct children of the one densest node**, not body-level siblings. Any deck whose slides are top-level `<section>`/`<div class="slide">` siblings of `<body>` (the most common AI-generated pattern, and exactly this fixture) fails.
- A report with one `<main>`/`<article>` wrapper whose children are repeated `.section` blocks would work — but that's the report shape, not a deck.
- It depends on consistent class signatures (`tag|className`, :87-89); decks with per-slide unique classes (e.g. `slide--cover`, `slide--metrics`) defeat the "repeated signature" test even at the right level (note: this deck's sections share `slide` but also carry unique modifiers; `getSignature` uses the full `className` string :88, so `slide slide--cover` ≠ `slide slide--metrics` → not "repeated"). This is a second latent failure even if body-level scanning were used naively with full-className signatures.

So the heuristic is tuned for a single-content-root report and does not generalize to the dominant deck structure.

### Fix options

| # | Option | Effort | Risk |
|---|--------|--------|------|
| A | **RECOMMENDED (if fixing)** — Add a body-level sibling-section detector that runs first: if `body` has N≥2 children that are sectioning tags OR share a common base class token (e.g. all contain class `slide`/`section`), treat **those** as regions. Use a relaxed signature (primary/first class token, like comments.js `getPrimaryClassSignature` :62-69) instead of the full className so `slide slide--cover` and `slide slide--metrics` both match on `slide`. Fall back to the current content-root heuristic for report-shaped docs. | M | Medium — must not regress the report fixture; needs a clear "deck vs report" branch. |
| B | Broaden the existing heuristic minimally: also consider **body children themselves** as a region set (not just the densest node's children), and switch `getSignature` to a primary-class-token signature. | S-M | Medium — simpler, but mixing body-level and content-root logic risks double-listing on report docs. |
| C | **Remove the outline panel entirely.** Touches: `app/index.html:42-47` (the `.outline-panel` block), `app/js/main.js` — `renderOutline`/`outlineRegions`/`activeOutlineHypId`/`setActiveOutline` (:11-13, :225-262), the `ready` handler call `renderOutline(...)` (:269), the `selection-changed` → `setActiveOutline` wiring (:273-275), and the `sections` payload from `runtime-main.js:203` + `regions()` consumer (regions() itself can stay for future use or be dropped). Outline-related CSS in `app/css/shell.css`. | S-M | Low functionally (it's already non-functional for decks); but discards a feature the owner might want fixed. |

### Owner-decisions

`OWNER-DECISION` (embedded question #3): **fix detection (A/B) vs remove the panel (C).** If fix: confirm the deck-vs-report heuristic and the primary-class-token signature relaxation. If remove: option C's touch-list applies.

---

## Cross-cutting findings

### Why v2's 67/67 green suite missed R1, R2, R8 in real use

The common failure mode is **the tests verified structure/seams, not real-input behavioral outcomes**, and **encoded skips that count as green when the behavior is absent.**

| Item | What the suite checked | What it never checked (the actual defect) |
|------|------------------------|-------------------------------------------|
| **R2 (resize dead)** | Presence of `.moveable-control-box`, `.moveable-direction`, wrapper, ring (E-F2-1/2/3). The two real-drag tests (E-F2-4/5) only looked for a `.moveable-line` guideline and **`skipTest` if not found** (test_f2_select_guides.py:143-144, 195-196). | That a real handle drag **changes the element's computed width/height/translate.** No geometry assertion exists anywhere. A 100%-dead resize passes. |
| **R1 (dialog behind)** | Dialog open/cancel via the **fake launcher seam** (`/api/_test/set-dialog`, server.py:138-143; api.py `set_dialog_launcher` :39-43). The real `_run_ps_dialog_default` (api.py:73-96) was **never executed** by tests — changelog row-62 says so explicitly ("real PowerShell dialog exercised via seam only"). | Z-order / window-ownership of the **real** PowerShell dialog. The seam returns a path string with no window at all, so "behind the browser" is structurally untestable by the seam. |
| **R8 (font-size single-fire)** | Likely a single A+ press and/or innerHTML-changed assertion. | **Repeated presses on one selection** across the toolbar-click focus cycle. The bug only manifests on press 2+, and only because the live Selection collapses between parent-button clicks — invisible to any test that presses once or re-selects between presses. Indeed the README already documented it as a "known limitation", so it was a *known-shipped* gap, not a missed regression. |

Underlying causes:
1. **Synthetic selection in tests.** Several F2 tests select via `el.dispatchEvent(new MouseEvent('click'))` (lines 117, 158, 254) — which doesn't exercise the real pointer path and can't reveal pointer-events-dead handles. D15 now bans this; it must be enforced.
2. **`skipTest` as a silent pass.** Real-drag tests degrade to skip when the drag has no effect — the exact bug condition is swallowed. A skipped behavioral test should be a **failure** in a behavioral suite, or the behavior should be asserted unconditionally.
3. **Seam-only coverage of OS-boundary behavior.** Window z-order, native dialogs, and clipboard live outside the DOM and outside the seam. The seam validates control-flow, not the OS-level UX the owner actually experiences.

### Test-strategy change that prevents recurrence (seeds the new test plan)

1. **Assert outcomes, not artifacts.** Every interaction test must assert a **measured state change**: resize → `getComputedStyle(el).width/height` (or inline `flex-basis`) differs by ~the drag delta; move → `el.style.translate` changes; reorder → DOM index changes; font-size → the *same* span's `font-size` increases by 2px per press. Presence of `.moveable-*` nodes is necessary but never sufficient.
2. **Real input only for interaction (enforce D15).** Drags/clicks/keypresses via `page.mouse.*` / `page.keyboard.*` / CDP `Input.*`. Ban `element.dispatchEvent(MouseEvent)` for selection and interaction in the suite (grep-gate the test files in CI).
3. **No skip-as-green for behavioral tests.** Replace `self.skipTest(...)` in drag/resize tests with hard assertions. If a handle can't be found or a drag has no effect, that is a **FAIL** (it is the bug). Keep skips only for genuinely environment-unavailable cases, never for "the behavior didn't happen".
4. **Repeat-operation coverage.** Add explicit "press A+ three times on one selection → exactly one span, size grew by 6px" and "drag the same handle twice" cases. Single-fire bugs and idempotency bugs only appear on N≥2.
5. **OS-boundary smoke (manual or instrumented).** The real PowerShell dialog's z-order and the real clipboard write cannot be covered by the seam. Add a documented **manual smoke checklist** (one real Open, one real Save As, confirm dialog appears above Chrome; one real token copy-HEX) gated before EXIT — the row-62 caveat must become a required check, not an optional note. If automatable, drive the real dialog via an OS-level UI automation (out of Playwright's scope; pywinauto/UIA) — but at minimum, make the manual smoke a blocking gate.
6. **Pointer-events regression guard for R2 specifically.** After the fix, add a test that asserts `document.elementFromPoint(handleCenter)` returns a `.moveable-*` element (i.e. handles are actually hittable), not `null`. This directly locks the R2 root cause.

### External-info needs parked (no web research performed, per mission)

- **R6 normalization:** whether to expose/normalize token values to `#rrggbb` (some `:root` tokens may be `rgb()`/named). `color.js:rgbToHex` (:169-175) handles rgb→hex but not named colors or hsl; if full normalization is wanted, the supported input space needs confirming. No web research needed to ship raw-value copy (recommended default); parked only if normalized output is chosen.
- **R2 Option C:** whether the **vendored** `app/js/vendor/moveable.min.js` version supports a shadow-DOM/portal rendering option (which would make its `:host` pointer-events rules apply natively). Determining this requires reading the vendored version's API/changelog — deferred; **Option A (re-enable pointer-events on the control elements) needs no external info and is recommended**, so this is non-blocking.
- **R1 Option B:** exact reliability of `[Microsoft.VisualBasic.Interaction]::AppActivate` / `SetForegroundWindow` under Windows 11 foreground-lock policy — would need platform docs. **Option A (TopMost hidden owner form) is the recommended, well-established fix and needs no external info**, so this is non-blocking.

---

## Evidence appendix (commands + key observations)

- Server: `python server/server.py 127.0.0.1 8791` with `HYP_TEST_DIALOG=1` (env set in-process via PowerShell; the seam `/api/_test/set-dialog` returned `200 {"ok":true}`).
- Open path: `POST /api/_test/set-dialog {"path": <temp deck copy>}` then click `#open-btn`; waited on `iframe.contentWindow.hyp`.
- R2 measured: `.research-card` 198×250 before and after a real SE-handle drag (+60px/+40px, 12 steps); `elementFromPoint(handleCenter)=null`; control-box & handle computed `pointer-events:none` (inherited from `#hyp-interaction-wrapper`); Moveable vendored CSS `pointer-events` rules all `:host`-scoped (1 `auto`, on `:host[data-able-origindraggable] .control.origin`).
- R8 measured: word "financeiras " selected on dblclick; press1 → one 34px span, selection collapsed to `DIV.slide-title`; press2 → empty 34px span prepended; press3 → second empty 34px span (`["34px","34px","34px"]`).
- R4 measured: no-selection `#color-btn` click opened Coloris on `{scope:"token", target:"--primary"}`.
- R9 measured: body has 10 `section.slide` children; `regions()` picks one slide as `contentRoot` (textCount 32, 3 children) → 0 regions → "No regions detected".
- R5/R6 measured: `navigator.clipboard.writeText("#123456")` → `wrote:true`, `readback:"#123456"`, `isSecureContext:true` on `http://127.0.0.1:8791`.
- All product files untouched; server + Chromium killed; scratch scripts deleted.
