# Hypresent UI bugfix — diagnosis (2026-06-11)

Eight owner-reported bugs from a live editing session (2026-06-10) on the GSMM board deck.
App: `3-resources/tools/rbtv/studio/hypresent` (rbtv repo, branch `master`).
Investigation: conductor (opus) on the comments cluster + shell reads; 3 parallel `systematic-debugging` investigators on text-edit, builder, and shell/switch. Static analysis only — bugs 3 and 5 carry a **live-repro-before-fix** flag.

Architecture recap: `app/` is the shell UI (Editor `app/index.html`+`app/js/main.js`, Builder `app/builder.html`+`app/js/builder/*`), served by `server/`. The open deck lives in an `<iframe class="doc-frame">`; `runtime/js/*` is the editing engine injected into that iframe. `app/js/bridge/bridge-parent.js` ↔ `runtime/js/bridge-iframe.js` is the command bridge; `runtime/js/runtime-main.js` registers every command.

---

## Bug 1 — Comment shortcut (Ctrl+Alt+C) does nothing

**Symptom:** The keyboard shortcut to add a comment doesn't fire; owner notes Ctrl+Alt+C "already does something else" and wants to try other shortcuts.

**Root cause:** The comment shortcut is bound to **Ctrl+Alt+C** in three places — runtime `shortcuts.js:30` (`(e.key==="c"||"C") && e.altKey`), shell `main.js:802` (`e.altKey && k==="c"`), and documented in `shortcuts-help.js:43`. On the owner's **Brazilian ABNT keyboard, Ctrl+Alt == AltGr**, a layout modifier consumed by the OS/IME to compose characters (AltGr+C). The browser keydown is intercepted/altered by the layout before the handler's condition matches, so the comment action never runs. This is layout-specific, not a wiring bug — the binding works on a US layout.

**Fix:** Rebind comment to a non-AltGr, non-browser-reserved combo, in all three places (`shortcuts.js`, `main.js` document keydown, `shortcuts-help.js` help table). **DESIGN DECISION — owner picks the key.** Candidates (all AltGr-free, not hard-reserved in Chrome): `Ctrl+M` (mnemonic "marcar"), `Ctrl+Shift+M`, `Ctrl+Shift+K`. Avoid: any `Ctrl+Alt+*` (AltGr), `Ctrl+Shift+C` (Chrome DevTools inspect).

**Confidence:** High (cause), pending owner's key choice.

---

## Bug 2 — Every comment marker shows the number "1"

**Symptom:** All in-deck comment pins display the same number (1).

**Root cause:** There is **no sequential comment numbering anywhere in the codebase.** The only number rendered is the in-deck marker badge, set to `String(1 + thread.replies.length)` at `comments.js:308-310` (`renderMarkerFor`) and `comments.js:341-343` (`updateMarkerState`). That is the *message count within a thread* (1 comment + N replies) — which is exactly `1` for every reply-less comment. The side panel (`main.js createThreadEl`) renders author/time/body but **no number at all**.

**Fix:** Introduce a sequential per-comment number and render it both on the marker badge and in the panel thread header. **Recommended scheme (low-impact default, confirm):** number anchored threads by **document order** (top-to-bottom position of their anchor element), recomputed on each render so deletions renumber cleanly; resolved/unanchored threads handled consistently. This replaces the message-count badge — if a message count is still wanted it becomes a secondary affordance, not the primary number.

**Confidence:** High.

---

## Bug 3 — Marking an existing comment "for agent" breaks the comment UI (red comment) — LIVE-REPRO REQUIRED

**Symptom:** Clicking "For agents" on an already-made comment broke the UI; the comment renders with a red border (screenshots `Captura de tela 2026-06-10 114018.png`, `…150516.png`). Owner adds: "the bug seems to be generated **not only** when I mark a comment for agent."

**Candidate causes (not yet confirmed — needs the browser):**
1. **Threads rendering as `.comment-thread-unanchored`** — a red-orange left border (`shell.css:252`, `--accent` `#D9532C`) applied when `matchAnchor(thread.anchor)` returns null in `comments.js threads()` (`:716-728`). On the GSMM deck the same structural elements implicated in bug 8 (inline-`<svg>` rows) or reordered/edited elements may fail anchor resolution, sorting live comments into the "Unanchored" red bucket.
2. **Double-refresh race** — `tag-agent` triggers `refreshCommentPanel()` twice: once explicitly in the agent-toggle `change` handler (`main.js:288-298`) and once via the `dirty-changed` event handler that also calls `refreshCommentPanel()` (`main.js:393-398`). Two concurrent `comments-read` round-trips can interleave the panel render.
3. **Serializer node-count guard abort** — `serialize()` stamps `data-hyp-agent` on live elements then aborts with a `null` return if the node-count guard fails (`serializer.js:253-317`); only relevant if the break appears on **save**, not on toggle.

