# Hypresent v2 — Feature Specification

Authoritative, executor-ready specification for the v2 improvement cycle (features F1–F5 + blockers G1–G2). Grounded in `changelog.md` (D1–D10, U1–U10), `docs/decision-log.md` (D1–D6, A1–A12), `recon.md`, and `research-01..04`. This document extends the v1 contracts in `docs/spec/01-architecture.md`, `02-html-convention.md`, `03-module-map.md`, `05-verification-plan.md`. It NEVER supersedes a v1 locked decision except where session decision D6 supersedes the LETTER of v1-D2 (recorded as S-row S1 and a decision-log append in V2-T13).

All injected classes/ids stay `hyp-`prefixed; all injected attributes stay `data-hyp-*` (A12). The app runtime stays dependency-free (A9/A10). The document's own scripts/styles/handlers are never sanitized away (A8/A11).

---

## 0. CRITICAL: Input-document contradiction (G1/G2 already fixed)

**Flagged loudly.** The scope prompt and `changelog.md` Exit Scorecard list G1 (B-PANEL) and G2 (B-SERIALIZE) as OPEN (☐). `recon.md` §7/§9 describes them as open bugs. **However, `docs/build-log.md` §"Browser checkpoint CP2 — re-run + residual fixes (GREEN)" (lines 264–271) records that Kimi already fixed BOTH during the v1 CP2 re-verify, and the current source confirms the fixes are present:**

| Blocker | Claimed state (scorecard/recon) | Actual current source state | Evidence |
|---------|--------------------------------|-----------------------------|----------|
| G1 B-PANEL | `color-popover.js` wipes `.shell-panel` innerHTML | FIXED — renders into dedicated `.hyp-color-popover-container` child via `insertBefore` | `app/js/shell/color-popover.js` (container-creation block ~lines 21–26; locate by the comment `// Dedicated child container …` + the `insertBefore` line) |
| G2 B-SERIALIZE | island-count hardcoded → save aborts with comments | FIXED — `islandCount = countAllNodes(island)` | `runtime/js/serializer.js` line 234 |

**Resolution (decision S0):** v2 does NOT re-implement G1/G2. Re-fixing already-correct code violates surgical-change discipline (rbtv-reasoning Execution Discipline) and risks regression. Instead, v2 treats G1/G2 as **verification-and-hardening** tasks: (a) lock the fixes with automated regression tests (unit for G2 serializer math, Playwright for G1 panel survival), so they can never silently regress as new panel UI (F4 Border row, F5 composer) and new serializer output (F5 agent block) are added; (b) apply the small residual hardening each blocker still needs once F4/F5 expand the panel and the serializer. See §8 (G1) and §9 (G2) for the precise residual scope. The recon and scorecard are stale on these two rows; this spec is authoritative.

---

## Spec-level decisions (decisions made beyond the registered D/U/A set)

