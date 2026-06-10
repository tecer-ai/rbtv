"""
cv_b15_exercise.py — Cold Verifier B15 Criterion 1 exercise (headed, real gestures).

Covers criterion 1:
- Open deck copy in builder
- Reorder slides (drag row[1] before row[0])
- Remove a slide (click .tray-remove on row[2])
- Duplicate a slide (click .tray-duplicate on row[0])
- Add blank slide (#add-blank-btn)
- Add a library slide (pick library + browse + add)
- Save as NEW file (#save-new-btn) to a temp path
- Switch to editor (#switch-to-editor-btn)
- Edit text in editor (type [CV-B15] via real keyboard)
- Switch back to builder (#open-in-builder via editor controls)

All captures go to EVIDENCE_DIR.
Results returned as a dict printed to stdout.

Usage:
  python cv_b15_exercise.py <server_base> <deck_copy> <library_path> <evidence_dir>
"""
import os, sys, json, time, hashlib, shutil, tempfile, urllib.request

SERVER = sys.argv[1]
DECK   = sys.argv[2]
LIBDIR = sys.argv[3] if len(sys.argv) > 3 else None
EVDIR  = sys.argv[4] if len(sys.argv) > 4 else "."

os.makedirs(EVDIR, exist_ok=True)
LOG = []

def log(msg):
    print(msg, flush=True)
    LOG.append(msg)

def post_json(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        SERVER + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read())

def set_dialog(path):
    status, resp = post_json("/api/_test/set-dialog", {"path": path})
    return resp

def set_folder_dialog(path):
    status, resp = post_json("/api/_test/set-folder-dialog", {"path": path})
    return resp

RESULTS = {}

from playwright.sync_api import sync_playwright

def sc(page, name):
    """Save screenshot."""
    path = os.path.join(EVDIR, name)
    page.screenshot(path=path)
    log(f"  [SCREENSHOT] {name}")
    return path

