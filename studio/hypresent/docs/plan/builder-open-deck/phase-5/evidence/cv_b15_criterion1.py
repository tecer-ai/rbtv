"""
cv_b15_criterion1.py — Cold Verifier B15 Criterion 1 exercise script.

ONE CONTINUOUS HEADED session on a real deck copy:
1. Open deck copy in the builder (via fake dialog)
2. Reorder slides (move slide 2 before slide 1)
3. Remove a slide (remove slide 3 from original order)
4. Duplicate a slide
5. Add a blank slide
6. Add a library slide
7. Save as a NEW file
8. Switch to editor (the save-and-switch crossing)
9. Make a real edit (type [CV-B15] into a slide's text via real keyboard)
10. Switch back to the builder

All evidence captured to:
  docs/plan/builder-open-deck/phase-5/evidence/
  (screenshots + saved file bytes check output)

Usage: python cv_b15_criterion1.py <server_base> <deck_copy_path> <library_path> <evidence_dir>
"""

import os
import sys
import json
import time
import hashlib
import shutil
import tempfile
import urllib.request

EVIDENCE_DIR = sys.argv[4] if len(sys.argv) > 4 else "."
SERVER_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9726"
DECK_COPY = sys.argv[2] if len(sys.argv) > 2 else None
LIBRARY_PATH = sys.argv[3] if len(sys.argv) > 3 else None

os.makedirs(EVIDENCE_DIR, exist_ok=True)

RESULTS = []

def log(msg):
    print(msg, flush=True)
    RESULTS.append(msg)

def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVER_BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

def set_fake_dialog(path_or_none):
    status, resp = post_json("/api/_test/set-dialog", {"path": path_or_none})
    log(f"  set-dialog -> {resp}")
    return resp

def set_fake_folder(path_or_none):
    status, resp = post_json("/api/_test/set-folder-dialog", {"path": path_or_none})
    log(f"  set-folder-dialog -> {resp}")
    return resp

