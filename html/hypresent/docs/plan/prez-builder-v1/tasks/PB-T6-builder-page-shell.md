You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by the exact strings quoted here, NEVER line numbers.

# PB-T6 — Builder page shell + nav (zero regression to the editor)

## Objective
Create the second static page `app/builder.html` (the builder shell), its `app/css/builder.css`, an empty mount module `app/js/builder/builder-main.js`, and add a plain two-link nav to BOTH pages. Adding the nav to `index.html` MUST NOT regress the existing editor boot.

## FILE ALLOWLIST
- ✚ create `html/hypresent/app/builder.html`
- ✚ create `html/hypresent/app/css/builder.css`
- ✚ create `html/hypresent/app/js/builder/builder-main.js`
- ✎ modify `html/hypresent/app/index.html` (ADD the nav only)
- ✗ nothing else. Do NOT touch `server/`, `main.js`, or any other JS.

## Why this serves with zero server change (fact)
The live server static router serves `/app/*` from the app root: in `server/server.py`, `do_GET` contains
```python
if path.startswith("/app/"):
    self._serve_static(APP_ROOT, path[len("/app/"):])
```
So `app/builder.html` is served at `GET /app/builder.html` with NO server edit (do NOT edit the server).

## index.html — the EXACT current content (anchor your edit on this)
The file `app/index.html` currently begins:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>hypresent</title>
  <link rel="stylesheet" href="/app/css/shell.css">
  <link rel="stylesheet" href="/app/js/vendor/coloris.css">
  <script src="/app/js/vendor/moveable.min.js"></script>
</head>
<body>
  <div class="shell-toolbar">
    <div class="toolbar-group">
      <button type="button" class="tool-btn" id="fmt-bold" title="Bold">B</button>
```
The body ends:
```html
  <script type="module" src="/app/js/main.js"></script>
</body>
</html>
```

### Your ONLY edit to index.html
Insert a nav bar IMMEDIATELY AFTER the `<body>` tag and BEFORE `<div class="shell-toolbar">`. Insert exactly:
```html
  <nav class="app-nav">
    <a href="/app/" class="app-nav-link" id="nav-editor">Editor</a>
    <a href="/app/builder.html" class="app-nav-link" id="nav-builder">Builder</a>
  </nav>
```
DO NOT change anything else in index.html. The existing selectors `.shell-toolbar`, `.shell-main`, `.doc-frame-mount`, `.doc-frame`, `#open-btn`, `#save-btn`, `#save-as-btn`, and all `id="fmt-*"`/`id="align-*"`/`id="comment-btn"`/`id="delete-btn"` buttons MUST remain byte-identical — `main.js` queries them at boot. (build-spec S-B1.3.)

## builder.html — create exactly this shell (D7-S4 two-static-pages)
A standalone HTML document with the same head conventions + a NEW `builder.css`, the nav (same as above), three zones (top bar with library pick + status; left browse pane; right compose tray), and a `type="module"` entry to `builder-main.js`. Create:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>hypresent — builder</title>
  <link rel="stylesheet" href="/app/css/shell.css">
  <link rel="stylesheet" href="/app/css/builder.css">
</head>
<body>
  <nav class="app-nav">
    <a href="/app/" class="app-nav-link" id="nav-editor">Editor</a>
    <a href="/app/builder.html" class="app-nav-link" id="nav-builder">Builder</a>
  </nav>
  <div class="builder-topbar">
    <button type="button" class="tool-btn" id="pick-library-btn">Pick library…</button>
    <span id="library-name" class="builder-library-name"></span>
    <span id="builder-status" class="shell-status"></span>
  </div>
  <div class="builder-main">
    <section class="builder-browse" id="builder-browse">
      <div class="browse-controls">
        <label>Language: <select id="lang-filter"><option value="all">all</option></select></label>
      </div>
      <div class="browse-groups" id="browse-groups"></div>
      <div class="builder-empty" id="browse-empty">Pick a slide library to begin.</div>
    </section>
    <aside class="builder-tray" id="builder-tray-pane">
      <div class="tray-controls">
        <label>Preset: <select id="preset-select"><option value="">(none)</option></select></label>
      </div>
      <ol class="tray-list" id="tray-list"></ol>
      <div class="tray-destination">
        <button type="button" class="tool-btn" id="pick-dest-btn">Pick destination…</button>
        <input type="text" id="deck-filename" placeholder="deck-name" />
        <span id="dest-path" class="builder-dest-path"></span>
      </div>
      <button type="button" class="tool-btn" id="assemble-btn" disabled>Assemble</button>
    </aside>
  </div>
  <script type="module" src="/app/js/builder/builder-main.js"></script>
</body>
</html>
```

## builder.css — create a minimal self-contained stylesheet
Style: `.app-nav` (a top link bar), `.builder-topbar`, `.builder-main` (flex row: browse left, tray right), `.builder-browse`/`.browse-groups`/`.browse-group` (a section block), the slide card grid + the preview wrapper (`.slide-thumb-wrapper { width:256px; height:144px; overflow:hidden; position:relative; }` and `.slide-thumb-wrapper iframe { width:1280px; height:720px; transform: scale(0.2); transform-origin: top left; pointer-events:none; border:0; }`), `.builder-tray`/`.tray-list`/`.tray-row` (with a position number + remove button), `.tray-drag-ghost` (a dragging state), `.builder-empty`/`.builder-invalid` (state banners). Keep it lean; do NOT modify `shell.css`. The `.slide-thumb-wrapper` rules above are load-bearing for previews (build-spec S-B5.3) — include them verbatim.

## builder-main.js — create an empty mount stub (later tasks fill it)
```js
// builder-main.js — prez-builder entry. Wiring is added by PB-T8..PB-T11.
document.addEventListener("DOMContentLoaded", () => {
  const browse = document.getElementById("browse-groups");
  const tray = document.getElementById("tray-list");
  if (!browse || !tray) { console.error("Builder DOM not mounted"); return; }
  console.info("Builder shell mounted");
});
```

## Acceptance criteria (self-verifiable)
1. `node --check html/hypresent/app/js/builder/builder-main.js` exits 0 (valid JS).
2. Start the server and assert both pages serve: run `python html/hypresent/server/server.py 127.0.0.1 8801` in the background; `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8801/app/builder.html` returns `200`; `http://127.0.0.1:8801/app/` returns `200`. Stop the server. (Use the OS tempdir for any scratch; do NOT leave the server running.)
3. Confirm `app/index.html` still contains the exact strings `id="open-btn"`, `class="shell-toolbar"`, `class="doc-frame"`, and `<script type="module" src="/app/js/main.js"></script>` (the editor boot is intact).
4. Confirm `app/index.html` now contains `<a href="/app/builder.html" class="app-nav-link" id="nav-builder">Builder</a>`.

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-shell-result.md`: the 4 probe results + `git status --porcelain html/hypresent/app/`.

DONE means: all four files in the allowlist created/modified, 4 probes pass, evidence written. Failure → BLOCKED + stop.
