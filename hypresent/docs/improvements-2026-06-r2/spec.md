# Hypresent v3 — Feature Specification (Session 2, improvements-2026-06-r2)

Authoritative, executor-ready specification for the Session-2 improvement cycle (scorecard R1–R9 + EXIT). Grounded in `changelog.md` Session-2 block (Exit Scorecard, Decision Register D15–D24, User Decisions U11–U16 + the still-binding Session-1 U1–U10a and carried protocols D8/D12/D14), `docs/improvements-2026-06-r2/user-feedback.md` (owner verbatim), and `docs/improvements-2026-06-r2/diagnosis.md` (authoritative root causes + landing maps + decision tables — the fix selections are FIXED per D19 and are NOT relitigated here).

This document extends the v1 contracts (`docs/spec/01-architecture.md`, `02-html-convention.md`, `03-module-map.md`, `05-verification-plan.md`) and the v2 spec (`docs/improvements-2026-06/spec.md`, S0–S27). It NEVER supersedes a v1/v2 locked decision. All injected classes/ids stay `hyp-`prefixed; all injected attributes stay `data-hyp-*` (A12). The app runtime stays dependency-free (A9/A10); Playwright remains dev/test only. The document's own scripts/styles/handlers are never sanitized away (A8/A11).

**Anchor discipline (binding for all downstream tasks):** every `file:line` citation in this spec is a NON-BINDING hint. The live code on `hypresent-v2` has drifted from the diagnosis line numbers (the diagnosis was written against an earlier read and several v2-accepted fixes landed after). Downstream task files MUST locate every edit by the quoted code CONTENT, never by line number. Where this spec cites a line, the executor re-locates by the surrounding quoted code.

---

## 0. Live-code reconciliation (contradictions between diagnosis and current source — flagged loudly)

The diagnosis is authoritative on ROOT CAUSE and FIX SELECTION. It drifted from the live source on a few mechanical points. These do NOT change any fix decision (D19); they change WHERE/HOW the anchor is matched. Stated here so no downstream task trusts a stale line number.

| # | Diagnosis statement | Live source on `hypresent-v2` | Impact on the fix |
|---|---------------------|-------------------------------|-------------------|
| C1 (R2) | "R2 root cause: `interaction.js:150-157`; handles inherit `pointer-events:none`; `elementFromPoint=null`." | The pointer-events-none wrapper is real (`createWrapper()`, the `Object.assign(... pointerEvents: "none" ...)` line). BUT `onDragEnd` ALREADY contains a v2-accepted hit-test workaround that temporarily sets `el.style.pointerEvents="none"` around `classifyDrop` (the "Temporarily disable pointer events on the dragged element" block). That workaround is for the DROP hit-test only; it does NOT make the resize/drag HANDLES hittable. R2's root cause (handles unhittable because the control box inherits `pointer-events:none` and Moveable's compensation CSS is `:host`-scoped) STANDS unchanged. | None to the fix selection (D19 R2 = scoped `pointer-events:auto` rule injected into the iframe). The fix is additive and independent of the existing onDragEnd workaround. The R2 task MUST NOT touch or remove the onDragEnd pointer-events block. |
| C2 (R9) | "`sections` payload + `regions()` consumer … `regions()` itself can stay for future use or be dropped." | Grep of the entire product tree confirms `sections` (emitted at `runtime-main.js` `emit("ready", { tokens: …, sections: regions() })`) is consumed by EXACTLY ONE site: `main.js` `renderOutline(payload.sections …)` inside the `ready` handler. `regions` is imported only at `runtime-main.js` top and called only at that one emit. There is NO other consumer anywhere in `app/` or `runtime/`. | Decides the open question in U12: because nothing else consumes `regions()` or `sections`, BOTH are stripped end-to-end (see R9 below). Not "may stay" — they go. |
| C3 (R4/R7) | main.js handler line numbers (`#color-btn` 436-448; formatButtons 413-433). | Live `main.js` matches these closely (the `#color-btn` block and the `formatButtons` loop are present verbatim as quoted in the diagnosis). | None; anchors are valid by content. |
| C4 (R5/R6) | color-popover token rows at `:132-149`, header at `:107`, change listener at `:221`; `rgbToHex` "not exported". | Live `color-popover.js` matches (token-row `for` loop, `Palette Tokens` header div, the `container.addEventListener("change", …)` block). `rgbToHex` confirmed present in `color.js` as a module-PRIVATE function (used by `readElementBorder`/`readElementColors`, both already exported) — NOT exported. | None to fix selection; R6 exports `rgbToHex` (D17) and adds a non-rgb fallback. |
| C5 (R3) | "no element-delete command anywhere." | Confirmed: grep finds no `delete-element` bridge command, no element-delete factory, no Delete/Backspace element handler. `commands.js` already has `reorder` (with its `place()` helper) and `colorBorder` to mirror. `comments.js` `threads()` already marks `unanchored:!el`; `reanchorAfterMove` exists. | None; R3 is a clean addition built on existing patterns. |

**No contradiction invalidates any D19 fix.** All five are mechanical (anchor location / consumer count), and each is resolved above.

---

## Spec-level decisions (S-numbers; resolve every ambiguity the scope delegated)

