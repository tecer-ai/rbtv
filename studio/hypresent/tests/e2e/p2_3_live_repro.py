"""[P2-3] Headed live-save reproduction driver (ADX-1: worker reproduces, owner AFK).

Drives the REAL builder UI (open -> restructure -> Save-As to a NEW dir) for two
scenarios and reports the on-disk asset-copy outcome at the destination:

  (a) source deck WITH its own assets/ beside it (small-deck-v3 copy in temp)
  (b) source deck with NO assets/ beside it (the e2e bare fixture in temp)

Run from the hypresent app dir:
    python tests/e2e/p2_3_live_repro.py

NEVER opens or writes the tecer-biz original — small-deck-v3 is copied OUT to temp first.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from playwright.sync_api import sync_playwright  # noqa: E402
import conftest_helpers as H  # noqa: E402

PORT = 8814
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SMALL_DECK_V3 = (
    r"C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz"
    r"\investors\_decks\pitch-deck\small-deck-v3"
)
BARE_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")
EVID = os.path.join(
    REPO, "docs", "plan", "own-asset-colocation", "phase-2", "done-gate-evidence"
)


def _copy_small_deck_to_temp():
    """Copy small-deck-v3 deck + its assets/ to a fresh temp dir; return deck path."""
    d = tempfile.mkdtemp(prefix="p2-3-deck-")
    dst_deck = os.path.join(d, "tecer-pitch-deck.html")
    shutil.copy(os.path.join(SMALL_DECK_V3, "tecer-pitch-deck.html"), dst_deck)
    shutil.copytree(
        os.path.join(SMALL_DECK_V3, "assets"), os.path.join(d, "assets")
    )
    return dst_deck


def _open_deck(page, base, deck_path):
    H.set_fake_dialog(base, deck_path)
    page.goto(base + "/app/builder.html")
    page.click("#open-deck-btn")
    page.wait_for_selector(".tray-row", timeout=10000)


def _tray_count(page):
    return page.eval_on_selector_all(".tray-row", "els=>els.length")


def _restructure(page):
    """Drop the 3rd slide and duplicate the 1st (a real restructure)."""
    page.locator(".tray-row:nth-child(3) .tray-remove").click()
    page.wait_for_timeout(150)
    page.click(".tray-row:nth-child(1) .tray-duplicate")
    page.wait_for_timeout(150)


def _save_as_new(page, base, save_path):
    H.set_fake_dialog(base, save_path)
    page.click("#save-new-btn")
    for _ in range(100):
        if os.path.exists(save_path):
            break
        page.wait_for_timeout(100)


def _dest_assets_listing(save_path):
    adir = os.path.join(os.path.dirname(save_path), "assets")
    if not os.path.isdir(adir):
        return None
    return sorted(os.listdir(adir))


def run_scenario(page, base, label, deck_path, src_has_assets):
    save_dir = tempfile.mkdtemp(prefix=f"p2-3-out-{label}-")
    save_path = os.path.join(save_dir, "saved.html")
    _open_deck(page, base, deck_path)
    n = _tray_count(page)
    _restructure(page)
    _save_as_new(page, base, save_path)
    listing = _dest_assets_listing(save_path)
    result = {
        "scenario": label,
        "deck_path": deck_path,
        "src_dir_has_assets": os.path.isdir(
            os.path.join(os.path.dirname(deck_path), "assets")
        ),
        "src_has_assets_expected": src_has_assets,
        "tray_count_on_open": n,
        "save_path": save_path,
        "saved_file_exists": os.path.exists(save_path),
        "dest_assets_dir_listing": listing,
        "dest_assets_count": len(listing) if listing else 0,
    }
    return result


def main():
    os.makedirs(EVID, exist_ok=True)
    # Clear the live-payload log so this run's captures are isolated.
    logf = pathlib.Path(EVID) / "p2-3-live-payloads.jsonl"
    if logf.exists():
        logf.unlink()

    proc, base = H.start_server(PORT, test_dialog=True)
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            try:
                deck_a = _copy_small_deck_to_temp()
                results.append(
                    run_scenario(page, base, "a-with-assets", deck_a, True)
                )

                # Scenario b: bare fixture (no assets/ beside it) in temp.
                db = tempfile.mkdtemp(prefix="p2-3-bare-")
                deck_b = os.path.join(db, "deck.html")
                shutil.copy(BARE_FIXTURE, deck_b)
                results.append(
                    run_scenario(page, base, "b-no-assets", deck_b, False)
                )
            finally:
                browser.close()
    finally:
        H.stop_server(proc)

    out = pathlib.Path(EVID) / "p2-3-repro-results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nResults: {out}")
    print(f"Payload log: {logf}")


if __name__ == "__main__":
    main()