These resolve every ambiguity the scope prompt delegated. Kimi treats each as binding.

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| S0 | G1/G2 are verification + residual-hardening tasks, not re-fixes; fixes already exist in source | Re-fixing correct code is a regression risk and violates surgical-change discipline; lock with tests instead (§0). |
| S1 | All editor move writes use the CSS individual `translate` property (`el.style.translate='Xpx Ypx'`), never `transform` | D6; composes independently with document-owned `transform:rotate/scale`, eliminating silent transform loss (recon Risk 3). |
| S2 | `set-tool` bridge command is RETAINED for test/compat but is NO LONGER the activation path; selection auto-mounts one combined Moveable | U1 modeless model; retiring the command would break the v1 round-trip test harness and the `set-tool` registration in `runtime-main.js` for no benefit. |
| S3 | Selection auto-mounts ONE Moveable with both `draggable:true` and `resizable:true` in a single new module `interaction.js`; `resize.js` and `move.js` are RETIRED (deleted) and their command/geometry logic folded into `interaction.js` | U1 requires a single combined instance; keeping two modules that each create a separate Moveable on the same target would race for pointer capture (research-03 §4). One module = one Moveable = no race. |
| S4 | The 150 ms `setInterval` selection polling in `resize.js`/`move.js` is replaced by event-driven re-target: `selection.js` owns an `onSelectionChange` observer registry; `runtime-main.js` `boot()` wires it (post-import) to re-point the single Moveable's `target` + `elementGuidelines` + `updateRect()`. `interaction.js` does NOT import `selection.js` (R09 — avoids the import cycle) | research-02 §5 confirms direct property assignment + `updateRect()` is the supported re-target path; polling is wasteful and laggy; runtime-main wiring breaks the cycle. |
| S5 | Guideline candidate set = same-parent `[data-hyp-id]` siblings ∪ the parent container element ∪ the nearest `section`/`.slide`/`[data-hyp-region]`/`body` ancestor (the "slide root"); deduplicated; capped at 30 candidates (nearest-by-center-distance kept if over cap) | research-02 §3 recipe + Google-Slides parity (sibling + container + slide edges); cap bounds `getBoundingClientRect` cost on dense slides (research-02 §6d). |
| S6 | `elementSnapDirections` AND `snapDirections` both set `{left,top,right,bottom,center,middle}` all `true`; `snapThreshold:5`, `snapGap:true`, `maxSnapElementGuidelineDistance:600`, `isDisplaySnapDigit:false`, `snapRenderThreshold:1` | research-02 §3 verbatim recipe for Slides-style center+edge alignment on Moveable 0.53.0. |
| S7 | Drop hit-test runs on `dragEnd` only (not during drag); pointer position is read from the LAST `onDrag` event's `clientX/clientY` (Moveable's `inputEvent`), cached in `interaction.js` | research-03 §2 Option B (on-drop only, no sibling shift during drag); Moveable does not pass clientX on `dragEnd`, so the last drag event's pointer is cached. |
| S8 | Re-parent drop CONTAINER = the hovered `[data-hyp-id]` element's PARENT, provided the parent is not a leaf/text element and is not the dragged element's own parent (that is the reorder case); insertion index from the midpoint rule against the hovered element | U4 + research-03 cross-parent extension; "parent of hovered" matches Slides' "drop next to the thing under the cursor" mental model. |
| S9 | Leaf/text test: an element is a NON-container (never inserted into) if it has zero element children AND `el.textContent.trim().length>0`, OR its tag is in the inline/void/replaced exclusion set (same set `selection.js` `isTextEditable` excludes), OR it carries `data-hyp-text="true"` | Prevents inserting a block INTO a `<p>`/`<span>`/`<img>`; reuses the existing exclusion taxonomy for consistency. |
| S10 | Drop classification precedence on `dragEnd`: (1) pointer over a same-parent sibling → reorder; (2) else pointer over a different-parent `[data-hyp-id]` whose parent qualifies as a container (S8/S9) → re-parent; (3) else → keep translate (out-of-flow) | U2/U3/U4 hybrid; explicit precedence removes ambiguity when the pointer is over a nested element belonging to another parent. |
| S11 | One history command per drop, label `"reorder"` or `"reparent"`, capturing `{oldParentHypId, oldPrevSiblingHypId, oldNextSiblingHypId, oldTranslate}`; `do()`/`undo()` re-resolve elements by hyp-id at run time (never cache node refs) | research-03 §3 undo contract + A12 "never cache a node reference across a tool switch"; hyp-id resolution survives intervening DOM mutation. |
| S12 | After ANY DOM move (reorder/reparent), `interaction.js` calls the `comments.js` export `reanchorAfterMove()` (owned/defined by V2-T9 — R11) which, for EVERY thread, re-resolves its element via the multi-signal `matchAnchor` and, if resolved, REGENERATES the full key (`path`+`siblingIndex`) from the element's CURRENT position via `buildAnchorKey`; threads that do not resolve keep their old anchor and show as unanchored (never deleted — R14), then `writeIsland()` + `reanchorAll()` | F3 mandate: the 5-field key's `path`/`siblingIndex` go stale after a move — for the moved element AND for unmoved siblings whose index drifts; regenerating from the resolved element for ALL threads keeps the island self-consistent for the next save/open. |
| S13 | Border row writes `border-color` (all four sides) via the existing `apply-color {scope:'element', prop:'border-color'}` path; the auto-1px rule (U6) is applied INSIDE `color.js` `applyElement` when `prop==='border-color'` and computed border is none/0 on all sides | U6; centralizing the auto-1px in `color.js` keeps the popover dumb and makes undo capture (S14) cover both the color and the synthesized `border` shorthand atomically. |
| S14 | Border undo captures the prior inline values of `border-color` AND `border-width` AND `border-style` (and the `border` shorthand if present) as a single command via a new `commands.js` factory `colorBorder(hypId, value)` | U6 auto-1px sets width+style, so undo must restore all border-related inline state, not just color. |
| S15 | Border row "mixed-side" display: on selection, `color.js` reports per-side border colors; if the four sides differ, the Border input shows placeholder `"mixed"` and is empty (no swatch); applying a value still writes all four sides uniformly | F4 interaction with existing per-side `border-*-color` inline sites (discoverInlineSites detects them); "mixed" is the Google-Docs convention and avoids lying about a single value. |
| S16 | Comment composer is a new shell module `comment-composer.js` rendering an absolutely-positioned popover in the PARENT document, anchored at the `rect` from `comment-requested`/`comment-anchor-clicked`; textarea + "For agents" checkbox + Save/Cancel | U7; parent-rendered popover stays out of the serialized document (A2) and reuses the existing rect-bearing events. |
| S17 | Composer keys: `Esc` = Cancel (no save); `Ctrl+Enter` OR `Cmd+Enter` = Save; plain `Enter` inserts a newline in the textarea | U7 "Enter+mod submit"; plain Enter as newline matches multi-line comment expectation. |
| S18 | `prompt()` is removed from the add-comment AND reply paths in `main.js`; reply reuses the same `comment-composer.js` popover in "reply mode" | U7 replaces `prompt()` composer; replies were also `prompt()`-based (`main.js` line 131) and must move to the popover for consistency. |
| S19 | Agent block format = research-04 Option A (delimited HTML comment), first child of `<head>`; entry escaping replaces any literal `-->` in instruction/reply bodies with `--&gt;` | D7 + U8; `--&gt;` is reversible-looking and HTML-comment-safe; chosen over `-- >` (which alters spacing) per "state exact escaping". |
| S20 | Agent block includes ALL replies of each emitted (unresolved, agent-tagged) thread as `reply:` continuation lines under its entry; entire resolved threads are excluded. Replies have NO individual `resolved` flag — "unresolved replies" means "replies under unresolved threads", and all of them are emitted in full | research-04 recommendation; replies carry instruction refinements an agent needs. |
| S21 | Side-panel per-thread "For agents" toggle is a checkbox in each rendered thread card (`main.js` `createThreadEl`); toggling sends a new bridge command `tag-agent {commentId, agentInstruction}` → `comments.js` `setAgentInstruction()` | U7 panel toggle; a dedicated command keeps the island the single source of truth (D7) and makes the toggle undoable. |
| S22 | The combined Moveable suspends (hides handles) during text edit: `interaction.js` listens for a new runtime-internal signal from `text-edit.js` (`enter`/`exit`) and calls `moveable.draggable=false; moveable.resizable=false` on enter, restores on exit | U1 "double-click enters text edit (suspend handles while editing)"; without suspension the drag handles intercept caret placement. |
| S23 | Server dialog injection seam: `api.py` exposes module-level `_run_ps_dialog_default` and the two handlers read it through an indirection (`_dialog_launcher`/`_launch_dialog`) that tests can monkeypatch; default launcher is the PowerShell subprocess | F1 testability mandate; a settable module attribute is the simplest stdlib-only injection seam (no DI framework). |
| S23a | Default launcher tries `pwsh` then falls back to `powershell.exe` on `FileNotFoundError`, both with `-STA -NoProfile -NonInteractive`; empty stdout = cancel | R02: `pwsh` is optional on Windows 11; hardcoding it 500s on inbox-only machines. See F1 "PowerShell launcher — exact subprocess contract". |
| S24 | "Save" (silent) when no file is open falls back to the Save As native dialog flow; the server tracks the open path in a new module-level `_open_path` set by `handle_open`/`handle_dialog_open` | U5; the server already knows the open path (it sets `_doc_root`), so persisting the file path there (not the directory) is the minimal change. |
| S25 | Toolbar loses BOTH `#open-path-input` and `#save-as-path-input`; Open/`Save`/`Save As` become three buttons; `Save` button is NEW | F1 "toolbar loses both path text inputs" + U5 three-button model. |
| S26 | `stripClone` sweeps any pre-existing `<head>` comment node whose value contains the agent-block sentinel (counted in `removedNodeCount`) BEFORE a fresh block is inserted | G2/F5: prevents a DOUBLE agent block when re-saving a file that already carries one; keeps the node-count guard exact. Landed in V2-T2 Phase A2. |
| S27 | Move/reorder drop is a no-op below a 3px cumulative Euclidean drag distance (accumulated in `onDrag`); the FLIP set excludes the dragged element; the selection→interaction observer is wired in `runtime-main.boot()` (interaction.js does not import selection.js) | R05 (spurious-reorder-on-click), R10 (FLIP flash), R09 (import cycle). See F2/F3. |

---

## F1 — Native open/save dialogs