**Why static analysis is insufficient:** the red styling has two sources (`-unanchored` left-border vs `-highlight` outline, `shell.css:252-253`) and the anchor round-trip (`buildAnchorKey`→`matchAnchor`) is data-dependent on the live GSMM DOM. The exact mechanism must be reproduced.

**Plan:** Reproduce on the real GSMM deck (start `server/server.py`, load the deck, toggle For-agents + other comment ops, capture console errors + the offending thread's `unanchored`/class state) → then spec the fix. **Do not dispatch a fix until reproduced.**

**Confidence:** Low (mechanism) until live repro.

---

## Bug 4 — Topbar shows the path twice and in full

**Symptom:** The topbar shows the full absolute path twice ("Saved to C:\…\te…" then "C:\…\te… • Unsaved"); the two also contradict (one says Saved, one says Unsaved). Owner wants: don't show the full path inline — show filename + Saved/Unsaved, reveal the path only on hover over "Unsaved".

**Root cause (two compounding defects, high confidence):**
1. **Basename split uses forward-slash only.** `setDocChip((path).split(/[\/]/).pop())` at `main.js:577` (Save→SaveAs fallback) and `main.js:601` (Save As). On Windows the dialog returns a backslash path (`api.py` `SaveFileDialog.FileName`), so `.pop()` returns the **entire path** into the `#doc-name` chip. (The `?file=` handoff branch at `main.js:526` uses the correct `/[\\/]/` and a basename `result.name`, so it is unaffected.)
2. **Status duplicates the path.** `setStatus("Saved to " + path)` at `main.js:583` / `:602` writes the full path into `#shell-status`, which sits next to `#doc-chip` in `.topbar-ctx` (`index.html`) with no mutual exclusion → both visible at once.
3. **Saved/Unsaved contradiction.** After Save As, `setDocState(false)` → "Saved"; a later `dirty-changed` flips the chip to "Unsaved" while `#shell-status` still holds the stale "Saved to …" string (no auto-clear).

**Fix (owner's stated preference ≈ investigator Option C):** show only the basename in `#doc-name` (fix the regex to `/[\\/]/`); set the full path as a `title=` tooltip on the doc-chip (hover reveals it); drop the "Saved to <full path>" status string (the chip's Saved/Unsaved state is the acknowledgement); optionally auto-clear `#shell-status` so it only carries transient errors.

**Confidence:** High.

---

## Bug 5 — Replying to a comment doesn't work — LIVE-REPRO REQUIRED

**Symptom:** Comment reply doesn't work.

**Analysis:** The reply path is wired correctly end-to-end: panel Reply button (`main.js:204-228`) → `openComposer({mode:"reply"})` → `bridge.command("reply-comment", {commentId, body, author})` → registered handler `runtime-main.js:230-235` → `comments.reply()` (`comments.js:448-471`) pushes the reply, persists, refreshes. No defect in the data path.

**Candidate causes:**
1. **Symptom of bug 3** — if the comment panel is in the broken/unanchored state, its buttons are effectively dead.
2. **Enter-key UX mismatch** — in the popover composer plain **Enter inserts a newline**; submit requires **Ctrl+Enter or the Save button** (`comment-composer.js:96-100`). But the *panel* composer submits on plain Enter (`main.js:836`). A user who types a reply and presses Enter gets a newline and concludes reply is broken.

**Plan:** Confirm in the same live repro as bug 3. If it is the Enter-key mismatch, the fix is to make plain Enter submit (Shift+Enter = newline) in the reply/edit popover, matching the panel composer.

**Confidence:** Medium until live repro.

---

## Bug 6 — Editor↔Builder switch pops a confusing save dialog; should be clearly "save" and auto-open

**Symptom:** Switching opens a native dialog that looks like an "open a file" dialog but is actually a save/choose-destination dialog (overwrite risk); and the owner expects the switched-to presentation to open automatically without saving again.

**Root cause (high confidence):**
- Both crossings already use a **real Windows `SaveFileDialog`** titled "Save As" (`api.py` `_SAVE_PS`): Editor→Builder via `dialogSaveAs` (`file-controls.js:56`); Builder→Editor via `/api/dialog-save-path` (`deck-save.js`, `deck_api.py`). The OS dialog's action button is "Save" — but it appears with **no context** right after the user clicked "Switch", so it reads as an unexpected file picker.
- **Auto-open is already implemented** on both sides via the `?file=` handoff (Editor reads it at `main.js:519-535` → `openFile`; Builder at `builder-main.js:593-608` → `loadDeckByPath`). So "open again" is not actually required — the friction *is* the surprise save dialog.

**Fix (DESIGN DECISION — how far to go):**
- **A — Contextual dialog (light):** pass a custom title ("Save before switching to Editor/Builder") + a one-line pre-dialog message. Server-only change, zero logic risk.
- **C — Silent overwrite if a path is known (medium, recommended):** if the deck already has a saved path, write to it silently (`mode:'overwrite'`) and switch with no dialog; show the dialog only for a never-saved deck. Low friction for the common case.
- **B — Temp-file seamless handoff (heavy):** write a server-side temp file, switch with `?file=<tmp>`, defer the destination choice to the first explicit Save on the other page. No dialog ever; new endpoint + temp-file lifecycle.

**Confidence:** High (cause); scope is the owner's call.

---

## Bug 7 — Inserting a blank slide replaces and deletes another slide

**Symptom:** Adding a blank slide in the Builder made it take the place of an existing slide and delete it.

**Root cause (high confidence):** `rebaseDeckToSavedFile()` — which re-syncs the tray model's `existing`-section indices to the freshly written file — is gated to `mode === 'new-file'` only (`builder-main.js:542`). An **overwrite** save also rewrites the deck's section layout (add/remove/reorder, including inserting `BLANK_SECTION`), but skips the rebase, so the model's `existing.index` values go **stale**. The next save resolves `sections[staleIdx]` against the mutated file and pulls the wrong section. Traced sequence: remove a slide → add blank → Overwrite → add another blank → Overwrite ⇒ a stale `existing:2(idx=2)` now points at the blank written by the previous overwrite, so the real section 2 is dropped and replaced by blank — exactly "the blank took the place of another slide and deleted it." (The `new-file` equivalent of this defect was fixed in commit `5fc186f`; the overwrite branch was not included.)

**Fix:** Call `rebaseDeckToSavedFile(result.path)` after **both** save modes (move it outside the `if (mode === 'new-file')`). Minimal blast radius (one reload round-trip per overwrite). Add a regression test for overwrite-then-overwrite-with-blank (none exists; `test_pb11_deck_save.py` PB11-2 covers only a single overwrite).

**Confidence:** High.

---

## Bug 8 — Some text boxes won't enter edit mode on double-click

**Symptom:** Double-clicking certain text boxes doesn't place a cursor. Repro: deck `…/gsmm/presentations/2026-06-11-board/old/tecer-gsmm-board-v7.html`, slide 7, "mapa preliminar de voces".

**Root cause (high confidence, validated against source):** `canEditText()` rejects any element that has a child whose tag is **not** in `INLINE_TAGS` — `text-edit.js:84-88`:
```js
for (const child of el.children) {
  if (!INLINE_TAGS.has(child.tagName.toLowerCase())) return false;
}
```
`INLINE_TAGS` (`text-edit.js:41-46`) lists phrasing tags (`span`, `strong`, `em`, …) but **omits `svg`**. The affected GSMM rows (`div.lead`, `div.map-legend`) carry a decorative inline `<svg class="map-mark">` icon, so `canEditText` returns false and `enterEdit` bails at `text-edit.js:103`. Plain rows (no children) and rows with `<strong>` edit fine. The same gate is duplicated in `selection.js isTextEditable` (so the shell also reports `isText:false`). Original behavior, not a regression — `svg` was never anticipated as inline content.

**Fix:** Add `"svg"` to `INLINE_TAGS` in **both** `text-edit.js:41-46` and `selection.js` (its local inline set). SVG roots and descendants stay non-editable via the separate `tag==="svg"` / `isInsideSvg` guards (`text-edit.js:69-70`), so double-clicking the icon itself still won't edit — only the text portion does. Add a test covering a text element with an inline `<svg>` child (none exists; `test_f2_select_guides.py` covers only childless titles).

**Confidence:** High.

---

## Fix-routing summary

| Bug | Severity | Root cause confidence | Fix size | Needs design decision | Live-repro before fix |
|-----|----------|----------------------|----------|----------------------|----------------------|
| 1 shortcut | med | high | small | YES (which key) | no |
| 2 numbering | med | high | medium | minor (scheme — default given) | no |
| 3 mark-for-agent UI break | **high** | **low** | unknown | no | **YES** |
| 4 topbar path×2 | low | high | small | resolved by owner's stated pref | no |
| 5 reply | med | medium | small | no | **YES** |
| 6 switch dialog | med | high | small→large | YES (scope A/C/B) | no |
| 7 blank-slide delete | **high** | high | 1-line | no | no |
| 8 can't edit text | high | high | small | no | no (repro optional) |

**Execution shape:** live-repro bugs 3 & 5 first → spec all fixes → kimi executes each code fix → per-fix verification (unit/e2e + real-browser exercise on the GSMM deck) → commit (scoped to hypresent; the repo's unrelated uncommitted `orchestration/.../core-protocol.md` is kept out).
