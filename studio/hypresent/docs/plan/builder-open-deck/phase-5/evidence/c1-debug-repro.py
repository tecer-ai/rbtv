"""
c1-debug-repro.py — DEBUG reproduction of the multi-step deck-save defect.

Reproduces the verifier's EXACT gesture sequence on a temp copy of the OWNER deck
(tecer-gsmm-introduction.html), instrumenting at every step:

  After EACH gesture:
    - dump the DOM row identities (uid, slideId, badge, title)
  At save time:
    - intercept the POST body to /api/deck-save (page.route) -> the literal getItems() payload
    - compare payload.items[].index against the intended final arrangement
    - compare payload -> saved bytes (section hashes)

Decides H1 (tray-model identity bug) vs H2 (server mis-splice) vs H3 (driver targeting drift).

Headless is fine: the defect is data-level (verifier's isolated reorder-only save was correct headless).

Usage:
  python c1-debug-repro.py <server_base> <owner_deck_copy> <evidence_dir>
"""
import os, sys, json, time, hashlib, re

SERVER = sys.argv[1]
DECK   = sys.argv[2]
EVDIR  = sys.argv[3] if len(sys.argv) > 3 else "."
os.makedirs(EVDIR, exist_ok=True)

from playwright.sync_api import sync_playwright

LOG = []
def log(m):
    print(m, flush=True)
    LOG.append(str(m))