### User-visible behavior
- Toolbar shows three buttons: **Open…**, **Save**, **Save As…**. Both path text inputs are gone (S25).
- **Open…** → native Windows file-open dialog (filter `HTML files (*.html;*.htm)|*.html;*.htm|All files (*.*)|*.*`). Pick a file → it loads exactly as today. Cancel → nothing happens (no error, no state change).
- **Save** → silently overwrites the currently-open file (no dialog). If no file is open, falls back to the **Save As** flow (S24).
- **Save As…** → native Windows save dialog. Default filename = current document name; default directory = current document directory. Cancel → no-op. Pick/confirm → writes there and that path becomes the new "currently-open file" for subsequent **Save**.

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `server/api.py` | MOD | Add `handle_dialog_open()→(status,resp)`, `handle_dialog_save_as(payload)→(status,resp)`, `handle_save(payload)→(status,resp)`. Add module-level `_open_path={"path":None}`, `set_open_path(p)`, `get_open_path()`. Add `_dialog_launcher` indirection + `_run_ps_dialog(script)` default (S23). `handle_open` and `handle_dialog_open` call `set_open_path`. Reuse `handle_open`/`handle_save_as` internals (no duplication). |
| `server/server.py` | MOD | Route `POST /api/dialog-open` → `api.handle_dialog_open()`; `POST /api/dialog-save-as` → `api.handle_dialog_save_as(payload)`; `POST /api/save` → `api.handle_save(payload)`. |
| `app/js/api-client.js` | MOD | Add `dialogOpen()→{html,dir,name,cancelled?}`, `dialogSaveAs(html)→{ok,path,cancelled?}`, `save(html)→{ok,path,cancelled?}`. |
| `app/js/shell/file-controls.js` | MOD | `openViaDialog(iframe)`: call `apiClient.dialogOpen()`; if `cancelled` return null; else run the existing iframe-load+runtime-inject flow with the returned `name`. Export `openFile` unchanged (reused by `openViaDialog`). |
| `app/js/main.js` | MOD | Rewire `#open-btn`→`openViaDialog`; NEW `#save-btn`→serialize+`apiClient.save`; rewire `#save-as-btn`→serialize+`apiClient.dialogSaveAs`. Remove all `#open-path-input`/`#save-as-path-input`/`deriveSaveDefault` usage. |
| `app/index.html` | MOD | Remove both `<input>`s; add `<button id="save-btn">Save</button>` between Open and Save As. |

### Exact algorithm — dialog endpoint (server)
The PowerShell scripts are research-01 §"Implementation Sketch for B2" verbatim, with the filter widened to `*.html;*.htm` (scope mandate) and the threading lock; the launcher itself follows the `pwsh`→`powershell.exe` fallback in S23a. `handle_dialog_open` returns `{"cancelled":true}` (200) on empty stdout, else delegates to `handle_open({"path":<path>})`. `handle_dialog_save_as` returns `{"cancelled":true}` on cancel, else sets `payload["path"]` and delegates to `handle_save_as`. `handle_save` reads `get_open_path()`; if `None` → returns `{"no_open_file":true}` (200) so the client falls back to the dialog; else delegates to `handle_save_as({"path":open_path,"html":payload["html"]})`.

### Injection seam (S23)
```python
# api.py
_dialog_launcher = None  # tests set this to a fake returning a path or None
def set_dialog_launcher(fn):
    global _dialog_launcher
    _dialog_launcher = fn
def _launch_dialog(kind):  # kind ∈ {"open","save"}
    fn = _dialog_launcher if _dialog_launcher is not None else _run_ps_dialog_default
    return fn(kind)
```
`_run_ps_dialog_default(kind)` runs the `-STA` PowerShell subprocess under `_DIALOG_LOCK` (research-01 pattern) and returns the chosen path or `None`. Tests call `set_dialog_launcher(lambda kind: "C:/tmp/x.html")` (or `lambda kind: None` for cancel).

### PowerShell launcher — exact subprocess contract (S23a, R02)
`pwsh` (PowerShell 7) is an OPTIONAL Windows install; the inbox shell is `powershell.exe` (Windows PowerShell 5.1). Hardcoding `pwsh` would permanently 500 every dialog on a machine that has only the inbox shell. The default launcher therefore tries `pwsh` FIRST, and on `FileNotFoundError` retries with `powershell.exe`, both invoked with the IDENTICAL flag list `["-STA", "-NoProfile", "-NonInteractive", "-Command", <script>]`:
```python
def _ps_args(exe, script):
    return [exe, "-STA", "-NoProfile", "-NonInteractive", "-Command", script]

def _run_ps_dialog_default(kind):
    script = _OPEN_PS if kind == "open" else _SAVE_PS
    candidates = ["pwsh", "powershell.exe"] if sys.platform == "win32" else ["pwsh"]
    last_exc = None
    with _DIALOG_LOCK:                       # serialize overlapping dialogs
        for exe in candidates:
            try:
                r = subprocess.run(_ps_args(exe, script),
                                   capture_output=True, text=True,
                                   encoding="utf-8", timeout=300)
            except FileNotFoundError as exc:
                last_exc = exc
                continue                      # this flavor absent → next candidate
            path = (r.stdout or "").strip()
            return path if path else None     # empty stdout ⇒ user cancelled
    raise last_exc if last_exc is not None else FileNotFoundError("No PowerShell executable found")
```
**Cancel/stdout contract (identical in V2-T3 and the unit-test design):** empty stripped stdout ⇒ user cancelled ⇒ return `None`; non-empty stdout ⇒ the chosen absolute path. If NEITHER `pwsh` nor `powershell.exe` exists, the function raises `FileNotFoundError`, caught by the handler → `(500, {"error": ...})`. Tests always inject a fake launcher via `set_dialog_launcher`, so suites never spawn PowerShell.

### Edge cases

| Case | Behavior |
|------|----------|
| Cancel open | `{"cancelled":true}`; client returns null; iframe unchanged; no `ensureBridge`. |
| Cancel save-as | `{"cancelled":true}`; dirty state unchanged; status shows nothing. |
| Save with no file open | `handle_save` returns `{"no_open_file":true}`; client invokes the Save As dialog flow. |
| Dialog appears behind Chrome | `$d.ShowHelp=$true` in the script forces foreground (research-01 §B2). |
| Non-ASCII path | `[Console]::OutputEncoding=UTF8` in script; `subprocess.run(...,encoding='utf-8')`. |
| Two dialog requests overlap | `_DIALOG_LOCK` serializes; second blocks until first returns. |
| Only inbox PowerShell present (no PowerShell 7) | `_run_ps_dialog_default` tries `pwsh`, catches `FileNotFoundError`, retries `powershell.exe` (S23a). Dialogs work on a stock Windows 11 Home machine. |
| Neither `pwsh` nor `powershell.exe` present / non-Windows | The launcher exhausts its candidates and raises `FileNotFoundError` → caught → `(500,{"error":...})`; tests always inject a fake so suites never spawn PowerShell. |
| `.htm` file opened | Filter accepts `.htm`; `handle_open` reads it identically (no extension logic in read path). |

### Non-goals
- No File System Access API (research-01 ruled out). No recent-files list. No multi-select open. No auto-save. No directory picker.

---

## F2 — Modeless interaction + alignment guides

