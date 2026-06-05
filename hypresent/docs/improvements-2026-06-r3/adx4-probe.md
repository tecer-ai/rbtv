# ADX4 — Alt-held Symmetric Resize: Center-Shift Contract (R12)

**Date:** 2026-06-05
**Mode:** Read-only design probe. Sole write = this file. No code edits, no git, no web.
**Bundle:** `app/js/vendor/moveable.min.js` (245,551 bytes, one minified line — all offsets are byte positions into that single line).
**Anchor discipline:** byte offsets are hints against the bundle as read this session; re-locate by quoted token, not offset.

**State correction (supersedes diagnosis.md R10/R12 "fix surface" framing):** R10 (dist-based resize) and the R12 trigger `e.setFixedDirection([0,0])` ARE ALREADY SHIPPED in the live tree. `applyVisualResize` now takes a `dist` param and writes `flexBasis = beforeRect[mainDim] + dist[idx]` (`interaction.js` line 130); `onResizeStart` already calls `e.setFixedDirection([0,0])` when `altKey` (line 224). The ONLY remaining gap is the one this probe answers: under `fixedDirection:[0,0]` Moveable doubles `e.dist` correctly but the box must ALSO shift by −Δ on the dragged axis to keep the center fixed, and `onResize` (line 226) consumes `e.width/e.height/e.direction/e.dist` and **ignores `e.drag`**.

---

## 1. Payload Evidence

**The vendored build exposes BOTH `e.drag.beforeTranslate` ([x,y] numbers) AND `e.drag.transform` (string) on every `onResize` event. The center-shift under `fixedDirection:[0,0]` lives in `e.drag.beforeTranslate`, and it is ABSOLUTE (final translate in transform space since gesture start), NOT a per-frame delta.**

### Evidence chain (quoted, with offsets)

**A. The onResize event object is built at `@~102100–102760`.** The `drag` field is the entire return of a synthetic Draggable call:

```js
// @102~ (onResize compute):
var Q=[(W=U-D)-b,(j=$-C)-x];               // Q = delta;  W=distWidth, j=distHeight
var tt=kr(t,U,$,Z,v,r);                      // tt = fixedDirection-induced POSITION offset (see C)
var et=Wi.drag(t,ur(e,t.state,tt,!!o,!1,"draggable")),  // et = e.drag  (full Draggable output)
    nt=et.transform,                          // nt = e.drag.transform (string)
    rt=g+W,it=m+j,
    ot=sa(t,e,Rn({width:rt,height:it,offsetWidth:Math.round(U),offsetHeight:Math.round($),
      startRatio:S,boundingWidth:U,boundingHeight:$,direction:Y,
      dist:[W,j],delta:Q,isPinch:!!o,drag:et},
      aa({style:{width:rt+"px",height:it+"px"},transform:nt},et,e)));
return !p&&la(t,"onResize",ot),ot
```

So `e.drag === et`, `e.drag.transform === nt`, and the emitted top-level `transform` is also `nt` (`e.drag.transform`).

**B. The Draggable `drag:` method (`drag:function` @94154) returns an object carrying BOTH arrays + the string.** Return body @95255–95650:

```js
// j is built first as the transform STRING:
//   ...,"translate(".concat(k[0],"px, ").concat(k[1],"px)"),...   (uses k = snapped translate)
var H=t.state,U=H.width,$=H.height,
Z=sa(t,e,Rn({transform:j, dist:B, delta:A, translate:k,
   beforeDist:I, beforeDelta:F, beforeTranslate:G,
   left:N, top:Y, right:q, bottom:X, width:U, height:$, isPinch:o}, ...));
```

Field map for the resize-drag (`et`):
| Field on `e.drag` | Type | Meaning |
|---|---|---|
| `beforeTranslate` = `G` | `[x,y]` numbers | **before-snap** absolute translate target (start-relative). **This is the center-shift.** |
| `translate` = `k` | `[x,y]` numbers | **snapped** absolute translate target (snap can perturb it; do NOT use for symmetric math) |
| `transform` = `j` | string `"... translate(k[0]px, k[1]px) ..."` | embeds the SNAPPED `k`, not `G` |
| `dist` = `B`, `beforeDist` = `I` | `[x,y]` | cumulative drag deltas (snapped / before-snap) |

