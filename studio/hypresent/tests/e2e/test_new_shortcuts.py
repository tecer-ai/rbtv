"""E2E for the added shortcuts: Ctrl+Shift+M (comment for agents),
Ctrl+Shift+Q (Save), Ctrl+Q (Save As).

Keys are pressed on the PARENT page (focus moved off the iframe by clicking a
neutral top-frame element first), because a synthetic modified keydown does not
reliably cross into the iframe document in headless Chromium/Windows. The runtime
selection is held in the iframe regardless of where focus is, so a parent-focused
shortcut still acts on the selected element.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8816


def _iframe_origin(page):
    return page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")


def _rect_in_iframe(page, selector):
    return H.doc_eval(page, f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};")


class NewShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(H.SYN_DIR, "agent-comments.html")):
            raise AssertionError("Required synthetic fixture missing: agent-comments.html")
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
        self.opened = H.copy_synthetic("agent-comments.html")
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.opened)

    def tearDown(self):
        self.page.close()

    def _read_island(self):
        txt = H.doc_eval(self.page, "const i=doc.getElementById('hyp-comments'); return i?i.textContent:null;")
        if not txt:
            return []
        data = json.loads(txt)
        return data["threads"] if isinstance(data, dict) and "threads" in data else data

    def _select(self, native_id):
        sel = f'#{native_id}'
        H.doc_eval(self.page, f"const e=doc.querySelector({sel!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(200)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, sel)
        self.assertIsNotNone(rect, f"{sel} not found")
        self.page.mouse.click(origin["x"] + rect["x"] + 5, origin["y"] + rect["y"] + 5)
        self.page.wait_for_timeout(250)

    def _focus_parent(self):
        # Move focus off the iframe so the parent keydown handler receives the keys.
        # The brand mark is a no-op click target in the top frame.
        self.page.click(".brand")
        self.page.wait_for_timeout(100)

    # ---- Ctrl+Shift+M opens the composer with "For agents" pre-checked ----
    def test_ctrl_shift_m_opens_agent_tagged_composer(self):
        self._select("p-lead")
        self._focus_parent()
        self.page.keyboard.press("Control+Shift+M")
        self.page.wait_for_timeout(250)
        composer = self.page.locator(".hyp-comment-composer").first
        self.assertGreater(composer.count(), 0, "Ctrl+Shift+M should open the comment composer")
        cb = self.page.locator(".hyp-comment-composer .hyp-composer-agent input").first
        self.assertGreater(cb.count(), 0, "agent composer should carry the For-agents checkbox")
        self.assertTrue(cb.is_checked(), "Ctrl+Shift+M must pre-check For agents")

        # Completing the composer persists an agent-tagged comment.
        self.page.locator(".hyp-composer-textarea").first.fill("do the thing")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)
        threads = self._read_island()
        self.assertEqual(len(threads), 1)
        self.assertTrue(threads[0].get("agentInstruction"), "comment created via Ctrl+Shift+M must be agent-tagged")

    # ---- plain Ctrl+M opens the composer WITHOUT For agents pre-checked ----
    def test_ctrl_m_plain_not_agent_checked(self):
        self._select("p-lead")
        self._focus_parent()
        self.page.keyboard.press("Control+m")
        self.page.wait_for_timeout(250)
        cb = self.page.locator(".hyp-comment-composer .hyp-composer-agent input").first
        self.assertGreater(cb.count(), 0)
        self.assertFalse(cb.is_checked(), "plain Ctrl+M must NOT pre-check For agents")

    # ---- Ctrl+Shift+Q saves (overwrites) the open file → chip returns to Saved ----
    def test_ctrl_shift_q_saves_open_file(self):
        # Make the document dirty by adding a comment.
        self._select("p-lead")
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)
        self.page.locator(".hyp-composer-textarea").first.fill("makes it dirty")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.locator("#doc-state").text_content(), "Unsaved")

        self._focus_parent()
        self.page.keyboard.press("Control+Shift+Q")
        self.page.wait_for_timeout(500)
        self.assertEqual(self.page.locator("#doc-state").text_content(), "Saved",
                         "Ctrl+Shift+Q should save the open file and mark it Saved")
        # And the overwrite landed on disk: the saved comment island is in the file.
        with open(self.opened, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("makes it dirty", html)

    # ---- Ctrl+Q triggers Save As → writes to the chosen path ----
    def test_ctrl_q_save_as_writes_new_path(self):
        out = tempfile.mktemp(suffix="-ctrlq-saveas.html")
        H.set_fake_dialog(self.base, out)
        self._focus_parent()
        self.page.keyboard.press("Control+q")
        self.page.wait_for_timeout(600)
        self.assertTrue(os.path.exists(out), "Ctrl+Q (Save As) should write the chosen file")
        with open(out, encoding="utf-8") as fh:
            html = fh.read()
        self.assertIn("<html", html.lower())


if __name__ == "__main__":
    unittest.main()
