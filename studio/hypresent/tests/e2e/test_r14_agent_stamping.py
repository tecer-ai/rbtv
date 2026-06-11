import os, sys, re, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8814


def _iframe_origin(page):
    return page.evaluate("() => { const f=document.querySelector('iframe.doc-frame'); const r=f.getBoundingClientRect(); return {x:r.left,y:r.top}; }")


def _rect_in_iframe(page, selector):
    return H.doc_eval(page, f"const e=doc.querySelector({selector!r}); if(!e) return null; const r=e.getBoundingClientRect(); return {{x:r.left,y:r.top,w:r.width,h:r.height}};")


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


class TestR14AgentStamping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(os.path.join(H.SYN_DIR, "agent-comments.html")):
            raise AssertionError("Required synthetic fixture missing: agent-comments.html")
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
        H.open_via_dialog_ui(self.page, self.base, H.copy_synthetic("agent-comments.html"))

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
        sel = f'#{native_id}'
        H.doc_eval(self.page, f"const e=doc.querySelector({sel!r}); if(e) e.scrollIntoView({{block:'center'}});")
        self.page.wait_for_timeout(200)
        origin = _iframe_origin(self.page)
        rect = _rect_in_iframe(self.page, sel)
        self.assertIsNotNone(rect, f"{sel} not found")
        self.page.mouse.click(origin["x"]+rect["x"]+5, origin["y"]+rect["y"]+5)
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
        # Fallback agent tagging via per-thread toggle if composer checkbox absent
        if agent:
            island = self._read_island()
            if island and not island[-1].get("agentInstruction"):
                toggle = self.page.locator("#comment-threads .comment-agent-toggle input").last
                if toggle.count():
                    toggle.check()
                    self.page.wait_for_timeout(300)

    def _add_reply(self, text):
        reply_input = self.page.locator("#comment-threads .comment-thread .comment-reply-input").first
        reply_input.fill(text)
        reply_input.press("Enter")
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

    def _extract_head_block(self, text):
        m = re.search(r'===== HYPRESENT AGENT INSTRUCTIONS =====.*?(?=-->)', text, re.S)
        return m.group(0) if m else ""

    # ---- E-R14-1: Single agent thread: stamp + selector resolves the right element ----
    def test_e_r14_1_single_agent_thread_stamp_and_resolve(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        threads = self._read_island()
        self.assertEqual(len(threads), 1)
        id0 = threads[0]["id"]

        out1 = self._save_to_temp("-r14-1.html")
        text1 = self._read_text(out1)

        # DOM-scoped: exactly one stamped element in the saved file
        fresh1 = self.browser.new_page()
        try:
            fresh1.goto("file://" + os.path.abspath(out1), wait_until="networkidle", timeout=10000)
            stamped = fresh1.evaluate("() => document.querySelectorAll('[data-hyp-agent]').length")
            self.assertEqual(stamped, 1, "Expected exactly one stamped element in saved file")
        finally:
            fresh1.close()

        # Value contains id0
        self.assertIn(id0, text1)
        # Stamped element is <p id="p-lead">
        stamp_match = re.search(r'<p[^>]*id="p-lead"[^>]*data-hyp-agent="([^"]*)"', text1)
        if not stamp_match:
            stamp_match = re.search(r'<p[^>]*data-hyp-agent="([^"]*)"[^>]*id="p-lead"', text1)
        self.assertIsNotNone(stamp_match, "p-lead should carry data-hyp-agent")
        self.assertIn(id0, stamp_match.group(1))

        # Head block contains target selector and self-cleanup directive
        block = self._extract_head_block(text1)
        self.assertIn(f'target: [data-hyp-agent~="{id0}"]', block)
        self.assertIn("remove the data-hyp-agent", block)

        # Reopen-resolve
        H.open_via_dialog_ui(self.page, self.base, out1)
        self.page.wait_for_timeout(500)
        result = H.doc_eval(self.page, f'const m=doc.querySelectorAll(\'[data-hyp-agent~="{id0}"]\'); return {{n:m.length, text:m[0]?m[0].textContent.slice(0,30):null}};')
        self.assertEqual(result["n"], 1)
        self.assertIn("Plataforma inteligente", result["text"])

    # ---- E-R14-2: Two agent threads on SAME element ----
    def test_e_r14_2_two_agent_threads_same_element(self):
        self._select("p-lead")
        self._add_comment("a", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        self._select("p-lead")
        self._add_comment("b", agent=True)
        threads = self._read_island()
        id1 = threads[1]["id"]

        out = self._save_to_temp("-r14-2.html")
        text = self._read_text(out)

        # Lead element's data-hyp-agent value == "<id0> <id1>"
        stamp_match = re.search(r'<p[^>]*id="p-lead"[^>]*data-hyp-agent="([^"]*)"', text)
        if not stamp_match:
            stamp_match = re.search(r'<p[^>]*data-hyp-agent="([^"]*)"[^>]*id="p-lead"', text)
        self.assertIsNotNone(stamp_match)
        self.assertEqual(stamp_match.group(1), f"{id0} {id1}")

        # Two block entries
        block = self._extract_head_block(text)
        self.assertEqual(block.count("[agent:"), 2)

        # Reopen: each selector resolves the single shared element
        H.open_via_dialog_ui(self.page, self.base, out)
        self.page.wait_for_timeout(500)
        r0 = H.doc_eval(self.page, f'const m=doc.querySelectorAll(\'[data-hyp-agent~="{id0}"]\'); return m.length;')
        r1 = H.doc_eval(self.page, f'const m=doc.querySelectorAll(\'[data-hyp-agent~="{id1}"]\'); return m.length;')
        self.assertEqual(r0, 1)
        self.assertEqual(r1, 1)

    # ---- E-R14-3: Resolved/deleted threads don't stamp ----
    def test_e_r14_3_resolved_deleted_threads_no_stamp(self):
        self._select("p-lead")
        self._add_comment("lead comment", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        self._select("p-arch")
        self._add_comment("arch comment", agent=True)
        threads = self._read_island()
        id1 = threads[1]["id"]

        # Resolve id0
        bridge_command(self.page, "resolve-comment", {"commentId": id0, "resolved": True})
        self.page.wait_for_timeout(300)
        outR = self._save_to_temp("-r14-3r.html")
        textR = self._read_text(outR)

        # No stamp for id0, no block entry for id0; id1 still stamped
        self.assertNotIn(f'data-hyp-agent="{id0}"', textR)
        self.assertNotIn(f'data-hyp-agent~="{id0}"', textR)
        blockR = self._extract_head_block(textR)
        self.assertNotIn(f"[agent:{id0}]", blockR)
        self.assertIn(id1, textR)  # id1 still present somewhere

        # Delete id1 on live doc
        bridge_command(self.page, "delete-comment", {"commentId": id1})
        self.page.wait_for_timeout(300)
        outD = self._save_to_temp("-r14-3d.html")
        textD = self._read_text(outD)

        # No stamp/entry for id1
        self.assertNotIn(f'data-hyp-agent="{id1}"', textD)
        self.assertNotIn(f'data-hyp-agent~="{id1}"', textD)
        blockD = self._extract_head_block(textD)
        self.assertNotIn(f"[agent:{id1}]", blockD)

    # ---- E-R14-4: Live DOM stays clean after save ----
    def test_e_r14_4_live_dom_clean_after_save(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        out = self._save_to_temp("-r14-4.html")
        # Immediately after save
        count = H.doc_eval(self.page, "return doc.querySelectorAll('[data-hyp-agent]').length;")
        self.assertEqual(count, 0)

    # ---- E-R14-5: Block format completeness ----
    def test_e_r14_5_block_format_completeness(self):
        self._select("p-lead")
        self._add_comment("rename heading", agent=True)
        self._add_reply("also bold it")
        out = self._save_to_temp("-r14-5.html")
        text = self._read_text(out)
        block = self._extract_head_block(text)

        self.assertIn("target: [data-hyp-agent", block)
        self.assertIn('context: p .lead | "', block)
        self.assertIn("instruction: rename heading", block)
        self.assertIn("reply: also bold it", block)
        self.assertIn("author:", block)
        self.assertIn("date:", block)
        self.assertIn("remove the data-hyp-agent", block)
        # Reply-don't-resolve convention (comment-implementation protocol): the
        # preamble instructs a reply under the agent name and forbids closing the thread.
        self.assertIn("do NOT delete the comment thread", block)

    # ---- E-R14-6: Stamping idempotence across multiple saves ----
    def test_e_r14_6_stamping_idempotence(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        out2 = self._save_to_temp("-r14-6a.html")
        text2 = self._read_text(out2)

        # DOM-scoped: first save has exactly one stamped element
        fresh2 = self.browser.new_page()
        try:
            fresh2.goto("file://" + os.path.abspath(out2), wait_until="networkidle", timeout=10000)
            stamped2 = fresh2.evaluate("() => document.querySelectorAll('[data-hyp-agent]').length")
            self.assertEqual(stamped2, 1, "Expected exactly one stamped element in first save")
        finally:
            fresh2.close()

        # Reopen out2 and save again
        H.open_via_dialog_ui(self.page, self.base, out2)
        self.page.wait_for_timeout(500)
        out3 = self._save_to_temp("-r14-6b.html")
        text3 = self._read_text(out3)

        # DOM-scoped: second save still has exactly one stamped element (idempotence)
        fresh3 = self.browser.new_page()
        try:
            fresh3.goto("file://" + os.path.abspath(out3), wait_until="networkidle", timeout=10000)
            stamped3 = fresh3.evaluate("() => document.querySelectorAll('[data-hyp-agent]').length")
            self.assertEqual(stamped3, 1, "Expected exactly one stamped element in second save")
        finally:
            fresh3.close()

        # Value is exactly id0
        stamp_match = re.search(r'data-hyp-agent="([^"]*)"', text3)
        self.assertIsNotNone(stamp_match)
        self.assertEqual(stamp_match.group(1), id0)
        # Exactly one block entry
        block = self._extract_head_block(text3)
        self.assertEqual(block.count("[agent:"), 1)

    # ---- E-R14-7: Node-count guard safe with stamps ----
    def test_e_r14_7_node_count_guard_safe_with_stamps(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        self._select("p-arch")
        self._add_comment("fix arch", agent=True)
        self._select("li-2")
        self._add_comment("fix li2", agent=True)

        out = self._save_to_temp("-r14-7.html")
        self.page.wait_for_function(
            "() => document.getElementById('doc-state')?.textContent === 'Saved'",
            timeout=5000,
        )
        self.assertEqual(self.page.text_content("#doc-state"), "Saved")
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

        text = self._read_text(out)
        # Count elements bearing data-hyp-agent
        stamped = re.findall(r'data-hyp-agent="[^"]*"', text)
        self.assertEqual(len(stamped), 3, f"Expected 3 stamped elements, got {len(stamped)}")

    # ---- E-R14-8: Stamp a non-first element with selection + markers live ----
    def test_e_r14_8_non_first_element_with_markers_live(self):
        self._select("p-arch")
        self._add_comment("fix arch", agent=True)
        threads = self._read_island()
        id0 = threads[0]["id"]

        self._select("li-2")
        self._add_comment("fix li2", agent=True)
        threads = self._read_island()
        id1 = threads[1]["id"]

        # Re-select li-2 so wrapper + markers are live body children
        self._select("li-2")
        pre = H.doc_eval(self.page, "return doc.querySelectorAll('.hyp-comment-marker, #hyp-interaction-wrapper').length;")
        self.assertGreaterEqual(pre, 2)

        out = self._save_to_temp("-r14-8.html")
        text = self._read_text(out)

        # id0 stamp sits on <p id="p-arch"> (text starts "Componentes desacoplados")
        arch_match = re.search(r'<p[^>]*id="p-arch"[^>]*data-hyp-agent="([^"]*)"', text)
        if not arch_match:
            arch_match = re.search(r'<p[^>]*data-hyp-agent="([^"]*)"[^>]*id="p-arch"', text)
        self.assertIsNotNone(arch_match, "p-arch should carry data-hyp-agent")
        self.assertIn(id0, arch_match.group(1))

        # id1 stamp sits on <li id="li-2"> (text "concilia")
        li2_match = re.search(r'<li[^>]*id="li-2"[^>]*data-hyp-agent="([^"]*)"', text)
        if not li2_match:
            li2_match = re.search(r'<li[^>]*data-hyp-agent="([^"]*)"[^>]*id="li-2"', text)
        self.assertIsNotNone(li2_match, "li-2 should carry data-hyp-agent")
        self.assertIn(id1, li2_match.group(1))

        # Live DOM clean immediately after save (before reopening)
        count_live = H.doc_eval(self.page, "return doc.querySelectorAll('[data-hyp-agent]').length;")
        self.assertEqual(count_live, 0, "Live DOM should be clean after save")

        # Reopen-resolve
        H.open_via_dialog_ui(self.page, self.base, out)
        self.page.wait_for_timeout(500)
        result = H.doc_eval(self.page, f'const m0=doc.querySelectorAll(\'[data-hyp-agent~="{id0}"]\'); const m1=doc.querySelectorAll(\'[data-hyp-agent~="{id1}"]\'); return {{n0:m0.length, t0:m0[0]?m0[0].id:null, n1:m1.length, t1:m1[0]?m1[0].id:null}};')
        self.assertEqual(result["n0"], 1)
        self.assertEqual(result["t0"], "p-arch")
        self.assertEqual(result["n1"], 1)
        self.assertEqual(result["t1"], "li-2")


if __name__ == "__main__":
    unittest.main()