**C. WHY `beforeTranslate` is the center-shift (`kr` @69213 + `Ra` @150863).** The resize feeds `tt = kr(...)` as the synthetic drag's distance. `kr` computes the position offset induced by `fixedDirection` (`v=o.fixedDirection` @69360). The size doubling and the matching position offset are conjugate: `Ra` (the dist function, `function Ra(` @150863) computes `m=[0,1].map(e=>Ia(t[e]-g[e]))` with `g=n.fixedDirection`, then `b=2/m[e]`. For `fixedDirection:[0,0]` and an East edge (`direction[0]=1`): `m[0]=|1−0|=1`, `b[0]=2/1=2` → **distWidth doubles** (matches diagnosis "doubles e.dist"). The conjugate `kr` offset is exactly −(halfGrowth) on the moved axis → fed through Draggable it surfaces as `G[0] = startTranslateX − dist[0]/2_growth`. Net: `e.drag.beforeTranslate` holds `startTranslate + centerCompensation`.

**D. ABSOLUTE, not per-frame — and baseline INCLUDES any pre-existing move.** In `drag:`, `G = ye(mr({datas,distX:f,distY:p}), g)` where **`g = n.startValue`**. `dragStart:function` (@93475) seeds `n.startValue=[0,0]` then calls `Cr(t,e,"translate")`, and `Cr` (@68150) sets `i.startValue = s[0].functionValue` — i.e. it **reads the element's existing `translate` start value** from `r.startTransforms`. Therefore `G` is the FINAL absolute translate measured from the element's start transform, every frame (cumulative), and it already folds in any pre-existing move. `I = Ee(G,g) = G − startValue` is the per-gesture delta; `G` itself is the absolute value the editor should write.

