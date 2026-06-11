"""Bug 3 deep repro: toggle For-agents via the LABEL (not the hidden input),
then SAVE -> RELOAD and inspect anchoring + the serialized output. Copies the
GSMM deck to a writable temp dir so saving is safe.

Run: python docs/plan/ui-bugfix-2026-06-11/evidence/repro_bug3_v2.py
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tests", "e2e"))
from conftest_helpers import start_server, stop_server, preset_author, set_fake_dialog, wait_runtime_ready, doc_eval  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SRC_DECK = r"C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\prospects\gsmm\presentations\2026-06-11-board\old\tecer-gsmm-board-v7.html"
PORT = 8801
OUT = os.path.join(HERE, "repro_bug3_v2_result.json")
report = {"console": [], "phases": {}}


def panel(page):
    return page.evaluate(
        """() => {
            const rows = [...document.querySelectorAll('#comment-threads .comment-thread, #comment-unanchored .comment-thread')];
            return {
              count: rows.length,
              unanchoredHeader: !!document.querySelector('.comment-unanchored-header'),
              threads: rows.map(el => ({ id: el.dataset.commentId, classes: el.className,
                  agentChecked: !!el.querySelector('.comment-agent-toggle input:checked') })),
            };
        }"""
    )


def runtime_threads(page):
    return doc_eval(page, """
        try { const j = win.hyp.comments.toJson();
          return j.map(t => ({id:t.id, agent:t.agentInstruction, replies:(t.replies||[]).length})); }
        catch(e){ return {error:String(e)}; }
    """)


def add_comment(page, hyp_id, body):
    fl = page.frame_locator("iframe.doc-frame")
    fl.locator(f'[data-hyp-id="{hyp_id}"]').first.click(timeout=5000)
    page.wait_for_timeout(150)
    page.click("#comment-btn")
    page.wait_for_selector(".hyp-comment-composer .hyp-composer-textarea", timeout=4000)
    page.fill(".hyp-comment-composer .hyp-composer-textarea", body)
    page.click(".hyp-comment-composer .hyp-composer-save")
    page.wait_for_timeout(400)


def open_deck(page, base, path):
    set_fake_dialog(base, path)
    page.click("#open-btn")
    wait_runtime_ready(page)
    page.wait_for_timeout(600)


def main():
    tmp = tempfile.mkdtemp()
    deck = os.path.join(tmp, "gsmm-repro.html")
    shutil.copy(SRC_DECK, deck)

    proc, base = start_server(PORT, test_dialog=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 900})
            page.on("console", lambda m: report["console"].append(f"{m.type}: {m.text}"[:300]))
            page.on("pageerror", lambda e: report["console"].append(f"PAGEERROR: {e}"[:500]))
            preset_author(page)
            page.goto(base + "/app/")
            open_deck(page, base, deck)

            cands = doc_eval(page, """
                const els = [...doc.querySelectorAll('[data-hyp-id]')];
                const out = [];
                for (const el of els) {
                  const txt = (el.textContent||'').replace(/\\s+/g,' ').trim();
                  if (!txt || txt.length < 3) continue;
                  out.push({ id: el.getAttribute('data-hyp-id'), tag: el.tagName.toLowerCase(),
                             svgChild: !!el.querySelector(':scope > svg'), text: txt.slice(0,32) });
                }
                const plain = out.filter(o => !o.svgChild && o.tag.match(/^(h1|h2|h3|p|div|span)$/)).slice(0,1);
                const svg = out.filter(o => o.svgChild).slice(0,1);
                return { plain, svg };
            """)
            report["candidates"] = cands
            targets = cands.get("plain", []) + cands.get("svg", [])

            # PHASE 1: add comments + toggle For-agents via the LABEL
            for i, t in enumerate(targets):
                try:
                    add_comment(page, t["id"], f"agent test {i}: {t['text']}")
                except Exception as e:
                    report.setdefault("add_errors", []).append(repr(e))
            report["phases"]["after_adds"] = {"panel": panel(page), "runtime": runtime_threads(page)}

            labels = page.locator("#comment-threads .comment-thread .comment-agent-toggle")
            tag_results = []
            for i in range(labels.count()):
                try:
                    labels.nth(i).click(timeout=4000)
                    page.wait_for_timeout(350)
                    tag_results.append({"i": i, "ok": True})
                except Exception as e:
                    tag_results.append({"i": i, "ok": False, "err": repr(e)[:200]})
            report["phases"]["tag_clicks"] = tag_results
            report["phases"]["after_tag"] = {"panel": panel(page), "runtime": runtime_threads(page)}
            page.screenshot(path=os.path.join(HERE, "v2-after-tag.png"))

            # PHASE 2: SAVE
            try:
                page.click("#save-btn")
                page.wait_for_timeout(800)
                report["phases"]["save_status"] = page.text_content("#shell-status")
            except Exception as e:
                report["phases"]["save_err"] = repr(e)

            # inspect serialized output on disk
            with open(deck, "r", encoding="utf-8") as f:
                saved = f.read()
            report["phases"]["saved_inspect"] = {
                "has_agent_block": "HYPRESENT AGENT INSTRUCTIONS" in saved,
                "data_hyp_agent_count": len(re.findall(r'data-hyp-agent', saved)),
                "comment_island_present": 'id="hyp-comments"' in saved,
                "size": len(saved),
            }

            # PHASE 3: RELOAD the saved deck in a fresh page
            page2 = browser.new_page(viewport={"width": 1500, "height": 900})
            page2.on("console", lambda m: report["console"].append(f"[reload] {m.type}: {m.text}"[:300]))
            page2.on("pageerror", lambda e: report["console"].append(f"[reload] PAGEERROR: {e}"[:500]))
            preset_author(page2)
            page2.goto(base + "/app/")
            open_deck(page2, base, deck)
            report["phases"]["after_reload"] = {"panel": panel(page2), "runtime": runtime_threads(page2)}
            page2.screenshot(path=os.path.join(HERE, "v2-after-reload.png"))

            # PHASE 4: on the reloaded deck, click a comment's marker pin (highlight) + toggle one for-agents
            try:
                fl2 = page2.frame_locator("iframe.doc-frame")
                markers = fl2.locator(".hyp-comment-marker")
                if markers.count():
                    markers.first.click(timeout=3000)
                    page2.wait_for_timeout(300)
                report["phases"]["after_marker_click"] = {"panel": panel(page2)}
                labels2 = page2.locator("#comment-threads .comment-thread .comment-agent-toggle")
                if labels2.count():
                    labels2.first.click(timeout=3000)
                    page2.wait_for_timeout(350)
                report["phases"]["after_reload_tag"] = {"panel": panel(page2), "runtime": runtime_threads(page2)}
                page2.screenshot(path=os.path.join(HERE, "v2-after-reload-tag.png"))
            except Exception as e:
                report["phases"]["reload_tag_err"] = repr(e)

            browser.close()
    finally:
        stop_server(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report["phases"], indent=2, ensure_ascii=False)[:6500])
    print("\n--- CONSOLE (errors/pageerrors) ---")
    for line in report["console"]:
        if "error" in line.lower() or "PAGEERROR" in line:
            print(line)


if __name__ == "__main__":
    main()
