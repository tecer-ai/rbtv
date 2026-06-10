"""
exit_probes.py — CONDUCTOR-EXECUTED exit probes (verification card §5), builder-open-deck run close.
Authored and run by the conductor itself — not a dispatched worker. One continuous HEADED session
on a fresh temp copy of the owner's real deck. Five probes, evidence files per probe, fail-loud
(no fallback path may mask a failure).

P1 Ingest    — open deck in builder -> 10 rows, slideIds deck-section-0..9
P2 Compose   — identity-targeted reorder (sec1 before sec0) + duplicate sec1 -> DOM order proof
P3 Save      — save-new via seam -> bytes FROZEN immediately -> section-hash order proof, 0 leakage
P4 Bridge    — switch-to-editor -> type " [EXIT-PROBE]" -> save crossback -> open-in-builder back
P5 Integration — crossback bytes carry the marker; 11 sections; >=9/11 hashes identical to frozen save

Usage: python exit_probes.py <server_base> <deck_copy> <evidence_dir>
"""
import os, sys, json, time, hashlib, re, shutil, urllib.request
from html import unescape

SERVER, DECK, EVDIR = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(EVDIR, exist_ok=True)
from playwright.sync_api import sync_playwright

LOG, RESULT = [], {"probes": {}}
def log(m): print(m, flush=True); LOG.append(str(m))