### User-visible behavior
- Single-click an element → it is selected and a combined Moveable mounts immediately, showing BOTH drag (body) and resize (edge/corner) handles. No tool switch.
- Drag the body → move (translate); drag a handle → resize. While dragging or resizing, Google-Slides-style alignment guides (edge + center, both axes) appear and the element snaps within ~5px.
- Double-click → enter text edit; handles suspend until edit ends.
- `Esc` or click on empty space → deselect, handles unmount.

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/interaction.js` | NEW | `mount(hypId)`, `unmount()`, `suspend()`, `resume()`, `isActive()→bool`, `remount(hypId)`. Owns the single combined Moveable, snapping config, drag/resize commit, drop hit-test (F3), guideline candidate selection. Does NOT import `selection.js` (R09); `runtime-main.js` wires `onSelectionChange`→mount/remount/unmount. `text-edit.js` calls `suspend()`/`resume()` (S22). |
| `runtime/js/resize.js` | DELETE | Logic folded into `interaction.js` (S3); resize sizing helpers (`captureSizingState`, `applyVisualResize`) move verbatim into `interaction.js`. |
| `runtime/js/move.js` | DELETE | Logic folded into `interaction.js` (S3); translate parse/accumulate moves into `interaction.js`, rewritten to use the CSS `translate` property (S1). |
| `runtime/js/runtime-main.js` | MOD | Replace `resize`/`move` imports with `interaction` (`mount/unmount/remount/isActive`); import `onSelectionChange` from `selection.js` and wire it in `boot()` to mount/remount/unmount (R09); keep `set-tool` as a compat shim calling `mount/unmount` (S2); keep `move-commit`/`resize-commit` for the test harness. `select`/`clear-selection` registrations unchanged (the observer handles mount/unmount). |
| `runtime/js/text-edit.js` | MOD | On `enterEdit`, call `interaction.suspend()`; on `commit`, call `interaction.resume()`. Imports `interaction` (one-way; interaction does NOT import text-edit → no cycle, R09). |
| `runtime/js/selection.js` | MOD | Add an `onSelectionChange` observer registry (R09) invoked after each `selection-changed` emit in `select`/`clear`; imports ONLY `element-registry.js` + `bridge-iframe.js` (no import of interaction/text-edit). Existing click-to-select/click-empty-to-clear logic unchanged. |

### Exact algorithm — combined Moveable (S3, S6)
```js
// interaction.js (pseudocode of the constructor)
moveable = new window.Moveable(wrapper, {
  target: el,
  draggable: true,
  resizable: true,
  edge: true,
  throttleResize: 1,
  throttleDrag: 0,
  snappable: true,
  snapContainer: wrapper,
  snapThreshold: 5,
  snapGap: true,
  maxSnapElementGuidelineDistance: 600,
  snapRenderThreshold: 1,
  isDisplaySnapDigit: false,
  snapDirections: { left:true, top:true, right:true, bottom:true, center:true, middle:true },
  elementSnapDirections: { left:true, top:true, right:true, bottom:true, center:true, middle:true },
  elementGuidelines: getElementGuidelines(el),
});
```
Wrapper = single `div#hyp-interaction-wrapper` (fixed, full-viewport, `pointer-events:none`, z-index 999998) — the same wrapper pattern the old `resize.js` used, renamed. Guidelines auto-render inside it (research-02 §4).

### Exact algorithm — guideline candidate selection (S5)
```
getElementGuidelines(targetEl):
  parent = targetEl.parentElement
  siblings = [c for c in parent.children if c !== targetEl and c.dataset.hypId]
  slideRoot = targetEl.closest('section, .slide, [data-hyp-region], body') or document.body
  candidates = unique( siblings + [parent] + [slideRoot] )
  candidates = candidates.filter(c => c !== targetEl and c is in document.body and c !== document.body ? true : true)
  // never use the dragged element itself; body IS allowed (it provides slide edges)
  if candidates.length > 30:
    tc = targetEl.getBoundingClientRect(); center = (tc.left+tc.right)/2, (tc.top+tc.bottom)/2
    candidates.sort(by ascending distance from each candidate's center to target center)
    candidates = candidates.slice(0, 30)
  return candidates
```
Reassigned on EVERY activation/selection change: `interaction.js`'s `selection-changed` handler sets `moveable.target = newEl; moveable.elementGuidelines = getElementGuidelines(newEl); moveable.updateRect();` (S4, research-02 §5).

### Event-driven re-target (S4) — observer registry in selection.js, wired by runtime-main (R09)
No `setInterval`. `selection.js` OWNS a module-internal observer registry and exports `onSelectionChange(cb)`; `select()`/`clear()` invoke registered callbacks AFTER emitting `selection-changed`. `selection.js` imports NOTHING from `interaction.js` or `text-edit.js`. `interaction.js` does NOT import `selection.js` or self-register. Instead, `runtime-main.js` — which already imports both modules — registers the bridge in `boot()` AFTER all modules are fully evaluated:
```js
onSelectionChange((info) => {
  if (info && info.hypId) {
    if (interactionIsActive()) interactionRemount(info.hypId);
    else interactionMount(info.hypId);
  } else {
    interactionUnmount();
  }
});
```
This keeps the iframe-internal re-target synchronous, avoids a parent round-trip, AND eliminates the former ES-module import cycle (`runtime-main → text-edit → interaction → selection ← runtime-main`) that could leave `onSelectionChange` undefined at registration time. Final import graph is in V2-T8. (Wired in V2-T8 PART F; observer registry added to selection.js in V2-T8 PART D.)

### Edge cases

| Case | Behavior |
|------|----------|
| Select element with no siblings | `getElementGuidelines` returns `[parent, slideRoot]`; center/edge guides still work against the container. |
| Select then double-click same element | `mount` then `suspend` (handles hidden, edit active); on commit `resume`. |
| Pre-transformed element (`transform:rotate`) | Guidelines may drift slightly (research-02 §6b); S1 ensures move writes `translate` so rotate is preserved; accept minor guide drift (stated non-goal of pixel-perfect guides on rotated elements). |
| Element removed by document JS while selected | `byId` returns null on next interaction; `interaction.unmount()` called defensively; no crash. |
| Click empty space | `selection.clear()` → observer fires → `interaction.unmount()`. |

### Non-goals
- No multi-select. No rotation handle. No grid snapping (`snapGridWidth/Height`). No keyboard nudge. Pixel-perfect guides on rotated/scaled elements are out of scope.

---

## F3 — Move / reorder / re-parent

### User-visible behavior
- Drag an element's body. During drag it follows the pointer (translate); guides show (F2).
- Drop over a same-parent sibling → the element reorders into flow at that position; displaced siblings animate (FLIP ~180ms); translate clears.
- Drop over an element belonging to a different (container) parent → the element re-parents into that container at the computed index; translate clears.
- Drop in empty space → translate is kept; the out-of-flow badge stays (existing behavior).
- One Ctrl+Z undoes the entire drop (reorder/reparent/translate) exactly.

