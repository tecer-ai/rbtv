# Hypresent — Implementation Plan (04)

PHASED, ordered tasks `T1..Tn` for downstream `kimi` coding agents. Each task is a self-contained unit implementable from its contract alone. Foundation (server, app shell, iframe load, element-registry/`data-hyp-id`, selection, history, serializer) lands BEFORE features.

**How a kimi agent uses this file:** read the row for your task ID, read the named spec sections, implement ONLY the files in "Files", satisfy the "Public Contract", then verify against the "Acceptance" IDs (defined in `docs/spec/05-verification-plan.md`). Do not exceed declared scope. Prompts are dispatched per `docs/kimi-cheatsheet.md` (`--work-dir` = the `hypresent/` root, `--quiet --prompt`, positive `--max-ralph-iterations`).

**Status legend:** `TODO` (not started) · `DOING` · `DONE` · `BLOCKED`. All tasks start `TODO`.

**AUTHORITATIVE CONTRACT:** the per-task ROWS in this file (Phases 1–3 + Final) are the single authoritative, complete contract for every task `T1..T21`. Each row carries Goal, Files, Depends on, Public Contract, Acceptance, Parallel-safe, and Status — sufficient for a zero-context kimi agent to implement the task from the row plus the named spec sections alone. Any `*.task.md` files under `docs/plan/hypresent-v1/phase-*/` are SUPPLEMENTARY execution wrappers (phased understand→execute→validate→close steps for the orchestration layer); where a task has no `.task.md` file, its row here is the complete contract and nothing is missing. If a row and a task file ever disagree, the row here wins.

**Grounding:** decisions in `docs/decision-log.md`; architecture in `docs/spec/01-architecture.md`; convention in `docs/spec/02-html-convention.md`; modules in `docs/spec/03-module-map.md`; tests in `docs/spec/05-verification-plan.md`.

---

## Dependency Graph (text)

```
T1 server ─┬─ T2 app-shell-static ─ T3 iframe-load ─ T4 bridge ─┬─ T5 registry ─ T6 selection ─┬─ T7 commands ─ T8 history ─┬─ T9 serializer ─ [CP1]
           │                                                    │                               │
           └────────────────────────────────────────────────── (T4 needs T2+T3) ───────────────┘
                                                                                                 │
   ┌─────────────────────────────────────── after [CP1], features (parallel-safe band) ─────────┘
   ├─ T10 text-edit ─ T11 text-format
   ├─ T12 resize
   ├─ T13 move
   ├─ T14 color
   └─ T15 comments ──────────────── [CP2]
                                      │
   T16 outline ─ T17 save-as-wiring ─ T18 e2e-verification ─ [CP3] ─ T19 readme ─ T20 refs ─ T21 compound ─ [FINAL CP]
```

---

## Phase 1 — Foundation (strictly sequential within the chain)

