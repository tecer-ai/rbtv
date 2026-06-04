import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8792


def _iframe_origin(page):
    return page.evaluate(
        "() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }"
    )


def _rect_in_iframe(page, selector):
    return H.doc_eval(
        page,
        f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};",
    )


def _screen_center(origin, rect):
    return origin["x"] + rect["x"] + rect["w"] / 2, origin["y"] + rect["y"] + rect["h"] / 2


class R2ResizeRealTests(unittest.TestCase):
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
        self.copy = H.copy_fixture()

    def tearDown(self):
        self.page.close()

    def _open(self):
        self.page.goto(self.base + "/app/")
        H.open_via_dialog_ui(self.page, self.base, self.copy)

    def _scroll_into_view(self, selector):
        """Scroll an element to viewport center, then WAIT (event-driven) until its
        rect is actually within the iframe viewport — no fixed timeout (RV14)."""
        H.doc_eval(self.page, f"const e=doc.querySelector({selector!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_function(
            """(sel) => {
                const f = document.querySelector('iframe.doc-frame');
                if (!f) return false;
                const d = f.contentDocument; if (!d) return false;
                const e = d.querySelector(sel); if (!e) return false;
                const r = e.getBoundingClientRect();
                const vh = f.contentWindow.innerHeight, vw = f.contentWindow.innerWidth;
                // visible within the iframe viewport (some part of the box on-screen)
                return r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw;
            }""",
            arg=selector,
            timeout=5000,
        )

    def _real_click(self, selector):
        """Select an element by a REAL mouse click at its on-screen center (no dispatchEvent)."""
        self._scroll_into_view(selector)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, selector)
        self.assertIsNotNone(rect, f"element {selector} not found for selection")
        cx, cy = _screen_center(origin, rect)
        self.page.mouse.click(cx, cy)
        self.page.wait_for_timeout(300)

    def _handle_center(self):
        """On-screen center of the SE (or E) resize handle inside the iframe."""
        origin = _iframe_origin(self.page)
        h = H.doc_eval(
            self.page,
            "const el=doc.querySelector('.moveable-control-box .moveable-se') || doc.querySelector('.moveable-control-box .moveable-e');"
            "if(!el) return null; const r=el.getBoundingClientRect();"
            "return {x:r.left,y:r.top,w:r.width,h:r.height,"
            " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};",
        )
        self.assertIsNotNone(h, "resize handle (.moveable-se / .moveable-e) not rendered after selection")
        self.assertTrue(h["in_vp"], f"resize handle center is outside the iframe viewport ({origin['x'] + h['x'] + h['w']/2},{origin['y'] + h['y'] + h['h']/2}) — control box mis-placed (R2 product bug)")
        return origin["x"] + h["x"] + h["w"] / 2, origin["y"] + h["y"] + h["h"] / 2

    def _iframe_handle_local_center(self):
        """Handle center in IFRAME-local coordinates (for elementFromPoint inside the iframe doc)."""
        h = H.doc_eval(
            self.page,
            "const el=doc.querySelector('.moveable-control-box .moveable-se') || doc.querySelector('.moveable-control-box .moveable-e');"
            "if(!el) return null; const r=el.getBoundingClientRect();"
            "return {x:r.left+r.width/2, y:r.top+r.height/2,"
            " in_vp:(r.left+r.width/2>=0 && r.left+r.width/2<=win.innerWidth && r.top+r.height/2>=0 && r.top+r.height/2<=win.innerHeight)};",
        )
        self.assertIsNotNone(h, "resize handle not rendered")
        self.assertTrue(h["in_vp"], f"resize handle center is outside the iframe viewport ({h['x']},{h['y']}) — control box mis-placed (R2 product bug)")
        return h["x"], h["y"]

    # E-R2-1 — hittability guard (the direct R2 root-cause lock)
    def test_handle_is_hittable(self):
        self._open()
        self._real_click(".research-card")
        hx, hy = self._iframe_handle_local_center()
        hit_class = H.doc_eval(
            self.page,
            f"const el=doc.elementFromPoint({hx},{hy}); return el ? (el.className && el.className.toString ? el.className.toString() : String(el.className)) : null;",
        )
        self.assertIsNotNone(hit_class, "elementFromPoint(handleCenter) is null — handle is not hittable (R2 root cause)")
        self.assertIn("moveable-", hit_class, f"elementFromPoint hit a non-moveable element: {hit_class!r}")

    # E-R2-2 — resize changes computed geometry
    def test_resize_changes_geometry(self):
        self._open()
        self._real_click(".research-card")
        before = H.doc_eval(
            self.page,
            "const e=doc.querySelector('.research-card'); const cs=getComputedStyle(e); return {w:parseFloat(cs.width), h:parseFloat(cs.height)};",
        )
        hx, hy = self._handle_center()
        self.page.mouse.move(hx, hy)
        self.page.mouse.down()
        for i in range(1, 11):
            self.page.mouse.move(hx + i * 6, hy + i * 4)
            self.page.wait_for_timeout(30)
        self.page.mouse.up()
        self.page.wait_for_timeout(200)
        after = H.doc_eval(
            self.page,
            "const e=doc.querySelector('.research-card'); const cs=getComputedStyle(e); return {w:parseFloat(cs.width), h:parseFloat(cs.height)};",
        )
        self.assertNotAlmostEqual(after["w"], before["w"], delta=2,
                                  msg=f"width did not change on resize: {before['w']} -> {after['w']} (R2 still dead)")
        self.assertNotAlmostEqual(after["h"], before["h"], delta=2,
                                  msg=f"height did not change on resize: {before['h']} -> {after['h']} (R2 still dead)")
        self.assertGreater(after["w"], before["w"] - 5, "width should grow with a +drag")

    # E-R2-3 — twice (idempotency, N>=2)
    def test_resize_twice(self):
        self._open()
        self._real_click(".research-card")

        def drag_once():
            hx, hy = self._handle_center()
            self.page.mouse.move(hx, hy)
            self.page.mouse.down()
            for i in range(1, 9):
                self.page.mouse.move(hx + i * 6, hy + i * 4)
                self.page.wait_for_timeout(25)
            self.page.mouse.up()
            self.page.wait_for_timeout(150)

        w0 = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.research-card')).width);")
        drag_once()
        w1 = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.research-card')).width);")
        drag_once()
        w2 = H.doc_eval(self.page, "return parseFloat(getComputedStyle(doc.querySelector('.research-card')).width);")
        self.assertNotAlmostEqual(w1, w0, delta=2, msg="first resize had no effect")
        self.assertNotAlmostEqual(w2, w1, delta=2, msg="second resize had no effect (handle is one-shot — R2 not fully fixed)")

    # E-R2-4 — MOVE: a real body drag >=40px changes the CSS `translate` by ~the drag delta
    def test_move_changes_translate_by_delta(self):
        self._open()
        self._real_click(".slide-number")

        def parse_translate(s):
            s = (s or "").strip()
            if not s:
                return 0.0, 0.0
            parts = s.split()
            tx = float(parts[0].replace("px", "")) if parts else 0.0
            ty = float(parts[1].replace("px", "")) if len(parts) > 1 else 0.0
            return tx, ty

        before = H.doc_eval(self.page, "return doc.querySelector('.slide-number').style.translate || '';")
        bx, by = parse_translate(before)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, ".slide-number")
        cx, cy = _screen_center(origin, rect)
        # .slide-number is an absolutely-positioned corner badge; dragging right lands in
        # empty space (classifyDrop=none ⇒ keep-translate), exercising MOVE rather than reorder.
        DX, DY = 40, 0
        self.page.mouse.move(cx, cy)
        self.page.mouse.down()
        for i in range(1, 9):
            self.page.mouse.move(cx + (DX * i) / 8.0, cy + (DY * i) / 8.0)
            self.page.wait_for_timeout(20)
        self.page.mouse.up()
        self.page.wait_for_timeout(150)
        after = H.doc_eval(self.page, "return doc.querySelector('.slide-number').style.translate || '';")
        ax, ay = parse_translate(after)
        self.assertTrue(after.strip() != "", f"body drag did not write style.translate (got {after!r})")
        # the translate delta must approximate the drag delta (snapping tolerance ±15px)
        self.assertAlmostEqual(ax - bx, DX, delta=15, msg=f"translate-x delta {ax-bx} not ~{DX} (move dead/wrong)")
        self.assertAlmostEqual(ay - by, DY, delta=15, msg=f"translate-y delta {ay-by} not ~{DY} (move dead/wrong)")

    # E-R2-5 — REORDER: one real drag of a sibling over its adjacent sibling changes the DOM index
    def test_reorder_changes_dom_index(self):
        self._open()
        # Find a parent that has >= 2 sibling children both bearing data-hyp-id (a reorderable pair).
        pair = H.doc_eval(
            self.page,
            "const headers=Array.from(doc.querySelectorAll('.slide-header'));"
            "for(const h of headers){"
            " const sibs=Array.from(h.children).filter(c=>c.getAttribute('data-hyp-id'));"
            " if(sibs.length>=2){"
            "  return {first:sibs[0].getAttribute('data-hyp-id'), second:sibs[1].getAttribute('data-hyp-id')};}}"
            "const all=Array.from(doc.querySelectorAll('[data-hyp-id]'));"
            "for(const el of all){const p=el.parentElement; if(!p) continue;"
            " if(p===doc.body) continue;"
            " const sibs=Array.from(p.children).filter(c=>c.getAttribute('data-hyp-id'));"
            " if(sibs.length>=2){"
            "  const r0=sibs[0].getBoundingClientRect();"
            "  if(r0.width>=win.innerWidth*0.9 && r0.height>=win.innerHeight*0.9) continue;"
            "  return {first:sibs[0].getAttribute('data-hyp-id'), second:sibs[1].getAttribute('data-hyp-id')};}}"
            "return null;",
        )
        self.assertIsNotNone(pair, "fixture has no parent with two data-hyp-id siblings to reorder")
        first_id, second_id = pair["first"], pair["second"]

        def index_of(hyp):
            return H.doc_eval(
                self.page,
                f'const e=doc.querySelector(\'[data-hyp-id="{hyp}"]\'); if(!e) return -1;'
                "return Array.from(e.parentElement.children).indexOf(e);",
            )

        idx_before = index_of(first_id)
        # select the FIRST sibling, then real-drag it onto the SECOND sibling's center (overlap → reorder)
        sel_first = f'[data-hyp-id="{first_id}"]'
        self._real_click(sel_first)
        origin = _iframe_origin(self.page)
        r1 = _rect_in_iframe(self.page, sel_first)
        r2 = _rect_in_iframe(self.page, f'[data-hyp-id="{second_id}"]')
        self.assertIsNotNone(r2, "second sibling rect not found")
        sx, sy = _screen_center(origin, r1)
        tx = origin["x"] + r2["x"] + r2["w"] / 2
        ty = origin["y"] + r2["y"] + r2["h"] * 0.75   # lower half ⇒ insertBefore=false ⇒ real index change
        self.page.mouse.move(sx, sy)
        self.page.mouse.down()
        steps = 10
        for i in range(1, steps + 1):
            self.page.mouse.move(sx + (tx - sx) * i / steps, sy + (ty - sy) * i / steps)
            self.page.wait_for_timeout(20)
        self.page.mouse.up()
        self.page.wait_for_timeout(300)
        idx_after = index_of(first_id)
        self.assertNotEqual(
            idx_after, idx_before,
            f"a real drag of one sibling over its neighbor must change its DOM index (reorder dead): {idx_before} -> {idx_after}",
        )

    # E-R2-7 — control box alignment with target (regression guard for position:fixed coordinate-frame bug)
    def test_control_box_aligns_with_target(self):
        self._open()
        # .slide-title has no registered child at its geometric centre, so the registry
        # selects .slide-title itself — no selection-vs-clicked mismatch (v3-t2c-debug.md §2).
        self._real_click(".slide-title")
        alignment = H.doc_eval(
            self.page,
            "const box=doc.querySelector('.moveable-control-box');"
            "const ring=doc.querySelector('.hyp-selection-ring');"
            "if(!box || !ring) return null;"
            "const rr=ring.getBoundingClientRect();"
            # Resolve the ACTUALLY-selected element by matching ring geometry (D26(b)).
            "const candidates=Array.from(doc.querySelectorAll('[data-hyp-id]')).filter(el=>{"
            " const r=el.getBoundingClientRect();"
            " return Math.abs(r.left-rr.left)<2 && Math.abs(r.top-rr.top)<2"
            "  && Math.abs(r.width-rr.width)<2 && Math.abs(r.height-rr.height)<2;});"
            "const target=candidates[0];"
            "if(!target) return null;"
            "const tr=target.getBoundingClientRect();"
            "const br=box.getBoundingClientRect();"
            "return {tx:tr.left, ty:tr.top, bx:br.left, by:br.top, dx:br.left-tr.left, dy:br.top-tr.top};",
        )
        self.assertIsNotNone(alignment, "control box, ring, or matching selected element not found")
        self.assertLessEqual(abs(alignment["dx"]), 8,
            f"control-box left {alignment['bx']}px is >8px from selected-element left {alignment['tx']}px (coordinate frame regression)")
        self.assertLessEqual(abs(alignment["dy"]), 8,
            f"control-box top {alignment['by']}px is >8px from selected-element top {alignment['ty']}px (coordinate frame regression)")

    # E-R2-6 — no console errors
    def test_no_console_errors(self):
        self._open()
        errors = []
        def on_console(msg):
            if msg.type == "error":
                t = msg.text
                if "assets/" in t and ("404" in t or "Failed to load resource" in t):
                    return
                errors.append(t)
        self.page.on("console", on_console)
        self._real_click(".research-card")
        self.assertEqual(len(errors), 0, f"unexpected console errors: {errors}")


if __name__ == "__main__":
    unittest.main()
