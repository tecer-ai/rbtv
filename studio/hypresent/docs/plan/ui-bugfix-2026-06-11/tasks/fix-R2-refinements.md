---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/main.js
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the three allowlisted files. Use ASCII-only identifiers.

# Fix-round R2 — owner refinements to fixes 4 (status), 5 (reply UX), 6 (save UX)

Three changes from owner feedback after using the build.

## Allowed Paths
- `app/js/main.js`
- `app/js/shell/file-controls.js`
- `app/js/builder/builder-main.js`

## Forbidden Paths
- Every other file. No new files. No commits.

---

## Fix 4 (refine) — stop the leftover "Saved" status contradicting the chip

Symptom: after save → edit, the top bar shows "Saved  teste.html • Unsaved" — the `#shell-status` text "Saved" lingers while the chip flips to Unsaved. The chip (`• Saved/Unsaved`) is the only indicator we want.

**Change in `app/js/main.js`:** replace EVERY occurrence of `setStatus("Saved", "success");` with `setStatus("");` (there are three — the Save no-open-file fallback, the normal Save, and Save As). This clears the status area on save instead of printing a lingering "Saved". Change nothing else about those handlers.

---

## Fix 5 (refine) — reply field inline in the comment card (Google-Docs style), not a floating popover

Symptom: clicking Reply opens a floating popover that lands at the top of the page (the anchor element is scrolled off-view). Owner wants the reply field inline at the bottom of the comment card in the right panel, like Google Docs.

In `app/js/main.js`, function `createThreadEl(thread, isUnanchored = false)`:

**(5a) Remove the floating-popover Reply button.** Delete the entire `replyBtn` block (the `const replyBtn = document.createElement("button");` … through `actions.appendChild(replyBtn);`). The Reply button must no longer be created or appended to `actions`. Leave Resolve / Edit / Delete / the agent toggle exactly as they are. (Keep `openComposer` and its imports — it is still used for NEW comments and EDIT.)

**(5b) Add an inline reply input at the bottom of the card.** After the block that appends the replies:
```js
  if (repliesDiv) {
    div.appendChild(repliesDiv);
  }
```
insert this (an always-visible compact reply field for anchored, unresolved threads; Enter sends, Shift+Enter newline is not needed for a single-line input):
```js
  if (!isUnanchored && !thread.resolved) {
    const replyForm = document.createElement("div");
    replyForm.className = "comment-reply-form";
    const replyInput = document.createElement("input");
    replyInput.type = "text";
    replyInput.className = "comment-reply-input";
    replyInput.placeholder = "Reply…";
    replyInput.style.cssText =
      "width:100%; margin-top:10px; height:32px; padding:0 12px; border:1px solid var(--line-2); border-radius:999px; background:var(--white); font-size:12.5px; color:var(--ink);";
    replyInput.addEventListener("click", (e) => e.stopPropagation());
    replyInput.addEventListener("keydown", async (e) => {
      e.stopPropagation();
      if (e.key === "Enter") {
        e.preventDefault();
        const text = replyInput.value.trim();
        if (!text) return;
        const author = getAuthorName();
        replyInput.disabled = true;
        try {
          await bridge.command("reply-comment", { commentId: thread.id, body: text, author });
          await refreshCommentPanel();
        } catch (err) {
          console.error("Reply failed:", err.message);
          replyInput.disabled = false;
        }
      }
    });
    replyForm.appendChild(replyInput);
    div.appendChild(replyForm);
  }
```
`getAuthorName`, `bridge`, and `refreshCommentPanel` are already in scope in this module. Do not redefine them.

---

## Fix 6 (refine) — switch saves to the existing file silently; OS dialog only for a never-saved deck

Symptom: switching pops the native save dialog with a near-invisible topbar message. Owner wants no confusing dialog when the deck already has a file.

**(6a) `app/js/shell/file-controls.js`, `setupOpenInBuilder`'s click handler.** Currently it shows a status line then always calls `apiClient.dialogSaveAs(html)`. Replace the block from the `getStatusSetter()('Choose where to save…', '');` line through the `const result = await apiClient.dialogSaveAs(html);` line with a silent-save-first version:
```js
      let result = await apiClient.save(html);            // silent overwrite of the currently-open file
      if (result && result.no_open_file) {
        result = await apiClient.dialogSaveAs(html);      // never-saved deck → ask once
      }
```
Leave the rest of the handler (the `if (result && result.cancelled) return;`, the `!result || !result.ok` error branch, and the `window.location.href = '/app/builder.html?file=' + …` navigation) unchanged. Remove the `getStatusSetter()('Choose where to save…', '');` line entirely.

**(6b) `app/js/builder/builder-main.js`, the `switchToEditorBtn` click handler.** Currently:
```js
        setStatus('Choose where to save the deck — it then opens in the Editor.', '');
        const result = await saveDeck({ deck: state.deck, items, mode: 'new-file' });
```
Replace those two lines with (overwrite silently when the deck already has a path; dialog only for a never-saved deck):
```js
        const mode = state.deck.path ? 'overwrite' : 'new-file';
        const result = await saveDeck({ deck: state.deck, items, mode });
```
Leave the rest of the handler unchanged.

---

## Validation (run before returning)
- `git --no-pager diff -- app/js/main.js app/js/shell/file-controls.js app/js/builder/builder-main.js` → confirm: three `setStatus("Saved"…)`→`setStatus("")`; the Reply button removed + the inline reply input added in `createThreadEl`; the two silent-save edits. No stray changes; ASCII identifiers only.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
