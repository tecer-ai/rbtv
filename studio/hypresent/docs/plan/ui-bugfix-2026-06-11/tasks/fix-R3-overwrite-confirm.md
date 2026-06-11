---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/shell/confirm-modal.js
  - app/js/shell/file-controls.js
  - app/js/builder/builder-main.js
sandbox: workspace-write
commit_policy: none
test_command: NONE (conductor runs the e2e gate)
forbidden_ops:
  - git commit
  - git push
  - git reset
  - writes outside allowlist
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus
---

## Sandbox + Approval
`--sandbox workspace-write` + `-c approval_policy="never"`. Create ONE new file + edit two existing files (all allowlisted). ASCII-only identifiers.

# Fix-round R3 — confirm before the switch overwrites the opened file

Owner decision: switching Editor↔Builder must NOT silently overwrite the originally-opened file. Show an in-app confirm modal first, with a clear "overwrite & continue" and a "Save As…" escape. Only when the deck already has a path; a never-saved deck still goes straight to Save As.

## Allowed Paths
- `app/js/shell/confirm-modal.js` (NEW)
- `app/js/shell/file-controls.js`
- `app/js/builder/builder-main.js`

## Forbidden Paths
- Every other file. No commits.

---

## Step 1 — create `app/js/shell/confirm-modal.js` with EXACTLY this content:

```js
/**
 * app/js/shell/confirm-modal.js
 * In-app confirm modal for the save-before-switch step.
 *   confirmSaveOverwrite(fileName) -> Promise<"proceed" | "saveas" | "cancel">
 */
export function confirmSaveOverwrite(fileName) {
  return new Promise((resolve) => {
    const scrim = document.createElement("div");
    scrim.className = "hyp-modal-scrim";
    scrim.style.cssText =
      "position:fixed; inset:0; z-index:1000001; display:flex; align-items:center; justify-content:center; background:rgba(27,31,42,.35);";

    const card = document.createElement("div");
    card.style.cssText =
      "background:var(--white,#fff); border-radius:10px; box-shadow:0 2px 8px rgba(27,31,42,.10),0 24px 48px rgba(27,31,42,.14); width:420px; max-width:92vw; padding:22px 24px; font-family:var(--font-ui),sans-serif;";

    const title = document.createElement("div");
    title.style.cssText = "font-size:15px; font-weight:700; color:var(--ink,#1B1F2A); margin-bottom:8px;";
    title.textContent = "Save over the original file?";

    const body = document.createElement("div");
    body.style.cssText = "font-size:13px; line-height:1.5; color:var(--ink-mut,#5B6172); margin-bottom:18px;";
    body.textContent =
      "Your changes will overwrite “" + (fileName || "the file you opened") +
      "” — the file you opened initially. Proceed, or save as a new file to keep the original?";

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex; gap:8px; justify-content:flex-end;";

    const saveAsBtn = document.createElement("button");
    saveAsBtn.type = "button";
    saveAsBtn.textContent = "Save As…";
    saveAsBtn.style.cssText =
      "height:34px; padding:0 14px; font-size:13px; font-weight:600; border:1px solid var(--line-2,#CFC9BA); border-radius:6px; background:var(--white,#fff); color:var(--ink,#1B1F2A); cursor:pointer;";

    const proceedBtn = document.createElement("button");
    proceedBtn.type = "button";
    proceedBtn.textContent = "Overwrite & continue";
    proceedBtn.style.cssText =
      "height:34px; padding:0 14px; font-size:13px; font-weight:600; border:1px solid var(--ink,#1B1F2A); border-radius:6px; background:var(--ink,#1B1F2A); color:var(--paper,#FAF8F4); cursor:pointer;";

    let done = false;
    function close(choice) {
      if (done) return;
      done = true;
      document.removeEventListener("keydown", onKey, true);
      if (scrim.parentNode) scrim.parentNode.removeChild(scrim);
      resolve(choice);
    }
    function onKey(e) {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close("cancel"); }
    }

    saveAsBtn.addEventListener("click", () => close("saveas"));
    proceedBtn.addEventListener("click", () => close("proceed"));
    scrim.addEventListener("click", (e) => { if (e.target === scrim) close("cancel"); });
    document.addEventListener("keydown", onKey, true);

    actions.appendChild(saveAsBtn);
    actions.appendChild(proceedBtn);
    card.appendChild(title);
    card.appendChild(body);
    card.appendChild(actions);
    scrim.appendChild(card);
    document.body.appendChild(scrim);
    proceedBtn.focus();
  });
}
```

