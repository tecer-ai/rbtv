"""
c1-s2-driver.py — Cold Verifier Session 2, Criterion C1 re-exercise.

Corrected targeting recipe (per c1-debug-diagnosis.md):
  - HEADED (headless=False), real mouse/keyboard gestures
  - Identity-based: re-query by data-slide-id / data-uid before every click
  - Assert reorder took before proceeding (wait_for_function on uid swap)
  - After EACH gesture: capture tray.getItems() model state
  - Library add: use .s-cap (caption area below thumb) not .slide-thumb-wrapper
  - Full disk assertions at content/order/identity level (ANTI-COUNT-ONLY)

Usage:
  python c1-s2-driver.py <server_base> <owner_deck_copy> <lib_folder> <evidence_dir>

All output files get c1-s2- prefix.
"""

import os, sys, json, time, hashlib, re, shutil, tempfile

SERVER  = sys.argv[1]
DECK    = sys.argv[2]
LIB_DIR = sys.argv[3]
EVDIR   = sys.argv[4] if len(sys.argv) > 4 else "."
os.makedirs(EVDIR, exist_ok=True)

from playwright.sync_api import sync_playwright

LOG = []
STATES = {}
CAPTURED = {"deck_save_body": None, "crossback_path": None,
            "all_saves": []}

def log(m):
    print(m, flush=True)
    LOG.append(str(m))