| ID | Goal | Files (CREATE unless noted) | Depends on | Public Contract | Acceptance | Parallel-safe? | Status |
|----|------|-----------------------------|-----------|-----------------|-----------|----------------|--------|
| **T1** | Stdlib HTTP server: FIXED static `/app/*` + FIXED static `/runtime/*` (served from the app's own `runtime/` dir), MUTABLE `/doc/*` rooted at the open file's dir, JSON API `open`/`save-as`. | `server/server.py`, `server/api.py` | — | `run(host,port)`; `GET /app/*` static (app shell); `GET /runtime/*` static from the app's own `runtime/` dir — FIXED root, NEVER re-pointed to `/doc/` (serves the injected edit-runtime so its absolute `src`+`import` chain resolves per `01` §8); `GET /doc/*` static from the currently-open file's dir (re-pointed on each `open`); `POST /api/open {path}→{html,dir,name}`; `POST /api/save-as {path,html}→{ok,path}`. No Flask. Never executes file content. (`01` §1,§8 routes, A10; `03` §2) | V-OPEN-1/2 server side: open returns the fixture bytes; save-as writes a temp file then reads it back equal; `GET /runtime/js/runtime-main.js` returns the runtime module with a JS content-type. | No (root of graph) | DONE |
| **T2** | App-shell parent page + static assets + vendored libs placed, no build step. | `app/index.html`, `app/css/shell.css`, `app/js/main.js`, `app/js/vendor/{moveable.min.js,coloris.min.js,coloris.css,purify.min.js}` | T1 | Parent page loads at `/app/`, mounts an empty iframe container + toolbar/panel placeholders; vendor modules import as native ES modules. DOMPurify is vendored for OPTIONAL comment-text sanitize only (A11) — it is NOT used by the serializer. (`03` §1; `decision-log` Vendored Libraries) | Shell renders at `/app/`; `evaluate_script` confirms Moveable + Coloris load with no 404s (DOMPurify present but optional — its absence must not break the shell). | No | DONE |
| **T3** | Load a user document into a same-origin iframe via `/doc/`; inject the runtime after iframe `load` using the ABSOLUTE `/runtime/*` src. | `app/js/shell/file-controls.js` (open path only), `app/js/api-client.js`, `runtime/js/runtime-main.js` (boot stub: expose `window.hyp`, emit `ready`) | T2 | `api-client.open(path)`; set iframe `src=/doc/<name>`; on iframe `load`, append to the iframe document a `<script type="module">` whose `src` is the ABSOLUTE runtime URL `/runtime/js/runtime-main.js` (origin = server origin; NOT `/doc/`-relative). The runtime's ES-module `import`s of sibling modules resolve against `/runtime/js/` and vendored libs against absolute `/app/js/vendor/...` — confirm the import chain loads with no 404s. `window.hyp` exists; `ready` emitted. Served `/doc/` bytes identical to disk. (`01` §2,§8, A10) | V-OPEN-1, V-OPEN-2 (both fixtures render; REPORT's own JS runs; `ready` received; runtime module + its imports load from `/runtime/` and `/app/js/vendor/` with no 404). | No | DONE |
| **T4** | Parent↔iframe protocol: command dispatch + event emit, origin-filtered. | `app/js/bridge/bridge-parent.js`, `runtime/js/bridge-iframe.js` | T3 | Parent `command(type,payload)→Promise`; `on(type,handler)`. Iframe `command()` dispatch table + `emit(type,payload)`→`postMessage`. Filter `origin`+`source:'hyp'`. Command/event sets per `01` §3. | Round-trip test: parent sends a no-op command, receives ack; runtime emits a test event, parent handler fires. | No | DONE |
| **T5** | Element registry: detect editable elements, assign additive `data-hyp-id`, record original state, resolve id↔node, report layout role + regions; strip ids. | `runtime/js/element-registry.js` | T4 | `tag()`,`byId`,`idOf`,`roleOf`,`regions()`,`stripIds(clone)`. NEVER mutate non-`hyp` attrs/classes/ids; respect existing native `id`; detection per `02` §1,§4. (`03` §4) | V-BOOT-3 (all editable tagged; native ids + native `data-*` untouched; `stripIds` clears all). | No | DONE |
| **T6** | Selection: track selected element, draw `hyp-` ring, clear; emit `selection-changed`. | `runtime/js/selection.js` | T5 | `select(hypId)`,`clear()`,`current()→{hypId,role,rect,isText}`; ring is `hyp-`classed only. | V-SEL-1, V-SEL-2, V-SEL-3 (select works incl. absolute node + SVG; no doc class mutated; SVG path not text-editable). | No | DONE |
| **T7** | Command factory: build `{do,undo,label}` per op type, capturing inverse at creation. Applies nothing itself. | `runtime/js/commands.js` | T6 | `text/format/resize/move/colorToken/colorElement/comment(...)→command`. Pure; inverse captured from pre-state. (`03` §4) | Unit: each factory returns a command whose `undo()` restores the captured pre-state on a synthetic element. | No | DONE |
| **T8** | Unified history: single linear stack across ALL ops; cursor; redo-tail truncation; emit `history-changed`. | `runtime/js/history.js` | T7 | `push(cmd)` (runs `do()`),`undo()`,`redo()`,`state()→{cursor,canUndo,canRedo}`. One stack for text/format/resize/move/color/comments (A7). | V-HIST-1/2 partial: push synthetic commands, undo/redo restores DOM signature; redo tail truncates. | No | DONE |
| **T9** | Serializer: clone→strip ALL `hyp-`/editor chrome + `data-hyp-*` + injected inline styles→restore original `contenteditable`→re-embed comment island→node-count guard→emit standalone HTML. NO whole-document DOMPurify/sanitizer pass. | `runtime/js/serializer.js` | T8 | `serialize()→htmlString`. Strip-only chrome removal + order per `01` §5 and `decision-log` A8/A11; the document's own scripts/handlers/`<style>`/SVG/native `data-*` are preserved by NOT touching them. Node-count delta guard (delta = removed `hyp-` chrome + re-embedded island); abort with `error` on out-of-band drop. DOMPurify is NOT imported here. | T9-scoped (built before features exist, with an EMPTY comment store): (a) serialized output is chrome-free — `evaluate_script` finds ZERO `[class^="hyp-"],[class*=" hyp-"],[id^="hyp-"]` and ZERO `data-hyp-*` (no `#hyp-comments` yet, store empty); (b) DECK has no `<script>` added, REPORT's own `<script>` IIFE is retained byte-for-byte; (c) output is valid standalone HTML that loads in a fresh page without layout collapse. Visual/reflow fidelity, comment-island round-trip, and re-editability are verified later by T18 (`05` §4 gate), NOT at T9. | No | DONE |
| **CP1** | **CHECKPOINT — Foundation usable end-to-end.** | (review only) | T9 | Evaluate: server serves both fixtures; iframe loads; bridge round-trips; registry tags without collision; selection works; history undo/redo on synthetic commands; serializer emits chrome-free HTML that re-opens. | Gate review per `04`/`05`; HALT for human approval. | No | DONE |