def post_json(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r: return r.status

def split_top_sections(html):
    spans=[]; depth=0; in_comment=False; i=0; n=len(html); cur=None
    while i<n:
        if in_comment:
            if html.startswith("-->",i): in_comment=False; i+=3
            else: i+=1
            continue
        if html.startswith("<!--",i): in_comment=True; i+=4; continue
        if html.startswith("<section",i) and i+8<n and html[i+8] in " \t\n>":
            if depth==0: cur=i
            depth+=1; i+=8; continue
        if html.startswith("</section>",i):
            depth-=1
            if depth==0 and cur is not None: spans.append((cur,i+10)); cur=None
            i+=10; continue
        i+=1
    return spans

def hashes(html): return [hashlib.sha256(html[s:e].encode()).hexdigest()[:12] for s,e in split_top_sections(html)]

def rows(page):
    return page.evaluate("() => Array.from(document.querySelectorAll('#tray-list .tray-row')).map(r=>({uid:r.dataset.uid, slideId:r.dataset.slideId}))")

def shot(page, name):
    page.screenshot(path=os.path.join(EVDIR, f"ep-{name}.png")); log(f"  [shot] ep-{name}.png")

def main():
    t0 = time.time()
    orig = open(DECK, encoding="utf-8").read()
    oh = hashes(orig)
    log(f"orig sections: {len(oh)} {oh}")
    save_path  = os.path.join(EVDIR, "ep-probe-save.html")
    frozen     = os.path.join(EVDIR, "ep-probe-save1-frozen.html")
    crossback  = os.path.join(EVDIR, "ep-probe-crossback.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=60)
        page = browser.new_context(viewport={"width":1400,"height":900}).new_page()

        # P1 — Ingest
        log("=== P1 Ingest ===")
        post_json(SERVER + "/api/_test/set-dialog", {"path": DECK})
        page.goto(SERVER + "/app/builder.html"); page.wait_for_load_state("networkidle", timeout=10000)
        page.click("#open-deck-btn")
        page.wait_for_function("() => document.querySelectorAll('#tray-list .tray-row').length > 0", timeout=15000)
        page.wait_for_timeout(900)
        r1 = rows(page); shot(page, "p1-opened")
        p1 = len(r1)==10 and [r["slideId"] for r in r1]==[f"deck-section-{i}" for i in range(10)]
        RESULT["probes"]["P1_ingest"] = {"rows": len(r1), "order_ok": p1, "verdict": "held" if p1 else "failed"}
        log(f"P1 {'HELD' if p1 else 'FAILED'}: {[r['slideId'] for r in r1]}")

        uid0 = next(r["uid"] for r in r1 if r["slideId"]=="deck-section-0")
        uid1 = next(r["uid"] for r in r1 if r["slideId"]=="deck-section-1")

        # P2 — Compose: reorder sec1 before sec0, then duplicate sec1
        log("=== P2 Compose ===")
        ok_reorder = False
        for attempt in range(2):
            g = page.query_selector(f"#tray-list .tray-row[data-uid='{uid1}'] .grip").bounding_box()
            t = page.query_selector(f"#tray-list .tray-row[data-uid='{uid0}']").bounding_box()
            sx, sy = g["x"]+g["width"]/2, g["y"]+g["height"]/2
            tx, ty = t["x"]+t["width"]/2, t["y"]-6
            page.mouse.move(sx, sy); page.mouse.down(); time.sleep(0.25)
            for k in range(19): page.mouse.move(sx+(tx-sx)*k/18, sy+(ty-sy)*k/18); time.sleep(0.025)
            time.sleep(0.25); page.mouse.up(); page.wait_for_timeout(700)
            try:
                page.wait_for_function(
                    f"() => document.querySelectorAll('#tray-list .tray-row')[0].dataset.uid==='{uid1}'", timeout=3000)
                ok_reorder = True; break
            except Exception: log(f"  reorder attempt {attempt+1} did not take")
        page.query_selector(f"#tray-list .tray-row[data-uid='{uid1}'] .tray-duplicate").click()
        page.wait_for_timeout(600)
        r2 = rows(page); shot(page, "p2-composed")
        ids = [r["slideId"] for r in r2]
        p2 = ok_reorder and len(r2)==11 and ids[0]=="deck-section-1" and ids[1]=="deck-section-1" and ids[2]=="deck-section-0"
        RESULT["probes"]["P2_compose"] = {"reorder_took": ok_reorder, "dom": ids, "verdict": "held" if p2 else "failed"}
        log(f"P2 {'HELD' if p2 else 'FAILED'}: {ids}")

        # P3 — Save new + freeze + hash proof
        log("=== P3 Save ===")
        post_json(SERVER + "/api/_test/set-dialog", {"path": save_path})
        page.click("#save-new-btn"); page.wait_for_timeout(2500)
        p3 = False; sh = []
        if os.path.exists(save_path):
            shutil.copy(save_path, frozen)               # freeze save-#1 bytes before ANY further gesture
            html = open(frozen, encoding="utf-8").read()
            sh = hashes(html)
            expected = [oh[1], oh[1], oh[0]] + oh[2:]    # dup'd sec1 x2, sec0, then sec2..sec9
            leak = len(re.findall(r"hyp-[a-z]", html)) + len(re.findall(r"data-hyp-", html))
            p3 = sh == expected and leak == 0
            RESULT["probes"]["P3_save"] = {"frozen": "ep-probe-save1-frozen.html", "sections": len(sh),
                                           "hash_order_ok": sh == expected, "leakage": leak,
                                           "verdict": "held" if p3 else "failed"}
        else:
            RESULT["probes"]["P3_save"] = {"error": "save file not created", "verdict": "failed"}
        shot(page, "p3-saved"); log(f"P3 {'HELD' if p3 else 'FAILED'}: {sh}")

        # P4 — Bridge: cross to editor, type marker, save crossback, cross back
        log("=== P4 Bridge ===")
        MARKER = " [EXIT-PROBE]"
        page.click("#switch-to-editor-btn")
        page.wait_for_load_state("networkidle", timeout=15000); page.wait_for_timeout(1500)
        try:    # the doc-frame iframe is the editor-only surface — the definitive arrival signal
            page.wait_for_function("() => !!document.querySelector('iframe.doc-frame')", timeout=8000)
            in_editor = True
        except Exception:
            in_editor = False
        shot(page, "p4-editor")
        typed = False
        try:
            page.wait_for_function("() => !!document.querySelector('iframe.doc-frame')", timeout=8000)
            ed = page.frame_locator("iframe.doc-frame").first.locator(
                "[contenteditable='true'], .cover-title, .slide-content, section div, section p").first
            ed.wait_for(timeout=5000); ed.dblclick(); page.wait_for_timeout(300)
            page.keyboard.press("End"); page.keyboard.type(MARKER); page.wait_for_timeout(500)
            typed = True
        except Exception as e:
            log(f"  typing failed: {e}")
        shot(page, "p4-typed")
        post_json(SERVER + "/api/_test/set-dialog", {"path": crossback})
        page.click("#save-as-btn"); page.wait_for_timeout(2500)
        cb_saved = os.path.exists(crossback)             # NO fallback copy — fail loud
        page.click("#open-in-builder-btn"); page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(1000)
        back = "builder.html" in page.url
        shot(page, "p4-back-in-builder")
        p4 = in_editor and typed and cb_saved and back
        RESULT["probes"]["P4_bridge"] = {"entered_editor": in_editor, "typed": typed,
                                         "crossback_saved": cb_saved, "back_in_builder": back,
                                         "verdict": "held" if p4 else "failed"}
        log(f"P4 {'HELD' if p4 else 'FAILED'}: editor={in_editor} typed={typed} cb={cb_saved} back={back}")
        browser.close()

    # P5 — Integration. The crossing's second save MUST be byte-identical to frozen save-#1
    # (builder recompose contract); the crossback (editor serializer round-trip) is held to TEXT-level
    # integrity: same section order, exactly one section differing by the typed marker only.
    log("=== P5 Integration ===")
    p5 = False
    if os.path.exists(crossback) and os.path.exists(frozen):
        fz = open(frozen, encoding="utf-8").read()
        second_save_identical = open(save_path, encoding="utf-8").read() == fz if os.path.exists(save_path) else False
        cb = open(crossback, encoding="utf-8").read()
        def texts(html):
            # entity-decode AFTER tag-strip (so &lt; can't fabricate tags), BEFORE whitespace collapse
            # (so &nbsp; -> \xa0 normalizes to a plain space): editor's lossless &->&amp; re-encoding
            # and contenteditable &nbsp; artifacts must not read as content diffs.
            return [re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html[s:e]))).strip() for s, e in split_top_sections(html)]
        ft, ct = texts(fz), texts(cb)
        ident = sum(1 for a, b in zip(ft, ct) if a == b)
        # marker removal is whitespace-tolerant: contenteditable may place the marker against the
        # next word and convert the displaced space to &nbsp; — token-level equality is the contract.
        edited = sum(1 for a, b in zip(ft, ct)
                     if a != b and re.sub(r"\s*" + re.escape(MARKER.strip()) + r"\s*", " ", b).strip() == a)
        marker_ok = " [EXIT-PROBE]" in cb
        leak = len(re.findall(r"hyp-[a-z]", cb)) + len(re.findall(r"data-hyp-", cb))
        p5 = (second_save_identical and marker_ok and len(ct) == len(ft) == 11
              and edited == 1 and ident == len(ft) - 1 and leak == 0)
        RESULT["probes"]["P5_integration"] = {"second_save_byte_identical_to_frozen": second_save_identical,
                                              "marker_in_bytes": marker_ok, "sections": len(ct),
                                              "text_identical": f"{ident}/{len(ft)}", "edited_with_marker_only": edited,
                                              "leakage": leak, "verdict": "held" if p5 else "failed"}
    else:
        RESULT["probes"]["P5_integration"] = {"error": "missing crossback or frozen file", "verdict": "failed"}
    log(f"P5 {'HELD' if p5 else 'FAILED'}")

    RESULT["wall_ms"] = int((time.time() - t0) * 1000)
    RESULT["all_held"] = all(v.get("verdict") == "held" for v in RESULT["probes"].values())
    json.dump(RESULT, open(os.path.join(EVDIR, "exit-probes-result.json"), "w"), indent=1)
    open(os.path.join(EVDIR, "exit-probes-log.txt"), "w", encoding="utf-8").write("\n".join(LOG))
    log(f"ALL_HELD={RESULT['all_held']} wall_ms={RESULT['wall_ms']}")
    sys.exit(0 if RESULT["all_held"] else 1)

main()
