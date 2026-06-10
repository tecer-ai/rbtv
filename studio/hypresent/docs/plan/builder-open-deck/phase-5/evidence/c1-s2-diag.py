"""
Diagnostic: capture actual builder save-new payload and inspect saved file
to understand why headed run produces [1,1,1,...] vs headless [1,1,0,...].
"""
import subprocess, sys, time, os, urllib.request, json, tempfile, shutil, hashlib
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", ".."))
# Adjust: c1-s2-diag.py is at hypresent/docs/plan/builder-open-deck/phase-5/evidence/
# So REPO = hypresent = 6 levels up from __file__? Let's count:
# evidence/ -> phase-5/ -> builder-open-deck/ -> plan/ -> docs/ -> hypresent/
# That's 5 levels up
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))

env = dict(os.environ)
env["HYP_TEST_DIALOG"] = "1"
proc = subprocess.Popen(
    [sys.executable, "server/server.py", "127.0.0.1", "9994"],
    cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
base = "http://127.0.0.1:9994"
deadline = time.time() + 10
while time.time() < deadline:
    try:
        with urllib.request.urlopen(base + "/app/", timeout=1):
            break
    except Exception:
        time.sleep(0.15)

tmp = tempfile.mkdtemp()
deck = os.path.join(tmp, "deck.html")
save_path = os.path.join(tmp, "saved.html")
shutil.copy(os.path.join(REPO, "tecer-gsmm-introduction.html"), deck)


def post(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=5):
        pass


post(base + "/api/_test/set-dialog", {"path": deck})

CAPTURED = {}


def dom_rows(page):
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r,i)=>({
            i, uid:r.dataset.uid, slideId:r.dataset.slideId,
        }))
    """
    )


def split_top_sections(html):
    spans = []
    depth = 0
    in_comment = False
    i = 0
    n = len(html)
    cur = None
    while i < n:
        if not in_comment:
            if html.startswith("<!--", i):
                in_comment = True
                i += 4
                continue
        else:
            if html.startswith("-->", i):
                in_comment = False
                i += 3
                continue
            i += 1
            continue
        if html.startswith("<section", i):
            after = i + 8
            if after < n and html[after] in " \t\n>":
                if depth == 0:
                    cur = i
                depth += 1
                i += 8
                continue
        if html.startswith("</section>", i):
            depth -= 1
            if depth == 0 and cur is not None:
                spans.append((cur, i + 10))
                cur = None
            i += 10
            continue
        i += 1
    return spans


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=120)
    context = browser.new_context(viewport={"width": 1400, "height": 900})
    page = context.new_page()

    save_count = [0]

    def route_handler(route):
        req = route.request
        if req.method == "POST" and "/api/deck-save" in req.url:
            try:
                body = req.post_data_json
            except Exception:
                body = req.post_data
            save_count[0] += 1
            CAPTURED[f"save_{save_count[0]}"] = body
            items = body.get("items") if isinstance(body, dict) else body
            print(f"[SAVE #{save_count[0]}] items: {json.dumps(items)[:200]}", flush=True)
        route.continue_()

    page.route("**/api/deck-save", route_handler)

    page.goto(base + "/app/builder.html")
    page.wait_for_load_state("networkidle")
    page.click("#open-deck-btn")
    page.wait_for_function(
        "() => document.querySelectorAll('#tray-list .tray-row').length > 0"
    )
    page.wait_for_timeout(800)

    rows = dom_rows(page)
    print("After open:", [(r["slideId"], r["uid"]) for r in rows], flush=True)

    uid_sec1 = next(r["uid"] for r in rows if r["slideId"] == "deck-section-1")
    uid_sec0 = next(r["uid"] for r in rows if r["slideId"] == "deck-section-0")

    # Reorder
    row1 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec1}']")
    row0 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec0}']")
    grip1 = row1.query_selector(".grip")
    g_bb = grip1.bounding_box()
    r0_bb = row0.bounding_box()
    sx = g_bb["x"] + g_bb["width"] / 2
    sy = g_bb["y"] + g_bb["height"] / 2
    tx = r0_bb["x"] + r0_bb["width"] / 2
    ty = r0_bb["y"] - 5
    page.mouse.move(sx, sy)
    page.mouse.down()
    time.sleep(0.2)
    for k in range(16):
        page.mouse.move(sx + (tx - sx) * k / 15, sy + (ty - sy) * k / 15)
        time.sleep(0.02)
    time.sleep(0.2)
    page.mouse.up()
    page.wait_for_timeout(600)

    try:
        page.wait_for_function(
            f"() => {{ const r=document.querySelectorAll('#tray-list .tray-row');"
            f" return r.length>1&&r[0].dataset.uid==='{uid_sec1}'; }}",
            timeout=3000,
        )
        print("Reorder: TOOK", flush=True)
    except Exception:
        print("Reorder: FAILED", flush=True)

    rows_r = dom_rows(page)
    print("After reorder:", [(r["slideId"], r["uid"]) for r in rows_r], flush=True)

    # Remove deck-section-2 by identity
    rm_btn = page.query_selector(
        "#tray-list .tray-row[data-slide-id='deck-section-2'] .tray-remove"
    )
    rm_btn.click()
    page.wait_for_timeout(500)
    rows_rm = dom_rows(page)
    print("After remove:", [(r["slideId"], r["uid"]) for r in rows_rm], flush=True)

    # Duplicate uid_sec1 (deck-section-1)
    dup_btn = page.query_selector(
        f"#tray-list .tray-row[data-uid='{uid_sec1}'] .tray-duplicate"
    )
    dup_btn.click()
    page.wait_for_timeout(500)
    rows_d = dom_rows(page)
    print("After dup:", [(r["slideId"], r["uid"]) for r in rows_d], flush=True)

    # Add blank
    page.click("#add-blank-btn")
    page.wait_for_timeout(400)
    rows_b = dom_rows(page)
    print("After blank:", [(r["slideId"], r["uid"]) for r in rows_b], flush=True)

    # Inject fetch hook
    hook_result = page.evaluate(
        """
        () => {
            const orig_fetch = window.fetch;
            window._lastDecksave = null;
            window.fetch = function(url, opts) {
                if (url && url.includes && url.includes('deck-save')) {
                    try { window._lastDecksave = JSON.parse(opts.body); } catch(e) {}
                }
                return orig_fetch.apply(this, arguments);
            };
            return 'hooked';
        }
    """
    )
    print(f"fetch hook: {hook_result}", flush=True)

    # Save
    post(base + "/api/_test/set-dialog", {"path": save_path})
    page.click("#save-new-btn")
    page.wait_for_timeout(2500)

    last_save = page.evaluate("() => window._lastDecksave")
    print(
        f"JS-captured save payload: {json.dumps(last_save)[:300] if last_save else 'None'}",
        flush=True,
    )

    browser.close()

proc.terminate()

print("\n=== Saved file check ===")
if os.path.exists(save_path):
    with open(os.path.join(REPO, "tecer-gsmm-introduction.html"), encoding="utf-8") as f:
        orig = f.read()
    with open(save_path, encoding="utf-8") as f:
        saved = f.read()
    orig_hashes = [
        hashlib.sha256(orig[s:e].encode()).hexdigest()[:12]
        for s, e in split_top_sections(orig)
    ]
    saved_hashes = [
        hashlib.sha256(saved[s:e].encode()).hexdigest()[:12]
        for s, e in split_top_sections(saved)
    ]
    print(f"orig hashes: {orig_hashes}")
    print(f"saved hashes: {saved_hashes}")
    for i, h in enumerate(saved_hashes):
        label = (
            f"orig[{orig_hashes.index(h)}]"
            if h in orig_hashes
            else "new/blank"
        )
        print(f"  saved[{i}]={h}->{label}")
else:
    print("SAVE FILE NOT FOUND")

print("\n=== All intercepted saves ===")
for k, v in CAPTURED.items():
    print(f"{k}: {json.dumps(v.get('items') if isinstance(v, dict) else v)[:200]}")
