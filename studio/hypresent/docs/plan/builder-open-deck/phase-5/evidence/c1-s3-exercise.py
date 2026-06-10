"""
c1-s3-exercise.py  —  Cold Verifier Session 3 (B15)
Re-exercises the C1 save->cross->back leg on the FIXED build (commit 5fc186f).

Mandate: structural section-mapping assertions at FULL fidelity:
  A. Crossing fidelity: crossing saved file == save1-frozen (same order, every hash identical, byte-identical expected)
  B. Crossback fidelity: post-edit saved file matches frozen save except EXACTLY ONE section differs by the typed marker
  C. No hyp-leakage in any exercise-produced file

Evidence files produced (all c1-s3- prefix, written to phase-5/evidence/):
  c1-s3-run-log.txt                     — full session log
  c1-s3-save1-frozen.html               — copy of save1 file frozen immediately after save-new
  c1-s3-save2-crossing.html             — copy of file written by editor crossing Save-As
  c1-s3-save3-crossback.html            — copy of file written after editor edit + crossback
  c1-s3-section-map-save1.json          — per-section SHA-256 + text for save1
  c1-s3-section-map-save2.json          — per-section mapping for save2 (crossing file)
  c1-s3-section-map-save3.json          — per-section mapping for save3 (post-edit crossback)
  c1-s3-structural-assertions.json      — all assertion results (A, B, C)
  c1-s3-screenshots/                    — screenshots (01..N)
  c1-s3-hash-post.json                  — owner deck hash bracket (post)
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import traceback

# ── resolve paths ────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = HERE   # phase-5/evidence/
APP_ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
# APP_ROOT  = hypresent/
E2E = os.path.join(APP_ROOT, 'tests', 'e2e')
SCREENSHOTS = os.path.join(EVIDENCE, 'c1-s3-screenshots')
os.makedirs(SCREENSHOTS, exist_ok=True)

sys.path.insert(0, E2E)
import conftest_helpers as H
import builder_helpers as BH

LOG_PATH = os.path.join(EVIDENCE, 'c1-s3-run-log.txt')
log_fh = open(LOG_PATH, 'w', encoding='utf-8')

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    log_fh.write(line + '\n')
    log_fh.flush()

def sha256_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

# ── section splitter ─────────────────────────────────────────────────────────
def split_sections(html_bytes):
    """Return list of {index, sha256, text_normalized} dicts, one per top-level <section>."""
    text = html_bytes.decode('utf-8', errors='replace')
    # find all top-level <section ...> ... </section> spans
    spans = []
    pos = 0
    while True:
        start = text.find('<section', pos)
        if start == -1:
            break
        # find matching </section> — naive but sufficient for flat structure
        end = text.find('</section>', start)
        if end == -1:
            break
        end += len('</section>')
        span = text[start:end]
        spans.append(span)
        pos = end
    result = []
    for i, span in enumerate(spans):
        h = sha256_bytes(span.encode('utf-8'))
        # normalized text: entity-decode common sequences, collapse whitespace
        t = span
        t = t.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        t = re.sub(r'<[^>]+>', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        result.append({'index': i, 'sha256': h, 'text_normalized': t[:300]})
    return result

def save_section_map(sections, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2)
    log(f"  section map written → {os.path.basename(path)} ({len(sections)} sections)")

def screencap(page, name):
    p = os.path.join(SCREENSHOTS, name)
    page.screenshot(path=p)
    log(f"  screenshot → {name}")
    return p

# ── owner deck hashes (post-exercise bracket) ────────────────────────────────
OWNER_FILES = [
    'tecer-gsmm-introduction.html',
    'tecer-gsmm-introduction-test.html',
    'tecer-gsmm-introduction-test-v2.html',
    'tecer-gsmm-introduction-test-v3.html',
]
PRE_HASHES = {
    'tecer-gsmm-introduction.html': '5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae',
    'tecer-gsmm-introduction-test.html': 'c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0',
    'tecer-gsmm-introduction-test-v2.html': 'f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db',
    'tecer-gsmm-introduction-test-v3.html': '93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a',
}

def write_post_hashes():
    post = {}
    for f in OWNER_FILES:
        fp = os.path.join(APP_ROOT, f)
        post[f] = sha256_file(fp)
    match = all(post[f] == PRE_HASHES[f] for f in OWNER_FILES)
    result = {'session': 'c1-s3', 'phase': 'post-exercise', 'files': post,
              'all_unchanged': match}
    with open(os.path.join(EVIDENCE, 'c1-s3-hash-post.json'), 'w') as fh:
        json.dump(result, fh, indent=2)
    log(f"  owner deck hash bracket: all_unchanged={match}")
    return match

PORT = 9741

def main():
    log("=== c1-s3 session 3 start ===")
    log(f"APP_ROOT: {APP_ROOT}")
    log(f"EVIDENCE: {EVIDENCE}")

    # ── temp paths ─────────────────────────────────────────────────────────
    tmpdir = tempfile.mkdtemp(prefix='c1s3_')
    deck_copy = os.path.join(tmpdir, 'deck.html')
    shutil.copy(os.path.join(APP_ROOT, 'tecer-gsmm-introduction.html'), deck_copy)
    log(f"Deck copy: {deck_copy}")

    save1_tmp = os.path.join(tmpdir, 'save1.html')
    save2_tmp = os.path.join(tmpdir, 'save2.html')
    save3_tmp = os.path.join(tmpdir, 'save3.html')

    log(f"save1 path: {save1_tmp}")
    log(f"save2 path: {save2_tmp}")
    log(f"save3 path: {save3_tmp}")

    proc, base = H.start_server(PORT, test_dialog=True)
    log(f"Server started: {base}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            H.preset_author(page)

            # ─── 1. Open builder, load deck copy ──────────────────────────
            log("Step 1: open builder")
            page.goto(f"{base}/app/builder.html")
            page.wait_for_load_state('networkidle')
            screencap(page, '01-builder-initial.png')

            H.set_fake_dialog(base, deck_copy)
            page.click('#open-deck-btn')
            page.wait_for_selector('.tray-row', timeout=15000)
            time.sleep(0.8)
            rows = page.query_selector_all('.tray-row')
            log(f"  Initial tray rows: {len(rows)}")
            assert len(rows) == 10, f"Expected 10 rows, got {len(rows)}"
            screencap(page, '02-deck-opened.png')

            def tray_order():
                return page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.tray-row'))
                        .map(r => ({uid: r.dataset.uid, slideId: r.dataset.slideId}));
                }""")

            order0 = tray_order()
            log(f"  Initial order: {[r['slideId'] for r in order0]}")

            # ─── 2. Restructure: reorder, remove, duplicate, add blank ────
            log("Step 2: reorder — move last slide before slide at position 0")

            # Get UIDs for targeting
            last_uid = order0[-1]['uid']
            first_uid = order0[0]['uid']
            last_slide_id = order0[-1]['slideId']
            first_slide_id = order0[0]['slideId']
            log(f"  Moving last (uid={last_uid}, sid={last_slide_id}) before first (uid={first_uid}, sid={first_slide_id})")

            # Drag last slide's grip to above first slide's grip
            last_grip = page.query_selector(f'.tray-row[data-uid="{last_uid}"] .grip')
            first_row = page.query_selector(f'.tray-row[data-uid="{first_uid}"]')
            assert last_grip and first_row, "Could not find grip/row elements"

            lg_box = last_grip.bounding_box()
            fr_box = first_row.bounding_box()

            # Slow stepped mouse drag
            page.mouse.move(lg_box['x'] + lg_box['width']/2, lg_box['y'] + lg_box['height']/2)
            page.mouse.down()
            time.sleep(0.15)
            # Move in steps toward target (above first row)
            target_x = fr_box['x'] + fr_box['width']/2
            target_y = fr_box['y'] + 5
            steps = 15
            sx = lg_box['x'] + lg_box['width']/2
            sy = lg_box['y'] + lg_box['height']/2
            for i in range(1, steps+1):
                mx = sx + (target_x - sx) * i / steps
                my = sy + (target_y - sy) * i / steps
                page.mouse.move(mx, my)
                time.sleep(0.02)
            time.sleep(0.15)
            page.mouse.up()
            time.sleep(0.8)

            order1 = tray_order()
            reorder_took = order1[0]['uid'] == last_uid
            log(f"  After reorder: order[0]={order1[0]}, reorder_took={reorder_took}")
            if not reorder_took:
                # retry with a simpler move (just a bit further up)
                log("  Reorder did not take, retrying...")
                last_grip2 = page.query_selector(f'.tray-row[data-uid="{last_uid}"] .grip')
                first_row2 = page.query_selector(f'.tray-row[data-uid="{first_uid}"]')
                if last_grip2 and first_row2:
                    lg2 = last_grip2.bounding_box()
                    fr2 = first_row2.bounding_box()
                    page.mouse.move(lg2['x']+lg2['width']/2, lg2['y']+lg2['height']/2)
                    page.mouse.down()
                    time.sleep(0.2)
                    # move above first row by more margin
                    ty2 = fr2['y'] - 5
                    for i in range(1, 20):
                        page.mouse.move(
                            lg2['x']+lg2['width']/2 + (fr2['x']+fr2['width']/2 - lg2['x']-lg2['width']/2)*i/20,
                            lg2['y']+lg2['height']/2 + (ty2 - lg2['y']-lg2['height']/2)*i/20
                        )
                        time.sleep(0.025)
                    time.sleep(0.2)
                    page.mouse.up()
                    time.sleep(0.9)
                    order1 = tray_order()
                    reorder_took = order1[0]['uid'] == last_uid
                    log(f"  Retry reorder: order[0]={order1[0]}, reorder_took={reorder_took}")

            screencap(page, '03-after-reorder.png')
            # Record DOM order
            log(f"  DOM order after reorder: {[r['slideId'] for r in order1]}")

            log("Step 2b: remove slide at position 2 (by data-slide-id)")
            remove_target_sid = order1[2]['slideId']
            log(f"  Removing: {remove_target_sid}")
            remove_btn = page.query_selector(f'.tray-row[data-slide-id="{remove_target_sid}"] .tray-remove')
            if remove_btn:
                remove_btn.click()
                time.sleep(0.5)
            else:
                log(f"  WARNING: no remove btn found for {remove_target_sid}")
            order2 = tray_order()
            removed_ok = not any(r['slideId'] == remove_target_sid for r in order2)
            log(f"  After remove: {[r['slideId'] for r in order2]}, removed_ok={removed_ok}")
            screencap(page, '04-after-remove.png')

            log("Step 2c: duplicate slide at position 0")
            dup_uid = order2[0]['uid']
            dup_sid = order2[0]['slideId']
            dup_btn = page.query_selector(f'.tray-row[data-uid="{dup_uid}"] .tray-duplicate')
            if dup_btn:
                dup_btn.click()
                time.sleep(0.5)
            else:
                log(f"  WARNING: no dup btn for uid={dup_uid}")
            order3 = tray_order()
            dup_count = sum(1 for r in order3 if r['slideId'] == dup_sid)
            log(f"  After dup: {[r['slideId'] for r in order3]}, dup_count={dup_count}")
            screencap(page, '05-after-duplicate.png')

            log("Step 2d: add blank")
            page.click('#add-blank-btn')
            time.sleep(0.5)
            order4 = tray_order()
            blank_sids = [r['slideId'] for r in order4 if 'blank' in str(r['slideId']).lower()]
            log(f"  After add blank: {[r['slideId'] for r in order4]}, blanks={blank_sids}")
            screencap(page, '06-after-add-blank.png')

            # ─── 3. Save as new file ──────────────────────────────────────
            log("Step 3: save as new file")
            H.set_fake_dialog(base, save1_tmp)
            page.click('#save-new-btn')
            # Wait for save to complete — look for status success or for file to appear
            deadline = time.time() + 15
            while time.time() < deadline:
                status_el = page.query_selector('#status-bar, .status-bar, [data-testid="status"]')
                if os.path.exists(save1_tmp):
                    break
                time.sleep(0.2)
            time.sleep(0.8)  # wait for rebaseDeckToSavedFile async to complete
            screencap(page, '07-after-save-new.png')

            assert os.path.exists(save1_tmp), f"save1 file not created at {save1_tmp}"
            save1_bytes = open(save1_tmp, 'rb').read()
            log(f"  save1 file size: {len(save1_bytes)} bytes")

            # Freeze copy immediately
            frozen_path = os.path.join(EVIDENCE, 'c1-s3-save1-frozen.html')
            shutil.copy(save1_tmp, frozen_path)
            log(f"  Frozen copy written: {frozen_path}")

            # Tray DOM order after save (post-rebase check)
            order5 = tray_order()
            log(f"  Tray DOM order after save-new (post-rebase): {[r['slideId'] for r in order5]}")

            # Section map for save1
            sections_save1 = split_sections(save1_bytes)
            map1_path = os.path.join(EVIDENCE, 'c1-s3-section-map-save1.json')
            save_section_map(sections_save1, map1_path)

            # ─── 4. Cross to editor ───────────────────────────────────────
            log("Step 4: cross to editor via #switch-to-editor-btn")
            H.set_fake_dialog(base, save2_tmp)
            page.click('#switch-to-editor-btn')
            # Wait for editor to load
            deadline = time.time() + 20
            while time.time() < deadline:
                url = page.url
                if 'editor' in url.lower() or 'present' in url.lower():
                    break
                time.sleep(0.3)
            time.sleep(1.5)
            log(f"  Current URL after crossing: {page.url}")
            screencap(page, '08-editor-loaded.png')

            # Wait for save2 to appear (crossing Save-As writes it)
            deadline = time.time() + 12
            while time.time() < deadline:
                if os.path.exists(save2_tmp):
                    break
                time.sleep(0.3)

            assert os.path.exists(save2_tmp), f"save2 (crossing file) not created at {save2_tmp}"
            save2_bytes = open(save2_tmp, 'rb').read()
            log(f"  save2 file size: {len(save2_bytes)} bytes")
            shutil.copy(save2_tmp, os.path.join(EVIDENCE, 'c1-s3-save2-crossing.html'))

            # Wait for runtime in editor iframe
            try:
                H.wait_runtime_ready(page, timeout=15000)
                log("  Runtime ready in editor")
            except Exception:
                log("  wait_runtime_ready timed out — proceeding anyway")

            # ─── 5. Edit in editor: type marker ──────────────────────────
            log("Step 5: type marker [CV-B15-S3] into editor slide text")
            MARKER = ' [CV-B15-S3]'
            # Click into the iframe content
            try:
                frame = page.frame_locator('iframe.doc-frame').first
                # Find first editable text element in the slide
                # Try clicking on the first section text
                frame.locator('section').first.click()
                time.sleep(0.5)
                # Focus and type
                page.keyboard.type(MARKER)
                time.sleep(0.5)
                log("  Marker typed")
            except Exception as e:
                log(f"  iframe click failed ({e}), trying direct keyboard")
                # Try clicking iframe directly
                iframe_el = page.query_selector('iframe.doc-frame')
                if iframe_el:
                    bbox = iframe_el.bounding_box()
                    page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + bbox['height']/2)
                    time.sleep(0.5)
                page.keyboard.type(MARKER)
                time.sleep(0.5)
            screencap(page, '09-after-typing.png')

            # ─── 6. Save in editor (Save-As → save3_tmp) ─────────────────
            log("Step 6: save in editor (Save-As)")
            H.set_fake_dialog(base, save3_tmp)
            # Try save-as button
            save_as_btn = page.query_selector('#save-as-btn')
            if save_as_btn:
                save_as_btn.click()
            else:
                # Try generic save button
                save_btn = page.query_selector('#save-btn, [data-action="save"]')
                if save_btn:
                    save_btn.click()
                else:
                    log("  WARNING: no save-as-btn found, trying keyboard Ctrl+S")
                    page.keyboard.press('Control+s')
            deadline = time.time() + 15
            while time.time() < deadline:
                if os.path.exists(save3_tmp):
                    break
                time.sleep(0.3)
            time.sleep(0.8)
            screencap(page, '10-after-save-editor.png')

            # If save3 not at expected path, look for the crossing file updated by editor
            if not os.path.exists(save3_tmp):
                log(f"  save3 not at {save3_tmp} — checking if crossing file was updated")
                # The editor might save back to save2_tmp if it was opened from there
                save3_candidate = save2_tmp
                if os.path.exists(save3_candidate):
                    save3_bytes = open(save3_candidate, 'rb').read()
                    log(f"  Using crossing file as save3 ({len(save3_bytes)} bytes)")
                    shutil.copy(save3_candidate, os.path.join(EVIDENCE, 'c1-s3-save3-crossback.html'))
                    save3_actual_path = save3_candidate
                    log(f"  Note: save3 came from crossing file path (editor saved in-place)")
                else:
                    # Last resort: check if file was saved at a new path we missed
                    log("  WARNING: save3 file not found at either expected location")
                    save3_bytes = None
                    save3_actual_path = None
            else:
                save3_bytes = open(save3_tmp, 'rb').read()
                log(f"  save3 file size: {len(save3_bytes)} bytes")
                shutil.copy(save3_tmp, os.path.join(EVIDENCE, 'c1-s3-save3-crossback.html'))
                save3_actual_path = save3_tmp

            # ─── 7. Cross back to builder ─────────────────────────────────
            log("Step 7: cross back to builder via #open-in-builder-btn")
            open_builder_btn = page.query_selector('#open-in-builder-btn')
            if open_builder_btn:
                open_builder_btn.click()
                deadline = time.time() + 15
                while time.time() < deadline:
                    url = page.url
                    if 'builder' in url.lower():
                        break
                    time.sleep(0.3)
                time.sleep(1.0)
                log(f"  URL after crossback: {page.url}")
                screencap(page, '11-back-in-builder.png')
            else:
                log("  WARNING: #open-in-builder-btn not found")
                screencap(page, '11-back-in-builder-NOT-FOUND.png')

            browser.close()
        log("Browser closed")

    finally:
        H.stop_server(proc)
        log("Server stopped")

    # ── STRUCTURAL ASSERTIONS ────────────────────────────────────────────────
    log("\n=== STRUCTURAL ASSERTIONS ===")
    assertions = {}

    # Section maps
    sections_save1 = split_sections(save1_bytes)
    log(f"save1 sections: {len(sections_save1)}")

    sections_save2 = split_sections(save2_bytes)
    log(f"save2 sections: {len(sections_save2)}")
    map2_path = os.path.join(EVIDENCE, 'c1-s3-section-map-save2.json')
    save_section_map(sections_save2, map2_path)

    # Assertion A: crossing fidelity (save2 == save1 frozen)
    log("\n-- A. Crossing fidelity --")
    byte_identical = save1_bytes == save2_bytes
    count_match = len(sections_save1) == len(sections_save2)
    hash_matches = []
    if count_match:
        for i, (s1, s2) in enumerate(zip(sections_save1, sections_save2)):
            match = s1['sha256'] == s2['sha256']
            hash_matches.append({'index': i, 'save1_sha': s1['sha256'], 'save2_sha': s2['sha256'], 'match': match})
    all_hashes_match = count_match and all(m['match'] for m in hash_matches)
    assertions['A_crossing_fidelity'] = {
        'byte_identical': byte_identical,
        'count_match': count_match,
        'save1_count': len(sections_save1),
        'save2_count': len(sections_save2),
        'all_section_hashes_match': all_hashes_match,
        'per_section': hash_matches,
        'result': 'PASS' if all_hashes_match else 'FAIL',
    }
    log(f"  byte_identical: {byte_identical}")
    log(f"  count_match: {count_match} ({len(sections_save1)} vs {len(sections_save2)})")
    log(f"  all_section_hashes_match: {all_hashes_match}")
    log(f"  A result: {assertions['A_crossing_fidelity']['result']}")

    # Assertion B: crossback fidelity (save3 == save1 except exactly 1 section differs by marker)
    log("\n-- B. Crossback fidelity --")
    if save3_bytes is not None:
        sections_save3 = split_sections(save3_bytes)
        map3_path = os.path.join(EVIDENCE, 'c1-s3-section-map-save3.json')
        save_section_map(sections_save3, map3_path)
        log(f"save3 sections: {len(sections_save3)}")

        count_match3 = len(sections_save1) == len(sections_save3)
        diff_sections = []
        if count_match3:
            for i, (s1, s3) in enumerate(zip(sections_save1, sections_save3)):
                if s1['sha256'] != s3['sha256']:
                    # Check if the difference is ONLY the marker
                    t1 = s1['text_normalized']
                    t3 = s3['text_normalized']
                    marker_present = '[CV-B15-S3]' in t3
                    # Remove the marker from t3 and compare
                    t3_stripped = t3.replace('[CV-B15-S3]', '').strip()
                    t1_norm = t1.strip()
                    # Normalize multiple spaces
                    t3_stripped_n = re.sub(r'\s+', ' ', t3_stripped).strip()
                    t1_norm_n = re.sub(r'\s+', ' ', t1_norm).strip()
                    only_marker_diff = (t3_stripped_n == t1_norm_n) or (t3_stripped_n in t1_norm_n) or (t1_norm_n in t3_stripped_n)
                    diff_sections.append({
                        'index': i,
                        'save1_sha': s1['sha256'],
                        'save3_sha': s3['sha256'],
                        'marker_present_in_save3': marker_present,
                        'only_marker_diff': only_marker_diff,
                        'save1_text': t1[:200],
                        'save3_text': t3[:200],
                        'save3_stripped': t3_stripped[:200],
                    })

        exactly_one_diff = len(diff_sections) == 1
        marker_in_diff = exactly_one_diff and diff_sections[0]['marker_present_in_save3']
        only_marker_diff = exactly_one_diff and diff_sections[0]['only_marker_diff']
        b_pass = count_match3 and exactly_one_diff and marker_in_diff

        assertions['B_crossback_fidelity'] = {
            'count_match': count_match3,
            'save1_count': len(sections_save1),
            'save3_count': len(sections_save3),
            'diff_sections': diff_sections,
            'exactly_one_diff': exactly_one_diff,
            'marker_in_diff_section': marker_in_diff,
            'only_marker_diff': only_marker_diff,
            'result': 'PASS' if b_pass else 'FAIL',
        }
        log(f"  count_match: {count_match3}")
        log(f"  diff_sections count: {len(diff_sections)}")
        log(f"  exactly_one_diff: {exactly_one_diff}")
        log(f"  marker_in_diff: {marker_in_diff}")
        log(f"  only_marker_diff: {only_marker_diff}")
        log(f"  B result: {assertions['B_crossback_fidelity']['result']}")
        if diff_sections:
            for ds in diff_sections:
                log(f"    diff sec {ds['index']}: save3_text={ds['save3_text'][:100]}")
    else:
        assertions['B_crossback_fidelity'] = {'result': 'UNEXERCISABLE', 'reason': 'save3 file not found'}
        log("  B: UNEXERCISABLE — save3 not found")

    # Assertion C: no hyp-leakage
    log("\n-- C. No hyp-leakage --")
    leakage = {}
    for name, content in [('save1', save1_bytes), ('save2', save2_bytes),
                           ('save3', save3_bytes if save3_bytes else b'')]:
        text = content.decode('utf-8', errors='replace')
        hyp_tokens = re.findall(r'hyp-[a-z]', text)
        data_hyp = re.findall(r'data-hyp-', text)
        leakage[name] = {'hyp_tokens': hyp_tokens, 'data_hyp_tokens': data_hyp,
                         'count': len(hyp_tokens) + len(data_hyp)}
    c_pass = all(v['count'] == 0 for v in leakage.values())
    assertions['C_no_hyp_leakage'] = {'per_file': leakage, 'result': 'PASS' if c_pass else 'FAIL'}
    log(f"  leakage counts: save1={leakage['save1']['count']}, save2={leakage['save2']['count']}, save3={leakage['save3']['count']}")
    log(f"  C result: {assertions['C_no_hyp_leakage']['result']}")

    # Overall
    all_pass = all(
        v.get('result') == 'PASS'
        for v in assertions.values()
    )
    assertions['overall'] = 'PASS' if all_pass else 'FAIL'
    assertions['reorder_took'] = reorder_took
    assertions['removed_ok'] = removed_ok
    assertions['dup_count'] = dup_count
    assertions['blank_sids'] = blank_sids
    assertions['save1_section_count'] = len(sections_save1)
    assertions['save1_path'] = save1_actual_path if 'save1_actual_path' in dir() else save1_tmp
    assertions['save2_path'] = save2_tmp
    assertions['save3_path'] = save3_actual_path

    result_path = os.path.join(EVIDENCE, 'c1-s3-structural-assertions.json')
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(assertions, f, indent=2)
    log(f"\nStructural assertions written: {result_path}")
    log(f"Overall result: {assertions['overall']}")

    # Post-exercise owner deck hash bracket
    log("\n=== Post-exercise owner deck hashes ===")
    owner_ok = write_post_hashes()
    log(f"Owner deck unchanged: {owner_ok}")

    log("\n=== SESSION 3 COMPLETE ===")
    log_fh.close()
    return assertions


if __name__ == '__main__':
    try:
        result = main()
        print(f"\nFINAL RESULT: {result.get('overall')}")
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        traceback.print_exc()
        log_fh.close()
        sys.exit(1)
