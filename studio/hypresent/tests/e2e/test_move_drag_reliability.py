import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

import conftest_helpers as H


PORT = 8796


class MoveDragReliabilityTests(unittest.TestCase):
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
        self.page = self.browser.new_page(viewport={"width": 1400, "height": 950})
        self.page.goto(self.base + "/app/")
        H.preset_author(self.page)
        self.copy = H.copy_fixture()
        H.open_via_dialog_ui(self.page, self.base, self.copy)
        self._install_fixture()

    def tearDown(self):
        self.page.close()

    def _install_fixture(self):
        self.page.evaluate(
            """() => {
                const f = document.querySelector('iframe.doc-frame');
                const doc = f.contentDocument;
                doc.body.insertAdjacentHTML('beforeend', `
                  <div id="p2-stage" data-hyp-id="p2-stage" style="position:relative;margin:80px;width:900px;padding:24px;border:1px solid #ddd;background:white;">
                    <div id="p2-left" data-hyp-id="p2-left" style="display:flex;gap:14px;align-items:center;margin-bottom:48px;">
                      <div id="p2-a" data-hyp-id="p2-a" style="width:110px;height:64px;background:#dbeafe;">A</div>
                      <div id="p2-b" data-hyp-id="p2-b" style="width:110px;height:64px;background:#dcfce7;">B</div>
                      <div id="p2-c" data-hyp-id="p2-c" style="width:110px;height:64px;background:#fef3c7;">C</div>
                    </div>
                    <div id="p2-right" data-hyp-id="p2-right" style="display:flex;gap:14px;align-items:center;margin-bottom:48px;">
                      <div id="p2-x" data-hyp-id="p2-x" style="width:110px;height:64px;background:#fee2e2;">X</div>
                      <div id="p2-y" data-hyp-id="p2-y" style="width:110px;height:64px;background:#ede9fe;">Y</div>
                    </div>
                    <div id="p2-grid" data-hyp-id="p2-grid" style="display:grid;grid-template-columns:110px 110px 110px;gap:14px;">
                      <div id="p2-g1" data-hyp-id="p2-g1" style="height:64px;background:#e0f2fe;">G1</div>
                      <div id="p2-g2" data-hyp-id="p2-g2" style="height:64px;background:#fce7f3;">G2</div>
                      <div id="p2-g3" data-hyp-id="p2-g3" style="height:64px;background:#ecfccb;">G3</div>
                    </div>
                    <div id="p2-block" data-hyp-id="p2-block" style="display:block;margin-top:48px;width:360px;">
                      <div id="p2-k1" data-hyp-id="p2-k1" style="height:48px;margin-bottom:12px;background:#fae8ff;">K1</div>
                      <div id="p2-k2" data-hyp-id="p2-k2" style="height:48px;margin-bottom:12px;background:#ccfbf1;">K2</div>
                      <div id="p2-k3" data-hyp-id="p2-k3" style="height:48px;background:#ffedd5;">K3</div>
                    </div>
                  </div>
                `);
                doc.getElementById('p2-stage').scrollIntoView({block: 'center'});
                f.contentWindow.__p2Tagged = false;
                const s = doc.createElement('script');
                s.type = 'module';
                s.textContent = "import('/runtime/js/element-registry.js').then(m => { m.tag(); self.__p2Tagged = true; });";
                doc.head.appendChild(s);
            }"""
        )
        self.page.wait_for_function(
            """() => {
                const f = document.querySelector('iframe.doc-frame');
                return !!(f && f.contentWindow && f.contentWindow.__p2Tagged);
            }""",
            timeout=5000,
        )

    def _frame(self):
        return self.page.frame_locator("iframe.doc-frame")

    def _box(self, hyp_id):
        box = self._frame().locator(f'[data-hyp-id="{hyp_id}"]').first.bounding_box()
        if not box:
            raise AssertionError(f"Missing bounding box for {hyp_id}")
        return box

    def _select(self, hyp_id):
        self._frame().locator(f'[data-hyp-id="{hyp_id}"]').first.click()
        self._frame().locator("#hyp-interaction-wrapper").wait_for(timeout=10000)
        self.page.wait_for_timeout(150)

    def _drag_to(self, drag_id, target_id, x_frac=0.75, y_frac=0.5, shift=False):
        self._select(drag_id)
        drag_box = self._box(drag_id)
        target_box = self._box(target_id)
        start_x = drag_box["x"] + drag_box["width"] / 2
        start_y = drag_box["y"] + drag_box["height"] / 2
        end_x = target_box["x"] + target_box["width"] * x_frac
        end_y = target_box["y"] + target_box["height"] * y_frac
        self.page.mouse.move(start_x, start_y)
        if shift:
            self.page.keyboard.down("Shift")
        self.page.mouse.down()
        self.page.mouse.move(end_x, end_y, steps=14)
        self.page.mouse.up()
        if shift:
            self.page.keyboard.up("Shift")
        self.page.wait_for_timeout(500)

    def _state(self):
        return H.doc_eval(
            self.page,
            """
            const ids = ['p2-a','p2-b','p2-c','p2-x','p2-y','p2-g1','p2-g2','p2-g3'];
            const out = {};
            for (const id of ids) {
              const el = doc.querySelector(`[data-hyp-id="${id}"]`);
              const r = el.getBoundingClientRect();
              out[id] = {
                parent: el.parentElement.getAttribute('data-hyp-id'),
                order: Array.from(el.parentElement.children).map(c => c.getAttribute('data-hyp-id')).filter(Boolean),
                translate: el.style.translate || '',
                transform: el.style.transform || '',
                rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
              };
            }
            return out;
            """,
        )

    def _order(self, parent_id):
        return H.doc_eval(
            self.page,
            f"""
            const parent = doc.querySelector('[data-hyp-id="{parent_id}"]');
            return Array.from(parent.children).map(c => c.getAttribute('data-hyp-id')).filter(Boolean);
            """,
        )

    def test_plain_drag_keeps_translate_parent_size_and_order(self):
        before = self._state()
        self._drag_to("p2-a", "p2-b", shift=False)
        after = self._state()

        self.assertEqual(after["p2-a"]["parent"], before["p2-a"]["parent"])
        self.assertEqual(after["p2-a"]["order"], before["p2-a"]["order"])
        self.assertEqual(after["p2-a"]["rect"]["w"], before["p2-a"]["rect"]["w"])
        self.assertEqual(after["p2-a"]["rect"]["h"], before["p2-a"]["rect"]["h"])
        self.assertNotEqual(after["p2-a"]["translate"], "")
        self.assertNotEqual(after["p2-a"]["rect"]["x"], before["p2-a"]["rect"]["x"])

    def test_shift_drag_reorders_same_parent(self):
        before = self._state()["p2-a"]["order"]
        self._drag_to("p2-a", "p2-c", x_frac=0.9, shift=True)
        after = self._state()["p2-a"]["order"]

        self.assertNotEqual(after, before)
        self.assertEqual(after, ["p2-b", "p2-c", "p2-a"])
        self.assertEqual(self._state()["p2-a"]["translate"], "")

    def test_shift_drag_reorders_grid_and_block_midpoints(self):
        self._drag_to("p2-g1", "p2-g3", x_frac=0.8, shift=True)
        self.assertEqual(self._order("p2-grid"), ["p2-g2", "p2-g3", "p2-g1"])
        self._drag_to("p2-g1", "p2-g2", x_frac=0.2, shift=True)
        self.assertEqual(self._order("p2-grid"), ["p2-g1", "p2-g2", "p2-g3"])

        self._drag_to("p2-k1", "p2-k3", y_frac=0.8, shift=True)
        self.assertEqual(self._order("p2-block"), ["p2-k2", "p2-k3", "p2-k1"])
        self._drag_to("p2-k1", "p2-k2", y_frac=0.2, shift=True)
        self.assertEqual(self._order("p2-block"), ["p2-k1", "p2-k2", "p2-k3"])

    def test_shift_drag_reparents_to_different_container(self):
        self._drag_to("p2-a", "p2-x", x_frac=0.25, shift=True)
        after = self._state()

        self.assertEqual(after["p2-a"]["parent"], "p2-right")
        self.assertEqual(after["p2-x"]["order"], ["p2-a", "p2-x", "p2-y"])
        self.assertEqual(after["p2-a"]["translate"], "")

    def test_undo_restores_pre_drag_translate_after_structural_drop(self):
        H.doc_eval(
            self.page,
            "doc.querySelector('[data-hyp-id=\"p2-a\"]').style.translate = '12px 8px'; return true;",
        )
        before = self._state()
        self._drag_to("p2-a", "p2-c", x_frac=0.9, shift=True)
        self._frame().locator("body").press("Control+z")
        self.page.wait_for_timeout(300)
        after = self._state()

        self.assertEqual(after["p2-a"]["parent"], before["p2-a"]["parent"])
        self.assertEqual(after["p2-a"]["order"], before["p2-a"]["order"])
        self.assertEqual(after["p2-a"]["translate"], "12px 8px")

    def test_flip_preserves_displaced_sibling_transform(self):
        H.doc_eval(
            self.page,
            "doc.querySelector('[data-hyp-id=\"p2-b\"]').style.transform = 'rotate(8deg)'; return true;",
        )
        self._drag_to("p2-a", "p2-c", x_frac=0.9, shift=True)
        self.page.wait_for_timeout(300)
        after = self._state()

        self.assertIn("rotate(8deg)", after["p2-b"]["transform"])


if __name__ == "__main__":
    unittest.main()