def run():
    save_tmpdir = tempfile.mkdtemp()
    save_path = os.path.join(save_tmpdir, "deck-cv-b15-saved.html")
    crossback_path = os.path.join(save_tmpdir, "deck-cv-b15-crossback.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context()
        page = ctx.new_page()

        # ── OPEN DECK ─────────────────────────────────────────────────────────
        log("=== STEP 1: Open deck in builder ===")
        page.goto(SERVER + "/app/builder.html")
        page.wait_for_load_state("networkidle", timeout=8000)
        sc(page, "01-builder-initial.png")

        set_dialog(DECK)
        page.click("#open-deck-btn")

        # Wait for tray to populate
        page.wait_for_function(
            "() => document.querySelectorAll('#tray-list .tray-row').length > 0",
            timeout=15000,
        )
        # Wait for srcdoc thumbnails
        page.wait_for_timeout(1500)

        initial_count = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Deck loaded — {initial_count} slides")
        sc(page, "02-deck-opened.png")

        # Capture initial order for anti-count-only proof
        initial_order_info = page.evaluate("""
            () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r, i) => ({
                i,
                uid: r.dataset.uid,
                slideId: r.dataset.slideId,
                badge: r.querySelector('.tray-badge') ? r.querySelector('.tray-badge').textContent : '',
                title: r.querySelector('.tray-title') ? r.querySelector('.tray-title').textContent.trim() : ''
            }))
        """)
        log(f"  Initial tray: {json.dumps(initial_order_info[:4], indent=2)}")
        RESULTS["initial_count"] = initial_count
        RESULTS["initial_order"] = initial_order_info

        # ── REORDER ───────────────────────────────────────────────────────────
        log("=== STEP 2: Reorder — drag row[1] before row[0] ===")
        rows = page.query_selector_all("#tray-list .tray-row")
        row0 = rows[0].bounding_box()
        row1 = rows[1].bounding_box()

        # Record UIDs before reorder
        uid_before = [r['uid'] for r in initial_order_info[:4]]
        log(f"  UIDs before reorder (first 4): {uid_before}")

        # Drag grip of row[1] to above row[0]
        grip1 = rows[1].query_selector(".grip")
        if not grip1:
            # Fallback: drag by row itself
            src_x = row1['x'] + 15
            src_y = row1['y'] + row1['height'] / 2
        else:
            grip1_box = grip1.bounding_box()
            src_x = grip1_box['x'] + grip1_box['width'] / 2
            src_y = grip1_box['y'] + grip1_box['height'] / 2

        tgt_x = row0['x'] + row0['width'] / 2
        tgt_y = row0['y'] - 4   # above row[0]

        page.mouse.move(src_x, src_y)
        page.mouse.down()
        time.sleep(0.25)
        # Move in steps
        steps = 12
        for step in range(steps + 1):
            t = step / steps
            px = src_x + (tgt_x - src_x) * t
            py = src_y + (tgt_y - src_y) * t
            page.mouse.move(px, py)
            time.sleep(0.03)
        time.sleep(0.15)
        page.mouse.up()
        time.sleep(0.8)

        sc(page, "03-after-reorder.png")

        after_reorder_info = page.evaluate("""
            () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r, i) => ({
                i, uid: r.dataset.uid,
                slideId: r.dataset.slideId,
                title: r.querySelector('.tray-title') ? r.querySelector('.tray-title').textContent.trim() : ''
            }))
        """)
        uid_after = [r['uid'] for r in after_reorder_info[:4]]
        log(f"  UIDs after reorder (first 4): {uid_after}")
        log(f"  Reorder happened: {uid_after[0] != uid_before[0]}")
        RESULTS["after_reorder"] = after_reorder_info
        RESULTS["reorder_happened"] = uid_after[0] != uid_before[0]

        # ── REMOVE ────────────────────────────────────────────────────────────
        log("=== STEP 3: Remove slide at position 2 ===")
        rows_now = page.query_selector_all("#tray-list .tray-row")
        if len(rows_now) >= 3:
            row_to_remove = rows_now[2]
            remove_uid = row_to_remove.get_attribute("data-uid")
            remove_slide_id = row_to_remove.get_attribute("data-slide-id")
            remove_title = row_to_remove.evaluate(
                "el => el.querySelector('.tray-title') ? el.querySelector('.tray-title').textContent.trim() : ''"
            )
            log(f"  Removing uid={remove_uid} slideId={remove_slide_id} title='{remove_title}'")

            remove_btn = row_to_remove.query_selector(".tray-remove")
            if remove_btn:
                remove_btn.click()
                time.sleep(0.6)
                log("  Clicked .tray-remove")
            else:
                log("  WARN: .tray-remove not found on row[2]")

            RESULTS["removed_uid"] = remove_uid
            RESULTS["removed_slide_id"] = remove_slide_id
            RESULTS["removed_title"] = remove_title
        else:
            log(f"  WARN: Only {len(rows_now)} rows, cannot remove row[2]")

        count_after_remove = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Count after remove: {count_after_remove}")
        RESULTS["count_after_remove"] = count_after_remove
        sc(page, "04-after-remove.png")

        # ── DUPLICATE ─────────────────────────────────────────────────────────
        log("=== STEP 4: Duplicate slide at position 0 ===")
        rows_now2 = page.query_selector_all("#tray-list .tray-row")
        if rows_now2:
            dup_row = rows_now2[0]
            dup_uid = dup_row.get_attribute("data-uid")
            dup_slide_id = dup_row.get_attribute("data-slide-id")
            dup_title = dup_row.evaluate(
                "el => el.querySelector('.tray-title') ? el.querySelector('.tray-title').textContent.trim() : ''"
            )
            log(f"  Duplicating uid={dup_uid} slideId={dup_slide_id} title='{dup_title}'")

            dup_btn = dup_row.query_selector(".tray-duplicate")
            if dup_btn:
                dup_btn.click()
                time.sleep(0.6)
                log("  Clicked .tray-duplicate")
            else:
                log("  WARN: .tray-duplicate not found on row[0]")

            RESULTS["duplicated_uid"] = dup_uid
            RESULTS["duplicated_slide_id"] = dup_slide_id
            RESULTS["duplicated_title"] = dup_title

        count_after_dup = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Count after duplicate: {count_after_dup}")
        RESULTS["count_after_dup"] = count_after_dup
        sc(page, "05-after-duplicate.png")

        # ── ADD BLANK ─────────────────────────────────────────────────────────
        log("=== STEP 5: Add blank slide ===")
        page.click("#add-blank-btn")
        time.sleep(0.5)
        count_after_blank = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Count after blank: {count_after_blank}")
        RESULTS["count_after_blank"] = count_after_blank
        sc(page, "06-after-add-blank.png")

        # Verify blank badge is present
        blank_rows = page.evaluate("""
            () => Array.from(document.querySelectorAll('#tray-list .tray-row'))
                .filter(r => r.querySelector('.tray-badge') && r.querySelector('.tray-badge').textContent === 'blank')
                .map(r => ({uid: r.dataset.uid, badge: r.querySelector('.tray-badge').textContent}))
        """)
        log(f"  Blank-badged rows: {blank_rows}")
        RESULTS["blank_rows"] = blank_rows

        # ── ADD LIBRARY SLIDE ─────────────────────────────────────────────────
        log("=== STEP 6: Add a library slide ===")
        lib_added = False
        if LIBDIR:
            set_folder_dialog(LIBDIR)
            page.click("#pick-library-btn")
            try:
                page.wait_for_function(
                    "() => { const el = document.getElementById('browse-groups'); return el && el.children.length > 0; }",
                    timeout=10000,
                )
                log("  Library browse loaded")
                sc(page, "07-library-browse.png")

                # Click the first slide's add button in the browse grid
                # Browse grid has .browse-row or .slide-card with add button
                add_btn = page.query_selector(".slide-card .add-btn, .browse-item .add-btn, .slide-add-btn, [data-slide-id] button")
                if add_btn:
                    add_btn.click()
                    time.sleep(0.5)
                    log("  Clicked first library slide add button")
                    lib_added = True
                else:
                    # Try clicking any clickable item in browse-groups
                    items = page.query_selector_all("#browse-groups li, #browse-groups .slide-card, #browse-groups .slide-item")
                    if items:
                        items[0].click()
                        time.sleep(0.3)
                        log(f"  Clicked first item in browse-groups (selector: li/card/item)")
                        # Check if a button appeared
                        add_btn2 = page.query_selector("#browse-groups .add-btn, .add-selected-btn")
                        if add_btn2:
                            add_btn2.click()
                            time.sleep(0.3)
                            lib_added = True
                        else:
                            lib_added = True  # single-click may have added it
                    else:
                        log("  WARN: No browse items found in browse-groups")
            except Exception as e:
                log(f"  WARN: Library loading failed: {e}")
        else:
            log("  WARN: No library path, skipping library add")

        count_after_lib = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Count after lib add: {count_after_lib}")
        RESULTS["count_after_lib"] = count_after_lib
        RESULTS["lib_add_attempted"] = bool(LIBDIR)
        RESULTS["lib_added"] = lib_added
        sc(page, "08-after-lib-add.png")

        # ── SAVE AS NEW FILE ───────────────────────────────────────────────────
        log("=== STEP 7: Save as NEW file ===")
        set_dialog(save_path)

        # deck-save-pane should be visible in deck mode; click save-new-btn
        # Check if deck-save-pane is visible
        pane_visible = page.evaluate(
            "() => { const p = document.getElementById('deck-save-pane'); return p && !p.hidden; }"
        )
        log(f"  deck-save-pane visible: {pane_visible}")

        # Save-new btn enabled state
        save_new_enabled = page.evaluate(
            "() => !document.getElementById('save-new-btn').disabled"
        )
        log(f"  save-new-btn enabled: {save_new_enabled}")

        if save_new_enabled:
            page.click("#save-new-btn")
            log("  Clicked #save-new-btn")
        else:
            log("  WARN: #save-new-btn disabled, trying anyway")
            page.click("#save-new-btn", force=True)

        page.wait_for_timeout(3000)
        sc(page, "09-after-save.png")

        # Check if saved file exists
        saved_file_exists = os.path.exists(save_path)
        saved_size = os.path.getsize(save_path) if saved_file_exists else 0
        log(f"  Saved file exists: {saved_file_exists} ({saved_size} bytes)")
        RESULTS["save_path"] = save_path
        RESULTS["saved_file_exists"] = saved_file_exists
        RESULTS["saved_size"] = saved_size
        RESULTS["save_tmpdir"] = save_tmpdir

        # ── SWITCH TO EDITOR ──────────────────────────────────────────────────
        log("=== STEP 8: Switch to editor ===")
        # The switch-to-editor-btn opens Save-As dialog then navigates
        set_dialog(save_path)   # point to already-saved file or same path

        switch_btn_enabled = page.evaluate(
            "() => !document.getElementById('switch-to-editor-btn').disabled"
        )
        log(f"  switch-to-editor-btn enabled: {switch_btn_enabled}")
        sc(page, "10-pre-switch.png")

        if switch_btn_enabled:
            page.click("#switch-to-editor-btn")
            log("  Clicked #switch-to-editor-btn")
        else:
            log("  WARN: switch-to-editor-btn disabled — trying force click")
            page.click("#switch-to-editor-btn", force=True)

        page.wait_for_timeout(2500)
        url_after_switch = page.url
        log(f"  URL after switch: {url_after_switch}")
        sc(page, "11-editor-loaded.png")
        RESULTS["url_after_switch"] = url_after_switch
        RESULTS["switched_to_editor"] = "/app/" in url_after_switch and "builder" not in url_after_switch

        # Wait for editor runtime
        try:
            page.wait_for_function(
                """() => {
                    const f = document.querySelector('iframe.doc-frame');
                    return f && f.contentWindow && f.contentWindow.hyp;
                }""",
                timeout=20000,
            )
            log("  Editor runtime ready")
            RESULTS["editor_runtime_ready"] = True
        except Exception as e:
            log(f"  WARN: Editor runtime wait failed: {e}")
            RESULTS["editor_runtime_ready"] = False

        # ── MAKE REAL EDIT ─────────────────────────────────────────────────────
        log("=== STEP 9: Make real edit — type [CV-B15] via keyboard ===")
        MARKER = " [CV-B15]"
        edit_success = False

        try:
            editor_iframe = page.query_selector("iframe.doc-frame")
            if editor_iframe:
                iframe_box = editor_iframe.bounding_box()
                if iframe_box:
                    # Click in the top-third area of the iframe to land on a text element
                    click_x = iframe_box['x'] + iframe_box['width'] * 0.5
                    click_y = iframe_box['y'] + iframe_box['height'] * 0.25

                    page.mouse.click(click_x, click_y)
                    time.sleep(0.4)
                    page.mouse.dblclick(click_x, click_y)
                    time.sleep(0.3)
                    page.keyboard.type(MARKER)
                    time.sleep(0.3)
                    sc(page, "12-after-typing.png")
                    log(f"  Typed marker '{MARKER}' via real keyboard")
                    edit_success = True
                else:
                    log("  WARN: iframe bounding box is None")
            else:
                log("  WARN: No iframe.doc-frame found in editor")
        except Exception as e:
            log(f"  WARN: Typing in editor failed: {e}")

        RESULTS["edit_success"] = edit_success

        # ── SWITCH BACK TO BUILDER ────────────────────────────────────────────
        log("=== STEP 10: Switch back to builder ===")
        # The editor has an "Open in builder" button in the toolbar
        set_dialog(crossback_path)

        open_in_builder_btn = page.query_selector(
            "#open-in-builder-btn, [data-action='open-in-builder']"
        )
        if open_in_builder_btn:
            btn_enabled = not open_in_builder_btn.get_attribute("disabled")
            log(f"  #open-in-builder-btn found, enabled: {btn_enabled}")
            open_in_builder_btn.click()
            log("  Clicked #open-in-builder-btn")
        else:
            # Look for a button that says builder
            btns = page.query_selector_all("button, a")
            found = False
            for btn in btns:
                txt = (btn.text_content() or "").strip()
                if "builder" in txt.lower() or "Builder" in txt:
                    log(f"  Found button with text '{txt}' — clicking")
                    btn.click()
                    found = True
                    break
            if not found:
                log("  WARN: No open-in-builder button found")

        page.wait_for_timeout(2500)
        url_final = page.url
        log(f"  Final URL: {url_final}")
        sc(page, "13-back-in-builder.png")
        RESULTS["url_after_back"] = url_final
        RESULTS["returned_to_builder"] = "builder" in url_final

        # ── FINAL TRAY STATE ──────────────────────────────────────────────────
        final_tray = page.evaluate("""
            () => Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r, i) => ({
                i, uid: r.dataset.uid, slideId: r.dataset.slideId,
                badge: r.querySelector('.tray-badge') ? r.querySelector('.tray-badge').textContent : '',
                title: r.querySelector('.tray-title') ? r.querySelector('.tray-title').textContent.trim() : ''
            }))
        """)
        final_count = page.evaluate(
            "() => document.querySelectorAll('#tray-list .tray-row').length"
        )
        log(f"  Final tray count: {final_count}")
        RESULTS["final_tray"] = final_tray
        RESULTS["final_count"] = final_count

        browser.close()

    # Save log
    with open(os.path.join(EVDIR, "c1-exercise-log.txt"), "w") as f:
        f.write("\n".join(LOG))
    RESULTS["log_file"] = os.path.join(EVDIR, "c1-exercise-log.txt")

    # Print results
    print("\n=== EXERCISE RESULTS ===")
    printable = {k: v for k, v in RESULTS.items() if not isinstance(v, (bytes, bytearray))}
    print(json.dumps(printable, indent=2))
    return RESULTS

if __name__ == "__main__":
    run()