These extend (never replace) v2's S0–S27. Kimi treats each as binding.

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| V3-S1 | R1 fix = a hidden, `TopMost`, minimized, no-taskbar owner WinForms Form created in BOTH `_OPEN_PS` and `_SAVE_PS`, passed to `$d.ShowDialog($owner)`, then `$owner.Dispose()`. `ShowHelp` stays (harmless) OR is removed (it is the failing hack); spec removes it to avoid a misleading second mechanism. `-STA` stays (already on the launcher). | D19 option A; a `TopMost` owner deterministically forces the dialog above Chrome (it inherits the owner's top-most band); pure-PS, no new dep. |
| V3-S2 | R1 verification = a stdlib `ctypes` Win32 z-order test against the REAL dialog endpoint (NOT the seam): drive the real `_run_ps_dialog_default` so a genuine OS dialog appears, `EnumWindows` to find it by title, assert it is foreground/top-most, then `WM_CLOSE` it. Skip ONLY if no interactive desktop session (this machine HAS one → it runs). | D22/D23; OS z-order is outside Playwright; ctypes keeps the app dependency-free. |
| V3-S3 | R2 fix = a `hyp-`scoped stylesheet rule injected ONCE into the iframe document that re-enables `pointer-events:auto` on Moveable's control elements under the wrapper. Selector covers `.moveable-control-box`, `.moveable-control`, `.moveable-line`, `.moveable-area`, `.moveable-direction` scoped under `#hyp-interaction-wrapper`. Injected from `interaction.js` at wrapper creation (a `hyp-`id'd `<style>` appended to the iframe `document.head`). | D19 option A; surgical, only Moveable's own controls become interactive; the wrapper stays click-through for empty regions. |
| V3-S4 | R2 keeps the wrapper `pointer-events:none` (empty-region click-through is required for select/clear). Only the named control descendants get `auto` — INCLUDING `.moveable-area` (the body-drag MOVE surface; a real body-drag produced no `translate` without it). The existing `onDragEnd` drop-hit-test pointer-events toggle is UNCHANGED and is NOT extended to `.moveable-area`. | The two mechanisms are orthogonal (handles-hittable vs drop-see-beneath); both are needed. RV07 skip-confirmed: making `.moveable-area` hittable does NOT pollute the drop hit-test because `classifyDrop`'s scanner (`reorder.js` `elementUnderPointerSkippingHypChrome`) already skips every Moveable-internal element via its `#hyp-interaction-wrapper` ancestor (the `[id^="hyp-"]` branch of its `closest()` filter) — verified against live `reorder.js`. |
| V3-S5 | R3 delete = a `deleteElement(hypId)` command factory in `commands.js` mirroring `reorder`'s `place()` capture pattern: capture parent hyp-id + nextSibling hyp-id + the detached node ref; `do()` = `parent.removeChild(el)`; `undo()` = re-insert the captured node before the captured next-sibling anchor (or append). Node ref is captured so undo restores the exact subtree (it keeps its `data-hyp-id`). | D20 + diagnosis R3 map; mirrors the proven reorder undo contract; node keeps its id so `byId` re-resolves on re-attach. |
| V3-S6 | R3 trigger = TOOLBAR BUTTON ONLY (`🗑`). NO Delete/Backspace key handler is added anywhere (U14). The button reads the current selection via `get-selection`; if a `hypId` exists it calls `delete-element`; else a status message "Select an element to delete." | U14 explicit; a keyboard path would collide with text-edit character deletion and native form controls. |
| V3-S7 | R3 last-region guard = `delete-element` refuses to delete the only remaining top-level region (a `document.body` direct-child element that is the sole `[data-hyp-id]`-bearing body child) and returns `{blocked:"last-region"}`; the shell shows a status message "Cannot delete the last remaining region." | D20; avoids an empty-document state. |
| V3-S8 | R3 thread fate = anchored threads on a deleted element are KEPT and shown "Unanchored" (U15), identical to move semantics; `delete-element` calls `comments.reanchorAfterMove()` after BOTH `do()` and `undo()` so anchors recompute (the thread re-anchors on undo). Threads are NEVER cascade-deleted. | U15 explicit; mirrors v2 reorder; `reanchorAfterMove` already iterates ALL threads and never deletes. |
| V3-S9 | R3 selection + Moveable cleanup = after a successful delete, `delete-element` calls `selection.clear()`. The selection observer (runtime-main `boot()`) fires with `null` → `interaction.unmount()` tears down the Moveable bound to the now-removed target. No explicit `interaction` call from comments/commands (avoids an import into the runtime command layer). | Diagnosis R3 map; reuses the existing observer wiring; keeps the delete path free of interaction.js imports. |
| V3-S10 | R3 edit-active guard = `delete-element` is a no-op returning `{blocked:"editing"}` when a text edit is active. Detection = `document.activeElement` has `contenteditable==="true"` (the same signal `text-format.js` `getActiveEditElement` uses). The button handler in the shell is also gated, but the runtime command re-checks (defense in depth). | Diagnosis R3 edge case; prevents deleting the element while the user is mid-text-edit. |
| V3-S11 | R4 = DELETE `#color-btn`: remove the `<button … id="color-btn" …>` line from `index.html` AND its enclosing empty `toolbar-group` wrapper (the `<div class="toolbar-group"> … 🎨 … </div>` that contains ONLY this button), AND the `const colorBtn = document.getElementById("color-btn"); …` handler block in `main.js`. | U11 explicit; the button is redundant (diagnosis R4) and its enclosing group has no other child. |
| V3-S12 | R5 = a single header-level info affordance on the "Palette Tokens" header (diagnosis option A, D18). A `<span class="hyp-token-info" title="…">ⓘ</span>` appended inside the existing `.hyp-color-header` that reads "Palette Tokens". Title text VERBATIM per D18: "Changing a palette token recolors every element using that color across the whole document." No per-row tooltip. | D18; one message, zero per-row noise; matches the owner's own phrasing. |
| V3-S13 | R6 = a discreet per-token copy-HEX button appended to each `.hyp-token-row` (after the token name, before/around the Coloris input). Button `class="hyp-token-copy"`, `data-hex="<normalized #rrggbb>"`, `title="Copy HEX"`. A delegated `click` handler on the existing `container` listener region calls `navigator.clipboard.writeText(hex)` and shows a transient "copied" affordance (title swap to "Copied!" + a transient class, reverting after ~1200ms). | R6 + D17; clipboard verified working on `http://127.0.0.1` (secure-context exemption); gesture is a real button click. |
| V3-S14 | R6 normalization (D17) = the copied value is normalized to `#rrggbb`: export `rgbToHex` from `color.js`; the token value is normalized at copy time. Because token values may be named/`hsl()` (not `rgb()`), normalization uses a computed-style fallback: resolve the raw token string through a throwaway element's `getComputedStyle().color` to obtain an `rgb(...)` form, then `rgbToHex`. If the value is already `#rrggbb`/`#rgb`, it is normalized to lower-case 6-digit. The DATA path for the copy hex is computed in the RUNTIME (where the document's CSS context resolves named colors correctly), surfaced to the popover via the palette token payload. | D17 "the HEX code"; the runtime owns the document CSS context, so named/hsl resolution is correct there, not in the shell. |
| V3-S15 | R7 = a new `align(hypId, axis, value)` command factory in `commands.js` capturing the prior inline values of EVERY property it may write (`text-align`, `justify-content`, `align-items`, `justify-items`, `align-content`, `justify-self`, `align-self`, `vertical-align`) for exact undo (same capture-all pattern as `colorBorder`). The apply logic branches on `getComputedStyle(el).display` (+ `flexDirection` for flex) per the R7 decision table (normative, reproduced verbatim below). It NEVER converts a plain block to flex. | D21 + diagnosis R7 table; display-branching is the whole correctness surface; capture-all guarantees reversible undo. |
| V3-S16 | R7 horizontal is ALWAYS available (every selectable element gets `text-align` at minimum). Vertical is enabled ONLY where a real mechanism exists: flex container, grid container, `table-cell`, or a block/inline-block with an explicit `height`/`min-height` inline-or-computed > its content. On a plain auto-height block, vertical is DISABLED with a tooltip hint (U13). | U13/D21; honest affordances; no silent layout conversion. |
| V3-S17 | R7 capability bridge = the runtime exposes the selected element's alignment capabilities to the shell by EXTENDING the `selection-changed` event payload (`selection.js` `buildInfo`) with an `alignCaps` object: `{ horizontal:true, vertical:bool, hMap:{left,center,right}, vMap:{top,middle,bottom} }` where each map value is the CSS property+value the command will write for that button (so the shell can both enable/disable AND label honestly). Computed in a new pure helper in `text-format.js`/`align` logic called from `buildInfo`. | D21 "buttons reflect the selected element's capabilities"; extending the existing event is one round-trip, no new command, and the shell already re-renders on `selection-changed`. |
| V3-S18 | R7 toolbar = a new `toolbar-group` placed immediately AFTER the format group (B/I/A+/A−) in `index.html`, with SIX icon buttons: align-left, align-center, align-right (horizontal) and align-top, align-middle, align-bottom (vertical). Icons + tooltips only, NO jargon group label (U16). Tooltip pattern: "Align left (inside its box)", "Align middle (vertical, inside its box)", etc. Buttons wired in `main.js` mirroring the `formatButtons` loop; each sends `align {axis,value}`. Disabled state is set reactively from `selection-changed`'s `alignCaps`. | D21/U16; text-adjacent placement; icon+tooltip honesty; reactive disable. |
| V3-S19 | R7 `align` bridge command = `register("align", …)` in `runtime-main.js` next to the existing `format` registration; payload `{axis:'h'|'v', value:'left'|'center'|'right'|'top'|'middle'|'bottom'}`; resolves the current selection's hypId itself (no hypId in payload) so it works on the selected element exactly like the toolbar expects; applies via the `align` apply logic + `historyPush`. | D21; selection-scoped like format; one undoable command per press. |
| V3-S20 | R8 fix = snapshot/restore the actual iframe Selection range across the toolbar click (D19 option A) PLUS a tracked-span fallback (option B). On the toolbar button's `mousedown` (BEFORE the focus shift), the shell signals the runtime to snapshot the live range; `apply('fontInc'/'fontDec')` restores the snapshot if the live selection has collapsed/relocated, then operates. A module-level "current font-size span for this edit" is also tracked and used as a fallback when no usable range exists; the tracked span is CLEARED on edit commit (`text-edit.js` `commit`). | D19 options A+B; A fixes the root (selection survival) for all font ops, B is the robustness net for the focus-loss case; lifecycle clear prevents stale-span reuse across edits. |
| V3-S21 | R8 snapshot point = the runtime exposes a `format-snapshot` bridge command (registered in `runtime-main.js`) that captures the current iframe Selection's first range (cloned) into module state in `text-format.js`. The shell's existing toolbar `mousedown` handler (which already does `e.preventDefault(); iframe.contentWindow.focus();` for the format buttons) is extended to FIRST fire `bridge.command("format-snapshot")` for the font-size buttons (and harmlessly for B/I) BEFORE the focus call. | Diagnosis R8 root cause #1 (the mousedown focus cycle collapses the selection); snapshotting before the focus call is the only point where the original range is still live. |
| V3-S22 | R8 restore = SNAPSHOT-ALWAYS-WINS. On `apply`, if a mousedown snapshot exists AND is still valid (its `startContainer` and `endContainer` are both connected — `isConnected` — AND the active editable `contains` its `commonAncestorContainer`), restore that snapshot range UNCONDITIONALLY, then operate. There is NO collapse-detection on the live selection: the post-toolbar-click live selection is focus-shift garbage by construction (the mousedown→focus cycle relocated it), so the validated snapshot ALWAYS supersedes it. If no valid snapshot exists, operate on the live selection (current behavior). If neither yields a usable range, fall back to the tracked span (`currentFontSpan`): bump its `font-size` directly. The snapshot is consumed (cleared) and re-taken on the next mousedown. NO `commonAncestorContainer === el`-style live-collapse check exists anywhere in the R8 path. | Diagnosis R8 root cause #2 (`expandToWord` bails on a non-text caret; the walk-up never reaches the existing span). The collapse-detection design was brittle — Chromium collapses to the first TEXT NODE after `focus()`, not to the editable element, so an identity check on the container never matches (RV04). Restoring the validated snapshot unconditionally sidesteps the detection problem entirely. |
| V3-S23 | R9 = REMOVE the outline panel entirely (U12, diagnosis option C). Touch-list: `index.html` `.outline-panel` block; `main.js` `outlineRegions`/`activeOutlineHypId` declarations, `renderOutline`, `setActiveOutline`, the `renderOutline(...)` call in the `ready` handler, the `selection-changed → setActiveOutline` wiring; the `.outline-*` CSS in `shell.css`; `runtime-main.js` `sections: regions()` in the `ready` emit AND the `regions` import; `element-registry.js` `regions()` export (+ its private helpers used ONLY by it: `countTextDescendants`, `getSignature`, `getRegionLabel`, `SECTIONING_TAGS`, `isDecorativeForRegions` — each removed ONLY if no other consumer remains; verify by grep). | U12 + C2 (nothing else consumes `regions()`/`sections`); full strip, end-to-end. |
| V3-S24 | R9 `regions()` fate = STRIP. Per C2, grep confirms `sections`/`regions()` has no consumer other than the outline. So `regions()` and the `sections` payload are removed end-to-end. The `ready` emit becomes `emit("ready", { tokens: palette.tokens })`. The shell `ready` handler stops reading `payload.sections`. | C2 finding; "keep-if-used-elsewhere, else strip" (U12) resolves to STRIP. |
| V3-S25 | EXIT = the full automated suite green (v2's 67 MINUS the outline-coupled tests removed by R9 — see test-plan — PLUS all new/changed v3 tests), a clean error-free server run on the sample, and zero editor-origin console errors. The R1 ctypes z-order test runs on this machine (interactive desktop present). | EXIT scorecard row; v2 had no dedicated outline test, so the 67 changes only by the F2 test rewrite, not by deletion (see test-plan §"Suite delta"). |

---

## R1 — Native open/save dialogs appear ON TOP of the browser window

### Requirement (trace: user-feedback.md R1)
> "currently opens behind the main window (must open on top of the open browser window … clicked many times thinking it was not working, until I minimized the browser and saw the modal in the back)."

Native Windows open/save dialogs MUST appear on top of (above the z-order of) the focused Chrome window.

### Chosen fix (D19 / V3-S1)
A hidden, `TopMost`, minimized, no-taskbar owner WinForms `Form` is created in each PowerShell dialog script and passed to `ShowDialog($owner)`, then disposed. The dialog inherits the owner's top-most band → renders above all normal-z windows including Chrome, deterministically. Applies identically to `_OPEN_PS` and `_SAVE_PS` in `server/api.py`. The unreliable `$d.ShowHelp = $true` foreground hack is removed (it is the current failing mechanism; leaving it would be a misleading second path).

### Precise behavior spec
- Each PS script, before `$d.ShowDialog(...)`:
  ```powershell
  $owner = New-Object System.Windows.Forms.Form
  $owner.TopMost = $true
  $owner.ShowInTaskbar = $false
  $owner.WindowState = 'Minimized'
  $owner.Opacity = 0
  $owner.Show()
  ```
  then `if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.FileName }`, then in a `finally`-equivalent: `$owner.Close(); $owner.Dispose()`.
- `-STA` stays on the launcher argv (`_ps_args`); `[Console]::OutputEncoding = UTF8` stays for non-ASCII paths; the `pwsh`→`powershell.exe` fallback (S23a) is UNCHANGED.
- Cancel contract UNCHANGED: empty stripped stdout ⇒ `None` ⇒ `{"cancelled":true}` (200).
- `set_open_path` tracking, `handle_save` no-open fallback (S24) — UNCHANGED.

### Edge cases
| Case | Behavior |
|------|----------|
| User clicks away mid-open | Default V3-S1 behavior: the dialog appears on top, focused (owner is `TopMost`). Matches the request; no extra focus-steal logic. |
| Owner Form fails to create (headless service context) | Dialog still shows ownerless (current behavior) — no regression; the owner block is wrapped so a creation failure does not abort the dialog. Tests inject a fake launcher (no real PS). |
| Non-ASCII path | `[Console]::OutputEncoding=UTF8` + `subprocess.run(...,encoding="utf-8")` — UNCHANGED. |
| Neither `pwsh` nor `powershell.exe` | Launcher raises `FileNotFoundError` → handler 500 — UNCHANGED. |

### Acceptance criteria (MEASURED OUTCOMES)
- **OS z-order (real dialog, ctypes — V3-S2):** with a real `_run_ps_dialog_default("open")` running in a background thread so a genuine OS dialog appears, `EnumWindows` finds a top-level window whose title contains "Open Presentation" (open) / "Save As" (save); `GetForegroundWindow()` equals that HWND OR the window's extended style includes `WS_EX_TOPMOST` (the owner-inherited top-most band); the test then posts `WM_CLOSE` to it and asserts the launcher returns (cancel → `None`). MEASURED: foreground/top-most HWND match, not "a dialog object exists".
- **Seam regression (unchanged routes):** `handle_dialog_open()` with a fake launcher returning a path → `(200,{html,dir,name})`; returning `None` → `(200,{"cancelled":True})`; `handle_save` with no open path → `(200,{"no_open_file":True})`. (These re-lock the F1 routes that R1 must not break.)

---

## R2 — Resize works via real handle drag

### Requirement (trace: user-feedback.md R2)
> "I see the 'box' around the item with 'circles' edges … but when I click there and drag, nothing happens."

Dragging a resize handle MUST resize the element (and dragging the body MUST move it).

### Chosen fix (D19 / V3-S3, V3-S4)
The root cause (diagnosis R2, reconciled in C1) is that Moveable's control box and handles are plain light-DOM children of the `pointer-events:none` `#hyp-interaction-wrapper`, and Moveable's compensating pointer-events CSS is `:host`-scoped (shadow-DOM only) so it never applies. Fix: inject ONCE into the iframe document a `hyp-`scoped stylesheet that re-enables `pointer-events:auto` on Moveable's control elements scoped under the wrapper. The wrapper itself stays `pointer-events:none` so empty-region clicks still pass through to select/clear. The existing `onDragEnd` drop-hit-test pointer-events toggle (a v2-accepted fix) is left untouched (C1, V3-S4).

### Precise behavior spec
- A new `hyp-`id'd `<style id="hyp-interaction-style">` is appended to the iframe `document.head` exactly once (idempotent: skip if `document.getElementById("hyp-interaction-style")` exists), at wrapper creation in `interaction.js`. Rule:
  ```css
  #hyp-interaction-wrapper .moveable-control-box,
  #hyp-interaction-wrapper .moveable-control,
  #hyp-interaction-wrapper .moveable-line,
  #hyp-interaction-wrapper .moveable-area,
  #hyp-interaction-wrapper .moveable-direction { pointer-events: auto; }
  ```
- The wrapper's inline `pointerEvents:"none"` (in `createWrapper`) is UNCHANGED.
- No change to `buildMoveable`, snapping config, the FLIP logic, or the resize/drag commit logic — those already exist and work once the pointer reaches the handle.

### Regression guard (mandated by scope)
A test asserts `document.elementFromPoint(handleCenter)` resolves to a `.moveable-*` element (the SE/E resize handle, hittable), NOT `null`. This directly locks the R2 root cause: pre-fix it was `null`; post-fix it must be a Moveable control.

### Edge cases
| Case | Behavior |
|------|----------|
| Style injected twice (remount) | Idempotent — the `getElementById` guard skips re-append. |
| Wrapper torn down on unmount | The `<style>` may be left in `document.head` (harmless, `hyp-`id'd, stripped at serialize); OR removed in `teardown` alongside the wrapper. Spec: remove it in `teardown` for cleanliness (it is editor chrome). |
| Document with its own `.moveable-*` classes | Vanishingly unlikely (these are Moveable-vendor class names); the rule is scoped under `#hyp-interaction-wrapper`, so only Moveable's controls inside our wrapper are affected — never the document's own elements (they are not under our wrapper). |
| Resize after the fix | A real SE-handle drag of +Δpx changes the element's inline/computed size by ~Δ (the existing `onResize`/`onResizeEnd` sizing logic runs once the handle receives the pointer). |

### Acceptance criteria (MEASURED OUTCOMES)
- **Hittability guard:** after selecting an element, `document.elementFromPoint(seHandleCenterX, seHandleCenterY)` (computed from the handle's `getBoundingClientRect`) returns an element matching `[class*="moveable-"]`, not `null`.
- **Resize outcome (N≥2 repeats):** a real `mouse.down()` on the SE handle → ≥8 incremental `mouse.move(+Δx,+Δy)` → `mouse.up()` changes the element's computed `width` AND `height` by approximately the drag delta (within a tolerance, e.g. |Δactual − Δdrag| ≤ 20px to absorb snapping); a SECOND independent drag on the same element changes the size AGAIN (idempotency: the handle is not a one-shot). MEASURED: `getComputedStyle(el).width/height` deltas, not handle presence.
- **Move outcome (delta, N=1):** a real body drag with a cumulative delta ≥40px changes `el.style.translate` by APPROXIMATELY the drag delta (Δx/Δy within ±15px for snapping), not merely to a non-empty value (S1 property); a click (zero-distance drag) writes none (R05 guard, already present). This is the orchestrator-mandated MOVE coverage — the body-drag produced no translate pre-fix.
- **Reorder outcome (real input):** one real drag of a `[data-hyp-id]` sibling over its adjacent `[data-hyp-id]` sibling (overlap) changes the dragged element's DOM child-index — the v2 F3 reorder-on-overlap behavior, now exercised under REAL pointer input (orchestrator-mandated).

---

## R3 — Element deletion

### Requirement (trace: user-feedback.md R3)
> "does not exist, there should be an option to delete element."

A user-facing way to delete the selected element, with the UX settled by the question round (U14/U15/D20).

### Chosen fix (U14/U15/D20 / V3-S5–S10)
A `deleteElement` command (full undo via captured parent/nextSibling/node, mirroring `reorder`'s `place()`), a `delete-element` bridge command, and a TOOLBAR `🗑` BUTTON ONLY (no keyboard). Threads on the deleted element go Unanchored (kept, never lost); undo re-anchors. Deleting the last top-level region is blocked with a status message. Selection is cleared (→ Moveable teardown via the observer).

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/commands.js` | MOD | Add `deleteElement(hypId)` factory: captures `parentHypId`, `nextHypId` (next sibling's `data-hyp-id` or null), and the detached node ref; `do()` = `parent.removeChild(el)`; `undo()` = re-insert the captured node before the captured next-sibling (resolve by hyp-id; append if null). Mirrors `reorder`'s `place()` helper. |
| `runtime/js/runtime-main.js` | MOD | Register `delete-element {hypId}`: edit-active guard (V3-S10) → `{blocked:"editing"}`; last-region guard (V3-S7) → `{blocked:"last-region"}`; else `historyPush(deleteElement(hypId))`, `comments.reanchorAfterMove()`, `selection.clear()`, return `{deleted:hypId}`. Import `clear` from selection.js (already imported) and `reanchorAfterMove` from comments.js (NEW import). |
| `app/index.html` | MOD | Add a `🗑` `tool-btn` `id="delete-btn"` to a toolbar group (placed with the other element-action buttons, e.g. beside comment). |
| `app/js/main.js` | MOD | Wire `#delete-btn`: `get-selection` → if no `hypId`, status "Select an element to delete."; else `delete-element {hypId}` → on `{blocked}` show the matching status; else `refreshCommentPanel()` (threads may have gone unanchored). |

### Exact algorithm — delete command (V3-S5)
```
deleteElement(hypId):
  el = byId(hypId)                       // throws if not found
  parent = el.parentElement
  parentHypId = parent.getAttribute('data-hyp-id') || null   // body has none → null path handled by place()
  nextHypId = el.nextElementSibling?.getAttribute('data-hyp-id') ?? null
  node = el                              // capture the live node ref for exact-subtree undo
  do():   parent.removeChild(node)
  undo(): place(node, parentHypId, nextHypId)   // resolve parent by hyp-id OR use captured parent if body; insertBefore next (or append)
```
`place()` for undo: if `parentHypId` resolves via `byId`, insert into it; if the original parent was `document.body` (no hyp-id), insert into `document.body`. Resolve `nextHypId` via `byId`; if present and still a child of the resolved parent, `insertBefore`; else `appendChild`. The node keeps its `data-hyp-id`, so `byId` resolves it again once re-attached.

### Last-region guard (V3-S7)
```
isLastTopLevelRegion(el):
  if el.parentElement !== document.body: return false
  bodyRegionChildren = [c for c in document.body.children if c.getAttribute('data-hyp-id')]
  return bodyRegionChildren.length <= 1 and bodyRegionChildren[0] === el
```
When true, `delete-element` returns `{blocked:"last-region"}` and does NOTHING.

### Edit-active guard (V3-S10)
```
isEditing():
  a = document.activeElement
  return !!(a && a.getAttribute && a.getAttribute('contenteditable') === 'true')
```
When true, `delete-element` returns `{blocked:"editing"}` and does NOTHING (the user is mid text-edit; deleting the element would be destructive and surprising).

### Iframe/parent split (no keyboard — U14)
There is NO keydown handler for delete anywhere (U14). The only trigger is the parent shell's toolbar button, which calls the `delete-element` bridge command. The diagnosis's "iframe-side keydown" landing is intentionally NOT implemented (U14 overrides it).

### Edge cases
| Case | Required behavior |
|------|-------------------|
| Delete while text-editing | No-op, `{blocked:"editing"}` (V3-S10). The button is gated in the shell AND the runtime re-checks. |
| Delete the body / last region | Body is never selectable (`shouldTag` excludes body). Last top-level region → blocked with status (V3-S7). |
| Delete an element whose descendants have threads | Those threads' anchors no longer resolve → `threads()` marks them `unanchored:true` → shown in the "Unanchored" panel section. Never lost. |
| Delete then Save | The serializer clones the live DOM; the deleted element is simply absent. No special handling; the node-count guard tolerates the live tree. |
| Undo after delete | The captured node (with its `data-hyp-id`) is re-inserted at the captured anchor; `byId` resolves it again; `reanchorAfterMove` re-anchors its threads; markers re-render. |
| Delete an element that is selected | `selection.clear()` after delete → observer fires `null` → `interaction.unmount()` tears down the Moveable (V3-S9). |
| Comment panel after delete | `refreshCommentPanel()` re-reads threads; the deleted element's threads now appear under "Unanchored". |

### Acceptance criteria (MEASURED OUTCOMES)
- **Delete outcome:** select a registered element with a known `data-hyp-id`; click `#delete-btn`; the element is GONE from the live DOM (`doc.querySelector('[data-hyp-id="<id>"]')` is `null`) and `document.body` child count decreased by exactly 1 (for a body-level target). MEASURED: DOM mutation (node count), not button presence.
- **Undo outcome:** after delete, one `undo` re-inserts the element at its original index (`previousElementSibling`/`nextElementSibling` match the pre-delete neighbors); the element's `data-hyp-id` is unchanged.
- **Thread fate:** a thread anchored to the deleted element appears with `unanchored:true` in `comments-read` after delete, and `unanchored:false` (re-anchored) after undo. Thread count is unchanged across delete+undo (never lost).
- **Last-region block:** with exactly one body-level `[data-hyp-id]` region remaining, `delete-element` returns `{blocked:"last-region"}` and the region still exists.
- **Edit guard:** with a `contenteditable="true"` element active, `delete-element` returns `{blocked:"editing"}` and the element still exists.
- **No keyboard path:** pressing `Delete`/`Backspace` with an element selected (not editing) does NOT remove it (no handler exists) — DOM unchanged.
- **Moveable teardown:** after a successful delete, `#hyp-interaction-wrapper` is absent (selection cleared → unmount).

---

## R4 — `#color-btn` 🎨 removal

### Requirement (trace: user-feedback.md R4 + U11)
> "has no apparent function … if this is true, it can be deleted." → Owner decision U11: **DELETE**.

### Chosen fix (U11 / V3-S11)
Remove the button, its handler, and its now-empty `toolbar-group` wrapper. Diagnosis R4 verified the button only opens the first palette token's Coloris picker — fully reachable directly from the always-visible Palette Tokens list; no capability lost.

### Precise behavior spec
- `index.html`: remove the entire `<div class="toolbar-group"> <button … id="color-btn" title="Color picker">🎨</button> </div>` block (the button is the SOLE child of that group → remove the wrapper too).
- `main.js`: remove the `const colorBtn = document.getElementById("color-btn"); if (colorBtn) { … }` block in its entirety.

### Edge cases
| Case | Behavior |
|------|----------|
| Any other code references `#color-btn` | Grep confirms the only references are the `index.html` button and the `main.js` handler; nothing else. Both removed; no dangling reference. |
| Palette/element color still reachable | The Palette Tokens list and the per-element color rows are always visible in the side panel (`color-popover.js`); unaffected. |

### Acceptance criteria (MEASURED OUTCOMES)
- After load, `document.getElementById("color-btn")` is `null`.
- The toolbar group that contained it is absent (no empty `toolbar-group` left behind): the toolbar's `.toolbar-group` count decreased by exactly 1 vs the pre-change DOM.
- Grep of `app/` for `color-btn` yields zero hits.
- The color popover (Palette Tokens + Selected Element rows) still renders and functions (a token color change still dispatches `apply-color`).

---

## R5 — Palette token tooltip

### Requirement (trace: user-feedback.md R5)
> "Palette Tokens work well, but there should be a tooltip to explain that, when editing there, it will edit all components with that color across the doc."

### Chosen fix (D18 / V3-S12)
A single header-level info affordance on the "Palette Tokens" header (diagnosis option A), title text VERBATIM per D18.

### Precise behavior spec
- In `color-popover.js`, the injected `container.innerHTML` block's `<div class="hyp-color-header">Palette Tokens</div>` gains a trailing `<span class="hyp-token-info" title="Changing a palette token recolors every element using that color across the whole document.">ⓘ</span>` (inside the same header div).
- Discreet styling added to the popover's `<style>` block: `.hyp-token-info { margin-left: 0.35rem; color: #999; cursor: help; font-size: 0.7rem; }`.
- No per-row tooltip; the message is the native `title` (hover) on the single ⓘ.

### Edge cases
| Case | Behavior |
|------|----------|
| Header re-rendered | The ⓘ is part of the static injected header markup, not the dynamic token loop → always present once the popover mounts. |
| Screen reader | `ⓘ` carries the explanatory `title`; acceptable for a help affordance (no interactive role needed). |

### Acceptance criteria (MEASURED OUTCOMES)
- The element matching `.hyp-color-popover-container .hyp-token-info` exists; its `title` attribute EQUALS exactly: `Changing a palette token recolors every element using that color across the whole document.`
- It is a descendant of the header whose text contains "Palette Tokens".
- There is exactly ONE such info affordance (not one per token row).

---

## R6 — Per-token discreet copy-HEX button

### Requirement (trace: user-feedback.md R6)
> "For each color of the palette token, user should have a small, 'discreto' [discreet] button to copy the HEX code (for when user wants to apply that color in another component)."

### Chosen fix (R6 + D17 / V3-S13, V3-S14)
A discreet per-row copy button that writes the NORMALIZED `#rrggbb` to the clipboard, with a transient "copied" affordance. Normalization reuses/exports `rgbToHex` and adds a computed-style fallback for named/hsl token values, computed in the runtime where the document CSS context resolves named colors.

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/color.js` | MOD | Export `rgbToHex` (currently module-private). Add a normalization helper `normalizeHex(value)→'#rrggbb'` that: if `value` matches `#rgb`/`#rrggbb` → lower-case 6-digit; else resolve via a throwaway element's computed `color` (`el.style.color=value; getComputedStyle(el).color` → `rgb(...)`) then `rgbToHex`. Include the normalized hex in each token of the `readPalette().tokens` payload as `token.hex`. |
| `app/js/shell/color-popover.js` | MOD | In the token-row template, append `<button type="button" class="hyp-token-copy" data-hex="${escapeHtml(token.hex || token.value)}" title="Copy HEX" aria-label="Copy ${token.name} hex">⧉</button>`. Add a delegated `click` handler (in/near the existing `container.addEventListener("change", …)` region — a sibling `container.addEventListener("click", …)`) matching `.hyp-token-copy`: `navigator.clipboard.writeText(btn.dataset.hex)`; on success swap `title`→"Copied!" + add a transient `.hyp-token-copied` class, reverting after ~1200ms. Add discreet CSS for `.hyp-token-copy`. |

### Exact algorithm — normalization (V3-S14, runtime)
```
// color.js
export function rgbToHex(rgb) { … existing impl … }     // now EXPORTED

// Probe is ATTACHED to document.body, hidden — required so CSS var() chains resolve
// (RV11). A detached element computes only against the UA stylesheet and returns '' for
// a var() reference; attached, it inherits the document :root cascade.
const _hexProbe = document.createElement('span');
_hexProbe.style.visibility = 'hidden';
_hexProbe.style.position = 'absolute';
_hexProbe.style.pointerEvents = 'none';
if (document.body) document.body.appendChild(_hexProbe);
else document.addEventListener('DOMContentLoaded', () => { if (!_hexProbe.isConnected && document.body) document.body.appendChild(_hexProbe); });
export function normalizeHex(value) {
  const v = (value || '').trim();
  if (/^#[0-9a-fA-F]{6}$/.test(v)) return v.toLowerCase();
  if (/^#[0-9a-fA-F]{3}$/.test(v)) {                       // #abc → #aabbcc
    return ('#' + v.slice(1).split('').map(c => c + c).join('')).toLowerCase();
  }
  // named / hsl / rgb / var() → resolve through computed style in the document context
  if (!_hexProbe.isConnected && document.body) document.body.appendChild(_hexProbe);
  _hexProbe.style.color = '';
  _hexProbe.style.color = v;
  const resolved = getComputedStyle(_hexProbe).color;     // 'rgb(r, g, b)' or '' if invalid
  return resolved ? rgbToHex(resolved) : v;
}
```
`readPalette()` maps each token to add `hex: normalizeHex(token.value)`. The attached hidden probe is what lets a token value of `var(--brand-color)` resolve to a concrete hex (the document :root cascade is in scope); a detached probe would fall back to the raw `var(...)` string (RV11).

### Clipboard (verified live, diagnosis R6)
`navigator.clipboard.writeText` succeeds on `http://127.0.0.1` (Chrome treats localhost as a secure context). The copy is invoked from a user-gesture button click. No HTTPS needed.

### Edge cases
| Case | Behavior |
|------|----------|
| Token value is `rgb(...)`/named/`hsl(...)` | `normalizeHex` resolves it to `#rrggbb` via computed style. |
| Token value is a CSS `var()` chain (e.g. `var(--brand-color)`) | Resolves to `#rrggbb` BECAUSE the probe is attached to `document.body` (RV11): the document `:root` cascade is in scope, so `getComputedStyle(probe).color` returns the concrete `rgb(...)`. A detached probe would return `''` → fall back to the raw `var(...)` string. |
| Token value is already `#abc`/`#aabbcc` | Normalized to lower-case 6-digit. |
| Token value is an unparseable string | `getComputedStyle().color` returns `''` → fall back to the raw value (button copies the raw string rather than nothing). |
| Clipboard write rejects (rare) | The transient "Copied!" affordance is shown only on resolve; on reject, a console error is logged and the title stays "Copy HEX". |
| Copy button click vs Coloris input | The copy button `type="button"` and the delegated handler match only `.hyp-token-copy`; it does NOT open Coloris (separate element). |

### Acceptance criteria (MEASURED OUTCOMES)
- Each `.hyp-token-row` contains exactly one `.hyp-token-copy` button with a `data-hex` matching `^#[0-9a-f]{6}$`.
- Clicking a copy button writes that exact `#rrggbb` to the clipboard (read back via `navigator.clipboard.readText()` in the test, with clipboard permission granted): readback EQUALS `data-hex`.
- For a token whose `:root` value is a named color (e.g. `red`) or `rgb(...)`, the copied value is the normalized `#rrggbb` (e.g. `#ff0000`), NOT the raw string.
- After click, the button's `title` transiently becomes "Copied!" (or a `.hyp-token-copied` class is present), then reverts.

---

## R7 — Text alignment controls (horizontal + vertical within the element's box)

### Requirement (trace: user-feedback.md R7 + U13/U16/D21)
> "add option to centralize (horizontal or vertical), align left, right, top or bottom (only aligning the text inside its text box …)."

Terminology (state plainly, per diagnosis): **"text box" is not an HTML term.** The target is the SELECTED ELEMENT'S CONTENT BOX (the element currently selected). Horizontal = `text-align`; vertical depends on the element's computed `display` (U13: never silently convert layout).

### Chosen fix (U13/U16/D21 / V3-S15–S19)
A display-branched `align(hypId, axis, value)` command (the diagnosis R7 decision table is NORMATIVE), horizontal always available, vertical disabled+tooltip-hint on plain auto-height blocks, a toolbar group of 6 icon buttons with a capability-reactive disabled state driven by an extended `selection-changed` payload (`alignCaps`), undo capturing prior inline values.

### Decision table (NORMATIVE — reproduced verbatim from diagnosis R7)

| Computed `display` of selected element | Horizontal (left/center/right) | Vertical (top/middle/bottom) |
|----------------------------------------|--------------------------------|------------------------------|
| `block` / `inline-block` / `list-item` (normal flow text) | `text-align: left\|center\|right` | **No reliable vertical alignment** unless the element has a fixed height. If `height`/`min-height` is set: set `display:flex; flex-direction:column; justify-content: flex-start\|center\|flex-end` (converts to flex — see risk) OR leave vertical disabled. Recommend: vertical writes nothing for plain block without a height; surface a hint. |
| `flex` (element IS a flex container) | main-axis vs cross-axis depends on `flex-direction`. For `row`: horizontal = `justify-content`, vertical = `align-items`. For `column`: horizontal = `align-items`, vertical = `justify-content`. | (same — mapped by `flex-direction`) |
| `grid` (element IS a grid container) | horizontal = `justify-items` (or `justify-content` for track alignment) | vertical = `align-items` (or `align-content`) |
| `flex-child` / `grid-child` (element is an ITEM in a flex/grid parent) | Self-alignment: `align-self` (cross axis) + `justify-self` (grid) — aligns the element within its track, not text within it. For text *inside* the child, fall back to the `block` row (`text-align` + height rule). | as above |
| `table-cell` | `text-align` | `vertical-align: top\|middle\|bottom` (this is the one display type where `vertical-align` actually works) |

**Binding resolution of the table's two "OR"/"recommend" branches (V3-S16):**
- Plain `block`/`inline-block`/`list-item` WITHOUT a fixed height → vertical is DISABLED (writes nothing); a tooltip hint explains why (U13: never silently convert to flex).
- Plain block WITH an explicit `height`/`min-height` (computed > 0 and inline-or-stylesheet-set, not auto) → vertical IS enabled and writes `display:flex; flex-direction:column; justify-content: flex-start|center|flex-end`. (This is the one block case where conversion is acceptable because the user already fixed the height, so flow is not destroyed.)
- For `flex-child`/`grid-child`: the align command targets TEXT inside the child, so it uses the `block` row mapping (`text-align` + the height rule for vertical) — NOT `align-self`/`justify-self` (those move the child in its track, which is not "align the text inside its box"). This keeps R7 faithful to "aligning the text inside its text box".

### Capability bridge (V3-S17)
`selection.js` `buildInfo(el)` gains an `alignCaps` field computed by a pure helper `computeAlignCaps(el)` (lives in the align logic module, imported by selection.js — one-way, no cycle):
```
computeAlignCaps(el):
  cs = getComputedStyle(el)
  display = cs.display
  // horizontal always available
  hMap = mapping per table → { left:{prop,value}, center:{…}, right:{…} }
  // vertical availability + mapping
  if display is flex/grid container OR table-cell OR (block-ish AND hasFixedHeight(el)):
     vertical = true; vMap = mapping per table
  else:
     vertical = false; vMap = null
  return { horizontal:true, vertical, hMap, vMap }
hasFixedHeight(el):
  h = el.style.height || el.style.minHeight
  if h && h !== 'auto' && parseFloat(h) > 0: return true
  cs = getComputedStyle(el); return cs.minHeight !== '0px' && cs.minHeight !== 'auto'
```
The shell reads `info.alignCaps` on `selection-changed` to enable/disable the 6 buttons and (optionally) to label them.

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/text-format.js` (or a new `runtime/js/align.js`) | MOD/NEW | `computeAlignCaps(el)→{horizontal,vertical,hMap,vMap}` (pure, reads computed style); `applyAlign(el, axis, value)` (writes the mapped property per table, branching on display; never converts plain auto-height block). Spec choice: add to `text-format.js` to avoid a new module and a new import edge (it already owns inline-format logic). |
| `runtime/js/commands.js` | MOD | Add `align(hypId, axis, value)` factory: capture prior inline values of ALL alignment props it may write — `text-align`, `justify-content`, `align-items`, `justify-items`, `align-content`, `justify-self`, `align-self`, `vertical-align`, `display`, `flex-direction` (the full V3-S15 capture-all set, matching `colorBorder`'s pattern) — for exact undo; `do()` = call `applyAlign`; `undo()` = restore captured inline state. |
| `runtime/js/selection.js` | MOD | `buildInfo(el)` adds `alignCaps: computeAlignCaps(el)` (import `computeAlignCaps` from `./text-format.js`). |
| `runtime/js/runtime-main.js` | MOD | Register `align {axis,value}` (next to `format`): resolve current selection's hypId via `current()`; `historyPush(commands.align(hypId, axis, value))`. |
| `app/index.html` | MOD | New `toolbar-group` after the format group with 6 icon buttons: `#align-left`, `#align-center`, `#align-right`, `#align-top`, `#align-middle`, `#align-bottom`, each `tool-btn` with a tooltip per V3-S18. |
| `app/js/main.js` | MOD | Wire the 6 align buttons (mirror `formatButtons`): each `mousedown` preventDefault + `iframe.contentWindow.focus()` is NOT needed (align does not need editable focus); each `click` sends `align {axis,value}`. On `selection-changed`, set `disabled` on the 6 buttons from `payload.alignCaps` (horizontal always enabled when a selection exists; vertical enabled only when `alignCaps.vertical`); set a `title` hint on disabled vertical buttons ("Vertical alignment needs a fixed-height, flex, grid, or table-cell element"). |

### Exact algorithm — applyAlign (V3-S15, table-normative)
```
applyAlign(el, axis, value):     // axis 'h'|'v'; value left/center/right or top/middle/bottom
  cs = getComputedStyle(el); display = cs.display; fd = cs.flexDirection || 'row'
  if axis === 'h':
    if display is 'flex'/'inline-flex':
      if fd startsWith 'row': el.style.justifyContent = {left:'flex-start',center:'center',right:'flex-end'}[value]
      else:                   el.style.alignItems     = {left:'flex-start',center:'center',right:'flex-end'}[value]
    elif display is 'grid'/'inline-grid':
      el.style.justifyItems = {left:'start',center:'center',right:'end'}[value]
    else:  // block/inline-block/list-item/table-cell/flex-child/grid-child → text-align
      el.style.textAlign = value
  else (axis === 'v'):
    if display is 'flex'/'inline-flex':
      if fd startsWith 'row': el.style.alignItems     = {top:'flex-start',middle:'center',bottom:'flex-end'}[value]
      else:                   el.style.justifyContent = {top:'flex-start',middle:'center',bottom:'flex-end'}[value]
    elif display is 'grid'/'inline-grid':
      el.style.alignItems = {top:'start',middle:'center',bottom:'end'}[value]
    elif display === 'table-cell':
      el.style.verticalAlign = value     // top|middle|bottom
    elif blockish AND hasFixedHeight(el):
      el.style.display = 'flex'; el.style.flexDirection = 'column'
      el.style.justifyContent = {top:'flex-start',middle:'center',bottom:'flex-end'}[value]
    else:
      return   // plain auto-height block → no-op (button is disabled in the shell; runtime no-ops defensively)
```
The command's `undo()` restores every captured inline value (including `display`/`flex-direction` for the converted-block case), so undo perfectly reverses even the flex conversion.

### Edge cases
| Case | Required behavior |
|------|-------------------|
| Plain auto-height block, vertical pressed | Button disabled in the shell (`alignCaps.vertical===false`); if somehow invoked, `applyAlign` no-ops. No layout conversion (U13). |
| Block WITH fixed height, vertical pressed | Converts to `display:flex; flex-direction:column; justify-content:…`; undo restores the prior `display`/`flex-direction`/`justify-content` inline state exactly. |
| Flex row container | Horizontal→`justify-content`, vertical→`align-items`. |
| Flex column container | Horizontal→`align-items`, vertical→`justify-content`. |
| Grid container | Horizontal→`justify-items`, vertical→`align-items`. |
| table-cell | Horizontal→`text-align`, vertical→`vertical-align` (the one display where it works). |
| flex-child/grid-child | Text alignment uses the block mapping (`text-align`; vertical per the height rule) — NOT `align-self`/`justify-self` (which would move the child, not its text). |
| Undo any align | All captured inline alignment props restored; no residue. |
| Selection changes | The 6 buttons re-derive disabled state from the new `alignCaps`. |
| Element has an alignment property set inline with `!important` (e.g. `style="justify-content: flex-end !important"`) | OUT OF SCOPE (documented limitation, no code). `applyAlign` writes via `el.style.<prop> = value` (CSSOM property assignment), which CANNOT override an existing `!important` inline declaration on the same property — the assignment silently has no effect and `getComputedStyle` still reports the `!important` value. v3 does NOT detect or work around this (it would require `setProperty(prop, value, "important")` or stripping the prior `!important`, neither of which is in scope). Real-world fixtures are unlikely to carry `!important` on inline alignment properties. The R7 decision table assumes no `!important` on the targeted properties. |

### Acceptance criteria (MEASURED OUTCOMES)
- **Horizontal on a block:** select a block text element; click `#align-center`; `getComputedStyle(el).textAlign === "center"`; one `align` history entry; undo restores the prior `text-align`.
- **Vertical on a flex-row container:** `#align-middle` sets `getComputedStyle(el).alignItems` to `center` (NOT `text-align`); undo restores.
- **Vertical disabled on plain block:** with a plain auto-height block selected, `#align-top/middle/bottom` are `disabled` in the DOM (`button.disabled === true`) and carry the hint `title`; horizontal buttons are enabled.
- **Vertical on fixed-height block:** with an inline `height` set, `#align-middle` yields `getComputedStyle(el).display === "flex"` and `justifyContent === "center"`; undo restores `display` to its pre-press value.
- **table-cell vertical:** on a `table-cell` element, `#align-bottom` sets `verticalAlign:"bottom"`.
- **Capability payload:** the `selection-changed` event payload contains `alignCaps` with `horizontal:true` and the correct `vertical` boolean for the selected element's display.

---

## R8 — Font-size A+/A− repeatable without re-selection

### Requirement (trace: user-feedback.md R8)
> "the buttons to increase and decrease font size only allow one increase/decrease 'per selection' … it should allow to increase/decrease as many times as user wants, without having to select again."

The README "font-size caret artifact" note is now a REQUIRED FIX, not a documented limitation.

### Chosen fix (D19 / V3-S20–S22)
Snapshot the actual iframe Selection range on the toolbar button's `mousedown` (BEFORE the focus shift), restore it in `apply` when the live selection has collapsed/relocated, with validation that the snapshot still points into the active editable; plus a tracked-span fallback; clear the tracked span on edit commit. Root causes (diagnosis R8): (1) the toolbar `mousedown` focus cycle collapses the iframe Selection to the editable root; (2) `adjustFontSize`/`expandToWord` cannot re-expand a non-text caret, so press 2+ wraps an empty span at the front instead of bumping the existing span.

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/text-format.js` | MOD | Add module state `savedRange` and `currentFontSpan`. Add `snapshotSelection()` (clone the live first range into `savedRange` if it lies inside an active editable). In `adjustFontSize`: at entry, if the live selection is collapsed at the editable root (or `rangeCount===0`) AND `savedRange` is valid (still contained by the active editable), restore `savedRange` before `expandToWord`; track the span it bumps/creates in `currentFontSpan`; if no usable range AND `currentFontSpan` is set, bump `currentFontSpan.style.fontSize` directly. Clear `savedRange`+`currentFontSpan` on edit commit (called from `text-edit.js`). |
| `runtime/js/runtime-main.js` | MOD | Register `format-snapshot` → `textFormat.snapshotSelection()`; returns `{ok:true}`. |
| `runtime/js/text-edit.js` | MOD | In `commit()`, call `textFormat.clearFontState()` (clears `savedRange`+`currentFontSpan`) so a fresh edit starts clean. Import the clear fn from `./text-format.js` (one-way). |
| `app/js/main.js` | MOD | The existing `formatButtons` `mousedown` handler additionally fires `bridge.command("format-snapshot")` BEFORE `iframe.contentWindow.focus()`, for the font-size buttons (firing it for B/I is harmless). |

### Exact algorithm — snapshot + restore (V3-S20–S22)
```
// text-format.js
let savedRange = null;
let currentFontSpan = null;

function activeEditable() {
  const a = document.activeElement;
  return (a && a.getAttribute && a.getAttribute('contenteditable') === 'true') ? a : null;
}

export function snapshotSelection() {           // called via format-snapshot, BEFORE focus shift
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return;
  const r = sel.getRangeAt(0);
  const ed = activeEditable();
  if (ed && ed.contains(r.commonAncestorContainer)) savedRange = r.cloneRange();
}

export function clearFontState() { savedRange = null; currentFontSpan = null; }

// SNAPSHOT-ALWAYS-WINS validity check: the snapshot's endpoints must still be in
// the live DOM AND inside the currently-active editable. NO live-collapse check.
function snapshotIsValid(el) {
  if (!savedRange) return false;
  if (!savedRange.startContainer.isConnected || !savedRange.endContainer.isConnected) return false;
  return el.contains(savedRange.commonAncestorContainer);
}

// inside adjustFontSize(el, delta), BEFORE the existing expandToWord:
const sel = window.getSelection();
// SNAPSHOT-ALWAYS-WINS (V3-S22): if a valid mousedown snapshot exists, restore it
// UNCONDITIONALLY — the live post-toolbar-click selection is focus-shift garbage by
// construction. There is NO `commonAncestorContainer === el` collapse-detection.
if (snapshotIsValid(el)) {
  sel.removeAllRanges();
  sel.addRange(savedRange.cloneRange());      // restore the real word selection
}
// … existing expandToWord + walk-up-to-existing-span logic now finds the span …
// When the walk-up bumps an existing span, set currentFontSpan = that span.
// When it creates a new span, set currentFontSpan = the new span.
// Fallback: if there is STILL no usable range (no valid snapshot AND the live
//   selection has no range / rangeCount === 0) AND currentFontSpan is set and in-DOM:
//   bump currentFontSpan.style.fontSize directly and return.
savedRange = null;   // consume the snapshot; next mousedown re-takes it
```
The existing reselect-the-new-span tail (`sel.selectNodeContents(span)`) stays; combined with restoring `savedRange` on the next press, the SAME span is found and bumped each time. Note the fallback's "no usable range" test is `sel.rangeCount === 0` (a genuine no-range state) — NEVER a `collapsed && commonAncestorContainer === el` check (RV04: that identity check never matches Chromium's post-`focus()` collapse target).

### Edge cases
| Case | Required behavior |
|------|-------------------|
| Press 1 on a word selection | Word selected → span created at the chosen size; `currentFontSpan` = that span; range reselected. |
| Press 2 without re-selecting | `mousedown` snapshot fired again (but the live selection is the reselected span from press 1, still valid) → walk-up finds the span → bumps it +2px. If the focus cycle collapsed it, `savedRange` restoration brings the word range back, walk-up finds the span, bumps it. |
| Press 3+ | Same as press 2 — the single span grows monotonically. |
| Snapshot points outside the active editable (selection moved to another element) | `el.contains(savedRange.commonAncestorContainer)` is false → no restore; falls back to `currentFontSpan` if set, else current behavior. |
| Edit committed, new edit started | `clearFontState()` on commit wipes `savedRange`+`currentFontSpan`; the new edit's first press starts fresh (no stale span reuse). |
| Font-size floor | Existing `Math.max(8, …)` floor preserved (no shrink below 8px). |

### Acceptance criteria (MEASURED OUTCOMES — the load-bearing test)
- **3 presses, one selection, one span:** double-click a word to enter edit and select it; click `#fmt-font-inc` THREE times WITHOUT re-selecting; assert: the edited element contains EXACTLY ONE span with an inline `font-size`; that span's `font-size` increased by +6px total (3 × +2px) from the base; there are ZERO empty sibling spans (no `<span style="font-size:…"></span>` with empty text). MEASURED: span count = 1, font-size delta = +6px, empty-span count = 0.
- **A− symmetry:** the same with `#fmt-font-dec` decreases the single span by 6px total (floored at 8px).
- **N≥2 repeat coverage** is intrinsic to the 3-press case (presses 2 and 3 are the regression that the v2 suite missed).

---

## R9 — Outline panel removed

### Requirement (trace: user-feedback.md R9 + U12)
> "dont understand what it is, wherever I click it shows 'no regions detected'. Its either broken or its useless." → Owner decision U12: **REMOVE entirely**.

### Chosen fix (U12 / V3-S23, V3-S24; C2)
Remove the outline panel end-to-end. Per C2, `regions()`/`sections` has NO consumer other than the outline → strip `regions()` and the `sections` payload too.

### Precise behavior spec — touch-list (diagnosis option C + U12 + V3-S24)
- `app/index.html`: remove the entire `<div class="outline-panel"> … <div class="outline-list" id="outline-list"></div> </div>` block.
- `app/js/main.js`: remove `let outlineRegions = [];`, `let activeOutlineHypId = null;`, the entire `renderOutline(regions)` function, the entire `setActiveOutline(hypId)` function, the `renderOutline(payload && payload.sections ? payload.sections : [])` call inside the `ready` handler, and the `bridge.on("selection-changed", (payload) => { setActiveOutline(…); })` wiring. (Leave the other `selection-changed` consumer in `color-popover.js` untouched — that is a different file and listener.)
- `app/css/shell.css`: remove the `.outline-panel`, `.outline-panel-header h3`, `.outline-list`, `.outline-item`, `.outline-item:hover`, `.outline-item-active`, `.outline-empty` rules.
- `runtime/js/runtime-main.js`: change `emit("ready", { tokens: palette.tokens, sections: regions() })` to `emit("ready", { tokens: palette.tokens })`; remove `regions` from the `import { tag, regions, byId } from "./element-registry.js";` line (→ `import { tag, byId } from "./element-registry.js";`).
- `runtime/js/element-registry.js`: remove the `regions()` export and its private-helper dependencies that become orphans: `countTextDescendants`, `getSignature`, `getRegionLabel`, `isDecorativeForRegions`, and the `SECTIONING_TAGS` constant — each removed ONLY after grep confirms no other consumer in the file. (`isInsideSvg`, `shouldTag`, `isExplicitlyDecorative` stay — they serve `tag()`.) Update the module's doc-comment public-contract list to drop `regions()`.

### `regions()` fate decision (V3-S24, grep-verified)
Grep findings stated in C2: `regions`/`sections` is consumed ONLY by `main.js` `renderOutline(payload.sections)`. With the outline removed, there is no consumer → `regions()` and `sections` are STRIPPED. (Verified: no other `.js` in `app/` or `runtime/` references `regions(` or `payload.sections`.)

### Edge cases
| Case | Required behavior |
|------|-------------------|
| A private helper is shared | If grep shows `getSignature`/`countTextDescendants`/etc. is referenced elsewhere in `element-registry.js`, KEEP it (remove only true orphans). The task file MUST grep before removing each helper and report what it kept. |
| `ready` payload shape change | The shell `ready` handler no longer reads `sections`; the color popover's `ready` handler reads only `tokens` (unchanged). No consumer breaks. |
| Panel layout | With `.outline-panel` gone, the side panel shows the color popover container + the comment panel only; G1's container-survival invariant is unaffected (the popover only ever touches its own `.hyp-color-popover-container`). |

### Acceptance criteria (MEASURED OUTCOMES)
- After load, `document.getElementById("outline-list")` is `null` and no element matches `.outline-panel`.
- Grep of `app/` and `runtime/` PRODUCT files for the EXACT removed identifiers ONLY — `outline-list`, `renderOutline`, `outlineRegions`, `setActiveOutline`, any CSS rule whose SELECTOR matches `^\.outline-`, `regions(`, and `sections` (payload key) — yields zero hits. The BARE substring `outline` is NEVER a failure condition: the CSS `outline:` PROPERTY (e.g. `outline: 2px solid #fbbf24;` in a comment-highlight rule) is explicitly allowed and stays (RV03).
- The runtime `ready` event payload has `tokens` and NO `sections` key.
- The side panel still renders the color popover and the comment panel; opening a second document does not wipe them (G1 invariant holds without the outline).
- Zero console errors after load and after a selection change (the removed `setActiveOutline` wiring cannot throw).

---

## EXIT — Kimi-evidenced clean run + full green suite

### Requirement (trace: changelog Session-2 scorecard EXIT)
A clean, error-free server run on the sample plus the full automated suite green, INCLUDING the new real-input tests; the R1 OS-z-order ctypes test runs on this machine (interactive desktop present).

### Spec (V3-S25)
- The full suite = v2's 67 tests, MINUS none-by-deletion (v2 has no dedicated outline test; the only outline references are inside `test_g1_panel_survival.py`, which is UPDATED not deleted — see test-plan §"Suite delta"), PLUS all new/changed v3 tests (R1 ctypes z-order + seam regression, R2 hittability + resize-outcome, R3 delete/undo/thread/guards, R4 removal, R5 tooltip, R6 copy-hex, R7 align matrix + caps, R8 three-press span, R9 removal), AND the rewritten `test_f2_select_guides.py` (real-input, no skip-as-green, replacing synthetic clicks).
- Clean server run: `GET /app/` 200; runtime served; opening the sample produces ZERO editor-origin console errors (the deck's own `assets/*` 404s are allowed).
- The EXIT smoke (`test_exit_smoke.py`) is updated to exercise a real resize (R2-fixed), a real delete (R3), a real 3-press font-size (R8), and to assert the absence of the outline (R9) and `#color-btn` (R4).

### Acceptance criteria (MEASURED OUTCOMES)
- `python -m unittest discover -s tests -p "test_*.py" -v` → all tests pass, ZERO skips except the documented headless-CI skip on the R1 ctypes test (which, on this interactive machine, does NOT skip — it runs and passes).
- The R2, R3, R8 outcome tests (geometry deltas / DOM mutation / span count) pass — proving the features work under REAL input, not seams.
- The R1 ctypes z-order test passes against the REAL dialog endpoint on this machine.
- Clean server run confirmed (`/app/` 200, zero editor console errors on the sample).

---

## Cross-feature module map delta (03-module-map.md additions for docs-sync)

| Module | Status | One-line purpose |
|--------|--------|------------------|
| `runtime/js/commands.js` | MOD | + `deleteElement(hypId)` (full-undo delete, mirrors `reorder.place()`); + `align(hypId,axis,value)` (capture-all undo, display-branched). |
| `runtime/js/interaction.js` | MOD | + injects a `hyp-`scoped `<style>` re-enabling `pointer-events:auto` on Moveable controls under the wrapper (R2 fix); existing onDragEnd hit-test toggle unchanged. |
| `runtime/js/text-format.js` | MOD | + `snapshotSelection`/`clearFontState`/`currentFontSpan` (R8 range-survival + tracked-span fallback); + `computeAlignCaps`/`applyAlign` (R7 capability + apply). |
| `runtime/js/selection.js` | MOD | + `alignCaps` in `buildInfo` payload (R7 capability bridge). |
| `runtime/js/color.js` | MOD | + `rgbToHex` EXPORTED; + `normalizeHex`; + `token.hex` in `readPalette` payload (R6). |
| `runtime/js/element-registry.js` | MOD | − `regions()` export + its orphan helpers (R9 removal). |
| `runtime/js/runtime-main.js` | MOD | + `delete-element`, `align`, `format-snapshot` registrations; − `regions`/`sections` from the `ready` emit (R9). |
| `runtime/js/comments.js` | (unchanged) | `reanchorAfterMove`/`threads()` already support R3's thread fate — NO edit. |
| `server/api.py` | MOD | + hidden `TopMost` owner Form in `_OPEN_PS`/`_SAVE_PS` (R1); − `ShowHelp` hack. |
| `app/index.html` | MOD | + `#delete-btn`, + 6 align buttons; − `#color-btn` + its group; − `.outline-panel` block. |
| `app/js/main.js` | MOD | + delete + align wiring + `format-snapshot` mousedown; − `#color-btn` handler; − outline functions/wiring. |
| `app/js/shell/color-popover.js` | MOD | + Palette-Tokens ⓘ tooltip (R5); + per-row copy-HEX button + handler + CSS (R6). |
| `app/css/shell.css` | MOD | − `.outline-*` rules (R9); (+ optional align-button styling if needed). |

---

## Global non-goals (v3 scope fence)
- No new vendored libraries (A9/A10); Playwright + stdlib ctypes remain the only dev/test surface (ctypes is stdlib — not a dependency).
- No re-architecture of the bridge, history, element-registry (beyond the `regions()` removal), selection (beyond the `alignCaps` field), or interaction (beyond the one injected style).
- No Delete/Backspace keyboard path for R3 (U14).
- No silent layout conversion for vertical alignment on plain auto-height blocks (U13).
- No fix to Moveable's grid explicit-placement reorder limitation (carried v2 limitation).
- No support for browsers other than Chrome on Windows 11.
- No change to the v1/v2 serializer strip semantics; the document's own scripts/styles/handlers/SVG remain untouched (A8/A11).
