"""Cold-verifier headed Playwright driver for B12 p4-checkpoint.

Run from the hypresent app root:
  python docs/plan/builder-open-deck/phase-4/evidence/cv_driver.py

Writes all capture files into the sibling evidence/ directory.

Architecture: each UI criterion gets its OWN server + browser launch to avoid
any state contamination between criteria. C5 and C6 are CLI/file-based (no browser).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
EVIDENCE = os.path.dirname(os.path.abspath(__file__))

assert os.path.isfile(os.path.join(REPO, "tecer-gsmm-introduction.html")), \
    f"REPO={REPO!r} doesn't contain tecer-gsmm-introduction.html"

_PORT_COUNTER = [18700]

OWNER_DECKS = [
    os.path.join(REPO, "tecer-gsmm-introduction.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test-v2.html"),
    os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html"),
]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def next_port():
    _PORT_COUNTER[0] += 1
    return _PORT_COUNTER[0]


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


def copy_owner_deck():
    d = tempfile.mkdtemp()
    src = os.path.join(REPO, "tecer-gsmm-introduction.html")
    dst = os.path.join(d, "deck.html")
    shutil.copy(src, dst)
    assets_src = os.path.join(REPO, "assets")
    if os.path.isdir(assets_src):
        shutil.copytree(assets_src, os.path.join(d, "assets"))
    return dst


def ev(name):
    return os.path.join(EVIDENCE, name)


def append_log(msg):
    with open(ev("run-log.txt"), "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def log_section(title):
    with open(ev("run-log.txt"), "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\n{title}\n{'='*70}\n")


def wait_runtime_ready(page, timeout=20000):
    page.wait_for_function(
        """() => {
            const f = document.querySelector('iframe.doc-frame');
            return f && f.contentWindow && f.contentWindow.hyp;
        }""",
        timeout=timeout,
    )


def wait_tray_populated(page, min_items=1, timeout=20000):
    page.wait_for_function(
        f"() => document.querySelectorAll('.tray-list li').length >= {min_items}",
        timeout=timeout,
    )


def open_deck_in_builder(page, base, deck_path):
    """Set dialog seam, navigate to builder, click open, wait for tray."""
    set_dialog(base, deck_path)
    page.goto(f"{base}/app/builder.html", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    page.click("#open-deck-btn")
    wait_tray_populated(page, min_items=1, timeout=20000)
    page.wait_for_timeout(500)


def open_doc_in_editor(page, base, deck_path):
    """Set dialog seam, navigate to editor, click open, wait for runtime."""
    set_dialog(base, deck_path)
    page.goto(f"{base}/app/", wait_until="domcontentloaded")
    page.wait_for_timeout(300)
    page.click("#open-btn")
    wait_runtime_ready(page, timeout=20000)


# ---------------------------------------------------------------------------
# Criterion 4: Disabled states
# ---------------------------------------------------------------------------

def run_c4():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log_section("C4: disabled states")
    port = next_port()
    proc, base = start_server(port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            page.add_init_script("window.localStorage.setItem('hypresent-comment-author','CVTester');")

            # --- Disabled when empty / no doc ---
            page.goto(f"{base}/app/builder.html", wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            ste_disabled = page.locator("#switch-to-editor-btn").is_disabled()
            page.screenshot(path=ev("c4-builder-empty-disabled.png"))
            append_log(f"  STE disabled on empty tray: {ste_disabled}")

            page.goto(f"{base}/app/", wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            oib_disabled = page.locator("#open-in-builder-btn").is_disabled()
            page.screenshot(path=ev("c4-editor-no-doc-disabled.png"))
            append_log(f"  OIB disabled on no doc: {oib_disabled}")

            # --- Enabling: open deck in builder ---
            deck_b = copy_owner_deck()
            open_deck_in_builder(page, base, deck_b)
            ste_enabled = not page.locator("#switch-to-editor-btn").is_disabled()
            page.screenshot(path=ev("c4-builder-deck-loaded-enabled.png"))
            append_log(f"  STE enables after deck load: {ste_enabled}")

            # --- Enabling: open doc in editor ---
            deck_e = copy_owner_deck()
            open_doc_in_editor(page, base, deck_e)
            try:
                page.wait_for_function(
                    "() => !document.getElementById('open-in-builder-btn').disabled",
                    timeout=15000
                )
                oib_enabled = True
            except PWTimeout:
                oib_enabled = False
            page.screenshot(path=ev("c4-editor-doc-open-enabled.png"))
            append_log(f"  OIB enables after doc + runtime ready: {oib_enabled}")

            browser.close()

    finally:
        stop_server(proc)

    if ste_disabled and oib_disabled and ste_enabled and oib_enabled:
        return "PASS", "Both disabled states confirmed; both enable correctly"
    else:
        notes = []
        if not ste_disabled: notes.append("STE not disabled on empty tray")
        if not oib_disabled: notes.append("OIB not disabled with no doc")
        if not ste_enabled: notes.append("STE did not enable after deck load")
        if not oib_enabled: notes.append("OIB did not enable after runtime ready")
        return "FAIL", "; ".join(notes)


# ---------------------------------------------------------------------------
# Criterion 7: Enable-on-ready latency
# ---------------------------------------------------------------------------

def run_c7():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log_section("C7: enable-on-ready latency")
    port = next_port()
    proc, base = start_server(port)
    latency_log = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)

            for path_label in ["dialog", "file-param"]:
                page = browser.new_page()
                page.add_init_script("window.localStorage.setItem('hypresent-comment-author','CVTester');")
                deck = copy_owner_deck()

                if path_label == "dialog":
                    set_dialog(base, deck)
                    page.goto(f"{base}/app/", wait_until="domcontentloaded")
                    page.wait_for_timeout(300)
                    t_start = time.monotonic()
                    page.click("#open-btn")
                    try:
                        page.wait_for_function(
                            """() => {
                                const f = document.querySelector('iframe.doc-frame');
                                return f && f.contentDocument
                                       && f.contentDocument.body
                                       && f.contentDocument.body.children.length > 0;
                            }""",
                            timeout=15000
                        )
                    except PWTimeout:
                        pass
                    t_content_visible = time.monotonic()
                else:
                    page.goto(f"{base}/app/", wait_until="domcontentloaded")
                    page.wait_for_timeout(200)
                    t_start = time.monotonic()
                    page.goto(
                        f"{base}/app/?file={urllib.parse.quote(deck)}",
                        wait_until="domcontentloaded"
                    )
                    try:
                        page.wait_for_function(
                            """() => {
                                const f = document.querySelector('iframe.doc-frame');
                                return f && f.contentDocument
                                       && f.contentDocument.body
                                       && f.contentDocument.body.children.length > 0;
                            }""",
                            timeout=15000
                        )
                    except PWTimeout:
                        pass
                    t_content_visible = time.monotonic()

                try:
                    page.wait_for_function(
                        "() => !document.getElementById('open-in-builder-btn').disabled",
                        timeout=15000
                    )
                    t_enabled = time.monotonic()
                    gap_ms = int((t_enabled - t_content_visible) * 1000)
                    total_ms = int((t_enabled - t_start) * 1000)
                    enabled = True
                except PWTimeout:
                    gap_ms = -1
                    total_ms = -1
                    enabled = False

                page.screenshot(path=ev(f"c7-latency-{path_label}.png"))
                entry = {
                    "path": path_label,
                    "enabled": enabled,
                    "gap_content_to_button_ms": gap_ms,
                    "total_open_to_button_ms": total_ms,
                }
                latency_log.append(entry)
                append_log(f"  {entry}")
                page.close()

            browser.close()
    finally:
        stop_server(proc)

    with open(ev("c7-latency-log.json"), "w", encoding="utf-8") as f:
        json.dump(latency_log, f, indent=2)

    all_enabled = all(e["enabled"] for e in latency_log)
    all_fast = all(e["gap_content_to_button_ms"] <= 1000 for e in latency_log if e["enabled"])
    if all_enabled and all_fast:
        gaps = [e["gap_content_to_button_ms"] for e in latency_log]
        return "PASS", f"Gaps (content→button): {gaps}ms"
    elif not all_enabled:
        return "FAIL", "Button did not enable within 15s on ≥1 path"
    else:
        return "FAIL", f"Gap > 1000ms: {latency_log}"


# ---------------------------------------------------------------------------
# Criterion 1: Full round trip
# ---------------------------------------------------------------------------

def run_c1():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log_section("C1: full round trip")
    port = next_port()
    proc, base = start_server(port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            page.add_init_script("window.localStorage.setItem('hypresent-comment-author','CVTester');")

            # 1. Open deck in builder
            deck = copy_owner_deck()
            open_deck_in_builder(page, base, deck)
            tray_before = page.locator(".tray-list li").count()
            page.screenshot(path=ev("c1-01-builder-deck-loaded.png"))
            append_log(f"  tray items after load: {tray_before}")

            if tray_before < 2:
                browser.close()
                return "FAIL", f"Only {tray_before} slide(s) in tray; need ≥2 to reorder"

            # 2. Reorder: drag slide 1 below slide 2
            first_box = page.locator(".tray-list li").nth(0).bounding_box()
            second_box = page.locator(".tray-list li").nth(1).bounding_box()
            fx = first_box["x"] + first_box["width"] / 2
            fy = first_box["y"] + first_box["height"] / 2
            tx = second_box["x"] + second_box["width"] / 2
            ty = second_box["y"] + second_box["height"] * 0.8

            page.mouse.move(fx, fy)
            page.mouse.down()
            page.wait_for_timeout(400)
            page.mouse.move(fx, fy + 5, steps=3)
            page.mouse.move(tx, ty, steps=15)
            page.wait_for_timeout(300)
            page.mouse.up()
            page.wait_for_timeout(1000)
            page.screenshot(path=ev("c1-02-builder-after-reorder.png"))

            # 3. Switch to editor — inject save path
            save_dir_1 = tempfile.mkdtemp()
            save_path_1 = os.path.join(save_dir_1, "bridge-crossing-1.html")
            set_dialog(base, save_path_1)
            page.click("#switch-to-editor-btn")

            # Wait for editor page
            try:
                page.wait_for_function(
                    "() => !window.location.pathname.includes('builder') && "
                    "window.location.pathname.includes('app')",
                    timeout=20000
                )
            except PWTimeout:
                pass
            page.wait_for_timeout(500)
            page.screenshot(path=ev("c1-03-editor-after-first-crossing.png"))
            file_written_1 = os.path.isfile(save_path_1)
            append_log(f"  crossing1 (STE) file written: {file_written_1} ({save_path_1})")

            # Wait for OIB button to enable (runtime ready)
            try:
                page.wait_for_function(
                    "() => !document.getElementById('open-in-builder-btn').disabled",
                    timeout=20000
                )
                oib_ready = True
            except PWTimeout:
                oib_ready = False
            append_log(f"  OIB button ready after STE crossing: {oib_ready}")

            # 4. Edit text in iframe with real gesture
            iframe_box = page.locator("iframe.doc-frame").bounding_box()
            if iframe_box:
                cx = iframe_box["x"] + iframe_box["width"] * 0.5
                cy = iframe_box["y"] + iframe_box["height"] * 0.3
                page.mouse.dblclick(cx, cy)
                page.wait_for_timeout(500)
                page.keyboard.type(" [CV]")
                page.wait_for_timeout(300)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            page.screenshot(path=ev("c1-04-editor-text-edited.png"))

            # 5. Open in builder — inject second save path
            save_dir_2 = tempfile.mkdtemp()
            save_path_2 = os.path.join(save_dir_2, "bridge-crossing-2.html")
            set_dialog(base, save_path_2)
            page.click("#open-in-builder-btn")

            # Wait for builder
            try:
                page.wait_for_function(
                    "() => window.location.pathname.includes('builder')",
                    timeout=25000
                )
                page.wait_for_timeout(3000)
                builder_loaded = True
            except PWTimeout:
                builder_loaded = False

            file_written_2 = os.path.isfile(save_path_2)
            tray_final = page.locator(".tray-list li").count()
            page.screenshot(path=ev("c1-05-builder-final-tray.png"))
            append_log(
                f"  crossing2 (OIB) file written: {file_written_2} ({save_path_2})\n"
                f"  builder loaded: {builder_loaded}; final tray: {tray_final}"
            )

            browser.close()
    finally:
        stop_server(proc)

    ok = file_written_1 and file_written_2 and builder_loaded and tray_final > 0
    if ok:
        return "PASS", f"Both crossings wrote new files; final tray has {tray_final} slides"
    notes = []
    if not file_written_1: notes.append("STE crossing did not write file")
    if not file_written_2: notes.append("OIB crossing did not write file")
    if not builder_loaded: notes.append("builder did not load after OIB crossing")
    if tray_final == 0: notes.append("final tray empty")
    return "FAIL", "; ".join(notes)


# ---------------------------------------------------------------------------
# Criterion 2: New-file guarantee
# ---------------------------------------------------------------------------

def run_c2(pre_hashes):
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log_section("C2: new-file guarantee")
    port = next_port()
    proc, base = start_server(port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            page.add_init_script("window.localStorage.setItem('hypresent-comment-author','CVTester');")

            deck = copy_owner_deck()
            orig_hash = sha256(deck)
            open_deck_in_builder(page, base, deck)

            # Crossing 1: STE
            dir_1 = tempfile.mkdtemp()
            save_1 = os.path.join(dir_1, "c2-crossing-1.html")
            set_dialog(base, save_1)
            page.click("#switch-to-editor-btn")
            try:
                page.wait_for_function(
                    "() => !window.location.pathname.includes('builder') && "
                    "window.location.pathname.includes('app')",
                    timeout=20000
                )
            except PWTimeout:
                pass
            page.wait_for_timeout(300)

            c1_written = os.path.isfile(save_1)
            c1_diff = save_1 != deck
            src_hash_after_c1 = sha256(deck)

            # Wait for OIB
            try:
                page.wait_for_function(
                    "() => !document.getElementById('open-in-builder-btn').disabled",
                    timeout=20000
                )
            except PWTimeout:
                pass

            # Crossing 2: OIB
            dir_2 = tempfile.mkdtemp()
            save_2 = os.path.join(dir_2, "c2-crossing-2.html")
            set_dialog(base, save_2)
            page.click("#open-in-builder-btn")
            try:
                page.wait_for_function(
                    "() => window.location.pathname.includes('builder')",
                    timeout=25000
                )
                page.wait_for_timeout(500)
            except PWTimeout:
                pass

            c2_written = os.path.isfile(save_2)
            c2_diff_from_c1 = save_2 != save_1
            c2_diff_from_src = save_2 != deck
            src_hash_after_c2 = sha256(deck)

            page.screenshot(path=ev("c2-builder-after-second-crossing.png"))
            browser.close()
    finally:
        stop_server(proc)

    # Owner deck hashes at this point
    owner_now = {p: sha256(p) for p in OWNER_DECKS}
    owner_unchanged = all(owner_now[p] == pre_hashes[p] for p in OWNER_DECKS)

    hash_data = {
        "pre_exercise": {os.path.basename(p): pre_hashes[p] for p in OWNER_DECKS},
        "post_c2": {os.path.basename(p): owner_now[p] for p in OWNER_DECKS},
        "owner_decks_unchanged": owner_unchanged,
        "source_deck_unchanged_after_c1": orig_hash == src_hash_after_c1,
        "source_deck_unchanged_after_c2": orig_hash == src_hash_after_c2,
        "crossing1_wrote_new_distinct_file": c1_written and c1_diff,
        "crossing2_wrote_new_distinct_file": c2_written and c2_diff_from_c1 and c2_diff_from_src,
        "paths": {"source": deck, "crossing1": save_1, "crossing2": save_2},
    }
    with open(ev("c2-hash-comparison.json"), "w", encoding="utf-8") as f:
        json.dump(hash_data, f, indent=2)

    for k, v in hash_data.items():
        append_log(f"  {k}: {v}")

    ok = (owner_unchanged and c1_written and c1_diff
          and c2_written and c2_diff_from_c1 and c2_diff_from_src
          and orig_hash == src_hash_after_c1
          and orig_hash == src_hash_after_c2)
    if ok:
        return "PASS", "Each crossing wrote a distinct new file; source and owner decks unchanged"
    notes = []
    if not owner_unchanged: notes.append("owner decks mutated")
    if not c1_written: notes.append("crossing1 did not write")
    if not c2_written: notes.append("crossing2 did not write")
    if not c2_diff_from_c1: notes.append("crossing2 same path as crossing1")
    if orig_hash != src_hash_after_c1: notes.append("source deck mutated after c1")
    if orig_hash != src_hash_after_c2: notes.append("source deck mutated after c2")
    return "FAIL", "; ".join(notes)


# ---------------------------------------------------------------------------
# Criterion 3: Cancel semantics
# ---------------------------------------------------------------------------

def run_c3():
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    log_section("C3: cancel semantics")
    port = next_port()
    proc, base = start_server(port)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False)
            page = browser.new_page()
            page.add_init_script("window.localStorage.setItem('hypresent-comment-author','CVTester');")

            # Cancel A: STE cancel
            deck_a = copy_owner_deck()
            open_deck_in_builder(page, base, deck_a)
            page.screenshot(path=ev("c3-01-builder-deck-loaded.png"))

            url_before_a = page.url
            set_dialog(base, None)  # inject cancel
            page.click("#switch-to-editor-btn")
            page.wait_for_timeout(2500)
            url_after_a = page.url
            still_on_builder = "builder.html" in url_after_a
            page.screenshot(path=ev("c3-02-builder-after-cancel.png"))
            status_a = page.locator("#builder-status").inner_text()
            append_log(
                f"  STE cancel: still on builder={still_on_builder}\n"
                f"  url before: {url_before_a}\n"
                f"  url after:  {url_after_a}\n"
                f"  status:     '{status_a}'"
            )

            # Cancel B: OIB cancel
            deck_b = copy_owner_deck()
            open_doc_in_editor(page, base, deck_b)
            try:
                page.wait_for_function(
                    "() => !document.getElementById('open-in-builder-btn').disabled",
                    timeout=15000
                )
            except PWTimeout:
                pass
            page.screenshot(path=ev("c3-03-editor-doc-loaded.png"))

            url_before_b = page.url
            set_dialog(base, None)
            page.click("#open-in-builder-btn")
            page.wait_for_timeout(2500)
            url_after_b = page.url
            still_on_editor = "builder" not in url_after_b and "/app/" in url_after_b
            page.screenshot(path=ev("c3-04-editor-after-cancel.png"))
            status_b = page.locator("#shell-status").inner_text()
            append_log(
                f"  OIB cancel: still on editor={still_on_editor}\n"
                f"  url before: {url_before_b}\n"
                f"  url after:  {url_after_b}\n"
                f"  status:     '{status_b}'"
            )

            browser.close()
    finally:
        stop_server(proc)

    if still_on_builder and still_on_editor:
        return "PASS", "Both cancel paths leave current view intact; no navigation or error"
    notes = []
    if not still_on_builder: notes.append("STE cancel caused navigation away from builder")
    if not still_on_editor: notes.append("OIB cancel caused navigation away from editor")
    return "FAIL", "; ".join(notes)


# ---------------------------------------------------------------------------
# Criterion 5: Editor regression pytest
# ---------------------------------------------------------------------------

def run_c5():
    log_section("C5: pytest regression")
    t0 = time.monotonic()
    try:
        cmd = [sys.executable, "-m", "pytest",
               "tests/e2e/test_g2_save_with_comments.py",
               "tests/e2e/test_exit_smoke.py",
               "-q", "--tb=short"]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=300)
        wall_ms = int((time.monotonic() - t0) * 1000)
        output = r.stdout + r.stderr
        with open(ev("c5-pytest-output.txt"), "w", encoding="utf-8") as f:
            f.write(f"EXIT: {r.returncode}\nWALL_MS: {wall_ms}\n\n{output}")
        append_log(f"  pytest exit: {r.returncode}, wall_ms: {wall_ms}")
        append_log("  last 10 lines:\n" + "\n".join(output.strip().splitlines()[-10:]))
        if r.returncode == 0:
            return "PASS", f"Exit 0 in {wall_ms}ms"
        return "FAIL", f"Exit {r.returncode} — see c5-pytest-output.txt"
    except subprocess.TimeoutExpired:
        return "FAIL", "pytest timed out after 300s"
    except Exception as e:
        return "FAIL", f"Exception: {e}"


# ---------------------------------------------------------------------------
# Criterion 6: decisions.md audit
# ---------------------------------------------------------------------------

def run_c6():
    import re
    log_section("C6: decisions.md audit")
    try:
        decisions_path = os.path.join(REPO, "docs/plan/builder-open-deck/decisions.md")
        with open(decisions_path, "r", encoding="utf-8") as f:
            content = f.read()

        section_start = content.find("## Decisions and Discoveries")
        if section_start == -1:
            return "FAIL", "Section 'Decisions and Discoveries' not found"

        # Scope the section to just the Decisions and Discoveries block
        # (stop at the next top-level "## " heading)
        rest = content[section_start:]
        next_section = rest.find("\n## ", 3)  # skip the heading line itself
        section = rest if next_section == -1 else rest[:next_section]
        violations = []

        # No file-change bullets
        fc = re.findall(
            r'^\s*[-*]\s+(?:Created|Updated|Modified|Added|Deleted|Removed)\s+(?:file|files?)',
            section, re.IGNORECASE | re.MULTILINE
        )
        if fc:
            violations.append(f"File-change bullets: {fc[:3]}")

        # No N→M count narratives
        nm = re.findall(r'\b\d+\s*(?:→|->)\s*\d+\b', section)
        if nm:
            violations.append(f"N→M narrative: {nm}")

        # Structure: named ### entries with decision+rationale+scope
        entries = re.findall(r'###\s+.+', section)
        n = len(entries)
        n_dec = len(re.findall(r'\*\*Decision:\*\*', section))
        n_rat = len(re.findall(r'\*\*Rationale:\*\*', section))
        n_sco = len(re.findall(r'\*\*Scope:\*\*', section))

        summary = (f"entries={n}, Decision={n_dec}, Rationale={n_rat}, "
                   f"Scope={n_sco}, violations={violations}")
        append_log(f"  {summary}")
        for e in entries:
            append_log(f"    entry: {e}")

        with open(ev("c6-decisions-audit.txt"), "w", encoding="utf-8") as f:
            f.write(f"decisions.md audit\nFile: {decisions_path}\n\n{summary}\n\n")
            f.write("--- Entries ---\n")
            for e in entries:
                f.write(f"  {e}\n")
            f.write("\n--- Decisions and Discoveries section (first 3000 chars) ---\n")
            f.write(section[:3000])

        if violations:
            return "FAIL", f"Violations found: {violations}"
        if n == 0:
            return "FAIL", "No entries found in Decisions and Discoveries section"
        # Each named entry must have Decision + Rationale + Scope fields
        if not (n_dec >= n and n_rat >= n and n_sco >= n):
            return "FAIL", (f"Entries missing required fields: {summary}. "
                            "Expected ≥{n} each of Decision/Rationale/Scope")
        return "PASS", f"No prohibited narratives; all {n} entries have Decision+Rationale+Scope; {summary}"

    except Exception as e:
        return "FAIL", f"Exception: {e}\n{traceback.format_exc()}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Initialize log
    pre_hashes = {p: sha256(p) for p in OWNER_DECKS}
    with open(ev("run-log.txt"), "w", encoding="utf-8") as f:
        f.write("Cold Verifier B12 run log\n")
        f.write(f"REPO={REPO}\nEVIDENCE={EVIDENCE}\n\n")
        f.write("=== Pre-exercise owner-deck hashes ===\n")
        for p, h in pre_hashes.items():
            f.write(f"  {os.path.basename(p)}: {h}\n")

    results = {}
    criteria = [
        ("C4", run_c4),
        ("C7", run_c7),
        ("C1", run_c1),
        ("C2", lambda: run_c2(pre_hashes)),
        ("C3", run_c3),
        ("C5", run_c5),
        ("C6", run_c6),
    ]

    for cid, fn in criteria:
        print(f"\n[CV] Running {cid}...")
        try:
            verdict, notes = fn()
        except Exception as e:
            verdict = "FAIL"
            notes = f"Unhandled exception: {e}\n{traceback.format_exc()}"
            append_log(f"  UNHANDLED EXCEPTION in {cid}:\n{notes}")
        results[cid] = (verdict, notes)
        print(f"  {cid}: {verdict} — {notes}")
        append_log(f"  VERDICT: {verdict} — {notes}")

    # Post-exercise hashes
    post_hashes = {p: sha256(p) for p in OWNER_DECKS}
    with open(ev("c2-owner-deck-hash-post.json"), "w", encoding="utf-8") as f:
        json.dump({
            "pre": {os.path.basename(p): pre_hashes[p] for p in OWNER_DECKS},
            "post": {os.path.basename(p): post_hashes[p] for p in OWNER_DECKS},
            "all_unchanged": all(post_hashes[p] == pre_hashes[p] for p in OWNER_DECKS),
        }, f, indent=2)
    log_section("Post-exercise owner deck hashes")
    for p in OWNER_DECKS:
        unchanged = post_hashes[p] == pre_hashes[p]
        append_log(f"  {os.path.basename(p)}: unchanged={unchanged}")

    print("\n=== VERDICT SUMMARY ===")
    for cid in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]:
        v, n = results.get(cid, ("NOT_RUN", ""))
        print(f"  {cid}: {v} — {n}")

    with open(ev("results.json"), "w", encoding="utf-8") as f:
        json.dump({k: {"verdict": v, "notes": n} for k, (v, n) in results.items()}, f, indent=2)

    return results


if __name__ == "__main__":
    main()