---

## Phase 2 — Features (parallel-safe band — see notes)

All Phase-2 feature tasks depend ONLY on the foundation (through CP1). They touch DISJOINT files and each emits commands through the shared `history` (T8) and uses `commands` (T7) — so they are **parallel-safe with respect to each other** EXCEPT the two intra-pair sequences noted. Each must run the §3 regression checklist before claiming done.

| ID | Goal | Files | Depends on | Public Contract | Acceptance | Parallel-safe? | Status |
|----|------|-------|-----------|-----------------|-----------|----------------|--------|
| **T10** | Text edit: double-click text-editable element → `contenteditable` (record prior) → commit on blur/Esc as a text command. | `runtime/js/text-edit.js` | CP1 | Double-click lifecycle; excludes SVG text/path; commits via `commands.text`+`history`. (`02` §1, H4 fallback; `03` §4) | V-TXT-1, V-TXT-2, V-TXT-NEG. | Yes (vs T12–T15); **before T11** | DONE |
| **T11** | Text format: bold/italic/font-size via `execCommand`+Selection within an active edit. | `runtime/js/text-format.js`, UPDATE `app/js/shell/toolbar.js` | T10 | `apply(op)` op∈{bold,italic,fontInc,fontDec}; format command pushed to history. (`research-oss` Cat 2) | V-FMT-1, V-FMT-2. | After T10 (pair sequential) | DONE |
| **T12** | Resize (flow-aware, D1): mount Moveable in iframe; on end, write `width`/`height`/`flex-basis`/grid track from layout role; never convert to absolute; emit `geometry-changed`. | `runtime/js/resize.js`, UPDATE `app/js/shell/toolbar.js` (resize tool) | CP1 | `begin(hypId)`,`end()`; resize command (before/after sizing). D1 + reconciliation (`decision-log`). Moveable in-iframe (A5). | V-RSZ-1/2/3, V-RSZ-NEG. | Yes | DONE |
| **T13** | Move (D2): mount Moveable drag; write ONLY `transform: translate()`; compute + emit `out-of-flow`. | `runtime/js/move.js`, UPDATE `app/js/shell/toolbar.js` (move tool) | CP1 | `begin(hypId)`,`end()`; move command (before/after transform); `out-of-flow {bool}`. D2 + reconciliation. | V-MOV-1/2/3/4. | Yes | DONE |
| **T14** | Recolor (D6): token mutation + per-element override + inline-`style` color mutation; palette read filtered to color tokens. | `runtime/js/color.js`, `app/js/shell/color-popover.js` (wraps Coloris) | CP1 | `readPalette()→{tokens[],inlineSites[]}`; `applyToken`,`applyElement`; color commands. Handles colors outside `:root` (D6). (`02` H2/H9 fallback) | V-COL-1/2/3/4/5. | Yes | DONE |
| **T15** | Comments (D4): store + `#hyp-comments` island read/write + element anchoring + add/reply/resolve + one-time author name; Google-Slides-style marker→popover + side panel. | `runtime/js/comments.js`, `app/js/shell/comment-panel.js` | CP1 | `load`,`toJson`,`add`,`reply`,`resolve`,`threads`,`anchorRect`,`buildAnchorKey`,`matchAnchor`; anchor by the collision-resistant 5-field key (tag+nth-of-type path + nearest native id + content hash + same-key sibling index) per `01` §6.1 — MUST disambiguate the repeated identical siblings BOTH fixtures contain; unresolvable threads → "unanchored" group, never lost; comment text rendered via `textContent` (XSS-safe; DOMPurify on comment text OPTIONAL only, A11); mutations are undoable commands; author name in `localStorage`. | V-CMT-1/2/3/4/5. | Yes | DONE |
| **CP2** | **CHECKPOINT — All features functional on both fixtures.** | (review only) | T10–T15 | Evaluate each feature's V-cases pass on DECK and REPORT; regression checklist clean; namespacing intact. | Gate review; HALT for approval. | No | DONE |

> **Parallelization note:** T10→T11 is a strict pair (format needs the contenteditable session). T12, T13, T14, T15 are fully independent of each other and of the T10/T11 pair — a kimi orchestrator MAY dispatch T10, T12, T13, T14, T15 concurrently (5-wide), then T11 after T10. The only shared files are `toolbar.js` (tool buttons) and the shared `history`/`commands` modules, which are append-only extension points; if concurrent edits to `toolbar.js` are a risk, serialize the `toolbar.js` UPDATE portions or assign all `toolbar.js` edits to a single follow-up micro-task.

