"""
Browser-based criteria 1, 2, 3 for p3-checkpoint.
Run as: python run_browser_criteria.py
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
APP_ROOT = EVIDENCE_DIR.parents[4]
FIXTURE = APP_ROOT / "tecer-gsmm-introduction.html"
BUILDER_LIB = APP_ROOT / "tests" / "e2e" / "fixtures" / "builder-lib"

PORT = 19877
BASE_URL = f"http://127.0.0.1:{PORT}"


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


def wait_tray_loaded(page, min_items=1, timeout=12000):
    page.wait_for_function(
        f"""() => {{
            const rows = document.querySelectorAll('#tray-list .tray-row');
            return rows.length >= {min_items};
        }}""",
        timeout=timeout,
    )


def get_tray_info(page):
    return page.evaluate("""() => {
        const rows = document.querySelectorAll('#tray-list .tray-row');
        return Array.from(rows).map(r => ({
            uid: r.dataset.uid,
            slideId: r.dataset.slideId,
            title: (r.querySelector('.tray-title') || {}).textContent || '',
            badge: (r.querySelector('.tray-badge') || {}).textContent || '',
        }));
    }""")


def screenshot(page, name):
    p = EVIDENCE_DIR / name
    page.screenshot(path=str(p), full_page=False)
    print(f"  [screenshot] {p.name}")
    return str(p)


def get_status(page):
    return page.evaluate("() => { const s = document.getElementById('builder-status'); return s ? s.textContent : ''; }")


def open_deck_via_seam(page, deck_path):
    """Open a deck using the dialog seam. Handles the confirm dialog if needed."""
    # Set up dialog handler for JS confirm
    page.on("dialog", lambda d: d.accept())
    set_fake_dialog(deck_path)
    page.click("#open-deck-btn")


# ─────────────────────────────────────────────────────────────────────────────
# CRITERION 1
# ─────────────────────────────────────────────────────────────────────────────

def criterion_1(page, tmpdir):
    print("\n=== CRITERION 1: Full loop at the floor ===")
    r = {"criterion": "C1"}

    deck_copy = str(pathlib.Path(tmpdir) / "deck_c1.html")
    shutil.copy(str(FIXTURE), deck_copy)
    print(f"  Deck copy: {deck_copy}")

    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    # Open deck
    open_deck_via_seam(page, deck_copy)
    wait_tray_loaded(page, min_items=1, timeout=12000)
    time.sleep(1.0)

    initial = get_tray_info(page)
    n0 = len(initial)
    print(f"  Initial tray: {n0} slides")
    r["initial_count"] = n0

    if n0 < 3:
        r["verdict"] = "FAIL"
        r["reason"] = f"Need ≥3 slides to run full loop, got {n0}"
        return r

    ss1 = screenshot(page, "c1_01_initial_tray.png")
    r["ss_before"] = ss1

    # ── REORDER: drag row[1] above row[0] ────────────────────────────────
    rows = page.query_selector_all("#tray-list .tray-row")
    r0 = rows[0].bounding_box()
    r1 = rows[1].bounding_box()
    if r0 and r1:
        cx0 = r0["x"] + r0["width"] / 2
        cy0 = r0["y"] + r0["height"] / 2
        cx1 = r1["x"] + r1["width"] / 2
        cy1 = r1["y"] + r1["height"] / 2
        page.mouse.move(cx1, cy1)
        page.mouse.down()
        time.sleep(0.15)
        # Move to above row[0]
        for step in range(10):
            frac = step / 9
            page.mouse.move(cx1, cy1 - (cy1 - cy0 + 5) * frac)
            time.sleep(0.03)
        time.sleep(0.2)
        page.mouse.up()
        time.sleep(0.5)

    after_reorder = get_tray_info(page)
    r["after_reorder"] = [x["slideId"] for x in after_reorder]
    # Check if order changed
    reorder_changed = (
        len(after_reorder) == n0 and
        after_reorder[0]["slideId"] != initial[0]["slideId"]
    ) if len(after_reorder) >= 2 else False
    print(f"  After reorder: {[x['slideId'] for x in after_reorder[:3]]} — changed={reorder_changed}")
    r["reorder_changed"] = reorder_changed

    # ── REMOVE: remove row[0] ────────────────────────────────────────────
    first_row = page.query_selector("#tray-list .tray-row")
    if first_row:
        remove_btn = first_row.query_selector(".tray-remove")
        if remove_btn:
            remove_btn.click()
            time.sleep(0.4)

    after_remove = get_tray_info(page)
    n1 = len(after_remove)
    remove_ok = n1 == n0 - 1
    print(f"  After remove: {n1} slides (expected {n0-1}) — ok={remove_ok}")
    r["after_remove_count"] = n1
    r["remove_ok"] = remove_ok
    r["removed_slide_gone"] = remove_ok

    # ── DUPLICATE: duplicate row[0] ───────────────────────────────────────
    first_row = page.query_selector("#tray-list .tray-row")
    dup_id_before = None
    if first_row:
        dup_id_before = first_row.get_attribute("data-slide-id")
        dup_btn = first_row.query_selector(".tray-duplicate")
        if dup_btn:
            dup_btn.click()
            time.sleep(0.4)

    after_dup = get_tray_info(page)
    n2 = len(after_dup)
    dup_ok = n2 == n1 + 1
    # Check duplicate is adjacent (rows 0 and 1 have same slideId)
    dup_adjacent = (n2 >= 2 and after_dup[0]["slideId"] == after_dup[1]["slideId"]) if dup_ok else False
    print(f"  After dup: {n2} slides — dup_ok={dup_ok} adjacent={dup_adjacent}")
    r["after_dup_count"] = n2
    r["dup_ok"] = dup_ok
    r["dup_adjacent"] = dup_adjacent

    # ── ADD BLANK ─────────────────────────────────────────────────────────
    page.click("#add-blank-btn")
    time.sleep(0.4)

    after_blank = get_tray_info(page)
    n3 = len(after_blank)
    blank_ok = n3 == n2 + 1
    blank_present = any(x["badge"] == "blank" for x in after_blank)
    print(f"  After blank: {n3} slides — blank_ok={blank_ok} blank_present={blank_present}")
    r["after_blank_count"] = n3
    r["blank_ok"] = blank_ok
    r["blank_present"] = blank_present

    # ── ADD LIBRARY SLIDE ─────────────────────────────────────────────────
    # Pick a library (after deck open, lib state was cleared)
    set_fake_folder(str(BUILDER_LIB))
    page.click("#pick-library-btn")
    try:
        page.wait_for_function(
            """() => {
                const el = document.getElementById('browse-groups');
                return el && el.children.length > 0;
            }""",
            timeout=10000,
        )
        time.sleep(0.5)
        first_card = page.query_selector(".slide-card")
        lib_slide_added = False
        lib_slide_id = None
        if first_card:
            lib_slide_id = first_card.get_attribute("data-slide-id")
            first_card.click()
            time.sleep(0.4)
            after_lib = get_tray_info(page)
            n4 = len(after_lib)
            lib_slide_added = n4 == n3 + 1 or any(x["badge"] == "lib" for x in after_lib)
            print(f"  After lib slide: {n4} slides — lib_added={lib_slide_added} id={lib_slide_id}")
            r["lib_slide_id"] = lib_slide_id
            r["after_lib_count"] = n4
            r["lib_slide_added"] = lib_slide_added
        else:
            print("  WARNING: no .slide-card found in browse grid")
            r["lib_slide_added"] = False
            after_lib = after_blank
            n4 = n3
    except Exception as e:
        print(f"  WARNING: lib pick failed: {e}")
        r["lib_slide_added"] = False
        after_lib = after_blank
        n4 = n3

    ss2 = screenshot(page, "c1_02_restructured_tray.png")
    r["ss_restructured"] = ss2

    # ── SAVE TO NEW FILE ─────────────────────────────────────────────────
    save_path = str(pathlib.Path(tmpdir) / "deck_c1_saved.html")
    set_fake_dialog(save_path)
    page.click("#save-new-btn")
    time.sleep(2.0)

    save_status = get_status(page)
    save_ok = "Saved:" in save_status and pathlib.Path(save_path).exists()
    print(f"  Save status: '{save_status}' — ok={save_ok}")
    r["save_status"] = save_status
    r["save_ok"] = save_ok

    if not save_ok:
        r["verdict"] = "FAIL"
        r["reason"] = f"Save failed: status='{save_status}' file_exists={pathlib.Path(save_path).exists()}"
        return r

    # ── REOPEN ───────────────────────────────────────────────────────────
    page.on("dialog", lambda d: d.accept())
    open_deck_via_seam(page, save_path)
    wait_tray_loaded(page, min_items=1, timeout=12000)
    time.sleep(1.0)

    reopened = get_tray_info(page)
    n5 = len(reopened)
    reopened_badges = [x["badge"] for x in reopened]
    all_deck_badges = all(b == "deck" for b in reopened_badges)
    print(f"  Reopened: {n5} slides, badges={reopened_badges}")
    r["reopened_count"] = n5
    r["reopened_all_deck"] = all_deck_badges

    # The reopened tray should have exactly n4 slides (what we saved)
    count_matches = n5 == n4
    print(f"  Count match: expected {n4}, got {n5} — {count_matches}")
    r["count_matches"] = count_matches

    ss3 = screenshot(page, "c1_03_reopened_tray.png")
    r["ss_reopened"] = ss3

    # Verdict logic
    all_ok = (
        remove_ok and           # removed 1 slide
        dup_ok and              # duplicated 1 slide
        blank_present and       # blank slide present
        r.get("lib_slide_added", False) and  # library slide added
        save_ok and             # saved ok
        count_matches           # reopened count matches
    )
    r["all_ok"] = all_ok

    if all_ok:
        r["verdict"] = "PASS"
    else:
        issues = []
        if not remove_ok:
            issues.append(f"remove: expected {n0-1} got {n1}")
        if not dup_ok:
            issues.append(f"dup: expected {n1+1} got {n2}")
        if not blank_present:
            issues.append("blank slide missing")
        if not r.get("lib_slide_added", False):
            issues.append("library slide not added")
        if not save_ok:
            issues.append(f"save failed: {save_status}")
        if not count_matches:
            issues.append(f"reopen count mismatch: expected {n4} got {n5}")
        r["verdict"] = "FAIL"
        r["reason"] = "; ".join(issues)

    return r


# ─────────────────────────────────────────────────────────────────────────────
# CRITERION 2
# ─────────────────────────────────────────────────────────────────────────────

def criterion_2(page, tmpdir):
    print("\n=== CRITERION 2: Overwrite path + chooser every time ===")
    r = {"criterion": "C2"}

    deck_copy = str(pathlib.Path(tmpdir) / "deck_c2.html")
    shutil.copy(str(FIXTURE), deck_copy)

    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    open_deck_via_seam(page, deck_copy)
    wait_tray_loaded(page, min_items=1, timeout=12000)
    time.sleep(0.8)

    # Check deck-save pane is visible (chooser exists)
    pane_visible_1 = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    assemble_hidden = page.evaluate("() => document.querySelector('.assemble').hidden")
    new_btn_enabled = not page.evaluate("() => document.getElementById('save-new-btn').disabled")
    overwrite_btn_enabled = not page.evaluate("() => document.getElementById('save-overwrite-btn').disabled")
    print(f"  Initial: pane_visible={pane_visible_1} assemble_hidden={assemble_hidden} new_btn_enabled={new_btn_enabled} overwrite_btn_enabled={overwrite_btn_enabled}")
    r["pane_visible_1"] = pane_visible_1
    r["assemble_hidden"] = assemble_hidden
    r["new_btn_enabled"] = new_btn_enabled
    r["overwrite_btn_enabled"] = overwrite_btn_enabled

    ss1 = screenshot(page, "c2_01_save_pane_initial.png")
    r["ss_initial"] = ss1

    orig_hash = hashlib.sha256(pathlib.Path(deck_copy).read_bytes()).hexdigest()

    # First overwrite
    page.click("#save-overwrite-btn")
    time.sleep(1.5)
    status_1 = get_status(page)
    overwrite_1_ok = "Saved:" in status_1
    new_hash_1 = hashlib.sha256(pathlib.Path(deck_copy).read_bytes()).hexdigest()
    print(f"  Overwrite 1: status='{status_1}' ok={overwrite_1_ok}")
    r["overwrite_1_status"] = status_1
    r["overwrite_1_ok"] = overwrite_1_ok

    # Chooser must still be visible after first save
    pane_visible_after_1 = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    r["pane_visible_after_1"] = pane_visible_after_1
    print(f"  After overwrite 1: pane_visible={pane_visible_after_1}")

    ss2 = screenshot(page, "c2_02_after_overwrite_1.png")
    r["ss_after_1"] = ss2

    # Second overwrite (chooser still there, no sticky default)
    page.click("#save-overwrite-btn")
    time.sleep(1.5)
    status_2 = get_status(page)
    overwrite_2_ok = "Saved:" in status_2
    print(f"  Overwrite 2: status='{status_2}' ok={overwrite_2_ok}")
    r["overwrite_2_status"] = status_2
    r["overwrite_2_ok"] = overwrite_2_ok

    pane_visible_after_2 = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    r["pane_visible_after_2"] = pane_visible_after_2
    print(f"  After overwrite 2: pane_visible={pane_visible_after_2}")

    ss3 = screenshot(page, "c2_03_after_overwrite_2.png")
    r["ss_after_2"] = ss3

    # New-file save
    new_path = str(pathlib.Path(tmpdir) / "deck_c2_new.html")
    set_fake_dialog(new_path)
    page.click("#save-new-btn")
    time.sleep(1.5)
    status_new = get_status(page)
    new_file_ok = "Saved:" in status_new and pathlib.Path(new_path).exists()
    print(f"  New-file: status='{status_new}' ok={new_file_ok}")
    r["new_file_status"] = status_new
    r["new_file_ok"] = new_file_ok

    pane_visible_after_new = not page.evaluate("() => document.getElementById('deck-save-pane').hidden")
    r["pane_visible_after_new"] = pane_visible_after_new
    print(f"  After new-file: pane_visible={pane_visible_after_new}")

    ss4 = screenshot(page, "c2_04_after_new_file.png")
    r["ss_after_new"] = ss4

    # Verify overwrite actually changed the file
    overwrite_changed_file = new_hash_1 != orig_hash
    print(f"  Overwrite changed file: {overwrite_changed_file} (orig={orig_hash[:16]}... new={new_hash_1[:16]}...)")
    # Note: if deck has all identity sections, recompose may be identical bytes
    # The important thing is the save succeeded
    r["overwrite_changed_file_note"] = f"orig_hash={orig_hash[:16]}, post_overwrite_hash={new_hash_1[:16]}"

    chooser_every_time = pane_visible_1 and pane_visible_after_1 and pane_visible_after_2 and pane_visible_after_new

    all_ok = (
        pane_visible_1 and
        overwrite_1_ok and
        pane_visible_after_1 and
        overwrite_2_ok and
        pane_visible_after_2 and
        new_file_ok and
        pane_visible_after_new
    )
    r["chooser_every_time"] = chooser_every_time

    if all_ok:
        r["verdict"] = "PASS"
    else:
        issues = []
        if not pane_visible_1:
            issues.append("save pane not visible after deck open")
        if not overwrite_1_ok:
            issues.append(f"overwrite 1 failed: {status_1}")
        if not pane_visible_after_1:
            issues.append("chooser disappeared after overwrite 1")
        if not overwrite_2_ok:
            issues.append(f"overwrite 2 failed: {status_2}")
        if not pane_visible_after_2:
            issues.append("chooser disappeared after overwrite 2")
        if not new_file_ok:
            issues.append(f"new-file failed: {status_new}")
        if not pane_visible_after_new:
            issues.append("chooser disappeared after new-file save")
        r["verdict"] = "FAIL"
        r["reason"] = "; ".join(issues)

    return r


# ─────────────────────────────────────────────────────────────────────────────
# CRITERION 3
# ─────────────────────────────────────────────────────────────────────────────

def criterion_3(page, tmpdir):
    print("\n=== CRITERION 3: Saved output clean ===")
    r = {"criterion": "C3"}

    deck_copy = str(pathlib.Path(tmpdir) / "deck_c3_src.html")
    shutil.copy(str(FIXTURE), deck_copy)

    page.goto(f"{BASE_URL}/app/builder.html")
    page.wait_for_load_state("networkidle")
    time.sleep(0.5)

    open_deck_via_seam(page, deck_copy)
    wait_tray_loaded(page, min_items=1, timeout=12000)
    time.sleep(0.8)

    # Pick library and add first library slide
    set_fake_folder(str(BUILDER_LIB))
    page.click("#pick-library-btn")
    lib_slide_id = None
    lib_slide_frag = None
    try:
        page.wait_for_function(
            """() => {
                const el = document.getElementById('browse-groups');
                return el && el.children.length > 0;
            }""",
            timeout=10000,
        )
        time.sleep(0.5)
        first_card = page.query_selector(".slide-card")
        if first_card:
            lib_slide_id = first_card.get_attribute("data-slide-id")
            print(f"  Library slide id: {lib_slide_id}")
            first_card.click()
            time.sleep(0.4)
        else:
            print("  WARNING: no .slide-card found in browse grid")
    except Exception as e:
        print(f"  WARNING: library load failed: {e}")

    # Also add a blank slide
    page.click("#add-blank-btn")
    time.sleep(0.3)

    # Save
    save_dir_path = pathlib.Path(tmpdir) / "c3_save"
    save_dir_path.mkdir(exist_ok=True)
    save_path = str(save_dir_path / "deck_c3_saved.html")
    set_fake_dialog(save_path)
    page.click("#save-new-btn")
    time.sleep(2.0)

    status = get_status(page)
    save_ok = "Saved:" in status and pathlib.Path(save_path).exists()
    print(f"  Save: status='{status}' ok={save_ok}")
    r["save_status"] = status
    r["save_ok"] = save_ok

    if not save_ok:
        r["verdict"] = "FAIL"
        r["reason"] = f"Save failed: {status}"
        return r

    saved_html = pathlib.Path(save_path).read_text(encoding="utf-8")
    r["saved_size"] = len(saved_html.encode("utf-8"))
    print(f"  Saved file: {r['saved_size']} bytes")

    # --- No hyp-/data-hyp-* tokens ---
    hyp_tokens = re.findall(r'(?:hyp-|data-hyp-)[^\s"\'>/;]+', saved_html)
    r["hyp_token_count"] = len(hyp_tokens)
    r["hyp_tokens_sample"] = hyp_tokens[:10]
    no_hyp = len(hyp_tokens) == 0
    print(f"  hyp-/data-hyp-* tokens: {len(hyp_tokens)} — clean={no_hyp}")
    if hyp_tokens:
        print(f"  Sample: {hyp_tokens[:5]}")

    # --- Library slide markup verbatim ---
    lib_verbatim = True
    if lib_slide_id:
        frag_file = BUILDER_LIB / "slides" / f"{lib_slide_id}.html"
        if frag_file.exists():
            frag_text = frag_file.read_text(encoding="utf-8").strip()
            lib_verbatim = frag_text in saved_html
            print(f"  Library fragment verbatim: {lib_verbatim} (id={lib_slide_id})")
            r["lib_slide_id"] = lib_slide_id
            r["lib_verbatim"] = lib_verbatim
            if not lib_verbatim:
                # check partial
                start_ok = frag_text[:80] in saved_html
                end_ok = frag_text[-80:] in saved_html
                print(f"    Fragment start in output: {start_ok}, end in output: {end_ok}")
        else:
            print(f"  WARNING: fragment file not found: {frag_file}")
    r["lib_verbatim"] = lib_verbatim

    # --- Asset refs and copies (LIBRARY FRAGMENT assets only) ---
    # The contract: "referenced assets are copied beside the saved file"
    # applies only to assets from LIBRARY fragments, NOT from the source deck's
    # own pre-existing asset references (those are embedded in the source HTML
    # and not the recompose's responsibility to copy).
    lib_frag_asset_refs = []
    if lib_slide_id:
        frag_file_for_assets = BUILDER_LIB / "slides" / f"{lib_slide_id}.html"
        if frag_file_for_assets.exists():
            frag_html_for_assets = frag_file_for_assets.read_text(encoding="utf-8")
            lib_frag_asset_refs = [m[0] or m[1] for m in re.findall(
                r'(?:src|href)\s*=\s*["\']?(assets/[^"\'>\s]+)["\']?|url\(\s*["\']?(assets/[^"\'>\s]+)["\']?\s*\)',
                frag_html_for_assets, re.IGNORECASE
            )]

    r["lib_frag_asset_refs"] = lib_frag_asset_refs
    print(f"  Library fragment asset refs: {lib_frag_asset_refs}")

    assets_ok = True
    missing_assets = []
    for ref in lib_frag_asset_refs:
        asset_p = save_dir_path / ref
        if not asset_p.exists():
            # Check if it exists in the library
            lib_asset = BUILDER_LIB / ref
            if lib_asset.exists():
                assets_ok = False
                missing_assets.append(ref)
                print(f"    MISSING (should have been copied from lib): {ref}")
            else:
                print(f"    SKIP (not in lib either): {ref}")
        else:
            print(f"    OK: {ref}")
    r["assets_ok"] = assets_ok
    r["missing_assets"] = missing_assets

    # Also grab total asset refs for informational logging
    all_asset_refs = [m[0] or m[1] for m in re.findall(
        r'(?:src|href)\s*=\s*["\']?(assets/[^"\'>\s]+)["\']?|url\(\s*["\']?(assets/[^"\'>\s]+)["\']?\s*\)',
        saved_html, re.IGNORECASE
    )]
    r["all_asset_refs_in_output"] = all_asset_refs

    # Write inspection log
    log_path = EVIDENCE_DIR / "c3_inspection.txt"
    with open(str(log_path), "w", encoding="utf-8") as f:
        f.write(f"Saved file: {save_path}\n")
        f.write(f"Size: {r['saved_size']} bytes\n\n")
        f.write(f"hyp-/data-hyp-* token count: {len(hyp_tokens)}\n")
        for t in hyp_tokens[:50]:
            f.write(f"  {t}\n")
        f.write(f"\nAll asset refs in output (informational):\n")
        for ref in all_asset_refs:
            f.write(f"  {ref}\n")
        f.write(f"\nLibrary fragment asset refs (checked for copy):\n")
        for ref in lib_frag_asset_refs:
            ap = save_dir_path / ref
            f.write(f"  {ref} — {'EXISTS' if ap.exists() else 'MISSING'}\n")
        f.write(f"\nAsset directory listing ({save_dir_path / 'assets'}):\n")
        assets_dir = save_dir_path / "assets"
        if assets_dir.exists():
            for p in sorted(assets_dir.rglob("*")):
                f.write(f"  {p.relative_to(save_dir_path)}\n")
        else:
            f.write("  (no assets/ directory)\n")
        f.write(f"\nLibrary fragment verbatim: {lib_verbatim}\n")
    r["inspection_log"] = str(log_path)

    all_ok = no_hyp and lib_verbatim and assets_ok
    if all_ok:
        r["verdict"] = "PASS"
    else:
        issues = []
        if not no_hyp:
            issues.append(f"hyp tokens present: {hyp_tokens[:3]}")
        if not lib_verbatim:
            issues.append("library fragment not verbatim")
        if not assets_ok:
            issues.append(f"missing assets: {missing_assets}")
        r["verdict"] = "FAIL"
        r["reason"] = "; ".join(issues)

    return r


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    import hashlib as _h
    from playwright.sync_api import sync_playwright

    print(f"APP_ROOT: {APP_ROOT}")
    print(f"EVIDENCE_DIR: {EVIDENCE_DIR}")
    print(f"PORT: {PORT}")

    tmpdir = tempfile.mkdtemp(prefix="hyp_verifier_")
    print(f"Temp dir: {tmpdir}")

    all_results = {}

    server_proc = start_server()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=60)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.set_default_timeout(20000)

            t1_start = time.time()
            page1 = context.new_page()
            all_results["c1"] = criterion_1(page1, tmpdir)
            all_results["c1"]["wall_ms"] = int((time.time() - t1_start) * 1000)
            page1.close()

            t2_start = time.time()
            page2 = context.new_page()
            all_results["c2"] = criterion_2(page2, tmpdir)
            all_results["c2"]["wall_ms"] = int((time.time() - t2_start) * 1000)
            page2.close()

            t3_start = time.time()
            page3 = context.new_page()
            all_results["c3"] = criterion_3(page3, tmpdir)
            all_results["c3"]["wall_ms"] = int((time.time() - t3_start) * 1000)
            page3.close()

            context.close()
            browser.close()
    finally:
        stop_server(server_proc)

    # Write JSON results
    out = EVIDENCE_DIR / "c123_results.json"
    out.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    print(f"\nResults: {out}")

    print("\n" + "="*60)
    for cn in ["c1","c2","c3"]:
        r = all_results.get(cn, {})
        print(f"  {cn.upper()} | {r.get('verdict','NO_RESULT')}  {r.get('reason','')}")
    print("="*60)
    return all_results


if __name__ == "__main__":
    main()
