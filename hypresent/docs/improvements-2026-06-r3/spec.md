# Hypresent v3 — Feature Specification (Session 3, improvements-2026-06-r3)

Authoritative, executor-ready specification for the Session-3 improvement cycle (scorecard **R10–R14** + EXIT). Grounded in `docs/improvements-2026-06-r3/user-feedback.md` (owner verbatim + locked decisions D1–D6), `docs/improvements-2026-06-r3/diagnosis.md` (authoritative root causes + fix surfaces — NOT relitigated here), and `docs/improvements-2026-06-r3/evidence-summary.md` (live gesture numbers — the source of every acceptance threshold). It extends but NEVER supersedes any v1/v2/`decision-log.md` locked decision (D1 flow-aware resize, D2/D7 `translate`-only move, A8/A11/A12 serializer guarantees).

The orchestrator-locked **architecture directives AD1–AD8** (see scope) are binding. This document designs the details *within* them; where a directive and the diagnosis differ on a mechanical point, the directive wins and the difference is flagged.

**Anchor discipline (binding for all downstream tasks):** every `file:line` citation is a NON-BINDING hint against the source as read 2026-06-05. The live tree drifts. Downstream task files MUST locate every edit by the quoted code CONTENT, never by line number.

**Implementation sequencing (AD7, binding):** **R10 → R12 → R11 → R13 → R14**, each landing with its own tests and its own commit on `master` (no push, per D6). Do not interleave R10 and R12 (they share the resize handlers; R12 must layer onto a verified-1:1 R10).

---

## 0. Live-code reconciliation (diagnosis vs. current source — flagged loudly)

The diagnosis is authoritative on ROOT CAUSE and FIX SURFACE. It drifted from the live source on a few mechanical points that change WHERE/HOW an edit lands, never WHETHER. Stated here so no downstream task trusts a stale detail.

| # | Diagnosis / scope statement | Live source (read 2026-06-05) | Impact |
|---|------------------------------|-------------------------------|--------|
| L1 (R10) | `captureSizingState` "captures only `flex-basis`/`width`/`height` for the flex role" | CONFIRMED verbatim: `interaction.js` `captureSizingState`, `role === "flex-child"` branch captures `flex-basis`, `width`, `height` only — NO `flex-grow`/`flex-shrink`. | AD1 requires undo to capture prior values of all THREE longhands. `captureSizingState` MUST add `flex-grow` + `flex-shrink` to the flex-child branch (see R10 change map). `commands.resize` needs NO change — its `applyStyleMap` already maps `""`→`removeProperty`, which restores the absent-inline case. |
| L2 (R10) | `onResize` "passes only `e.width`/`e.height`" | CONFIRMED: `onResize(e) { applyVisualResize(el, roleOf(el), e.width, e.height, e.direction); }`. `e.dist` is never read. `onResizeStart` already captures `beforeRect = el.getBoundingClientRect()`. | `onResize` must pass `e.dist` through; `applyVisualResize` gains the dist-based path for the flex-grow branch. `beforeRect` is the start-rendered baseline AD1 needs — already present. |
| L3 (R12) | `fixedDirection` is the native center-origin primitive; `startFixedDirection` snapshots at resizeStart | CONFIRMED in vendored `moveable.min.js`. `moveable` is a module-level `let` in `interaction.js`, mutable from `onResizeStart`/`onResizeEnd`. | AD3's `fixedDirection` assignment is a one-line set on the module-level `moveable`. Default must be restored at `resizeEnd` so non-Alt gestures keep Moveable's opposite-edge anchor. |
| L4 (R11) | Position-snap resize guides are wired and fire on the healthy path; only equal-size matching is net-new | CONFIRMED: `buildMoveable` sets `snappable:true` + `elementGuidelines`; `test_f2_select_guides.py::test_resize_shows_guidelines` asserts a `.moveable-line` renders during a real `.research-card` resize. README line 34 claims alignment guides appear during both drag and resize. | R11(a) = a VERIFICATION test on a flex-grow element post-R10 (no new snap config). R11(b) = NET-NEW equal-size matching (custom overlay; Moveable has no size-equality snap). |
| L5 (R13) | No edit/delete op exists for comments or replies | CONFIRMED: `comments.js` exports `add`/`reply`/`resolve`/`setAgentInstruction` only; `main.js` `createThreadEl` renders Reply / Resolve / For-agents only; `comment-composer.js` has `mode:'new'|'reply'` only. | R13 is a clean addition across `comments.js` (4 ops), `runtime-main.js` (4 registrations), `main.js` `createThreadEl` (edit/delete affordances), `comment-composer.js` (`edit` mode). |
| L6 (R14) | `data-hyp-agent` does not exist; `stripClone` removes every `data-hyp-*`; the agent block emits a stale structural path | CONFIRMED: `serializer.js` `stripClone` Phase B removes every `data-hyp-*` attribute; `comments.js` `buildAgentBlock` emits `anchor: ${path} | id="${nid}" | "${ctx}"`. `resolveCloneNode` (index-based live→clone mapping) exists for the contenteditable sweep but is UNSOUND for stamping (review F3: its live `childNodes` indices desync from the post-strip clone once body-appended `hyp-` chrome is removed). | AD6 is satisfied by the **transient live-stamp + strip-exempt-this-pass** strategy (S3-13): `serialize()` stamps the live element by `matchAnchor` identity BEFORE cloning, exempts `data-hyp-agent` from the strip for that pass, and unstamps the live DOM in a `finally` — so the SAVED clone carries the stamp and the live DOM is clean again before `serialize()` returns (history-safe). `buildAgentBlock` anchor line is rewritten. NOT index-based `resolveCloneNode`. |

**No reconciliation invalidates any directive.** All six are mechanical.

---

## Spec-level decisions (S3-numbers; resolve every ambiguity the directives delegated)

These extend (never replace) the decision-log and the v2 S-numbers. Each is binding on the implementer.

