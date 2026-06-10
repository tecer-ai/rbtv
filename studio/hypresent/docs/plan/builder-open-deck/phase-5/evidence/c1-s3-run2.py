"""
c1-s3-run2.py  —  Cold Verifier Session 3, Run 2
Focus: properly type marker into editor slide (corrected iframe focus gesture),
then capture save3 with marker present.
Produces c1-s3-r2-* evidence files.
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

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = HERE
APP_ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
E2E = os.path.join(APP_ROOT, 'tests', 'e2e')
SCREENSHOTS = os.path.join(EVIDENCE, 'c1-s3-r2-screenshots')
os.makedirs(SCREENSHOTS, exist_ok=True)

sys.path.insert(0, E2E)
import conftest_helpers as H

LOG_PATH = os.path.join(EVIDENCE, 'c1-s3-r2-log.txt')
log_fh = open(LOG_PATH, 'w', encoding='utf-8')

def log(msg):
    ts = time.strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    log_fh.write(line + '\n')
    log_fh.flush()

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def split_sections(html_bytes):
    text = html_bytes.decode('utf-8', errors='replace')
    spans = []
    pos = 0
    while True:
        start = text.find('<section', pos)
        if start == -1:
            break
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
    log(f"  screenshot → c1-s3-r2-screenshots/{name}")
    return p

PORT = 9743
MARKER = ' [CV-B15-S3]'

PRE_HASHES = {
    'tecer-gsmm-introduction.html': '5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae',
    'tecer-gsmm-introduction-test.html': 'c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0',
    'tecer-gsmm-introduction-test-v2.html': 'f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db',
    'tecer-gsmm-introduction-test-v3.html': '93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a',
}

def main():
    log("=== c1-s3 run2 start ===")

    tmpdir = tempfile.mkdtemp(prefix='c1s3r2_')
    deck_copy = os.path.join(tmpdir, 'deck.html')
    shutil.copy(os.path.join(APP_ROOT, 'tecer-gsmm-introduction.html'), deck_copy)

    save1_tmp = os.path.join(tmpdir, 'r2save1.html')
    save2_tmp = os.path.join(tmpdir, 'r2save2.html')
    save3_tmp = os.path.join(tmpdir, 'r2save3.html')
    log(f"tmpdir: {tmpdir}")

    proc, base = H.start_server(PORT, test_dialog=True)
    log(f"Server: {base}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            H.preset_author(page)

            # 1. Open builder, load deck
            log("Step 1: open builder + load deck")
            page.goto(f"{base}/app/builder.html")
            page.wait_for_load_state('networkidle')
            H.set_fake_dialog(base, deck_copy)
            page.click('#open-deck-btn')
            page.wait_for_selector('.tray-row', timeout=15000)
            time.sleep(0.8)
            rows = page.query_selector_all('.tray-row')
            log(f"  rows: {len(rows)}")
            assert len(rows) == 10
            screencap(page, '01-opened.png')

            def tray_order():
                return page.evaluate("""() =>
                    Array.from(document.querySelectorAll('.tray-row'))
                        .map(r => ({uid: r.dataset.uid, sid: r.dataset.slideId}))
                """)

            order0 = tray_order()
            log(f"  initial: {[r['sid'] for r in order0]}")

            # 2. Restructure: remove sec-2, duplicate sec-0, add blank
            # (skip drag since it was timing-fragile — do remove+dup+blank to displace indices)
            log("Step 2: remove sec-2")
            remove_sid = order0[2]['sid']
            btn = page.query_selector(f'.tray-row[data-slide-id="{remove_sid}"] .tray-remove')
            btn.click()
            time.sleep(0.5)
            order1 = tray_order()
            removed = not any(r['sid'] == remove_sid for r in order1)
            log(f"  removed {remove_sid}: {removed}, order: {[r['sid'] for r in order1]}")
            screencap(page, '02-removed.png')

            log("Step 2b: duplicate sec-0 (now at pos 0)")
            dup_uid = order1[0]['uid']
            dup_sid = order1[0]['sid']
            dup_btn = page.query_selector(f'.tray-row[data-uid="{dup_uid}"] .tray-duplicate')
            dup_btn.click()
            time.sleep(0.5)
            order2 = tray_order()
            dup_count = sum(1 for r in order2 if r['sid'] == dup_sid)
            log(f"  dup {dup_sid}: count={dup_count}, order: {[r['sid'] for r in order2]}")
            screencap(page, '03-dup.png')

            log("Step 2c: add blank")
            page.click('#add-blank-btn')
            time.sleep(0.5)
            order3 = tray_order()
            blanks = [r['sid'] for r in order3 if 'blank' in str(r['sid'])]
            log(f"  blanks: {blanks}, total rows: {len(order3)}")
            screencap(page, '04-blank.png')

            # 3. Save as new file
            log("Step 3: save-new")
            H.set_fake_dialog(base, save1_tmp)
            page.click('#save-new-btn')
            deadline = time.time() + 15
            while time.time() < deadline:
                if os.path.exists(save1_tmp):
                    break
                time.sleep(0.2)
            time.sleep(1.0)  # wait for rebaseDeckToSavedFile to complete
            assert os.path.exists(save1_tmp), "save1 not created"
            save1_bytes = open(save1_tmp, 'rb').read()
            log(f"  save1: {len(save1_bytes)} bytes")
            # Tray order post-rebase
            order4 = tray_order()
            log(f"  tray after save-new (post-rebase): {[r['sid'] for r in order4]}")
            screencap(page, '05-saved.png')

            # Freeze copy
            frozen_path = os.path.join(EVIDENCE, 'c1-s3-r2-save1-frozen.html')
            shutil.copy(save1_tmp, frozen_path)
            sections_save1 = split_sections(save1_bytes)
            save_section_map(sections_save1, os.path.join(EVIDENCE, 'c1-s3-r2-map-save1.json'))

            # 4. Cross to editor
            log("Step 4: cross to editor")
            H.set_fake_dialog(base, save2_tmp)
            page.click('#switch-to-editor-btn')
            # Wait for navigation to editor
            deadline = time.time() + 20
            while time.time() < deadline:
                if 'app/' in page.url and 'builder' not in page.url:
                    break
                if os.path.exists(save2_tmp):
                    break
                time.sleep(0.3)
            time.sleep(2.0)
            log(f"  URL after crossing: {page.url}")
            screencap(page, '06-editor.png')

            # Wait for save2 to appear
            deadline = time.time() + 15
            while time.time() < deadline:
                if os.path.exists(save2_tmp):
                    break
                time.sleep(0.3)
            assert os.path.exists(save2_tmp), "save2 not created"
            save2_bytes = open(save2_tmp, 'rb').read()
            log(f"  save2: {len(save2_bytes)} bytes, byte_identical_to_save1: {save2_bytes==save1_bytes}")

            # Wait for runtime
            try:
                H.wait_runtime_ready(page, timeout=20000)
                log("  runtime ready")
            except Exception as e:
                log(f"  wait_runtime_ready: {e} — continuing")

            time.sleep(1.5)

            # 5. Type marker into editor
            log("Step 5: type marker into editor")
            # Strategy: use JavaScript to focus a text node in the iframe, then use keyboard
            # First find the iframe
            iframe_el = page.query_selector('iframe.doc-frame')
            if iframe_el:
                # Click in the MIDDLE of the iframe (over first slide visible area)
                bbox = iframe_el.bounding_box()
                log(f"  iframe bbox: {bbox}")
                # Click inside the iframe at a text area
                page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + 100)
                time.sleep(0.5)
                screencap(page, '07-iframe-clicked.png')
                # Now try to focus using evaluate + execCommand
                try:
                    page.evaluate("""() => {
                        const f = document.querySelector('iframe.doc-frame');
                        if (!f) return;
                        const doc = f.contentDocument;
                        const win = f.contentWindow;
                        // Find first contenteditable or focusable element
                        const editable = doc.querySelector('[contenteditable=true]');
                        if (editable) {
                            editable.focus();
                            const sel = win.getSelection();
                            const range = doc.createRange();
                            // Select end of first text node in first section
                            const section = doc.querySelector('section');
                            if (section) {
                                const walker = doc.createTreeWalker(section, NodeFilter.SHOW_TEXT);
                                const textNode = walker.nextNode();
                                if (textNode) {
                                    range.setStart(textNode, textNode.length);
                                    range.collapse(true);
                                    sel.removeAllRanges();
                                    sel.addRange(range);
                                }
                            }
                        }
                    }""")
                    time.sleep(0.3)
                    log("  iframe content focused via JS")
                except Exception as e:
                    log(f"  JS focus failed: {e}")

                # Re-click into the iframe to ensure focus
                page.mouse.click(bbox['x'] + bbox['width']/2, bbox['y'] + 120)
                time.sleep(0.4)

            # Type the marker
            page.keyboard.type(MARKER)
            time.sleep(0.5)
            screencap(page, '08-typed.png')

            # Verify marker is in iframe DOM
            marker_in_dom = False
            try:
                marker_in_dom = page.evaluate("""() => {
                    const f = document.querySelector('iframe.doc-frame');
                    if (!f) return false;
                    return f.contentDocument.body.innerText.includes('[CV-B15-S3]');
                }""")
            except Exception as e:
                log(f"  marker check eval error: {e}")
            log(f"  marker in iframe DOM: {marker_in_dom}")

            # If marker not in DOM, try a different approach: click on a known text element
            if not marker_in_dom:
                log("  Trying alternative: click on iframe + use Ctrl+End to go to end, then type")
                try:
                    iframe_el2 = page.query_selector('iframe.doc-frame')
                    bbox2 = iframe_el2.bounding_box()
                    # Click toward bottom of first visible section
                    page.mouse.click(bbox2['x'] + 100, bbox2['y'] + 80)
                    time.sleep(0.4)
                    page.keyboard.press('Control+End')
                    time.sleep(0.2)
                    page.keyboard.type(MARKER)
                    time.sleep(0.5)
                    marker_in_dom = page.evaluate("""() => {
                        const f = document.querySelector('iframe.doc-frame');
                        if (!f) return false;
                        return f.contentDocument.body.innerText.includes('[CV-B15-S3]');
                    }""")
                    log(f"  marker in DOM after retry: {marker_in_dom}")
                except Exception as e:
                    log(f"  retry failed: {e}")

            screencap(page, '09-post-typing.png')

            # 6. Save in editor
            log("Step 6: save in editor")
            H.set_fake_dialog(base, save3_tmp)
            save_as_btn = page.query_selector('#save-as-btn')
            if save_as_btn:
                save_as_btn.click()
                log("  clicked #save-as-btn")
            else:
                log("  #save-as-btn not found, using Ctrl+Shift+S")
                page.keyboard.press('Control+Shift+S')

            deadline = time.time() + 15
            while time.time() < deadline:
                if os.path.exists(save3_tmp):
                    break
                time.sleep(0.3)
            time.sleep(0.8)
            screencap(page, '10-saved-editor.png')

            if os.path.exists(save3_tmp):
                save3_bytes = open(save3_tmp, 'rb').read()
                log(f"  save3: {len(save3_bytes)} bytes")
                save3_actual = save3_tmp
            else:
                # The editor might have saved over save2 OR to a new path
                # Check if save2 was modified
                save2_now = open(save2_tmp, 'rb').read()
                if save2_now != save2_bytes:
                    log("  save3 not at expected path; save2 was modified by editor save")
                    save3_bytes = save2_now
                    save3_actual = save2_tmp
                else:
                    log("  WARNING: save3 not created and save2 unchanged")
                    save3_bytes = None
                    save3_actual = None

            if save3_bytes:
                shutil.copy(save3_actual, os.path.join(EVIDENCE, 'c1-s3-r2-save3.html'))
                marker_in_file = MARKER.strip() in save3_bytes.decode('utf-8', errors='replace')
                log(f"  marker in save3 file: {marker_in_file}")

            # 7. Cross back to builder
            log("Step 7: crossback to builder")
            open_builder_btn = page.query_selector('#open-in-builder-btn')
            if open_builder_btn:
                open_builder_btn.click()
                deadline = time.time() + 15
                while time.time() < deadline:
                    if 'builder' in page.url:
                        break
                    time.sleep(0.3)
                time.sleep(1.0)
                log(f"  URL: {page.url}")
                screencap(page, '11-crossback.png')
            else:
                log("  WARNING: #open-in-builder-btn not found")
                screencap(page, '11-crossback-NOT-FOUND.png')

            browser.close()

    finally:
        H.stop_server(proc)
        log("Server stopped")

    # STRUCTURAL ASSERTIONS
    log("\n=== STRUCTURAL ASSERTIONS (Run 2) ===")
    assertions = {}

    sections_save1 = split_sections(save1_bytes)
    sections_save2 = split_sections(save2_bytes)
    save_section_map(sections_save2, os.path.join(EVIDENCE, 'c1-s3-r2-map-save2.json'))

    # A: crossing fidelity
    log("\n-- A. Crossing fidelity --")
    byte_identical = save1_bytes == save2_bytes
    count_match = len(sections_save1) == len(sections_save2)
    hash_matches = []
    if count_match:
        for i, (s1, s2) in enumerate(zip(sections_save1, sections_save2)):
            match = s1['sha256'] == s2['sha256']
            hash_matches.append({'index': i, 's1': s1['sha256'], 's2': s2['sha256'], 'match': match})
    all_hashes_match = count_match and all(m['match'] for m in hash_matches)
    assertions['A'] = {
        'byte_identical': byte_identical,
        'count_match': count_match,
        'save1_count': len(sections_save1),
        'save2_count': len(sections_save2),
        'all_section_hashes_match': all_hashes_match,
        'result': 'PASS' if all_hashes_match else 'FAIL',
    }
    log(f"  byte_identical={byte_identical}, count_match={count_match}, all_hashes_match={all_hashes_match}")
    log(f"  A: {assertions['A']['result']}")

    # B: crossback fidelity
    log("\n-- B. Crossback fidelity --")
    if save3_bytes is not None:
        sections_save3 = split_sections(save3_bytes)
        save_section_map(sections_save3, os.path.join(EVIDENCE, 'c1-s3-r2-map-save3.json'))
        log(f"  save3 sections: {len(sections_save3)}")
        count_match3 = len(sections_save1) == len(sections_save3)
        diff_sections = []
        if count_match3:
            for i, (s1, s3) in enumerate(zip(sections_save1, sections_save3)):
                if s1['sha256'] != s3['sha256']:
                    t1 = s1['text_normalized']
                    t3 = s3['text_normalized']
                    marker_present = '[CV-B15-S3]' in t3
                    t3_stripped = re.sub(r'\s+', ' ', t3.replace('[CV-B15-S3]', '').replace(MARKER.strip(), '').strip())
                    t1_norm = re.sub(r'\s+', ' ', t1.strip())
                    only_marker = (t3_stripped == t1_norm)
                    diff_sections.append({
                        'index': i, 's1_sha': s1['sha256'], 's3_sha': s3['sha256'],
                        'marker_present': marker_present, 'only_marker_diff': only_marker,
                        's1_text': t1[:200], 's3_text': t3[:200],
                    })

        marker_in_save3_file = MARKER.strip() in save3_bytes.decode('utf-8', errors='replace')
        exactly_one_diff = len(diff_sections) == 1
        # Check if all diffs are ONLY serialization (same normalized text)
        # even if marker didn't land
        secs_norm_same = count_match3 and all(
            re.sub(r'\s+', ' ', sections_save1[i]['text_normalized'].strip()) ==
            re.sub(r'\s+', ' ', sections_save3[i]['text_normalized'].strip())
            for i in range(len(sections_save1))
        )

        marker_ok = exactly_one_diff and diff_sections[0].get('marker_present') and diff_sections[0].get('only_marker_diff')
        b_result = 'PASS' if (count_match3 and marker_ok) else ('FAIL_NO_MARKER' if (count_match3 and secs_norm_same and not marker_in_save3_file) else 'FAIL')
        assertions['B'] = {
            'count_match': count_match3,
            'save1_count': len(sections_save1),
            'save3_count': len(sections_save3),
            'diff_sections_count': len(diff_sections),
            'diff_sections': diff_sections,
            'exactly_one_diff': exactly_one_diff,
            'marker_in_save3_file': marker_in_save3_file,
            'all_secs_normalized_text_same': secs_norm_same,
            'result': b_result,
        }
        log(f"  count_match={count_match3}, diff_count={len(diff_sections)}, marker_in_file={marker_in_save3_file}")
        log(f"  all_secs_normalized_same={secs_norm_same}")
        log(f"  B: {b_result}")
    else:
        assertions['B'] = {'result': 'UNEXERCISABLE', 'reason': 'save3 file not found'}
        log("  B: UNEXERCISABLE")

    # C: no hyp-leakage
    log("\n-- C. No hyp-leakage --")
    leakage = {}
    for name, content in [('save1', save1_bytes), ('save2', save2_bytes),
                           ('save3', save3_bytes if save3_bytes else b'')]:
        text = content.decode('utf-8', errors='replace')
        ht = re.findall(r'hyp-[a-z]', text)
        dh = re.findall(r'data-hyp-', text)
        leakage[name] = {'hyp': ht, 'data_hyp': dh, 'count': len(ht)+len(dh)}
    c_pass = all(v['count'] == 0 for v in leakage.values())
    assertions['C'] = {'per_file': leakage, 'result': 'PASS' if c_pass else 'FAIL'}
    log(f"  leakage: {leakage}")
    log(f"  C: {assertions['C']['result']}")

    assertions['reorder_skipped_drag_fragile'] = True
    assertions['removed_ok'] = removed
    assertions['dup_count'] = dup_count
    assertions['blank_count'] = len(blanks)
    assertions['save1_section_count'] = len(sections_save1)
    assertions['save3_actual_path'] = save3_actual if save3_bytes else None

    out_path = os.path.join(EVIDENCE, 'c1-s3-r2-assertions.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(assertions, f, indent=2)
    log(f"\nAssertions written: {out_path}")

    # Post owner hashes
    post = {}
    for fn in PRE_HASHES:
        post[fn] = hashlib.sha256(open(os.path.join(APP_ROOT, fn), 'rb').read()).hexdigest()
    all_ok = all(post[f] == PRE_HASHES[f] for f in PRE_HASHES)
    with open(os.path.join(EVIDENCE, 'c1-s3-r2-hash-post.json'), 'w') as f:
        json.dump({'phase': 'run2-post', 'files': post, 'all_unchanged': all_ok}, f, indent=2)
    log(f"  Owner deck unchanged: {all_ok}")

    log("\n=== RUN 2 COMPLETE ===")
    log_fh.close()
    return assertions


if __name__ == '__main__':
    try:
        r = main()
        print(f"\nA={r.get('A',{}).get('result')} B={r.get('B',{}).get('result')} C={r.get('C',{}).get('result')}")
    except Exception as e:
        log(f"FATAL: {e}")
        traceback.print_exc()
        log_fh.close()
        sys.exit(1)
