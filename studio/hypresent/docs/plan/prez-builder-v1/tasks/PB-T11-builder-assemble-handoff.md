You are Kimi, a code executor. Do EXACTLY what this file says. Read nothing else. Inline content below is the full and only context.

ORCHESTRATOR ADDENDUM (binding):
1) If a PRODUCT bug blocks any test from passing, do NOT modify product files — write the failing evidence into the evidence file under a BLOCKED section and finish.
2) NEVER create files at the workspace root; any scratch goes in the OS tempdir.
3) Write ALL run output as evidence into the files this task specifies — your final chat message is not read.

Edit-anchoring rule: locate code by the exact strings quoted here, NEVER line numbers.

# PB-T11 — Builder JS: assemble + editor handoff (smallest-change to the editor boot)

## Objective
Implement the Assemble action (destination pick + engine subprocess via the server) and the builder→editor handoff. The handoff is the SMALLEST additive change to the live editor boot: one `?file=` param branch reusing the already-exported `openFile`.

## FILE ALLOWLIST
- ✚ create `html/hypresent/app/js/builder/assemble.js`
- ✎ modify `html/hypresent/app/js/builder/builder-main.js` (wire Assemble; strictly AFTER PB-T10's edit — plan serialization)
- ✎ modify `html/hypresent/app/js/main.js` (ADD the `?file=` boot branch ONLY)
- ✗ nothing else. This is the ONLY task that touches `main.js`.

## DOM contract (from PB-T6)
- `#assemble-btn`, `#pick-dest-btn`, `#deck-filename` (text input), `#dest-path` (span), `#builder-status`.

## The endpoints / state you use
- `POST /api/dialog-folder` (PB-T7) → `{path}` or `{cancelled}` — reused to pick the OUTPUT folder.
- `POST /api/assemble {path, slides, out, lang?, title?, accent?, client_logo?}` (PB-T7) → the engine envelope `{ ok, errors, output, assets_copied, unfilled_tokens, as_built_entry }`.
- `state.libraryPath`, `state.data`, and the `tray` object (`tray.getOrder()` returns the ordered id array) — from PB-T8/PB-T10.

## assemble.js
Export `async function pickDestination()` → `fetch('/api/dialog-folder', {POST})`; return the chosen folder path or null on cancel.
Export `async function assembleDeck({ libraryPath, slides, outPath, lang, title })`:
- POST `/api/assemble` with the body; parse the envelope.
- Return `{ ok: envelope.ok, output: envelope.output, assetsCopied: envelope.assets_copied, unfilledTokens: envelope.unfilled_tokens, asBuilt: envelope.as_built_entry, errors: envelope.errors }`.
Export `function buildOutPath(folder, filename)` → join `folder` + `filename` ensuring a `.html` suffix (e.g. `folder.replace(/[\\/]+$/,'') + '/' + filename.replace(/\.html$/,'') + '.html'`).

## builder-main.js — wire the destination + Assemble (additive, after PB-T10)
- `#pick-dest-btn` click → `pickDestination()`; store the folder; set `#dest-path` text. (build-spec S-B10.1 — output folder + filename; warn in `#builder-status` if the chosen folder equals `state.libraryPath`, since the deck must be written OUTSIDE the library — convention-spec §1.2/§5.1 §4.)
- `#assemble-btn` click → require: `state.libraryPath`, a non-empty `tray.getOrder()`, a destination folder, and a filename. Compute `outPath = buildOutPath(folder, filename)`. Call `assembleDeck({libraryPath: state.libraryPath, slides: tray.getOrder(), outPath, lang, title})` where `lang`/`title` come from the preset defaults or are left undefined.
- On `ok:true`: show success in `#builder-status` (deck path + `assetsCopied.length` + `unfilledTokens.length` + an as-built confirmation), THEN HAND OFF to the editor: `window.location.href = '/app/?file=' + encodeURIComponent(output);` (build-spec S-B10.3 step 2).
- On `ok:false` or an HTTP error: show the `errors`/error in `#builder-status` as an error; do NOT navigate (build-spec S-B11.4).

## main.js — the EXACT current boot (anchor your edit here)
The file `app/js/main.js` imports at the top:
```js
import { openViaDialog } from "/app/js/shell/file-controls.js";
```
Its boot handler is:
```js
document.addEventListener("DOMContentLoaded", () => {
  const toolbar = document.querySelector(".shell-toolbar");
  const main = document.querySelector(".shell-main");
  const mount = document.querySelector(".doc-frame-mount");
  const iframe = document.querySelector(".doc-frame");
  ...
  const openBtn = document.querySelector("#open-btn");
  if (!openBtn) {
    console.error("Open control not found");
  } else {
    openBtn.addEventListener("click", async () => {
      try {
        const result = await openViaDialog(iframe);
        if (!result) return; // cancelled
        ensureBridge(iframe);
        setStatus("");
      } catch (err) {
        console.error("Open failed:", err.message);
        setStatus("Open failed: " + err.message, "error");
      }
    });
  }
```
The function `ensureBridge(iframe)` exists in this file and is what wires the bridge after a load (called in the open handler above).

The file `app/js/shell/file-controls.js` ALREADY EXPORTS (currently unused) the programmatic open:
```js
export async function openFile(path, iframe) {
  const result = await apiClient.open(path);
  await loadIntoIframe(result.name, iframe);
}
```

### Your TWO edits to main.js (additive only — zero regression)
(1) Extend the file-controls import to ALSO bring in `openFile`. Locate the exact line:
```js
import { openViaDialog } from "/app/js/shell/file-controls.js";
```
and replace it with:
```js
import { openViaDialog, openFile } from "/app/js/shell/file-controls.js";
```
(2) Add the `?file=` boot branch. Locate the open-button wiring block ending with its closing `}` (the block quoted above that ends `    });\n  }`). IMMEDIATELY AFTER that block (still inside the `DOMContentLoaded` handler, where `iframe` and `ensureBridge` are in scope), insert:
```js
    // prez-builder handoff: open a deck passed via ?file= (set by the builder page).
    // Absent the param, the editor boot is unchanged (this branch is skipped).
    // URLSearchParams.get() ALREADY returns the percent-decoded value — do NOT decode again
    // (a second decodeURIComponent would throw URIError / corrupt a path bearing a literal '%').
    const fileParam = new URLSearchParams(location.search).get("file");
    if (fileParam) {
      (async () => {
        try {
          await openFile(fileParam, iframe);
          ensureBridge(iframe);
          setStatus("");
        } catch (err) {
          console.error("Handoff open failed:", err.message);
          setStatus("Open failed: " + err.message, "error");
        }
      })();
    }
```
Change NOTHING else in main.js. When `?file=` is absent the branch does not run → the existing boot is byte-for-byte unchanged (build-spec S-B10.3/S-B10.4 zero regression). Do NOT edit file-controls.js (`openFile` already exists).

## Why this is correct (facts)
`openFile` calls `POST /api/open {path}` (live `api-client.js`), which in `server/api.py` `handle_open` re-points the `/doc/` root to the deck's parent directory, then `loadIntoIframe` sets `iframe.src = '/doc/' + name` — so the assembled deck's sibling `assets/` resolve via `/doc/`. This is the same path the Open button uses; no new server endpoint, no localStorage.

**Single decode (RV2-3 — verified):** `URLSearchParams.get("file")` returns the already-percent-decoded value; `api-client.js` `open` does a single `JSON.stringify({path})` with no URL layer (verified). The builder side `encodeURIComponent`s once on the way out (the `window.location.href` assignment below); `URLSearchParams.get` is the matching single decode. A second `decodeURIComponent` would mis-decode or throw `URIError` on a deck path containing a literal `%` (a legal Windows filename char) — so it is NOT used. PB-T14's handoff suite exercises a `%`-bearing deck path to prove this.

## Acceptance criteria (self-verifiable)
1. `node --check` passes on `assemble.js`, `builder-main.js`, and `main.js`.
2. `main.js` now contains the exact string `import { openViaDialog, openFile } from "/app/js/shell/file-controls.js";` AND `new URLSearchParams(location.search).get("file")` AND still contains the existing `openViaDialog(iframe)` open-button wiring (grep all three).
3. `main.js` does NOT contain `localStorage` added for handoff and does NOT add any new `import` beyond the extended file-controls line (diff is exactly the two edits). The handoff branch passes `fileParam` DIRECTLY to `openFile` — `main.js` does NOT contain `decodeURIComponent` in the `?file=` branch (grep: `decodeURIComponent` is absent from the param-read path; RV2-3).
4. `assemble.js` exports `assembleDeck`, `pickDestination`, `buildOutPath`.

Full assemble + handoff behavior is verified by PB-T14's e2e suite (real assemble → navigate `?file=` → deck renders in the editor iframe).

## Evidence file
Write to `html/hypresent/docs/verification/prez-v1/builder-assemble-handoff-result.md`: the probe results + `git diff --stat html/hypresent/app/js/main.js` (confirming a small additive diff) + `git status --porcelain html/hypresent/app/js/builder/`.

DONE means: assemble.js created, builder-main.js + main.js edited additively, probes pass (esp. probe 2/3 confirming the minimal main.js diff), evidence written. Failure → BLOCKED + stop.
