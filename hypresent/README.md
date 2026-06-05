# hypresent

A local, browser-based WYSIWYG editor for AI-generated HTML. hypresent opens an existing HTML file from disk, lets you edit it visually (text, formatting, flow-aware resize, transform-based move, recolor, and embedded comments), and saves a new standalone HTML file with zero editor chrome — the document's own CSS, JavaScript, and assets are preserved untouched.

It is robust on conforming files and degrades gracefully on any HTML; it was verified end-to-end against two fixtures spanning the structural extremes — a zero-JS flex/grid slide deck (the deck fixture) and a JS-driven scrolling report (the report fixture). See [`docs/fixture-profiles.md`](docs/fixture-profiles.md).

## Requirements

- **Python 3** (standard library only — no `pip install`, no virtualenv).
- **Google Chrome** (the editor targets Chrome; see Known Limitations).
- **No build step.** No bundler, no Node, no dependencies to install. Third-party libraries (Moveable, Coloris, DOMPurify) are vendored as native ES modules under `app/js/vendor/`.

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

1. **Open a document.** Click **Open…** to pick a file via a native OS file dialog. The document loads in an isolated iframe from its own directory (so its relative `assets/` and CDN references resolve), the document's own JavaScript runs normally, and the edit-runtime is injected on top.
2. **Edit text.** **Double-click** any text element to edit it inline; click away (or press Esc) to commit.
3. **Format text.** With a text edit active, use the toolbar: **B** (bold), **I** (italic), **A+ / A-** (font size up/down).
4. **Resize / Move / Delete / Align.** Select an element and its drag + resize handles appear immediately (no tool switch). Drag the body to move/reorder/re-parent; drag a handle to resize. Alignment guides appear like Google Slides during drag and resize. Resize is **flow-aware**: it edits `width` / `height` / `flex-basis` / grid tracks in place and never force-converts an element to absolute positioning, so the layout stays responsive. Moves write **only** the CSS `translate` property (non-destructive and fully reversible); a badge appears if the element visually leaves its flow box. Click the **🗑** toolbar button to **delete** the selected element (full undo; deleting the last remaining region is blocked). Use the **alignment toolbar group** to align text inside the selected element's box — horizontal (left/center/right) is always available; vertical (top/middle/bottom) is enabled only for flex/grid containers, table cells, or fixed-height blocks (it never silently converts a plain block's layout).
5. **Recolor.** The color popover changes a theme **token** (recolors every element bound to that `:root` variable in one operation — a ⓘ tooltip on the Palette Tokens header explains this) or applies a **per-element** color override, including a **Border** color row (applies to all sides; adds a 1px border if the element has none). Each palette token has a discreet **copy-HEX** button that copies the normalized `#rrggbb` to the clipboard. Colors set via inline `style=` are handled too. Color picking uses Coloris.
6. **Comment.** Add a comment anchored to any element (Google-Slides style: marker → thread). Adding or replying to a comment opens an anchored composer popover (not a prompt). Tag a thread **For agents** to emit a machine-readable instruction block at the top of the saved file's `<head>` for AI coding agents. You are asked for your name **once** (stored in `localStorage`); after that, **reply** and **resolve** threads from the side panel. Comments persist inside the saved file as a hidden, inert JSON island and re-anchor on reopen.
7. **Undo / Redo.** A single unified history stack covers every operation above; use the toolbar **Undo** / **Redo** buttons.
8. **Save / Save As.** Click **Save** to silently overwrite the currently-open file (or **Save As…** to choose a new path via a native save dialog). The output is chrome-free (no `hyp-` classes/ids, no `data-hyp-*` attributes, no injected scripts/styles) except for the one inert comment island, and the document's own scripts still run. Native dialogs appear **on top of** the browser window.

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

- **Specs** (`docs/spec/`): [`01-architecture.md`](docs/spec/01-architecture.md), [`02-html-convention.md`](docs/spec/02-html-convention.md), [`03-module-map.md`](docs/spec/03-module-map.md), [`04-implementation-plan.md`](docs/spec/04-implementation-plan.md), [`05-verification-plan.md`](docs/spec/05-verification-plan.md), and the pre-build [`review-log.md`](docs/spec/review-log.md).
- **Decisions:** [`docs/decision-log.md`](docs/decision-log.md) (locked product decisions D1–D6 + architecture choices A1–A12).
- **Plan:** [`docs/plan/hypresent-v1/`](docs/plan/hypresent-v1/) (shape, execution index, per-task files).
- **Build log:** [`docs/build-log.md`](docs/build-log.md) (one entry per task: what was built, files, how verified).
- **Verification:** [`docs/verification/foundation-smoke/result.md`](docs/verification/foundation-smoke/result.md), [`docs/verification/cp1/result.md`](docs/verification/cp1/result.md), [`docs/verification/cp2/result.md`](docs/verification/cp2/result.md) (includes the final GREEN re-verify).
- **Learnings:** [`docs/learnings.md`](docs/learnings.md).

## Known limitations

- **The deck fixture's `assets/` images are absent.** The deck fixture references relative `assets/*` images that do not exist in this workspace, so opening it logs `404`s for those images. These are the fixture's own missing assets, not a hypresent defect.
- **Chrome only.** The editor targets and is verified on Google Chrome; other browsers are unverified.
- **Reorder of grid items with explicit `grid-column/row` placement** changes DOM order but may not change visual order (CSS grid honors explicit placement).
- **Edits existing files only.** hypresent does not create new documents, and has no real-time collaboration — comments are single-user and embedded.
