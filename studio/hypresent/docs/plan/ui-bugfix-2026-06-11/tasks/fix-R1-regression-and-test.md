---
execution_kind: code
executor: codex
allowed_workdir: C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent
allowlist:
  - app/js/shell/file-controls.js
  - tests/e2e/test_f5_comments.py
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
`--sandbox workspace-write` + `-c approval_policy="never"`. Edit ONLY the two allowlisted files.

# Fix-round R1 — file-controls.js regression + test update for the new Enter behavior

Two fixes from e2e triage.

## Allowed Paths
- `app/js/shell/file-controls.js`
- `tests/e2e/test_f5_comments.py`

## Forbidden Paths
- Every other file. No new files. No commits.

---

## Fix A — `app/js/shell/file-controls.js`: `setStatusSetter` is undefined (ReferenceError)

`setupOpenInBuilder` destructures the param named **`getStatusSetter`**, but the body calls **`setStatusSetter()`** in four places (lines ~46, ~56, ~60, ~66). `setStatusSetter` is undefined → a ReferenceError. The previously-added pre-dialog status line (line ~56) is in the happy path, so every Editor→Builder crossing now throws and breaks.

**Change: replace EVERY occurrence of `setStatusSetter` with `getStatusSetter` in this file** (all four call sites). After the change, each call reads `getStatusSetter()('...', '...')`. Do not change anything else (not the destructured param, not the messages).

## Fix B — `tests/e2e/test_f5_comments.py`: update E-F5-3 for the new Enter behavior

The composer now SUBMITS on plain Enter and inserts a newline on **Shift+Enter** (Ctrl/Cmd+Enter still submits). The old test `test_plain_enter_inserts_newline` (around lines 107-117) asserts the obsolete behavior. Replace the ENTIRE method:

```python
    def test_plain_enter_inserts_newline(self):            # E-F5-3
        self._open_composer()
        textarea = self.page.locator(".hyp-composer-textarea")
        textarea.click()
        textarea.type("do X")
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(100)

        val = textarea.input_value()
        self.assertIn("\n", val)
        self.assertIsNotNone(self.page.query_selector(".hyp-comment-composer"))
```

with:

```python
    def test_enter_submits_shift_enter_newline(self):      # E-F5-3 (Enter submits; Shift+Enter = newline)
        self._open_composer()
        textarea = self.page.locator(".hyp-composer-textarea")
        textarea.click()
        textarea.type("line one")
        # Shift+Enter inserts a newline and keeps the composer open
        self.page.keyboard.press("Shift+Enter")
        self.page.wait_for_timeout(100)
        self.assertIn("\n", textarea.input_value())
        self.assertIsNotNone(self.page.query_selector(".hyp-comment-composer"))
        # Plain Enter submits: composer closes and a thread is created
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(300)
        self.assertIsNone(self.page.query_selector(".hyp-comment-composer"))
        cards = self.page.query_selector_all("#comment-threads .comment-thread")
        self.assertEqual(len(cards), 1)
```

## Validation (run before returning)
- `git --no-pager diff -- app/js/shell/file-controls.js tests/e2e/test_f5_comments.py` → confirm: file-controls.js has the four `setStatusSetter`→`getStatusSetter` renames and nothing else; the test method was replaced as above.
Report the command, output, and EXIT in `validation`.

## Commit Rule
Do NOT commit. Leave the files modified; the conductor reviews and commits.

## Return Format (the five-field schema, exactly)
- `status` · `landed` · `validation` · `concerns` · `open_questions`
