"""
c1-s3-run3.py  —  Cold Verifier Session 3, Run 3
Fix: use page.wait_for_url to correctly wait for the editor URL
before typing the marker.
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
SCREENSHOTS = os.path.join(EVIDENCE, 'c1-s3-r3-screenshots')
os.makedirs(SCREENSHOTS, exist_ok=True)

sys.path.insert(0, E2E)
import conftest_helpers as H

LOG_PATH = os.path.join(EVIDENCE, 'c1-s3-r3-log.txt')
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
        if start == -1: break
        end = text.find('</section>', start)
        if end == -1: break
        end += len('</section>')
        spans.append(text[start:end])
        pos = end
    result = []
    for i, span in enumerate(spans):
        h = sha256_bytes(span.encode('utf-8'))
        t = span.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        t = re.sub(r'<[^>]+>', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        result.append({'index': i, 'sha256': h, 'text_normalized': t[:300]})
    return result

def save_section_map(sections, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2)
    log(f"  section map → {os.path.basename(path)} ({len(sections)} secs)")

def screencap(page, name):
    p = os.path.join(SCREENSHOTS, name)
    page.screenshot(path=p)
    log(f"  screenshot → {name}")

PORT = 9745
MARKER = ' [CV-B15-S3]'

PRE_HASHES = {
    'tecer-gsmm-introduction.html': '5733924338571f3246b49c38e1ac6af7c210ef372fb1948c383d0026583332ae',
    'tecer-gsmm-introduction-test.html': 'c2f2df5e61f37f70b8ac10ab74a5d91bae8cf51f95a4d4dea731611c62e6ecb0',
    'tecer-gsmm-introduction-test-v2.html': 'f496f6373d21fcd981cf00139a6954284280f5c049a9f7d0c48c05dd5db519db',
    'tecer-gsmm-introduction-test-v3.html': '93b2e53b22d284f5d7b7781da3d05d5ed6a3289625467160c45ee4d2e2a9ad4a',
}


def main():
    log("=== c1-s3 run3 start ===")

    tmpdir = tempfile.mkdtemp(prefix='c1s3r3_')
    deck_copy = os.path.join(tmpdir, 'deck.html')
    shutil.copy(os.path.join(APP_ROOT, 'tecer-gsmm-introduction.html'), deck_copy)
    save1_tmp = os.path.join(tmpdir, 'r3save1.html')
    save2_tmp = os.path.join(tmpdir, 'r3save2.html')
    save3_tmp = os.path.join(tmpdir, 'r3save3.html')
    log(f"tmpdir: {tmpdir}")

    proc, base = H.start_server(PORT, test_dialog=True)
    log(f"Server: {base}")

    save1_bytes = None
    save2_bytes = None
    save3_bytes = None
    save3_actual = None
    removed = False
    dup_count = 0
    blanks = []

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context()
            page = context.new_page()
            H.preset_author(page)

            # 1. Open builder + load deck
            log("Step 1: builder + deck")
            page.goto(f"{base}/app/builder.html")
            page.wait_for_load_state('networkidle')
            H.set_fake_dialog(base, deck_copy)
            page.click('#open-deck-btn')
            page.wait_for_selector('.tray-row', timeout=15000)
            time.sleep(1.0)
            rows = page.query_selector_all('.tray-row')
            assert len(rows) == 10, f"Expected 10 rows, got {len(rows)}"
            log(f"  rows: {len(rows)}")
            screencap(page, '01-opened.png')

            def tray_order():
                return page.evaluate("""() =>
                    Array.from(document.querySelectorAll('.tray-row'))
                        .map(r => ({uid: r.dataset.uid, sid: r.dataset.slideId}))
                """)

            order0 = tray_order()
            log(f"  initial: {[r['sid'] for r in order0]}")

            # 2. Restructure
            log("Step 2a: remove sec-2")
            remove_sid = order0[2]['sid']
            btn = page.query_selector(f'.tray-row[data-slide-id="{remove_sid}"] .tray-remove')
            btn.click()
            time.sleep(0.6)
            order1 = tray_order()
            removed = not any(r['sid'] == remove_sid for r in order1)
            log(f"  removed {remove_sid}: {removed}")
            screencap(page, '02-removed.png')

            log("Step 2b: duplicate sec-0")
            dup_uid = order1[0]['uid']
            dup_sid = order1[0]['sid']
            dup_btn = page.query_selector(f'.tray-row[data-uid="{dup_uid}"] .tray-duplicate')
            dup_btn.click()
            time.sleep(0.6)
            order2 = tray_order()
            dup_count = sum(1 for r in order2 if r['sid'] == dup_sid)
            log(f"  dup {dup_sid}: count={dup_count}")
            screencap(page, '03-dup.png')

            log("Step 2c: add blank")
            page.click('#add-blank-btn')
            time.sleep(0.6)
            order3 = tray_order()
            blanks = [r['sid'] for r in order3 if 'blank' in str(r['sid'])]
            log(f"  blanks: {blanks}, rows: {len(order3)}")
            screencap(page, '04-blank.png')

            # 3. Save new
            log("Step 3: save-new")
            H.set_fake_dialog(base, save1_tmp)
            page.click('#save-new-btn')
            deadline = time.time() + 20
            while time.time() < deadline:
                if os.path.exists(save1_tmp):
                    break
                time.sleep(0.2)
            time.sleep(1.5)  # wait for rebaseDeckToSavedFile (async)
            assert os.path.exists(save1_tmp), "save1 not created"
            save1_bytes = open(save1_tmp, 'rb').read()
            log(f"  save1: {len(save1_bytes)} bytes")
            order4 = tray_order()
            log(f"  tray post-save (post-rebase): {[r['sid'] for r in order4]}")
            screencap(page, '05-saved.png')

            frozen_path = os.path.join(EVIDENCE, 'c1-s3-r3-save1-frozen.html')
            shutil.copy(save1_tmp, frozen_path)
            sections_save1 = split_sections(save1_bytes)
            save_section_map(sections_save1, os.path.join(EVIDENCE, 'c1-s3-r3-map-save1.json'))

            # 4. Cross to editor — wait for editor URL explicitly
            log("Step 4: cross to editor")
            H.set_fake_dialog(base, save2_tmp)
            page.click('#switch-to-editor-btn')

            # Wait explicitly for the editor URL pattern (/app/ without builder)
            # The editor URL is /app/?file=... (index.html)
            try:
                page.wait_for_url(
                    re.compile(r'/app/\?file='),
                    timeout=15000
                )
                log(f"  EDITOR URL detected: {page.url}")
            except Exception as e:
                log(f"  wait_for_url failed: {e}, current URL: {page.url}")
                # If we already have the editor URL that's fine
                if '?file=' in page.url and 'builder' not in page.url:
                    log("  Editor URL already loaded")
                else:
                    # Wait for save2 to exist and see if editor is reachable
                    deadline = time.time() + 10
                    while time.time() < deadline:
                        if os.path.exists(save2_tmp):
                            break
                        time.sleep(0.3)

            # Capture screenshot at editor
            time.sleep(1.0)
            screencap(page, '06-editor.png')
            log(f"  URL: {page.url}")

            # Ensure save2 exists
            deadline = time.time() + 15
            while time.time() < deadline:
                if os.path.exists(save2_tmp):
                    break
                time.sleep(0.3)
            assert os.path.exists(save2_tmp), "save2 not created"
            save2_bytes = open(save2_tmp, 'rb').read()
            log(f"  save2: {len(save2_bytes)} bytes, byte_id={save2_bytes==save1_bytes}")

            # Wait for runtime
            try:
                H.wait_runtime_ready(page, timeout=25000)
                log("  runtime ready")
            except Exception as e:
                log(f"  runtime wait: {e} — may still be in builder; check URL")
                # If we're already in builder, this means the crossback happened before we could type
                if 'builder' in page.url:
                    log("  DETECTION: URL is builder after runtime wait — crossback happened prematurely")
                    # We'll still proceed with the save3 that exists

            time.sleep(1.0)
            screencap(page, '06b-post-runtime.png')
            log(f"  URL after runtime: {page.url}")

            # 5. Type marker (only if we're in the editor, not builder)
            marker_in_dom = False
            typing_ok = False

            if '?file=' in page.url and 'builder' not in page.url:
                log("Step 5: typing marker (in editor)")
                try:
                    page.wait_for_function(
                        "() => !!document.querySelector('iframe.doc-frame')",
                        timeout=8000
                    )
                    frame = page.frame_locator("iframe.doc-frame").first
                    editable = frame.locator("[contenteditable='true'], .cover-title, .slide-content, section div, section p").first
                    editable.wait_for(timeout=5000)
                    editable.dblclick()
                    time.sleep(0.4)
                    page.keyboard.press("End")
                    page.keyboard.type(MARKER)
                    time.sleep(0.6)
                    typing_ok = True
                    log("  Typed via frame_locator + contenteditable")
                except Exception as e1:
                    log(f"  frame_locator approach: {e1}")
                    try:
                        # Fallback: click directly in iframe
                        iframe_el = page.query_selector('iframe.doc-frame')
                        if iframe_el:
                            bb = iframe_el.bounding_box()
                            page.mouse.click(bb['x'] + bb['width']/2, bb['y'] + 100)
                            time.sleep(0.5)
                        page.keyboard.press('End')
                        page.keyboard.type(MARKER)
                        time.sleep(0.5)
                        typing_ok = True
                        log("  Typed via direct iframe click")
                    except Exception as e2:
                        log(f"  fallback typing: {e2}")

                # Check marker in DOM
                try:
                    marker_in_dom = page.evaluate("""() => {
                        const f = document.querySelector('iframe.doc-frame');
                        if (!f) return false;
                        return f.contentDocument.body.innerText.includes('[CV-B15-S3]');
                    }""")
                    log(f"  marker_in_dom: {marker_in_dom}")
                except Exception as e:
                    log(f"  marker DOM check: {e}")
            else:
                log(f"Step 5: SKIPPED — not in editor (URL: {page.url})")

            screencap(page, '07-post-typing.png')

            # 6. Save in editor
            log("Step 6: save in editor")
            H.set_fake_dialog(base, save3_tmp)

            if '?file=' in page.url and 'builder' not in page.url:
                save_as_btn = page.query_selector('#save-as-btn')
                if save_as_btn:
                    save_as_btn.click()
                    log("  clicked #save-as-btn")
                else:
                    page.keyboard.press('Control+Shift+S')
                    log("  Ctrl+Shift+S")
                deadline = time.time() + 15
                while time.time() < deadline:
                    if os.path.exists(save3_tmp):
                        break
                    time.sleep(0.3)
                time.sleep(0.8)
            else:
                log("  Not in editor — skipping save-as click")

            screencap(page, '08-saved.png')

            if os.path.exists(save3_tmp):
                save3_bytes = open(save3_tmp, 'rb').read()
                save3_actual = save3_tmp
                log(f"  save3: {len(save3_bytes)} bytes")
                marker_in_file = MARKER.strip() in save3_bytes.decode('utf-8', errors='replace')
                log(f"  marker in save3: {marker_in_file}")
            else:
                log("  save3 not created at expected path")

            # 7. Crossback
            log("Step 7: crossback")
            open_builder_btn = page.query_selector('#open-in-builder-btn')
            if open_builder_btn:
                open_builder_btn.click()
                try:
                    page.wait_for_url(re.compile(r'builder\.html'), timeout=15000)
                except Exception:
                    pass
                time.sleep(1.0)
                log(f"  URL: {page.url}")
                screencap(page, '09-crossback.png')
            else:
                log("  #open-in-builder-btn not found")
                screencap(page, '09-crossback-NA.png')

            browser.close()

    finally:
        H.stop_server(proc)
        log("Server stopped")

    # STRUCTURAL ASSERTIONS
    log("\n=== STRUCTURAL ASSERTIONS (Run 3) ===")
    assertions = {}

    if save1_bytes is None:
        log("  FATAL: save1 not available")
        log_fh.close()
        return {'error': 'save1 not available'}

    sections_save1 = split_sections(save1_bytes)
    log(f"save1: {len(sections_save1)} sections")

    if save2_bytes is not None:
        sections_save2 = split_sections(save2_bytes)
        save_section_map(sections_save2, os.path.join(EVIDENCE, 'c1-s3-r3-map-save2.json'))
        log(f"save2: {len(sections_save2)} sections")
        byte_identical = save1_bytes == save2_bytes
        count_match = len(sections_save1) == len(sections_save2)
        hm = []
        if count_match:
            for i, (s1, s2) in enumerate(zip(sections_save1, sections_save2)):
                hm.append({'index': i, 's1': s1['sha256'], 's2': s2['sha256'], 'match': s1['sha256']==s2['sha256']})
        all_match = count_match and all(m['match'] for m in hm)
        assertions['A'] = {
            'byte_identical': byte_identical,
            'count_match': count_match,
            's1_count': len(sections_save1), 's2_count': len(sections_save2),
            'all_hashes_match': all_match,
            'per_section': hm,
            'result': 'PASS' if all_match else 'FAIL',
        }
        log(f"  A: byte_id={byte_identical}, count_match={count_match}, all_hashes={all_match} → {assertions['A']['result']}")
    else:
        assertions['A'] = {'result': 'UNEXERCISABLE', 'reason': 'save2 missing'}
        log("  A: UNEXERCISABLE")

    if save3_bytes is not None:
        sections_save3 = split_sections(save3_bytes)
        save_section_map(sections_save3, os.path.join(EVIDENCE, 'c1-s3-r3-map-save3.json'))
        log(f"save3: {len(sections_save3)} sections")
        count_match3 = len(sections_save1) == len(sections_save3)
        diff_secs = []
        if count_match3:
            for i, (s1, s3) in enumerate(zip(sections_save1, sections_save3)):
                if s1['sha256'] != s3['sha256']:
                    t1 = re.sub(r'\s+', ' ', s1['text_normalized'].strip())
                    t3 = re.sub(r'\s+', ' ', s3['text_normalized'].strip())
                    marker_present = '[CV-B15-S3]' in t3
                    t3_stripped = re.sub(r'\s+', ' ', t3.replace('[CV-B15-S3]', '').replace('CV-B15-S3', '').strip())
                    only_marker = (t3_stripped == t1)
                    diff_secs.append({
                        'index': i, 's1_sha': s1['sha256'], 's3_sha': s3['sha256'],
                        'marker_present': marker_present, 'only_marker_diff': only_marker,
                        's1_text': t1[:200], 's3_text': t3[:200],
                    })
        marker_in_file = MARKER.strip() in save3_bytes.decode('utf-8', errors='replace')
        exactly_one = len(diff_secs) == 1
        marker_ok = exactly_one and diff_secs[0].get('marker_present') and diff_secs[0].get('only_marker_diff')
        # Also check if all normalized texts are same (serialization-only diff)
        all_norm_same = count_match3 and all(
            re.sub(r'\s+', ' ', sections_save1[i]['text_normalized'].strip()) ==
            re.sub(r'\s+', ' ', sections_save3[i]['text_normalized'].strip())
            for i in range(min(len(sections_save1), len(sections_save3)))
        )
        b_result = ('PASS' if (count_match3 and marker_ok) else
                    'FAIL_NO_MARKER_serialization_only' if (count_match3 and all_norm_same and not marker_in_file) else
                    'FAIL')
        assertions['B'] = {
            'count_match': count_match3, 's1_count': len(sections_save1), 's3_count': len(sections_save3),
            'diff_count': len(diff_secs), 'diff_sections': diff_secs,
            'exactly_one_diff': exactly_one,
            'marker_in_save3_file': marker_in_file,
            'all_normalized_text_same': all_norm_same,
            'result': b_result,
        }
        log(f"  B: count_match={count_match3}, diff_count={len(diff_secs)}, marker_in_file={marker_in_file}, all_norm_same={all_norm_same} → {b_result}")
    else:
        assertions['B'] = {'result': 'UNEXERCISABLE', 'reason': 'save3 missing'}
        log("  B: UNEXERCISABLE")

    # C: no hyp-leakage
    leakage = {}
    for name, content in [('save1', save1_bytes),
                           ('save2', save2_bytes if save2_bytes else b''),
                           ('save3', save3_bytes if save3_bytes else b'')]:
        text = content.decode('utf-8', errors='replace')
        ht = re.findall(r'hyp-[a-z]', text)
        dh = re.findall(r'data-hyp-', text)
        leakage[name] = {'hyp': ht, 'data_hyp': dh, 'count': len(ht)+len(dh)}
    c_pass = all(v['count'] == 0 for v in leakage.values())
    assertions['C'] = {'per_file': leakage, 'result': 'PASS' if c_pass else 'FAIL'}
    log(f"  C: leakage={leakage} → {assertions['C']['result']}")

    assertions.update({
        'removed_ok': removed, 'dup_count': dup_count, 'blank_count': len(blanks),
        'save1_section_count': len(sections_save1),
    })

    out = os.path.join(EVIDENCE, 'c1-s3-r3-assertions.json')
    with open(out, 'w') as f:
        json.dump(assertions, f, indent=2)
    log(f"\nAssertions: {out}")

    # Post-exercise hash bracket
    post = {fn: hashlib.sha256(open(os.path.join(APP_ROOT, fn), 'rb').read()).hexdigest() for fn in PRE_HASHES}
    ok = all(post[f] == PRE_HASHES[f] for f in PRE_HASHES)
    with open(os.path.join(EVIDENCE, 'c1-s3-r3-hash-post.json'), 'w') as f:
        json.dump({'phase': 'r3-post', 'files': post, 'all_unchanged': ok}, f, indent=2)
    log(f"Owner deck unchanged: {ok}")
    log("\n=== RUN 3 COMPLETE ===")
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
