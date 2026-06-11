"""Live verification of bug-7: adding a blank slide then overwriting must NOT
delete a real slide. Drives the builder through the exact data-loss sequence
(remove -> add blank -> overwrite -> add blank -> overwrite) and proves every
non-removed original section survives in the final saved file.
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
sys.path.insert(0, os.path.join(REPO, "server"))
from conftest_helpers import start_server, stop_server, set_fake_dialog  # noqa: E402
from recompose import split_sections  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")
PORT = 8808
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def section_texts(html):
    spans = split_sections(html)
    out = []
    for s, e in spans:
        raw = html[s:e]
        txt = re.sub(r"<[^>]+>", " ", raw)
        txt = re.sub(r"\s+", " ", txt).strip()
        out.append(txt)
    return out


def main():
    d = tempfile.mkdtemp()
    deck = os.path.join(d, "deck.html")
    shutil.copy(DECK_FIXTURE, deck)
    orig_html = open(deck, encoding="utf-8").read()
    orig_secs = section_texts(orig_html)  # 10 sections, in tray order

    proc, base = start_server(PORT, test_dialog=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            set_fake_dialog(base, deck)
            page.goto(base + "/app/builder.html")
            page.click("#open-deck-btn")
            page.wait_for_selector(".tray-row", timeout=10000)
            n0 = page.eval_on_selector_all(".tray-row", "els=>els.length")
            check("builder: deck opened with rows", n0 >= 5, f"rows={n0}")

            # Remove row 2 (original section index 1)
            removed_idx = 1
            page.locator(".tray-row:nth-child(2) .tray-remove").click()
            page.wait_for_timeout(150)
            # Add blank, overwrite
            page.click("#add-blank-btn"); page.wait_for_timeout(120)
            page.click("#save-overwrite-btn")
            page.wait_for_selector(".shell-status.success", timeout=10000)
            page.wait_for_timeout(300)
            # Add another blank, overwrite again (this is where the stale index struck)
            page.click("#add-blank-btn"); page.wait_for_timeout(120)
            page.click("#save-overwrite-btn")
            page.wait_for_selector(".shell-status.success", timeout=10000)
            page.wait_for_timeout(400)
            browser.close()
    finally:
        stop_server(proc)

    saved_html = open(deck, encoding="utf-8").read()
    saved_secs = section_texts(saved_html)
    expected = [t for i, t in enumerate(orig_secs) if i != removed_idx]  # 9 originals kept

    # Each surviving original's distinctive middle chunk must appear in the saved file.
    saved_join = " ".join(saved_secs)
    missing = []
    for t in expected:
        if len(t) < 25:
            continue
        chunk = t[15:75] if len(t) >= 75 else t[10:]
        if chunk not in saved_join:
            missing.append(t[:50])
    removed_text = orig_secs[removed_idx]
    removed_chunk = removed_text[15:75] if len(removed_text) >= 75 else removed_text[10:]

    check("bug7: saved deck has expected section count (orig-1 + 2 blanks)",
          len(saved_secs) == (len(orig_secs) - 1 + 2),
          f"saved={len(saved_secs)} expected={len(orig_secs) - 1 + 2}")
    check("bug7: every non-removed original slide survives (none deleted by overwrite)",
          len(missing) == 0, f"missing={missing}")
    check("bug7: the intentionally-removed slide is absent",
          (len(removed_chunk) < 10) or (removed_chunk not in " ".join(saved_secs)),
          f"removed_chunk_present={removed_chunk in ' '.join(saved_secs)}")

    allok = all(r["pass"] for r in results)
    print(json.dumps({"all_pass": allok, "results": results}, indent=2, ensure_ascii=False))
    with open(os.path.join(HERE, "live_verify_bug7_result.json"), "w", encoding="utf-8") as f:
        json.dump({"all_pass": allok, "results": results}, f, indent=2, ensure_ascii=False)
    shutil.rmtree(d, ignore_errors=True)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
