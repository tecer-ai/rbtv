"""Live verification of the R2 owner refinements:
  bug-5  reply is an INLINE input in the comment card (not a floating popover); Enter sends
  bug-4  after save the status bar is empty (no lingering 'Saved' contradicting the chip)
  bug-6  Editor->Builder switch saves to the existing file SILENTLY (no dialog) and navigates
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tests", "e2e"))
from conftest_helpers import start_server, stop_server, preset_author, set_fake_dialog, wait_runtime_ready, doc_eval  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SRC_DECK = r"C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\prospects\gsmm\presentations\2026-06-11-board\old\tecer-gsmm-board-v7.html"
PORT = 8809
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def add_comment(page, hyp_id, body):
    fl = page.frame_locator("iframe.doc-frame")
    fl.locator(f'[data-hyp-id="{hyp_id}"]').first.click(timeout=5000)
    page.wait_for_timeout(150)
    page.click("#comment-btn")
    page.wait_for_selector(".hyp-comment-composer .hyp-composer-textarea", timeout=4000)
    page.fill(".hyp-comment-composer .hyp-composer-textarea", body)
    page.keyboard.press("Control+Enter")
    page.wait_for_timeout(400)


def main():
    tmp = tempfile.mkdtemp()
    deck = os.path.join(tmp, "gsmm.html")
    shutil.copy(SRC_DECK, deck)
    proc, base = start_server(PORT, test_dialog=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1500, "height": 900})
            preset_author(page)
            page.goto(base + "/app/")
            set_fake_dialog(base, deck)
            page.click("#open-btn")
            wait_runtime_ready(page)
            page.wait_for_timeout(600)

            ids = doc_eval(page, "return [...doc.querySelectorAll('[data-hyp-id]')].filter(el=>(el.textContent||'').trim().length>3).slice(0,5).map(el=>el.getAttribute('data-hyp-id'));")
            add_comment(page, ids[0], "parent comment")

            # ---- bug-5: inline reply input present in the card, NOT a floating popover ----
            inline = page.locator("#comment-threads .comment-thread .comment-reply-input")
            floating = page.locator(".hyp-comment-composer")
            check("bug5: inline reply input exists in the comment card", inline.count() >= 1, f"count={inline.count()}")
            check("bug5: no floating reply popover open", floating.count() == 0, f"popovers={floating.count()}")
            if inline.count():
                inline.first.click()
                inline.first.fill("my inline reply")
                inline.first.press("Enter")
                page.wait_for_timeout(500)
                rep = doc_eval(page, "try{const j=win.hyp.comments.toJson(); return j[0]?(j[0].replies||[]).length:0;}catch(e){return -1;}")
                check("bug5: Enter in the inline input sends the reply", rep == 1, f"replies={rep}")
                shown = page.locator("#comment-threads .comment-thread .comment-reply").count()
                check("bug5: the reply renders in the panel", shown >= 1, f"reply_cards={shown}")

            # ---- bug-4: status bar empty after save (chip is the only indicator) ----
            set_fake_dialog(base, os.path.join(tmp, "saved.html"))
            page.click("#save-as-btn")
            page.wait_for_timeout(700)
            st = page.evaluate("() => { const s=document.getElementById('shell-status'); const d=document.getElementById('doc-state'); return { status: s?s.textContent:null, state: d?d.textContent:null }; }")
            check("bug4: status bar no longer prints a lingering 'Saved'", (st["status"] or "") == "", f"status='{st['status']}'")
            check("bug4: chip state shows Saved", st["state"] == "Saved", f"state={st['state']}")

            # ---- bug-6: Editor->Builder switch is silent (no dialog) + navigates to builder ----
            # Point the fake dialog at a sentinel path; if the silent save path is taken it is NOT used.
            sentinel = os.path.join(tmp, "SHOULD_NOT_BE_USED.html")
            set_fake_dialog(base, sentinel)
            page.wait_for_selector("#open-in-builder-btn:not([disabled])", timeout=8000)
            page.click("#open-in-builder-btn")
            page.wait_for_url("**/builder.html?file=*", timeout=8000)
            url_ok = "builder.html?file=" in page.url
            sentinel_used = os.path.exists(sentinel)
            check("bug6: switch navigated to the Builder (silent save, no dialog needed)", url_ok and not sentinel_used, f"url={page.url[-60:]} sentinel_used={sentinel_used}")

            browser.close()
    finally:
        stop_server(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    allok = all(r["pass"] for r in results)
    print(json.dumps({"all_pass": allok, "results": results}, indent=2, ensure_ascii=False))
    with open(os.path.join(HERE, "live_verify_r2_result.json"), "w", encoding="utf-8") as f:
        json.dump({"all_pass": allok, "results": results}, f, indent=2, ensure_ascii=False)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