**E. Moveable does NOT auto-write the element during resize.** `dr(t,e,"translate")` (@64655) only mutates the internal `nextTransforms` list used to build the reported `transform` string; it does not assign `el.style`. The host (`applyVisualResize`) is the sole writer. (Confirmed: the editor's wrapper is a separate node; Moveable reports geometry, the handler applies it.)

> **Confidence: HIGH** that `e.drag.beforeTranslate` is `[x,y]` numbers and is the center-shift. **HIGH** that it is absolute (start-relative final), not per-frame. **MED-HIGH** that its baseline `startValue` already includes a pre-existing `translate` — `Cr`/`startTransforms` reads the element transform at start, but the synthetic resize-drag's `startTransforms` seeding was not live-probed this session. **The contract is designed to be correct under both readings** (see §3 "Composition" — write the absolute value; verify via the one-line live probe in §4).

---

## 2. Move-path Map

How the editor writes element position for MOVES (the format the center-shift must match exactly):

| Concern | Where | Detail |
|---|---|---|
| **CSS property** | `onDrag` `interaction.js:248` | CSS individual `translate` property: `el.style.translate = "${x}px ${y}px"` (space-separated, NOT `transform: translate()`). Decision-log "Move = CSS `translate` only"; chosen so it composes with document-owned `transform: rotate()/scale()` (commands.js:105-110 docblock). |
| **Format** | `interaction.js:248` | Exactly `` `${baseTranslate[0] + dx}px ${baseTranslate[1] + dy}px` `` → e.g. `"30px 40px"`. Two values, `px` units, single space. Empty/zero ⇒ property removed. |
| **Parse helper** | `parseTranslate` `interaction.js:78-85` | Splits on `/\s+/`, `parseFloat` each; single value ⇒ `[x,0]`. This is the canonical reader of `el.style.translate`. |
| **Base composition** | `onDragStart:241-242` | `baseTranslate = parseTranslate(el.style.translate)` captured at gesture start; per-frame `e.translate` (cumulative `[dx,dy]`) is ADDED to it. So a move always composes onto the pre-existing translate. |
| **Write helper (history)** | `move(hypId, before, after)` `commands.js:112-132` | `do()`: `after===""||null ⇒ removeProperty("translate")` else `setProperty("translate", after)`. `undo()`: same on `before`. `before`/`after` are the raw `el.style.translate` strings. |
| **Undo capture** | `onDragEnd:279-281` | `before = beforeTranslate` (the string captured at dragStart, `interaction.js:241`); `after = el.style.translate`; pushed via `historyPush(makeMoveCommand(id, before, after))`. One command, captured atomically at gesture end. |
| **History push** | `history.push` `history.js:39-53` | Runs `cmd.do()`, appends, truncates redo tail. Single linear stack shared by resize+move (`makeResizeCommand` and `makeMoveCommand` both land here). |
| **Out-of-flow badge** | `computeOutOfFlow` `interaction.js:86-89` + emit `interaction.js:283` | `out-of-flow {hypId, bool}` fires after a MOVE when `|translate.x|≥0.5 || |translate.y|≥0.5`. Driven purely off `el.style.translate`. |
| **Serializer** | `serializer.js` (no `translate` special-case — grep: zero hits) | Inline `style` (incl. `translate`) is serialized verbatim with the element. No coupling to fix. |

**Key consequence:** the move path's "position" surface is the SAME CSS `translate` longhand, same `"Xpx Ypx"` string format, same `move()` command, same single history stack. The resize center-shift must reuse all of these so serializer/undo/move stay coherent.

---

## 3. Implementation Contract

Transcribable by a non-reasoning executor. All anchors are quoted-token re-locatable.

### 3.0 Role matrix (which writer applies the center-shift)

`roleOf` (`element-registry.js:129-146`) returns one of `absolute | flex-child | grid-child | block`.

| Role | Size write today | Box anchor after size write | Center-shift method |
|---|---|---|---|
| `flex-child` (row) | `flexBasis = beforeRect.width + dist[0]` (`:130`) | flex line start-edge (left) holds | **`translate.x −= dist[0]`** (write to CSS `translate`) |
| `flex-child` (col) | `flexBasis = beforeRect.height + dist[1]` (`:130`) | flex line start-edge (top) holds | **`translate.y −= dist[1]`** |
| `grid-child` / `block` | `width = e.width`, `height = e.height` (else-branch `:137`) | top-left holds | **`translate.x −= dist[0]` and/or `translate.y −= dist[1]`** |
| `absolute` | `width/height = e.width/e.height` + edge comp (`:139-143`) | left/top, with `-1`-edge comp only | **left/top path — see 3.3; do NOT write translate** |

**The shift magnitude is `dist[axis]` (NOT `dist/2`).** Under `fixedDirection:[0,0]`, `e.dist[0]` is ALREADY the doubled value (total width growth). The box grew `dist[0]` from a fixed left edge; to recenter, shift left by the full `dist[0]` is WRONG (that would move the whole box, not center it) — shift by `dist[0]/2`? No. Resolve this by READING Moveable's own number, not recomputing:

> **CONTRACT PRIMITIVE: do NOT hand-compute the shift. Read `e.drag.beforeTranslate` and write it as the absolute translate.** Moveable already solved the conjugate position offset in `kr`/`Ra`; `beforeTranslate` = `startTranslate + exactCenterShift`. Writing it verbatim is correct for any handle (edge or corner), any direction, and any `fixedDirection`, with zero arithmetic risk.

### 3.1 onResize handler (flow elements: flex-child, grid-child, block)

Replace `interaction.js:226`:

```js
// BEFORE (current):
function onResize(e) { const el = e.target; applyVisualResize(el, roleOf(el), e.width, e.height, e.direction, e.dist); }

// AFTER:
function onResize(e) {
  const el = e.target;
  const role = roleOf(el);
  applyVisualResize(el, role, e.width, e.height, e.direction, e.dist);
  // R12 center-shift: under fixedDirection:[0,0] (Alt) Moveable doubles dist AND
  // reports the conjugate center-compensating translate on e.drag.beforeTranslate
  // (ABSOLUTE, start-relative, already folds in any pre-existing move). For flow
  // roles, write it to the SAME CSS `translate` longhand the move path uses.
  // Absolute role compensates via left/top inside applyVisualResize — skip there.
  if (resizeAltActive && role !== "absolute" && e.drag && e.drag.beforeTranslate) {
    const bt = e.drag.beforeTranslate;          // [x, y] numbers, absolute
    el.style.translate = `${bt[0]}px ${bt[1]}px`;
  }
}
```

`resizeAltActive` is a module-scope boolean set in `onResizeStart` (3.4). Gate on it so a NON-Alt resize never touches `translate` (one-sided resize keeps the opposite edge fixed natively — no shift, and the box's translate must stay whatever the user's prior move set).

**Composition (the load-bearing correctness point):** because `e.drag.beforeTranslate` is the ABSOLUTE translate measured from the element's start transform (§1-D, `g = startValue` read from `startTransforms`), assigning it **REPLACES** `el.style.translate` with the correct composed value `(pre-existing move) + (center shift)`. It must NOT be added to `beforeTranslateResizeStart` — that would double-count the pre-existing move. Write absolute, do not accumulate.

### 3.2 Undo capture — translate folded into the SAME resize command

The size longhands and the translate must restore in ONE undo step. Two equivalent surfaces; **Option A (extend the resize capture map) is recommended** — it reuses `makeResizeCommand`'s `applyStyleMap` with zero new command type.

**Extend `captureSizingState` (`interaction.js:92-106`) to also capture `translate` for flow roles:**

```js
function captureSizingState(el, role) {
  const s = el.style; const m = {};
  if (role === "absolute") {
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
    m.top = s.getPropertyValue("top") || ""; m.left = s.getPropertyValue("left") || "";
  } else if (role === "flex-child") {
    m.flexBasis = s.getPropertyValue("flex-basis") || "";
    m["flex-grow"] = s.getPropertyValue("flex-grow") || "";
    m["flex-shrink"] = s.getPropertyValue("flex-shrink") || "";
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
    m.translate = s.getPropertyValue("translate") || "";        // R12 ADD
  } else {
    m.width = s.getPropertyValue("width") || ""; m.height = s.getPropertyValue("height") || "";
    m.translate = s.getPropertyValue("translate") || "";        // R12 ADD (grid/block)
  }
  return m;
}
```

Then `onResizeEnd` (`interaction.js:227-236`) is UNCHANGED in structure: it already diffs `beforeSizing` vs `after` over `Object.keys(after)`, so `translate` is automatically included in the change-detection and in the `makeResizeCommand(id, beforeSizing, after)` map. `commands.resize.do/undo` (`commands.js:90-102`) calls `applyStyleMap`, and `applyStyleMap` (`commands.js:36-45`) already does `removeProperty` on `""`/null and `setProperty` otherwise — so a `translate:""` before-value (no prior move) correctly RESTORES to "no translate" on undo, and a `translate:"40px 0px"` before-value (prior move) restores the move exactly. **`kebabCase("translate")` = "translate"** (no uppercase) — passes through `applyStyleMap` correctly.

**Atomicity:** capture happens at `onResizeStart` (before-snapshot, line 220) and `onResizeEnd` (after-snapshot, line 229) — both already in the resize lifecycle. The translate before-value is captured in the SAME `beforeSizing` map as the flex/size longhands, at the same instant. One `historyPush`, one command, one undo step. ✔ satisfies "translate before-value captured atomically with the flex/size longhands in the SAME history command."

### 3.3 Absolute branch

**Do NOT write `translate` for `role==='absolute'`.** Verify-and-act:

- The absolute branch (`applyVisualResize` `:139-143`) compensates `left`/`top` ONLY when `direction[axis]===-1` (the dragged handle is the west/north edge). Under `fixedDirection:[0,0]`, BOTH edges move but Moveable reports a single `direction` for the grabbed handle (e.g. East = `[1,0]`, so `direction[0]===-1` is FALSE) → **the current left/top comp does NOT fire for the center case** → absolute elements would also grow one-sided unless fixed.
- **Moveable does NOT auto-write left/top** (§1-E: `dr` only builds the transform string). So for absolute, the center-shift must be applied by the editor via left/top, mirroring the existing dw/dh comp but for the symmetric case.

**Absolute center-shift (extend `applyVisualResize` `:139-143`):**

```js
if (role === "absolute") {
  const dw = width != null ? width - beforeRect.width : 0;
  const dh = height != null ? height - beforeRect.height : 0;
  if (resizeAltActive) {
    // Symmetric: half the growth on EACH side. Move left/top by -growth/2 to keep center fixed.
    if (dw !== 0) el.style.left = originalLeft - dw / 2 + "px";
    if (dh !== 0) el.style.top  = originalTop  - dh / 2 + "px";
  } else {
    if (direction && direction[0] === -1 && dw !== 0) el.style.left = originalLeft - dw + "px";
    if (direction && direction[1] === -1 && dh !== 0) el.style.top  = originalTop  - dh + "px";
  }
}
```

Undo for absolute already captures `left`/`top` in `captureSizingState` (`:95-96`) → no translate added to the absolute map; the `left`/`top` before-values restore the position atomically in the same resize command. **(Do NOT add `m.translate` to the absolute branch — it does not use translate.)**

> **Note for absolute under Alt:** `dw` here is `e.width − beforeRect.width`. Because Alt sets `fixedDirection:[0,0]`, `e.width` is the doubled value, so `dw` = total growth, and `dw/2` = per-side shift. This is the one place the contract DOES compute (`/2`) rather than read `beforeTranslate`, because the absolute path's position surface is left/top, not translate — Moveable's `beforeTranslate` is transform-space and would not map onto left/top. Verify the `/2` against a live absolute Alt-resize; if Moveable's reported `e.width` is NOT doubled for the absolute target, drop the `/2`. (Flow roles avoid this ambiguity entirely by reading `beforeTranslate`.)

### 3.4 onResizeStart — set the Alt flag alongside the existing setFixedDirection

`onResizeStart` (`interaction.js:218-225`) ALREADY calls `e.setFixedDirection([0,0])` on `altKey`. Add the module-scope latch so `onResize`/`onResizeEnd` know the gesture is symmetric:

```js
// module scope, near line 42-51:
let resizeAltActive = false;

function onResizeStart(e) {
  const el = e.target; const role = roleOf(el);
  resizeAltActive = !!(e.inputEvent && e.inputEvent.altKey);   // R12 latch
  beforeSizing = captureSizingState(el, role);                 // now also captures translate (3.2)
  beforeRect = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  originalTop = parseFloat(cs.top) || 0; originalLeft = parseFloat(cs.left) || 0;
  if (resizeAltActive) { e.setFixedDirection([0, 0]); }        // unchanged behavior
}
```

**Why latch at start, not read `altKey` each frame:** Moveable snapshots `fixedDirection` at resizeStart (`startFixedDirection`, bundle @99603 region). The anchor mode is fixed for the whole gesture. Reading `altKey` per-frame in `onResize` would desync the shift from the anchor if the user releases Alt mid-drag (Moveable keeps the doubled dist; the handler would stop shifting → drift). Latch once.

### 3.5 resizeEnd finalization

`onResizeEnd` (`interaction.js:227-236`) needs only the latch reset; the translate is already in the captured `after` map (3.2) and flows into the single resize command:

```js
function onResizeEnd() {
  const el = byId(activeHypId);
  if (!el) { beforeSizing = null; beforeRect = null; resizeAltActive = false; return; }   // reset on early-out
  const role = roleOf(el); const after = captureSizingState(el, role);
  let changed = false; for (const k of Object.keys(after)) if (beforeSizing[k] !== after[k]) { changed = true; break; }
  if (changed) {
    historyPush(makeResizeCommand(activeHypId, beforeSizing, after));
    emit("geometry-changed", { hypId: activeHypId, prop: "resize", before: beforeSizing, after });
    if (resizeAltActive) maybeEmitOutOfFlow(el);    // 3.6 — recommended, see Edge Rules
  }
  beforeSizing = null; beforeRect = null;
  resizeAltActive = false;                          // R12 reset
}
```

No separate `move()` command is pushed for the shift — the translate rides inside the resize command's style map. This keeps it ONE undo step and avoids a spurious second history entry. ✔ "resizeEnd finalization."

### 3.6 Out-of-flow badge (recommendation, one line — see Edge Rules)

---

## 4. Edge Rules

| # | Edge case | Rule |
|---|---|---|
| **E1** | **Alt-resize on an element with a pre-existing translate from a prior MOVE** | SAFE by construction. `e.drag.beforeTranslate` is ABSOLUTE and its baseline `startValue` is read from the element's start transform (§1-D), so it ALREADY equals `(prior move) + (center shift)`. Assign it directly (`onResize`, 3.1) — REPLACE, never add to `beforeSizing.translate`. The prior move is preserved, not lost. **Verify once live:** in DevTools, give an element `style.translate="80px 0px"`, Alt-resize East +60, and confirm `e.drag.beforeTranslate[0]` ≈ `80 − 30` (i.e. ~50), not `−30`. If it reads `−30` (delta-only), Moveable did NOT seed startValue from the element transform → fallback: `el.style.translate = (baseTranslateAtResizeStart[0] + e.drag.beforeTranslate[0]) + "px " + (baseTranslateAtResizeStart[1] + e.drag.beforeTranslate[1]) + "px"`, capturing `baseTranslateAtResizeStart = parseTranslate(el.style.translate)` in `onResizeStart`. The §1 evidence points to ABSOLUTE; this is the one bundle behavior worth confirming before shipping. |
| **E2** | **Alt-resize undo restoring BOTH size longhands AND translate in one step** | SATISFIED by 3.2: `translate` is captured into the SAME `beforeSizing`/`after` map as `flex-basis`/`flex-grow`/`flex-shrink`/`width`/`height` (flow) or `width`/`height`/`left`/`top` (absolute). `onResizeEnd` pushes ONE `makeResizeCommand(id, before, after)`. `commands.resize.undo` → `applyStyleMap(el, before)` restores every longhand incl. `translate` in a single `cmd.undo()`. One Ctrl+Z reverts size AND position together. No second command, no ordering hazard. |
| **E3** | **No-prior-move element, Alt-resize, then undo** | `beforeSizing.translate = ""` (captured at start). `applyStyleMap` on `""` calls `removeProperty("translate")` (`commands.js:39-41`) → the property is REMOVED on undo (not set to `"0px 0px"`), returning the element to a clean no-translate state. ✔ |
| **E4** | **Non-Alt (one-sided) resize must not write translate** | `resizeAltActive` is `false` → the `onResize` translate write is gated off (3.1), and `captureSizingState` still captures `translate` but it never changes, so `onResizeEnd`'s diff sees `before.translate === after.translate` and it contributes nothing to the command. A pre-existing move on a one-sided-resized element is left untouched. ✔ |
| **E5** | **Out-of-flow badge for Alt-resize shifts (RECOMMENDATION)** | **Do NOT fire the `out-of-flow` badge for Alt-resize center shifts.** Rationale: the badge (`computeOutOfFlow`, `interaction.js:86`) signals "this element was DRAGGED out of its flow position" — a deliberate move. An Alt-resize translate is a *symmetry artifact* (the element is still in its flow slot, just visually centered around it); flagging it as out-of-flow would mislead the user into thinking they moved it. The translate IS non-zero, so `computeOutOfFlow` would return `true` — therefore the badge must be SUPPRESSED for resize-origin translates, not merely "not emitted." Implementation: simply DO NOT call any out-of-flow emit in `onResizeEnd` (omit 3.6's `maybeEmitOutOfFlow`). The move path (`onDragEnd:283`) remains the sole emitter. **One-line rule: resize never emits `out-of-flow`; only `dragEnd` (a real move) does.** (If product later wants "visually-left-its-box" signalling for Alt-resize, add a DISTINCT badge — do not overload out-of-flow.) |
| **E6** | **Corner Alt-resize (both axes shift)** | `e.drag.beforeTranslate` is `[x,y]` — both components are set for a corner handle, so writing it covers both axes in one assignment (3.1). No per-axis branching needed for flow roles. For absolute (3.3), both `dw/2` and `dh/2` fire. ✔ |
| **E7** | **Flex column vs row** | `e.drag.beforeTranslate` is axis-agnostic (Moveable computes the conjugate offset on whichever axis(es) the handle moved). The flow write in 3.1 assigns the whole `[x,y]` regardless of `isFlexRow`, so column resizes get `translate.y` shift automatically — no dependence on `applyVisualResize`'s internal `mainAxisIdx`. ✔ |
| **E8** | **Serializer coherence** | The shift uses CSS `translate` longhand = the move path's exact surface; `serializer.js` has zero `translate` special-casing (serializes inline style verbatim), so a center-shifted element saves and reloads identically whether the translate came from a move or an Alt-resize. No serializer change. ✔ |

---

## Verification checklist (for the implementer)

1. **E1 live probe** (the one HIGH-but-confirm item): pre-set `translate`, Alt-resize, read `e.drag.beforeTranslate` — absolute (includes prior move) vs delta-only. Pick the 3.1 write vs the E1 fallback accordingly.
2. **Absolute `/2`**: confirm `e.width` is doubled for an absolute target under `fixedDirection:[0,0]`; keep `dw/2` if yes, drop `/2` if no.
3. **Undo**: Alt-resize a start-pinned block, Ctrl+Z once → width AND translate both revert in a single step (E2).
4. **Repro fix**: Alt E-drag +60 on a start-pinned block → right edge +60, left edge −60 (center fixed), NOT right +120 / left 0.
5. **Regression**: non-Alt resize of the same element writes NO translate (E4); existing `test_r2_resize_real.py` (one-sided width path) stays green.
