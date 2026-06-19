# hypresent

A local, browser-based WYSIWYG editor for AI-generated HTML. hypresent opens an existing HTML file from disk, lets you edit it visually (text, formatting, flow-aware resize, transform-based move, recolor, and embedded comments), and saves a new standalone HTML file with zero editor chrome — the document's own CSS, JavaScript, and assets are preserved untouched.

It is robust on conforming files and degrades gracefully on any HTML; it was verified end-to-end against two fixtures spanning the structural extremes — a zero-JS flex/grid slide deck (the deck fixture) and a JS-driven scrolling report (the report fixture). See `docs/fixture-profiles.md` (archived to the vault's build-history).

## Requirements

- **Python 3** (standard library only — no `pip install`, no virtualenv).
- **Google Chrome** (the editor targets Chrome; see Known Limitations).
- **No build step.** No bundler, no Node, no dependencies to install. Third-party libraries (Moveable, Coloris, DOMPurify) are vendored as native ES modules under `app/js/vendor/`; the UI fonts (Fraunces, Hanken Grotesk) are vendored as woff2 under `app/fonts/` — no CDN at runtime.

## How to run

```
python server/server.py
```

This serves `http://127.0.0.1:8765`. Then open the editor shell in Chrome:

```
http://127.0.0.1:8765/app/
```

Custom host/port: `python server/server.py 0.0.0.0 9000`.

To stop, Ctrl-C the server. Nothing is written to disk except when you explicitly use **Save As**.

## How to use

1. **Open a document.** Click **Open…** (topbar) to pick a file via a native OS file dialog. The topbar then shows the open file's name with a live **Saved / Unsaved** state. The document loads in an isolated iframe from its own directory (so its relative `assets/` and CDN references resolve), the document's own JavaScript runs normally, and the edit-runtime is injected on top.
2. **Edit text.** **Double-click** any text element to edit it inline; click away (or press Esc) to commit.
3. **Format text.** With a text edit active, use the toolbar: **B** (bold), **I** (italic), **A+ / A-** (font size up/down).
4. **Resize / Move / Delete / Align.** Select an element and its drag + resize handles appear immediately (no tool switch). Drag the body normally to move it freely; it stays in its current parent and writes only CSS `translate` (non-destructive and fully reversible). Hold **Shift** while dropping to make a structural move instead: same-parent drops reorder by sibling midpoint, and cross-parent drops re-parent into the target container. A badge appears if a free move visually leaves its flow box. Drag a handle to resize. Alignment guides appear like Google Slides during drag and resize. Resize is **flow-aware** and **cursor-true**: it edits `width` / `height` / `flex-basis` / grid tracks in place, the dragged edge tracks the cursor exactly in every layout context (flow, flex, and grid), and it never force-converts an element to absolute positioning, so the layout stays responsive. Holding **Alt** during a resize grows the element symmetrically from its center (any element); without Alt, resize is one-sided (auto-centered elements still mirror — honest layout). Resize now shows **equal-size matching** — when a dimension comes within a few px of a nearby element's width or height it snaps to it exactly and shows a dashed hint with the matched value. Click the **trash** toolbar button to **delete** the selected element (full undo; deleting the last remaining region is blocked). Use the **alignment toolbar group** to align text inside the selected element's box — horizontal (left/center/right) is always available; vertical (top/middle/bottom) is enabled only for flex/grid containers, table cells, or fixed-height blocks (it never silently converts a plain block's layout).
5. **Recolor.** The color popover changes a theme **token** (recolors every element bound to that `:root` variable in one operation — a ⓘ tooltip on the Palette Tokens header explains this) or applies a **per-element** color override, including a **Border** color row (applies to all sides; adds a 1px border if the element has none). Each palette token has a discreet **copy-HEX** button that copies the normalized `#rrggbb` to the clipboard. Colors set via inline `style=` are handled too. Color picking uses Coloris.
6. **Comment.** Add a comment anchored to any element (Google-Slides style: marker → thread). Adding or replying to a comment opens an anchored composer popover (not a prompt). Posted comments (root and replies) can be **edited** and **deleted** from the comment panel (full undo; edits propagate to the saved JSON island and, for agent-tagged comments, to the `<head>` agent block). Tag a thread **For agents** to emit a machine-readable instruction block at the top of the saved file's `<head>` for AI coding agents; the saved file stamps a `data-hyp-agent="<id>"` attribute on the target element and the `<head>` block references it via a copy-pasteable `[data-hyp-agent~="<id>"]` selector (robust to DOM shifts) with a self-cleanup directive. Resolved or deleted agent comments leave no stamp. You are asked for your name **once** (stored in `localStorage`); after that, **reply**, **edit**, **delete**, and **resolve** threads from the side panel. Comments persist inside the saved file as a hidden, inert JSON island and re-anchor on reopen.
7. **Undo / Redo.** A single unified history stack covers every operation above; use the **Undo** / **Redo** buttons in the topbar.
8. **Save / Save As.** Click **Save** to silently overwrite the currently-open file (or **Save As…** to choose a new path via a native save dialog). While the topbar shows **Unsaved**, trying to close or refresh the browser tab (e.g. an accidental Ctrl+W) raises the browser's "Leave site? Changes you made may not be saved" confirmation so edits are not silently discarded; saving clears it. The output is chrome-free (no `hyp-` classes/ids, no `data-hyp-*` attributes, no injected scripts/styles) except for the one inert comment island, and the document's own scripts still run. Native dialogs appear **on top of** the browser window.

## Builder

hypresent ships a second page at `/app/builder.html` for composing presentation decks from any RBTV slide library. Start the server as above, then open `http://127.0.0.1:8765/app/builder.html`.

1. **Pick a library.** Click **Pick library…** to choose a slide-library folder. The builder validates the library by running its vendored engine in `--catalog-data --json` mode; if the library is invalid, every §8 error is listed before you proceed. On success the left rail shows the library card (name, path, slide/section counts), a segmented **language filter**, and a **sections nav** that scrolls the browse pane and tracks the visible section.
2. **Choose a flow.** Either select a **preset** to preload the tray with the preset's ordered slides, or build from **scratch** by clicking cards in the browse pane. Clicking a card toggles it: added cards show their tray position as a badge; clicking again removes them.
3. **Compose the tray.** The right-hand tray shows the deck order with live slide thumbnails. Drag any row to reorder; the sorter is a hand-rolled pointer-events implementation (no native HTML5 DnD) so it can be driven by real mouse input in tests. Remove rows with the ✗ button.
4. **Assemble.** Pick a destination folder, fill **Deck name**, **Language**, optional **Title** and **Accent**, and click **Assemble presentation**. The builder calls the library's own `assemble.py` via subprocess with `--slides` and `--json`; the engine writes the deck, copies assets, appends the as-built entry, and reports unfilled tokens. On success, the builder navigates to `/app/?file={encodedOutputPath}`, where the editor boot reads the `?file=` parameter once (single decode via `URLSearchParams.get`) and opens the assembled deck through the existing `/api/open` path.

The builder never duplicates engine behavior: the library's vendored engine is the single source of truth for parsing, validation, assembly, and logging (ADX-2).

## Architecture

- **Python stdlib server** (`server/`) with three roots: `GET /app/*` (the editor shell, fixed), `GET /runtime/*` (the injected edit-runtime, fixed, served from the app's own dir), and `GET /doc/*` (the open document's directory, re-pointed on each open). JSON API: `POST /api/open` and `POST /api/save-as`.
- **Same-origin iframe isolation.** The user's document loads in an iframe from `/doc/`; its relative assets and its own JS run unmodified. The app shell (toolbar, panels, color popover) lives in the parent page and never enters the document.
- **`hyp-` namespacing is absolute.** Every injected class/id is `hyp-`prefixed and every injected attribute is `data-hyp-*`; the editor never reads-then-writes the document's own classes, ids, or native `data-*`. The parent and iframe communicate over an origin-filtered command/event bridge.
- **Strip-only serializer.** Save As clones the document, removes editor chrome **solely by namespace stripping** (no whole-document sanitizer pass — the file is the user's own, not untrusted), re-embeds the comment island, runs a node-count integrity guard, and emits standalone HTML. The document's own scripts/handlers/`<style>`/SVG survive because nothing touches them.

## Repository layout

| Path | Purpose |
|------|---------|
| `server/server.py` | Stdlib HTTP server: static `/app` + `/runtime` roots, mutable `/doc` root, API router |
| `server/api.py` | `open` / `save-as` request handlers |
| `app/index.html` | Editor shell parent page (toolbar, panels, iframe mount) |
| `app/css/shell.css` | Shell styling (parent only; never enters the document) |
| `app/js/main.js` | Shell bootstrap: bridge wiring, toolbar, comment panel, Save As |
| `app/js/api-client.js` | `fetch` wrappers for the JSON API |
| `app/js/bridge/bridge-parent.js` | Parent side of the parent↔iframe protocol |
| `app/js/shell/file-controls.js` | Open / Save As flow |
| `app/js/shell/color-popover.js` | Color UI (wraps Coloris) |
| `app/js/shell/comment-composer.js` | Anchored comment composer popover (replaces `prompt()`) |
| `app/js/vendor/` | Vendored ES modules: Moveable, Coloris (+ css), DOMPurify |
| `runtime/js/runtime-main.js` | Iframe boot orchestrator; exposes `window.hyp`, emits `ready` |
| `runtime/js/bridge-iframe.js` | Iframe side of the protocol (command dispatch + event emit) |
| `runtime/js/element-registry.js` | Editable-element detection, additive `data-hyp-id`, role/regions |
| `runtime/js/selection.js` | Selection state + `hyp-` selection ring |
| `runtime/js/history.js` | Unified undo/redo stack across all operations |
| `runtime/js/commands.js` | Command factory (captures inverse at creation) |
| `runtime/js/text-edit.js` · `text-format.js` | Inline editing + bold/italic/font-size |
| `runtime/js/interaction.js` | Combined Moveable: drag+resize+snap+guides; on-drop FLIP reorder/re-parent |
| `runtime/js/reorder.js` | Pure drop-classification helpers for reorder/re-parent |
| `runtime/js/resize.js` · `move.js` | Flow-aware resize (D1) + transform-translate move (D2) — **removed in v2** (folded into `interaction.js`) |
| `runtime/js/color.js` | Token + per-element + inline-style recolor (D6) |
| `runtime/js/comments.js` | Comment store, anchor key, JSON-island read/write (D4) |
| `runtime/js/serializer.js` | Clone → strip chrome → re-embed island → guard → standalone HTML |
| `docs/` | Specs, plan, decision log, build log, verification results |

## Documentation index

- **Specs** (`docs/spec/`): `01-architecture.md`, `02-html-convention.md`, `03-module-map.md`, `04-implementation-plan.md`, `05-verification-plan.md`, and the pre-build `review-log.md` (the full spec set is archived to the vault's build-history).
- **Decisions:** `docs/decision-log.md` (archived to the vault's build-history) (locked product decisions D1–D6 + architecture choices A1–A12).
- **Plan:** `docs/plan/hypresent-v1/` (archived to the vault's build-history) (shape, execution index, per-task files).
- **Build log:** `docs/build-log.md` (archived to the vault's build-history) (one entry per task: what was built, files, how verified).
- **Verification:** `docs/verification/foundation-smoke/result.md`, `docs/verification/cp1/result.md`, `docs/verification/cp2/result.md` (archived to the vault's build-history; includes the final GREEN re-verify).
- **Learnings:** `docs/learnings.md` (archived to the vault's build-history).

## Known limitations

- **The deck fixture's `assets/` images are absent.** The deck fixture references relative `assets/*` images that do not exist in this workspace, so opening it logs `404`s for those images. These are the fixture's own missing assets, not a hypresent defect.
- **Chrome only.** The editor targets and is verified on Google Chrome; other browsers are unverified.
- **Reorder of grid items with explicit `grid-column/row` placement** changes DOM order but may not change visual order (CSS grid honors explicit placement).
- **Edits existing files only.** hypresent does not create new documents, and has no real-time collaboration — comments are single-user and embedded.
- **Alt-resize on a flex child inside a non-centering flex parent combined with equal-size snap is untested** (bounded case).
- **Logical `justify-content` keywords (`start`/`end`)** fall through to the translate-compensation path (correct behavior, documented).
- **In reflow-coupled flex rows** (flexible siblings), resize honors SIZE intent 1:1 — edge positions follow layout physics (ADX-2 semantics).
- **Agent-tagged saves carry exactly one `data-hyp-agent` attribute per commented element** (user decision D4) — saved files are otherwise chrome-free.