---

## Phase 3 — Integration & End-to-End

| ID | Goal | Files | Depends on | Public Contract | Acceptance | Parallel-safe? | Status |
|----|------|-------|-----------|-----------------|-----------|----------------|--------|
| **T16** | Outline/region navigator wired to runtime regions; click→select. | `app/js/shell/outline.js`, UPDATE `runtime/js/runtime-main.js` (emit regions on `ready`) | CP2 | Renders `regions()`; click→`select`. (`02` §4) | Outline lists DECK's 10 slides and REPORT's sections; click selects in iframe. | Yes (vs T17) | DONE |
| **T17** | Save-As wiring end-to-end: serialize → `/api/save-as` → disk; dirty-state + error handling. | UPDATE `app/js/shell/file-controls.js` (save path), UPDATE `app/js/main.js` | CP2 | Save As: `bridge.command('serialize')`→`api-client.saveAs(path,html)`; reflects `dirty-changed`; handles 500 per `01` §7. | V-SAVE-1/2/3. | Yes (vs T16) | DONE |
| **T18** | End-to-end verification run via Chrome DevTools MCP on BOTH fixtures: every V-case + regression checklist + Save-As gate. Owns the Save-As VISUAL/REFLOW fidelity, COMMENT-ISLAND round-trip, and RE-EDITABILITY gates (moved here from T9 — those require features T10–T17 to exist). | (no product code; produces a results log under `docs/`) | T16,T17 | Execute all `05` §2 cases on DECK + REPORT; run `05` §3 regression checklist; run `05` §4 Save-As validity gate on both fixtures. Explicitly verify: §4 item 1 (renders, screenshot matches edited state — visual/reflow fidelity), §4 item 3 + V-CMT-3 (comment island round-trips and re-anchors), §4 item 7 (saved file re-opens to `ready`). | All V-* PASS; §3 checklist clean; §4 gate green on DECK and REPORT (hard release blocker). | No | DONE (verification ran iteratively as CP1 → CP2 → CP2 re-verify rather than as one discrete T18 pass; the §2 cases, §3 checklist, and §4 gate are all GREEN on BOTH fixtures per `docs/verification/cp1/result.md` + `docs/verification/cp2/result.md` RE-VERIFY) |
| **CP3** | **CHECKPOINT — Product complete & verified.** | (review only) | T18 | Evaluate the V-results log; confirm gate green on both fixtures; confirm no editor leakage and document-JS preservation. | Gate review; HALT for approval. | No | DONE |

---

## Final Phase — Completion

| ID | Goal | Files | Depends on | Public Contract | Acceptance | Parallel-safe? | Status |
|----|------|-------|-----------|-----------------|-----------|----------------|--------|
| **T19** | Run/usage doc: the exact run command and open/edit/save walkthrough. | `README.md` | CP3 | Documents `python server/server.py`, how to open a file by path, edit, Save As; per `kimi-cheatsheet` no build step. | A fresh reader starts the server and opens a fixture from the README alone. | Yes | DONE |
| **T20** | Reference review: verify all internal plan links resolve and comply with Plan Linking Standard. | (review only; touches plan artifacts under `docs/plan/`) | CP3 | Internal links file-relative; external links root-relative; no broken paths. | Link audit clean. | Yes | DONE |
| **T21** | Compound learnings: process `docs/plan/hypresent-v1/learnings.md` into actionable system improvements. | UPDATE `docs/plan/hypresent-v1/learnings.md` | T20 | Each compound-ready learning grouped + actioned per the learnings template. | Learnings triaged; compound entries written or "none". | No | DONE (compounding lessons captured in `docs/learnings.md`) |
| **FINAL CP** | **FINAL CHECKPOINT — user approval to complete.** | (review only) | T21 | Present full summary; HALT for approval. | Human approves completion. | No | DONE |

---

## Per-Task Kimi Dispatch Contract (applies to every product-code task)

A kimi prompt for task `Tn` MUST be self-contained and include:
1. **Scope lock:** "Implement ONLY the files listed in `Tn` of `docs/spec/04-implementation-plan.md`. Do not modify other files."
2. **Spec pointers:** the exact `docs/spec/*` sections named in the row (read them before coding).
3. **Public contract:** the function/route signatures from the row + `03-module-map.md`.
4. **Namespacing mandate:** all injected classes/ids `hyp-`prefixed, all injected attributes `data-hyp-*`; never touch document-native classes/ids/`data-*` (A12).
5. **Acceptance:** the V-IDs from the row; the task is done only when those pass and the §3 regression checklist is clean.
6. **No build step; native ES modules; Python stdlib only** (A9/A10).

A kimi run is accepted only after a `git diff` confirms changes are confined to the task's declared files (per `kimi-cheatsheet` Confinement) and the acceptance V-cases pass.
