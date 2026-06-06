import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H


class TestG2SaveWithComments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)")
        cls.proc, cls.base = H.start_server(8787, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.copy = H.copy_fixture()
        self.page = self.browser.new_page()
        H.preset_author(self.page)
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def tearDown(self):
        self.page.close()

    # ------------------------------------------------------------------ #

    def add_comment(self, text, agent=False):
        page = self.page
        page.frame_locator("iframe.doc-frame").locator(".slide-title").first.click()
        page.click("#comment-btn")
        page.fill(".hyp-composer-textarea", text)
        if agent:
            page.check(".hyp-composer-agent input")
            page.focus(".hyp-composer-textarea")
        page.keyboard.press("Control+Enter")
        page.wait_for_selector("#comment-threads .comment-thread")

    def save_as(self, out):
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)

    # ------------------------------------------------------------------ #
    # E-G2-1
    # ------------------------------------------------------------------ #
    def test_e_g2_1_save_with_user_comment_succeeds(self):
        out1 = self.copy.replace(".html", "-out1.html")
        self.add_comment("c1")
        self.save_as(out1)
        status = self.page.text_content("#shell-status")
        self.assertIn("Saved", status)
        self.assertTrue(os.path.exists(out1))
        self.assertGreater(os.path.getsize(out1), 0)

    # ------------------------------------------------------------------ #
    # E-G2-2
    # ------------------------------------------------------------------ #
    def test_e_g2_2_saved_file_contains_exactly_one_comments_block(self):
        out1 = self.copy.replace(".html", "-out1.html")
        self.add_comment("c1")
        self.save_as(out1)
        with open(out1, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count('id="hyp-comments"'), 1)
        # extract and parse the JSON
        import re
        m = re.search(r'<script type="application/json" id="hyp-comments">(.*?)</script>', text, re.S)
        self.assertIsNotNone(m)
        data = json.loads(m.group(1))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    # ------------------------------------------------------------------ #
    # E-G2-3
    # ------------------------------------------------------------------ #
    def test_e_g2_3_save_with_agent_comment_and_guard(self):
        out2 = self.copy.replace(".html", "-out2.html")
        self.add_comment("c2", agent=True)
        self.save_as(out2)
        status = self.page.text_content("#shell-status")
        self.assertIn("Saved", status)
        with open(out2, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('id="hyp-comments"', text)
        self.assertIn("===== HYPRESENT AGENT INSTRUCTIONS =====", text)

    # ------------------------------------------------------------------ #
    # E-G2-4
    # ------------------------------------------------------------------ #
    def test_e_g2_4_roundtrip_no_agent_block_duplication(self):
        out2 = self.copy.replace(".html", "-out2.html")
        out3 = self.copy.replace(".html", "-out3.html")
        self.add_comment("c2", agent=True)
        self.save_as(out2)
        # open the saved file again via dialog seam
        H.open_via_dialog_ui(self.page, self.base, out2)
        self.page.wait_for_timeout(500)
        self.save_as(out3)
        status = self.page.text_content("#shell-status")
        self.assertIn("Saved", status)
        with open(out3, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count("===== HYPRESENT AGENT INSTRUCTIONS ====="), 1)

    # ------------------------------------------------------------------ #
    # E-G2-5
    # ------------------------------------------------------------------ #
    def test_e_g2_5_no_comments_means_chrome_free(self):
        out5 = self.copy.replace(".html", "-out5.html")
        self.save_as(out5)
        status = self.page.text_content("#shell-status")
        self.assertIn("Saved", status)
        with open(out5, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("data-hyp-", text)
        self.assertNotIn("/runtime/js/runtime-main.js", text)
        self.assertNotIn('id="hyp-comments"', text)
        self.assertNotIn("HYPRESENT AGENT INSTRUCTIONS", text)
        import re
        self.assertEqual(re.findall(r'class="[^"]*\bhyp-', text), [])


import json  # noqa: E402

if __name__ == "__main__":
    unittest.main()