def dom_rows(page):
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r,i)=>({
            i, uid:r.dataset.uid, slideId:r.dataset.slideId,
            badge:r.querySelector('.tray-badge')?r.querySelector('.tray-badge').textContent:'',
            title:r.querySelector('.tray-title')?r.querySelector('.tray-title').textContent.trim():''
        }))
    """)

def split_top_sections(html):
    """Mirror server/recompose.split_sections: byte spans of top-level <section>."""
    spans = []
    depth = 0
    in_comment = False
    i = 0
    n = len(html)
    cur = None
    while i < n:
        if not in_comment:
            if html.startswith("<!--", i):
                in_comment = True; i += 4; continue
        else:
            if html.startswith("-->", i):
                in_comment = False; i += 3; continue
            i += 1; continue
        if html.startswith("<section", i):
            after = i + 8
            if after < n and html[after] in " \t\n>":
                if depth == 0: cur = i
                depth += 1; i += 8; continue
        if html.startswith("</section>", i):
            depth -= 1
            if depth == 0 and cur is not None:
                spans.append((cur, i + 10)); cur = None
            i += 10; continue
        i += 1
    return spans

def section_hashes(html):
    spans = split_top_sections(html)
    return [hashlib.sha256(html[s:e].encode()).hexdigest()[:12] for (s, e) in spans]

CAPTURED = {"deck_save_body": None}

def run():
    with open(DECK, encoding="utf-8") as f:
        orig_html = f.read()
    orig_hashes = section_hashes(orig_html)
    log(f"ORIG section count: {len(orig_hashes)}")
    log(f"ORIG hashes: {orig_hashes}")

    import tempfile
    save_dir = tempfile.mkdtemp()
    save_path = os.path.join(save_dir, "c1-debug-saved.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()

        # Intercept the deck-save POST to capture the literal getItems() payload.
        def handle_route(route):
            req = route.request
            if req.method == "POST" and "/api/deck-save" in req.url:
                try:
                    CAPTURED["deck_save_body"] = req.post_data_json
                except Exception:
                    CAPTURED["deck_save_body"] = req.post_data
                log("  [INTERCEPT] captured /api/deck-save POST body")
            route.continue_()
        page.route("**/api/deck-save", handle_route)

        # set fake open dialog -> owner deck copy
        page.request.post(SERVER + "/api/_test/set-dialog", data=json.dumps({"path": DECK}),
                          headers={"Content-Type": "application/json"})

        # STEP 1 — open deck
        page.goto(SERVER + "/app/builder.html")
        page.wait_for_load_state("networkidle", timeout=8000)
        page.click("#open-deck-btn")
        page.wait_for_function(
            "() => document.querySelectorAll('#tray-list .tray-row').length > 0", timeout=15000)
        page.wait_for_timeout(800)
        s_open = dom_rows(page)
        log("=== AFTER OPEN ===")
        log(json.dumps(s_open[:5], indent=2))

        # STEP 2 — reorder: drag row[1] grip above row[0] (swap 0<->1)
        rows = page.query_selector_all("#tray-list .tray-row")
        r0 = rows[0].bounding_box(); r1 = rows[1].bounding_box()
        grip1 = rows[1].query_selector(".grip").bounding_box()
        sx = grip1["x"] + grip1["width"]/2; sy = grip1["y"] + grip1["height"]/2
        tx = r0["x"] + r0["width"]/2; ty = r0["y"] - 4
        page.mouse.move(sx, sy); page.mouse.down(); time.sleep(0.2)
        for k in range(13):
            t = k/12
            page.mouse.move(sx+(tx-sx)*t, sy+(ty-sy)*t); time.sleep(0.02)
        time.sleep(0.15); page.mouse.up(); time.sleep(0.6)
        s_reorder = dom_rows(page)
        log("=== AFTER REORDER (swap 0<->1) ===")
        log(json.dumps(s_reorder[:5], indent=2))

        # STEP 3 — remove row[2]
        rows = page.query_selector_all("#tray-list .tray-row")
        rm = rows[2]
        rm_id = rm.get_attribute("data-slide-id"); rm_uid = rm.get_attribute("data-uid")
        log(f"REMOVE target: pos2 uid={rm_uid} slideId={rm_id}")
        rm.query_selector(".tray-remove").click(); time.sleep(0.5)
        s_remove = dom_rows(page)
        log("=== AFTER REMOVE (pos2) ===")
        log(json.dumps(s_remove[:5], indent=2))

        # STEP 4 — duplicate row[0]
        rows = page.query_selector_all("#tray-list .tray-row")
        dup = rows[0]
        dup_id = dup.get_attribute("data-slide-id"); dup_uid = dup.get_attribute("data-uid")
        log(f"DUPLICATE target: pos0 uid={dup_uid} slideId={dup_id}")
        dup.query_selector(".tray-duplicate").click(); time.sleep(0.5)
        s_dup = dom_rows(page)
        log("=== AFTER DUPLICATE (pos0) ===")
        log(json.dumps(s_dup[:6], indent=2))

        # STEP 5 — add blank
        page.click("#add-blank-btn"); time.sleep(0.4)
        s_blank = dom_rows(page)
        log("=== AFTER ADD BLANK ===")
        log(json.dumps(s_blank[-2:], indent=2))

        # (skip library add — known pointer-interception failure, irrelevant to defect)

        # STEP 6 — save as new file
        page.request.post(SERVER + "/api/_test/set-dialog", data=json.dumps({"path": save_path}),
                          headers={"Content-Type": "application/json"})
        page.click("#save-new-btn")
        page.wait_for_timeout(2500)

        final_dom = dom_rows(page)
        log("=== FINAL DOM (pre-nav) ===")
        log(json.dumps(final_dom, indent=2))

        browser.close()

    # ── Analyze ───────────────────────────────────────────────────────────────
    body = CAPTURED["deck_save_body"]
    log("=== CAPTURED POST PAYLOAD items ===")
    items = body.get("items") if isinstance(body, dict) else None
    log(json.dumps(items, indent=2))

    saved_exists = os.path.exists(save_path)
    saved_hashes = []
    if saved_exists:
        with open(save_path, encoding="utf-8") as f:
            saved_html = f.read()
        saved_hashes = section_hashes(saved_html)
    log(f"SAVED exists: {saved_exists} sections={len(saved_hashes)}")
    log(f"SAVED hashes: {saved_hashes}")

    # Map each existing item.index -> orig hash; predict saved hashes from payload.
    predicted = []
    for it in (items or []):
        if it.get("kind") == "existing":
            predicted.append(orig_hashes[it["index"]] if 0 <= it["index"] < len(orig_hashes) else f"OOR:{it['index']}")
        elif it.get("kind") == "blank":
            predicted.append("BLANK")
        elif it.get("kind") == "library":
            predicted.append("LIB")
        else:
            predicted.append("?")
    log("=== PREDICTED-FROM-PAYLOAD vs SAVED ===")
    log(f"predicted: {predicted}")
    log(f"saved-mapped: {[ (h if h in orig_hashes else ('BLANK' if False else h)) for h in saved_hashes]}")

    # Intended final arrangement (what the gestures SHOULD produce, by orig index):
    #   open:    [0,1,2,3,4,5,6,7,8,9]
    #   swap0<->1[1,0,2,3,4,5,6,7,8,9]
    #   remove pos2 (orig idx2): [1,0,3,4,5,6,7,8,9]
    #   dup pos0 (orig idx1):    [1,1,0,3,4,5,6,7,8,9]
    #   add blank:               [1,1,0,3,4,5,6,7,8,9,BLANK]
    intended_idx = [1,1,0,3,4,5,6,7,8,9]
    intended = [orig_hashes[i] for i in intended_idx] + ["BLANK"]
    log("=== INTENDED (correct) arrangement ===")
    log(f"intended idx: {intended_idx} + blank")
    log(f"intended hashes: {intended}")

    payload_matches_intended = (predicted == intended)
    saved_matches_payload = (saved_hashes[:len(predicted)] == [p for p in predicted if p != "BLANK"] or
                             saved_section_eq(saved_hashes, predicted, orig_hashes))
    log("=== VERDICT INPUTS ===")
    log(f"payload_matches_intended (H not-1 if True): {payload_matches_intended}")

    out = {
        "orig_hashes": orig_hashes,
        "dom_after_open": s_open if False else None,
        "states": {
            "open": s_open, "reorder": s_reorder, "remove": s_remove,
            "duplicate": s_dup, "blank": s_blank, "final_dom": final_dom,
        },
        "captured_payload_items": items,
        "saved_hashes": saved_hashes,
        "predicted_from_payload": predicted,
        "intended_arrangement": intended,
        "intended_idx": intended_idx,
        "payload_matches_intended": payload_matches_intended,
        "saved_matches_payload": saved_hashes_match(saved_hashes, predicted),
        "save_path": save_path,
    }
    with open(os.path.join(EVDIR, "c1-debug-repro-result.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(EVDIR, "c1-debug-repro-log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))
    log("WROTE c1-debug-repro-result.json + c1-debug-repro-log.txt")

def saved_hashes_match(saved, predicted):
    """Compare saved hashes to payload-predicted hashes, treating BLANK as a wildcard
    (blank section content is deterministic but not an orig hash)."""
    if len(saved) != len(predicted):
        return False
    for s, pr in zip(saved, predicted):
        if pr == "BLANK":
            continue
        if s != pr:
            return False
    return True

def saved_section_eq(saved, predicted, orig):
    return saved_hashes_match(saved, predicted)

if __name__ == "__main__":
    run()
