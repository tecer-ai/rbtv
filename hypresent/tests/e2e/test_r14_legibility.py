import os, sys, re, json, tempfile, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unittest
from playwright.sync_api import sync_playwright
import conftest_helpers as H

PORT = 8815


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


class TestR14Legibility(unittest.TestCase):
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

    # ---- G-R14-LEGIBILITY-1: Every target resolvable via the head block alone ----
    def test_g_r14_legibility_1_targets_resolvable_via_head_block(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        self._select("li-2")
        self._add_comment("renumber item", agent=True)

        out = self._save_to_temp("-r14-leg1.html")
        text = self._read_text(out)
        block = self._extract_head_block(text)

        # Extract every [agent:<id>] entry's target: selector and instruction: line
        entries = []
        for m in re.finditer(r'\[agent:([^\]]+)\](.*?)(?=\[agent:|===== HYPRESENT AGENT INSTRUCTIONS =====|$)', block, re.S):
            entry_text = m.group(2)
            target_m = re.search(r'target:\s*(.+)', entry_text)
            instr_m = re.search(r'instruction:\s*(.+)', entry_text)
            entries.append({
                "id": m.group(1).strip(),
                "target": target_m.group(1).strip() if target_m else None,
                "instruction": instr_m.group(1).strip() if instr_m else None,
            })

        # Criterion 1: exactly 2 [agent: markers
        self.assertEqual(len(entries), 2, f"Expected 2 agent entries, got {len(entries)}")

        # Resolve phase: fresh context-free page via file:// (standalone fresh-agent modality)
        fresh = self.browser.new_page()
        try:
            fresh.goto("file://" + os.path.abspath(out), wait_until="networkidle", timeout=10000)
            # Verify the page actually loaded
            body_exists = fresh.evaluate("() => !!document.querySelector('body')")
            self.assertTrue(body_exists, "Fresh page should have loaded the saved file")

            # Criterion 2 & 3: each target selector resolves to exactly one correct element
            for entry in entries:
                self.assertIsNotNone(entry["target"], f"Missing target for {entry['id']}")
                result = fresh.evaluate(
                    """(sel) => {
                        const m = document.querySelectorAll(sel);
                        return m.length === 1 ? {ok: true, html: m[0].outerHTML.slice(0,120), text: m[0].textContent.slice(0,40)} : {ok: false, n: m.length};
                    }""",
                    entry["target"],
                )
                self.assertTrue(result.get("ok"), f"Selector '{entry['target']}' did not resolve to exactly one element (got n={result.get('n')})")
                # Verify the resolved element matches the intended anchor
                if "lead" in (entry["instruction"] or "").lower():
                    self.assertIn("p-lead", result["html"])
                    self.assertIn("Plataforma inteligente", result["text"])
                elif "renumber" in (entry["instruction"] or "").lower() or "item" in (entry["instruction"] or "").lower():
                    self.assertIn("li-2", result["html"])
                    self.assertIn("concilia", result["text"])

            # Criterion 4: Position-independence
            fresh.evaluate("""() => {
                const sec = document.querySelector('#sec-ops');
                if (sec) sec.insertAdjacentHTML('afterbegin', '<p>injected</p>');
            }""")
            for entry in entries:
                result = fresh.evaluate(
                    """(sel) => {
                        const m = document.querySelectorAll(sel);
                        return m.length === 1 ? {ok: true, html: m[0].outerHTML.slice(0,120), text: m[0].textContent.slice(0,40)} : {ok: false, n: m.length};
                    }""",
                    entry["target"],
                )
                self.assertTrue(result.get("ok"), f"After injection, selector '{entry['target']}' did not resolve to exactly one element (got n={result.get('n')})")
                if "lead" in (entry["instruction"] or "").lower():
                    self.assertIn("p-lead", result["html"])
                    self.assertIn("Plataforma inteligente", result["text"])
                elif "renumber" in (entry["instruction"] or "").lower() or "item" in (entry["instruction"] or "").lower():
                    self.assertIn("li-2", result["html"])
                    self.assertIn("concilia", result["text"])
        finally:
            fresh.close()

    # ---- G-R14-LEGIBILITY-2: Self-cleanup directive present and actionable ----
    def test_g_r14_legibility_2_self_cleanup_directive(self):
        self._select("p-lead")
        self._add_comment("fix lead", agent=True)
        self._select("li-2")
        self._add_comment("renumber item", agent=True)

        out = self._save_to_temp("-r14-leg2.html")
        text = self._read_text(out)
        block = self._extract_head_block(text)

        # Self-cleanup directive present
        self.assertIn("remove the data-hyp-agent", block)

        # Extract targets and ids
        entries = []
        for m in re.finditer(r'\[agent:([^\]]+)\](.*?)(?=\[agent:|===== HYPRESENT AGENT INSTRUCTIONS =====|$)', block, re.S):
            entry_text = m.group(2)
            target_m = re.search(r'target:\s*(.+)', entry_text)
            entries.append({
                "id": m.group(1).strip(),
                "target": target_m.group(1).strip() if target_m else None,
            })

        self.assertEqual(len(entries), 2)

        # Verify cleanup is per-id and non-destructive to siblings
        fresh = self.browser.new_page()
        try:
            fresh.goto("file://" + os.path.abspath(out), wait_until="networkidle", timeout=10000)

            id0 = entries[0]["id"]
            id1 = entries[1]["id"]
            sel0 = entries[0]["target"]
            sel1 = entries[1]["target"]

            # Both resolve before cleanup
            r0 = fresh.evaluate("""(sel) => document.querySelectorAll(sel).length;""", sel0)
            r1 = fresh.evaluate("""(sel) => document.querySelectorAll(sel).length;""", sel1)
            self.assertEqual(r0, 1)
            self.assertEqual(r1, 1)

            # Remove id0's data-hyp-agent token
            fresh.evaluate(
                r"""([sel, id]) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    const val = el.getAttribute('data-hyp-agent');
                    if (!val) return false;
                    const parts = val.split(/\s+/).filter(s => s !== id);
                    if (parts.length === 0) el.removeAttribute('data-hyp-agent');
                    else el.setAttribute('data-hyp-agent', parts.join(' '));
                    return true;
                }""",
                [sel0, id0],
            )

            # id0 no longer resolves (selector uses ~= or =)
            post0 = fresh.evaluate("""(sel) => document.querySelectorAll(sel).length;""", sel0)
            self.assertEqual(post0, 0)

            # id1 still resolves
            post1 = fresh.evaluate("""(sel) => document.querySelectorAll(sel).length;""", sel1)
            self.assertEqual(post1, 1)
        finally:
            fresh.close()


if __name__ == "__main__":
    unittest.main()
