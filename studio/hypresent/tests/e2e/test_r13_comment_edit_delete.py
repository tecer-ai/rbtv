import os, sys, re, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8813


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
                iframe.contentWindow.postMessage({ source: 'hyp', kind: 'command', id, type, ...(payload||{}) }, location.origin);
                setTimeout(() => { window.removeEventListener('message', handler); reject(new Error('bridge '+type+' timed out')); }, 5000);
            });
        }
        """,
        [type_, payload or {}],
    )


class R13CommentEditDeleteTests(unittest.TestCase):
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

    def _find_thread(self, thread_id):
        for t in self._read_island():
            if t.get("id") == thread_id:
                return t
        return None

    def _row_for(self, thread_id):
        row = self.page.locator(f"#comment-threads .comment-thread[data-thread-id='{thread_id}'], #comment-threads .comment-thread[data-comment-id='{thread_id}']")
        if row.count() == 0:
            row = self.page.locator("#comment-threads .comment-thread").first
        return row

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

    def _click_row_action(self, thread_id, label):
        row = self._row_for(thread_id)
        btn = row.locator("button", has_text=re.compile(label, re.I)).first
        btn.click()
        self.page.wait_for_timeout(200)

    def _click_reply_action(self, thread_id, reply_index, label):
        row = self._row_for(thread_id)
        replies = row.locator(".comment-reply").all()
        target = replies[reply_index] if replies else row
        btn = target.locator("button", has_text=re.compile(label, re.I)).first
        btn.click()
        self.page.wait_for_timeout(200)

    # ---- E-R13-1: Edit root comment body ----
    def test_e_r13_1_edit_root_comment_body(self):
        self._select("p-lead")
        self._add_comment("original")
        threads = self._read_island()
        self.assertEqual(len(threads), 1)
        id0 = threads[0]["id"]

        self._click_row_action(id0, "Edit")
        ta = self.page.locator(".hyp-comment-composer textarea, .hyp-composer-textarea").first
        self.assertEqual(ta.input_value(), "original")
        ta.fill("edited body")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

        thread = self._find_thread(id0)
        self.assertIsNotNone(thread)
        self.assertEqual(thread["body"], "edited body")
        self.assertTrue(thread.get("editedAt"))

        panel_text = self._row_for(id0).locator(".comment-body").first.text_content()
        self.assertEqual(panel_text, "edited body")

    # ---- E-R13-2: Edit undo restores exact prior body + editedAt absence ----
    def test_e_r13_2_edit_undo_restores_prior_body(self):
        self._select("p-lead")
        self._add_comment("original")
        id0 = self._read_island()[0]["id"]

        self._click_row_action(id0, "Edit")
        ta = self.page.locator(".hyp-comment-composer textarea, .hyp-composer-textarea").first
        ta.fill("edited body")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

        bridge_command(self.page, "undo")
        self.page.wait_for_timeout(150)

        thread = self._find_thread(id0)
        self.assertEqual(thread["body"], "original")
        self.assertNotIn("editedAt", thread)

    # ---- E-R13-3: Delete root comment ----
    def test_e_r13_3_delete_root_comment(self):
        self._select("p-lead")
        self._add_comment("c0")
        self._select("p-arch")
        self._add_comment("c1")
        threads = self._read_island()
        self.assertEqual(len(threads), 2)
        id0 = threads[0]["id"]
        id1 = threads[1]["id"]
        before_markers = H.doc_eval(self.page, "return doc.querySelectorAll('.hyp-comment-marker').length;")

        self._click_row_action(id0, "Delete")
        self.page.wait_for_timeout(300)

        threads = self._read_island()
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["id"], id1)
        self.assertEqual(self.page.locator("#comment-threads .comment-thread").count(), 1)
        after_markers = H.doc_eval(self.page, "return doc.querySelectorAll('.hyp-comment-marker').length;")
        self.assertEqual(after_markers, before_markers - 1)

    # ---- E-R13-4: Delete-root undo restores thread + marker ----
    def test_e_r13_4_delete_root_undo_restores(self):
        self._select("p-lead")
        self._add_comment("c0")
        self._select("p-arch")
        self._add_comment("c1")
        threads = self._read_island()
        id0 = threads[0]["id"]
        id1 = threads[1]["id"]
        before_markers = H.doc_eval(self.page, "return doc.querySelectorAll('.hyp-comment-marker').length;")

        self._click_row_action(id0, "Delete")
        self.page.wait_for_timeout(300)

        bridge_command(self.page, "undo")
        self.page.wait_for_timeout(150)

        threads = self._read_island()
        ids = [t["id"] for t in threads]
        self.assertEqual(len(threads), 2)
        self.assertIn(id0, ids)
        self.assertIn(id1, ids)
        self.assertEqual(self.page.locator("#comment-threads .comment-thread").count(), 2)
        after_markers = H.doc_eval(self.page, "return doc.querySelectorAll('.hyp-comment-marker').length;")
        self.assertEqual(after_markers, before_markers)

    # ---- E-R13-5: Delete-reply undo restores at the ORIGINAL index ----
    def test_e_r13_5_delete_reply_undo_restores_index(self):
        self._select("p-lead")
        self._add_comment("root")
        id0 = self._read_island()[0]["id"]
        self._add_reply("r1")
        self._add_reply("r2")

        self._click_reply_action(id0, 0, "Delete")
        self.page.wait_for_timeout(300)

        thread = self._find_thread(id0)
        self.assertEqual([r["body"] for r in thread.get("replies", [])], ["r2"])

        bridge_command(self.page, "undo")
        self.page.wait_for_timeout(150)

        thread = self._find_thread(id0)
        bodies = [r["body"] for r in thread.get("replies", [])]
        self.assertEqual(bodies, ["r1", "r2"])

    # ---- E-R13-6: Edit reply body ----
    def test_e_r13_6_edit_reply_body(self):
        self._select("p-lead")
        self._add_comment("root")
        id0 = self._read_island()[0]["id"]
        self._add_reply("r1")

        self._click_reply_action(id0, 0, "Edit")
        ta = self.page.locator(".hyp-comment-composer textarea, .hyp-composer-textarea").first
        self.assertEqual(ta.input_value(), "r1")
        ta.fill("r1-edited")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

        thread = self._find_thread(id0)
        reply = thread["replies"][0]
        self.assertEqual(reply["body"], "r1-edited")
        self.assertTrue(reply.get("editedAt"))

    # ---- E-R13-7: Edit composer stays in-viewport on a low anchor; no For-agents checkbox ----
    def test_e_r13_7_edit_composer_viewport_and_no_agent_checkbox(self):
        self._select("li-2")
        self._add_comment("x")
        id0 = self._read_island()[0]["id"]

        self._click_row_action(id0, "Edit")
        composer = self.page.locator(".hyp-comment-composer").first
        self.assertTrue(composer.count() > 0)
        bottom = composer.evaluate("el => el.getBoundingClientRect().bottom")
        height = self.page.evaluate("() => window.innerHeight")
        self.assertLessEqual(bottom, height)
        cb_count = self.page.locator(".hyp-comment-composer .hyp-composer-agent, .hyp-comment-composer input[type=checkbox]").count()
        self.assertEqual(cb_count, 0)

    # ---- E-R13-8: Agent-block reflects an edited agent-tagged comment ----
    def test_e_r13_8_agent_block_reflects_edited_comment(self):
        self._select("p-lead")
        self._add_comment("do X", agent=True)
        id0 = self._read_island()[0]["id"]

        out1 = tempfile.mktemp(suffix="-r13-8a.html")
        H.set_fake_dialog(self.base, out1)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        with open(out1, encoding="utf-8") as fh:
            html1 = fh.read()
        self.assertIn("instruction: do X", html1)

        self._click_row_action(id0, "Edit")
        ta = self.page.locator(".hyp-comment-composer textarea, .hyp-composer-textarea").first
        ta.fill("do Y")
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_timeout(300)

        out2 = tempfile.mktemp(suffix="-r13-8b.html")
        H.set_fake_dialog(self.base, out2)
        self.page.click("#save-as-btn")
        self.page.wait_for_timeout(600)
        with open(out2, encoding="utf-8") as fh:
            html2 = fh.read()
        self.assertIn("instruction: do Y", html2)
        self.assertNotIn("instruction: do X", html2)


if __name__ == "__main__":
    unittest.main()
