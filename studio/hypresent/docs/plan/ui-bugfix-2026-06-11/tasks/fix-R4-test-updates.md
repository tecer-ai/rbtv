---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - tests/e2e/test_f5_comments.py
  - tests/e2e/test_r13_comment_edit_delete.py
  - tests/e2e/test_r14_agent_stamping.py
  - tests/e2e/test_g2_save_with_comments.py
  - tests/e2e/test_pb12_bridge.py
sandbox: workspace-write
commit_policy: none
test_command: python -m pytest tests/e2e/test_f5_comments.py tests/e2e/test_r13_comment_edit_delete.py tests/e2e/test_r14_agent_stamping.py tests/e2e/test_g2_save_with_comments.py tests/e2e/test_pb12_bridge.py -q
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the five allowlisted test files.

# Fix-round R4 — update e2e tests to the NEW (verified, owner-approved) UI behavior

Three app-behavior changes shipped this run and are LIVE-VERIFIED working. The e2e tests still drive the OLD UI and fail. Update them to drive the new UI. **Preserve every assertion's intent — do NOT weaken, skip, or delete assertions to make a test pass. Only change HOW the action is performed.** After editing, RUN the affected tests and confirm green (except the one known pre-existing failure noted below).

## The three behavior changes (and the new drivers)

**(A) Reply is now INLINE, not a floating popover.** OLD: a "Reply" button in the comment card opened the `.hyp-comment-composer` popover (`.hyp-composer-textarea`) and you typed + Ctrl+Enter / Save. NEW: each anchored, unresolved comment card has an inline `<input class="comment-reply-input">` at its bottom — fill it and press **Enter** to send.
- NEW driver for posting a reply to a thread's card `row`: `row.locator(".comment-reply-input").fill("<text>"); row.locator(".comment-reply-input").press("Enter")` then a short wait. (If the test targets the first/only thread, `self.page.locator("#comment-threads .comment-thread .comment-reply-input").first` works.)
- IMPORTANT: NEW comments and the EDIT action STILL use the `.hyp-comment-composer` popover — do NOT change those. Only change steps that post a **reply**.

**(B) Editor save no longer writes a status string.** OLD: after a successful save the editor set `#shell-status` to `"Saved to <path>"`. NEW: it sets `#shell-status` to `""`; the Saved/Unsaved indicator is `#doc-state` (text `"Saved"` / `"Unsaved"`).
- Where a test asserts save success via `#shell-status` text (e.g. `assertIn("Saved", self.page.text_content("#shell-status"))`), replace it with an assertion on `#doc-state`: wait for / assert `self.page.text_content("#doc-state") == "Saved"`. Keep ALL saved-file / island / agent-block assertions exactly as they are — those are the real test.
- NOTE: the BUILDER status `#builder-status` ("Saved: …") is UNCHANGED — do not touch builder-side status assertions.

**(C) Editor↔Builder switch now shows an in-app confirm modal.** OLD: clicking `#open-in-builder-btn` (editor→builder) or `#switch-to-editor-btn` (builder→editor) went straight to a save dialog. NEW: when the deck already has a path, a confirm modal `.hyp-modal-scrim` appears first, with two buttons: **"Overwrite & continue"** (saves over the opened file silently, no dialog) and **"Save As…"** (opens the save dialog to pick a new path). Esc / click-outside cancels and stays.
- For a crossing test that EXPECTS the save dialog + a chosen path (it sets a fake dialog and asserts the saved file at that path): after the crossing click, add `self.page.wait_for_selector(".hyp-modal-scrim", timeout=8000)` then click the Save As button: `self.page.locator(".hyp-modal-scrim button", has_text="Save As").click()`. The rest of the test (fake dialog → path → navigation/assertions) then holds unchanged.
- For a "cancel → no navigation" test: after the crossing click, `self.page.wait_for_selector(".hyp-modal-scrim", timeout=8000)`, then `self.page.keyboard.press("Escape")`, then assert NO navigation happened (the page URL did not change / stays on the builder or editor) and the modal is gone.

## Allowed Paths
- `tests/e2e/test_f5_comments.py`
- `tests/e2e/test_r13_comment_edit_delete.py`
- `tests/e2e/test_r14_agent_stamping.py`
- `tests/e2e/test_g2_save_with_comments.py`
- `tests/e2e/test_pb12_bridge.py`

## Forbidden Paths
- App/runtime/server source (already correct — do NOT change it). No new files. No commits.

## The failing tests to fix (run the suite to see current failures; fix each to green)
- `test_f5_comments.py`: `test_reply_appears_in_agent_block`, `test_resolved_agent_thread_removes_block` (reply driver A).
- `test_r13_comment_edit_delete.py`: `test_e_r13_5_delete_reply_undo_restores_index`, `test_e_r13_6_edit_reply_body` (reply driver A).
- `test_r14_agent_stamping.py`: `test_e_r14_5_block_format_completeness`, `test_e_r14_7_node_count_guard_safe_with_stamps` (reply driver A; and/or a `#shell-status` assertion → driver B).
- `test_g2_save_with_comments.py`: `test_e_g2_1_…`, `test_e_g2_3_…`, `test_e_g2_4_…`, `test_e_g2_5_…` (save-status driver B — change `#shell-status` checks to `#doc-state`; keep the file/island assertions).
- `test_pb12_bridge.py`: `test_builder_to_editor_crossing`, `test_round_trip_preserves_order` (driver C, click "Save As…" in the modal), `test_cancel_builder_to_editor_no_navigation`, `test_cancel_editor_to_builder_no_navigation` (driver C, Esc to cancel).
- KNOWN PRE-EXISTING failure to LEAVE AS-IS (do not try to fix, it is unrelated — a missing-deck-asset layout reflow): `test_f5_comments.py::test_tagging_does_not_move_marker`.

For each failing test, READ it, apply the matching driver, and RUN it to confirm it passes. Investigate the exact reason each one fails (it will be one of A/B/C) before editing.

## Validation (run before returning)
- Run the full set: `python -m pytest tests/e2e/test_f5_comments.py tests/e2e/test_r13_comment_edit_delete.py tests/e2e/test_r14_agent_stamping.py tests/e2e/test_g2_save_with_comments.py tests/e2e/test_pb12_bridge.py -q` and report the pass/fail tail. Target: ALL pass except the one pre-existing `test_tagging_does_not_move_marker`.
- `git --no-pager diff --stat -- tests/e2e/` to show the scope.
Report both, with EXIT codes, in `validation`.

## Commit Rule
Do NOT commit. Leave the test files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
