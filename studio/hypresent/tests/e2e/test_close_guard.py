"""E2E: unsaved-changes close-guard (beforeunload).

Verifies the editor shell asks the browser to confirm before the tab is closed or
refreshed while the open document has unsaved edits, and stays silent when the
document is clean (freshly opened or just saved).

Runs headless by default (CI). Set HYP_HEADED=1 to watch it; set HYP_SHOT_DIR to a
folder to capture top-bar screenshots + results.json (used for the done-gate
evidence run). Uses a synthetic fixture, so it runs without the gitignored sample.
"""
import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8791
HEADED = os.environ.get("HYP_HEADED") == "1"
SHOT_DIR = os.environ.get("HYP_SHOT_DIR")
FIXTURE = "agent-comments.html"
COMMENT_ANCHOR = ".hd"   # a heading with text in agent-comments.html (registered editable)


def _shot(page, name):
    if not SHOT_DIR:
        return
    os.makedirs(SHOT_DIR, exist_ok=True)
    page.screenshot(path=os.path.join(SHOT_DIR, name))


class TestCloseGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=not HEADED)
        cls.results = {}

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)
        if SHOT_DIR:
            os.makedirs(SHOT_DIR, exist_ok=True)
            with open(os.path.join(SHOT_DIR, "results.json"), "w", encoding="utf-8") as fh:
                json.dump(cls.results, fh, indent=2)

    def _open_clean(self):
        page = self.browser.new_page()
        H.preset_author(page)
        page.goto(self.base + "/app/")
        H.open_via_dialog_ui(page, self.base, H.copy_synthetic(FIXTURE))
        return page

    def _make_dirty(self, page):
        """Add a comment (the user's real scenario) so the document goes Unsaved."""
        page.frame_locator("iframe.doc-frame").locator(COMMENT_ANCHOR).first.click()
        page.click("#comment-btn")
        page.fill(".hyp-composer-textarea", "close-guard exercise")
        page.keyboard.press("Control+Enter")
        page.wait_for_selector("#comment-threads .comment-thread")

    def _attempt_close(self, page):
        """Run beforeunload on a real tab close. Returns the dialog type seen (or None).
        beforeunload is dismissed (== Cancel), so a guarded page stays open for asserts."""
        seen = {"type": None}
        page.on("dialog", lambda d: (seen.__setitem__("type", d.type), d.dismiss()))
        try:
            page.close(run_before_unload=True)
        except Exception:
            pass
        if not page.is_closed():
            page.wait_for_timeout(300)
        return seen["type"]

    # C1 — unsaved edits → refresh/close raises the leave-confirm; Cancel keeps the doc.
    # "Refresh" is a named C1 trigger and lets us prove BOTH halves in one real gesture:
    # the beforeunload prompt fires, and dismissing it (== Cancel) abandons the navigation
    # so the work survives. (page.close(run_before_unload=True) force-closes regardless of
    # the dialog choice, so it can only prove the prompt fired, not that Cancel keeps work.)
    def test_c1_dirty_refresh_prompts_and_cancel_keeps_doc(self):
        page = self._open_clean()
        self._make_dirty(page)
        self.assertEqual(page.text_content("#doc-state"), "Unsaved")
        _shot(page, "c1-unsaved-chip.png")
        seen = {"type": None}
        page.on("dialog", lambda d: (seen.__setitem__("type", d.type), d.dismiss()))  # Cancel
        try:
            page.reload(timeout=2500)
        except Exception:
            pass  # cancelled by the dismissed beforeunload → reload does not complete
        thread = page.query_selector("#comment-threads .comment-thread")
        chip = page.text_content("#doc-state") if not page.is_closed() else None
        self.__class__.results["C1"] = {
            "dialog": seen["type"], "thread_present": thread is not None, "chip": chip,
        }
        self.assertEqual(seen["type"], "beforeunload")   # browser raised the leave-confirm
        self.assertIsNotNone(thread)                     # Cancel kept the work
        self.assertEqual(chip, "Unsaved")
        page.close()

    # C2 — freshly opened, no edits → no prompt.
    def test_c2_clean_open_close_silent(self):
        page = self._open_clean()
        self.assertEqual(page.text_content("#doc-state"), "Saved")
        _shot(page, "c2-saved-chip.png")
        seen = self._attempt_close(page)
        self.__class__.results["C2"] = {"dialog": seen, "page_closed": page.is_closed()}
        self.assertIsNone(seen)

    # C3 — edited then saved → no prompt (save clears the guard).
    def test_c3_saved_close_silent(self):
        page = self._open_clean()
        self._make_dirty(page)
        self.assertEqual(page.text_content("#doc-state"), "Unsaved")
        page.click("#save-btn")
        page.wait_for_function(
            "() => document.getElementById('doc-state')?.textContent === 'Saved'",
            timeout=5000,
        )
        _shot(page, "c3-saved-after-edit-chip.png")
        seen = self._attempt_close(page)
        self.__class__.results["C3"] = {"dialog": seen, "page_closed": page.is_closed()}
        self.assertIsNone(seen)


if __name__ == "__main__":
    unittest.main()
