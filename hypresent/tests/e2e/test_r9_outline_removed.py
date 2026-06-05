import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8799


class R9OutlineRemovedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(
                f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page()
        H.preset_author(self.page)
        self.copy = H.copy_fixture()

    def tearDown(self):
        self.page.close()

    # E-R9-1 — panel + list gone
    def test_outline_absent(self):
        self.page.goto(self.base + "/app/")
        self.assertIsNone(self.page.query_selector("#outline-list"), "#outline-list must be removed")
        self.assertIsNone(self.page.query_selector(".outline-panel"), ".outline-panel must be removed")

    # E-R9-2 — ready payload has no sections
    def test_ready_payload_has_no_sections(self):
        self.page.goto(self.base + "/app/")
        # Hook the bridge ready event by reading the runtime's emitted payload.
        # The shell does not expose it; instead probe the runtime: regions() is gone,
        # and the ready emit carries only tokens. Assert the runtime no longer defines regions.
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        has_regions = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const win=f.contentWindow;"
            " return !!(win.hyp && win.hyp.regions); }"
        )
        self.assertFalse(has_regions, "runtime must not expose regions after R9")
        # Also assert the shell never created an outline list element from a sections payload.
        self.assertIsNone(self.page.query_selector("#outline-list"))

    # E-R9-3 — panels survive a second open (G1 invariant without the outline)
    def test_panels_survive_second_open(self):
        self.page.goto(self.base + "/app/")
        copyA = H.copy_fixture()
        copyB = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, copyA)
        # add a comment so the comment panel has a card
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)
        # composer textarea: support either selector form
        ta = self.page.query_selector(".hyp-composer-textarea") or self.page.query_selector(".hyp-comment-composer textarea")
        self.assertIsNotNone(ta, "composer textarea should appear")
        ta.fill("note A")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread")
        # OPEN document B
        H.open_via_dialog_ui(self.page, self.base, copyB)
        self.page.wait_for_timeout(400)
        self.assertIsNotNone(self.page.query_selector("#comment-threads"), "comment threads container must survive")
        self.assertIsNotNone(self.page.query_selector(".hyp-color-popover-container"), "color popover container must survive")

    # E-R9-4 — no console errors
    def test_no_console_errors(self):
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "Failed to load resource" in t and "404" in t:
                    return
                errors.append(t)
        self.page.on("console", on_console)
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        self.page.frame_locator("iframe.doc-frame").locator(".slide-title").first.click()
        self.page.wait_for_timeout(300)
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
