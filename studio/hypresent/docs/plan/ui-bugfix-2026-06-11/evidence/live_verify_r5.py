"""Live verification of R5: the top-left Editor/Builder pill toggle now opens the
save-confirm modal (instead of discarding work). Tests both pills."""
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
PORT = 8812
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def main():
    tmp = tempfile.mkdtemp()
    deck = os.path.join(tmp, "gsmm.html")
    shutil.copy(SRC_DECK, deck)
    proc, base = start_server(PORT, test_dialog=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()

            # --- Editor "Builder" pill (#nav-builder) ---
            page = browser.new_page(viewport={"width": 1400, "height": 880})
            preset_author(page)
            page.goto(base + "/app/")
            set_fake_dialog(base, deck)
            page.click("#open-btn")
            wait_runtime_ready(page)
            page.wait_for_timeout(500)
            page.wait_for_selector("#open-in-builder-btn:not([disabled])", timeout=8000)
            page.click("#nav-builder")                       # the pill, NOT the button
            page.wait_for_selector(".hyp-modal-scrim", timeout=5000)
            check("R5 editor pill: clicking the Builder pill opens the save-confirm modal", True, "")
            page.locator(".hyp-modal-scrim button", has_text="Overwrite").click()
            page.wait_for_url("**/builder.html?file=*", timeout=8000)
            check("R5 editor pill: Overwrite saves + switches to the Builder", "builder.html?file=" in page.url, "")
            page.close()

            # --- Builder "Editor" pill (#nav-editor) ---
            page = browser.new_page(viewport={"width": 1400, "height": 880})
            set_fake_dialog(base, deck)
            page.goto(base + "/app/builder.html")
            page.click("#open-deck-btn")
            page.wait_for_selector(".tray-row", timeout=10000)
            page.wait_for_timeout(300)
            page.click("#nav-editor")                        # the pill, NOT the button
            page.wait_for_selector(".hyp-modal-scrim", timeout=5000)
            check("R5 builder pill: clicking the Editor pill opens the save-confirm modal", True, "")
            page.locator(".hyp-modal-scrim button", has_text="Overwrite").click()
            page.wait_for_url("**/app/?file=*", timeout=8000)
            check("R5 builder pill: Overwrite saves + switches to the Editor", "/app/?file=" in page.url, "")
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
