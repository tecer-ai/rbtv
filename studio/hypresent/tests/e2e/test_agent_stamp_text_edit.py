"""E2E: an agent-stamped element keeps its data-hyp-agent stamp after its text
is edited and the file is saved.

Regression for the anchor-hash-drift bug: at save, serializer.js rebuilds the
agent stamp map via comments.agentStampMap → matchAnchorHighConfidence, which
requires computeContentHash(el) === anchor.contentHash. Editing the element's
text changed its content hash, so the anchor no longer matched, the element was
omitted from the stamp map, and its data-hyp-agent token silently vanished from
the saved file — orphaning the agent comment thread.

Fix: text-edit.commit refreshes the anchor's content hash (comments
.refreshAnchorsForElement) for any thread anchored to the edited element, on
edit and on undo/redo, so the stamp survives the save.

Exercises the real runtime via real Playwright double-click + type gestures and
verifies the SAVED FILE (not the live DOM), reopening it to confirm the thread
re-resolves to the edited element.
"""
import os, sys, re, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8839
FIXTURE = "agent-stamp-text-edit.html"


def _iframe_origin(page):
    return page.evaluate(
        "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
    )


def _rect_in_iframe(page, selector):
    return H.doc_eval(
        page,
        f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
    )


def bridge_command(page, type_, payload=None):
    return page.evaluate(
        """
        async ([type, payload]) => {
            const iframe = document.querySelector('iframe.doc-frame');
            return new Promise((resolve, reject) => {
                const id = 'probe-' + Date.now() + '-' + Math.random();
                const handler = (e) => {
                    if (e.origin !== location.origin) return;
                    if (e.data?.source !== 'hyp') return;
                    if (e.data?.kind === 'response' && e.data?.id === id) {
                        window.removeEventListener('message', handler);
                        if (e.data.ok) resolve(e.data.result); else reject(new Error(e.data.error));
                    }
                };
                window.addEventListener('message', handler);
                iframe.contentWindow.postMessage({ source: 'hyp', kind: 'command', id, type, payload: (payload||{}) }, location.origin);
                setTimeout(() => { window.removeEventListener('message', handler); reject(new Error('bridge '+type+' timed out')); }, 5000);
            });
        }
        """,
        [type_, payload or {}],
    )


class AgentStampTextEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(H.SYN_DIR, FIXTURE)):
            raise AssertionError(f"Required synthetic fixture missing: {FIXTURE}")
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
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic(FIXTURE))

    def tearDown(self):
        self.page.close()

    # ---- helpers ----

    def _read_island(self):
        txt = H.doc_eval(self.page, "const i=doc.getElementById('hyp-comments'); return i?i.textContent:null;")
        if not txt:
            return []
        data = json.loads(txt)
        return data["threads"] if isinstance(data, dict) and "threads" in data else data

    def _select(self, native_id):
        sel = f"#{native_id}"
        H.doc_eval(self.page, f"const e=doc.querySelector({sel!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(200)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, sel)
        self.assertIsNotNone(rect, f"{sel} not found")
        self.page.mouse.click(origin["x"] + rect["x"] + 5, origin["y"] + rect["y"] + 5)
        self.page.wait_for_timeout(250)
        info = bridge_command(self.page, "get-selection")
        target_id = H.doc_eval(self.page, f"const e=doc.querySelector('#{native_id}'); return e?e.getAttribute('data-hyp-id'):null;")
        selected = info.get("hypId") if isinstance(info, dict) else None
        self.assertEqual(selected, target_id, f"selected {selected} but target is {target_id}")

    def _add_comment(self, text, agent=False):
        self.page.click("#comment-btn")
        self.page.wait_for_timeout(200)
        ta = self.page.locator(".hyp-comment-composer textarea, .hyp-composer-textarea").first
        ta.fill(text)
        if agent:
            cb = self.page.locator(".hyp-comment-composer .hyp-composer-agent input, .hyp-comment-composer input[type=checkbox], .hyp-composer-agent input").first
            if cb.count():
                cb.check()
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)
        if agent:
            island = self._read_island()
            if island and not island[-1].get("agentInstruction"):
                toggle = self.page.locator("#comment-threads .comment-agent-toggle input").last
                if toggle.count():
                    toggle.check()
                    self.page.wait_for_timeout(300)

    def _dblclick(self, selector, dx=30, frac_y=0.5):
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(150)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, selector)
        self.assertIsNotNone(rect, f"{selector} not found")
        cx = origin["x"] + rect["x"] + min(rect["w"] / 2, dx)
        cy = origin["y"] + rect["y"] + rect["h"] * frac_y
        self.page.mouse.dblclick(cx, cy)
        self.page.wait_for_timeout(250)

    def _editable(self, selector):
        return H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); return e ? e.getAttribute('contenteditable') : null;")

    def _edit_text(self, selector, appended):
        """Real double-click → caret to end → type → Esc-commit gesture."""
        self._dblclick(selector)
        self.assertEqual(self._editable(selector), "true", f"{selector} must enter edit mode")
        self.page.keyboard.press("End")
        self.page.keyboard.type(appended)
        self.page.keyboard.press("Escape")  # commit
        self.page.wait_for_timeout(300)

    def _save_to_temp(self, suffix=".html"):
        out = tempfile.mktemp(suffix=suffix)
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        return out

    def _read_text(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _stamped_in_saved_file(self, path, selector):
        """Open the saved file in a fresh page; return data-hyp-agent value of selector (or None)."""
        fresh = self.browser.new_page()
        try:
            fresh.goto("file://" + os.path.abspath(path), wait_until="networkidle", timeout=10000)
            return fresh.evaluate(
                "(sel) => { const e=document.querySelector(sel); return e ? e.getAttribute('data-hyp-agent') : null; }",
                selector,
            )
        finally:
            fresh.close()

    # ---- C1: stamp survives text-edit + save; thread re-resolves on reopen ----

    def test_c1_plain_stamped_element_survives_text_edit(self):
        """Edit the text of a plain agent-stamped <p>, save → stamp survives + thread re-resolves."""
        self._select("p-stamped")
        self._add_comment("clarify Arguments", agent=True)
        threads = self._read_island()
        self.assertEqual(len(threads), 1)
        id0 = threads[0]["id"]
        self.assertTrue(threads[0].get("agentInstruction"), "thread must be agent-tagged")

        self._edit_text("#p-stamped", " activate modes")

        out = self._save_to_temp("-c1-plain.html")
        text = self._read_text(out)
        # Edited text persisted
        self.assertIn("Arguments activate modes", text, "edited text must persist in saved file")

        # SAVED FILE carries the stamp on the edited element (verify via fresh DOM render)
        stamp_val = self._stamped_in_saved_file(out, "#p-stamped")
        self.assertIsNotNone(stamp_val, "edited element must STILL carry data-hyp-agent after edit+save")
        self.assertIn(id0, stamp_val.split(), f"stamp must include thread id {id0}; got {stamp_val!r}")

        # Reopen in the editor: the thread re-resolves to the edited element
        H.open_via_dialog_ui(self.page, self.base, out)
        self.page.wait_for_timeout(500)
        result = H.doc_eval(
            self.page,
            f'const m=doc.querySelectorAll(\'[data-hyp-agent~="{id0}"]\'); return {{n:m.length, text:m[0]?m[0].textContent.slice(0,40):null}};',
        )
        self.assertEqual(result["n"], 1, "exactly one element must resolve the thread after reopen")
        self.assertIn("Arguments activate modes", result["text"])

    def test_c1_decorative_child_stamped_element_survives_text_edit(self):
        """The reported case: a stamped element with a decorative child, text edited → stamp survives."""
        self._select("p-decorated")
        self._add_comment("legend for output format", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        self._edit_text("#p-decorated", " (legend)")

        out = self._save_to_temp("-c1-decor.html")
        text = self._read_text(out)
        self.assertIn("Output format (legend)", text, "edited text must persist")
        # Decorative child must survive intact (decorative-child fix not regressed)
        self.assertTrue(re.search(r'<span class="dot"></span>', text), "decorative dot span must survive")

        stamp_val = self._stamped_in_saved_file(out, "#p-decorated")
        self.assertIsNotNone(stamp_val, "stamped decorative-child element must keep data-hyp-agent after edit+save")
        self.assertIn(id0, stamp_val.split())

        H.open_via_dialog_ui(self.page, self.base, out)
        self.page.wait_for_timeout(500)
        n = H.doc_eval(self.page, f'return doc.querySelectorAll(\'[data-hyp-agent~="{id0}"]\').length;')
        self.assertEqual(n, 1, "thread must re-resolve after reopen")

    # ---- C2: editing a NON-stamped element produces no spurious stamp ----

    def test_c2_editing_unstamped_element_no_spurious_stamp(self):
        """Stamp p-stamped, then edit the UNSTAMPED p-plain → only p-stamped is stamped; no spurious stamp appears."""
        self._select("p-stamped")
        self._add_comment("keep this", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        # Edit a DIFFERENT, unstamped element
        self._edit_text("#p-plain", " EDITED")

        out = self._save_to_temp("-c2.html")
        text = self._read_text(out)
        self.assertIn("Plain unstamped paragraph. EDITED", text)

        # Exactly ONE stamped element in the saved file, and it is p-stamped (not p-plain)
        fresh = self.browser.new_page()
        try:
            fresh.goto("file://" + os.path.abspath(out), wait_until="networkidle", timeout=10000)
            total = fresh.evaluate("() => document.querySelectorAll('[data-hyp-agent]').length")
            on_stamped = fresh.evaluate("() => { const e=document.querySelector('#p-stamped'); return e?e.getAttribute('data-hyp-agent'):null; }")
            on_plain = fresh.evaluate("() => { const e=document.querySelector('#p-plain'); return e?e.getAttribute('data-hyp-agent'):null; }")
        finally:
            fresh.close()
        self.assertEqual(total, 1, "editing an unstamped element must NOT create a spurious stamp")
        self.assertIsNotNone(on_stamped, "p-stamped must keep its stamp")
        self.assertIn(id0, on_stamped.split())
        self.assertIsNone(on_plain, "the edited UNSTAMPED element must NOT gain a stamp")

    # ---- C3: no-edit load → Save-As preserves all stamps (regression) ----

    def test_c3_no_edit_roundtrip_preserves_stamps(self):
        """Stamp two elements, save (baseline), reopen, Save-As again with NO edit → all stamps preserved."""
        self._select("p-stamped")
        self._add_comment("a", agent=True)
        self._select("p-decorated")
        self._add_comment("b", agent=True)
        threads = self._read_island()
        ids = sorted(t["id"] for t in threads)
        self.assertEqual(len(ids), 2)

        baseline = self._save_to_temp("-c3-base.html")

        # Reopen baseline, then Save-As again WITHOUT any edit
        H.open_via_dialog_ui(self.page, self.base, baseline)
        self.page.wait_for_timeout(500)
        out2 = self._save_to_temp("-c3-roundtrip.html")

        fresh = self.browser.new_page()
        try:
            fresh.goto("file://" + os.path.abspath(out2), wait_until="networkidle", timeout=10000)
            total = fresh.evaluate("() => document.querySelectorAll('[data-hyp-agent]').length")
            resolved = {}
            for cid in ids:
                resolved[cid] = fresh.evaluate(
                    "(id) => document.querySelectorAll('[data-hyp-agent~=\"' + id + '\"]').length",
                    cid,
                )
        finally:
            fresh.close()
        self.assertEqual(total, 2, "no-edit round-trip must preserve BOTH stamps")
        for cid in ids:
            self.assertEqual(resolved[cid], 1, f"thread {cid} must still resolve after no-edit round-trip")

    # ---- C1-undo: edit → undo restores original; stamp still survives save ----

    def test_c1_undo_after_edit_preserves_stamp(self):
        """Edit then Ctrl+Z back to original text → stamp still survives the save (anchor stays in sync)."""
        self._select("p-stamped")
        self._add_comment("keep anchored", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        self._edit_text("#p-stamped", " XYZ")
        # Undo the text edit
        self.page.keyboard.press("Control+z")
        self.page.wait_for_timeout(300)
        # Confirm text reverted in the live doc
        reverted = H.doc_eval(self.page, "const e=doc.querySelector('#p-stamped'); return e?e.textContent.trim():null;")
        self.assertEqual(reverted, "Arguments", "undo must restore original text")

        out = self._save_to_temp("-c1-undo.html")
        stamp_val = self._stamped_in_saved_file(out, "#p-stamped")
        self.assertIsNotNone(stamp_val, "stamp must survive even after edit→undo (no anchor-staleness regression)")
        self.assertIn(id0, stamp_val.split())


if __name__ == "__main__":
    unittest.main()