| ID | Decision | One-line rationale |
|----|----------|--------------------|
| S3-1 | **R10 fix primitive = `flex-grow:0; flex-shrink:0; flex-basis:<target>px` longhands** on the resized main-axis for a `flex-child` whose parent is the resize axis (AD1). `target = beforeRect[axis] + e.dist[axis]`. This kills grow-refill (dead zone) AND basis-double-apply (amplification) in one write. | Diagnosis Open-Q1 option (a); the only primitive that tracks the cursor 1:1 in BOTH slack and no-slack regimes. Neutralizing grow is D1-legal (D1 lists `flex-grow` editable). |
| S3-2 | **R10 cross-axis on a flex-row child = plain `height` from `beforeRect.height + e.dist[1]`** (AD2: height stays plain `height`). The content-min floor is accepted (the element cannot shrink below its text); a 1:1 fix tracks the cursor until that floor, then clamps — that residual clamp is correct, not a bug. | AD2; diagnosis R10c. Cross-axis height is not grow-controlled, so no grow neutralization on that axis. |
| S3-3 | **R10 passes `e.dist` + `e.direction` through `onResize`**; `applyVisualResize` signature gains `dist`. The healthy non-grow branches (block/grid `else`, `absolute`) keep consuming `e.width`/`e.height` UNCHANGED — ZERO behavior change, guarded by `test_r2_resize_real.py` + new healthy-path tests (AD1). | Diagnosis Healthy-paths table; the amplification/dead-zone lives ONLY in the `flex-child` grow branch. |
| S3-4 | **R10 undo capture = add `flex-grow` + `flex-shrink` to `captureSizingState`'s `flex-child` branch** (L1). Captured BEFORE the gesture writes, so the absent-inline case captures `""` → undo `removeProperty` restores it. `commands.resize` unchanged. | AD1 "Undo MUST capture prior values of all three longhands including the absent-inline case"; Risk-2 (highest-value regression hazard). |
| S3-5 | **R12 Alt source = `e.inputEvent.altKey` read at `onResizeStart`**; if held, `moveable.fixedDirection = [0,0]` (native center-origin) for the gesture; restored to the default `false` at `onResizeEnd` (AD3). Start-only: a mid-gesture Alt change is ignored (Moveable snapshots `fixedDirection` at resizeStart). | AD3; diagnosis R12. `false` is Moveable's default (opposite-edge anchor) — confirmed in vendored bundle. |
| S3-6 | **R12 composes with R10 unchanged in CODE — but the doubled-dist semantics are explicit.** Under `fixedDirection:[0,0]`, Moveable's `Ra()` distance compute sets `b = 2/|direction − fixedDirection|`, so for an E-handle (`direction[0]=1`, `fixedDirection[0]=0`) `b[0] = 2/1 = 2`: `e.dist[0]` arrives **DOUBLED** (`2·Δcursor`) and `e.width = startWidth + 2·Δcursor`. The S3-1 write path (`flexBasis = beforeRect[axis] + e.dist[axis]`) is therefore **UNCHANGED in code** — `dist` arrives pre-doubled, so `beforeRect + dist` lands the dragged edge exactly under the cursor (1:1) while the box grows `2Δ` (Δ per side, the opposite edge mirrors). The write needs NO special-case math; the spec states the magnitude is `2Δ` (not `Δ`) so tests assert the right number. | AD3 "Composes with AD1's write path unchanged"; Risk-9; review F1 (`Ra` @150863 `b=2/m`). |
| S3-7 | **R11 equal-size candidate set = same-section visible siblings**, cached at `resizeStart` as `{width, height}` rendered dimensions, **EXCLUDING solver-derived flex-grow siblings of the resized element** (F5). "Same-section" = the elements returned by the existing `getElementGuidelines(el)` candidate set (siblings + parent + slide-root), filtered to those with a non-zero on-screen rect AND not excluded by the flex-grow-sibling rule below. Width and height cached independently. **Exclusion rule (precise):** drop any candidate `c` for which `c.parentElement === el.parentElement` (a sibling of the resized element under the SAME parent) AND that shared parent's computed `display` is `flex`/`inline-flex` AND `getComputedStyle(c).flexGrow` parses to a value `> 0`. Such a candidate's rendered width/height is the flex solver's grow-share output (not an author-set size), so it is not a meaningful equal-size target; same-parent flex siblings are already covered by *position* guides. Out-of-flow peers (`twin`-style: different parent, or `flex-grow:0`, or explicitly width/height-set) REMAIN candidates. The exclusion is evaluated per-candidate at cache time and applies to BOTH the width and height candidate sets. | AD4 "candidate dimensions cached at resizeStart (same-section visible elements, width+height)"; review F5 (phantom snap to grow-derived sibling widths). Reusing `getElementGuidelines` keeps one candidate-resolution path. |
| S3-8 | **R11 equal-size snap = 4px threshold on the target dimension**; when `|candidateTarget − matchedDim| ≤ 4`, the applied size is overridden to land EXACTLY on the matched dimension (the S3-1/S3-2 write uses the matched value instead of `beforeRect+dist`). Snap is evaluated per-axis, per-`onResize`. | AD4 "snap threshold 4px on the target dimension, snap overrides the applied size". |
| S3-9 | **R11 equal-size hint = a `hyp-`namespaced dashed-outline overlay** on the matched element + a small dimension badge showing the matched value (e.g. `392px`). Built as `hyp-`prefixed absolutely-positioned `<div>`s appended to the interaction wrapper; `pointer-events:none`. Torn down at `resizeEnd`. The `hyp-` namespace makes them serializer-exempt (stripped by the existing `hyp-` namespace strip). | AD4 hint spec + Risk-8. |
| S3-10 | **R13 = four undoable store ops** (`editComment`, `deleteComment`, `editReply`, `deleteReply`) in `comments.js`, each via `makeCommentCommand` (do/undo closures) → `writeIsland()` + marker update + `emit("dirty-changed")`. Edited items gain an `editedAt` ISO stamp. Panel affordances (Edit/Delete on root AND each reply) live in `main.js` `createThreadEl`. Editing reuses the anchored composer (`comment-composer.js`) in a new `edit` mode, pre-filled. | AD5; D3; diagnosis R13. |
| S3-11 | **R13 delete-reply undo restores at the ORIGINAL index** (`splice(i, 0, savedReply)`), not append; edit undo restores the EXACT prior body string + prior `editedAt`. Delete-root removes the marker and (if `agentInstruction`) drops from the agent block automatically (the thread is gone). | AD5 (ops round-trip and are undoable); Risk-5; diagnosis R13 undo notes. |
| S3-12 | **R13 island + head block regenerate automatically.** Every store mutation calls `writeIsland()`; the serializer reads the live store via `toJson`; `buildAgentBlock` rebuilds from the store on every serialize. NO extra block-sync wiring beyond the store mutation. An edited agent-tagged thread re-emits its new `instruction:` (and `editedAt`); a deleted agent thread vanishes. | AD5 "island + head agent block regenerate on save automatically"; diagnosis R13 island-sync. |
| S3-13 | **R14 stamping = transient live-stamp + strip-exempt-this-pass, NEVER index-based clone mapping** (AD6 satisfied: clone carries the stamp, live DOM is clean again before `serialize()` returns). The index-based `resolveCloneNode` is UNSOUND for stamping because it walks the POST-strip clone using LIVE `childNodes` indices, and `stripClone` removes body-appended `hyp-comment-marker`/`hyp-interaction-wrapper` nodes — desyncing the indices so a stamp lands on the wrong element or is dropped (review F3). Instead, in `serialize()`, BEFORE the clone is taken: (1) remove every existing `data-hyp-agent` from the LIVE DOM (clears any reopened-file or stale residue); (2) build `stampMap = agentStampMap()` and for each `[liveEl, ids]` set `liveEl.setAttribute("data-hyp-agent", ids.join(" "))` on the LIVE element; (3) clone; (4) run `stripClone` with `data-hyp-agent` EXEMPTED from the `data-hyp-*` strip for this pass (so the just-applied stamps survive into the clone); (5) in a `finally`, remove every `data-hyp-agent` from the LIVE DOM unconditionally — the live editing DOM ends each save with ZERO `data-hyp-agent` (history-safe, no residue between saves). Steps (1)+(2) normalize the live attribute set to exactly the current unresolved-thread ids, so the strip exemption is safe: only current stamps survive; resolved/deleted/stale ids were removed in (1) and never re-applied in (2). This sidesteps `resolveCloneNode` entirely. | AD6; review F3 (index-walk desync); Risk-3 (attributes are not nodes → guard-safe). |
| S3-14 | **R14 multiple agent threads on the SAME element = space-separated id list** in one `data-hyp-agent` attribute; each head-block entry's selector is `[data-hyp-agent~="<id>"]` (the CSS `~=` whitespace-token match). Single-thread elements get `[data-hyp-agent="<id>"]` (both forms resolve a single-id attribute identically). | AD6 (single attribute per element) + diagnosis Open-Q6 (the attribute-collision case the path-based block never had). `~=` keeps it a copy-pasteable one-liner. |
| S3-15 | **R14 head block format** (AD6) per agent thread: a `target:` line = the copy-pasteable selector, a `context:` line (tag + non-`hyp` classes + ≤80-char text excerpt), the `instruction:` line, `author:`/`date:` lines, and a one-time **self-cleanup directive** in the block preamble instructing the consuming agent to REMOVE the `data-hyp-agent` token for an id AND that id's block entry after applying its change. The runtime island anchor format (`thread.anchor`) is UNCHANGED. | AD6 full format; diagnosis R14 rewrite point (`buildAgentBlock` anchor line). |
| S3-16 | **R14 resolved/deleted threads do not stamp.** `buildAgentBlock` and the stamping pass both iterate `agentInstruction === true && resolved !== true`. A resolved or deleted thread is not in that set, so neither its block entry nor its attribute is emitted on the next save (D4 "attribute removed on save once resolved/deleted" — satisfied automatically because the clone is rebuilt each save and was never stamped for that thread). | AD6 "Resolved/deleted threads simply don't stamp on next save"; D4. |
| S3-17 | **All new tests use SYNTHETIC fixtures** (AD8). A new `tests/e2e/fixtures/` directory holds self-contained `.html` files; new tests write/serve them via the EXISTING dialog seam (`H.set_fake_dialog(base, path)` → `#open-btn`). NEVER reference `tecer-gsmm-introduction*.html`. The R10/R11/R12 synthetic fixture replicates the bug geometry: a `justify-content:center` flow row with a `flex-grow:1.4` accent item and a `flex-grow:1; flex-basis:0%` sibling. | AD8; harness convention (`conftest_helpers.py` `set_fake_dialog`/`open_via_dialog_ui`). |

---

## Synthetic fixtures (AD8 — binding; shared by R10/R11/R12 tests)

New tests do NOT load `H.FIXTURE` (the gitignored tecer client file). They serve self-contained synthetic HTML through the same fake-dialog seam. Add a helper and FOUR committed fixtures: `flow-grow.html` (R10 slack/amplification + R11 + R12), `flow-grow-deadzone.html` (R10 dead-zone red-first), `grid-healthy.html` (R10 healthy-grid regression), `agent-comments.html` (R13/R14).

### Helper (add to `conftest_helpers.py`)

```python
SYN_DIR = os.path.join(HERE, "fixtures")   # tests/e2e/fixtures/
def copy_synthetic(name):
    """Copy a synthetic fixture into a fresh tempdir; return the copy's path.
    Synthetic fixtures are fully self-contained (no external assets), so a
    tempdir copy serves correctly through the /doc/ route."""
    d = tempfile.mkdtemp()
    dst = os.path.join(d, name)
    shutil.copy(os.path.join(SYN_DIR, name), dst)
    return dst
```

A test opens it with the existing seam: `H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))`. The setUpClass fixture-existence guard checks `os.path.exists(os.path.join(H.SYN_DIR, name))` instead of `H.FIXTURE` (synthetic fixtures are committed, not gitignored).

### `tests/e2e/fixtures/flow-grow.html` (R10/R11/R12 — replicates the G0 bug geometry)