### Module-level design
All logic lives in `runtime/js/interaction.js` (F2's module) plus a small pure helper module for hit-testing so it is unit-testable in isolation.

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `runtime/js/reorder.js` | NEW | Pure, DOM-reading helpers (no history, no Moveable): `classifyDrop(dragEl, clientX, clientY) → {kind:'reorder'|'reparent'|'none', target, container, insertBefore}`; `isContainer(el)→bool` (S9); `dominantAxis(containerEl)→'x'|'y'` (research-03). Importable by tests. |
| `runtime/js/interaction.js` | MOD | `onDrag` caches last `{clientX,clientY}` (S7); writes `el.style.translate` (S1). `onDragEnd` calls `reorder.classifyDrop`, then performs reorder/reparent/keep via `commitDrop()` which builds the history command (S11), runs FLIP, and calls `comments.reanchorAfterMove()` (S12). |
| `runtime/js/commands.js` | MOD | Add `reorder(hypId, oldParentHypId, oldPrevHypId, oldNextHypId, newParentHypId, newNextHypId, oldTranslate)` factory → `{do,undo,label}` that re-resolves by hyp-id and clears/sets `translate` (S11). Move factory rewritten to use `translate` not `transform` (S1). |
| `runtime/js/comments.js` | MOD (in V2-T9) | Add `reanchorAfterMove()` (S12): for EVERY thread, `el=matchAnchor(t.anchor)` (multi-signal); if `el`, `t.anchor=buildAnchorKey(el)` (regenerates `path`+`siblingIndex` from current position — covers unmoved-sibling index drift, R14); unresolved threads keep their anchor and show unanchored (never deleted); then `writeIsland()` + `reanchorAll()`. Owned by V2-T9; `interaction.js` only calls it (R11). |

### Exact algorithm — hit-test + classification (S7–S10, research-03 §3)
```
dominantAxis(container):
  cs = getComputedStyle(container)
  if cs.display in ('flex','inline-flex') and cs.flexDirection startsWith 'row': return 'x'
  if cs.display in ('flex','inline-flex'): return 'y'                 // column
  if cs.display in ('grid','inline-grid'): return 'y'                 // DOM-order default; see grid limitation
  return 'y'                                                          // block flow

isContainer(el):                                                      // S9
  if el.children.length === 0 and el.textContent.trim().length > 0: return false  // leaf text
  if EXCLUDED/INLINE/VOID set has el.tagName: return false
  if el.getAttribute('data-hyp-text') === 'true': return false
  return true

classifyDrop(dragEl, x, y):
  hovered = elementUnderPointerSkippingHypChrome(x, y)               // see below
  if hovered is null: return {kind:'none'}
  // climb hovered to nearest [data-hyp-id]
  hov = hovered.closest('[data-hyp-id]')
  if hov is null or hov === dragEl: return {kind:'none'}
  // (1) same-parent sibling → reorder
  if hov.parentElement === dragEl.parentElement:
    axis = dominantAxis(dragEl.parentElement)
    r = hov.getBoundingClientRect()
    before = (axis==='x') ? (x < r.left + r.width/2) : (y < r.top + r.height/2)
    return {kind:'reorder', target:hov, container:dragEl.parentElement, insertBefore:before}
  // (2) different parent → reparent if hov.parentElement is a container
  container = hov.parentElement
  if container and container !== dragEl.parentElement and isContainer(container):
    axis = dominantAxis(container)
    r = hov.getBoundingClientRect()
    before = (axis==='x') ? (x < r.left + r.width/2) : (y < r.top + r.height/2)
    return {kind:'reparent', target:hov, container, insertBefore:before}
  // (3) else keep
  return {kind:'none'}

elementUnderPointerSkippingHypChrome(x, y):
  // Moveable wrapper has pointer-events:none, but be defensive:
  for el in document.elementsFromPoint(x, y):
    if el.closest('[id^="hyp-"], [class^="hyp-"], [class*=" hyp-"]'): continue
    return el
  return null
```

### Exact algorithm — commit + FLIP + undo (S11, research-03 §2/§3)
```
onDragEnd(dragEl):                                       // S7 + R05 zero-distance guard
  if dragDist <= DRAG_THRESHOLD (3px):                   // cumulative Euclidean, accumulated in onDrag
    restore dragEl.style.translate to its pre-drag value; return   // no-op: click, not a real drag
  classification = classifyDrop(dragEl, lastPointer.x, lastPointer.y)
  commitDrop(dragEl, classification)

commitDrop(dragEl, classification):
  if classification.kind === 'none':
    // keep translate; emit out-of-flow as today; push a move command (translate before/after)
    pushMoveCommand(...); return

  parent_old = dragEl.parentElement
  oldPrev = dragEl.previousElementSibling?.dataset.hypId ?? null
  oldNext = dragEl.nextElementSibling?.dataset.hypId ?? null
  oldTranslate = dragEl.style.translate || ''

  // FLIP FIRST snapshot — DISPLACED SIBLINGS ONLY; dragEl is EXCLUDED (R10) so it
  // lands instantly (animating it would invert it back to its old spot for ~180ms).
  affected = unique(childrenWithHypId(parent_old) + childrenWithHypId(classification.container)).filter(e => e !== dragEl)
  first = Map(el -> el.getBoundingClientRect())

  // compute new next-sibling hyp-id for undo/redo symmetry
  ref = classification.insertBefore ? classification.target : classification.target.nextElementSibling
  newNext = ref?.dataset.hypId ?? null
  newParent = classification.container

  cmd = commands.reorder(dragEl.dataset.hypId, idOf(parent_old)||registerTempId(parent_old),
                         oldPrev, oldNext, idOf(newParent)||registerTempId(newParent),
                         newNext, oldTranslate)
  history.push(cmd)        // push runs cmd.do() which performs insertBefore + clears translate

  // FLIP PLAY
  requestAnimationFrame(() => for [el, before] of first:
     after = el.getBoundingClientRect(); dx=before.left-after.left; dy=before.top-after.top
     if dx||dy: el.style.transition='none'; el.style.transform=`translate(${dx}px,${dy}px)`
        requestAnimationFrame(() => el.style.transition='transform 180ms ease'; el.style.transform=''))

  comments.reanchorAfterMove()      // S12
  // re-mount Moveable on the moved element at its new flow position
  interaction.remount(dragEl.dataset.hypId)
```
`commands.reorder.do()` resolves `newParent` by hyp-id, resolves `newNext` by hyp-id (or appends if null), `insertBefore`, then `el.style.translate=''`. `undo()` resolves `oldParent`, restores by `oldNext` (or appends), then sets `el.style.translate = oldTranslate` (restores the pre-drop translate, which is `''` in the common case). FLIP uses `transform` (transient, never serialized — cleared synchronously after the transition; it is editor-transient on `[data-hyp-id]` elements which the serializer strips inline styles from? NO — serializer keeps non-hyp inline styles; therefore FLIP transforms MUST be fully cleared before any serialize, which they are by the 180ms transition end + the `''` assignment). Stated limitation: a serialize during the 180ms FLIP window could capture a transient `transform`; mitigated because serialize is user-triggered and the window is sub-200ms (edge-case row below).

### `translate`-property migration (S1) — read/accumulate/undo/serializer
- **Read/accumulate (drag):** `onDragStart` parses `el.style.translate` (format `"Xpx Ypx"` or `"Xpx"` or empty) into `[bx,by]`; `onDrag` writes `el.style.translate = `${bx+dx}px ${by+dy}px``.
- **Out-of-flow flag:** `computeOutOfFlow(el)` returns `true` when parsed translate magnitude ≥0.5px on either axis (same threshold as v1, now reading `translate` not `transform`).
- **Undo:** move command before/after are `translate` strings; `commands.move.do/undo` set/remove the `translate` property (not `transform`).
- **Serializer implication:** the CSS `translate` property is a normal inline style on a non-`hyp` attribute → already preserved by the serializer (it only strips `data-hyp-*` and `hyp-` classes, never `style`). NO serializer change needed for translate. The serializer node-count guard is unaffected (translate is an attribute mutation, not a node add/remove).

### Edge cases

| Case | Behavior |
|------|----------|
| Single click (zero-distance drag) | `dragDist <= 3px` → `onDragEnd` restores the pre-drag translate and returns; NO `classifyDrop`, NO command, NO reorder (R05). Prevents a spurious reorder from `elementsFromPoint` near the iframe corner when `lastPointer` was never updated. |
| Drop on self | `classifyDrop` returns `none` (`hov===dragEl` guard). |
| FLIP after a reorder/reparent | Only DISPLACED SIBLINGS animate; the dragged element is excluded from the FLIP set and lands instantly at its new flow position (R10) — no 180ms flash. |
| Drop in flex gap (between siblings, over none) | `elementsFromPoint` returns the container; `hov.closest('[data-hyp-id]')` may be the container itself → if `hov===container of dragEl`'s parent and not a sibling → falls to reparent check; container is dragEl's own parent → excluded → `none` (keep translate). |
| Grid with explicit `grid-column/row` placement | Reorder mutates DOM order; visual order may not change (research-03 §5). STATED LIMITATION. |
| Drop onto a leaf `<p>` of another parent | `isContainer(<p>)` false → not a target; climbs to `<p>`'s parent only via the hovered-element's parent rule: container=`<p>`'s parent is tested, not `<p>`. Correct. |
| Re-parent into a container that is an ancestor of dragEl | Allowed by DOM (`insertBefore` handles it); element leaves its old position and joins the ancestor's children — valid Slides-like outdent. |
| Serialize during FLIP window (<200ms) | Possible transient `transform` on a sibling. Mitigation: documented limitation; user save during a sub-200ms animation is improbable; FLIP clears `transform` to `''` at transition end. |
| Comment anchor was on the moved element | `reanchorAfterMove` rewrites its anchor from the resolved (moved) element; marker re-renders at new position. |
| element-registry ids after move | `data-hyp-id` is on the element itself and travels with it through `insertBefore`; `idToEl`/`elToId` maps key on the node, unaffected. ids remain stable (F3 mandate). |

### Non-goals
- No live sibling-shift during drag (on-drop only). No cross-document drag. No re-parent into leaf/text/replaced elements. No fixing grid explicit-placement visual reorder.

---

## F4 — Border color

### User-visible behavior
- The per-element color panel gains a third row, **Border**, alongside Text and Background.
- Setting a border color writes `border-color` to all four sides. If the element currently has no visible border (style `none` or width 0 on all sides), the editor also applies `border:1px solid <color>` so the border becomes visible (U6).
- If the element's four sides already have DIFFERENT border colors, the Border input shows `mixed` (placeholder, empty); applying a value sets all four sides uniformly (S15).
- Ctrl+Z restores the prior border-color/width/style inline state exactly (S14).

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `app/js/shell/color-popover.js` | MOD | In `renderElement(info)`, add a third `.hyp-color-row` with `data-prop="border-color"`. On selection, pre-fill its value from `info.borderColor` (or empty + placeholder `mixed` if `info.borderMixed`). |
| `runtime/js/color.js` | MOD | `applyElement(hypId, prop, value)`: when `prop==='border-color'`, route to `colorBorder` (auto-1px logic, S13). Add `readElementBorder(hypId)→{color,mixed}` for the panel to call (via a new `element-color-read` bridge command or piggybacked on `selection-changed`). |
| `runtime/js/commands.js` | MOD | Add `colorBorder(hypId, value)` (S14): captures prior inline `border-color/-width/-style` (+ shorthand) and the four per-side `border-*-color`; `do()` sets `border-color:value` and, if needed, `border:1px solid value`; `undo()` restores all captured values. |
| `runtime/js/runtime-main.js` | MOD | Add `element-color-read {hypId}` command → returns `{color, background, borderColor, borderMixed}` so the popover fills all three rows from one read. |
| `app/js/main.js` | MOD | On `selection-changed`, the color popover already re-renders; ensure the border row is populated (handled inside color-popover.js). |

### Exact algorithm — auto-1px + mixed (S13, S15)
```
// color.js
applyElement(hypId, prop, value):
  if prop === 'border-color':
    historyPush(commands.colorBorder(hypId, value)); return
  historyPush(commands.colorElement(hypId, prop, value))   // existing path for color/background-color

// commands.colorBorder(hypId, value).do():
  cs = getComputedStyle(el)
  sides = ['top','right','bottom','left']
  noneOrZero = sides.every(s =>
     cs.getPropertyValue(`border-${s}-style`) === 'none' ||
     parseFloat(cs.getPropertyValue(`border-${s}-width`)) === 0)
  if noneOrZero:
     el.style.setProperty('border', `1px solid ${value}`)
  else:
     el.style.setProperty('border-color', value)

// readElementBorder(hypId):
  cs = getComputedStyle(el)
  colors = sides.map(s => cs.getPropertyValue(`border-${s}-color`))
  mixed = new Set(colors).size > 1
  return { color: mixed ? '' : rgbToHex(colors[0]), mixed }
```
The mixed test reads COMPUTED per-side colors (covers inline per-side `border-*-color` sites that `discoverInlineSites` already detects). When `mixed`, the popover input is empty with placeholder `mixed`.

### Edge cases

| Case | Behavior |
|------|----------|
| Element with `border:none` | `noneOrZero` true → `border:1px solid <color>` applied; undo removes the whole `border` inline shorthand and restores prior (empty) state. |
| Element with `border-width:0` | Same as none → auto-1px. |
| Element with existing 2px border | `noneOrZero` false → only `border-color` set; width/style preserved. |
| Four different per-side colors | Panel shows `mixed`; applying unifies all four. |
| Undo after auto-1px | Restores prior `border`, `border-color`, `border-width`, `border-style`, and per-side colors captured at command creation. |
| SVG element selected | `border-color` is meaningless on SVG geometry; SVG geometry is not selectable (selection excludes it), so the row is never shown for them. |

### Non-goals
- No per-side border editing UI (single all-sides row only, U6). No border-radius/width/style controls. No border on the `:root` token path.

---

## F5 — Agent comments

### User-visible behavior
- Adding a comment opens an anchored popover (textarea, "For agents" checkbox, Save/Cancel) instead of `prompt()`. `Esc` cancels; `Ctrl/Cmd+Enter` saves; plain `Enter` is a newline (S17).
- Each side-panel thread card has a "For agents" checkbox to tag/untag an existing comment.
- On Save, if ≥1 unresolved agent-tagged thread exists, the saved HTML carries a derived instruction block as the FIRST CHILD of `<head>` (research-04 Option A). The block is absent when no agent-tagged threads remain. It is regenerated on every save from the island (D7).

### Module-level design

| File | NEW/MOD | Public contract |
|------|---------|-----------------|
| `app/js/shell/comment-composer.js` | NEW | `openComposer({rect, mode:'new'|'reply', commentId?, onSubmit})` mounts a parent-document popover at `rect`; returns `{close()}`. Handles textarea, "For agents" checkbox (new mode only), Save/Cancel, key handling (S17). |
| `app/js/main.js` | MOD | Replace `prompt()` in the comment button handler and the reply button handler with `openComposer` (S18). New-comment submit calls `add-comment {hypId, body, author, agentInstruction}`; reply submit calls `reply-comment`. Add a "For agents" checkbox to `createThreadEl`; toggling calls `tag-agent` (S21). |
| `runtime/js/comments.js` | MOD | `add(hypId, body, author, agentInstruction=false)` stores the flag; add `setAgentInstruction(commentId, bool)` (undoable, S21); `toJson`/`writeIsland`/`load` round-trip `agentInstruction`; add `buildAgentBlock()→string|null` (derived block generator). |
| `runtime/js/serializer.js` | MOD | After re-embedding the island, call `comments.buildAgentBlock()`; if non-null, insert it as the FIRST CHILD of `<head>` in the clone; include its node count in the guard math (S19, §9). |
| `runtime/js/runtime-main.js` | MOD | `add-comment` handler passes `payload.agentInstruction` through; register `tag-agent {commentId, agentInstruction}` → `comments.setAgentInstruction`. |
| `app/index.html` / `app/css/shell.css` | MOD | Add minimal styles for `.hyp-comment-composer` popover and the thread "For agents" checkbox. |

### Exact escaping (S19, R06) — the single function, stated once
The agent block is one HTML comment; HTML comments cannot contain `-->`. There is EXACTLY ONE escape function, and EVERY interpolated value the block emits passes through it — `id`, `anchor.path`, `anchor.nativeId`, `contextText`, `instruction`/`body`, every reply `body` and `author`, and `author`. The only exception is `createdAt` (a machine-generated ISO-8601 timestamp that cannot contain `-->`). A native element id can be arbitrary (e.g. `id="a-->b"`), so `path`/`nativeId` MUST be escaped or they break the comment (R06). Signature (identical in V2-T9 and consumed unchanged by V2-T10):
```js
function escapeAgentBlock(s) {
  return String(s == null ? "" : s).replace(/-->/g, "--&gt;");
}
```

### Exact algorithm — agent block generation (S19, S20, research-04 Option A)
```
buildAgentBlock():
  agentThreads = threadStore.filter(t => t.agentInstruction === true && t.resolved !== true)
  if agentThreads.length === 0: return null
  lines = []
  lines.push('<!-- ===== HYPRESENT AGENT INSTRUCTIONS =====')
  lines.push('This block is auto-generated from agent-tagged review comments in this file. Each entry describes a change an AI coding agent should make to the element identified by its anchor.')
  lines.push('Do not edit this block manually — it is regenerated on every save and removed when no agent comments remain.')
  for t in agentThreads:
    lines.push('')
    lines.push(`[agent:${escapeAgentBlock(t.id)}]`)
    path = escapeAgentBlock(t.anchor.path || '(root)')
    nid  = escapeAgentBlock(t.anchor.nativeId || '')
    ctx  = escapeAgentBlock((t.contextText || '').slice(0,80))
    lines.push(`anchor: ${path} | id="${nid}" | "${ctx}"`)
    lines.push(`instruction: ${escapeAgentBlock(t.body)}`)
    for r in (t.replies || []):                       // S20: unresolved replies as continuation
      lines.push(`reply: ${escapeAgentBlock(r.body)} — ${escapeAgentBlock(r.author)}`)
    lines.push(`author: ${escapeAgentBlock(t.author)}`)
    lines.push(`date: ${t.createdAt}`)                 // ISO-8601; cannot contain '-->'
  lines.push('===== END HYPRESENT AGENT INSTRUCTIONS ===== -->')
  return lines.join('\n')
```
Serializer insertion (clone): `const head = clone.querySelector('head'); if (head && blockHtml) head.insertAdjacentHTML('afterbegin', blockHtml);` — `afterbegin` makes it the first child of `<head>`. The block is an HTML comment node; `insertAdjacentHTML` parses it as one comment node.

### Guard interaction (§9 dependency)
The agent block adds exactly ONE comment node to `<head>`. The serializer's node-count guard (§9, term `agentBlockCount`; pre-existing-block sweep S26) must add this to `expectedPostCount`. See §9 for the exact revised guard formula.

### Edge cases

| Case | Behavior |
|------|----------|
| No agent-tagged threads | `buildAgentBlock` returns null; no block inserted; guard math adds 0. |
| Agent thread later resolved | Excluded from block (filter `resolved!==true`); on next save block shrinks or disappears. |
| Instruction body contains `-->` | Escaped to `--&gt;` (S19). |
| Reply on an agent thread | All replies of the (unresolved) agent thread are emitted in full as `reply:` lines; replies carry no individual resolved flag (S20). |
| `agentInstruction` flag round-trip | Persisted in island via `writeIsland`/`toJson`/`load`; survives Save As + reopen. |
| In-editor markers/anchors | Unaffected by tagging — tagging only sets a boolean (U8 condition a). |
| Block anchors explicit | Each entry carries DOM path + native id + 80-char context quote (U8 condition b). |
| Composer opened, Cancel/Esc | No thread created; no island write. |
| Two agent threads | Two `[agent:N]` entries in document order of `threadStore`. |

### Non-goals
- No `<script type="text/llms.txt">` variant (research-04 Option B rejected). No JSON island duplicate (Option C rejected). No agent-block editing in-editor (derived only). No fallback to notice-only-in-head (U8 condition c is a contingency, not the default — Option A is fully specified and adopted).

---

## G1 — Panel survival (verification + residual hardening)

### Current state (§0): ALREADY FIXED in `color-popover.js` (dedicated child container).

### Residual scope
Two new panel features land in `.shell-panel`: F4 adds a Border row INSIDE the existing color popover container (no new top-level panel child), and F5's "For agents" checkbox renders inside existing thread cards (also no new top-level child). Therefore G1's residual risk is ONLY regression: a future innerHTML reset. v2 LOCKS the fix with a Playwright test (open document A, open document B, assert comment threads + outline survive) and asserts the final panel DOM structure below. No code change to `color-popover.js`'s container mechanism.

### Spec — exact final `.shell-panel` DOM structure (after a document open with the color popover mounted)
```
<aside class="shell-panel" id="shell-panel">
  <div class="hyp-color-popover-container">      <!-- inserted as firstChild by color-popover.js -->
    <style> … popover styles … </style>
    <div class="hyp-color-panel">
      <div><div class="hyp-color-header">Palette Tokens</div><div class="hyp-token-list">…</div></div>
      <div class="hyp-element-section">
        <div class="hyp-color-header">Selected Element</div>
        <div class="hyp-element-body">
          <div class="hyp-color-row"><label>Text</label><input data-prop="color" …></div>
          <div class="hyp-color-row"><label>Background</label><input data-prop="background-color" …></div>
          <div class="hyp-color-row"><label>Border</label><input data-prop="border-color" …></div>   <!-- F4 NEW -->
        </div>
      </div>
    </div>
  </div>
  <div class="outline-panel">…<div class="outline-list" id="outline-list">…</div></div>   <!-- SURVIVES -->
  <div class="comment-panel">…<div class="comment-threads" id="comment-threads">…</div>
       <div class="comment-unanchored" id="comment-unanchored"></div></div>               <!-- SURVIVES -->
</aside>
```
Invariant: `color-popover.js` only ever touches `.hyp-color-popover-container` (its own child); `#outline-list`, `#comment-threads`, `#comment-unanchored` are never re-created or wiped by the popover.

### Non-goals
- No panel layout redesign. No collapsible panels. No re-fix of the already-correct container mechanism.

---

## G2 — Serializer island-count guard (verification + agent-block extension)

### Current state (§0): ALREADY FIXED in `serializer.js` (`islandCount = countAllNodes(island)`).

### Diagnosis of the original guard (from `serializer.js` source)
`serialize()` flow: clone documentElement (preCount = all nodes in clone). The clone INCLUDES the live document's existing `#hyp-comments` island. `stripClone` removes every `hyp-`-prefixed-id element → the existing island (`id="hyp-comments"`) is removed and its nodes counted in `removedNodeCount` (`countAllNodes(island)` = `<script>` element node + its text node = 2). Then step 5 re-embeds a FRESH island: `islandCount = countAllNodes(island)` = 2 (script + text). Guard: `expectedPostCount = preCount - removedNodeCount + islandCount`. The off-by-one in the RED state was that the old code hardcoded `islandCount = 1` (counting only the `<script>` element, missing its text node), so `expectedPostCount` was 1 less than `postCount` → guard failed → `serialize()` returned null on every commented document. The current fix counts both nodes. **This diagnosis matches `build-log.md` line 267 exactly.**

### Residual scope part 1 (REQUIRED — R04): in-memory store is authoritative
`getCommentJson()` currently falls through to the live-DOM `#hyp-comments` island whenever `toJson()` returns `[]`. If a document was opened with comments and the user then RESOLVES all of them (store now empty), that fallthrough re-embeds the STALE island on save — resurrecting resolved threads and their stale `agentInstruction:true` flags. v2 fixes this: when the in-memory store EXISTS (the `toJson` function is present), it is the single source of truth (D7) — return its JSON when non-empty, return `null` (no island re-embed) when empty, and NEVER fall through to the DOM island. The DOM-island fallback survives ONLY for the pre-boot case where the store is not yet present. Guard math stays consistent because the live island (id `hyp-comments`) is already stripped in Phase A and counted in `removedNodeCount`; suppressing re-embed simply leaves `islandCount = 0`. (Landed in V2-T2 Change 0.)

### Residual scope part 2 (REQUIRED by F5): agent-block guard term
F5 inserts the agent block (one HTML comment node) as the first child of `<head>` AFTER the strip. The current guard does NOT account for it → with an agent block present, `postCount` would exceed `expectedPostCount` by 1 and the guard would wrongly abort. v2 EXTENDS the guard:

### Spec — revised guard formula (the precise fix)
```
// serializer.js serialize(), replacing steps 5–7
let islandCount = 0;
if (commentJson) { …re-embed island…; islandCount = countAllNodes(island); }   // unchanged, =2

let agentBlockCount = 0;
const blockHtml = commentsBuildAgentBlock();         // null when no unresolved agent threads
if (blockHtml) {
  const head = clone.querySelector('head');
  if (head) { head.insertAdjacentHTML('afterbegin', blockHtml); agentBlockCount = 1; }  // one comment node
}

const postCount = countAllNodes(clone);
const expectedPostCount = preCount - removedNodeCount + islandCount + agentBlockCount;
if (postCount !== expectedPostCount) { emit('error', {...}); return null; }
```
`agentBlockCount` is 1 because an HTML comment is a single `Comment` node with no children (verified: `countAllNodes` over a lone comment = 1). The existing-block case: if the LIVE document already had an agent block in `<head>` from a prior save, it is a plain comment node (not `hyp-`-classed, not removed by strip) — it is preserved by the clone AND a fresh one is added → DOUBLE block. **Mitigation (S26 — required, landed in V2-T2 Phase A2):** before inserting, `stripClone` ALSO removes any existing agent block comment node from `<head>` (match by the sentinel `===== HYPRESENT AGENT INSTRUCTIONS =====`), counting it in `removedNodeCount`. The revised `stripClone` adds a comment-node sweep over `<head>` children removing nodes whose `nodeType===8` and `nodeValue` contains the sentinel.

### Edge cases

| Case | Behavior |
|------|----------|
| Save with comments, no agent tags | island re-embedded (count 2); no agent block (count 0); guard passes. |
| Save with ≥1 agent tag | island (2) + agent block (1); existing prior block stripped first; guard passes. |
| Save with no comments at all | `commentJson` null → island 0; no agent block; guard = preCount−removed; passes (this is the v1 empty-store path, unchanged). |
| Open with comments, then resolve ALL of them, then save (R04) | Store exists but `toJson()`=[] → `getCommentJson()` returns `null` → no island re-embed; the stale live island was stripped in Phase A and counted; guard passes; resolved threads do NOT reappear. |
| Re-save a file that already has an agent block | Prior block stripped (counted in removed), fresh block added (count 1); no duplication; guard passes. |
| Guard genuinely fails (real content loss) | `emit('error', …)`; `serialize()` returns null; save aborts (never emit a damaged file — A8 §5 step 4). |

### Non-goals
- No change to the strip semantics for document content. No removal of the node-count guard (it is the integrity gate). No pre-DOCTYPE block placement (head-first-child only).

---

## Cross-feature module map delta (03-module-map.md additions)

| Module | Status | One-line purpose |
|--------|--------|------------------|
| `runtime/js/interaction.js` | NEW | Single combined Moveable (drag+resize+snap+guides); drop hit-test; commits drop as one history command (F2/F3). |
| `runtime/js/reorder.js` | NEW | Pure DOM-reading drop classification helpers: `classifyDrop`, `isContainer`, `dominantAxis` (F3, unit-testable). |
| `runtime/js/resize.js` | DELETED | Folded into `interaction.js`. |
| `runtime/js/move.js` | DELETED | Folded into `interaction.js`. |
| `app/js/shell/comment-composer.js` | NEW | Parent-document anchored comment popover (textarea + "For agents" toggle + Save/Cancel) (F5). |
| `runtime/js/comments.js` | MOD (V2-T9) | + `agentInstruction` flag, `setAgentInstruction`, `buildAgentBlock` (single `escapeAgentBlock` on every value, R06), `reanchorAfterMove` (multi-signal regen for all threads, R11/R14). |
| `runtime/js/selection.js` | MOD (V2-T8) | + `onSelectionChange` observer registry (R09); imports unchanged. |
| `runtime/js/text-edit.js` | MOD (V2-T8) | + calls `interaction.suspend()/resume()` (one-way import, R09). |
| `runtime/js/serializer.js` | MOD | + agent-block insertion + revised guard (agentBlockCount + sentinel sweep S26) + `getCommentJson` empty-store fix (R04) (F5/G2). |
| `runtime/js/color.js` | MOD | + border-color routing + auto-1px + `readElementBorder`/`readElementColors` (F4). |
| `runtime/js/commands.js` | MOD | + `reorder`, `colorBorder`; `move` rewritten to `translate` (F3/F4/S1). |
| `runtime/js/runtime-main.js` | MOD | + dialog/interaction rewiring, `element-color-read`, `tag-agent`, `set-tool` shim, `onSelectionChange` wiring in `boot()` (R09). |
| `server/api.py` | MOD | + dialog handlers, open-path tracking, dialog launcher seam with `pwsh`→`powershell.exe` fallback (R02) (F1). |
| `server/server.py` | MOD | + `/api/dialog-open`, `/api/dialog-save-as`, `/api/save` routes + test-only `/api/_test/set-dialog` (F1). |

---

## Global non-goals (v2 scope fence)
- No new vendored libraries (A9/A10); Playwright is dev/test only.
- No refactor of the bridge, history, element-registry, or selection internals beyond the named seams (S4, S22).
- No support for browsers other than Chrome on Windows 11.
- No real-time collaboration, no multi-document, no new document creation.
- No change to the v1 serializer strip semantics for document content; the document's own scripts/styles/handlers/SVG/native `data-*` remain untouched (A8/A11).