## Step 2 — `app/js/shell/file-controls.js` (Editor→Builder crossing)

Add this import with the existing imports at the top:
```js
import { confirmSaveOverwrite } from '/app/js/shell/confirm-modal.js';
```

Inside `setupOpenInBuilder`'s click handler, the current `try { … }` body (from the previous round) is:
```js
    try {
      let result = await apiClient.save(html);            // silent overwrite of the currently-open file
      if (result && result.no_open_file) {
        result = await apiClient.dialogSaveAs(html);      // never-saved deck → ask once
      }
      if (result && result.cancelled) return; // user cancelled — stay put
      if (!result || !result.ok) {
        getStatusSetter()('Save failed.', 'error');
        return;
      }
      // Save succeeded — navigate to builder with ?file= handoff
      window.location.href = '/app/builder.html?file=' + encodeURIComponent(result.path);
    } catch (err) {
      getStatusSetter()('Save failed: ' + err.message, 'error');
    }
```
Replace it with (confirm before overwriting a known file; Save As keeps the original; brand-new deck goes straight to Save As):
```js
    try {
      const docChip = document.getElementById('doc-chip');
      const docName = document.getElementById('doc-name');
      const hasOpenFile = !!(docChip && !docChip.hidden && docName && docName.textContent);
      let result;
      if (hasOpenFile) {
        const choice = await confirmSaveOverwrite(docName.textContent);
        if (choice === 'cancel') return;                  // stay in the editor
        if (choice === 'proceed') {
          result = await apiClient.save(html);            // overwrite the opened file
          if (result && result.no_open_file) result = await apiClient.dialogSaveAs(html);
        } else {
          result = await apiClient.dialogSaveAs(html);    // Save As — keep the original
        }
      } else {
        result = await apiClient.dialogSaveAs(html);      // never-saved deck → pick a path
      }
      if (result && result.cancelled) return;
      if (!result || !result.ok) {
        getStatusSetter()('Save failed.', 'error');
        return;
      }
      window.location.href = '/app/builder.html?file=' + encodeURIComponent(result.path);
    } catch (err) {
      getStatusSetter()('Save failed: ' + err.message, 'error');
    }
```

## Step 3 — `app/js/builder/builder-main.js` (Builder→Editor crossing)

Add this import with the existing imports at the top of the file:
```js
import { confirmSaveOverwrite } from '/app/js/shell/confirm-modal.js';
```

Inside the `switchToEditorBtn` click handler, the current two lines (from the previous round) are:
```js
        const mode = state.deck.path ? 'overwrite' : 'new-file';
        const result = await saveDeck({ deck: state.deck, items, mode });
```
Replace them with:
```js
        let result;
        if (state.deck.path) {
          const choice = await confirmSaveOverwrite(state.deck.name || state.deck.path);
          if (choice === 'cancel') return;               // stay in the builder
          const mode = (choice === 'proceed') ? 'overwrite' : 'new-file';
          result = await saveDeck({ deck: state.deck, items, mode });
        } else {
          result = await saveDeck({ deck: state.deck, items, mode: 'new-file' });
        }
```
Leave the rest of the handler (the `if (result.cancelled) return;` and the navigation to `/app/?file=…`) unchanged.

## Validation (run before returning)
- `git --no-pager diff -- app/js/shell/confirm-modal.js app/js/shell/file-controls.js app/js/builder/builder-main.js` → confirm the new file, the two imports, and the two handler replacements. `node --check` is NOT valid for these ES modules; do not run it.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave changes in the working tree; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
