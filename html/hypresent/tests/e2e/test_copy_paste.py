import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8813


class CopyPasteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def tearDown(self):
        self.page.close()

    def _open_fixture(self, name):
        copy = H.copy_synthetic(name)
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, copy)

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

    def _bridge_cmd(self, type, payload=None):
        return self.page.evaluate(
            """(args) => {
                const { type, payload } = args;
                const f = document.querySelector('iframe.doc-frame');
                return new Promise((resolve, reject) => {
                    const id = 'test-' + type + '-' + Date.now();
                    const timer = setTimeout(() => {
                        window.removeEventListener('message', onMsg);
                        reject(new Error('bridge command timeout'));
                    }, 3000);
                    function onMsg(e) {
                        if (e.origin !== location.origin) return;
                        if (e.data?.source !== 'hyp') return;
                        if (e.data?.kind !== 'response') return;
                        if (e.data?.id !== id) return;
                        clearTimeout(timer);
                        window.removeEventListener('message', onMsg);
                        if (e.data.ok) resolve(e.data.result);
                        else reject(new Error(e.data.error || 'bridge command failed'));
                    }
                    window.addEventListener('message', onMsg);
                    f.contentWindow.postMessage(
                        { source: 'hyp', kind: 'command', id, type, payload: payload || {} },
                        location.origin
                    );
                });
            }""",
            {"type": type, "payload": payload or {}},
        )

    def _undo_btn(self):
        return self.page.locator("#undo-btn")

    def _redo_btn(self):
        return self.page.locator("#redo-btn")

    # C6 — float paste: copy exists and other components are untouched
    def test_float_paste_no_reflow(self):
        self._open_fixture("flow-grow.html")
        sel = "#node-a"
        self._real_select(sel)

        # Snapshot rects of all original flow-nodes BEFORE paste
        before_rects = H.doc_eval(
            self.page,
            "const nodes=Array.from(doc.querySelectorAll('.flow-node,.flow-node--accent'));"
            "return nodes.map(n=>{const r=n.getBoundingClientRect();return{left:r.left,top:r.top,width:r.width,height:r.height};});",
        )
        original_count = len(before_rects)

        # Copy via bridge
        result = self._bridge_cmd("copy")
        self.assertTrue(result.get("copied", False), "copy bridge command should succeed")

        # Paste-float via bridge at a coordinate inside the slide
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        slide_rect = H.doc_eval(
            self.page,
            "const s=doc.querySelector('.slide'); if(!s) return null; const r=s.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        self.assertIsNotNone(slide_rect, "slide not found")
        paste_x = slide_rect["x"] + slide_rect["w"] // 2
        paste_y = slide_rect["y"] + slide_rect["h"] // 2
        self._bridge_cmd("paste", {"x": paste_x, "y": paste_y})
        self.page.wait_for_timeout(400)

        # After paste, there should be one more node
        after_count = H.doc_eval(
            self.page,
            "return doc.querySelectorAll('.flow-node,.flow-node--accent').length;",
        )
        self.assertEqual(after_count, original_count + 1, "paste-float should add one copy")

        # Original nodes' rects must be unchanged
        after_rects = H.doc_eval(
            self.page,
            f"const nodes=Array.from(doc.querySelectorAll('.flow-node,.flow-node--accent'));"
            f"return nodes.slice(0,{original_count}).map(n=>{{const r=n.getBoundingClientRect();return{{left:r.left,top:r.top,width:r.width,height:r.height}};}});",
        )
        for i, (b, a) in enumerate(zip(before_rects, after_rects)):
            self.assertAlmostEqual(b["left"], a["left"], delta=0.5, msg=f"node {i} left changed")
            self.assertAlmostEqual(b["top"], a["top"], delta=0.5, msg=f"node {i} top changed")
            self.assertAlmostEqual(b["width"], a["width"], delta=0.5, msg=f"node {i} width changed")
            self.assertAlmostEqual(b["height"], a["height"], delta=0.5, msg=f"node {i} height changed")

    # C7 — flex: paste-into-layout inserts a sibling and a neighbour moves
    def test_paste_into_layout_flex(self):
        self._open_fixture("flow-grow.html")
        sel = "#node-a"
        self._real_select(sel)

        # Snapshot rects before
        before_rects = H.doc_eval(
            self.page,
            "const nodes=Array.from(doc.querySelectorAll('.flow-node,.flow-node--accent'));"
            "return nodes.map(n=>{const r=n.getBoundingClientRect();return{left:r.left,top:r.top,width:r.width,height:r.height};});",
        )
        original_count = len(before_rects)

        # Copy
        result = self._bridge_cmd("copy")
        self.assertTrue(result.get("copied", False))

        # Paste-into-layout
        origin = self.page.evaluate(
            "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
        )
        slide_rect = H.doc_eval(
            self.page,
            "const s=doc.querySelector('.slide'); if(!s) return null; const r=s.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        self.assertIsNotNone(slide_rect)
        paste_x = slide_rect["x"] + slide_rect["w"] // 2
        paste_y = slide_rect["y"] + slide_rect["h"] // 2
        self._bridge_cmd("paste-into-layout", {"x": paste_x, "y": paste_y})
        self.page.wait_for_timeout(400)

        # Count increased
        after_count = H.doc_eval(
            self.page,
            "return doc.querySelectorAll('.flow-node,.flow-node--accent').length;",
        )
        self.assertEqual(after_count, original_count + 1, "paste-into-layout should add a sibling")

        # At least one neighbour moved (layout reflow happened)
        after_rects = H.doc_eval(
            self.page,
            f"const nodes=Array.from(doc.querySelectorAll('.flow-node,.flow-node--accent'));"
            f"return nodes.slice(0,{original_count}).map(n=>{{const r=n.getBoundingClientRect();return{{left:r.left,top:r.top,width:r.width,height:r.height}};}});",
        )
        moved = False
        for b, a in zip(before_rects, after_rects):
            if abs(b["left"] - a["left"]) > 1 or abs(b["top"] - a["top"]) > 1:
                moved = True
                break
        self.assertTrue(moved, "a neighbour's position should change after layout paste (reflow)")

    # C7 — grid: paste-into-layout falls back to float (position:absolute)
    def test_paste_into_layout_grid_fallback(self):
        self._open_fixture("grid-healthy.html")
        sel = "#grid-left"
        self._real_select(sel)

        # Copy
        result = self._bridge_cmd("copy")
        self.assertTrue(result.get("copied", False))

        # Paste-into-layout
        slide_rect = H.doc_eval(
            self.page,
            "const s=doc.querySelector('.slide'); if(!s) return null; const r=s.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        self.assertIsNotNone(slide_rect)
        paste_x = slide_rect["x"] + slide_rect["w"] // 2
        paste_y = slide_rect["y"] + slide_rect["h"] // 2
        self._bridge_cmd("paste-into-layout", {"x": paste_x, "y": paste_y})
        self.page.wait_for_timeout(400)

        # The pasted element should be absolutely positioned (grid fallback to float)
        # pasteFloat inserts into the slide, not the grid, so look for any new absolutely-positioned element
        is_abs = H.doc_eval(
            self.page,
            "const slide=doc.querySelector('.slide');"
            "const abs=Array.from(slide.querySelectorAll('*')).filter(el=>getComputedStyle(el).position==='absolute');"
            "return abs.length > 0;",
        )
        self.assertTrue(is_abs, "grid paste-into-layout should fall back to float (position:absolute)")

        # Original grid children count unchanged
        original_count = H.doc_eval(
            self.page,
            "return doc.querySelectorAll('.intro-grid > div').length;",
        )
        self.assertEqual(original_count, 3, "original grid must remain intact (3 children)")

    # C9 — undo removes pasted copy; redo re-adds; serialize returns non-null HTML
    def test_undo_redo_serialize(self):
        self._open_fixture("flow-grow.html")
        sel = "#node-a"
        self._real_select(sel)

        # Copy and paste-float
        self._bridge_cmd("copy")
        slide_rect = H.doc_eval(
            self.page,
            "const s=doc.querySelector('.slide'); if(!s) return null; const r=s.getBoundingClientRect(); return {x:r.left,y:r.top,w:r.width,h:r.height};",
        )
        self.assertIsNotNone(slide_rect)
        self._bridge_cmd("paste", {"x": slide_rect["x"] + 100, "y": slide_rect["y"] + 100})
        self.page.wait_for_timeout(400)

        # The pasted element should exist (find the one that is absolutely positioned)
        pasted_id = H.doc_eval(
            self.page,
            "const nodes=Array.from(doc.querySelectorAll('.flow-node,.flow-node--accent'));"
            "for(let i=nodes.length-1;i>=0;i--){"
            "  if(getComputedStyle(nodes[i]).position==='absolute')"
            "    return nodes[i].getAttribute('data-hyp-id');"
            "}"
            "return null;",
        )
        self.assertIsNotNone(pasted_id, "pasted element should exist and be absolutely positioned")
        self.assertTrue(self._exists(pasted_id), "pasted element should be in DOM")

        # Undo removes it
        self._bridge_cmd("undo")
        self.page.wait_for_timeout(300)
        self.assertFalse(self._exists(pasted_id), "undo should remove the pasted copy")

        # Redo re-adds it
        self._bridge_cmd("redo")
        self.page.wait_for_timeout(300)
        self.assertTrue(self._exists(pasted_id), "redo should restore the pasted copy")

        # Serialize returns non-null HTML
        ser = self._bridge_cmd("serialize")
        self.assertIsNotNone(ser)
        html = ser.get("html")
        self.assertIsNotNone(html, "serialize should return html")
        self.assertTrue(len(html) > 0, "serialize html should be non-empty")


if __name__ == "__main__":
    unittest.main()
