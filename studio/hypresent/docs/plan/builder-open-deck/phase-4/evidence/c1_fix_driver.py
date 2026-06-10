"""Cold-verifier session 2 — C1 content-level fix driver.

Exercises criterion 1 at content level:
  - Per-row slide identity before and after reorder
  - Explicit order-match assertion (rows 1 and 2 swapped)
  - Marker text [CV-B12] present in final tray thumbnail (DOM-level)
  - Cropped/zoomed screenshot of thumbnail row with marker
  - SHA-256 proof that crossing-1 != deck (reorder serialized)
  - SHA-256 proof that crossing-2 contains [CV-B12] marker in bytes
  - Owner deck hash proof (before + after)

Run from the hypresent app root:
  python docs/plan/builder-open-deck/phase-4/evidence/c1_fix_driver.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
EVIDENCE = os.path.dirname(os.path.abspath(__file__))

OWNER_DECKS = [
    os.path.join(REPO, "tecer-gsmm-introduction.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test-v2.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html"),
]

PORT = 18900


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def post_json(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def set_dialog(base, path_or_none):
    post_json(base, "/api/_test/set-dialog", {"path": path_or_none})


def start_server(port):
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=REPO, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 12
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError(f"Server on {port} did not start")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def ev(name):
    return os.path.join(EVIDENCE, name)


def wait_tray_populated(page, min_items=1, timeout=20000):
    page.wait_for_function(
        f"() => document.querySelectorAll('.tray-list li').length >= {min_items}",
        timeout=timeout,
    )


def wait_runtime_ready(page, timeout=20000):
    page.wait_for_function(
        """() => {
            const f = document.querySelector('iframe.doc-frame');
            return f && f.contentWindow && f.contentWindow.hyp;
        }""",
        timeout=timeout,
    )


def get_tray_identities(page):
    """Get stable identity for each tray row."""
    return page.evaluate("""() => {
        const rows = document.querySelectorAll('.tray-list li');
        return Array.from(rows).map((li, idx) => {
            const iframe = li.querySelector('iframe');
            let srcdoc_snippet = '';
            let title_text = '';
            let data_src = '';
            if (iframe) {
                const sd = iframe.getAttribute('srcdoc') || '';
                srcdoc_snippet = sd.substring(0, 200);
                data_src = iframe.getAttribute('data-src') || '';
                const titleMatch = sd.match(/<title[^>]*>(.*?)<\\/title>/i);
                if (titleMatch) title_text = titleMatch[1].trim();
                const h1Match = sd.match(/<h[123][^>]*>(.*?)<\\/h[123]>/i);
                if (h1Match) title_text = title_text || h1Match[1].replace(/<[^>]+>/g,'').trim();
            }
            const liText = li.innerText ? li.innerText.substring(0, 100) : '';
            return {
                row_index: idx,
                srcdoc_snippet,
                data_src,
                title_text,
                li_text: liText
            };
        });
    }""")


def get_tray_full_srcdoc(page):
    """Get full srcdoc for each tray row."""
    return page.evaluate("""() => {
        const rows = document.querySelectorAll('.tray-list li');
        return Array.from(rows).map((li, idx) => {
            const iframe = li.querySelector('iframe');
            let srcdoc = '';
            if (iframe) {
                srcdoc = iframe.getAttribute('srcdoc') || '';
            }
            return { row_index: idx, srcdoc };
        });
    }""")


def main():
    print(f"[CV-FIX] REPO={REPO}")
    print(f"[CV-FIX] EVIDENCE={EVIDENCE}")

    # Pre-exercise owner deck hashes
    pre_hashes = {p: sha256(p) for p in OWNER_DECKS}
    print("[CV-FIX] Pre-exercise owner deck hashes:")
    for p, h in pre_hashes.items():
        print(f"  {os.path.basename(p)}: {h}")

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    proc, base = start_server(PORT)
    log = []

    def logit(msg):
        print(msg)
        log.append(msg)

    # Declare these at outer scope so they're available after the try block
    identities_before = []
    identities_after_reorder = []
    identities_final = []
    crossing1_path = ""
    crossing2_path = ""
    crossing1_written = False
    crossing2_written = False
    reorder_happened = False
    swapped = False
    title_swapped = None
    marker_in_dom = False
    marker_found_row = None
    marker_snippet = ""
    edit_success = False
    deck_copy = ""

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.add_init_script(
                "window.localStorage.setItem('hypresent-comment-author','CVFixSession');"
            )

            # ----------------------------------------------------------------
            # Step 1: Copy deck to temp
            # ----------------------------------------------------------------
            src_deck = os.path.join(REPO, "tecer-gsmm-introduction.html")
            temp_dir = tempfile.mkdtemp()
            deck_copy = os.path.join(temp_dir, "deck.html")
            shutil.copy(src_deck, deck_copy)
            logit(f"[step 1] deck copy: {deck_copy}")

            # ----------------------------------------------------------------
            # Step 2: Open deck in builder, capture per-row identity BEFORE reorder
            # ----------------------------------------------------------------
            set_dialog(base, deck_copy)
            page.goto(f"{base}/app/builder.html", wait_until="domcontentloaded")
            page.wait_for_timeout(500)
            page.click("#open-deck-btn")
            wait_tray_populated(page, min_items=2, timeout=20000)
            page.wait_for_timeout(800)

            identities_before = get_tray_identities(page)
            logit(f"[step 2] tray rows before reorder: {len(identities_before)}")
            for r in identities_before:
                logit(
                    f"  row {r['row_index']}: title={r['title_text']!r} "
                    f"srcdoc_snippet={r['srcdoc_snippet'][:60]!r}"
                )

            page.screenshot(path=ev("c1-fix-01-loaded.png"))
            logit("[step 2] screenshot c1-fix-01-loaded.png saved")

            with open(ev("c1-fix-order-before.json"), "w", encoding="utf-8") as f:
                json.dump({"tray_before_reorder": identities_before}, f, indent=2)

            if len(identities_before) < 2:
                logit("[FAIL] fewer than 2 slides in tray")
                browser.close()
                return False

            # ----------------------------------------------------------------
            # Step 3: REAL drag — row 0 below row 1
            # ----------------------------------------------------------------
            handle_sel = ".tray-list li .drag-handle"
            handles = page.locator(handle_sel)
            handle_count = handles.count()
            logit(f"[step 3] drag handles found: {handle_count}")

            if handle_count >= 2:
                h0_box = handles.nth(0).bounding_box()
                h1_box = handles.nth(1).bounding_box()
                fx = h0_box["x"] + h0_box["width"] / 2
                fy = h0_box["y"] + h0_box["height"] / 2
                tx = h1_box["x"] + h1_box["width"] / 2
                ty = h1_box["y"] + h1_box["height"] * 1.1
                logit(
                    f"[step 3] drag handle from ({fx:.0f},{fy:.0f}) to ({tx:.0f},{ty:.0f})"
                )
            else:
                row0_box = page.locator(".tray-list li").nth(0).bounding_box()
                row1_box = page.locator(".tray-list li").nth(1).bounding_box()
                fx = row0_box["x"] + row0_box["width"] / 2
                fy = row0_box["y"] + row0_box["height"] / 2
                tx = row1_box["x"] + row1_box["width"] / 2
                ty = row1_box["y"] + row1_box["height"] * 0.85
                logit(
                    f"[step 3] drag row body from ({fx:.0f},{fy:.0f}) to ({tx:.0f},{ty:.0f})"
                )

            page.mouse.move(fx, fy)
            page.mouse.down()
            page.wait_for_timeout(300)
            page.mouse.move(fx, fy + 5, steps=3)
            page.mouse.move(tx, ty, steps=20)
            page.wait_for_timeout(400)
            page.mouse.up()
            page.wait_for_timeout(1500)

            identities_after_reorder = get_tray_identities(page)
            logit(f"[step 3] tray rows after reorder: {len(identities_after_reorder)}")
            for r in identities_after_reorder:
                logit(f"  row {r['row_index']}: title={r['title_text']!r}")

            # Check swap
            row0_before_sig = identities_before[0]["srcdoc_snippet"][:80]
            row1_before_sig = identities_before[1]["srcdoc_snippet"][:80]
            row0_after_sig = (
                identities_after_reorder[0]["srcdoc_snippet"][:80]
                if identities_after_reorder else ""
            )
            row1_after_sig = (
                identities_after_reorder[1]["srcdoc_snippet"][:80]
                if len(identities_after_reorder) > 1 else ""
            )

            swapped = (
                row0_before_sig == row1_after_sig and
                row1_before_sig == row0_after_sig
            )
            title_swapped = None
            if (identities_before[0]["title_text"] and
                    identities_before[1]["title_text"] and
                    len(identities_after_reorder) >= 2):
                title_swapped = (
                    identities_before[0]["title_text"] ==
                    identities_after_reorder[1]["title_text"]
                    and
                    identities_before[1]["title_text"] ==
                    identities_after_reorder[0]["title_text"]
                )

            reorder_happened = swapped or (title_swapped is True)
            logit(f"[step 3] swap assertion (srcdoc): {swapped}")
            logit(f"[step 3] swap assertion (title): {title_swapped}")
            logit(f"[step 3] reorder_happened: {reorder_happened}")
            logit(
                f"  before: row0={identities_before[0]['title_text']!r} "
                f"row1={identities_before[1]['title_text']!r}"
            )
            if len(identities_after_reorder) >= 2:
                logit(
                    f"  after:  row0={identities_after_reorder[0]['title_text']!r} "
                    f"row1={identities_after_reorder[1]['title_text']!r}"
                )

            page.screenshot(path=ev("c1-fix-02-reordered.png"))
            logit("[step 3] screenshot c1-fix-02-reordered.png saved")

            # ----------------------------------------------------------------
            # Step 4: Switch to Editor (crossing 1)
            # ----------------------------------------------------------------
            crossing1_dir = tempfile.mkdtemp()
            crossing1_path = os.path.join(crossing1_dir, "crossing-1.html")
            set_dialog(base, crossing1_path)
            page.click("#switch-to-editor-btn")

            try:
                page.wait_for_function(
                    "() => !window.location.pathname.includes('builder') && "
                    "window.location.pathname.includes('app')",
                    timeout=20000,
                )
                logit(f"[step 4] navigated to editor: {page.url}")
            except PWTimeout:
                logit(f"[step 4] WARNING: timed out waiting for editor. URL={page.url}")

            page.wait_for_timeout(500)
            crossing1_written = os.path.isfile(crossing1_path)
            logit(f"[step 4] crossing-1.html written: {crossing1_written} ({crossing1_path})")

            try:
                page.wait_for_function(
                    "() => !document.getElementById('open-in-builder-btn').disabled",
                    timeout=20000,
                )
                oib_ready = True
                logit("[step 4] OIB button enabled")
            except PWTimeout:
                oib_ready = False
                logit("[step 4] WARNING: OIB button did not enable within 20s")

            # ----------------------------------------------------------------
            # Step 5: Edit text with real gesture — type marker [CV-B12]
            # ----------------------------------------------------------------
            iframe_box = page.locator("iframe.doc-frame").bounding_box()
            edit_notes = []

            if iframe_box:
                attempts = [
                    (0.5, 0.25),
                    (0.5, 0.4),
                    (0.3, 0.3),
                    (0.5, 0.15),
                ]
                for rx, ry in attempts:
                    cx = iframe_box["x"] + iframe_box["width"] * rx
                    cy = iframe_box["y"] + iframe_box["height"] * ry
                    page.mouse.dblclick(cx, cy)
                    page.wait_for_timeout(600)
                    sel_mode = page.evaluate("""() => {
                        const f = document.querySelector('iframe.doc-frame');
                        if (!f || !f.contentWindow) return 'no-frame';
                        const sel = f.contentWindow.getSelection();
                        if (sel && sel.rangeCount > 0) return 'has-selection';
                        const focused = f.contentDocument && f.contentDocument.activeElement;
                        if (focused && (
                            focused.contentEditable === 'true' ||
                            focused.tagName === 'INPUT' ||
                            focused.tagName === 'TEXTAREA'
                        )) return 'has-editable';
                        return 'no-edit';
                    }""")
                    edit_notes.append(
                        f"dblclick at ({rx:.1f},{ry:.1f}): sel_mode={sel_mode}"
                    )
                    logit(f"[step 5] dblclick at ({rx:.1f},{ry:.1f}): {sel_mode}")

                    if sel_mode in ('has-selection', 'has-editable'):
                        page.keyboard.type(" [CV-B12]")
                        page.wait_for_timeout(400)
                        marker_check = page.evaluate("""() => {
                            const f = document.querySelector('iframe.doc-frame');
                            if (!f || !f.contentDocument) return false;
                            return f.contentDocument.body.innerHTML.includes('[CV-B12]');
                        }""")
                        edit_notes.append(f"  marker_in_iframe_dom: {marker_check}")
                        logit(f"[step 5]   marker_in_iframe_dom: {marker_check}")
                        if marker_check:
                            edit_success = True
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(300)
                            break
                        else:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(200)
                    else:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(200)

                if not edit_success:
                    logit("[step 5] dblclick attempts failed, trying click + single-click approach")
                    cx = iframe_box["x"] + iframe_box["width"] * 0.5
                    cy = iframe_box["y"] + iframe_box["height"] * 0.3
                    page.mouse.click(cx, cy)
                    page.wait_for_timeout(300)
                    page.mouse.dblclick(cx, cy)
                    page.wait_for_timeout(500)
                    page.keyboard.type(" [CV-B12]")
                    page.wait_for_timeout(400)
                    marker_check = page.evaluate("""() => {
                        const f = document.querySelector('iframe.doc-frame');
                        if (!f || !f.contentDocument) return false;
                        return f.contentDocument.body.innerHTML.includes('[CV-B12]');
                    }""")
                    edit_notes.append(f"  fallback marker_in_iframe_dom: {marker_check}")
                    logit(f"[step 5] fallback marker_in_iframe_dom: {marker_check}")
                    if marker_check:
                        edit_success = True
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(300)

            logit(f"[step 5] edit_success: {edit_success}")
            logit(f"[step 5] edit_notes: {edit_notes}")
            page.screenshot(path=ev("c1-fix-03-edited.png"))
            logit("[step 5] screenshot c1-fix-03-edited.png saved")

            # ----------------------------------------------------------------
            # Step 6: Open in Builder (crossing 2)
            # ----------------------------------------------------------------
            crossing2_dir = tempfile.mkdtemp()
            crossing2_path = os.path.join(crossing2_dir, "crossing-2.html")
            set_dialog(base, crossing2_path)
            page.click("#open-in-builder-btn")

            try:
                page.wait_for_function(
                    "() => window.location.pathname.includes('builder')",
                    timeout=25000,
                )
                logit(f"[step 6] navigated to builder: {page.url}")
            except PWTimeout:
                logit(f"[step 6] WARNING: timed out waiting for builder. URL={page.url}")

            page.wait_for_timeout(2000)
            wait_tray_populated(page, min_items=1, timeout=20000)
            page.wait_for_timeout(1000)

            crossing2_written = os.path.isfile(crossing2_path)
            logit(f"[step 6] crossing-2.html written: {crossing2_written} ({crossing2_path})")

            # ----------------------------------------------------------------
            # Step 7: Capture final tray identity and ASSERT order
            # ----------------------------------------------------------------
            identities_final = get_tray_identities(page)
            logit(f"[step 7] final tray rows: {len(identities_final)}")
            for r in identities_final:
                logit(f"  row {r['row_index']}: title={r['title_text']!r}")

            final_row0_sig = identities_final[0]["srcdoc_snippet"][:80] if identities_final else ""
            final_row1_sig = (
                identities_final[1]["srcdoc_snippet"][:80]
                if len(identities_final) > 1 else ""
            )
            postreorder_row0_sig = (
                identities_after_reorder[0]["srcdoc_snippet"][:80]
                if identities_after_reorder else ""
            )
            postreorder_row1_sig = (
                identities_after_reorder[1]["srcdoc_snippet"][:80]
                if len(identities_after_reorder) > 1 else ""
            )

            order_matches_post_reorder = None
            if final_row0_sig and postreorder_row0_sig:
                order_matches_post_reorder = (
                    final_row0_sig == postreorder_row0_sig and
                    final_row1_sig == postreorder_row1_sig
                )

            final_title0 = identities_final[0]["title_text"] if identities_final else ""
            final_title1 = (
                identities_final[1]["title_text"]
                if len(identities_final) > 1 else ""
            )
            postreorder_title0 = (
                identities_after_reorder[0]["title_text"]
                if identities_after_reorder else ""
            )
            postreorder_title1 = (
                identities_after_reorder[1]["title_text"]
                if len(identities_after_reorder) > 1 else ""
            )
            original_title0 = identities_before[0]["title_text"]

            order_matches_title = None
            if final_title0 and postreorder_title0:
                order_matches_title = (
                    final_title0 == postreorder_title0 and
                    final_title1 == postreorder_title1
                )

            order_not_original_title = None
            if final_title0 and original_title0:
                order_not_original_title = final_title0 != original_title0

            logit(f"[step 7] order_matches_post_reorder (srcdoc): {order_matches_post_reorder}")
            logit(f"[step 7] order_matches_title: {order_matches_title}")
            logit(f"[step 7] order_not_original_title: {order_not_original_title}")
            logit(
                f"  final_title0={final_title0!r} expected={postreorder_title0!r} "
                f"original={original_title0!r}"
            )
            logit(
                f"  final_title1={final_title1!r} expected={postreorder_title1!r}"
            )

            # ----------------------------------------------------------------
            # Step 8: ASSERT marker in final tray thumbnail
            # ----------------------------------------------------------------
            final_srcdocs = get_tray_full_srcdoc(page)
            logit(f"[step 8] scanning {len(final_srcdocs)} final tray rows for [CV-B12]")

            for row in final_srcdocs:
                if "[CV-B12]" in row["srcdoc"]:
                    marker_found_row = row["row_index"]
                    idx = row["srcdoc"].index("[CV-B12]")
                    start = max(0, idx - 100)
                    end = min(len(row["srcdoc"]), idx + 50)
                    marker_snippet = row["srcdoc"][start:end]
                    logit(f"[step 8] MARKER FOUND in row {marker_found_row}")
                    logit(f"  snippet: {marker_snippet!r}")
                    break

            marker_in_dom = marker_found_row is not None

            # DOM dump
            with open(ev("c1-fix-thumbnail-dom.txt"), "w", encoding="utf-8") as f:
                f.write("Marker [CV-B12] search in final tray thumbnail DOM\n")
                f.write(f"Rows scanned: {len(final_srcdocs)}\n")
                f.write(f"Marker found in row: {marker_found_row}\n")
                f.write(f"Marker snippet: {marker_snippet!r}\n\n")
                f.write("--- Per-row srcdoc presence ---\n")
                for row in final_srcdocs:
                    present = "[CV-B12]" in row["srcdoc"]
                    f.write(
                        f"  row {row['row_index']}: contains_marker={present}, "
                        f"srcdoc_len={len(row['srcdoc'])}\n"
                    )
                if marker_found_row is not None:
                    f.write(f"\n  Context snippet: {marker_snippet!r}\n")
                f.write("\n--- Full srcdoc of marker row (first 3000 chars) ---\n")
                for row in final_srcdocs:
                    if "[CV-B12]" in row["srcdoc"]:
                        f.write(row["srcdoc"][:3000])
                        break

            logit(f"[step 8] marker_in_dom: {marker_in_dom}")

            # Full tray screenshot
            page.screenshot(path=ev("c1-fix-04-final-tray.png"))
            logit("[step 8] screenshot c1-fix-04-final-tray.png saved")

            # Cropped/zoomed screenshot of the row with marker
            if marker_found_row is not None:
                row_locator = page.locator(".tray-list li").nth(marker_found_row)
                try:
                    row_locator.screenshot(path=ev("c1-fix-05-thumbnail-zoom.png"))
                    logit(
                        f"[step 8] cropped row screenshot saved: "
                        f"c1-fix-05-thumbnail-zoom.png"
                    )
                except Exception as ex:
                    logit(f"[step 8] row screenshot failed: {ex}")
                    try:
                        from PIL import Image
                        import io
                        row_box = row_locator.bounding_box()
                        if row_box:
                            full_ss = page.screenshot(full_page=False)
                            img = Image.open(io.BytesIO(full_ss))
                            dpr = page.evaluate("window.devicePixelRatio || 1")
                            x = int(row_box["x"] * dpr)
                            y = int(row_box["y"] * dpr)
                            w = int(row_box["width"] * dpr)
                            h = int(row_box["height"] * dpr)
                            cropped = img.crop((x, y, x + w, y + h))
                            cropped.save(ev("c1-fix-05-thumbnail-zoom.png"))
                            logit("[step 8] PIL crop saved: c1-fix-05-thumbnail-zoom.png")
                    except Exception as ex2:
                        logit(f"[step 8] PIL crop also failed: {ex2}")
            else:
                logit("[step 8] marker not found in DOM — no zoom screenshot possible")

            browser.close()

    finally:
        stop_server(proc)

    # ----------------------------------------------------------------
    # Step 9: Disk verification
    # ----------------------------------------------------------------
    logit("[step 9] disk verification")

    crossing2_has_marker = False
    crossing1_differs_from_deck = False

    if crossing2_written and os.path.isfile(crossing2_path):
        with open(crossing2_path, "rb") as f:
            c2_bytes = f.read()
        crossing2_has_marker = b"[CV-B12]" in c2_bytes
        logit(f"[step 9] crossing-2.html bytes contain [CV-B12]: {crossing2_has_marker}")

    if crossing1_written and deck_copy and os.path.isfile(crossing1_path):
        h_deck = sha256(deck_copy)
        h_c1 = sha256(crossing1_path)
        crossing1_differs_from_deck = h_deck != h_c1
        logit(f"[step 9] deck hash:       {h_deck}")
        logit(f"[step 9] crossing-1 hash: {h_c1}")
        logit(f"[step 9] crossing-1 differs from deck: {crossing1_differs_from_deck}")
    else:
        logit("[step 9] crossing-1 not written — skipping hash comparison")

    # ----------------------------------------------------------------
    # Step 10: Owner deck hashes (post)
    # ----------------------------------------------------------------
    post_hashes = {p: sha256(p) for p in OWNER_DECKS}
    owner_unchanged = all(post_hashes[p] == pre_hashes[p] for p in OWNER_DECKS)

    owner_hash_data = {
        "pre_exercise": {os.path.basename(p): pre_hashes[p] for p in OWNER_DECKS},
        "post_exercise": {os.path.basename(p): post_hashes[p] for p in OWNER_DECKS},
        "all_owner_decks_unchanged": owner_unchanged,
    }
    with open(ev("c1-fix-owner-hashes.json"), "w", encoding="utf-8") as f:
        json.dump(owner_hash_data, f, indent=2)
    logit(f"[step 10] owner decks unchanged: {owner_unchanged}")

    # ----------------------------------------------------------------
    # Derive summary order assertion
    # ----------------------------------------------------------------
    order_matches_combined = order_matches_post_reorder or order_matches_title

    # ----------------------------------------------------------------
    # Write consolidated order/assertion JSON
    # ----------------------------------------------------------------
    order_data = {
        "tray_before_reorder": identities_before,
        "tray_after_reorder": identities_after_reorder,
        "tray_final": identities_final,
        "assertions": {
            "reorder_happened": reorder_happened,
            "reorder_happened_srcdoc_based": swapped,
            "reorder_happened_title_based": title_swapped,
            "order_matches_post_reorder_srcdoc": order_matches_post_reorder,
            "order_matches_post_reorder_title": order_matches_title,
            "final_order_not_equal_to_original_title": order_not_original_title,
            "marker_in_final_tray_dom": marker_in_dom,
            "marker_in_row": marker_found_row,
            "marker_snippet": marker_snippet,
            "crossing2_bytes_contain_marker": crossing2_has_marker,
            "crossing1_differs_from_deck_by_hash": crossing1_differs_from_deck,
            "owner_decks_unchanged": owner_unchanged,
        },
    }
    with open(ev("c1-fix-order.json"), "w", encoding="utf-8") as f:
        json.dump(order_data, f, indent=2)
    logit("[step 9] c1-fix-order.json written")

    # ----------------------------------------------------------------
    # Final summary
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("=== C1 FIX SUMMARY ===")
    print(f"  reorder_happened:                    {reorder_happened}")
    print(f"  order_matches_post_reorder:          {order_matches_combined}")
    print(f"  marker_in_final_tray_dom:            {marker_in_dom}")
    print(f"  crossing2_bytes_contain_marker:      {crossing2_has_marker}")
    print(f"  crossing1_differs_from_deck_by_hash: {crossing1_differs_from_deck}")
    print(f"  owner_decks_unchanged:               {owner_unchanged}")
    print(f"  edit_success:                        {edit_success}")
    print("=" * 60)

    with open(ev("c1-fix-run-log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    return {
        "reorder_happened": reorder_happened,
        "order_matches_post_reorder": order_matches_combined,
        "marker_in_final_tray_dom": marker_in_dom,
        "crossing2_bytes_contain_marker": crossing2_has_marker,
        "edit_success": edit_success,
        "owner_decks_unchanged": owner_unchanged,
    }


if __name__ == "__main__":
    result = main()
    print("\nDONE:", result)
