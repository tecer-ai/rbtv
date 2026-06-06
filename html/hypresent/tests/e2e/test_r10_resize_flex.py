import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8810


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


def bridge_command(page, type_, payload=None):
    """postMessage command round-trip for {undo, redo}. Mirrors bridge_get_selection."""
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
                        if (e.data.ok) resolve(e.data.result);
                        else reject(new Error(e.data.error));
                    }
                };
                window.addEventListener('message', handler);
                iframe.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', id, type, ...(payload||{}) },
                    location.origin
                );
                setTimeout(() => { window.removeEventListener('message', handler); reject(new Error('bridge '+type+' timed out')); }, 5000);
            });
        }
        """,
        [type_, payload or {}],
    )


_HANDLE_SELECTOR = {
    "e":  ".moveable-control-box .moveable-line.moveable-e, .moveable-control-box .moveable-control.moveable-e, .moveable-control-box .moveable-e",
    "se": ".moveable-control-box .moveable-control.moveable-se, .moveable-control-box .moveable-se",
    "ne": ".moveable-control-box .moveable-control.moveable-ne, .moveable-control-box .moveable-ne",
    "w":  ".moveable-control-box .moveable-line.moveable-w, .moveable-control-box .moveable-control.moveable-w, .moveable-control-box .moveable-w",
}


class R10ResizeFlexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ("flow-grow.html", "flow-grow-deadzone.html", "grid-healthy.html"):
            if not os.path.exists(os.path.join(H.SYN_DIR, name)):
                raise AssertionError(f"Required synthetic fixture missing: {name}")
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
        self.page.mouse.click(origin["x"]+rect["x"]+5, origin["y"]+rect["y"]+5)  # +5 → target itself, not a child
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

    # E-R10-1 — Slack-row amplification killed (flow-grow.html)
    def test_e_r10_1_slack_row_amplification_killed(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("node-accent")
        before = self.rendered("node-accent")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("node-accent")
        self.assertAlmostEqual(after["w"] - before["w"], 60, delta=2)
        self.assertEqual(float(after["inlGrow"]), 0.0)
        self.assertEqual(float(after["inlShrink"]), 0.0)
        self.assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] + 60 - 48, delta=1)

    # E-R10-2 — No-slack dead zone killed (flow-grow-deadzone.html)
    def test_e_r10_2_no_slack_dead_zone_killed(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow-deadzone.html"))
        self.select_by_native_id("node-accent")
        before = self.rendered("node-accent")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx - i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("node-accent")
        self.assertAlmostEqual(after["w"] - before["w"], -60, delta=2)
        self.assertEqual(float(after["inlGrow"]), 0.0)
        self.assertEqual(float(after["inlShrink"]), 0.0)
        self.assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] - 60 - 48, delta=1)

    # E-R10-2b — First-gesture escape on the leftover-pinned fixture (flow-grow-deadzone.html)
    def test_e_r10_2b_first_gesture_escape(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow-deadzone.html"))
        self.select_by_native_id("node-accent")
        before = self.rendered("node-accent")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx - i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("node-accent")
        self.assertAlmostEqual(after["w"] - before["w"], -60, delta=2)
        self.assertEqual(float(after["inlGrow"]), 0.0)
        self.assertEqual(float(after["inlShrink"]), 0.0)
        self.assertAlmostEqual(parse_px(after["inlBasis"]), before["w"] - 60 - 48, delta=1)

    # E-R10-3 — Healthy block width path UNCHANGED (flow-grow.html)
    def test_e_r10_3_healthy_block_width_unchanged(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        before = self.rendered("twin")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 5, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("twin")
        self.assertAlmostEqual(parse_px(after["inlWidth"]), 300 + 50, delta=2)
        self.assertEqual(after["inlBasis"], "")
        self.assertEqual(after["inlGrow"], "")

    # E-R10-4 — Healthy grid MIDDLE column unchanged (grid-healthy.html)
    def test_e_r10_4_healthy_grid_middle_unchanged(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("grid-healthy.html"))
        self.select_by_native_id("grid-mid")
        before = self.rendered("grid-mid")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6.1, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("grid-mid")
        self.assertAlmostEqual(after["w"] - before["w"], 61, delta=2)
        self.assertEqual(after["inlBasis"], "")
        self.assertEqual(after["inlGrow"], "")
        self.assertAlmostEqual(before["left"] - after["left"], 0, delta=2)

    # E-R10-5 — Healthy grid START-PINNED column unchanged (grid-healthy.html)
    def test_e_r10_5_healthy_grid_start_pinned_unchanged(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("grid-healthy.html"))
        self.select_by_native_id("grid-start")
        before = self.rendered("grid-start")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx - i * 16, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("grid-start")
        self.assertAlmostEqual(after["w"] - before["w"], -160, delta=2)
        self.assertEqual(after["inlBasis"], "")
        self.assertEqual(after["inlGrow"], "")
        self.assertLessEqual(abs(after["left"] - before["left"]), 3)

    # E-R10-6 — Corner height axis tracks cursor to the content floor (flow-grow.html)
    def test_e_r10_6_corner_height_tracks_cursor(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("twin")
        content_floor = H.doc_eval(self.page, "const e=doc.querySelector('#twin'); const prev=e.style.height; e.style.height='0'; const f=e.getBoundingClientRect().height; e.style.height=prev; return f;")
        before = self.rendered("twin")
        hx, hy = self.edge_handle_screen("ne")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 7):
            self.page.mouse.move(hx, hy + i * 6)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        after = self.rendered("twin")
        self.assertLess(after["h"], before["h"])
        self.assertGreaterEqual(after["h"], before["h"] - 40)
        self.assertTrue(abs((before["h"] - after["h"]) - min(36, before["h"] - content_floor)) <= 3)

    # G-R10-UNDO — Undo restores ALL three flex longhands incl. absent-inline (flow-grow.html)
    def test_g_r10_undo_restores_flex_longhands(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("node-accent")
        pre = {k: self.rendered("node-accent")[k] for k in ("inlBasis", "inlGrow", "inlShrink")}
        before_gesture = self.rendered("node-accent")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        bridge_command(self.page, "undo")
        self.page.wait_for_timeout(150)
        post = {k: self.rendered("node-accent")[k] for k in ("inlBasis", "inlGrow", "inlShrink")}
        after_undo = self.rendered("node-accent")
        self.assertEqual(post["inlBasis"], pre["inlBasis"])
        self.assertEqual(post["inlGrow"], pre["inlGrow"])
        self.assertEqual(post["inlShrink"], pre["inlShrink"])
        self.assertAlmostEqual(after_undo["w"], before_gesture["w"], delta=2)

    # G-R10-REDO — Undo→redo idempotence (flow-grow.html)
    def test_g_r10_redo_idempotence(self):
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("flow-grow.html"))
        self.select_by_native_id("node-accent")
        hx, hy = self.edge_handle_screen("e")
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        post_gesture_w = self.rendered("node-accent")["w"]
        bridge_command(self.page, "undo")
        self.page.wait_for_timeout(150)
        bridge_command(self.page, "redo")
        self.page.wait_for_timeout(150)
        after = self.rendered("node-accent")
        self.assertAlmostEqual(after["w"], post_gesture_w, delta=2)
        self.assertEqual(float(after["inlGrow"] or 0), 0.0)


if __name__ == "__main__":
    unittest.main()
