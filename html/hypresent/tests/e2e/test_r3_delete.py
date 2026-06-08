import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8793


class R3DeleteTests(unittest.TestCase):
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
        H.preset_author(self.page)  # init script BEFORE goto → skips the name prompt
        self.copy = H.copy_fixture()
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def tearDown(self):
        self.page.close()

    def _undo_btn(self):
        # The Undo button is the #undo-btn topbar icon (ui-redesign).
        return self.page.locator("#undo-btn")

    def _real_select(self, selector):
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(250)
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        rect = H.doc_eval(
            self.page,
            f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
        )
        self.assertIsNotNone(rect, f"{selector} not found")
        self.page.mouse.click(origin["x"] + rect["x"] + min(rect["w"]/2, 40), origin["y"] + rect["y"] + rect["h"]/2)
        self.page.wait_for_timeout(250)

    def _hyp_id_of(self, selector):
        return H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); return e ? e.getAttribute('data-hyp-id') : null;")

    def _exists(self, hyp_id):
        return H.doc_eval(self.page, f"return !!doc.querySelector('[data-hyp-id=\"{hyp_id}\"]');")

    # E-R3-1 / E-R3-2 — delete removes the node; undo restores it
    def test_delete_then_undo(self):
        # Pick a body-level element that is NOT the only region. Use a card-like
        # element nested inside a slide so its deletion never hits the last-region guard.
        sel = ".kicker"
        if not H.doc_eval(self.page, f"return !!doc.querySelector('{sel}');"):
            sel = ".kicker"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        self.assertIsNotNone(hyp, "selected element has no data-hyp-id")
        prev_id = H.doc_eval(self.page, f"const e=doc.querySelector('[data-hyp-id=\"{hyp}\"]'); const p=e.previousElementSibling; return p?p.getAttribute('data-hyp-id'):null;")

        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertFalse(self._exists(hyp), "element should be removed from the DOM after delete")

        self._undo_btn().click()
        self.page.wait_for_timeout(250)
        self.assertTrue(self._exists(hyp), "element should be restored after undo")
        # same data-hyp-id, same previous-sibling neighbor
        prev_id2 = H.doc_eval(self.page, f"const e=doc.querySelector('[data-hyp-id=\"{hyp}\"]'); const p=e.previousElementSibling; return p?p.getAttribute('data-hyp-id'):null;")
        self.assertEqual(prev_id2, prev_id, "element should return to its original position (same previous sibling)")

    # E-R3-3 / E-R3-4 — thread on a deleted element goes Unanchored; undo re-anchors
    def test_thread_unanchored_on_delete_and_reanchor_on_undo(self):
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        # add a comment via the composer
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)
        composer = self.page.locator(".hyp-comment-composer textarea")
        composer.fill("delete me later")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)
        anchored_before = self.page.locator("#comment-threads .comment-thread").count()
        self.assertGreaterEqual(anchored_before, 1, "comment should appear anchored before delete")

        # delete the element
        self._real_select(sel)
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(300)
        # the thread must now appear in the Unanchored section, not lost
        unanchored = self.page.locator("#comment-unanchored .comment-thread").count()
        self.assertGreaterEqual(unanchored, 1, "thread must move to Unanchored after deleting its element (not lost)")

        # undo → element back → thread re-anchors
        self._undo_btn().click()
        self.page.wait_for_timeout(300)
        anchored_after = self.page.locator("#comment-threads .comment-thread").count()
        unanchored_after = self.page.locator("#comment-unanchored .comment-thread").count()
        total_after = anchored_after + unanchored_after
        # the thread must STILL exist (never lost) AND must be RE-ANCHORED (not still unanchored)
        self.assertGreaterEqual(total_after, 1, "thread must still exist after undo (never lost)")
        self.assertEqual(
            unanchored_after, 0,
            "thread must re-anchor after undo, not remain unanchored (RV10)",
        )
        self.assertGreaterEqual(anchored_after, 1, "the re-anchored thread must appear in the anchored section after undo")

    # E-R3-5 — last-region block (D20): reduce the body to ONE tagged region via
    # doc_eval DOM surgery on the TEMP fixture copy, then assert delete is BLOCKED,
    # the status message is visible, and the region still exists.
    def test_last_region_block(self):
        # Precondition (fail-loud): the body must have >= 2 top-level tagged regions
        # so the surgery is meaningful (otherwise the fixture already is single-region).
        n_before = H.doc_eval(
            self.page,
            "return Array.from(doc.body.children).filter(c=>c.getAttribute('data-hyp-id')).length;",
        )
        self.assertGreaterEqual(
            n_before, 2,
            f"precondition: fixture body must have >=2 tagged top-level regions, found {n_before}",
        )
        # Surgery: keep the FIRST body-level tagged region, remove every other one
        # (siblings only — the survivor keeps its registry entry from boot tagging).
        survivor_id = H.doc_eval(
            self.page,
            "const kids=Array.from(doc.body.children).filter(c=>c.getAttribute('data-hyp-id'));"
            "const keep=kids[0];"
            "for(const c of kids.slice(1)){ c.parentNode.removeChild(c); }"
            "return keep.getAttribute('data-hyp-id');",
        )
        self.assertIsNotNone(survivor_id, "survivor region has no data-hyp-id")
        # Postcondition (fail-loud): exactly ONE tagged top-level region remains.
        n_after = H.doc_eval(
            self.page,
            "return Array.from(doc.body.children).filter(c=>c.getAttribute('data-hyp-id')).length;",
        )
        self.assertEqual(n_after, 1, f"surgery must leave exactly ONE tagged region, found {n_after}")

        # Select the survivor (real click) and attempt to delete it via the toolbar.
        self._real_select(f'[data-hyp-id="{survivor_id}"]')
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(300)

        # The region STILL exists (delete was blocked).
        self.assertTrue(
            self._exists(survivor_id),
            "the last remaining region must NOT be deletable (last-region guard — D20/V3-S7)",
        )
        # The shell status message is visible and carries the block text.
        status = self.page.locator("#shell-status")
        self.assertIn(
            "Cannot delete the last remaining region",
            (status.text_content() or ""),
            "the last-region block must surface the status message",
        )

    # E-R3-6 — edit-active guard
    def test_delete_blocked_while_editing(self):
        sel = ".slide-title"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        # enter edit via real double-click
        origin = self.page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")
        rect = H.doc_eval(self.page, f"const e=doc.querySelector('{sel}'); const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};")
        self.page.mouse.dblclick(origin["x"]+rect["x"]+min(rect["w"]/2,40), origin["y"]+rect["y"]+rect["h"]/2)
        self.page.wait_for_timeout(250)
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertTrue(self._exists(hyp), "element must NOT be deleted while a text edit is active (V3-S10)")

    # E-R3-7 — NO keyboard path (U14)
    def test_no_keyboard_delete(self):
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        hyp = self._hyp_id_of(sel)
        self.page.keyboard.press("Delete")
        self.page.wait_for_timeout(150)
        self.page.keyboard.press("Backspace")
        self.page.wait_for_timeout(150)
        self.assertTrue(self._exists(hyp), "Delete/Backspace must NOT remove the element (no keyboard path — U14)")

    # E-R3-8 — Moveable teardown after delete
    def test_moveable_torn_down_after_delete(self):
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        self.assertTrue(H.doc_eval(self.page, "return !!doc.getElementById('hyp-interaction-wrapper');"), "wrapper should exist while selected")
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(300)
        self.assertFalse(H.doc_eval(self.page, "return !!doc.getElementById('hyp-interaction-wrapper');"), "wrapper should be gone after delete (selection cleared → unmount)")

    # E-R3-9 — no console errors
    def test_no_console_errors(self):
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "assets/" in t and ("404" in t or "Failed to load resource" in t):
                    return
                errors.append(t)
        self.page.on("console", on_console)
        sel = ".research-card" if H.doc_eval(self.page, "return !!doc.querySelector('.research-card');") else ".kicker"
        self._real_select(sel)
        self.page.click("#delete-btn")
        self.page.wait_for_timeout(250)
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
