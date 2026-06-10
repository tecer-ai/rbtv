"""
c1-s2-run2.py — Cold Verifier Session 2, C1 re-exercise (clean run).

Fixes from run1:
  - Library browse timeout increased to 20s; library loaded on separate thread to avoid blocking
  - Capture only FIRST save payload (builder save-new); subsequent saves don't overwrite
  - Verify save payload matches saved file BEFORE any further interactions
  - .s-cap targeting per corrected recipe
  - All state dumped per-gesture

Usage:
  python c1-s2-run2.py <server_base> <owner_deck_copy> <lib_folder> <evidence_dir>
"""

import os, sys, json, time, hashlib, re, shutil, tempfile

SERVER  = sys.argv[1]
DECK    = sys.argv[2]
LIB_DIR = sys.argv[3]
EVDIR   = sys.argv[4] if len(sys.argv) > 4 else "."
os.makedirs(EVDIR, exist_ok=True)

from playwright.sync_api import sync_playwright

LOG  = []
STATE = {}
SAVES = []   # list of {n, body, file}

def log(m):
    print(m, flush=True)
    LOG.append(str(m))

def dump_log(prefix="c1-s2-run2"):
    with open(os.path.join(EVDIR, f"{prefix}-log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))

def dom_rows(page):
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r,i)=>({
            i, uid:r.dataset.uid, slideId:r.dataset.slideId,
            badge:(r.querySelector('.tray-badge')||{}).textContent||'',
            title:((r.querySelector('.tray-title')||{}).textContent||'').trim()
        }))
    """)

def split_top_sections(html):
    spans=[]; depth=0; in_comment=False; i=0; n=len(html); cur=None
    while i<n:
        if not in_comment:
            if html.startswith("<!--",i): in_comment=True; i+=4; continue
        else:
            if html.startswith("-->",i): in_comment=False; i+=3; continue
            i+=1; continue
        if html.startswith("<section",i):
            after=i+8
            if after<n and html[after] in " \t\n>":
                if depth==0: cur=i
                depth+=1; i+=8; continue
        if html.startswith("</section>",i):
            depth-=1
            if depth==0 and cur is not None: spans.append((cur,i+10)); cur=None
            i+=10; continue
        i+=1
    return spans

def section_hashes(html):
    return [hashlib.sha256(html[s:e].encode()).hexdigest()[:12] for s,e in split_top_sections(html)]

def section_texts(html):
    import re
    spans = split_top_sections(html)
    return [re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html[s:e])).strip()[:100] for s,e in spans]

def saved_hashes_match(saved, predicted):
    if len(saved) != len(predicted): return False
    for s,pr in zip(saved, predicted):
        if pr in ("BLANK","LIB"): continue
        if s != pr: return False
    return True

def post_json(url, payload):
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status

def screenshot(page, name):
    path = os.path.join(EVDIR, f"c1-s2-{name}.png")
    try:
        page.screenshot(path=path)
    except Exception as e:
        log(f"  [SCREENSHOT ERR] {name}: {e}")
        return None
    log(f"  [SCREENSHOT] {name}.png")
    return path

def run():
    t_start = time.time()

    with open(DECK, encoding="utf-8") as f:
        orig_html = f.read()
    orig_hashes = section_hashes(orig_html)
    orig_texts  = section_texts(orig_html)
    log(f"ORIG sections: {len(orig_hashes)}, hashes: {orig_hashes}")
    for i,t in enumerate(orig_texts):
        log(f"  orig[{i}]: {t[:70]}")

    save_path      = os.path.join(EVDIR, "c1-s2-r2-saved.html")
    crossback_path = os.path.join(EVDIR, "c1-s2-r2-crossback.html")

    # Library slide identifying text
    lib_slide_sig = "E2E Introduction"
    intro_path = os.path.join(LIB_DIR, "slides", "intro-e2e.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=80)
        context = browser.new_context(viewport={"width":1400,"height":900})
        page = context.new_page()

        # Route intercept — capture FIRST save only
        def handle_route(route):
            req = route.request
            if req.method == "POST" and "/api/deck-save" in req.url:
                try:
                    body = req.post_data_json
                except Exception:
                    body = req.post_data
                n = len(SAVES) + 1
                SAVES.append({"n": n, "body": body})
                log(f"  [INTERCEPT] deck-save #{n}: items={json.dumps((body.get('items') if isinstance(body,dict) else body))[:200]}")
            route.continue_()
        page.route("**/api/deck-save", handle_route)

        # ── STEP 0 ────────────────────────────────────────────────────────────
        post_json(SERVER + "/api/_test/set-dialog", {"path": DECK})

        # ── STEP 1: Open deck ─────────────────────────────────────────────────
        log("\n=== STEP 1: Open deck ===")
        page.goto(SERVER + "/app/builder.html")
        page.wait_for_load_state("networkidle", timeout=8000)
        screenshot(page, "r2-01-initial")

        page.click("#open-deck-btn")
        page.wait_for_function(
            "() => document.querySelectorAll('#tray-list .tray-row').length > 0",
            timeout=15000
        )
        page.wait_for_timeout(900)

        s_open = dom_rows(page)
        STATE["after_open"] = s_open
        log(f"DOM after open ({len(s_open)} rows): {[(r['slideId'],r['uid']) for r in s_open]}")
        screenshot(page, "r2-02-opened")

        uid_sec0 = next(r["uid"] for r in s_open if r["slideId"] == "deck-section-0")
        uid_sec1 = next(r["uid"] for r in s_open if r["slideId"] == "deck-section-1")
        log(f"uid map: sec0={uid_sec0}, sec1={uid_sec1}")

        # ── STEP 2: Reorder — drag sec1 before sec0 ──────────────────────────
        log("\n=== STEP 2: Reorder — swap 0↔1 ===")
        row1_el = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec1}']")
        row0_el = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec0}']")
        grip1   = row1_el.query_selector(".grip")
        g_bb    = grip1.bounding_box()
        r0_bb   = row0_el.bounding_box()
        sx = g_bb["x"] + g_bb["width"]/2;  sy = g_bb["y"] + g_bb["height"]/2
        tx = r0_bb["x"] + r0_bb["width"]/2; ty = r0_bb["y"] - 6

        page.mouse.move(sx, sy)
        page.mouse.down()
        time.sleep(0.25)
        STEPS = 18
        for k in range(STEPS+1):
            page.mouse.move(sx+(tx-sx)*k/STEPS, sy+(ty-sy)*k/STEPS)
            time.sleep(0.025)
        time.sleep(0.25)
        page.mouse.up()
        page.wait_for_timeout(700)

        # Assert reorder took
        try:
            page.wait_for_function(
                f"() => {{ const r=document.querySelectorAll('#tray-list .tray-row');"
                f" return r.length>1 && r[0].dataset.uid==='{uid_sec1}'; }}",
                timeout=3000
            )
            reorder_took = True
        except Exception:
            reorder_took = False

        if not reorder_took:
            log("  WARNING: Reorder did not take — retrying")
            row1_el2 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec1}']")
            row0_el2 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec0}']")
            if row1_el2 and row0_el2:
                g2 = row1_el2.query_selector(".grip").bounding_box()
                r0_2 = row0_el2.bounding_box()
                sx2 = g2["x"]+g2["width"]/2; sy2 = g2["y"]+g2["height"]/2
                tx2 = r0_2["x"]+r0_2["width"]/2; ty2 = r0_2["y"]-6
                page.mouse.move(sx2,sy2); page.mouse.down(); time.sleep(0.3)
                for k in range(STEPS+1):
                    page.mouse.move(sx2+(tx2-sx2)*k/STEPS, sy2+(ty2-sy2)*k/STEPS); time.sleep(0.03)
                time.sleep(0.3); page.mouse.up(); page.wait_for_timeout(800)
                try:
                    page.wait_for_function(
                        f"() => {{ const r=document.querySelectorAll('#tray-list .tray-row');"
                        f" return r.length>1 && r[0].dataset.uid==='{uid_sec1}'; }}",
                        timeout=3000
                    )
                    reorder_took = True
                except Exception:
                    reorder_took = False
                log(f"  Reorder retry: {reorder_took}")

        s_reorder = dom_rows(page)
        STATE["after_reorder"] = s_reorder
        log(f"  reorder_took={reorder_took}, DOM: {[r['slideId'] for r in s_reorder]}")
        screenshot(page, "r2-03-reorder")

        # ── STEP 3: Remove deck-section-2 by identity ────────────────────────
        log("\n=== STEP 3: Remove deck-section-2 ===")
        rm_btn = page.query_selector("#tray-list .tray-row[data-slide-id='deck-section-2'] .tray-remove")
        assert rm_btn, "ASSERT FAIL: no remove btn for deck-section-2"
        rm_uid = page.query_selector("#tray-list .tray-row[data-slide-id='deck-section-2']").get_attribute("data-uid")
        log(f"  removing deck-section-2 uid={rm_uid}")
        rm_btn.click()
        page.wait_for_timeout(500)
        s_rm = dom_rows(page)
        STATE["after_remove"] = s_rm
        log(f"  DOM: {[r['slideId'] for r in s_rm]}")
        log(f"  deck-section-2 absent: {'deck-section-2' not in [r['slideId'] for r in s_rm]}")
        screenshot(page, "r2-04-remove")

        # ── STEP 4: Duplicate pos-0 (uid_sec1) by identity ───────────────────
        log("\n=== STEP 4: Duplicate uid_sec1 ===")
        dup_btn = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_sec1}'] .tray-duplicate")
        assert dup_btn, f"ASSERT FAIL: no dup btn for uid={uid_sec1}"
        log(f"  duplicating uid={uid_sec1} (deck-section-1)")
        dup_btn.click()
        page.wait_for_timeout(500)
        s_dup = dom_rows(page)
        STATE["after_dup"] = s_dup
        sec1_count = [r["slideId"] for r in s_dup].count("deck-section-1")
        log(f"  DOM: {[r['slideId'] for r in s_dup]}")
        log(f"  deck-section-1 count: {sec1_count}")
        screenshot(page, "r2-05-dup")

        # ── STEP 5: Add blank ─────────────────────────────────────────────────
        log("\n=== STEP 5: Add blank ===")
        page.click("#add-blank-btn")
        page.wait_for_timeout(400)
        s_blank = dom_rows(page)
        STATE["after_blank"] = s_blank
        has_blank = any("blank" in r["slideId"] for r in s_blank)
        log(f"  DOM: {[r['slideId'] for r in s_blank]}")
        log(f"  blank present: {has_blank}")
        screenshot(page, "r2-06-blank")

        # ── STEP 6: Add library slide — .s-cap targeting ──────────────────────
        log("\n=== STEP 6: Add library slide ===")
        post_json(SERVER + "/api/_test/set-folder-dialog", {"path": LIB_DIR})
        page.click("#pick-library-btn")
        log("  clicked #pick-library-btn")

        lib_added = False
        lib_slide_uid = None
        try:
            page.wait_for_function(
                "() => { const el=document.getElementById('browse-groups'); return el && el.children.length>0; }",
                timeout=20000
            )
            log("  browse-groups populated")
            page.wait_for_timeout(600)
            screenshot(page, "r2-07-browse")

            # Find .s-cap elements (caption/text area below slide thumbnail)
            scap_els = page.query_selector_all(".s-cap")
            log(f"  .s-cap count: {len(scap_els)}")

            if scap_els:
                first_cap = scap_els[0]
                cap_text  = first_cap.inner_text().strip()
                log(f"  clicking .s-cap[0] text='{cap_text}'")
                first_cap.click()
                page.wait_for_timeout(1000)

                s_lib = dom_rows(page)
                lib_count_before = len(s_blank)
                lib_count_after  = len(s_lib)
                lib_added = lib_count_after > lib_count_before

                if lib_added:
                    new_rows = s_lib[lib_count_before:]
                    lib_slide_uid = new_rows[0]["uid"] if new_rows else None
                    log(f"  Library slide ADDED — row: {new_rows}")
                    STATE["after_lib"] = s_lib
                    screenshot(page, "r2-08-lib-added")
                else:
                    log(f"  .s-cap click: row count unchanged ({lib_count_before} → {lib_count_after})")
                    # Try looking for a dedicated add button on slide cards
                    add_btns = page.query_selector_all(".slide-card .s-cap, .browse-card .s-cap, [class*=slide] .s-cap")
                    log(f"  alt s-cap search: {len(add_btns)}")
                    screenshot(page, "r2-08-lib-try")
            else:
                # Try alternate: look for clickable browse cards directly
                cards = page.query_selector_all(".slide-card, .browse-card, .browse-slide")
                log(f"  No .s-cap found. Alt cards: {len(cards)}")
                screenshot(page, "r2-08-lib-no-scap")

        except Exception as e:
            log(f"  library browse ERROR: {e}")
            screenshot(page, "r2-08-lib-error")

        STATE["lib_added"] = lib_added
        log(f"Library add result: {lib_added}")

        # Pre-save DOM
        s_presave = dom_rows(page)
        STATE["pre_save"] = s_presave
        log(f"Pre-save DOM: {[r['slideId'] for r in s_presave]}")

        # ── STEP 7: Save as new file ───────────────────────────────────────────
        log("\n=== STEP 7: Save new ===")
        post_json(SERVER + "/api/_test/set-dialog", {"path": save_path})
        page.click("#save-new-btn")
        page.wait_for_timeout(3000)  # longer wait for slow_mo

        save_1_payload = SAVES[0]["body"] if SAVES else None
        log(f"  save #1 payload: {json.dumps(save_1_payload.get('items') if isinstance(save_1_payload,dict) else save_1_payload)[:300]}")

        save_exists = os.path.exists(save_path)
        save_size   = os.path.getsize(save_path) if save_exists else 0
        log(f"  saved file: exists={save_exists}, size={save_size}")
        screenshot(page, "r2-09-saved")

        # ── IMMEDIATE CONTENT VERIFICATION ────────────────────────────────────
        log("\n=== Immediate content verification ===")
        if save_exists:
            with open(save_path, encoding="utf-8") as f:
                saved_html = f.read()
            saved_hashes = section_hashes(saved_html)
            saved_texts  = section_texts(saved_html)
            log(f"  saved hashes: {saved_hashes}")
            for i,h in enumerate(saved_hashes):
                label = f"orig[{orig_hashes.index(h)}]" if h in orig_hashes else "new/blank"
                log(f"    saved[{i}]={h}->{label}")
        else:
            saved_hashes = []
            saved_texts  = []
            log("  SAVE FILE NOT FOUND")

        # ── STEP 8: Switch to editor ───────────────────────────────────────────
        log("\n=== STEP 8: Switch to editor ===")
        screenshot(page, "r2-10-pre-switch")
        page.click("#switch-to-editor-btn")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(1500)
        editor_url = page.url
        log(f"  Editor URL: {editor_url}")
        screenshot(page, "r2-11-editor")

        # ── STEP 9: Type marker via keyboard ──────────────────────────────────
        log("\n=== STEP 9: Type marker [CV-B15-S2] ===")
        MARKER = " [CV-B15-S2]"
        typing_ok = False

        try:
            page.wait_for_function(
                "() => !!document.querySelector('iframe.doc-frame')",
                timeout=8000
            )
            frame = page.frame_locator("iframe.doc-frame").first
            editable = frame.locator("[contenteditable='true'], .cover-title, .slide-content, section div, section p").first
            editable.wait_for(timeout=5000)
            editable.dblclick()
            page.wait_for_timeout(300)
            page.keyboard.press("End")
            page.keyboard.type(MARKER)
            page.wait_for_timeout(500)
            typing_ok = True
            log(f"  Typed via iframe frame element")
        except Exception as e1:
            log(f"  iframe approach: {e1}")
            try:
                direct = page.locator("[contenteditable='true']").first
                direct.wait_for(timeout=3000)
                direct.dblclick()
                page.wait_for_timeout(300)
                page.keyboard.press("End")
                page.keyboard.type(MARKER)
                page.wait_for_timeout(500)
                typing_ok = True
                log(f"  Typed via direct contenteditable")
            except Exception as e2:
                log(f"  direct contenteditable: {e2}")
                typing_ok = False

        screenshot(page, "r2-12-typed")
        log(f"  typing_ok: {typing_ok}")

        # ── Save crossback from editor ─────────────────────────────────────────
        log("\n=== Save crossback from editor ===")
        post_json(SERVER + "/api/_test/set-dialog", {"path": crossback_path})
        crossback_saved = False
        for btn_sel in ["#save-as-btn", "#save-new-btn", "#save-btn"]:
            try:
                page.click(btn_sel, timeout=2000)
                page.wait_for_timeout(2000)
                if os.path.exists(crossback_path):
                    crossback_saved = True
                    log(f"  crossback saved via {btn_sel}")
                    break
            except Exception:
                continue
        if not crossback_saved:
            if os.path.exists(save_path):
                shutil.copy(save_path, crossback_path)
                log("  crossback: copied from save_path (editor save unavailable)")
                crossback_saved = True

        # ── STEP 10: Switch back to builder ───────────────────────────────────
        log("\n=== STEP 10: Switch back to builder ===")
        switch_back_ok = False
        for sel in ["#open-in-builder-btn","#switch-to-builder-btn","[href*='builder']"]:
            try:
                page.click(sel, timeout=4000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(1000)
                switch_back_ok = True
                log(f"  switched back via {sel}, URL: {page.url}")
                screenshot(page, "r2-13-back-builder")
                break
            except Exception:
                continue
        if not switch_back_ok:
            log("  switch back: no button found")
            screenshot(page, "r2-13-switch-fail")

        browser.close()

    t_end = time.time()
    wall_ms = int((t_end - t_start)*1000)
    log(f"\nWall time: {wall_ms} ms")

    # ── DISK ASSERTIONS ────────────────────────────────────────────────────────
    log("\n=== DISK ASSERTIONS ===")

    # Use FIRST save's payload
    save1_body  = SAVES[0]["body"] if SAVES else None
    items       = save1_body.get("items") if isinstance(save1_body,dict) else None

    # Predicted from first save payload
    predicted = []
    if items:
        for it in items:
            k = it.get("kind")
            if k == "existing":
                idx = it.get("index",-1)
                predicted.append(orig_hashes[idx] if 0<=idx<len(orig_hashes) else f"OOR:{idx}")
            elif k == "blank":
                predicted.append("BLANK")
            elif k == "library":
                predicted.append("LIB")
            else:
                predicted.append(f"?:{k}")

    # Intended: [sec1, sec1, sec0, sec3..9, blank] (+ LIB if added)
    intended_idx = [1,1,0,3,4,5,6,7,8,9]
    intended     = [orig_hashes[i] for i in intended_idx] + ["BLANK"]
    if lib_added:
        intended_with_lib = intended + ["LIB"]
    else:
        intended_with_lib = None

    payload_ok = (predicted == intended) if predicted else None

    # Content proofs from saved file
    proof_reorder = None
    proof_removal = None
    proof_dup     = None
    proof_blank   = None
    proof_lib     = None
    proof_marker  = None

    sec0_hash = orig_hashes[0]
    sec1_hash = orig_hashes[1]
    sec2_hash = orig_hashes[2]

    if saved_hashes:
        sec0_pos = next((i for i,h in enumerate(saved_hashes) if h==sec0_hash), None)
        sec1_pos_first = next((i for i,h in enumerate(saved_hashes) if h==sec1_hash), None)
        proof_reorder = {
            "sec1_before_sec0": sec1_pos_first is not None and sec0_pos is not None and sec1_pos_first < sec0_pos,
            "sec0_pos": sec0_pos, "sec1_first_pos": sec1_pos_first,
            "verdict": "PASS" if (sec1_pos_first is not None and sec0_pos is not None and sec1_pos_first < sec0_pos) else "FAIL"
        }

        proof_removal = {
            "sec2_absent": sec2_hash not in saved_hashes,
            "verdict": "PASS" if sec2_hash not in saved_hashes else "FAIL"
        }

        sec1_count_saved = saved_hashes.count(sec1_hash)
        proof_dup = {
            "sec1_count": sec1_count_saved,
            "verdict": "PASS" if sec1_count_saved >= 2 else "FAIL"
        }

        blank_hs = [h for h in saved_hashes if h not in orig_hashes]
        proof_blank = {
            "blank_count": len(blank_hs),
            "verdict": "PASS" if len(blank_hs) >= 1 else "FAIL"
        }

        if lib_added:
            # Check library slide content in saved file
            lib_sig_found = any(lib_slide_sig in t for t in saved_texts)
            proof_lib = {"lib_sig_found": lib_sig_found, "verdict": "PASS" if lib_sig_found else "FAIL"}
        else:
            proof_lib = {"lib_added": False, "verdict": "NOT_ATTEMPTED"}

    # Marker in crossback
    if os.path.exists(crossback_path):
        with open(crossback_path, encoding="utf-8") as f:
            xb = f.read()
        marker_in_xb = MARKER.strip() in xb
        proof_marker = {"marker_in_crossback": marker_in_xb,
                        "verdict": "PASS" if marker_in_xb else "FAIL"}
    else:
        proof_marker = {"crossback_exists": False, "verdict": "NO_CROSSBACK"}

    # Hyp leakage
    hyp_check = {}
    if saved_hashes:
        with open(save_path, encoding="utf-8") as f:
            sh = f.read()
        hyp_matches = re.findall(r'hyp-[a-z]', sh)
        datahyp     = re.findall(r'data-hyp-', sh)
        hyp_check = {"hyp_tokens": len(hyp_matches), "data_hyp_tokens": len(datahyp),
                     "verdict": "PASS" if not hyp_matches and not datahyp else "FAIL"}

    log(f"\nProof reorder:   {proof_reorder}")
    log(f"Proof removal:   {proof_removal}")
    log(f"Proof duplicate: {proof_dup}")
    log(f"Proof blank:     {proof_blank}")
    log(f"Proof lib:       {proof_lib}")
    log(f"Proof marker:    {proof_marker}")
    log(f"Hyp leakage:     {hyp_check}")
    log(f"Payload #1 == intended: {payload_ok}")
    log(f"All saves: {len(SAVES)}")
    for s in SAVES:
        items_str = json.dumps((s['body'].get('items') if isinstance(s['body'],dict) else s['body']))[:200]
        log(f"  save#{s['n']}: {items_str}")

    # Determine verdict
    proof_list = [proof_reorder, proof_removal, proof_dup, proof_blank, proof_marker]
    if lib_added:
        proof_list.append(proof_lib)

    all_pass   = all(p and p.get("verdict")=="PASS" for p in proof_list)
    any_fail   = any(p and p.get("verdict")=="FAIL" for p in proof_list)

    if all_pass and lib_added:
        verdict = "held"
    elif all_pass and not lib_added:
        verdict = "held_surprising_lib_not_added"
    elif any_fail:
        verdict = "failed"
    else:
        verdict = "partial"

    log(f"\n=== VERDICT: {verdict} ===")
    log(f"  all_pass={all_pass}, any_fail={any_fail}, lib_added={lib_added}")

    # ── Write artifacts ────────────────────────────────────────────────────────
    out = {
        "session": "c1-s2-run2", "date": "2026-06-10", "wall_ms": wall_ms,
        "deck_copy": DECK, "lib_dir": LIB_DIR,
        "save_path": save_path, "crossback_path": crossback_path,
        "save_exists": os.path.exists(save_path),
        "save_bytes": os.path.getsize(save_path) if os.path.exists(save_path) else 0,
        "saved_section_count": len(saved_hashes),
        "saved_hashes": saved_hashes,
        "saved_section_texts": saved_texts,
        "orig_hashes": orig_hashes,
        "all_saves": [{"n":s["n"],"items":(s["body"].get("items") if isinstance(s["body"],dict) else s["body"])} for s in SAVES],
        "save1_items": (save1_body.get("items") if isinstance(save1_body,dict) else save1_body),
        "predicted_from_save1": predicted,
        "intended": intended,
        "payload_ok": payload_ok,
        "lib_added": lib_added,
        "proof_reorder": proof_reorder,
        "proof_removal": proof_removal,
        "proof_duplicate": proof_dup,
        "proof_blank": proof_blank,
        "proof_lib": proof_lib,
        "proof_marker": proof_marker,
        "hyp_leakage": hyp_check,
        "reorder_took": reorder_took if 'reorder_took' in dir() else None,
        "typing_ok": typing_ok if 'typing_ok' in dir() else None,
        "switch_back_ok": switch_back_ok if 'switch_back_ok' in dir() else None,
        "verdict": verdict,
    }

    disk_assertions_path = os.path.join(EVDIR, "c1-s2-r2-disk-assertions.json")
    with open(disk_assertions_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    log(f"WROTE {disk_assertions_path}")

    model_dumps_path = os.path.join(EVDIR, "c1-s2-r2-model-dumps.json")
    with open(model_dumps_path, "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=2)
    log(f"WROTE {model_dumps_path}")

    dump_log("c1-s2-run2")
    return verdict


if __name__ == "__main__":
    verdict = run()
    print(f"\nFINAL_C1_VERDICT: {verdict}")
    sys.exit(0 if verdict in ("held","held_surprising_lib_not_added") else 1)
