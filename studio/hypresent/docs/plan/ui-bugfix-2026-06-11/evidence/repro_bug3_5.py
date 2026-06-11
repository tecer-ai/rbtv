"""Live reproduction for bug 3 (mark-for-agent breaks UI / red comment) and
bug 5 (reply not working), on the real GSMM v7 deck. Static analysis could not
prove the mechanism; this drives the real app and captures the truth.

Run:  python docs/plan/ui-bugfix-2026-06-11/evidence/repro_bug3_5.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tests", "e2e"))
from conftest_helpers import start_server, stop_server, preset_author, set_fake_dialog, wait_runtime_ready, doc_eval  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

DECK = r"C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\prospects\gsmm\presentations\2026-06-11-board\old\tecer-gsmm-board-v7.html"
PORT = 8799
OUT = os.path.join(HERE, "repro_bug3_5_result.json")
SHOTS = HERE

report = {"console": [], "steps": []}


def panel_state(page):
    """Read the comment panel's rendered threads from the PARENT document."""
    return page.evaluate(
        """() => {
            const rows = [...document.querySelectorAll('#comment-threads .comment-thread, #comment-unanchored .comment-thread')];
            return {
              threadCount: rows.length,
              threads: rows.map(el => ({
                id: el.dataset.commentId,
                classes: el.className,
                hasReplies: !!el.querySelector('.comment-reply'),
                agentChecked: !!el.querySelector('.comment-agent-toggle input:checked'),
              })),
              unanchoredHeader: !!document.querySelector('.comment-unanchored-header'),
            };
        }"""
    )


def thread_data(page):
    """Read the runtime's own view of threads (unanchored flag, marker text)."""
    return doc_eval(page, """
        const out = [];
        const markers = [...doc.querySelectorAll('.hyp-comment-marker')].map(m => m.textContent);
        try {
          const j = win.hyp && win.hyp.comments ? win.hyp.comments.toJson() : [];
          return { island: j.map(t => ({id:t.id, agent:t.agentInstruction, replies:(t.replies||[]).length})), markers };
        } catch(e) { return { error: String(e), markers }; }
    """)


def add_comment_on(page, hyp_id, body):
    """Select an element by hyp-id (click in iframe), open composer, save."""
    fl = page.frame_locator("iframe.doc-frame")
    fl.locator(f'[data-hyp-id="{hyp_id}"]').first.click(timeout=5000)
    page.wait_for_timeout(150)
    page.click("#comment-btn")
    page.wait_for_selector(".hyp-comment-composer .hyp-composer-textarea", timeout=4000)
    page.fill(".hyp-comment-composer .hyp-composer-textarea", body)
    page.click(".hyp-comment-composer .hyp-composer-save")
    page.wait_for_timeout(400)


def main():
    proc, base = start_server(PORT, test_dialog=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 900})
            page.on("console", lambda m: report["console"].append(f"{m.type}: {m.text}"[:300]))
            page.on("pageerror", lambda e: report["console"].append(f"PAGEERROR: {e}"[:400]))
            preset_author(page)
            page.goto(base + "/app/")
            set_fake_dialog(base, DECK)
            page.click("#open-btn")
            wait_runtime_ready(page)
            page.wait_for_timeout(600)

            # Enumerate candidate comment targets: a plain title vs an inline-svg lead row.
            cands = doc_eval(page, """
                const els = [...doc.querySelectorAll('[data-hyp-id]')];
                const pick = [];
                for (const el of els) {
                  const txt = (el.textContent||'').replace(/\\s+/g,' ').trim().slice(0,40);
                  if (!txt) continue;
                  const svg = !!el.querySelector(':scope > svg');
                  pick.push({ id: el.getAttribute('data-hyp-id'), tag: el.tagName.toLowerCase(), svgChild: svg, text: txt });
                }
                const titles = pick.filter(p => !p.svgChild).slice(0, 2);
                const svgs = pick.filter(p => p.svgChild).slice(0, 2);
                return { total: pick.length, titles, svgs };
            """)
            report["candidates"] = cands

            targets = (cands.get("titles", [])[:1] + cands.get("svgs", [])[:1]) or cands.get("titles", [])[:2]

            for i, t in enumerate(targets):
                step = {"target": t}
                try:
                    add_comment_on(page, t["id"], f"repro comment {i} on {t['text']}")
                    step["after_add_panel"] = panel_state(page)
                    step["after_add_runtime"] = thread_data(page)
                    # Toggle "For agents" on the LAST thread in the panel.
                    toggles = page.locator("#comment-threads .comment-thread .comment-agent-toggle input")
                    n = toggles.count()
                    if n:
                        toggles.nth(n - 1).click()
                        page.wait_for_timeout(400)
                        step["after_tagagent_panel"] = panel_state(page)
                        step["after_tagagent_runtime"] = thread_data(page)
                    page.screenshot(path=os.path.join(SHOTS, f"repro-step{i}-{'svg' if t['svgChild'] else 'plain'}.png"))
                except Exception as e:
                    step["error"] = repr(e)
                report["steps"].append(step)

            # ---- Bug 5: reply behavior (plain Enter vs Ctrl+Enter) ----
            reply = {}
            try:
                first = page.locator("#comment-threads .comment-thread").first
                if first.count():
                    first.locator(".comment-action-btn", has_text="Reply").click()
                    page.wait_for_selector(".hyp-comment-composer .hyp-composer-textarea", timeout=4000)
                    page.fill(".hyp-comment-composer .hyp-composer-textarea", "first reply line")
                    page.locator(".hyp-comment-composer .hyp-composer-textarea").press("Enter")
                    page.wait_for_timeout(300)
                    reply["composer_open_after_plain_enter"] = page.locator(".hyp-comment-composer").count() > 0
                    reply["textarea_value_after_enter"] = (
                        page.locator(".hyp-comment-composer .hyp-composer-textarea").input_value()
                        if reply["composer_open_after_plain_enter"] else None
                    )
                    # Now submit properly
                    if reply["composer_open_after_plain_enter"]:
                        page.locator(".hyp-comment-composer .hyp-composer-textarea").press("Control+Enter")
                        page.wait_for_timeout(400)
                    reply["panel_after_submit"] = panel_state(page)
                    reply["runtime_after_submit"] = thread_data(page)
            except Exception as e:
                reply["error"] = repr(e)
            report["reply"] = reply

            browser.close()
    finally:
        stop_server(proc)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: report[k] for k in ("candidates", "steps", "reply")}, indent=2, ensure_ascii=False)[:6000])
    print("\n--- CONSOLE (last 25) ---")
    for line in report["console"][-25:]:
        print(line)


if __name__ == "__main__":
    main()