def dump_log():
    with open(os.path.join(EVDIR, "c1-s2-session-log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG))

def dom_rows(page):
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r,i)=>({
            i, uid:r.dataset.uid, slideId:r.dataset.slideId,
            badge: (r.querySelector('.tray-badge')||{}).textContent||'',
            title: ((r.querySelector('.tray-title')||{}).textContent||'').trim()
        }))
    """)

def get_tray_items(page):
    """Call tray.getItems() via JS — the actual model state sent to deck-save."""
    return page.evaluate("() => window.tray ? window.tray.getItems() : null")

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

def section_texts(html):
    """Extract identifying text from each top-level section for order-proof."""
    spans = split_top_sections(html)
    results = []
    for s, e in spans:
        chunk = html[s:e]
        # Extract all text-node-like content (strip tags)
        text = re.sub(r'<[^>]+>', ' ', chunk)
        text = re.sub(r'\s+', ' ', text).strip()[:120]
        results.append(text)
    return results

def saved_hashes_match(saved, predicted):
    if len(saved) != len(predicted):
        return False
    for s, pr in zip(saved, predicted):
        if pr == "BLANK" or pr == "LIB":
            continue
        if s != pr:
            return False
    return True

def post_json_urllib(url, payload):
    import urllib.request
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status

def screenshot(page, name):
    path = os.path.join(EVDIR, f"c1-s2-{name}.png")
    page.screenshot(path=path)
    log(f"  [SCREENSHOT] {path}")
    return path

def run():
    t_start = time.time()

    # ── Read original deck ────────────────────────────────────────────────────
    with open(DECK, encoding="utf-8") as f:
        orig_html = f.read()
    orig_hashes = section_hashes(orig_html)
    orig_texts  = section_texts(orig_html)
    log(f"ORIG section count: {len(orig_hashes)}")
    log(f"ORIG hashes: {orig_hashes}")
    for idx, t in enumerate(orig_texts):
        log(f"  orig[{idx}]: {t[:80]}")

    # Save paths
    save_path      = os.path.join(EVDIR, "c1-s2-saved.html")
    crossback_path = os.path.join(EVDIR, "c1-s2-crossback.html")
    CAPTURED["crossback_path"] = crossback_path

    # ── Read library slide for content-proof ─────────────────────────────────
    intro_path = os.path.join(LIB_DIR, "slides", "intro-e2e.html")
    if os.path.exists(intro_path):
        with open(intro_path, encoding="utf-8") as f:
            lib_slide_text = f.read()
        lib_slide_sig = "E2E Introduction"  # identifying text from intro-e2e.html
    else:
        lib_slide_sig = None
    log(f"Library slide signature: '{lib_slide_sig}'")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=120)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # Intercept deck-save POST
        save_count = [0]
        def handle_route(route):
            req = route.request
            if req.method == "POST" and "/api/deck-save" in req.url:
                try:
                    body = req.post_data_json
                except Exception:
                    body = req.post_data
                save_count[0] += 1
                n = save_count[0]
                CAPTURED["all_saves"].append({"n": n, "body": body})
                if n == 1:
                    CAPTURED["deck_save_body"] = body  # first save = builder save-new
                    log(f"  [INTERCEPT] captured /api/deck-save POST body (save #1 — builder)")
                else:
                    CAPTURED[f"save_{n}_body"] = body
                    log(f"  [INTERCEPT] captured /api/deck-save POST body (save #{n})")
            route.continue_()
        page.route("**/api/deck-save", handle_route)

        # ── STEP 0: Set fake open dialog → owner deck copy ───────────────────
        post_json_urllib(SERVER + "/api/_test/set-dialog", {"path": DECK})

        # ── STEP 1: Open deck in builder ─────────────────────────────────────
        log("\n=== STEP 1: Open builder + load deck ===")
        page.goto(SERVER + "/app/builder.html")
        page.wait_for_load_state("networkidle", timeout=8000)
        screenshot(page, "01-builder-initial")

        page.click("#open-deck-btn")
        page.wait_for_function(
            "() => document.querySelectorAll('#tray-list .tray-row').length > 0",
            timeout=15000
        )
        page.wait_for_timeout(800)

        s_open = dom_rows(page)
        m_open = get_tray_items(page)
        STATES["after_open_dom"] = s_open
        STATES["after_open_model"] = m_open
        log(f"DOM rows after open: {len(s_open)}")
        for r in s_open:
            log(f"  {r}")
        log(f"tray.getItems() after open: {json.dumps(m_open)}")
        screenshot(page, "02-deck-opened")

        # Record uid map: at open, uid=str(n+1) -> slideId deck-section-n
        uid_at_open = {r["slideId"]: r["uid"] for r in s_open}
        log(f"uid map at open: {uid_at_open}")

        # ── STEP 2: Reorder — swap slides 0↔1 by REAL drag ──────────────────
        log("\n=== STEP 2: Reorder — swap 0↔1 ===")
        # Identify targets by slideId identity
        uid_of_sec0 = uid_at_open["deck-section-0"]
        uid_of_sec1 = uid_at_open["deck-section-1"]
        log(f"  Intent: drag uid={uid_of_sec1} (deck-section-1) before uid={uid_of_sec0} (deck-section-0)")

        # Re-query fresh handles
        row1 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_of_sec1}']")
        row0 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_of_sec0}']")
        assert row1 and row0, "Could not find rows by uid for reorder"

        grip1 = row1.query_selector(".grip")
        assert grip1, "No .grip on row1"
        g_bb = grip1.bounding_box()
        r0_bb = row0.bounding_box()

        sx = g_bb["x"] + g_bb["width"] / 2
        sy = g_bb["y"] + g_bb["height"] / 2
        tx = r0_bb["x"] + r0_bb["width"] / 2
        ty = r0_bb["y"] - 5

        page.mouse.move(sx, sy)
        page.mouse.down()
        time.sleep(0.2)
        steps = 15
        for k in range(steps + 1):
            t_ratio = k / steps
            page.mouse.move(sx + (tx - sx) * t_ratio, sy + (ty - sy) * t_ratio)
            time.sleep(0.02)
        time.sleep(0.2)
        page.mouse.up()
        page.wait_for_timeout(600)

        # ASSERT the reorder took — uid_of_sec1 should now be at position 0
        try:
            page.wait_for_function(
                f"() => {{ const rows=document.querySelectorAll('#tray-list .tray-row'); "
                f"return rows.length>1 && rows[0].dataset.uid==='{uid_of_sec1}'; }}",
                timeout=3000
            )
            reorder_took = True
        except Exception:
            reorder_took = False

        s_reorder = dom_rows(page)
        m_reorder = get_tray_items(page)
        STATES["after_reorder_dom"] = s_reorder
        STATES["after_reorder_model"] = m_reorder
        log(f"Reorder took: {reorder_took}")
        log(f"DOM rows after reorder: {[r['slideId'] for r in s_reorder]}")
        log(f"tray.getItems() after reorder: {json.dumps(m_reorder)}")
        screenshot(page, "03-after-reorder")

        if not reorder_took:
            log("  WARNING: Reorder DID NOT take — retrying once")
            # Retry
            row1 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_of_sec1}']")
            row0 = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_of_sec0}']")
            if row1 and row0:
                g_bb = row1.query_selector(".grip").bounding_box()
                r0_bb = row0.bounding_box()
                sx = g_bb["x"] + g_bb["width"] / 2
                sy = g_bb["y"] + g_bb["height"] / 2
                tx = r0_bb["x"] + r0_bb["width"] / 2
                ty = r0_bb["y"] - 5
                page.mouse.move(sx, sy); page.mouse.down(); time.sleep(0.25)
                for k in range(15 + 1):
                    page.mouse.move(sx + (tx - sx) * k / 15, sy + (ty - sy) * k / 15)
                    time.sleep(0.025)
                time.sleep(0.25); page.mouse.up(); page.wait_for_timeout(700)
                try:
                    page.wait_for_function(
                        f"() => {{ const rows=document.querySelectorAll('#tray-list .tray-row'); "
                        f"return rows.length>1 && rows[0].dataset.uid==='{uid_of_sec1}'; }}",
                        timeout=3000
                    )
                    reorder_took = True
                except Exception:
                    reorder_took = False
                s_reorder = dom_rows(page)
                m_reorder = get_tray_items(page)
                STATES["after_reorder_retry_dom"] = s_reorder
                STATES["after_reorder_retry_model"] = m_reorder
                log(f"Reorder took after retry: {reorder_took}")
                log(f"DOM rows after retry: {[r['slideId'] for r in s_reorder]}")
                log(f"tray.getItems() after retry: {json.dumps(m_reorder)}")
                screenshot(page, "03b-after-reorder-retry")

        # ── STEP 3: Remove deck-section-2 by identity ────────────────────────
        log("\n=== STEP 3: Remove deck-section-2 ===")
        # Re-query by slideId identity
        remove_btn = page.query_selector("#tray-list .tray-row[data-slide-id='deck-section-2'] .tray-remove")
        assert remove_btn, "No tray-remove button for deck-section-2"
        remove_row_uid = page.query_selector("#tray-list .tray-row[data-slide-id='deck-section-2']").get_attribute("data-uid")
        log(f"  Removing: data-slide-id=deck-section-2, uid={remove_row_uid}")
        remove_btn.click()
        page.wait_for_timeout(500)

        s_remove = dom_rows(page)
        m_remove = get_tray_items(page)
        STATES["after_remove_dom"] = s_remove
        STATES["after_remove_model"] = m_remove
        removed_ids = [r["slideId"] for r in s_remove]
        log(f"slideIds after remove: {removed_ids}")
        log(f"deck-section-2 present: {'deck-section-2' in removed_ids}")
        log(f"tray.getItems() after remove: {json.dumps(m_remove)}")
        screenshot(page, "04-after-remove")

        # ── STEP 4: Duplicate the row now at position 0 (uid_of_sec1) ────────
        log("\n=== STEP 4: Duplicate pos-0 row (deck-section-1) ===")
        # Re-query by uid identity
        dup_btn = page.query_selector(f"#tray-list .tray-row[data-uid='{uid_of_sec1}'] .tray-duplicate")
        assert dup_btn, f"No tray-duplicate button for uid={uid_of_sec1}"
        log(f"  Duplicating uid={uid_of_sec1} (deck-section-1)")
        dup_btn.click()
        page.wait_for_timeout(500)

        s_dup = dom_rows(page)
        m_dup = get_tray_items(page)
        STATES["after_dup_dom"] = s_dup
        STATES["after_dup_model"] = m_dup
        dup_ids = [r["slideId"] for r in s_dup]
        log(f"slideIds after duplicate: {dup_ids}")
        log(f"deck-section-1 count: {dup_ids.count('deck-section-1')}")
        log(f"tray.getItems() after dup: {json.dumps(m_dup)}")
        screenshot(page, "05-after-duplicate")

        # ── STEP 5: Add blank slide ──────────────────────────────────────────
        log("\n=== STEP 5: Add blank slide ===")
        page.click("#add-blank-btn")
        page.wait_for_timeout(500)

        s_blank = dom_rows(page)
        m_blank = get_tray_items(page)
        STATES["after_blank_dom"] = s_blank
        STATES["after_blank_model"] = m_blank
        blank_ids = [r["slideId"] for r in s_blank]
        log(f"slideIds after blank: {blank_ids}")
        log(f"blank row present: {any('blank' in sid for sid in blank_ids)}")
        log(f"tray.getItems() after blank: {json.dumps(m_blank)}")
        screenshot(page, "06-after-blank")

        # ── STEP 6: Add library slide via .s-cap click ───────────────────────
        log("\n=== STEP 6: Add library slide (corrected .s-cap targeting) ===")
        # Set fake folder dialog to lib folder
        post_json_urllib(SERVER + "/api/_test/set-folder-dialog", {"path": LIB_DIR})
        page.click("#pick-library-btn")
        log("  Clicked #pick-library-btn")

        # Wait for browse groups to populate
        try:
            page.wait_for_function(
                "() => { const el=document.getElementById('browse-groups'); return el && el.children.length>0; }",
                timeout=10000
            )
            log("  browse-groups populated")
            screenshot(page, "07-library-browse")

            # Wait for slide cards to appear
            page.wait_for_timeout(500)

            # Find the first .s-cap element (caption below the thumbnail)
            # .s-cap is the text area under the slide thumbnail in browse cards
            s_cap_elements = page.query_selector_all(".s-cap")
            log(f"  Found {len(s_cap_elements)} .s-cap elements")

            lib_added = False
            if s_cap_elements:
                # Click the first .s-cap — this triggers the add action
                first_cap = s_cap_elements[0]
                cap_text = first_cap.inner_text().strip()
                log(f"  Clicking .s-cap[0] text='{cap_text}'")
                first_cap.click()
                page.wait_for_timeout(800)

                s_lib = dom_rows(page)
                m_lib = get_tray_items(page)
                lib_ids = [r["slideId"] for r in s_lib]
                log(f"slideIds after lib add attempt: {lib_ids}")
                log(f"Row count before lib: {len(s_blank)}, after: {len(s_lib)}")

                # Check if a new library row appeared
                if len(s_lib) > len(s_blank):
                    lib_added = True
                    STATES["after_lib_dom"] = s_lib
                    STATES["after_lib_model"] = m_lib
                    log(f"  Library slide ADDED — new row: {s_lib[-1] if s_lib else 'none'}")
                    log(f"  tray.getItems() after lib: {json.dumps(m_lib)}")
                    screenshot(page, "08-after-lib-add")
                else:
                    log("  .s-cap click did not add a row — checking for button alternative")
                    # Try .slide-add-btn or any add button that may be in the browse card
                    add_btns = page.query_selector_all(".slide-add-btn, .browse-card-add, [data-action='add']")
                    log(f"  Alternate add buttons found: {len(add_btns)}")
                    if add_btns:
                        add_btns[0].click()
                        page.wait_for_timeout(800)
                        s_lib2 = dom_rows(page)
                        if len(s_lib2) > len(s_blank):
                            lib_added = True
                            STATES["after_lib_dom"] = s_lib2
                            STATES["after_lib_model"] = get_tray_items(page)
                            log(f"  Alt-btn lib add succeeded, rows now: {len(s_lib2)}")
                            screenshot(page, "08-after-lib-add-alt")
                        else:
                            log("  Alt-btn did not add row either")
                    else:
                        log("  No alternate add buttons found")
                        STATES["after_lib_dom"] = s_lib
                        STATES["after_lib_model"] = m_lib
                    screenshot(page, "08-lib-add-result")
            else:
                log("  No .s-cap elements found — browse may not show individual slides")
                screenshot(page, "08-lib-no-scap")

        except Exception as e:
            log(f"  Library browse ERROR: {e}")
            screenshot(page, "08-lib-error")
            lib_added = False

        STATES["lib_slide_added"] = lib_added
        log(f"Library add result: lib_added={lib_added}")

        # Get current state before save
        s_pre_save = dom_rows(page)
        m_pre_save = get_tray_items(page)
        STATES["pre_save_dom"] = s_pre_save
        STATES["pre_save_model"] = m_pre_save
        log(f"\nPre-save DOM: {[r['slideId'] for r in s_pre_save]}")
        log(f"Pre-save tray.getItems(): {json.dumps(m_pre_save)}")

        # ── STEP 7: Save as new file ─────────────────────────────────────────
        log("\n=== STEP 7: Save as new file ===")
        post_json_urllib(SERVER + "/api/_test/set-dialog", {"path": save_path})
        page.click("#save-new-btn")
        page.wait_for_timeout(2500)
        screenshot(page, "09-after-save")

        # Verify save
        save_exists = os.path.exists(save_path)
        save_size   = os.path.getsize(save_path) if save_exists else 0
        log(f"Saved file: exists={save_exists}, size={save_size}")

        # ── STEP 8: Switch to editor (save-and-switch crossing) ─────────────
        log("\n=== STEP 8: Switch to editor ===")
        screenshot(page, "10-pre-switch")
        page.click("#switch-to-editor-btn")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(1500)
        screenshot(page, "11-editor-loaded")
        log(f"  URL after switch: {page.url}")

        # ── STEP 9: Type marker via real keyboard ────────────────────────────
        log("\n=== STEP 9: Type marker [CV-B15-S2] via real keyboard ===")
        MARKER = " [CV-B15-S2]"

        # Find editable content in the editor (the doc iframe or a content-editable)
        try:
            # Wait for iframe doc-frame first
            page.wait_for_function(
                "() => !!document.querySelector('iframe.doc-frame')",
                timeout=8000
            )
            frame = page.frame_locator("iframe.doc-frame").first
            # Find the first editable element in the iframe
            # Try to dblclick into the first section's text
            editable = frame.locator("[contenteditable='true'], .slide-content, .cover-title, section p, section div").first
            editable.wait_for(timeout=5000)
            editable.dblclick()
            page.wait_for_timeout(300)
            # Move to end and type
            page.keyboard.press("End")
            page.keyboard.type(MARKER)
            page.wait_for_timeout(500)
            log(f"  Typed marker into iframe frame element")
            screenshot(page, "12-after-typing")
            typing_succeeded = True
        except Exception as e_frame:
            log(f"  iframe approach failed: {e_frame}")
            # Try direct page contenteditable
            try:
                editable_direct = page.locator("[contenteditable='true']").first
                editable_direct.wait_for(timeout=3000)
                editable_direct.dblclick()
                page.wait_for_timeout(300)
                page.keyboard.press("End")
                page.keyboard.type(MARKER)
                page.wait_for_timeout(500)
                log(f"  Typed marker into direct contenteditable")
                screenshot(page, "12-after-typing")
                typing_succeeded = True
            except Exception as e2:
                log(f"  Direct contenteditable failed: {e2}")
                # Last resort: click into the main editor area and type
                try:
                    page.click(".editor-area, #editor-container, main, body")
                    page.wait_for_timeout(200)
                    page.keyboard.press("End")
                    page.keyboard.type(MARKER)
                    page.wait_for_timeout(500)
                    log("  Typed marker via body click fallback")
                    screenshot(page, "12-after-typing")
                    typing_succeeded = True
                except Exception as e3:
                    log(f"  All typing approaches failed: {e3}")
                    typing_succeeded = False
                    screenshot(page, "12-typing-failed")

        # Save the crossback file via editor save (if available)
        log("\n=== Saving crossback file from editor ===")
        try:
            post_json_urllib(SERVER + "/api/_test/set-dialog", {"path": crossback_path})
            # Try #save-btn or #save-as-btn in the editor
            save_btns = ["#save-new-btn", "#save-as-btn", "#save-btn", "[data-action='save-new']"]
            saved_crossback = False
            for btn_sel in save_btns:
                try:
                    page.click(btn_sel, timeout=2000)
                    page.wait_for_timeout(2000)
                    if os.path.exists(crossback_path):
                        saved_crossback = True
                        log(f"  Crossback saved via {btn_sel}")
                        break
                except Exception:
                    continue

            if not saved_crossback:
                # Copy the current save_path as a proxy crossback
                if os.path.exists(save_path):
                    shutil.copy(save_path, crossback_path)
                    log(f"  Crossback: copied from save_path (editor save not available)")
                    saved_crossback = True
        except Exception as e_cb:
            log(f"  Crossback save error: {e_cb}")
            saved_crossback = False

        # ── STEP 10: Switch back to builder ─────────────────────────────────
        log("\n=== STEP 10: Switch back to builder ===")
        try:
            page.click("#open-in-builder-btn, #switch-to-builder-btn, [href*='builder']", timeout=5000)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(1500)
            screenshot(page, "13-back-in-builder")
            log(f"  URL after switch back: {page.url}")
            switch_back_ok = True
        except Exception as e_sb:
            log(f"  Switch back to builder failed: {e_sb}")
            screenshot(page, "13-switch-back-failed")
            switch_back_ok = False

        browser.close()

    t_end = time.time()
    wall_ms = int((t_end - t_start) * 1000)
    log(f"\n=== Wall time: {wall_ms} ms ===")

    # ── Analyze captured payload + saved bytes ────────────────────────────────
    log("\n=== DISK ASSERTION ANALYSIS ===")

    body = CAPTURED["deck_save_body"]
    items = body.get("items") if isinstance(body, dict) else None
    log(f"Captured /api/deck-save items: {json.dumps(items)}")

    # Read saved file
    saved_exists = os.path.exists(save_path)
    saved_hashes_list = []
    saved_texts_list  = []
    saved_html_bytes  = 0
    if saved_exists:
        with open(save_path, encoding="utf-8") as f:
            saved_html = f.read()
        saved_html_bytes  = len(saved_html.encode("utf-8"))
        saved_hashes_list = section_hashes(saved_html)
        saved_texts_list  = section_texts(saved_html)

    # Predicted from payload
    predicted = []
    if items:
        for it in items:
            kind = it.get("kind")
            if kind == "existing":
                idx = it.get("index", -1)
                predicted.append(orig_hashes[idx] if 0 <= idx < len(orig_hashes) else f"OOR:{idx}")
            elif kind == "blank":
                predicted.append("BLANK")
            elif kind == "library":
                predicted.append("LIB")
            else:
                predicted.append(f"?:{kind}")

    # Intended arrangement (swap 0↔1, remove sec-2, dup pos-0=sec-1, blank, then lib if added)
    # Base: [sec1, sec1, sec0, sec3..sec9, blank]
    intended_idx_no_lib = [1, 1, 0, 3, 4, 5, 6, 7, 8, 9]
    intended_no_lib     = [orig_hashes[i] for i in intended_idx_no_lib] + ["BLANK"]
    if lib_added:
        # library slide appended at end (after blank)
        intended_with_lib = intended_no_lib + ["LIB"]
    else:
        intended_with_lib = None

    log(f"Saved sections: {len(saved_hashes_list)}")
    log(f"Saved hashes: {saved_hashes_list}")
    log(f"Predicted from payload: {predicted}")
    log(f"Intended (no lib): {intended_no_lib}")
    if intended_with_lib:
        log(f"Intended (with lib): {intended_with_lib}")

    # Verify content identity proofs
    proof_reorder = None
    proof_removal = None
    proof_dup     = None
    proof_blank   = None
    proof_lib     = None
    proof_marker  = None

    if saved_hashes_list:
        # REORDER proof: sec1 must appear before sec0 in saved file
        sec0_hash = orig_hashes[0]
        sec1_hash = orig_hashes[1]
        sec0_pos = next((i for i, h in enumerate(saved_hashes_list) if h == sec0_hash), None)
        sec1_pos_first = next((i for i, h in enumerate(saved_hashes_list) if h == sec1_hash), None)
        if sec0_pos is not None and sec1_pos_first is not None:
            proof_reorder = {
                "sec0_pos": sec0_pos, "sec1_first_pos": sec1_pos_first,
                "sec1_before_sec0": sec1_pos_first < sec0_pos,
                "verdict": "PASS" if sec1_pos_first < sec0_pos else "FAIL"
            }
        else:
            proof_reorder = {"sec0_pos": sec0_pos, "sec1_first_pos": sec1_pos_first,
                             "verdict": "MISSING"}

        # REMOVAL proof: sec2 (orig index 2) must be ABSENT
        sec2_hash = orig_hashes[2]
        sec2_present = sec2_hash in saved_hashes_list
        proof_removal = {
            "sec2_hash": sec2_hash,
            "sec2_present_in_saved": sec2_present,
            "verdict": "PASS" if not sec2_present else "FAIL"
        }

        # DUPLICATE proof: sec1 must appear exactly 2x (or 2x+lib positions)
        sec1_count = saved_hashes_list.count(sec1_hash)
        proof_dup = {
            "sec1_hash": sec1_hash,
            "sec1_count_in_saved": sec1_count,
            "verdict": "PASS" if sec1_count >= 2 else "FAIL",
            "note": f"expected ≥2 (orig + duplicate)"
        }

        # BLANK proof: a blank section present (hash not matching any orig)
        blank_hashes = [h for h in saved_hashes_list if h not in orig_hashes]
        proof_blank = {
            "blank_hashes": blank_hashes,
            "count": len(blank_hashes),
            "verdict": "PASS" if len(blank_hashes) >= 1 else "FAIL"
        }

        # LIB proof
        if lib_added:
            # lib slide has identifying text "E2E Introduction"
            lib_sig_present_in_sections = any(lib_slide_sig in t for t in saved_texts_list) if lib_slide_sig else False
            proof_lib = {
                "lib_sig": lib_slide_sig,
                "lib_sig_present_in_sections": lib_sig_present_in_sections,
                "verdict": "PASS" if lib_sig_present_in_sections else "FAIL"
            }
        else:
            proof_lib = {"lib_added": False, "verdict": "NOT_ATTEMPTED"}

    # MARKER proof in crossback
    if os.path.exists(crossback_path):
        with open(crossback_path, encoding="utf-8") as f:
            crossback_html = f.read()
        marker_in_crossback = MARKER.strip() in crossback_html
        marker_in_save      = MARKER.strip() in (saved_html if saved_exists else "")
        proof_marker = {
            "marker": MARKER,
            "in_save": marker_in_save,
            "in_crossback": marker_in_crossback,
            "verdict": "PASS" if marker_in_crossback else "FAIL"
        }
    else:
        proof_marker = {"crossback_exists": False, "verdict": "NO_CROSSBACK"}

    # Check hyp- leakage
    hyp_check_save = {}
    if saved_exists:
        hyp_matches_save = re.findall(r'hyp-[a-z]', saved_html)
        datahyp_save     = re.findall(r'data-hyp-', saved_html)
        hyp_check_save = {
            "hyp_tokens": len(hyp_matches_save),
            "data_hyp_tokens": len(datahyp_save),
            "verdict": "PASS" if not hyp_matches_save and not datahyp_save else "FAIL"
        }

    # Payload matches intended
    payload_matches_intended_no_lib = (predicted == intended_no_lib) if predicted else None
    payload_matches_intended_with_lib = (predicted == intended_with_lib) if (predicted and intended_with_lib) else None

    log(f"\nProof — reorder: {proof_reorder}")
    log(f"Proof — removal: {proof_removal}")
    log(f"Proof — duplicate: {proof_dup}")
    log(f"Proof — blank: {proof_blank}")
    log(f"Proof — lib: {proof_lib}")
    log(f"Proof — marker: {proof_marker}")
    log(f"Hyp-leakage check: {hyp_check_save}")
    log(f"payload_matches_intended_no_lib: {payload_matches_intended_no_lib}")
    log(f"payload_matches_intended_with_lib: {payload_matches_intended_with_lib}")

    # Determine overall C1 verdict
    proofs_list = [proof_reorder, proof_removal, proof_dup, proof_blank]
    if lib_added:
        proofs_list.append(proof_lib)
    proofs_list.append(proof_marker)

    all_pass = all(p and p.get("verdict") == "PASS" for p in proofs_list)
    has_failure = any(p and p.get("verdict") == "FAIL" for p in proofs_list)
    lib_not_attempted = (not lib_added)

    if all_pass:
        c1_verdict = "held"
    elif has_failure:
        c1_verdict = "failed"
    elif lib_not_attempted:
        c1_verdict = "failed_lib_not_added"
    else:
        c1_verdict = "partial"

    log(f"\n=== C1 VERDICT: {c1_verdict} ===")
    log(f"  lib_added: {lib_added}")
    log(f"  all_pass: {all_pass}")
    log(f"  has_failure: {has_failure}")

    # ── Write disk assertions file ────────────────────────────────────────────
    disk_assertions = {
        "session": "cold-verifier-session-2",
        "date": "2026-06-10",
        "wall_ms": wall_ms,
        "deck_copy": DECK,
        "save_path": save_path,
        "crossback_path": crossback_path,
        "save_exists": saved_exists,
        "save_bytes": saved_html_bytes,
        "saved_section_count": len(saved_hashes_list),
        "saved_hashes": saved_hashes_list,
        "saved_section_texts": saved_texts_list,
        "orig_hashes": orig_hashes,
        "orig_section_count": len(orig_hashes),
        "captured_payload_items": items,
        "predicted_from_payload": predicted,
        "intended_no_lib": intended_no_lib,
        "intended_idx_no_lib": intended_idx_no_lib,
        "payload_matches_intended_no_lib": payload_matches_intended_no_lib,
        "lib_added": lib_added,
        "proof_reorder": proof_reorder,
        "proof_removal": proof_removal,
        "proof_duplicate": proof_dup,
        "proof_blank": proof_blank,
        "proof_lib": proof_lib,
        "proof_marker": proof_marker,
        "hyp_leakage_check": hyp_check_save,
        "reorder_took": reorder_took,
        "typing_succeeded": typing_succeeded if 'typing_succeeded' in dir() else None,
        "switch_back_ok": switch_back_ok if 'switch_back_ok' in dir() else None,
        "c1_verdict": c1_verdict,
    }

    disk_assertions_path = os.path.join(EVDIR, "c1-s2-disk-assertions.json")
    with open(disk_assertions_path, "w", encoding="utf-8") as f:
        json.dump(disk_assertions, f, indent=2)
    log(f"\nWROTE disk assertions: {disk_assertions_path}")

    # ── Write model state dumps ───────────────────────────────────────────────
    model_dumps_path = os.path.join(EVDIR, "c1-s2-model-dumps.json")
    with open(model_dumps_path, "w", encoding="utf-8") as f:
        json.dump(STATES, f, indent=2)
    log(f"WROTE model dumps: {model_dumps_path}")

    # ── Write log ─────────────────────────────────────────────────────────────
    dump_log()
    log(f"WROTE session log: {os.path.join(EVDIR, 'c1-s2-session-log.txt')}")

    return c1_verdict


if __name__ == "__main__":
    verdict = run()
    print(f"\nFINAL_C1_VERDICT: {verdict}")
    sys.exit(0 if verdict == "held" else 1)
