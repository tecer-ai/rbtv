import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
import urllib.request
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8788


class ExitSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(H.FIXTURE):
            raise AssertionError(f"Required fixture missing: {H.FIXTURE} (gitignored per U10a; restore it locally before running tests)")
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

    # ── E-EXIT-1 ──────────────────────────────────────────────────────────────
    def test_server_up_and_runtime_served(self):
        with urllib.request.urlopen(self.base + "/app/") as r:
            self.assertEqual(r.status, 200)
        with urllib.request.urlopen(self.base + "/runtime/js/runtime-main.js") as r:
            self.assertEqual(r.status, 200)
            ct = r.headers.get("Content-Type", "")
            self.assertIn("javascript", ct.lower(), f"runtime content-type was: {ct}")

    # ── E-EXIT-2 ──────────────────────────────────────────────────────────────
    def test_full_smoke_zero_console_errors(self):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        frame = self.page.frame_locator("iframe.doc-frame")

        # Attach console listener AFTER the document is loaded so initial asset 404s are not caught.
        errors = []
        def on_console(m):
            if m.type == "error":
                url = (m.location.get("url", "") if m.location else "")
                errors.append((m.type, m.text, url))
        self.page.on("console", on_console)

        # (a) text edit: double-click a slide title, type, Escape
        title = frame.locator(".slide-title").first
        title.dblclick()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(" SMOKE")
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(200)

        # (b) resize: select an element, drag a resize handle a little
        title.click()
        self.page.wait_for_timeout(300)
        handle_info = H.doc_eval(
            self.page,
            "const h=doc.querySelector('.moveable-control-box .moveable-e') || doc.querySelector('.moveable-control-box .moveable-se');"
            "if(!h) return null; const r=h.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        if handle_info:
            fb = self.page.evaluate(
                "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
            )
            hx = fb["x"] + handle_info["x"] + handle_info["w"] / 2
            hy = fb["y"] + handle_info["y"] + handle_info["h"] / 2
            self.page.mouse.move(hx, hy)
            self.page.mouse.down()
            self.page.mouse.move(hx + 15, hy + 5, steps=5)
            self.page.mouse.up()
            self.page.wait_for_timeout(200)

        # (c) move→translate: select an element, drag body and drop in empty space
        title.click()
        self.page.wait_for_timeout(300)
        box = title.bounding_box()
        if box:
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            self.page.mouse.move(cx, cy)
            self.page.mouse.down()
            self.page.mouse.move(cx + 200, cy, steps=10)
            self.page.mouse.up()
            self.page.wait_for_timeout(200)

        # (d) change a palette token color via the popover token input
        token_input = self.page.query_selector('.hyp-token-list .hyp-coloris-input[data-scope="token"]')
        if token_input:
            self.page.eval_on_selector(
                '.hyp-token-list .hyp-coloris-input[data-scope="token"]',
                "(el) => { el.value = '#ff5500'; el.dispatchEvent(new Event('change', {bubbles:true})); }"
            )
            self.page.wait_for_timeout(300)
        else:
            # If fixture has no tokens, fall back to element color change (still exercises the color path)
            title.click()
            self.page.wait_for_timeout(300)
            self.page.eval_on_selector(
                '.hyp-element-body .hyp-coloris-input[data-prop="color"]',
                "(el) => { el.value = '#ff5500'; el.dispatchEvent(new Event('change', {bubbles:true})); }"
            )
            self.page.wait_for_timeout(300)

        # (e) add a comment
        title.click()
        self.page.wait_for_timeout(200)
        self.page.click("#comment-btn")
        self.page.wait_for_selector(".hyp-composer-textarea", timeout=3000)
        self.page.fill(".hyp-composer-textarea", "exit smoke comment")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread")

        # (f) tag it for agents
        self.page.locator("#comment-threads .comment-agent-toggle input").first.check()
        self.page.wait_for_timeout(300)

        # Save As to temp via fake dialog
        out = os.path.join(os.path.dirname(self.copy), "exit-smoke.html")
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(800)
        self.assertTrue(os.path.exists(out), "saved file should exist")

        # Reopen the saved file in a NEW page via server /doc/ after second open
        page2 = self.browser.new_page()
        try:
            H.set_fake_dialog(self.base, out)
            page2.goto(self.base + "/app/")
            H.open_via_dialog_ui(page2, self.base, out)
            # Assert a known fixture element is visible (no layout collapse)
            visible = page2.frame_locator("iframe.doc-frame").locator(".slide-title").first.is_visible()
            self.assertTrue(visible, "reopened saved file should render without layout collapse")
        finally:
            page2.close()

        # Console error filter (allow asset 404 network errors)
        editor_errors = [
            t for (ty, t, url) in errors
            if "assets/" not in t and "/doc/assets" not in t and "assets/" not in url
        ]
        self.assertEqual(editor_errors, [], f"editor console errors: {editor_errors}")

    # ── E-EXIT-3 ──────────────────────────────────────────────────────────────
    def test_saved_file_chrome_free_gate(self):
        # Run the smoke ops again to produce a saved file for chrome-free inspection.
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        frame = self.page.frame_locator("iframe.doc-frame")

        # Minimal ops to get an agent-tagged comment into the saved file
        frame.locator(".slide-title").first.click()
        self.page.wait_for_timeout(200)
        self.page.click("#comment-btn")
        self.page.wait_for_selector(".hyp-composer-textarea", timeout=3000)
        # Check agent box BEFORE filling so focus stays on textarea for Ctrl+Enter
        self.page.eval_on_selector(".hyp-composer-agent input", "(el) => el.checked = true")
        self.page.fill(".hyp-composer-textarea", "agent task")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread")

        out = os.path.join(os.path.dirname(self.copy), "exit-chrome.html")
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(800)
        self.assertTrue(os.path.exists(out))

        with open(out, encoding="utf-8") as fh:
            text = fh.read()

        # zero data-hyp-
        self.assertNotIn("data-hyp-", text, "saved file must not contain data-hyp- attributes")
        # except one id="hyp-comments" island allowed
        self.assertEqual(text.count('id="hyp-comments"'), 1, "exactly one hyp-comments island allowed")

        # zero class="…hyp-…" tokens
        import re
        hyp_class_matches = re.findall(r'class="[^"]*\bhyp-', text)
        self.assertEqual(hyp_class_matches, [], f"no hyp- class tokens allowed: {hyp_class_matches}")

        # zero /runtime/js/runtime-main.js
        self.assertNotIn("/runtime/js/runtime-main.js", text, "runtime script must not be in saved file")

        # head agent block (a comment node) allowed — no assertion needed, just allowed
        # sample's own inline onerror= handlers PRESERVED
        self.assertIn("onerror=", text, "sample's own inline onerror handlers must be preserved")


if __name__ == "__main__":
    unittest.main()
