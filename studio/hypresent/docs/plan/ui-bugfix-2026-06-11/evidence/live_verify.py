"""Live verification of the behavior-change fixes not covered by existing e2e:
  bug-8  inline-<svg> text elements become editable on double-click
  bug-2  comment markers + panel show distinct sequential numbers (document order)
  bug-4  after Save As the doc chip shows the basename (not the full path) + path tooltip
Runs on the real GSMM v7 deck. Exit 0 + all PASS = verified.
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
PORT = 8806
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

            # ---- bug-8: inline-svg text element becomes editable ----
            cands = doc_eval(page, """
                const els = [...doc.querySelectorAll('[data-hyp-id]')];
                let svgEl = null, plainEl = null;
                for (const el of els) {
                  const txt = (el.textContent||'').replace(/\\s+/g,' ').trim();
                  if (!txt || txt.length < 3) continue;
                  if (!svgEl && el.querySelector(':scope > svg')) svgEl = el.getAttribute('data-hyp-id');
                  if (!plainEl && !el.querySelector(':scope > svg') && el.tagName.match(/^(H1|H2|H3|P|DIV)$/)) plainEl = el.getAttribute('data-hyp-id');
                }
                return { svgEl, plainEl };
            """)
            fl = page.frame_locator("iframe.doc-frame")
            if cands.get("svgEl"):
                fl.locator(f'[data-hyp-id="{cands["svgEl"]}"]').first.dblclick(timeout=5000)
                page.wait_for_timeout(250)
                ce = doc_eval(page, f"""const el = doc.querySelector('[data-hyp-id="{cands['svgEl']}"]'); return el ? el.getAttribute('contenteditable') : null;""")
                check("bug8: inline-svg element enters edit mode on dblclick", ce == "true", f"contenteditable={ce} on {cands['svgEl']}")
                # exit edit
                page.keyboard.press("Escape"); page.wait_for_timeout(150)
            else:
                check("bug8: found an inline-svg element", False, "no svg-child element on this deck")

            # ---- bug-2: distinct sequential numbers, document order ----
            ids = doc_eval(page, """
                const els = [...doc.querySelectorAll('[data-hyp-id]')].filter(el => (el.textContent||'').trim().length>3);
                return els.slice(0, 30).map(el => el.getAttribute('data-hyp-id'));
            """)
            # comment on three elements spread through the doc
            picks = [ids[0], ids[len(ids)//2], ids[-1]] if len(ids) >= 3 else ids
            for i, hid in enumerate(picks):
                add_comment(page, hid, f"verify numbering {i}")
            markers = doc_eval(page, "return [...doc.querySelectorAll('.hyp-comment-marker')].map(m => m.textContent);")
            panelNums = page.evaluate("() => [...document.querySelectorAll('#comment-threads .comment-number')].map(e => e.textContent)")
            uniq = sorted(set(markers))
            check("bug2: markers show distinct numbers (not all '1')", len(set(markers)) == len(markers) and "1" in markers, f"markers={markers}")
            check("bug2: numbers are contiguous 1..N", uniq == [str(i + 1) for i in range(len(markers))], f"sorted={uniq}")
            check("bug2: panel shows #N badges for each thread", len(panelNums) == len(picks), f"panel={panelNums}")

            # ---- bug-4: Save As -> chip basename + title tooltip, status 'Saved' (no path) ----
            out = os.path.join(tmp, "saved-deck.html")
            set_fake_dialog(base, out)
            page.click("#save-as-btn")
            page.wait_for_timeout(700)
            chip = page.evaluate("""() => {
                const n = document.getElementById('doc-name');
                const c = document.getElementById('doc-chip');
                const s = document.getElementById('shell-status');
                return { name: n ? n.textContent : null, title: c ? c.getAttribute('title') : null, status: s ? s.textContent : null };
            }""")
            check("bug4: doc chip shows basename only (no separators)", chip["name"] == "saved-deck.html", f"name={chip['name']}")
            check("bug4: full path on hover (title attr)", bool(chip["title"]) and chip["title"].endswith("saved-deck.html") and ("\\" in chip["title"] or "/" in chip["title"]), f"title={chip['title']}")
            check("bug4: status no longer prints the full path", chip["status"] == "Saved", f"status={chip['status']}")

            browser.close()
    finally:
        stop_server(proc)
        shutil.rmtree(tmp, ignore_errors=True)

    allok = all(r["pass"] for r in results)
    print(json.dumps({"all_pass": allok, "results": results}, indent=2, ensure_ascii=False))
    with open(os.path.join(HERE, "live_verify_result.json"), "w", encoding="utf-8") as f:
        json.dump({"all_pass": allok, "results": results}, f, indent=2, ensure_ascii=False)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
