"""Live verification of R3: the overwrite-confirm modal on Editor->Builder switch.
Tests the three outcomes: Overwrite & continue, Esc-cancel (stay), Save As (new path)."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tests", "e2e"))
from conftest_helpers import start_server, stop_server, preset_author, set_fake_dialog, wait_runtime_ready  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

SRC_DECK = r"C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\prospects\gsmm\presentations\2026-06-11-board\old\tecer-gsmm-board-v7.html"
PORT = 8810
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def main():
    tmp = tempfile.mkdtemp()
    deck = os.path.join(tmp, "gsmm.html")
    shutil.copy(SRC_DECK, deck)
    proc, base = start_server(PORT, test_dialog=True)

    def open_editor(browser):
        page = browser.new_page(viewport={"width": 1400, "height": 880})
        preset_author(page)
        page.goto(base + "/app/")
        set_fake_dialog(base, deck)
        page.click("#open-btn")
        wait_runtime_ready(page)
        page.wait_for_timeout(500)
        page.wait_for_selector("#open-in-builder-btn:not([disabled])", timeout=8000)
        return page

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()

            # Scenario A — Overwrite & continue
            page = open_editor(browser)
            page.click("#open-in-builder-btn")
            page.wait_for_selector(".hyp-modal-scrim", timeout=5000)
            has_buttons = (page.locator(".hyp-modal-scrim button", has_text="Overwrite").count() >= 1
                           and page.locator(".hyp-modal-scrim button", has_text="Save As").count() >= 1)
            check("R3: confirm modal appears on switch with both buttons", has_buttons, "")
            page.locator(".hyp-modal-scrim button", has_text="Overwrite").click()
            page.wait_for_url("**/builder.html?file=*", timeout=8000)
            check("R3 proceed: overwrites the opened file + navigates to Builder",
                  "builder.html?file=" in page.url and "gsmm.html" in page.url, f"url=…{page.url[-40:]}")
            page.close()

            # Scenario B — Esc cancels, stays in editor
            page = open_editor(browser)
            page.click("#open-in-builder-btn")
            page.wait_for_selector(".hyp-modal-scrim", timeout=5000)
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            stayed = (page.locator(".hyp-modal-scrim").count() == 0
                      and "builder.html" not in page.url and page.url.rstrip("/").endswith("/app"))
            check("R3 cancel: Esc closes the modal and stays in the editor", stayed, f"url=…{page.url[-30:]}")
            page.close()

            # Scenario C — Save As to a NEW path
            page = open_editor(browser)
            page.click("#open-in-builder-btn")
            page.wait_for_selector(".hyp-modal-scrim", timeout=5000)
            newpath = os.path.join(tmp, "saved-as-new.html")
            set_fake_dialog(base, newpath)
            page.locator(".hyp-modal-scrim button", has_text="Save As").click()
            page.wait_for_url("**/builder.html?file=*", timeout=8000)
            check("R3 saveas: navigates to the Builder with the NEW path (original kept)",
                  "saved-as-new.html" in page.url, f"url=…{page.url[-40:]}")
            orig_intact = os.path.exists(deck)
            check("R3 saveas: the originally-opened file still exists", orig_intact, "")
            page.close()

            browser.close()
    finally:
        stop_server(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    allok = all(r["pass"] for r in results)
    print(json.dumps({"all_pass": allok, "results": results}, indent=2, ensure_ascii=False))
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