A minimal document whose flow row reproduces the diagnosis geometry (grow:1.4 accent, justify-center parent, grow:1 basis:0% sibling). Self-contained; no `data-hyp-*`, no inline `flex-basis` residue (the PRISTINE-equivalent). The accent item is the R10 target; the two flow-nodes are the equal-size candidates for R11.

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  body { margin: 0; font-family: sans-serif; }
  .slide { padding: 60px; }
  .flow-diagram { display: flex; flex-direction: row; justify-content: center;
                  align-items: stretch; gap: 10px; width: 1200px; }
  .flow-node { flex-grow: 1; flex-shrink: 1; flex-basis: 0%;
               background: #e5e7eb; padding: 24px; text-align: center; }
  .flow-node--accent { flex-grow: 1.4; flex-shrink: 1; flex-basis: 0%;
                       background: #c7d2fe; padding: 24px; text-align: center; }
  .sizing-twin { width: 300px; height: 120px; background: #fde68a; margin-top: 40px; }
</style></head><body>
  <section class="slide">
    <div class="flow-diagram">
      <div class="flow-node" id="node-a">estrutura</div>
      <div class="flow-node--accent" id="node-accent">A Tecer · estrutura·concilia·aprende</div>
      <div class="flow-node" id="node-b">aprende</div>
    </div>
    <div class="sizing-twin" id="twin">equal-size match target</div>
  </section>
</body></html>
```

Native ids (`node-accent`, `node-a`, `node-b`, `twin`) satisfy D14: tests select by clicking, then assert the runtime-selected hypId maps to the intended native-id element before any outcome assertion.

### `tests/e2e/fixtures/flow-grow-deadzone.html` (R10 dead-zone — TRUE red-first proof, F6)

The PRISTINE `flow-grow.html` accent (`grow:1.4` vs two `grow:1`, all `basis:0%`) takes only `1.4/3.4 ≈ 41%` of the row — it has slack in BOTH directions, so its FIRST gesture is the AMPLIFICATION regime, NOT the dead zone. The live dead-zone (R10b) required the accent to be the **dominant grower consuming ALL container leftovers** (live forensics: `flex-basis:1323px` inline + `grow:1.4`, rendered = leftovers, basis moves ±1px while rendered width is PINNED). This fixture reproduces that condition so E-R10-2/-2b go red on current master for the RIGHT reason (a genuine dead zone, not amplification-in-reverse). It seeds the accent with an inline `flex-basis` near the full row width (mirroring the live `1323px` residue) AND raises its grow so leftovers vanish.

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  body { margin: 0; font-family: sans-serif; }
  .slide { padding: 60px; }
  .flow-diagram { display: flex; flex-direction: row; justify-content: center;
                  align-items: stretch; gap: 10px; width: 1200px; }
  .flow-node { flex-grow: 1; flex-shrink: 1; flex-basis: 0%;
               background: #e5e7eb; padding: 24px; text-align: center; }
  .flow-node--accent { flex-grow: 8; flex-shrink: 1; flex-basis: 1100px;
                       background: #c7d2fe; padding: 24px; text-align: center; }
  .sizing-twin { width: 300px; height: 120px; background: #fde68a; margin-top: 40px; }
</style></head><body>
  <section class="slide">
    <div class="flow-diagram">
      <div class="flow-node" id="node-a">estrutura</div>
      <div class="flow-node--accent" id="node-accent" style="flex-basis: 1100px;">A Tecer · estrutura·concilia·aprende</div>
      <div class="flow-node" id="node-b">aprende</div>
    </div>
    <div class="sizing-twin" id="twin">equal-size match target</div>
  </section>
</body></html>
```

The accent's `flex-grow:8` (vs siblings `1`) gives it `8/10 = 80%` of free space, and the inline `flex-basis:1100px` (both in CSS and as an inline `style` attribute, mirroring the live residue) places its rendered width at the container leftover. On CURRENT master, `applyVisualResize` writes `flexBasis = e.width`; with the accent leftover-pinned, `e.width` barely changes and grow refills any basis decrease → **rendered width is PINNED** (the dead zone). The expected PRE-fix failing numbers (from `evidence-summary.md` §Gesture archetypes, G2/G3/G5/G8/G9): a −120 E-handle drag moves `flex-basis` by ±1px and leaves rendered width UNCHANGED (Δ ≈ 0), so the post-fix assertion `|Δrendered − (−120)| ≤ 2` FAILS on master by ≈120px — a true red-first proof of the dead zone.

### `tests/e2e/fixtures/agent-comments.html` (R13/R14 — comment + agent-block tests)

A minimal multi-element document (≥3 distinct text blocks with native ids and varied tags/classes) so agent comments anchor to distinguishable targets for the R14 fresh-agent legibility test.

```html
<!doctype html><html><head><meta charset="utf-8"></head><body>
  <section id="sec-ops"><h2 class="hd">Operações Financeiras Autônomas</h2>
    <p class="lead" id="p-lead">Plataforma inteligente para conciliação.</p></section>
  <section id="sec-arch"><h2 class="hd">Arquitetura</h2>
    <p class="body" id="p-arch">Componentes desacoplados e testáveis.</p></section>
  <ul id="list-x"><li class="item" id="li-1">estrutura</li>
    <li class="item" id="li-2">concilia</li></ul>
</body></html>
```

### `tests/e2e/fixtures/grid-healthy.html` (R10 healthy-grid path — E-R10-4/-5, AD8)

The healthy GRID path is the highest regression-risk surface (diagnosis Risk-2/Risk-7): the R10 fix must NOT touch the grid `else` branch. This committed fixture provides a grid-centered middle column (`#grid-mid`, mirrors live G6/G11) and a start-pinned grid column (`#grid-start`, mirrors live G12/G13) so E-R10-4/-5 run in CI without the gitignored tecer file. Native ids satisfy D14.

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  body { margin: 0; font-family: sans-serif; }
  .slide { padding: 60px; }
  .intro-grid { display: grid; grid-template-columns: 408px 606px 408px;
                gap: 10px; margin-bottom: 40px; }
  .intro-grid > div { background: #e5e7eb; padding: 24px; text-align: center; }
  .intro-grid > .mid { background: #c7d2fe; }
  .heard-grid { display: grid; grid-template-columns: 360px 360px;
                justify-items: normal; gap: 10px; }
  .heard-grid > div { background: #fde68a; padding: 24px; }
</style></head><body>
  <section class="slide">
    <div class="intro-grid">
      <div id="grid-left">estrutura</div>
      <div class="mid" id="grid-mid">A Tecer · plataforma central</div>
      <div id="grid-right">aprende</div>
    </div>
    <div class="heard-grid">
      <div id="grid-start">conciliação automática</div>
      <div id="grid-end">trilha de auditoria</div>
    </div>
  </section>
</body></html>
```

`#grid-mid` sits in the middle column (committed fixture uses FIXED-track columns by design — x stays pinned; stale Δ/2-shift prose corrected per v4-t2-review finding D); `#grid-start` is start-pinned (`justify-items:normal` → x pinned, one-sided). Both are plain grid children → `roleOf` resolves them to the `else`/block-grid branch (NOT `flex-child`), so the R10 write must leave inline `width` 1:1 and write NO `flex-basis`/`flex-grow`.

---

## R10 — Resize amplification fix (dragged edge tracks cursor 1:1 in every layout context)

### Requirement (trace: user-feedback.md S1/R10, D1)
> Slightly resizing the accent box resized it by MUCH more than the drag distance (slack regime); other gestures could not resize it at all (no-slack dead zone).

The dragged edge MUST track the cursor 1:1 on flex-grow items, in BOTH the slack (amplification) and no-slack (dead-zone) regimes, and on the corner (height axis), without touching the already-correct width/grid/absolute paths.

### Root cause (diagnosis — ground truth, do NOT re-derive)
`applyVisualResize`'s `flex-child` branch writes Moveable's requested rendered width directly into `flex-basis` (`el.style.flexBasis = width + "px"`). On a `flex-grow>0` item the browser re-enters the grow solver: in slack rows the basis re-inflates (G0: cursor +66 → basis +183 = 2.77×); in no-slack rows grow refills any basis change so the rendered edge never moves (G2–G10 dead zone). `e.width` itself is wrong for a grow item because the box and the handle are decoupled by the solver. The fix neutralizes grow on the resized axis and drives the basis from `beforeRect[axis] + e.dist[axis]` (`e.width === startWidth + e.dist[0]`).

**Anchor-relative `e.dist` (binding distinction for contracts 1–5 vs R12):** `e.dist[0]` is the bounding-box SIZE delta the dragged edge produced, scaled by Moveable's `b = 2/|direction − fixedDirection|` (`Ra` @150863). Under the **default** anchor (no Alt; `fixedDirection` = opposite edge, e.g. `[-1,0]` for an E-handle) `b[0] = 2/|1−(−1)| = 1`, so `e.dist[0] = Δcursor` exactly — the dragged edge tracks the cursor 1:1 and the opposite edge stays put. Under the **center** anchor (Alt held; `fixedDirection:[0,0]`, R12) `b[0] = 2/|1−0| = 2`, so `e.dist[0] = 2·Δcursor` — the dragged edge STILL tracks the cursor 1:1 but the opposite edge mirrors, so the box grows `2Δ`. **The `beforeRect + dist` write is identical in both cases** because `dist` is pre-scaled for the active anchor; the contracts below are stated for the DEFAULT anchor (R10 in isolation), and R12's contracts restate the doubled-width magnitude for the Alt case.

### Behavior contract (exact, testable)
1. **Slack-row 1:1 (kills amplification).** On the `flow-grow.html` accent item (`justify-center` parent, `flex-grow:1.4`), a real E-handle drag of +Δ px (Δ ≈ +60) lands the dragged (right) edge within **±2px of the cursor's net travel**: `|Δrendered_right_edge − Δcursor_x| ≤ 2`. The inline `flex-basis` after the gesture equals `beforeRect.width + Δcursor` within ±2px, and `flex-grow` is `0`.
2. **No-slack 1:1 (kills dead zone).** After the first gesture establishes `flex-grow:0`, a second E-handle drag of −Δ (Δ ≈ −120) shrinks the rendered width by `|Δ|` within **±2px** (`|Δrendered_width − Δcursor_x| ≤ 2`) — the element is no longer pinned to container leftovers. (Equivalently, on a fresh open the FIRST gesture already escapes the dead zone because the write neutralizes grow within that same `onResize` stream.)
3. **Corner / height axis (AD2).** A real NE-corner drag with pointer +ΔY (downward, north edge) shrinks `height` by min(ΔY, slack-to-content-floor) within **±3px** until the content-min floor; once at the floor, further downward travel produces no further height change (accepted clamp). Width axis on the same corner obeys contract 1/2.
4. **Healthy paths unchanged (AD1).** On a grid middle-column element, a start-pinned grid column, and a `repeat(3, minmax(0,1fr))` grid card, a real E-handle drag of Δ writes inline `width` = `prevWidth + Δ` within **±2px** and writes NO `flex-basis`/`flex-grow` — byte-identical behavior to pre-R10. On an `position:absolute` element the `width`/`height` + top/left edge-compensation path is unchanged.
5. **Undo restores all three flex longhands (AD1).** After any flex-grow resize, one `undo` restores `flex-basis`, `flex-grow`, `flex-shrink` to their EXACT pre-gesture inline values — including the absent-inline case (pre-gesture had none → post-undo has none; `getPropertyValue` returns `""`).

### Change map

| File → function | What changes |
|-----------------|--------------|
| `interaction.js` → `captureSizingState`, `role === "flex-child"` branch | ADD `m["flex-grow"] = s.getPropertyValue("flex-grow") \|\| ""` and `m["flex-shrink"] = s.getPropertyValue("flex-shrink") \|\| ""` alongside the existing `flex-basis`/`width`/`height` captures. (L1/S3-4.) |
| `interaction.js` → `onResize(e)` | Pass `e.dist` through: `applyVisualResize(el, roleOf(el), e.width, e.height, e.direction, e.dist)`. (L2/S3-3.) |
| `interaction.js` → `applyVisualResize(el, role, width, height, direction, dist)` | Gain `dist` param. Replace ONLY the `role === "flex-child" && parent` branch body with the verbatim two-branch block below; grow-neutralize the MAIN axis ONLY (never both axes); the CROSS axis stays a plain `width`/`height` write with NO `top`/`left` compensation (the flex item is in normal flow — Moveable's `fixedDirection` holds the opposite edge — so the absolute-branch top/left comp at `direction[*]===-1` must NOT be added here, G9). The `else` (block/grid) and `absolute` branches are UNTOUCHED — they keep consuming `width`/`height` (S3-3). **Verbatim replacement for the flex-child branch (transcribe exactly):** `const mainDim = isFlexRow ? "width" : "height"; const mainAxisIdx = isFlexRow ? 0 : 1; el.style.flexGrow = "0"; el.style.flexShrink = "0"; el.style.flexBasis = (beforeRect[mainDim] + dist[mainAxisIdx]) + "px"; if (isFlexRow) { el.style.height = (beforeRect.height + dist[1]) + "px"; } else { el.style.width = (beforeRect.width + dist[0]) + "px"; }` — note `beforeRect[mainDim]` uses the literal STRING key `"width"`/`"height"` (NOT the numeric index); `dist[mainAxisIdx]` uses the numeric index. (R11's equal-size override, when active, replaces the `(beforeRect[mainDim] + dist[mainAxisIdx])` term and the cross-axis term per S3-8 BEFORE the write — see R11 change map.) |
| `interaction.js` → `onResizeStart` | No change required (`beforeRect` already captured). Confirm `beforeRect` is read inside `applyVisualResize` via the module-level `beforeRect` (it is). |
| `commands.js` → `resize` | No change. `applyStyleMap` already restores `""`→`removeProperty` for the new longhands (S3-4). |

`dist` is `e.dist = [distWidth, distHeight]` per the diagnosis Moveable payload; `dist[0]` is the cursor-true x delta, `dist[1]` the y delta. For a W-handle (west) gesture, Moveable's `e.dist[0]` is already signed for the left-edge drag and `fixedDirection` holds the right edge, so `beforeRect.width + dist[0]` is correct without special-casing the handle.

### Edge cases

| Case | Required behavior |
|------|-------------------|
| **Overfull row (negative slack, shrink-active)** | The grow-neutralizing write still sets `flex-basis = beforeRect.width + dist[0]` and `flex-grow:0; flex-shrink:0`. With shrink also neutralized, the item holds the explicit basis; the dragged edge tracks the cursor 1:1 BOUNDED by the row's available width (if the requested basis exceeds what the row can show, the rendered edge clamps at the row bound — a bounded deviation, documented, not amplification). Contract-1 tolerance (±2px) applies up to the row bound. |
| **Element with existing inline `flex` shorthand** (e.g. `style="flex: 1.4 1 0%"`) | `captureSizingState` reads the LONGHANDS via `getPropertyValue("flex-grow")` etc., which resolve the shorthand to its computed longhand values — so undo captures the effective pre-gesture longhands. The do-write sets longhands (`flex-grow`/`flex-shrink`/`flex-basis`), which OVERRIDE the shorthand in the cascade (later-set longhands win over an earlier shorthand on the same `style`). Undo `removeProperty` on the three longhands then re-applies the captured longhand strings; the original shorthand declaration remains and re-takes effect. NOTE: if the original was `style="flex:1.4 1 0%"` (shorthand only, no longhands), capture returns the resolved longhand strings (`"1.4"`,`"1"`,`"0%"`), and undo re-sets them as longhands — visually identical, though the serialized form becomes longhands rather than the shorthand. This is accepted (cosmetic serialization difference, zero layout difference). |
| **Existing inline `flex-basis` residue** (the owner's living test file) | The do-write overwrites it with the dist-derived basis; capture preserves the residue for undo. New tests use the pristine `flow-grow.html` (no residue) per AD8. |
| **Undo then redo** | Redo re-runs `commands.resize.do()` → `applyStyleMap(after)` re-applies the three longhands; undo→redo→undo is idempotent (the captured `before`/`after` maps are fixed at gesture end). |
| **Corner at content-min floor** | Height clamps at the content floor (accepted, AD2). The captured `height` for undo is the pre-gesture inline height; undo restores it. |
| **W-handle (west) on accent** | Same write path; `e.dist[0]` is the cursor-true delta for the left edge; `fixedDirection` (default) holds the right edge. 1:1 within ±2px (mirrors contract 1/2). |

### Non-goals / bounded cases
- R10 does NOT change the cross-axis content-min floor behavior (AD2 — accepted).
- R10 does NOT force `position:absolute` (D1 — illegal). Only `width`/`height`/`flex-basis`/`flex-grow`/`flex-shrink`/grid tracks.
- R10 does NOT touch the grid-track, block-width, or absolute branches (S3-3).
- Bounded deviation in overfull rows (rendered edge clamps at the row bound) is documented, not a bug.

> **Owner-ack flag (G7) — `flex-shrink:0` is a spec-internal extension of D1.** D1's locked text enumerates `flex-grow` as editable but does NOT name `flex-shrink`. I1/S3-1 neutralize `flex-shrink` too, because the overfull-row 1:1 contract (edge-case table below) requires the item to hold its explicit basis rather than shrink-collapse. This is a defensible, layout-necessary extension (shrink neutralization is scoped to the resized main axis only, captured for undo per S3-4), but it is NOT in the locked D1 wording. If the owner rejects shrink neutralization, the fallback is `flex-grow:0 + flex-basis` only, accepting shrink-bounded deviation in overfull rows. Default: neutralize shrink (the write as specified).

### Risk notes (tied to diagnosis Q6 / Risks table)
| Change | Possible regression | Guard |
|--------|---------------------|-------|
| Writing `flex-grow:0` on resize | Undo leaves a mutated `flex-grow` → silent layout drift if not captured (Risk-2, highest-value hazard) | New test **G-R10-UNDO**: asserts all three longhands restored to pre-gesture inline values incl. absent-inline. |
| dist-based math in `applyVisualResize` | Could break the healthy width/grid path if the `else`/`absolute` branches are accidentally touched | New tests **E-R10-3/4/5** (healthy grid/block/absolute 1:1) + existing `test_r2_resize_real.py` (`.research-card` width path) MUST stay green. |
| Neutralizing `flex-shrink` | An item that relied on shrink to fit could overflow after resize | Bounded-deviation contract (overfull-row edge case) + the write is scoped to the resized main axis only. |

---

## R12 — Alt-held symmetric resize (explicit center-origin, any element)

### Requirement (trace: user-feedback.md S2/R12, D1)
> Center boxes grew to both sides (center fixed) while leftmost boxes grew one-sided — the user must have BOTH options, predictably, not as a layout accident.

Holding **Alt** during a resize MUST anchor the gesture at the element's CENTER (both edges move symmetrically) on ANY element. Without Alt, the default one-sided (opposite-edge-anchored) behavior holds; auto-centered elements still mirror without Alt (honest layout, D1 — no compensation CSS).

### Root cause / mechanism (diagnosis — ground truth)
Moveable's `fixedDirection` is the resize-anchor primitive. Default `fixedDirection` is the edge OPPOSITE the dragged handle (one-sided growth). Setting `fixedDirection:[0,0]` pins the CENTER → symmetric. Moveable snapshots `fixedDirection` at resizeStart (`startFixedDirection`), so the assignment is start-only.

### Behavior contract (exact, testable)
1. **Alt-held symmetric on a non-centered element — dragged edge tracks the cursor 1:1, opposite edge mirrors, width grows 2Δ.** On a start-pinned element (e.g. a `flex-grow:0` item, or the `twin` after R10 establishes an explicit width), an E-handle drag of +Δ with `Alt` held moves the **dragged (right) edge to track the cursor 1:1** — `|ΔrightEdge − Δcursor| ≤ 3` (HEADLINE assertion: the dragged edge follows the pointer exactly, the property D1 mandates) — AND **mirrors the left edge by the same Δ** in the opposite direction (`|ΔleftEdge − Δcursor| ≤ 3`, i.e. the left edge moves LEFT by ≈Δ). The element's **width therefore increases by ≈2Δ** (`|Δwidth − 2·Δcursor| ≤ 3`). This is the honest native center-resize behavior (PowerPoint semantics): `fixedDirection:[0,0]` pins the center, so `e.dist` doubles (S3-6, `Ra` `b=2`) and `beforeRect+dist` lands the dragged edge under the cursor while the box expands symmetrically.
2. **No-Alt one-sided unchanged.** The SAME gesture WITHOUT Alt moves only the dragged (right) edge by Δ 1:1 (`|ΔrightEdge − Δcursor| ≤ 2`); the left edge is fixed (`|ΔleftEdge| ≤ 2`); width grows by Δ (not 2Δ).
3. **Start-only semantics (AD3).** Pressing or releasing Alt MID-gesture does not change the anchor for that gesture (Moveable read `fixedDirection` at resizeStart). Documented; not separately asserted beyond contract 1/2.
4. **Composes with R10 (S3-6).** On the `flow-grow.html` accent item, an Alt-held E-handle drag of +Δ still moves the dragged (right) edge to track the cursor 1:1 (`|ΔrightEdge − Δcursor| ≤ 3`) AND mirrors the left edge by Δ, so the rendered **width grows by ≈2Δ** (`|Δwidth − 2·Δcursor| ≤ 3`) — the basis-from-`beforeRect+dist` write is anchor-agnostic because `e.dist` arrives pre-doubled for the center anchor. `flex-grow` remains neutralized (R10 write intact). The R10 dist-write needs NO special-case math under Alt (S3-6).
5. **Auto-centered without Alt (D1).** A grid-centered or `justify-center` element grows both sides WITHOUT Alt (honest layout). NO compensation CSS is added to "fix" this. Alt adds explicit center-origin ON TOP for non-auto-centered elements.

### Change map

| File → function | What changes |
|-----------------|--------------|
| `interaction.js` → `onResizeStart(e)` | After the existing capture block, read Alt and set the gesture anchor: `if (moveable) { moveable.fixedDirection = (e.inputEvent && e.inputEvent.altKey) ? [0, 0] : false; }`. (S3-5; `false` = Moveable's default opposite-edge anchor.) |
| `interaction.js` → `onResizeEnd()` | After the existing commit/cleanup, restore the default: `if (moveable) moveable.fixedDirection = false;` so the NEXT gesture starts from the default unless Alt re-sets it. **The reset MUST run even if `onResize` threw mid-gesture (G10):** if any earlier step in `onResizeEnd` (or a prior `onResize`) can throw on a detached/invalid element, place this reset FIRST in `onResizeEnd` (before the `byId(activeHypId)` early-return path) OR in a `finally`, so a thrown gesture cannot leave `fixedDirection:[0,0]` stuck — which would silently make every subsequent gesture symmetric. Concretely: move the `moveable.fixedDirection = false` assignment ABOVE the existing `const el = byId(activeHypId); if (!el) { beforeSizing = null; beforeRect = null; return; }` guard so the early-return cannot skip it. |
| `interaction.js` → `applyVisualResize` | NO change for R12 (S3-6). |

`moveable` is the module-level `let`; both handlers run with it in scope. `e.inputEvent` is the native pointer event Moveable forwards (the same object `onDrag` already reads for `clientX`).

### Edge cases

| Case | Required behavior |
|------|-------------------|
| **Alt held on an auto-centered element** | `fixedDirection:[0,0]` and the element's own centering both push both edges; the net effect is still symmetric (no double-compensation — `fixedDirection` governs Moveable's frame math, the layout governs final rendered position; for a centered flex item the result remains symmetric). Accepted; D1-honest. |
| **Alt held on a corner handle** | `fixedDirection:[0,0]` pins the center on BOTH axes → symmetric in width and height simultaneously. The R10 dist-based width + plain-height writes apply per-axis unchanged. |
| **Alt released before resizeEnd** | The gesture keeps its start anchor (start-only). `onResizeEnd` then resets to `false`. |
| **Alt + Moveable's own key handling** | The explicit `fixedDirection` assignment is deterministic and version-safe; it does not depend on Moveable internally consuming Alt. No collision (diagnosis confirmed Moveable does not separately consume Alt in this config). The `history.js` keydown handler only fires on Ctrl/Meta, never Alt — no collision (Risk-4). |

### Non-goals / bounded cases
- R12 does NOT hand-roll symmetric delta math in `applyVisualResize` (would entangle R10's fix surface — diagnosis explicitly rejects this).
- R12 does NOT add compensation CSS for auto-centered elements (D1, Risk-10).
- R12 does NOT add a mid-gesture Alt toggle (start-only, AD3).

### Risk notes (tied to diagnosis Q6)
| Change | Possible regression | Guard |
|--------|---------------------|-------|
| Setting `moveable.fixedDirection` per gesture | If not reset at `resizeEnd`, a one-time Alt gesture would make ALL subsequent gestures symmetric | `onResizeEnd` resets to `false`; new test **E-R12-3** does a non-Alt gesture AFTER an Alt gesture and asserts one-sided. |
| Reading `e.inputEvent.altKey` | Could be undefined on synthetic events | Guarded with `e.inputEvent &&`; real Playwright `keyboard.down('Alt')` + mouse drag exercises the real path. |
| R12 × R10 coupling | The dist-based mapping could misbehave under a center anchor | **E-R12-4** runs Alt on the `flow-grow.html` accent and asserts both R10-1:1 (dragged edge) AND symmetry; sequencing (R10 verified before R12) per AD7. |

---

## R11 — Resize guides: move-parity alignment lines + equal-size matching

### Requirement (trace: user-feedback.md S3/R11, D2)
> Guide/snap lines (like move) do not appear when resizing; elements can't be matched to nearby sizes. README claims move-parity guides during resize.

(a) Position-snap alignment guides (sibling edges/centers, slide bounds) MUST fire during resize on a flex-grow element post-R10. (b) NET-NEW equal-size matching: when the resized dimension comes within 4px of a same-section visible element's dimension, snap to it exactly and show a visual hint.

### Root cause / finding (diagnosis — ground truth)
Position-snap resize guides are ALREADY wired (`snappable:true` + `elementGuidelines`) and fire on the healthy path (`test_resize_shows_guidelines` asserts it). The owner saw zero guides because the accent node's edges never moved (R10 dead zone) — no edge approached a guideline. **Fixing R10 makes the existing position guides appear on the flex node for free.** Equal-size matching has no native Moveable support (no size-equality snap in v0.53.0) and is the only net-new wiring.

### Behavior contract (exact, testable)
1. **(a) Position guides fire post-R10 (verification).** On the `flow-grow.html` accent item, a real E-handle drag (now that R10 makes the edge move) renders at least one `.moveable-line` during the gesture (`doc.querySelectorAll('.moveable-line').length >= 1` mid-drag), AND the rendered width changes by >2px. (Mirrors `test_resize_shows_guidelines` but on the flex-grow element that previously showed none.)
2. **(b) Equal-size snap.** With `flow-grow.html` modified so the `twin` is **width 300px** and the accent's pre-gesture width is, say, 280px: dragging the accent's E-handle to grow it toward 300px snaps the accent's width to EXACTLY the twin's width (300px) when the candidate target lands within 4px (`|accentWidth − twinWidth| ≤ 0.5` after snap, i.e. it lands ON the value, not merely within 4). Without the equal-size feature the accent would land at the raw cursor value; WITH it, it lands at the matched dimension.
3. **(b) Equal-size hint.** During a gesture where an equal-size snap is active, a `hyp-`namespaced dashed-outline overlay element exists over the matched element (`doc.querySelectorAll('[class*="hyp-size-hint"]').length >= 1`) AND a badge shows the matched value. The overlay is `pointer-events:none`. At `resizeEnd` the overlay is REMOVED (`length === 0`).
4. **(b) Serializer-exempt.** After a save following an equal-size gesture, the saved HTML contains NO `hyp-size-hint` class and NO equal-size overlay node (the existing `hyp-` namespace strip removes it; teardown at resizeEnd already removed it from the live DOM).
5. **No healthy-path regression.** `test_resize_shows_guidelines` (on `.research-card`) stays green — position-snap guides on the width path are unaffected.

### Change map

| File → function | What changes |
|-----------------|--------------|
| `interaction.js` → `onResizeStart` | Cache equal-size candidates: build `sizeCandidates = getElementGuidelines(el).map(c => { const r = c.getBoundingClientRect(); return { el: c, width: r.width, height: r.height }; }).filter(c => c.width > 0 && c.height > 0)` into a module-level `let sizeCandidates`. (S3-7.) |
| `interaction.js` → `applyVisualResize` (or a helper called from `onResize` BEFORE the write) | After computing the dist-based target for each axis, run equal-size matching: for the resized main dimension `t`, find the nearest `sizeCandidates[i].<dim>` with `|t − cand| ≤ 4`; if found, OVERRIDE `t := cand` and record `{matchEl, dim, value}` for the hint. Apply the (possibly overridden) `t` in the existing write. (S3-8.) Equal-size evaluated per-axis. |
| `interaction.js` → new `showSizeHint(matchEl, value)` / `clearSizeHint()` | `showSizeHint`: create (once per gesture) a `hyp-size-hint` outline `<div>` positioned over `matchEl.getBoundingClientRect()` (absolute, `pointer-events:none`, dashed border) + a `hyp-size-hint-badge` child showing `Math.round(value)+"px"`, appended to `wrapper`. **Position MUST add the scroll offset (G5):** the wrapper is `position:absolute; top:0; left:0` spanning `scrollWidth×scrollHeight` (document-relative origin), but `getBoundingClientRect()` is viewport-relative — so set `left = rect.left + window.scrollX` and `top = rect.top + window.scrollY` (mirror `positionMarker` in `comments.js`, which adds `scrollX/scrollY`). Without this the hint floats to the wrong place on a scrolled deck. `clearSizeHint`: remove both. Both `hyp-`namespaced (S3-9). |
| `interaction.js` → `onResize` | After applying the write, call `showSizeHint(matchEl, value)` (with the recorded match) when a match is active, else `clearSizeHint()`. |
| `interaction.js` → `onResizeEnd` + `teardown` | Call `clearSizeHint()` and null `sizeCandidates` (S3-9 teardown). |
| Position guides | NO code change (L4 — already wired; R10 makes edges move). |

### Edge cases

| Case | Required behavior |
|------|-------------------|
| **Sibling reflow during flex resize** (cached rects go stale) | Candidates are cached at `resizeStart` (S3-7). For a resize that reflows siblings, the cached dims are the pre-gesture rendered dims — the intended match target. Accepted; if staleness proves visible, the diagnosis-noted optional `refresh:true` on guideline entries is a follow-up, not in R11 scope. |
| **Two candidates within 4px** | Snap to the NEAREST (smallest `|t − cand|`); ties resolve to the first in candidate order. |
| **Equal-size match coincides with a position-snap** | Both can render (position `.moveable-line` from Moveable + the custom `hyp-size-hint`); the equal-size override wins on the applied dimension (S3-8 "snap overrides the applied size"). |
| **Match on the cross axis (height)** | Same logic per-axis; the height write uses the matched height. |
| **Alt-held (R12) + equal-size** | Equal-size overrides the dragged-edge target; with `fixedDirection:[0,0]` the symmetric frame uses the overridden size. Compatible. |
| **No candidates (single element in section)** | `sizeCandidates` empty → no equal-size snap, position guides still fire. |

### Non-goals / bounded cases
- R11(a) adds NO new snap config — it is a verification that R10 restored the existing guides (L4).
- R11 does NOT snap to arbitrary sizes — only to same-section visible candidate dimensions (S3-7).
- R11 does NOT use Moveable for the size-equality line (none exists) — it is a custom `hyp-` overlay (S3-9).
- Stale-rect refresh on heavy reflow is out of scope (follow-up).

### Risk notes (tied to diagnosis Q6)
| Change | Possible regression | Guard |
|--------|---------------------|-------|
| Custom `hyp-size-hint` overlay | Could leak into the saved file or block handles | `hyp-` namespace (serializer strips it) + `pointer-events:none` + `clearSizeHint` at resizeEnd/teardown. Test **E-R11-4** saves after an equal-size gesture and asserts no `hyp-size-hint` in output (Risk-8). |
| Equal-size override of the applied size | Could fight R10's 1:1 contract | Override only fires within 4px of a candidate; outside that band R10's 1:1 holds. Test **E-R11-2** asserts the snap lands ON the value; **E-R10** tests run on geometry with NO equal-size candidate in range so 1:1 is unperturbed. |
| Caching candidate rects | Stale rects could mis-snap | Cached at resizeStart (intended target); bounded to same-section visible set. |

---

## R13 — Comment edit + delete (comments & replies), island + agent-block sync

### Requirement (trace: user-feedback.md S5/R13, D3)
> Once posted, a comment cannot be edited. Owner wants edit AND delete, for root comments AND replies; edits propagate to the saved JSON island and the agent `<head>` block when agent-tagged.

### Finding (diagnosis — ground truth)
No edit/delete op exists anywhere (store, panel, bridge, composer are add/reply/resolve-only). R13 is a clean addition mirroring the existing `reply`/`resolve` undoable-command pattern across 4 layers.

### Behavior contract (exact, testable)
1. **Edit root comment.** Editing a root comment's body to new text `T` updates `thread.body = T`, sets `thread.editedAt` (ISO), persists to the island (`writeIsland`), and re-renders the panel body to `T`. One undoable history entry.
2. **Delete root comment.** Deleting a root comment removes it from `threadStore`, removes its marker, persists, and removes its panel entry. If it was the LAST thread, the island is suppressed on next save (per existing `getCommentJson` empty-store rule). One undoable entry.
3. **Edit reply.** Editing reply at index `i` updates `thread.replies[i].body = T` and `thread.replies[i].editedAt`, persists, re-renders that reply. One undoable entry.
4. **Delete reply.** Deleting reply at index `i` removes `thread.replies[i]`, persists, re-renders, and the marker count decrements (`1 + replies.length`). One undoable entry.
5. **Undo fidelity (S3-11).** Undo of edit restores the EXACT prior body string AND prior `editedAt` (or its absence). Undo of delete-reply restores the reply at its ORIGINAL index (`splice(i,0,saved)`). Undo of delete-root restores the thread (marker re-renders). Thread/reply counts return exactly to pre-op.
6. **Agent-block sync (S3-12).** Editing an agent-tagged root comment's body changes its `instruction:` line on the NEXT save; deleting it drops its entire block entry. Editing/deleting a reply changes/drops its `reply:` line. No extra wiring — `buildAgentBlock` rebuilds from the store.
7. **Edit composer prefill.** Clicking Edit opens the anchored composer (`comment-composer.js`) in `edit` mode with the textarea PRE-FILLED with the current body; saving submits the new text; the For-agents checkbox is HIDDEN in edit mode (Risk-12).

### Change map

| File → function | What changes |
|-----------------|--------------|
| `comments.js` → NEW `editComment(commentId, newBody)` | Find thread; capture `before = {body: thread.body, editedAt: thread.editedAt}`; `makeCommentCommand("edit-comment", do, undo)`; `do`: `thread.body = newBody; thread.editedAt = new Date().toISOString(); writeIsland(); updateMarkerState(commentId); emit("dirty-changed",{dirty:true})`; `undo`: `thread.body = before.body;` then **`if (before.editedAt === undefined) delete thread.editedAt; else thread.editedAt = before.editedAt;`** (G4 — DELETE the key when it was absent pre-edit; do NOT set it to `undefined`, which would leave a stale in-memory key that a later `toJson` consumer could read), `writeIsland()`, `updateMarkerState`, emit. `historyPush`. Return `{commentId}`. |
| `comments.js` → NEW `deleteComment(commentId)` | Capture the thread object + its index; `do`: `removeMarker(id); threadStore.splice(idx,1); writeIsland(); emit`; `undo`: `threadStore.splice(idx,0,saved); writeIsland(); reanchorAll()` (re-renders the marker); emit. `historyPush`. |
| `comments.js` → NEW `editReply(commentId, replyIndex, newBody)` | Capture `before = {...thread.replies[replyIndex]}`; `do`: set `replies[replyIndex].body = newBody`, `.editedAt = ISO`, `writeIsland()`, `updateMarkerState`, emit; `undo`: `replies[replyIndex] = before`, persist, emit. `historyPush`. |
| `comments.js` → NEW `deleteReply(commentId, replyIndex)` | Capture `saved = thread.replies[replyIndex]` + index; `do`: `replies.splice(replyIndex,1)`, persist, `updateMarkerState`, emit; `undo`: `replies.splice(replyIndex,0,saved)` (S3-11 index-safe), persist, `updateMarkerState`, emit. `historyPush`. |
| `comments.js` → `writeIsland` + `toJson` | ADD `editedAt: t.editedAt` to the persisted/serialized field set (so the stamp round-trips). Replies persist verbatim (already a passthrough) — `editedAt` on a reply rides along. |
| `comments.js` → `buildAgentBlock` | No structural change for R13 (it already emits `instruction:` from `t.body` and `reply:` from `r.body`). Edits/deletes flow through automatically. (R14 rewrites the anchor line — separate.) |
| `runtime-main.js` → boot | Register four commands next to `reply-comment`: `edit-comment {commentId, body}` → `editComment`; `delete-comment {commentId}` → `deleteComment`; `edit-reply {commentId, replyIndex, body}` → `editReply`; `delete-reply {commentId, replyIndex}` → `deleteReply`. Import the four new fns from `comments.js`. Each validates ONLY the fields listed in its payload and throws on missing — **edit/delete validators MUST NOT require `author`** (G3): `edit-comment` requires `{commentId, body}`; `delete-comment` requires `{commentId}`; `edit-reply` requires `{commentId, replyIndex, body}`; `delete-reply` requires `{commentId, replyIndex}`. Do NOT copy the `!payload.author` check from the `reply-comment`/`add-comment` validators — the composer edit-mode `onSubmit(text)` passes no author, so an `author` requirement would break every edit. (`replyIndex` is validated as a number, including `0` — use `typeof payload.replyIndex !== "number"`, NOT a falsy check, or index 0 throws.) |
| `app/js/main.js` → `createThreadEl` | On the ROOT actions row (near Reply/Resolve): add an **Edit** button → opens composer `mode:'edit'`, `initialText: thread.body`, `onSubmit:(text)=> bridge.command("edit-comment",{commentId:thread.id, body:text}) then refreshCommentPanel()`; add a **Delete** button → `bridge.command("delete-comment",{commentId:thread.id})` then `refreshCommentPanel()`. Inside the replies loop: per reply, add **Edit**/**Delete** buttons wired to `edit-reply`/`delete-reply` with that reply's index. All buttons `e.stopPropagation()`. |
| `app/js/shell/comment-composer.js` → `openComposer` | Accept `mode:'edit'` + `initialText`. When `mode==='edit'`: set `textarea.value = initialText` (prefill); HIDE the For-agents checkbox (only built for `mode==='new'` — extend the guard to `mode==='new'` only, already the case); set the textarea placeholder to the string `Edit comment`. `submit()` calls `onSubmit(text)` (agent arg irrelevant in edit). |

### Edge cases

| Case | Required behavior |
|------|-------------------|
| **Comment-edit on an agent-tagged thread** | Edit changes `thread.body`; on next save `buildAgentBlock` emits the new `instruction:` line (and R14 re-stamps the still-unresolved thread). No extra wiring (S3-12). |
| **Delete an agent-tagged root** | Thread removed from store → `buildAgentBlock` (filters `agentInstruction && !resolved`) no longer includes it → block entry gone; R14 stamping (iterates the same set) does not stamp it → no `data-hyp-agent` residue. |
| **Delete-reply undo index** | `splice(i,0,saved)` restores at the original ordinal so the agent-block `reply:` order is preserved (Risk-5). |
| **Edit to empty/whitespace** | Composer `submit()` already no-ops on empty (`if (!text) { closeActive(); return; }`) — an empty edit closes without mutating. Documented: empty edit = cancel. |
| **Edit then undo then redo** | Redo re-runs `do()` → re-applies `newBody`+a NEW `editedAt` timestamp (redo re-stamps). Accepted: `editedAt` reflects the most recent application time; body content is deterministic. |
| **Composer edit-mode does not regress new/reply flip-clamp** | The viewport flip/clamp (D12) is independent of `mode`; edit mode uses the same positioning. For-agents checkbox absent in edit (Risk-12). |
| **Reply index shifts after a sibling delete** | The panel re-renders after every op (`refreshCommentPanel`), so reply buttons always carry current indices; an op uses the index from the just-rendered panel. No stale-index op possible within a single render generation. |

### Non-goals / bounded cases
- R13 does NOT add a separate `comment-panel.js` module (the panel lives in `main.js` — AD5).
- R13 does NOT change the resolve/reopen or tag-agent ops.
- R13 does NOT add inline (non-composer) editing — edit reuses the anchored composer (AD5).
- Empty edit = cancel (no destructive clear).

### Risk notes (tied to diagnosis Q6)
| Change | Possible regression | Guard |
|--------|---------------------|-------|
| Composer `edit` mode | Could break `new`/`reply` flip-clamp or the For-agents checkbox | **E-R13-7** opens edit on a low anchor and asserts the composer stays in-viewport; checkbox absent in edit (Risk-12). |
| Four new undoable ops | Delete-reply undo could append instead of insert-at-index | **E-R13-5** deletes the FIRST of two replies, undoes, asserts order restored (Risk-5). |
| `editedAt` added to persisted fields | Could change island shape and break `test_g2`/`test_f5` assertions | `editedAt` is additive (extra key); existing tests assert presence of keys, not absence of new ones — re-run to confirm green (Risk-6). |

---

## R14 — Agent-anchor robustness: `data-hyp-agent` stamping + rewritten head block + fresh-agent legibility

### Requirement (trace: user-feedback.md S4/R14, D4)
> Doubt whether an agent can reliably resolve WHICH element a comment targets. The current anchor line uses an undefined structural path that goes stale after the agent's first edit.

The saved file MUST stamp `data-hyp-agent="<id>"` on each unresolved agent-tagged element, and the `<head>` block MUST reference it via a copy-pasteable attribute selector with a self-cleanup directive. Resolved/deleted threads don't stamp.

### Finding (diagnosis — ground truth)
`data-hyp-agent` does not exist; `stripClone` removes every `data-hyp-*`; the block emits a stale `buildPath`. The fix is a transient live-stamp (stamp the live element by `matchAnchor` identity BEFORE cloning, exempt `data-hyp-agent` from the strip for that pass, unstamp the live DOM in a `finally`) + a rewritten anchor line (S3-13). The index-based `resolveCloneNode` is NOT used for stamping — it desyncs against the strip's removal of body-appended `hyp-` chrome (review F3).

### Behavior contract (exact, testable)
1. **Stamping presence.** After saving a file with N unresolved agent-tagged threads, the saved HTML contains exactly N `data-hyp-agent` ATTRIBUTE occurrences-worth of ids (one attribute per distinct anchored element; an element with k unresolved agent threads carries a k-id space-separated value). Each thread id appears in exactly one element's `data-hyp-agent` value.
2. **Selector resolution.** For each agent thread, the head block's `target:` line is a string of the form `[data-hyp-agent~="<id>"]` (or `[data-hyp-agent="<id>"]` for a single-id element — both resolve the same element). Loading the saved file and running `document.querySelector(target)` returns exactly one element, and it is the element the comment was anchored to (verified by its native id / text in the synthetic fixture).
3. **Block format (S3-15).** Each entry contains, in order: `[agent:<id>]`, `target: <selector>`, `context: <tag> .<classes> | "<≤80-char excerpt>"`, `instruction: <body>`, optional `reply: <body> — <author>` lines (one per reply), `author: <name>`, `date: <ISO>`. The block preamble contains a self-cleanup directive instructing the consuming agent to remove the `data-hyp-agent` token for an id and that id's entry after applying the change.
4. **Live DOM clean after each save (S3-13).** After a save returns, the LIVE iframe document has NO `data-hyp-agent` attribute — the `serialize()` `finally` removes the transient live-stamp. (The stamp exists on the live DOM only momentarily, between stamping and the `finally`, and is never observable to a test that probes after the save completes.) Asserted: `doc.querySelectorAll('[data-hyp-agent]').length === 0` after a save.
5. **Resolved/deleted don't stamp (S3-16).** After resolving (or deleting) an agent thread and saving, the saved HTML contains NO `data-hyp-agent` for that thread's id AND no block entry for it.
6. **Stamping idempotence across saves.** Saving the SAME file twice (open → save → reopen the saved file → save again) yields the SAME stamping (one `data-hyp-agent` per element, one block entry per unresolved thread) with NO duplication and NO accumulation of attributes. On the resave, the reopened file's prior `data-hyp-agent` is present on the live DOM as a plain attribute; `serialize()` step (1) removes every live `data-hyp-agent` BEFORE cloning, and step (2) re-applies only current-unresolved ids from `agentStampMap` (the island id is stable, so the same id re-derives). No stale id survives into the clone.
7. **Node-count guard safe.** Stamping sets ATTRIBUTES, not nodes; `countAllNodes` counts nodes, so the serializer guard is unaffected (Risk-3). Save succeeds (no guard abort).
8. **Runtime island unchanged.** `thread.anchor` (the runtime anchor format) is NOT changed; re-anchoring on reopen still works via `matchAnchor`.

### Change map

| File → function | What changes |
|-----------------|--------------|
| `comments.js` → `buildAgentBlock` | Rewrite the per-thread anchor line. Replace the `anchor: ${path} | id="${nid}" | "${ctx}"` line with TWO lines: `target: [data-hyp-agent~="${escapeAgentBlock(t.id)}"]` and `context: ${escapeAgentBlock(tagAndClasses)} | "${ctx}"` where `tagAndClasses` is the thread's anchored element tag + non-`hyp` class tokens (resolve via `matchAnchor(t.anchor)`; if unresolved, emit `context: (unresolved) | "${ctx}"`). Update the preamble to add the self-cleanup directive (S3-15). All interpolations pass through `escapeAgentBlock`. `buildPath`/`anchor.path` are no longer emitted (kept in the store for `matchAnchor`). |
| `comments.js` → NEW exported helper `agentStampMap()` | Returns `Map<Element, string[]>`: for each thread with `agentInstruction===true && resolved!==true`, resolve `el = matchAnchor(t.anchor)`; if `el`, push `t.id` into the map entry for `el`. (Used by the serializer to know which LIVE elements to stamp with which ids.) Resolved/deleted/unanchored threads contribute nothing (S3-16). **High-confidence-only stamp (G6):** `matchAnchor` may return a FUZZY match (its level-4 same-parent scan or level-5 relaxed tail) that could be a wrong sibling with colliding content. `agentStampMap` MUST stamp ONLY on a high-confidence resolution — re-run the anchor resolution and accept the element ONLY if it matches via level 1 (unique `data-hyp-hook`) or level 2 (`nativeId`+path walk with `contentHash` equality); if resolution falls through to level 3/4/5, treat the thread as unanchored for stamping purposes (contribute nothing → no stamp; the block still emits its `context:` excerpt as the human fallback per S3-15). This prevents a fuzzy re-resolution from stamping the wrong element. |
| `serializer.js` → `serialize()` | Wrap the stamping in a try/finally around the clone+strip so the live DOM is restored even on error. The exact sequence (S3-13): `const stampMap = comments.agentStampMap();` then **BEFORE** `const clone = document.documentElement.cloneNode(true);`: (1) `for (const el of document.querySelectorAll("[data-hyp-agent]")) el.removeAttribute("data-hyp-agent");` (clear stale/reopened residue); (2) `for (const [liveEl, ids] of stampMap) liveEl.setAttribute("data-hyp-agent", ids.join(" "));` Then clone, then `stripClone(clone)` (which preserves `data-hyp-agent` via the exemption below). In a `finally` that wraps everything from step (1) onward: `for (const el of document.querySelectorAll("[data-hyp-agent]")) el.removeAttribute("data-hyp-agent");` so the LIVE DOM ends with ZERO `data-hyp-agent`. Import `agentStampMap` from `comments.js`. The node-count guard is computed on the clone AFTER stamping; attributes are not nodes, so `preCount`/`postCount` are unaffected (Risk-3). |
| `serializer.js` → `stripClone` | EXEMPT `data-hyp-agent` from the `data-hyp-*` removal loop in Phase B: change the attribute-removal test from `if (attr.name.startsWith("data-hyp-"))` to `if (attr.name.startsWith("data-hyp-") && attr.name !== "data-hyp-agent")`. The exemption is SAFE because `serialize()` step (1) cleared all live `data-hyp-agent` and step (2) re-applied only current-unresolved-thread ids, so the only `data-hyp-agent` present on the clone are the just-applied current stamps. A reopened file's prior `data-hyp-agent` is cleared by step (1) BEFORE the clone is taken, so it never reaches the clone (S3-16 idempotence holds: stale ids cannot survive). `stripIds`/`data-hyp-id` removal is UNCHANGED. |

The live-stamp (serialize steps 1–2) runs BEFORE `cloneNode`, so the clone carries the stamps; `stripClone` preserves them via the `data-hyp-agent` exemption; the `finally` unstamp restores a clean live DOM. The agent-block insertion (`insertAdjacentHTML` into `<head>`) is UNCHANGED and runs after the clone+strip; the block's `target:` selectors match the stamped clone attributes. The node-count guard is unaffected (attributes are not nodes).

### Edge cases

| Case | Required behavior |
|------|-------------------|
| **Two unresolved agent threads on the SAME element (S3-14)** | `agentStampMap` collects both ids under that element → `data-hyp-agent="id1 id2"`. Each block entry uses `[data-hyp-agent~="idN"]` (whitespace-token match) → each resolves the shared element. No collision. |
| **Agent thread whose anchor no longer resolves (unanchored)** | `matchAnchor` returns null → not added to `agentStampMap` → no stamp. The block entry still emits with `context: (unresolved)` so a human can locate it, but `target:` is a selector that matches nothing (documented: unanchored agent threads cannot be auto-stamped — the consuming agent falls back to the context excerpt). |
| **Stamping idempotence across multiple saves (S3-16)** | `serialize()` step (1) clears every live `data-hyp-agent` (including a reopened file's prior stamp) BEFORE cloning, then step (2) re-applies only current-unresolved ids from `agentStampMap`. So a stale id is gone before the clone is taken and is never re-applied. No accumulation. Asserted by **E-R14-6**. |
| **Edit/delete of an agent thread between saves (R13×R14)** | Edited thread re-stamps (still unresolved) with its new `instruction:`; deleted/resolved thread drops from `agentStampMap` and the block (S3-16). |
| **Comment text containing `-->`** | `escapeAgentBlock` wraps every interpolation incl. the id, selector, context, and instruction (the existing discipline extends to the new lines). |
| **Live DOM residue** | None — the `serialize()` `finally` removes every `data-hyp-agent` from the LIVE DOM after each save (the live-stamp is transient, present only between step 2 and the `finally`). Asserted by **E-R14-4** (`[data-hyp-agent]` count === 0 live after save). |
| **Node-count guard** | Attributes are not nodes; `expectedPostCount` unchanged; save succeeds (Risk-3). |

### Non-goals / bounded cases
- R14 stamps the LIVE DOM only TRANSIENTLY (between `serialize()` steps 2 and the `finally`); the live editing DOM is history-safe and carries ZERO `data-hyp-agent` between saves. The stamp survives into the SAVED clone, never into the persistent live DOM.
- R14 exempts `data-hyp-agent` from the strip FOR THE SERIALIZE PASS ONLY; the exemption is safe because the live attribute set is normalized to current ids immediately before the clone (S3-13).
- R14 does NOT change `thread.anchor` or the runtime island format (S3 contract 8).
- Unanchored AND fuzzy-only-resolved agent threads are not auto-stamped (bounded: context excerpt is the human fallback; G6 high-confidence gate).
- R14 does NOT emit the old structural `buildPath` line.
- R14 does NOT use the index-based `resolveCloneNode` for stamping (unsound against strip-induced index desync — review F3).

### Risk notes (tied to diagnosis Q6)
| Change | Possible regression | Guard |
|--------|---------------------|-------|
| Transient live-stamp + strip exemption | Could double-count nodes, trip the guard, or leave live residue on error | Attributes ≠ nodes (Risk-3); the `finally` removes live stamps even on a mid-serialize throw; **E-R14-7** asserts save succeeds (no guard error) with N agent stamps; **E-R14-4** asserts zero live residue. |
| Index-desync of `resolveCloneNode` for stamping | Stamp lands on the wrong element or is dropped when strip removes preceding body siblings | NOT USED for stamping (review F3); the transient-live-stamp path stamps the live element by identity (the exact `matchAnchor` result), independent of any clone index walk; **E-R14-8** stamps a NON-FIRST element with selection/markers live and asserts correct resolution. |
| Rewritten block anchor line | Could break `test_g2_save_with_comments` (asserts the sentinel string present) | The sentinel `===== HYPRESENT AGENT INSTRUCTIONS =====` is UNCHANGED; only the per-entry anchor line changes. Re-run `test_g2`; **G-R14-LEGIBILITY** verifies the new format (Risk-6). |
| Reopen-and-resave | Stale `data-hyp-agent` could survive | `serialize()` step (1) clears every live `data-hyp-agent` BEFORE cloning; stale ids never reach the clone; **E-R14-6** asserts idempotence. |
| Multiple ids per element | A malformed `~=` selector could mis-resolve | `~=` is exact whitespace-token match; **E-R14-2** with two threads on one element asserts each selector resolves the single shared element. |

---

## Cross-cutting invariants (binding on every R10–R14 change)

| # | Invariant | Source |
|---|-----------|--------|
| I1 | Resize edits ONLY `width`/`height`/`flex-basis`/`flex-grow`/`flex-shrink`/grid tracks; NEVER `position:absolute`, NEVER `translate`. | D1, D7, decision-log "Distinct CSS surfaces" |
| I2 | Move writes ONLY `translate`; R10/R12 never write `translate`. | D2/D7 |
| I3 | Every new injected class/id is `hyp-`prefixed; every new injected attribute is `data-hyp-*`; the serializer strips them by namespace. | A12, A8 |
| I4 | All new mutating ops (R10 augmented capture, R13's four ops) flow through the single linear history stack; nothing mutates outside a command. Serialize NEVER pushes history — the R14 transient live-stamp is applied and reverted (`finally`) WITHIN `serialize()`, never as a history command, so the live DOM and the undo stack are unchanged across a save. | A7, diagnosis R14 undo note |
| I5 | The R2 pointer-events rule (`ensureInteractionStyle`), the `onDragEnd` drop-hit-test toggle, the R05 zero-distance guard, FLIP reorder, and the R8 font-span logic are UNTOUCHED. | Risk-4, diagnosis Healthy-paths |
| I6 | The 116-test suite (`tests/e2e/` + `tests/unit/`) re-runs green; specifically `test_r2_resize_real.py`, `test_f2_select_guides.py`, `test_f5_comments.py`, `test_g2_save_with_comments.py`. | Risk-6 |
| I7 | New tests use SYNTHETIC fixtures only; NEVER `tecer-gsmm-introduction*.html`. | AD8 |

---

## Amendments (orchestrator errata — append-only)

**ADX-1 (2026-06-05, during V4-T2):** S3-1/S3-2 writes are box-sizing-aware. `beforeRect[axis] + e.dist[axis]` is a BORDER-BOX target; before writing `flex-basis` (main axis) or `height` (cross axis) in the flex-child branch, read `getComputedStyle(el).boxSizing` — if `content-box`, subtract that axis's paddings + borders from the target (floor at 0); if `border-box`, write as-is. Document elements' own `box-sizing` is NEVER mutated; fixtures stay content-box and serve as the content-box regression case. Else/absolute branches untouched (AD1 unchanged).

**ADX-2 (2026-06-05, during V4-T2b):** Contract 1 (slack flex row) is corrected for reflow-coupled rows (flexible siblings, container-filling): the dragged-edge-tracks-cursor property is geometrically unsatisfiable there (sibling reclaims Δ; right edge stationary until sibling min-content — confirmed by live G0 x-shift and V4-T2b instrumentation). Binding contract becomes: (i) rendered border-box width delta = cursor delta ±2px; (ii) inline flex-basis = box-sizing-converted target ±1px; (iii) flex-grow:0 and flex-shrink:0 written; (iv) edge-position assertions live ONLY on start-pinned contexts (contracts E-R10-3/4/5 unchanged). Anti-amplification / anti-dead-zone width-delta assertions are unweakened and mandatory. UX rationale: D1 accepted layout-honest mirroring in centered/coupled contexts.

**ADX-3 (2026-06-05, during V4-T4):** S3-5 corrected — the vendored Moveable ignores instance-property `fixedDirection` assignment mid-lifecycle; the binding mechanism is the per-gesture event API: `onResizeStart: if (e.inputEvent.altKey) e.setFixedDirection([0,0])`. Per-gesture scope makes the onResizeEnd reset unnecessary (dead step removed). Doubled-dist semantics (ADX-2 context, L193 formula) unchanged.

**ADX-4 (2026-06-05, during V4-T4b, per adx4-probe.md):** Alt-symmetric on flow elements requires consuming Moveable's center-shift: in onResize for an Alt-latched gesture with role ≠ absolute, write `el.style.translate = e.drag.beforeTranslate[0]+"px "+e.drag.beforeTranslate[1]+"px"` — REPLACE (beforeTranslate is absolute since gesture start and already folds in any pre-existing move). `translate` is captured in the same sizing snapshot as the flex longhands → one undo step restores size+position atomically (absent-inline restores to absent). Absolute branch: compensate left/top by −dw/2/−dh/2; no translate write. The flow-box badge keys on translate presence and fires naturally — accepted. E-R12-4's flex-basis expectation is the ADX-1-CONVERTED value. E1 caveat: if the prior-move edge test fails with an offset≈half signature, the executor STOPs (documented base+beforeTranslate fallback applies only by orchestrator decision).

**ADX-6 (2026-06-05, post-R12 review):** (a) The flex-child Alt center-shift skip is narrowed to a justify-aware gate — translate compensation is skipped ONLY when the flex parent re-centers on its own (computed justify-content of center / space-around / space-evenly, or horizontal auto-margins on the element); all other flex children receive the standard `base − dist/2` translate like block/grid-child. (b) R11's equal-size snap, when the gesture is Alt-latched, recomputes the center-shift from the FINAL applied size delta (post-snap), never from raw `e.dist` — otherwise the element mis-centers by half the snap correction. (c) Test additions: Alt-on-absolute coverage and a combined-undo assertion (single undo restores size longhands AND translate).
