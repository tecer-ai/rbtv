import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8812


def _iframe_origin(page):
    return page.evaluate(
        "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
    )


def _rect_in_iframe(page, selector):
    return H.doc_eval(
        page,
        f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
    )


def _scroll_into_view(page, selector):
    H.doc_eval(page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
    page.wait_for_timeout(250)


def parse_px(s):
    return float((s or "0").replace("px", "").strip() or 0)


def bridge_get_selection(page):
    return page.evaluate(
        """
        async () => {
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
                iframe.contentWindow.postMessage({ source: 'hyp', kind: 'command', id, type: 'get-selection' }, location.origin);
                setTimeout(() => { window.removeEventListener('message', handler); reject(new Error('bridge get-selection timed out')); }, 5000);
            });
        }
        """
    )


_HANDLE_SELECTOR = {
    "e":  ".moveable-control-box .moveable-line.moveable-e, .moveable-control-box .moveable-control.moveable-e, .moveable-control-box .moveable-e",
    "se": ".moveable-control-box .moveable-control.moveable-se, .moveable-control-box .moveable-se",
    "ne": ".moveable-control-box .moveable-control.moveable-ne, .moveable-control-box .moveable-ne",
    "w":  ".moveable-control-box .moveable-line.moveable-w, .moveable-control-box .moveable-control.moveable-w, .moveable-control-box .moveable-w",
}


class R12AltSymmetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(H.SYN_DIR, "flow-grow.html")):
            raise AssertionError("Required synthetic fixture missing: flow-grow.html")
        cls.proc, cls.base = H.start_server(PORT, test_dialog=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        H.stop_server(cls.proc)

    def setUp(self):
        self.page = self.browser.new_page(viewport={"width": 1920, "height": 1080})
        H.preset_author(self.page)
        self.page.goto(self.base + "/app/")

    def tearDown(self):
        self.page.close()

    def select_by_native_id(self, native_id):
        sel = f'#{native_id}'
        _scroll_into_view(self.page, sel)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, sel)
        self.assertIsNotNone(rect, f"element {sel} not found for selection")
        self.page.mouse.click(origin["x"]+rect["x"]+5, origin["y"]+rect["y"]+5)
        self.page.wait_for_timeout(300)
        info = bridge_get_selection(self.page)
        target_id = H.doc_eval(self.page, f"const e=doc.querySelector('#{native_id}'); return e?e.getAttribute('data-hyp-id'):null;")
        self.assertEqual(info.get("hypId") if info else None, target_id,
                         f"selected {info.get('hypId') if info else None} but target is {target_id}")

    def edge_handle_screen(self, which):
        sel = _HANDLE_SELECTOR[which]
        origin = _iframe_origin(self.page)
        h = H.doc_eval(self.page,
            f"const el=doc.querySelector({sel!r});"
            "if(!el) return null; const r=el.getBoundingClientRect();"
            "return {x:r.left,y:r.top,w:r.width,h:r.height,"
            " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};")
        self.assertIsNotNone(h, f"resize handle {which!r} not rendered after selection")
        self.assertTrue(h["in_vp"], f"resize handle {which!r} center outside the iframe viewport")
        return origin["x"] + h["x"] + h["w"] / 2, origin["y"] + h["y"] + h["h"] / 2

    def rendered(self, native_id):
        return H.doc_eval(self.page,
          f"const e=doc.querySelector('#{native_id}'); const r=e.getBoundingClientRect(); const cs=getComputedStyle(e);"
          f"return {{w:r.width,h:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom,"
          f" basis:cs.flexBasis, grow:cs.flexGrow, shrink:cs.flexShrink,"
          f" inlBasis:e.style.flexBasis, inlGrow:e.style.flexGrow, inlShrink:e.style.flexShrink,"
          f" inlWidth:e.style.width, inlHeight:e.style.height, translate:e.style.translate||''}};")

    # E-R12-1 — Alt-held: dragged edge tracks cursor 1:1, opposite edge mirrors, width grows 2Δ
    def test_e_r12_1_alt_symmetric_growth(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        before = self.rendered("twin")
        self.page.keyboard.down("Alt")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.keyboard.up("Alt")
        after = self.rendered("twin")
        self.assertAlmostEqual(after["right"] - before["right"], 60, delta=3)
        self.assertAlmostEqual(before["left"] - after["left"], 60, delta=3)
        self.assertAlmostEqual(after["w"] - before["w"], 120, delta=4)

    # E-R12-2 — No-Alt one-sided unchanged
    def test_e_r12_2_no_alt_one_sided(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        before = self.rendered("twin")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("twin")
        self.assertLessEqual(abs(after["left"] - before["left"]), 2)
        self.assertAlmostEqual(after["right"] - before["right"], 60, delta=3)

    # E-R12-3 — Default restored after an Alt gesture (resizeEnd reset)
    def test_e_r12_3_resize_end_reset(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        # Alt-held +40 gesture
        self.page.keyboard.down("Alt")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 8):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.keyboard.up("Alt")
        # Non-Alt +40 gesture
        before2 = self.rendered("twin")
        hx2, hy2 = self.edge_handle_screen("e")
        self.page.mouse.move(hx2, hy2)
        self.page.mouse.down()
        for i in range(1, 8):
            self.page.mouse.move(hx2 + i * 6, hy2)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after2 = self.rendered("twin")
        self.assertLessEqual(abs(after2["left"] - before2["left"]), 2)

    # E-R12-4 — Alt composes with R10: dragged edge 1:1, width grows 2Δ on the flex-grow accent
    def test_e_r12_4_alt_composes_with_r10(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("node-accent")
        before = self.rendered("node-accent")
        self.page.keyboard.down("Alt")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.keyboard.up("Alt")
        after = self.rendered("node-accent")
        self.assertAlmostEqual(after["right"] - before["right"], 60, delta=3)
        self.assertAlmostEqual(before["left"] - after["left"], 60, delta=3)
        self.assertAlmostEqual(after["w"] - before["w"], 120, delta=4)
        self.assertEqual(float(after["inlGrow"]), 0.0)
        # content-box: flexBasis = (rendered width + growth) − horizontal paddings/borders
        pad = H.doc_eval(self.page,
            "const e=doc.querySelector('#node-accent'); const cs=getComputedStyle(e); "
            "return (parseFloat(cs.paddingLeft)||0)+(parseFloat(cs.paddingRight)||0)"
            "+(parseFloat(cs.borderLeftWidth)||0)+(parseFloat(cs.borderRightWidth)||0);")
        self.assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] + 120 - pad, delta=4)


    # E-R12-5 — Alt-resize on an element with a pre-existing translate from a prior MOVE
    def test_e_r12_5_alt_with_prior_translate(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        # Simulate a prior move by setting translate directly, then remount so Moveable
        # seeds from the current transform state (E1 live-probe).
        H.doc_eval(self.page, "const e=doc.querySelector('#twin'); e.style.translate='80px 0px';")
        self.select_by_native_id("twin")
        before = self.rendered("twin")
        move_tx = parse_px(before["translate"].split()[0]) if before["translate"] else 0.0
        self.assertAlmostEqual(move_tx, 80, delta=5)
        center_before_x = (before["left"] + before["right"]) / 2
        # Now Alt-resize East +60
        self.page.keyboard.down("Alt")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.keyboard.up("Alt")
        after = self.rendered("twin")
        after_tx = parse_px(after["translate"].split()[0]) if after["translate"] else 0.0
        # E1 live-probe: beforeTranslate is absolute (includes prior move)
        # East +60 Alt resize: width grows 120, center shift = -60
        self.assertAlmostEqual(after_tx, move_tx - 60, delta=5)
        # Visual center must stay fixed
        center_after_x = (after["left"] + after["right"]) / 2
        self.assertAlmostEqual(center_after_x, center_before_x, delta=3)


if __name__ == "__main__":
    unittest.main()
