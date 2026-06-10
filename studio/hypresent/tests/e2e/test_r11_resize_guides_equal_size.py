import os, sys, re, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8811


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
    """postMessage get-selection round-trip — returns the selection result dict
    (a dict like {"hypId": "<id>"}, or None). Transcribed from test_r2_resize_real.py E-R2-8."""
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
                        if (e.data.ok) resolve(e.data.result);
                        else reject(new Error(e.data.error));
                    }
                };
                window.addEventListener('message', handler);
                iframe.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', id, type: 'get-selection' },
                    location.origin
                );
                setTimeout(() => {
                    window.removeEventListener('message', handler);
                    reject(new Error('bridge get-selection timed out'));
                }, 5000);
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


class R11ResizeGuidesEqualSizeTests(unittest.TestCase):
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
        """Click an element's on-screen center, then D14-assert the runtime selected it."""
        sel = f'#{native_id}'
        _scroll_into_view(self.page, sel)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, sel)
        self.assertIsNotNone(rect, f"element {sel} not found for selection")
        self.page.mouse.click(origin["x"]+rect["x"]+5, origin["y"]+rect["y"]+5)  # +5 -> target itself, not a child
        self.page.wait_for_timeout(300)
        info = bridge_get_selection(self.page)
        target_id = H.doc_eval(self.page, f"const e=doc.querySelector('#{native_id}'); return e?e.getAttribute('data-hyp-id'):null;")
        self.assertEqual(info.get("hypId") if info else None, target_id,
                         f"selected {info.get('hypId') if info else None} but target is {target_id}")

    def edge_handle_screen(self, which):
        """On-screen (x,y) center of the requested Moveable handle inside the iframe."""
        sel = _HANDLE_SELECTOR[which]
        origin = _iframe_origin(self.page)
        h = H.doc_eval(
            self.page,
            f"const el=doc.querySelector({sel!r});"
            "if(!el) return null; const r=el.getBoundingClientRect();"
            "return {x:r.left,y:r.top,w:r.width,h:r.height,"
            " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};",
        )
        self.assertIsNotNone(h, f"resize handle {which!r} ({sel}) not rendered after selection")
        self.assertTrue(h["in_vp"], f"resize handle {which!r} center is outside the iframe viewport — control box mis-placed")
        return origin["x"] + h["x"] + h["w"] / 2, origin["y"] + h["y"] + h["h"] / 2

    def rendered(self, native_id):
        return H.doc_eval(self.page,
          f"const e=doc.querySelector('#{native_id}'); const r=e.getBoundingClientRect(); const cs=getComputedStyle(e);"
          f"return {{w:r.width,h:r.height,left:r.left,right:r.right,top:r.top,bottom:r.bottom,"
          f" basis:cs.flexBasis, grow:cs.flexGrow, shrink:cs.flexShrink,"
          f" inlBasis:e.style.flexBasis, inlGrow:e.style.flexGrow, inlShrink:e.style.flexShrink,"
          f" inlWidth:e.style.width, inlHeight:e.style.height}};")

    # E-R11-1 — Position guides FIRE on the flex-grow element post-R10.
    def test_e_r11_1_position_guides_fire_on_flex_grow(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("node-accent")
        before_w = self.rendered("node-accent")["w"]
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 6):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        found = H.doc_eval(self.page, "return doc.querySelectorAll('.moveable-line').length >= 1;")
        for i in range(6, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after_w = self.rendered("node-accent")["w"]
        self.assertTrue(found, "position guides must appear during resize on the flex-grow element post-R10")
        self.assertNotAlmostEqual(after_w, before_w, delta=2)

    # E-R11-2 — Equal-size SNAP lands ON the matched dimension (snap to out-of-flow twin).
    def test_e_r11_2_equal_size_snap_lands_on_matched_dimension(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        twinW = self.rendered("twin")["w"]
        self.select_by_native_id("node-accent")
        accW0 = self.rendered("node-accent")["w"]
        # Stop the cursor just short of the twin so the un-snapped value differs from the twin.
        raw_target = twinW - 4.0
        target_travel = raw_target - accW0
        steps = 20
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, steps + 1):
            self.page.mouse.move(hx + target_travel * i / steps, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)
        accW1 = self.rendered("node-accent")["w"]
        self.assertAlmostEqual(accW1, twinW, delta=0.5)
        self.assertNotAlmostEqual(accW1, raw_target, delta=0.5)

    # E-R11-3 — Equal-size HINT renders during the snap, removed at end, positioned over the match.
    def test_e_r11_3_equal_size_hint_renders_during_snap(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        twinW = self.rendered("twin")["w"]
        self.select_by_native_id("node-accent")
        accW0 = self.rendered("node-accent")["w"]
        raw_target = twinW - 4.0
        target_travel = raw_target - accW0
        steps = 20
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        hint = 0
        pe = None
        pos = None
        for i in range(1, steps + 1):
            self.page.mouse.move(hx + target_travel * i / steps, hy)
            self.page.wait_for_timeout(30)
            cur_w = self.rendered("node-accent")["w"]
            if abs(cur_w - twinW) <= 4.0:
                hint = H.doc_eval(self.page, 'return doc.querySelectorAll(\'[class*="hyp-size-hint"]\').length;')
                pe = H.doc_eval(self.page, 'const h=doc.querySelector(\'[class*="hyp-size-hint"]\'); return h?getComputedStyle(h).pointerEvents:null;')
                pos = H.doc_eval(self.page, 'const h=doc.querySelector(\'[class*="hyp-size-hint"]\'); const t=doc.querySelector(\'#twin\'); if(!h||!t) return null; const hr=h.getBoundingClientRect(), tr=t.getBoundingClientRect(); return {dx:Math.abs(hr.left-tr.left), dy:Math.abs(hr.top-tr.top)};')
        self.page.mouse.up()
        self.page.wait_for_timeout(200)
        hint_after = H.doc_eval(self.page, 'return doc.querySelectorAll(\'[class*="hyp-size-hint"]\').length;')
        self.assertGreaterEqual(hint, 1)
        self.assertEqual(pe, "none")
        self.assertIsNotNone(pos)
        self.assertLessEqual(pos["dx"], 8)
        self.assertLessEqual(pos["dy"], 8)
        self.assertEqual(hint_after, 0)

    # E-R11-4 — Equal-size hint is serializer-EXEMPT.
    def test_e_r11_4_equal_size_hint_is_serializer_exempt(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        twinW = self.rendered("twin")["w"]
        self.select_by_native_id("node-accent")
        accW0 = self.rendered("node-accent")["w"]
        raw_target = twinW - 4.0
        target_travel = raw_target - accW0
        steps = 20
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, steps + 1):
            self.page.mouse.move(hx + target_travel * i / steps, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        out = os.path.join(tempfile.mkdtemp(), "saved.html")
        H.set_fake_dialog(self.base, out)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        with open(out, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("hyp-size-hint", text)
        self.assertEqual(re.findall(r'class="[^"]*hyp-size-hint', text), [])

    # E-R11-5 — NO phantom snap to a solver-derived flex-grow sibling width (F5 guard).
    def test_e_r11_5_no_phantom_snap_to_flex_grow_sibling(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        siblW = self.rendered("node-a")["w"]
        accW0 = self.rendered("node-accent")["w"]
        self.select_by_native_id("node-accent")
        # Overshoot the sibling by 10px so the final un-snapped width is not exactly siblW.
        raw_target = siblW - 10.0
        target_travel = raw_target - accW0
        steps = 12
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        mid = None
        hint = 0
        nearest = float("inf")
        for i in range(1, steps + 1):
            self.page.mouse.move(hx + target_travel * i / steps, hy)
            self.page.wait_for_timeout(40)
            cur_w = self.rendered("node-accent")["w"]
            d = abs(cur_w - siblW)
            if d < nearest:
                nearest = d
                mid = cur_w
                hint = H.doc_eval(self.page, 'return doc.querySelectorAll(\'[class*="hyp-size-hint"]\').length;')
        self.page.mouse.up()
        accW1 = self.rendered("node-accent")["w"]
        self.assertGreater(abs(accW1 - siblW), 1.0)
        self.assertEqual(hint, 0)

    # E-R11-6 — Alt + equal-size snap: center stays fixed after snap correction (ADX-6b).
    def test_e_r11_6_alt_equal_size_snap_center_fixed(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        # Inject a visible sibling with a specific width so twin has an equal-size candidate
        H.doc_eval(self.page, """
            const slide = doc.querySelector('.slide');
            const match = doc.createElement('div');
            match.id = 'match-target';
            match.setAttribute('data-hyp-id', 'match-target');
            match.style.width = '304px';
            match.style.height = '100px';
            match.style.background = '#ccc';
            slide.appendChild(match);
        """)
        self.select_by_native_id("twin")
        before = self.rendered("twin")
        center_before_x = (before["left"] + before["right"]) / 2
        twinW0 = before["w"]
        # Alt-resize east: target just past 304 so snap pulls it to exactly 304
        raw_target = 304 + 4
        target_travel = raw_target - twinW0
        steps = 15
        hx, hy = self.edge_handle_screen("e")
        self.page.keyboard.down("Alt")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, steps + 1):
            self.page.mouse.move(hx + target_travel * i / steps, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.keyboard.up("Alt")
        self.page.wait_for_timeout(200)
        after = self.rendered("twin")
        self.assertAlmostEqual(after["w"], 304, delta=0.5)
        # Center must stay fixed (Alt symmetric + snap-corrected shift)
        center_after_x = (after["left"] + after["right"]) / 2
        self.assertAlmostEqual(center_after_x, center_before_x, delta=3)


if __name__ == "__main__":
    unittest.main()
