import os
import sys
import unittest
import json
import tempfile

# e2e import bootstrap (R08)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8785


class F5CommentTests(unittest.TestCase):
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
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def tearDown(self):
        self.page.close()

    # ---- helpers ----

    def _select_first_slide_title(self):
        frame = self.page.frame_locator("iframe.doc-frame")
        frame.locator(".slide-title").first.click()
        self.page.wait_for_timeout(200)

    def _open_composer(self):
        self._select_first_slide_title()
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)

    def _type_and_submit(self, text, agent=False):
        if agent:
            self.page.locator(".hyp-composer-agent input").check()
        textarea = self.page.locator(".hyp-composer-textarea")
        textarea.fill(text)
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

    def _read_island(self):
        raw = H.doc_eval(
            self.page,
            "const i=doc.getElementById('hyp-comments'); return i?i.textContent:null;",
        )
        if raw:
            return json.loads(raw)
        return []

    def _save_as_and_read(self, out_path):
        H.set_fake_dialog(self.base, out_path)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        with open(out_path, encoding="utf-8") as fh:
            return fh.read()

    # ---- tests ----

    def test_composer_opens_with_no_prompt(self):          # E-F5-1
        prompts = []
        self.page.on("dialog", lambda d: (prompts.append(d.type), d.dismiss()))
        self._select_first_slide_title()
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)

        composer = self.page.query_selector(".hyp-comment-composer")
        self.assertIsNotNone(composer)
        self.assertIsNotNone(self.page.query_selector(".hyp-composer-textarea"))
        self.assertIsNotNone(self.page.query_selector(".hyp-composer-agent input"))
        self.assertIsNotNone(self.page.query_selector(".hyp-composer-save"))
        self.assertIsNotNone(self.page.query_selector(".hyp-composer-cancel"))
        self.assertEqual(prompts, [])

    def test_escape_closes_composer(self):                 # E-F5-2
        self._open_composer()
        textarea = self.page.locator(".hyp-composer-textarea")
        textarea.fill("x")
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

        self.assertIsNone(self.page.query_selector(".hyp-comment-composer"))
        cards = self.page.query_selector_all("#comment-threads .comment-thread")
        self.assertEqual(len(cards), 0)

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

    def test_submit_creates_thread_and_marker(self):       # E-F5-4
        self._open_composer()
        self._type_and_submit("hello")

        cards = self.page.query_selector_all("#comment-threads .comment-thread")
        self.assertEqual(len(cards), 1)

        marker = H.doc_eval(
            self.page,
            "return doc.querySelector('.hyp-comment-marker') ? true : false;",
        )
        self.assertTrue(marker)

    def test_agent_checkbox_on_submission(self):           # E-F5-5
        self._open_composer()
        self._type_and_submit("Replace bullets", agent=True)

        island = self._read_island()
        self.assertTrue(len(island) > 0)
        self.assertEqual(island[-1]["agentInstruction"], True)

    def test_agent_toggle_in_panel(self):                  # E-F5-6
        self._open_composer()
        self._type_and_submit("normal comment")

        # toggle on
        self.page.locator("#comment-threads .comment-agent-toggle").first.click()
        self.page.wait_for_timeout(300)
        island = self._read_island()
        self.assertEqual(island[0]["agentInstruction"], True)

        # toggle off
        self.page.locator("#comment-threads .comment-agent-toggle").first.click()
        self.page.wait_for_timeout(300)
        island = self._read_island()
        self.assertEqual(island[0]["agentInstruction"], False)

    def test_save_as_includes_agent_block_first_in_head(self):  # E-F5-7
        self._open_composer()
        self._type_and_submit("Replace bullets", agent=True)

        out = os.path.join(os.path.dirname(self.copy), "out_f5_7.html")
        html = self._save_as_and_read(out)

        self.assertIn("===== HYPRESENT AGENT INSTRUCTIONS =====", html)
        self.assertIn(
            "This block is auto-generated from agent-tagged review comments in this file.",
            html,
        )
        self.assertIn("[agent:", html)
        self.assertIn("target: [data-hyp-agent~=", html)
        self.assertIn("context:", html)
        self.assertIn("instruction: Replace bullets", html)
        self.assertIn("author:", html)
        self.assertIn("date:", html)

        agent_idx = html.find("===== HYPRESENT AGENT INSTRUCTIONS =====")
        link_idx = html.find("<link")
        style_idx = html.find("<style")
        self.assertLess(agent_idx, link_idx)
        self.assertLess(agent_idx, style_idx)

    def test_non_agent_does_not_emit_block(self):          # E-F5-8
        self._open_composer()
        self._type_and_submit("just a note")

        out = os.path.join(os.path.dirname(self.copy), "out_f5_8.html")
        html = self._save_as_and_read(out)
        self.assertNotIn("HYPRESENT AGENT INSTRUCTIONS", html)

    def test_agent_block_escapes_body(self):               # E-F5-9
        self._open_composer()
        self._type_and_submit("a --> b", agent=True)

        out = os.path.join(os.path.dirname(self.copy), "out_f5_9.html")
        html = self._save_as_and_read(out)

        block_start = html.find("===== HYPRESENT AGENT INSTRUCTIONS =====")
        block_end = html.find("===== END HYPRESENT AGENT INSTRUCTIONS =====")
        self.assertGreater(block_start, -1)
        self.assertGreater(block_end, -1)

        region = html[block_start:block_end]
        self.assertIn("a --&gt; b", region)
        # raw --> must not appear inside the region before the closing line
        self.assertNotIn("a --> b", region)

    def test_reply_appears_in_agent_block(self):           # E-F5-10
        self._open_composer()
        self._type_and_submit("Replace bullets", agent=True)

        # click Reply on the panel card
        self.page.locator("#comment-threads .comment-action-btn").first.click()
        self.page.wait_for_timeout(200)

        # reply composer should appear
        self.page.locator(".hyp-composer-textarea").fill("also bold it")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

        out = os.path.join(os.path.dirname(self.copy), "out_f5_10.html")
        html = self._save_as_and_read(out)
        self.assertIn("reply: also bold it — Tester", html)

    def test_resolved_agent_thread_removes_block(self):    # E-F5-11
        self._open_composer()
        self._type_and_submit("Replace bullets", agent=True)

        out1 = os.path.join(os.path.dirname(self.copy), "out_f5_11a.html")
        html1 = self._save_as_and_read(out1)
        self.assertIn("HYPRESENT AGENT INSTRUCTIONS", html1)

        # resolve the thread
        btns = self.page.query_selector_all("#comment-threads .comment-action-btn")
        # second button is Resolve (first is Reply)
        resolve_btn = btns[1]
        resolve_btn.click()
        self.page.wait_for_timeout(300)

        out2 = os.path.join(os.path.dirname(self.copy), "out_f5_11b.html")
        html2 = self._save_as_and_read(out2)
        self.assertNotIn("HYPRESENT AGENT INSTRUCTIONS", html2)

    def test_round_trip_reopens_agent_thread(self):        # E-F5-12
        self._open_composer()
        self._type_and_submit("Replace bullets", agent=True)

        out = os.path.join(os.path.dirname(self.copy), "out_f5_12.html")
        self._save_as_and_read(out)

        # open the saved file via dialog seam
        H.set_fake_dialog(self.base, out)
        self.page.click("#open-btn")
        H.wait_runtime_ready(self.page)
        self.page.wait_for_timeout(300)

        # island should still have agentInstruction true
        island = self._read_island()
        self.assertEqual(len(island), 1)
        self.assertEqual(island[0]["agentInstruction"], True)

        # marker should be re-anchored
        marker = H.doc_eval(
            self.page,
            "return doc.querySelector('.hyp-comment-marker') ? true : false;",
        )
        self.assertTrue(marker)

    def test_tagging_does_not_move_marker(self):           # E-F5-13
        self._open_composer()
        self._type_and_submit("stable anchor")

        before = H.doc_eval(
            self.page,
            """const m = doc.querySelector('.hyp-comment-marker');
               if (!m) return null;
               const r = m.getBoundingClientRect();
               return {top:r.top, left:r.left, width:r.width, height:r.height, display:m.style.display};""",
        )
        self.assertIsNotNone(before)

        self.page.locator("#comment-threads .comment-agent-toggle").first.click()
        self.page.wait_for_timeout(300)

        after = H.doc_eval(
            self.page,
            """const m = doc.querySelector('.hyp-comment-marker');
               if (!m) return null;
               const r = m.getBoundingClientRect();
               return {top:r.top, left:r.left, width:r.width, height:r.height, display:m.style.display};""",
        )
        self.assertIsNotNone(after)

        self.assertEqual(before["top"], after["top"])
        self.assertEqual(before["left"], after["left"])
        self.assertEqual(before["width"], after["width"])
        self.assertEqual(before["height"], after["height"])
        self.assertEqual(before["display"], after["display"])


if __name__ == "__main__":
    unittest.main()