from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
        context = browser.new_context()
        page = context.new_page()

        log("=== C1: Open deck copy in builder ===")

        # Set fake dialog to deck copy path
        set_fake_dialog(DECK_COPY)

        # Navigate to builder
        page.goto(SERVER_BASE + "/app/builder.html")
        page.wait_for_load_state("networkidle", timeout=10000)

        # Take initial screenshot
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-01-builder-initial.png"))
        log(f"  Screenshot: c1-01-builder-initial.png")

        # Click the open deck button (look for button in builder UI)
        # Wait for deck-open button to be visible
        page.wait_for_selector("#open-deck-btn", timeout=5000)
        page.click("#open-deck-btn")

        # Wait for tray to be populated
        page.wait_for_function(
            """() => {
                const tray = document.getElementById('tray');
                return tray && tray.querySelectorAll('.tray-row').length > 0;
            }""",
            timeout=15000,
        )

        # Capture slide count
        slide_count = page.evaluate(
            "() => document.getElementById('tray').querySelectorAll('.tray-row').length"
        )
        log(f"  Slides loaded: {slide_count}")

        # Take screenshot after deck open
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-02-deck-opened.png"))
        log("  Screenshot: c1-02-deck-opened.png")

        # Capture initial slide order (first 3 sections' identifying text from DOM)
        initial_order = page.evaluate("""
            () => {
                const rows = document.querySelectorAll('#tray .tray-row');
                return Array.from(rows).slice(0, 5).map((row, i) => {
                    const uid = row.dataset.uid || row.getAttribute('data-uid') || String(i);
                    const text = row.textContent.trim().slice(0, 60);
                    return {i, uid, text};
                });
            }
        """)
        log(f"  Initial tray order (first 5): {json.dumps(initial_order)}")

        # =====================================================================
        log("=== C1: Reorder — drag slide 2 before slide 1 ===")
        # Get positions of first two rows
        rows = page.query_selector_all("#tray .tray-row")
        if len(rows) >= 2:
            row0 = rows[0].bounding_box()
            row1 = rows[1].bounding_box()

            # Drag row1 handle above row0 (real mouse gesture)
            drag_handle_1 = page.query_selector_all("#tray .tray-row .drag-handle")
            if drag_handle_1 and len(drag_handle_1) >= 2:
                src = drag_handle_1[1].bounding_box()
                # Drag to just above row0
                page.mouse.move(src['x'] + src['width']/2, src['y'] + src['height']/2)
                page.mouse.down()
                time.sleep(0.3)
                page.mouse.move(row0['x'] + row0['width']/2, row0['y'] - 5, steps=10)
                time.sleep(0.3)
                page.mouse.up()
                time.sleep(0.5)
                log("  Drag gesture performed: row1 dragged above row0")
            else:
                # Try clicking reorder buttons if no drag handles
                log("  NOTE: Drag handles not found by .drag-handle selector, attempting alternate drag")
                # Try dragging the row itself
                src_box = rows[1].bounding_box()
                tgt_box = rows[0].bounding_box()
                page.mouse.move(src_box['x'] + 30, src_box['y'] + src_box['height']/2)
                page.mouse.down()
                time.sleep(0.3)
                page.mouse.move(tgt_box['x'] + 30, tgt_box['y'] - 5, steps=15)
                time.sleep(0.3)
                page.mouse.up()
                time.sleep(0.5)
                log("  Alternate drag gesture performed")

        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-03-after-reorder.png"))
        log("  Screenshot: c1-03-after-reorder.png")

        after_reorder = page.evaluate("""
            () => {
                const rows = document.querySelectorAll('#tray .tray-row');
                return Array.from(rows).slice(0, 3).map((row, i) => {
                    const uid = row.dataset.uid || row.getAttribute('data-uid') || String(i);
                    return {i, uid, text: row.textContent.trim().slice(0, 60)};
                });
            }
        """)
        log(f"  After reorder (first 3): {json.dumps(after_reorder)}")

        # =====================================================================
        log("=== C1: Remove slide (remove slide at position 2 — 0-indexed) ===")
        rows_after = page.query_selector_all("#tray .tray-row")
        if len(rows_after) >= 3:
            # Get the text of slide to remove for verification
            slide_to_remove_text = rows_after[2].evaluate(
                "el => el.textContent.trim().slice(0, 80)"
            )
            log(f"  Slide-to-remove text: '{slide_to_remove_text}'")

            # Find and click the remove button on row at index 2
            remove_btns = page.query_selector_all("#tray .tray-row .remove-btn")
            if remove_btns and len(remove_btns) >= 3:
                remove_btns[2].click()
                time.sleep(0.5)
                log("  Clicked remove button on row[2]")
            else:
                # Try right-click context menu or other remove mechanism
                log(f"  NOTE: .remove-btn not found ({len(remove_btns) if remove_btns else 0}), trying hover+button approach")
                rows_after[2].hover()
                time.sleep(0.3)
                remove_btn = rows_after[2].query_selector(".remove-btn, [data-action='remove'], button.delete")
                if remove_btn:
                    remove_btn.click()
                    time.sleep(0.5)
                    log("  Remove button found on hover, clicked")
                else:
                    log("  WARN: Could not find remove mechanism for slide[2]")

        new_count = page.evaluate(
            "() => document.getElementById('tray').querySelectorAll('.tray-row').length"
        )
        log(f"  Slide count after remove: {new_count}")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-04-after-remove.png"))
        log("  Screenshot: c1-04-after-remove.png")

        # =====================================================================
        log("=== C1: Duplicate slide (duplicate row at position 0) ===")
        rows_current = page.query_selector_all("#tray .tray-row")
        if rows_current:
            slide_to_dup_text = rows_current[0].evaluate(
                "el => el.textContent.trim().slice(0, 80)"
            )
            log(f"  Slide-to-duplicate text: '{slide_to_dup_text}'")

            dup_btns = page.query_selector_all("#tray .tray-row .dup-btn, #tray .tray-row .duplicate-btn")
            if dup_btns:
                dup_btns[0].click()
                time.sleep(0.5)
                log("  Clicked duplicate button on row[0]")
            else:
                # Hover to find
                rows_current[0].hover()
                time.sleep(0.3)
                dup_btn = rows_current[0].query_selector(".dup-btn, .duplicate-btn, [data-action='duplicate'], [title*='uplicate']")
                if dup_btn:
                    dup_btn.click()
                    time.sleep(0.5)
                    log("  Duplicate button found on hover, clicked")
                else:
                    log("  WARN: Could not find duplicate mechanism for slide[0]")

        count_after_dup = page.evaluate(
            "() => document.getElementById('tray').querySelectorAll('.tray-row').length"
        )
        log(f"  Slide count after duplicate: {count_after_dup}")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-05-after-duplicate.png"))
        log("  Screenshot: c1-05-after-duplicate.png")

        # =====================================================================
        log("=== C1: Add blank slide ===")
        blank_btn = page.query_selector("#add-blank-btn, [data-action='add-blank'], button[title*='blank'], button[title*='Blank']")
        if blank_btn:
            blank_btn.click()
            time.sleep(0.5)
            log("  Clicked add-blank button")
        else:
            # Try finding by text content
            btns = page.query_selector_all("button")
            for btn in btns:
                if "blank" in (btn.text_content() or "").lower():
                    btn.click()
                    time.sleep(0.5)
                    log(f"  Clicked button with 'blank' text: {btn.text_content()}")
                    break
            else:
                log("  WARN: Could not find add-blank button")

        count_after_blank = page.evaluate(
            "() => document.getElementById('tray').querySelectorAll('.tray-row').length"
        )
        log(f"  Slide count after add-blank: {count_after_blank}")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-06-after-add-blank.png"))
        log("  Screenshot: c1-06-after-add-blank.png")

        # =====================================================================
        log("=== C1: Add a library slide ===")
        if LIBRARY_PATH:
            set_fake_folder(LIBRARY_PATH)

            pick_lib_btn = page.query_selector("#pick-library-btn, [data-action='pick-library'], button[title*='library'], button[title*='Library']")
            if pick_lib_btn:
                pick_lib_btn.click()
                # Wait for browse groups to load
                page.wait_for_function(
                    """() => {
                        const el = document.getElementById('browse-groups');
                        return el && el.children.length > 0;
                    }""",
                    timeout=10000,
                )
                log("  Library loaded")
                page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-07-library-open.png"))
                log("  Screenshot: c1-07-library-open.png")

                # Click the first add slide button in the library browse pane
                add_slide_btn = page.query_selector(".browse-item .add-btn, .browse-row .add-btn, [data-action='add-slide']")
                if add_slide_btn:
                    add_slide_btn.click()
                    time.sleep(0.5)
                    log("  Clicked add slide from library")
                else:
                    # Try clicking any slide thumbnail in browse pane
                    slide_items = page.query_selector_all(".browse-item, .browse-row, .slide-thumb")
                    if slide_items:
                        slide_items[0].click()
                        time.sleep(0.3)
                        # May need to click add
                        add_btn = page.query_selector(".browse-item.selected .add-btn, #add-selected-btn, .browse-add-btn")
                        if add_btn:
                            add_btn.click()
                            time.sleep(0.3)
                            log("  Clicked add from browse pane selected item")
                        else:
                            slide_items[0].dblclick()
                            time.sleep(0.5)
                            log("  Double-clicked first browse item")
            else:
                log("  WARN: Could not find pick-library button")
        else:
            log("  WARN: No library path provided, skipping library add")

        count_after_lib = page.evaluate(
            "() => document.getElementById('tray').querySelectorAll('.tray-row').length"
        )
        log(f"  Slide count after library add: {count_after_lib}")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-08-after-lib-add.png"))
        log("  Screenshot: c1-08-after-lib-add.png")

        # =====================================================================
        log("=== C1: Save as NEW file ===")
        # Create the save target path in temp dir
        save_tmpdir = tempfile.mkdtemp()
        save_path = os.path.join(save_tmpdir, "deck-cv-b15-saved.html")

        # Set fake dialog to the save path
        set_fake_dialog(save_path)

        # Find and click "Save as" / "Save deck" button
        save_btn = page.query_selector("#save-deck-btn, #deck-save-btn, [data-action='save-deck'], button[title*='Save']")
        if save_btn:
            save_btn.click()
            time.sleep(0.5)
            log(f"  Clicked save button")
        else:
            # Try finding by text
            btns = page.query_selector_all("button")
            for btn in btns:
                txt = (btn.text_content() or "").lower()
                if "save" in txt and "switch" not in txt:
                    btn.click()
                    time.sleep(0.5)
                    log(f"  Clicked button with 'save' text: {btn.text_content()}")
                    break
            else:
                log("  WARN: Could not find save button")

        # Wait for possible save-mode dialog (new-file vs overwrite)
        page.wait_for_timeout(1000)

        # Check if a "new file" / "save as" option appeared
        new_file_btn = page.query_selector("#save-new-btn, #new-file-btn, [data-action='save-new'], button[title*='new']")
        if new_file_btn:
            new_file_btn.click()
            time.sleep(0.5)
            log("  Clicked 'new file' option")
        else:
            # Check if modal appeared
            modal_btns = page.query_selector_all(".modal button, .save-dialog button, dialog button")
            if modal_btns:
                for btn in modal_btns:
                    txt = (btn.text_content() or "").lower()
                    if "new" in txt or "save as" in txt or "file" in txt:
                        btn.click()
                        time.sleep(0.5)
                        log(f"  Clicked modal button: {btn.text_content()}")
                        break
                else:
                    modal_btns[0].click()
                    time.sleep(0.5)
                    log(f"  Clicked first modal button: {modal_btns[0].text_content()}")

        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-09-after-save.png"))
        log("  Screenshot: c1-09-after-save.png")

        # Check if saved file exists on disk
        if os.path.exists(save_path):
            log(f"  SAVED FILE EXISTS: {save_path}")
            with open(save_path, "rb") as f:
                saved_bytes = f.read()
            log(f"  Saved file size: {len(saved_bytes)} bytes")
            with open(os.path.join(EVIDENCE_DIR, "c1-saved-file-size.txt"), "w") as f:
                f.write(f"save_path: {save_path}\nsize_bytes: {len(saved_bytes)}\n")
        else:
            log(f"  WARN: Saved file NOT found at: {save_path}")
            # List tempdir
            log(f"  Tempdir contents: {os.listdir(save_tmpdir)}")
            save_path = None
            saved_bytes = None

        # =====================================================================
        log("=== C1: Switch to editor (save-and-switch crossing) ===")

        # If the deck was saved, we need to navigate to a different file
        # The save-and-switch button opens the saved deck in editor
        # Set fake dialog for any needed path
        if save_path:
            set_fake_dialog(save_path)

        # Find the "Switch to editor" / "Open in editor" button
        switch_btn = page.query_selector(
            "#switch-to-editor-btn, #open-in-editor-btn, #edit-in-editor-btn, "
            "[data-action='switch-to-editor'], [data-action='open-in-editor'], "
            "button[title*='editor'], button[title*='Editor']"
        )
        if switch_btn:
            switch_btn.click()
            log(f"  Clicked switch-to-editor button: {switch_btn.text_content()}")
        else:
            # Try text search
            btns = page.query_selector_all("button")
            for btn in btns:
                txt = (btn.text_content() or "").lower()
                if "editor" in txt or "switch" in txt:
                    btn.click()
                    log(f"  Clicked button with editor/switch text: {btn.text_content()}")
                    break
            else:
                log("  WARN: Could not find switch-to-editor button")

        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-10-switch-to-editor.png"))
        log("  Screenshot: c1-10-switch-to-editor.png")

        # Check if we navigated to editor (index.html or has iframe.doc-frame)
        current_url = page.url
        log(f"  Current URL after switch: {current_url}")

        # Wait for editor to load
        editor_frame = page.query_selector("iframe.doc-frame")
        if editor_frame:
            log("  Editor iframe found — waiting for runtime ready")
            try:
                page.wait_for_function(
                    """() => {
                        const f = document.querySelector('iframe.doc-frame');
                        return f && f.contentWindow && f.contentWindow.hyp;
                    }""",
                    timeout=20000,
                )
                log("  Editor runtime ready")
            except Exception as e:
                log(f"  WARN: Editor runtime timeout: {e}")

        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-11-editor-loaded.png"))
        log("  Screenshot: c1-11-editor-loaded.png")

        # =====================================================================
        log("=== C1: Make a real edit — type [CV-B15] via real keyboard ===")

        MARKER = " [CV-B15]"

        # Try to click on an editable element in the editor
        try:
            # Try to click inside the iframe editor area to position cursor
            editor_iframe = page.query_selector("iframe.doc-frame")
            if editor_iframe:
                iframe_content = page.frame_locator("iframe.doc-frame")

                # Wait for content to be ready
                page.wait_for_timeout(1000)

                # Try clicking on the first text element in the editor
                try:
                    # Click somewhere in the document
                    iframe_box = editor_iframe.bounding_box()
                    if iframe_box:
                        page.mouse.click(
                            iframe_box['x'] + iframe_box['width'] * 0.5,
                            iframe_box['y'] + iframe_box['height'] * 0.3
                        )
                        time.sleep(0.5)

                        # Try to get into edit mode (some editors need double-click)
                        page.mouse.dblclick(
                            iframe_box['x'] + iframe_box['width'] * 0.5,
                            iframe_box['y'] + iframe_box['height'] * 0.3
                        )
                        time.sleep(0.3)

                        # Type the marker
                        page.keyboard.type(MARKER)
                        time.sleep(0.3)
                        log(f"  Typed marker '{MARKER}' via real keyboard")
                        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-12-after-typing.png"))
                        log("  Screenshot: c1-12-after-typing.png")
                    else:
                        log("  WARN: Could not get iframe bounding box")
                except Exception as e:
                    log(f"  WARN: Click in editor failed: {e}")
            else:
                # Not in iframe-based editor — maybe a different approach
                log("  WARN: No editor iframe found — checking current page")
                page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-12-editor-state.png"))
                log("  Screenshot: c1-12-editor-state.png")
        except Exception as e:
            log(f"  WARN: Editor typing failed: {e}")

        # =====================================================================
        log("=== C1: Switch back to builder ===")

        # Find "Open in builder" button in the editor
        open_in_builder_btn = page.query_selector(
            "#open-in-builder-btn, #switch-to-builder-btn, "
            "[data-action='open-in-builder'], [data-action='switch-to-builder'], "
            "button[title*='builder'], button[title*='Builder']"
        )
        if open_in_builder_btn:
            # Set fake dialog for the Save-As that will happen
            if save_path:
                crossback_path = os.path.join(save_tmpdir, "deck-cv-b15-crossback.html")
                set_fake_dialog(crossback_path)
            open_in_builder_btn.click()
            log(f"  Clicked open-in-builder button: {open_in_builder_btn.text_content()}")
        else:
            btns = page.query_selector_all("button")
            for btn in btns:
                txt = (btn.text_content() or "").lower()
                if "builder" in txt:
                    if save_path:
                        crossback_path = os.path.join(save_tmpdir, "deck-cv-b15-crossback.html")
                        set_fake_dialog(crossback_path)
                    btn.click()
                    log(f"  Clicked button with 'builder' text: {btn.text_content()}")
                    break
            else:
                log("  WARN: Could not find open-in-builder button")
                crossback_path = None

        page.wait_for_timeout(2000)
        current_url_after = page.url
        log(f"  URL after switch-back: {current_url_after}")
        page.screenshot(path=os.path.join(EVIDENCE_DIR, "c1-13-back-in-builder.png"))
        log("  Screenshot: c1-13-back-in-builder.png")

        # Final log
        log("=== C1 EXERCISE COMPLETE ===")

        # Save results log
        with open(os.path.join(EVIDENCE_DIR, "c1-exercise-log.txt"), "w") as f:
            f.write("\n".join(RESULTS))
        log(f"  Log saved to: {EVIDENCE_DIR}/c1-exercise-log.txt")

        # Return key info for disk content checks
        return {
            "save_path": save_path,
            "save_tmpdir": save_tmpdir,
            "saved_bytes": saved_bytes,
            "initial_order": initial_order,
            "after_reorder": after_reorder,
            "slide_to_remove_text": slide_to_remove_text if 'slide_to_remove_text' in dir() else None,
        }

if __name__ == "__main__":
    result = run()
    # Write result info
    result_out = {k: v if not isinstance(v, bytes) else f"<{len(v)} bytes>"
                  for k, v in result.items()}
    print("\n=== RESULT ===")
    print(json.dumps(result_out, indent=2))
