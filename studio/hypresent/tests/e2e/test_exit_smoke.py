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

        # (a2) R8: re-enter edit, select the word via double-click, press A+ 3x → ONE span, +6px, zero empties.
        # Coordinates via iframe_origin + doc_eval getBoundingClientRect (the v2 pattern) — NOT frame_locator.bounding_box() (RV09).
        origin_t = self.page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")
        rect_t = H.doc_eval(self.page, "const e=doc.querySelector('.slide-title'); if(!e) return null; const r=e.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};")
        if rect_t:
            self.page.mouse.dblclick(origin_t["x"] + rect_t["x"] + min(rect_t["w"] / 2, 20), origin_t["y"] + rect_t["y"] + rect_t["h"] / 2)
            self.page.wait_for_timeout(200)
            base = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.slide-title')).fontSize);")
            for _ in range(3):
                self.page.click("#fmt-font-inc")
                self.page.wait_for_timeout(120)
            spans = H.doc_eval(
                self.page,
                "const e=doc.querySelector('.slide-title');"
                "const s=Array.from(e.querySelectorAll('span')).filter(x=>x.style&&x.style.fontSize);"
                "return {count:s.length, sizes:s.map(x=>parseFloat(x.style.fontSize)), empties:s.filter(x=>x.textContent.trim()==='').length};",
            )
            self.assertEqual(spans["count"], 1, f"R8: 3 presses must yield ONE span, got {spans['count']}")
            self.assertEqual(spans["empties"], 0, "R8: zero empty sibling spans")
            self.assertAlmostEqual(spans["sizes"][0], base + 6, delta=1.5, msg="R8: single span must be base+6px")
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(150)

        # (b) resize: select an element, drag a resize handle — MUST change geometry (R2 fixed)
        title.click()
        self.page.wait_for_timeout(300)
        handle_info = H.doc_eval(
            self.page,
            "const h=doc.querySelector('.moveable-control-box .moveable-e') || doc.querySelector('.moveable-control-box .moveable-se');"
            "if(!h) return null; const r=h.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        self.assertIsNotNone(handle_info, "resize handle must be present after selection (R2 fixed)")
        before_w = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.slide-title')).width);")
        fb = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        hx = fb["x"] + handle_info["x"] + handle_info["w"] / 2
        hy = fb["y"] + handle_info["y"] + handle_info["h"] / 2
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        self.page.mouse.move(hx + 30, hy + 10, steps=8)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)
        after_w = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.slide-title')).width);")
        self.assertNotAlmostEqual(after_w, before_w, delta=2, msg=f"resize must change width (R2): {before_w} -> {after_w}")

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
        self.page.locator("#comment-threads .comment-agent-toggle").first.click()
        self.page.wait_for_timeout(300)

        # (g) R3: delete an element then undo it (no leftover; round-trips clean)
        del_sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        H.doc_eval(self.page, f"const e=doc.querySelector('{del_sel}'); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(200)
        origin_d = self.page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")
        rect_d = H.doc_eval(self.page, f"const e=doc.querySelector('{del_sel}'); const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};")
        self.page.mouse.click(origin_d["x"]+rect_d["x"]+min(rect_d["w"]/2,40), origin_d["y"]+rect_d["y"]+rect_d["h"]/2)
        self.page.wait_for_timeout(200)
        # Capture the element the runtime ACTUALLY selected (the click resolves to the nearest
        # registered element under the pointer, which may be a registered CHILD of del_sel).
        # Delete + undo must round-trip on THAT element, not the static container query.
        del_id = H.doc_eval(
            self.page,
            "const r=doc.querySelector('.hyp-selection-ring');"
            "if(!r) return null;"
            "const rr=r.getBoundingClientRect();"
            "const c=Array.from(doc.querySelectorAll('[data-hyp-id]')).filter(el=>{"
            " const x=el.getBoundingClientRect();"
            " return Math.abs(x.left-rr.left)<2 && Math.abs(x.top-rr.top)<2"
            "  && Math.abs(x.width-rr.width)<2 && Math.abs(x.height-rr.height)<2;});"
            "return c[0] ? c[0].getAttribute('data-hyp-id') : null;",
        )
        self.assertIsNotNone(del_id, "R3: an element must be selected before delete")
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertFalse(H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{del_id}\"]');"), "R3: element deleted")
        self.page.click("#undo-btn")
        self.page.wait_for_timeout(250)
        self.assertTrue(H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{del_id}\"]');"), "R3: element restored on undo")

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
        # R4 + R9: the removed UI must be absent in the shell.
        self.assertIsNone(self.page.query_selector("#color-btn"), "R4: #color-btn must be removed")
        self.assertIsNone(self.page.query_selector("#outline-list"), "R9: #outline-list must be removed")
        self.assertIsNone(self.page.query_selector(".outline-panel"), "R9: .outline-panel must be removed")
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

        # data-hyp-agent is the ONLY allowed data-hyp- residue (R14 D4: intentional stamp).
        # All other data-hyp-* attributes (data-hyp-id, data-hyp-hook, etc.) must be absent.
        import re
        all_data_hyp = set(re.findall(r'data-hyp-[a-z-]+', text))
        leaked = all_data_hyp - {"data-hyp-agent"}
        self.assertEqual(leaked, set(), f"saved file must not contain non-agent data-hyp- residue: {leaked}")

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
