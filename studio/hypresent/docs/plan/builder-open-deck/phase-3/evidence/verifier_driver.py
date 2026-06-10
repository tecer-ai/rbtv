"""
Cold-verifier Playwright driver — p3-checkpoint (B10).

Exercises ALL SIX contract criteria independently.
Must be run from the evidence directory OR with the REPO env var set.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

EVIDENCE_DIR = pathlib.Path(__file__).resolve().parent
APP_ROOT = EVIDENCE_DIR.parents[5]  # studio/hypresent/
FIXTURE = APP_ROOT / "tecer-gsmm-introduction.html"
BUILDER_LIB = APP_ROOT / "tests" / "e2e" / "fixtures" / "builder-lib"

PORT = 19999  # use a unique port to avoid conflicts

BASE_URL = f"http://127.0.0.1:{PORT}"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def sha256_file(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def set_fake_dialog(path_or_none):
    return post_json("/api/_test/set-dialog", {"path": path_or_none})


def set_fake_folder(path_or_none):
    return post_json("/api/_test/set-folder-dialog", {"path": path_or_none})


def start_server():
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(PORT)],
        cwd=str(APP_ROOT), env=env,
    )
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE_URL + "/app/", timeout=1):
                print(f"[server] UP on {BASE_URL}")
                return proc
        except Exception:
            time.sleep(0.15)
    proc.terminate()
    raise RuntimeError(f"Server did not start on {PORT}")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def wait_runtime_ready(page, timeout=15000):
    page.wait_for_function(
        """() => {
            const f = document.querySelector('iframe.doc-frame');
            return f && f.contentWindow && f.contentWindow.hyp;
        }""",
        timeout=timeout,
    )


def wait_tray_loaded(page, min_items=1, timeout=10000):
    """Wait until the tray has at least min_items rows."""
    page.wait_for_function(
        f"""() => {{
            const rows = document.querySelectorAll('#tray-list .tray-row');
            return rows.length >= {min_items};
        }}""",
        timeout=timeout,
    )


def get_tray_titles(page):
    return page.evaluate("""() => {
        const rows = document.querySelectorAll('#tray-list .tray-row');
        return Array.from(rows).map(r => {
            const t = r.querySelector('.tray-title');
            return t ? t.textContent.trim() : '';
        });
    }""")


def get_tray_uids(page):
    return page.evaluate("""() => {
        return Array.from(document.querySelectorAll('#tray-list .tray-row'))
            .map(r => r.dataset.uid);
    }""")


def get_tray_slide_ids(page):
    return page.evaluate("""() => {
        return Array.from(document.querySelectorAll('#tray-list .tray-row'))
            .map(r => r.dataset.slideId);
    }""")


def get_tray_badges(page):
    return page.evaluate("""() => {
        return Array.from(document.querySelectorAll('#tray-list .tray-row'))
            .map(r => {
                const b = r.querySelector('.tray-badge');
                return b ? b.textContent.trim() : '';
            });
    }""")


def screenshot(page, name):
    p = EVIDENCE_DIR / name
    page.screenshot(path=str(p))
    print(f"  [screenshot] {p.name}")
    return str(p)


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 1 — Full loop at the floor
# ──────────────────────────────────────────────────────────────────────────────

def criterion_1(page, tmpdir):
    print("\n=== CRITERION 1: Full loop at the floor ===")
    results = {}

    # Make a temp copy of the owner deck
    deck_copy = str(pathlib.Path(tmpdir) / "deck_c1.html")
    shutil.copy(str(FIXTURE), deck_copy)
    print(f"  Deck copy: {deck_copy}")

    # Navigate to builder (headed mode already, server up)
    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")

    # Open deck via dialog seam
    set_fake_dialog(deck_copy)
    page.click("#open-deck-btn")
    wait_tray_loaded(page, min_items=1)
    time.sleep(0.8)  # let thumbnails settle

    initial_titles = get_tray_titles(page)
    initial_slide_ids = get_tray_slide_ids(page)
    print(f"  Initial tray: {len(initial_titles)} slides")
    results["initial_count"] = len(initial_titles)

    ss_before = screenshot(page, "c1_01_initial_tray.png")
    results["ss_before"] = ss_before

    # Must have at least 3 slides to do all operations
    if len(initial_titles) < 3:
        results["verdict"] = "FAIL"
        results["reason"] = f"Deck has only {len(initial_titles)} slides — need ≥3 for full loop"
        return results

    # --- Reorder: drag slide 2 (idx 1) up to position 0 ---
    # Use keyboard approach: find tray rows and drag first->second
    rows_before_reorder = page.query_selector_all("#tray-list .tray-row")
    if len(rows_before_reorder) >= 2:
        row_0 = rows_before_reorder[0]
        row_1 = rows_before_reorder[1]
        # Drag row[1] above row[0]
        r0_box = row_0.bounding_box()
        r1_box = row_1.bounding_box()
        if r0_box and r1_box:
            page.mouse.move(r1_box["x"] + r1_box["width"] / 2, r1_box["y"] + r1_box["height"] / 2)
            page.mouse.down()
            time.sleep(0.1)
            page.mouse.move(r0_box["x"] + r0_box["width"] / 2, r0_box["y"] + 2, steps=10)
            time.sleep(0.2)
            page.mouse.up()
            time.sleep(0.4)

    titles_after_reorder = get_tray_titles(page)
    slide_ids_after_reorder = get_tray_slide_ids(page)
    print(f"  After reorder: {titles_after_reorder[:3]}")
    results["after_reorder_titles"] = titles_after_reorder

    # --- Remove slide at position 0 (click its remove btn) ---
    first_row = page.query_selector("#tray-list .tray-row")
    if first_row:
        remove_btn = first_row.query_selector(".tray-remove")
        if remove_btn:
            remove_btn.click()
            time.sleep(0.3)

    titles_after_remove = get_tray_titles(page)
    slide_ids_after_remove = get_tray_slide_ids(page)
    count_after_remove = len(titles_after_remove)
    print(f"  After remove: {count_after_remove} slides")
    results["after_remove_count"] = count_after_remove
    removed_was_first = titles_after_remove[0] != initial_titles[0] or count_after_remove == len(initial_titles) - 1

    # --- Duplicate slide at position 0 ---
    dup_rows = page.query_selector_all("#tray-list .tray-row")
    if len(dup_rows) >= 1:
        dup_btn = dup_rows[0].query_selector(".tray-duplicate")
        if dup_btn:
            dup_btn.click()
            time.sleep(0.3)

    titles_after_dup = get_tray_titles(page)
    slide_ids_after_dup = get_tray_slide_ids(page)
    count_after_dup = len(titles_after_dup)
    print(f"  After duplicate: {count_after_dup} slides")
    results["after_dup_count"] = count_after_dup

    # Check duplicate is present twice at positions 0 and 1
    dup_present_twice = count_after_dup > count_after_remove and slide_ids_after_dup[0] == slide_ids_after_dup[1] if count_after_dup >= 2 else False
    print(f"  Duplicate present twice: {dup_present_twice}")
    results["dup_present_twice"] = dup_present_twice

    # --- Add blank slide ---
    page.click("#add-blank-btn")
    time.sleep(0.3)
    titles_after_blank = get_tray_titles(page)
    badges_after_blank = get_tray_badges(page)
    count_after_blank = len(titles_after_blank)
    blank_present = any(b == 'blank' for b in badges_after_blank)
    print(f"  After blank: {count_after_blank} slides, blank badge present: {blank_present}")
    results["after_blank_count"] = count_after_blank
    results["blank_present"] = blank_present

    # --- Add a library slide ---
    # First pick a library
    lib_path = str(BUILDER_LIB)
    set_fake_folder(lib_path)
    page.click("#pick-library-btn")
    try:
        page.wait_for_function(
            """() => {
                const el = document.getElementById('browse-groups');
                return el && el.children.length > 0;
            }""",
            timeout=10000,
        )
    except Exception as e:
        print(f"  WARNING: library didn't load: {e}")

    time.sleep(0.5)
    # Click the first browse card to add it to tray
    # In deck mode we loaded the deck FIRST, which cleared the library state.
    # So we need to check: after picking a library, can we add a library slide?
    first_card = page.query_selector(".browse-card")
    lib_slide_added = False
    if first_card:
        first_card.click()
        time.sleep(0.3)
        titles_after_lib = get_tray_titles(page)
        badges_after_lib = get_tray_badges(page)
        lib_badge_present = any(b == 'lib' for b in badges_after_lib)
        count_after_lib = len(titles_after_lib)
        print(f"  After library slide add: {count_after_lib} slides, lib badge present: {lib_badge_present}")
        lib_slide_added = lib_badge_present
        results["lib_slide_added"] = lib_slide_added
    else:
        print("  WARNING: No browse cards found to add library slide")
        results["lib_slide_added"] = False
        titles_after_lib = titles_after_blank
        badges_after_lib = badges_after_blank
        count_after_lib = count_after_blank

    ss_restructured = screenshot(page, "c1_02_restructured_tray.png")
    results["ss_restructured"] = ss_restructured

    # --- Save to NEW file ---
    save_path = str(pathlib.Path(tmpdir) / "deck_c1_saved.html")
    set_fake_dialog(save_path)
    page.click("#save-new-btn")
    time.sleep(1.5)  # wait for save

    # Check status shows saved
    status_text = page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")
    print(f"  Save status: '{status_text}'")
    results["save_status"] = status_text
    save_ok = "Saved:" in status_text
    results["save_ok"] = save_ok
    file_exists = pathlib.Path(save_path).exists()
    results["file_exists"] = file_exists
    print(f"  Saved file exists: {file_exists}")

    if not file_exists:
        results["verdict"] = "FAIL"
        results["reason"] = "Save did not produce the file"
        return results

    # --- Reopen the saved file ---
    set_fake_dialog(save_path)
    page.click("#open-deck-btn")
    # Handle the "Replace current deck?" confirm dialog
    try:
        page.once("dialog", lambda d: d.accept())
    except Exception:
        pass
    # Wait for potential dialog
    time.sleep(0.5)

    # Try accepting any open dialog
    try:
        page.evaluate("() => { /* noop — dialog handler registered above */ }")
    except Exception:
        pass

    wait_tray_loaded(page, min_items=1)
    time.sleep(0.8)

    reopened_titles = get_tray_titles(page)
    reopened_badges = get_tray_badges(page)
    reopened_count = len(reopened_titles)
    print(f"  Reopened tray: {reopened_count} slides")
    print(f"  Reopened badges: {reopened_badges}")
    results["reopened_count"] = reopened_count

    ss_reopened = screenshot(page, "c1_03_reopened_tray.png")
    results["ss_reopened"] = ss_reopened

    # The tray after reopen shows deck sections (all 'deck' badge)
    # The blank and library slides we saved appear as 'deck' badges since they're now
    # existing sections in the saved file
    # Check the count matches what we saved

    # Count what we tried to save:
    expected_count = count_after_lib
    count_matches = reopened_count == expected_count
    print(f"  Expected {expected_count} slides, got {reopened_count}: {'OK' if count_matches else 'MISMATCH'}")
    results["count_matches"] = count_matches

    # Summary
    all_ops_ok = (
        count_after_remove == len(initial_titles) - 1 and  # removed 1
        count_after_dup == count_after_remove + 1 and      # duplicated 1
        blank_present and                                   # blank present
        save_ok and file_exists and                        # saved ok
        count_matches                                       # reopened matches
    )
    results["all_ops_ok"] = all_ops_ok

    if all_ops_ok:
        results["verdict"] = "PASS"
    else:
        issues = []
        if count_after_remove != len(initial_titles) - 1:
            issues.append(f"remove: expected {len(initial_titles)-1} got {count_after_remove}")
        if count_after_dup != count_after_remove + 1:
            issues.append(f"dup: expected {count_after_remove+1} got {count_after_dup}")
        if not blank_present:
            issues.append("blank not found in tray")
        if not save_ok or not file_exists:
            issues.append(f"save failed (status={status_text}, exists={file_exists})")
        if not count_matches:
            issues.append(f"reopen count mismatch: expected {expected_count} got {reopened_count}")
        results["verdict"] = "FAIL"
        results["reason"] = "; ".join(issues)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 2 — Overwrite path + chooser every time
# ──────────────────────────────────────────────────────────────────────────────

def criterion_2(page, tmpdir):
    print("\n=== CRITERION 2: Overwrite path + chooser every time ===")
    results = {}

    # Make a temp copy
    deck_copy = str(pathlib.Path(tmpdir) / "deck_c2.html")
    shutil.copy(str(FIXTURE), deck_copy)

    # Navigate fresh
    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")

    # Open deck
    set_fake_dialog(deck_copy)
    page.click("#open-deck-btn")
    wait_tray_loaded(page, min_items=1)
    time.sleep(0.5)

    # Verify save pane is visible (deck mode)
    save_new_btn = page.query_selector("#save-new-btn")
    save_overwrite_btn = page.query_selector("#save-overwrite-btn")
    deck_save_pane = page.query_selector("#deck-save-pane")

    pane_visible = deck_save_pane and not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    new_btn_exists = save_new_btn is not None
    overwrite_btn_exists = save_overwrite_btn is not None
    print(f"  Save pane visible: {pane_visible}")
    print(f"  New file btn: {new_btn_exists}, Overwrite btn: {overwrite_btn_exists}")
    results["pane_visible"] = pane_visible
    results["new_btn_exists"] = new_btn_exists
    results["overwrite_btn_exists"] = overwrite_btn_exists

    ss_save_pane = screenshot(page, "c2_01_save_pane.png")
    results["ss_save_pane"] = ss_save_pane

    # --- First overwrite ---
    orig_bytes = pathlib.Path(deck_copy).read_bytes()
    orig_size = len(orig_bytes)

    page.click("#save-overwrite-btn")
    time.sleep(1.5)

    status_1 = page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")
    print(f"  Overwrite 1 status: '{status_1}'")
    new_size_1 = len(pathlib.Path(deck_copy).read_bytes())
    overwrite_1_ok = "Saved:" in status_1
    results["overwrite_1_status"] = status_1
    results["overwrite_1_ok"] = overwrite_1_ok
    results["size_change_1"] = new_size_1 - orig_size

    ss_overwrite_1 = screenshot(page, "c2_02_after_overwrite_1.png")
    results["ss_overwrite_1"] = ss_overwrite_1

    # --- Second overwrite (checking chooser appears again — both buttons should still be there) ---
    # The contract says "chooser appears on EVERY save (no sticky default)".
    # The chooser = the two-button panel (new-file + overwrite).
    pane_still_visible = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    assemble_hidden = page.evaluate("() => document.querySelector('.assemble').hidden")
    print(f"  After first save: pane still visible: {pane_still_visible}, assemble hidden: {assemble_hidden}")
    results["pane_still_visible_after_1"] = pane_still_visible
    results["assemble_hidden"] = assemble_hidden

    page.click("#save-overwrite-btn")
    time.sleep(1.5)

    status_2 = page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")
    overwrite_2_ok = "Saved:" in status_2
    print(f"  Overwrite 2 status: '{status_2}'")
    results["overwrite_2_status"] = status_2
    results["overwrite_2_ok"] = overwrite_2_ok

    pane_still_visible_2 = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    results["pane_still_visible_after_2"] = pane_still_visible_2
    print(f"  After second save: pane still visible: {pane_still_visible_2}")

    ss_overwrite_2 = screenshot(page, "c2_03_after_overwrite_2.png")
    results["ss_overwrite_2"] = ss_overwrite_2

    # --- New file path (dialog injects a different path) ---
    new_path = str(pathlib.Path(tmpdir) / "deck_c2_new.html")
    set_fake_dialog(new_path)
    page.click("#save-new-btn")
    time.sleep(1.5)

    status_new = page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")
    new_file_ok = "Saved:" in status_new and pathlib.Path(new_path).exists()
    print(f"  New-file status: '{status_new}', file exists: {pathlib.Path(new_path).exists()}")
    results["new_file_status"] = status_new
    results["new_file_ok"] = new_file_ok

    # After new-file save, pane must STILL be visible (chooser every time)
    pane_visible_after_new = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    results["pane_visible_after_new"] = pane_visible_after_new
    print(f"  After new-file save: pane visible: {pane_visible_after_new}")

    ss_after_new = screenshot(page, "c2_04_after_new_file.png")
    results["ss_after_new"] = ss_after_new

    chooser_every_time = (pane_visible and pane_still_visible and pane_still_visible_2 and pane_visible_after_new)
    results["chooser_every_time"] = chooser_every_time

    all_ok = overwrite_1_ok and overwrite_2_ok and new_file_ok and chooser_every_time
    if all_ok:
        results["verdict"] = "PASS"
    else:
        issues = []
        if not overwrite_1_ok:
            issues.append(f"overwrite 1 failed: {status_1}")
        if not overwrite_2_ok:
            issues.append(f"overwrite 2 failed: {status_2}")
        if not new_file_ok:
            issues.append(f"new-file failed: {status_new}")
        if not chooser_every_time:
            issues.append("chooser not visible every time")
        results["verdict"] = "FAIL"
        results["reason"] = "; ".join(issues)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 3 — Saved output clean
# ──────────────────────────────────────────────────────────────────────────────

def criterion_3(page, tmpdir):
    print("\n=== CRITERION 3: Saved output clean ===")
    results = {}

    # Make a temp copy
    deck_copy = str(pathlib.Path(tmpdir) / "deck_c3_src.html")
    shutil.copy(str(FIXTURE), deck_copy)

    # Navigate fresh
    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")

    # Open deck
    set_fake_dialog(deck_copy)
    page.click("#open-deck-btn")
    wait_tray_loaded(page, min_items=1)
    time.sleep(0.5)

    # Pick library and add a library slide (to test asset copy and markup verbatim)
    lib_path = str(BUILDER_LIB)
    set_fake_folder(lib_path)
    page.click("#pick-library-btn")
    try:
        page.wait_for_function(
            """() => {
                const el = document.getElementById('browse-groups');
                return el && el.children.length > 0;
            }""",
            timeout=10000,
        )
    except Exception as e:
        print(f"  WARNING: library didn't load: {e}")
    time.sleep(0.5)

    # Add first library slide
    first_card = page.query_selector(".browse-card")
    lib_slide_id = None
    if first_card:
        lib_slide_id = first_card.get_attribute("data-slide-id")
        first_card.click()
        time.sleep(0.3)

    # Add blank slide too
    page.click("#add-blank-btn")
    time.sleep(0.3)

    # Save to new file
    save_path = str(pathlib.Path(tmpdir) / "deck_c3_saved.html")
    save_dir = pathlib.Path(tmpdir)
    set_fake_dialog(save_path)
    page.click("#save-new-btn")
    time.sleep(2.0)

    status_text = page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")
    print(f"  Save status: '{status_text}'")
    results["save_status"] = status_text

    if not pathlib.Path(save_path).exists():
        results["verdict"] = "FAIL"
        results["reason"] = "Saved file not found"
        return results

    saved_html = pathlib.Path(save_path).read_text(encoding="utf-8")
    saved_size = len(saved_html.encode("utf-8"))
    print(f"  Saved file size: {saved_size} bytes")
    results["saved_size"] = saved_size

    # --- Check for hyp- markers ---
    hyp_markers = re.findall(r'(?:hyp-|data-hyp-)[^\s"\'>/]+', saved_html)
    hyp_marker_count = len(hyp_markers)
    print(f"  hyp-/data-hyp-* tokens found: {hyp_marker_count}")
    if hyp_marker_count > 0:
        print(f"  Sample: {hyp_markers[:5]}")
    results["hyp_marker_count"] = hyp_marker_count
    results["hyp_markers_sample"] = hyp_markers[:10]
    no_hyp_markers = hyp_marker_count == 0

    # --- Check library slide markup verbatim ---
    lib_slide_verbatim = True
    if lib_slide_id:
        frag_path = BUILDER_LIB / "slides" / f"{lib_slide_id}.html"
        if frag_path.exists():
            frag_html = frag_path.read_text(encoding="utf-8").strip()
            # The fragment should appear in the saved file
            lib_slide_verbatim = frag_html in saved_html
            print(f"  Library slide fragment verbatim in output: {lib_slide_verbatim}")
            if not lib_slide_verbatim:
                # Try searching for first/last 100 chars
                frag_start = frag_html[:100]
                frag_end = frag_html[-100:]
                start_found = frag_start in saved_html
                end_found = frag_end in saved_html
                print(f"  Fragment start found: {start_found}, end found: {end_found}")
        else:
            print(f"  WARNING: fragment file not found at {frag_path}")
    results["lib_slide_verbatim"] = lib_slide_verbatim

    # --- Check referenced assets copied ---
    # Look for any library slide in saved html and check assets/ dir
    assets_dir = save_dir / "assets"
    asset_refs_in_saved = re.findall(r'(?:src|href)\s*=\s*["\']?(assets/[^"\'>\s]+)["\']?|url\(\s*["\']?(assets/[^"\'>\s]+)["\']?\s*\)', saved_html, re.IGNORECASE)
    flat_asset_refs = [m[0] or m[1] for m in asset_refs_in_saved]
    print(f"  Asset refs in saved output: {flat_asset_refs}")
    results["asset_refs_in_saved"] = flat_asset_refs

    if flat_asset_refs:
        assets_ok = True
        for ref in flat_asset_refs:
            asset_path = save_dir / ref
            exists = asset_path.exists()
            print(f"    {ref}: {'OK' if exists else 'MISSING'}")
            if not exists:
                assets_ok = False
        results["assets_ok"] = assets_ok
    else:
        results["assets_ok"] = True  # no assets to check (library may have no asset refs)
        print("  No asset refs to check (library slide has no assets)")

    # Write inspection output
    inspection_log = EVIDENCE_DIR / "c3_inspection.txt"
    with open(str(inspection_log), "w", encoding="utf-8") as f:
        f.write(f"Saved file: {save_path}\n")
        f.write(f"Size: {saved_size} bytes\n")
        f.write(f"\n--- hyp-/data-hyp-* tokens ({hyp_marker_count}) ---\n")
        for t in hyp_markers[:50]:
            f.write(f"  {t}\n")
        f.write(f"\n--- Asset refs ---\n")
        for r in flat_asset_refs:
            f.write(f"  {r}\n")
        f.write(f"\n--- Asset directory listing ---\n")
        if assets_dir.exists():
            for p in sorted(assets_dir.rglob("*")):
                f.write(f"  {p.relative_to(save_dir)}\n")
        else:
            f.write("  (no assets/ dir)\n")
    results["inspection_log"] = str(inspection_log)

    all_ok = no_hyp_markers and lib_slide_verbatim and results.get("assets_ok", True)
    if all_ok:
        results["verdict"] = "PASS"
    else:
        issues = []
        if not no_hyp_markers:
            issues.append(f"hyp-markers present: {hyp_markers[:5]}")
        if not lib_slide_verbatim:
            issues.append("library slide fragment not verbatim in output")
        if not results.get("assets_ok", True):
            issues.append("referenced assets missing from output dir")
        results["verdict"] = "FAIL"
        results["reason"] = "; ".join(issues)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 4 — Assemble-mode regression
# ──────────────────────────────────────────────────────────────────────────────

def criterion_4():
    print("\n=== CRITERION 4: Assemble-mode regression ===")
    results = {}

    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/e2e/test_pb4_tray_reorder.py",
         "tests/e2e/test_pb5_assemble_handoff.py",
         "-q", "--tb=short"],
        cwd=str(APP_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    wall_ms = int((time.time() - t0) * 1000)
    results["exit_code"] = proc.returncode
    results["wall_ms"] = wall_ms

    pytest_log = EVIDENCE_DIR / "c4_pytest_output.txt"
    with open(str(pytest_log), "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(proc.stdout)
        f.write("\n=== STDERR ===\n")
        f.write(proc.stderr)
    results["log_file"] = str(pytest_log)

    print(f"  Exit code: {proc.returncode}")
    print(f"  Wall time: {wall_ms}ms")
    # Print last 20 lines of stdout
    lines = proc.stdout.strip().split("\n")
    for line in lines[-20:]:
        print(f"  {line}")

    # Parse skipped count
    skipped_count = 0
    for line in lines:
        m = re.search(r'(\d+) skipped', line)
        if m:
            skipped_count = int(m.group(1))
    results["skipped_count"] = skipped_count

    if proc.returncode == 0:
        results["verdict"] = "PASS"
    else:
        results["verdict"] = "FAIL"
        results["reason"] = f"pytest exit {proc.returncode}"

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 5 — Owner-data safety
# ──────────────────────────────────────────────────────────────────────────────

OWNER_DECKS = [
    "tecer-gsmm-introduction.html",
    "tecer-gsmm-introduction-test.html",
    "tecer-gsmm-introduction-test-v2.html",
    "tecer-gsmm-introduction-test-v3.html",
]

BASELINE_HASHES = {
    "tecer-gsmm-introduction.html":          "5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae",
    "tecer-gsmm-introduction-test.html":     "c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0",
    "tecer-gsmm-introduction-test-v2.html":  "f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db",
    "tecer-gsmm-introduction-test-v3.html":  "93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a",
}


def criterion_5():
    print("\n=== CRITERION 5: Owner-data safety ===")
    results = {}

    hash_log = EVIDENCE_DIR / "c5_owner_hashes.txt"
    all_ok = True
    rows = []

    with open(str(hash_log), "w", encoding="utf-8") as f:
        f.write("Owner deck hash verification\n")
        f.write(f"Checked at: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n")
        for fname in OWNER_DECKS:
            p = APP_ROOT / fname
            if not p.exists():
                row = f"MISSING  {fname}"
                all_ok = False
            else:
                current_hash = sha256_file(p)
                expected = BASELINE_HASHES[fname]
                match = current_hash == expected
                status = "OK" if match else "CHANGED"
                if not match:
                    all_ok = False
                row = f"{status}  {current_hash}  {fname}  (expected: {expected[:16]}...)"
            rows.append(row)
            f.write(row + "\n")
            print(f"  {row}")

    results["hash_log"] = str(hash_log)
    results["all_unchanged"] = all_ok
    results["rows"] = rows

    if all_ok:
        results["verdict"] = "PASS"
    else:
        changed = [r for r in rows if not r.startswith("OK")]
        results["verdict"] = "FAIL"
        results["reason"] = "Owner decks modified: " + "; ".join(changed)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Criterion 6 — decisions.md audit
# ──────────────────────────────────────────────────────────────────────────────

def criterion_6():
    print("\n=== CRITERION 6: decisions.md audit ===")
    results = {}

    decisions_path = APP_ROOT / "docs" / "plan" / "builder-open-deck" / "decisions.md"
    if not decisions_path.exists():
        results["verdict"] = "FAIL"
        results["reason"] = "decisions.md not found"
        return results

    content = decisions_path.read_text(encoding="utf-8")
    audit_log = EVIDENCE_DIR / "c6_decisions_audit.txt"

    issues = []

    with open(str(audit_log), "w", encoding="utf-8") as f:
        f.write("decisions.md audit\n")
        f.write(f"File: {decisions_path}\n")
        f.write(f"Size: {len(content)} bytes\n\n")

        # Check for file-change lists patterns (e.g., "created X", "updated Y", "modified Z files")
        file_change_patterns = [
            (r'\bcreated\s+\d+\s+file', "file-creation count narrative"),
            (r'\bupdated\s+\d+\s+file', "file-update count narrative"),
            (r'\bmodified\s+\d+\s+file', "file-modified count narrative"),
            (r'\d+\s*→\s*\d+', "N→M count narrative"),
            (r'^\s*-\s*`[^`]+`\s*(?:created|updated|modified|added|deleted|removed)\s*$', "file-list entry", re.MULTILINE),
        ]

        f.write("=== Pattern checks ===\n")
        for pattern_args in file_change_patterns:
            if len(pattern_args) == 3:
                pat, desc, flags = pattern_args
                matches = re.findall(pat, content, flags)
            else:
                pat, desc = pattern_args
                matches = re.findall(pat, content, re.IGNORECASE)
            if matches:
                issues.append(f"Found '{desc}' patterns: {matches[:3]}")
                f.write(f"  VIOLATION [{desc}]: {matches[:3]}\n")
            else:
                f.write(f"  OK [{desc}]: no matches\n")

        # Check each entry in "Decisions and Discoveries" section has decision+rationale+scope shape
        f.write("\n=== Decisions and Discoveries section entries ===\n")
        # Find the section
        dd_match = re.search(r'## Decisions and Discoveries(.*?)(?=^## |\Z)', content, re.DOTALL | re.MULTILINE)
        if dd_match:
            dd_content = dd_match.group(1)
            # Find all sub-headings (entries)
            entries = re.findall(r'^### (.+?)$(.*?)(?=^### |\Z)', dd_content, re.MULTILINE | re.DOTALL)
            f.write(f"  Found {len(entries)} entries\n")
            for title, body in entries:
                has_decision = bool(re.search(r'\*\*Decision\*\*|\bDecision\b', body))
                has_rationale = bool(re.search(r'\*\*Rationale\*\*|\bRationale\b', body))
                has_scope = bool(re.search(r'\*\*Scope\*\*|\bScope\b', body))
                shaped_ok = has_decision and has_rationale and has_scope
                status = "OK" if shaped_ok else "MISSING FIELDS"
                f.write(f"  [{status}] {title.strip()}: D={has_decision} R={has_rationale} S={has_scope}\n")
                if not shaped_ok:
                    issues.append(f"Entry '{title.strip()}' missing: " +
                                  ", ".join(x for x, v in [("Decision", has_decision), ("Rationale", has_rationale), ("Scope", has_scope)] if not v))

        # Check that entries that WERE present before aren't rewritten
        # (We can only check current state — no git diff here — but check for obvious issues)
        # Check no prior entry seems to have been truncated (ADX-1, ADX-2, ADX-3 should all be present)
        expected_entries = ["ADX-2", "ADX-3", "ADX-1"]
        for entry_name in expected_entries:
            found = entry_name in content
            f.write(f"\n  Required entry '{entry_name}': {'PRESENT' if found else 'MISSING'}\n")
            if not found:
                issues.append(f"Expected entry '{entry_name}' not found")

        f.write(f"\n=== Summary ===\n")
        f.write(f"Issues found: {len(issues)}\n")
        for issue in issues:
            f.write(f"  - {issue}\n")

    results["audit_log"] = str(audit_log)
    results["issues"] = issues

    print(f"  Audit complete. Issues: {len(issues)}")
    for issue in issues:
        print(f"    - {issue}")

    if not issues:
        results["verdict"] = "PASS"
    else:
        results["verdict"] = "FAIL"
        results["reason"] = "; ".join(issues)

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    from playwright.sync_api import sync_playwright

    print(f"APP_ROOT: {APP_ROOT}")
    print(f"EVIDENCE_DIR: {EVIDENCE_DIR}")
    print(f"PORT: {PORT}")
    print(f"FIXTURE: {FIXTURE}")
    print(f"BUILDER_LIB: {BUILDER_LIB}")

    # Take owner-deck baseline hashes BEFORE any exercise
    print("\n--- Baseline hashes ---")
    baselines = {}
    for fname in OWNER_DECKS:
        p = APP_ROOT / fname
        if p.exists():
            baselines[fname] = sha256_file(p)
            print(f"  {fname}: {baselines[fname][:16]}...")

    # Temporary directory for all deck copies
    tmpdir = tempfile.mkdtemp(prefix="hyp_verifier_")
    print(f"\nTemp dir: {tmpdir}")

    all_results = {}

    # Criterion 4 first (pytest, no browser needed)
    t4_start = time.time()
    all_results["c4"] = criterion_4()
    all_results["c4"]["wall_ms_total"] = int((time.time() - t4_start) * 1000)

    # Criterion 5 and 6 (static checks, no browser)
    all_results["c5"] = criterion_5()
    all_results["c6"] = criterion_6()

    # Browser-based criteria 1, 2, 3
    server_proc = start_server()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=80)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            context.set_default_timeout(20000)

            # Criterion 1
            page1 = context.new_page()
            t1_start = time.time()
            all_results["c1"] = criterion_1(page1, tmpdir)
            all_results["c1"]["wall_ms"] = int((time.time() - t1_start) * 1000)
            page1.close()

            # Criterion 2
            page2 = context.new_page()
            t2_start = time.time()
            all_results["c2"] = criterion_2(page2, tmpdir)
            all_results["c2"]["wall_ms"] = int((time.time() - t2_start) * 1000)
            page2.close()

            # Criterion 3
            page3 = context.new_page()
            t3_start = time.time()
            all_results["c3"] = criterion_3(page3, tmpdir)
            all_results["c3"]["wall_ms"] = int((time.time() - t3_start) * 1000)
            page3.close()

            context.close()
            browser.close()

    finally:
        stop_server(server_proc)

    # Criterion 5: re-check after all exercise (post-exercise hash check)
    print("\n--- Post-exercise hash check ---")
    post_hashes = {}
    for fname in OWNER_DECKS:
        p = APP_ROOT / fname
        if p.exists():
            post_hashes[fname] = sha256_file(p)
    # Update c5 with post-exercise data
    all_results["c5"]["post_hashes_match"] = all(
        post_hashes.get(f) == baselines.get(f) for f in OWNER_DECKS
    )
    # Re-run c5 to get fresh verdict
    all_results["c5"] = criterion_5()

    # Write summary JSON
    summary_path = EVIDENCE_DIR / "c_all_results.json"
    with open(str(summary_path), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults written to: {summary_path}")

    # Print summary table
    print("\n" + "=" * 60)
    print("CRITERION | VERDICT")
    print("-" * 60)
    for cn in ["c1", "c2", "c3", "c4", "c5", "c6"]:
        r = all_results.get(cn, {})
        v = r.get("verdict", "NO_RESULT")
        reason = r.get("reason", "")
        print(f"  {cn.upper()}  | {v}  {reason}")
    print("=" * 60)

    return all_results


if __name__ == "__main__":
    main()
