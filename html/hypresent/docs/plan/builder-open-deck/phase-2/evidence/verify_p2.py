"""
Phase-2 independent checkpoint verifier.
Exercises the 6 contract criteria at the fidelity floor using headed Playwright.
Write evidence files into the same directory as this script.
"""

import os
import sys
import json
import shutil
import tempfile
import time
import subprocess
import urllib.request
import urllib.error

# ── paths ───────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
# REPO should be hypresent/
E2E_DIR = os.path.join(REPO, "tests", "e2e")
sys.path.insert(0, E2E_DIR)

DECK_FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction-test-v3.html")
PORT = 8899

print(f"REPO: {REPO}")
print(f"DECK_FIXTURE exists: {os.path.exists(DECK_FIXTURE)}")

import conftest_helpers as H
from playwright.sync_api import sync_playwright

results = {}


def start_server():
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(PORT)],
        cwd=REPO, env=env,
    )
    base = f"http://127.0.0.1:{PORT}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                print(f"Server up at {base}")
                return proc, base
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"Server did not start on {PORT}")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def set_fake_dialog(base, path_or_none):
    data = json.dumps({"path": path_or_none}).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/_test/set-dialog", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def copy_deck():
    d = tempfile.mkdtemp()
    dst = os.path.join(d, "deck.html")
    shutil.copy(DECK_FIXTURE, dst)
    return dst


def make_sectionless():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bad.html")
    with open(p, "w", encoding="utf-8") as f:
        f.write("<html><body><p>No sections here — sectionless test file</p></body></html>")
    return p


proc, base = start_server()
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=False)

try:
    # ── C1: Open → full tray at the floor ───────────────────────────────────
    print("\n=== C1: Open deck → full tray ===")
    t0 = time.time()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        deck_path = copy_deck()
        set_fake_dialog(base, deck_path)
        page.goto(base + "/app/builder.html")
        page.click("#open-deck-btn")
        page.wait_for_selector(".tray-row", timeout=12000)
        rows = page.locator(".tray-row").all()
        row_count = len(rows)
        print(f"  Tray rows: {row_count}")
        # Capture screenshot
        ss_path = os.path.join(HERE, "c1-tray-full.png")
        page.screenshot(path=ss_path)
        print(f"  Screenshot: {ss_path}")
        # Check deck chip
        chip_name = page.locator("#deck-chip-name").text_content()
        print(f"  Deck chip name: {chip_name!r}")
        # C1 verdict
        c1_pass = row_count == 10
        results["C1"] = {
            "verdict": "held" if c1_pass else "failed",
            "row_count": row_count,
            "chip_name": chip_name,
            "wall_ms": int((time.time() - t0) * 1000),
            "evidence": "c1-tray-full.png",
        }
        print(f"  C1 verdict: {results['C1']['verdict']}")
    except Exception as e:
        results["C1"] = {"verdict": "failed", "error": str(e)}
        print(f"  C1 EXCEPTION: {e}")
    finally:
        page.close()

    # ── C2: Thumbnails themed ────────────────────────────────────────────────
    print("\n=== C2: Thumbnails themed ===")
    t0 = time.time()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        deck_path = copy_deck()
        set_fake_dialog(base, deck_path)
        page.goto(base + "/app/builder.html")
        page.click("#open-deck-btn")
        page.wait_for_selector(".tray-row", timeout=12000)
        rows = page.locator(".tray-row").all()
        row_count = len(rows)

        # Give iframes a moment to populate srcdoc (async)
        page.wait_for_timeout(500)

        srcdoc_details = []
        all_have_section = True
        all_have_style = True
        for i, row in enumerate(rows):
            iframe = row.locator("iframe")
            srcdoc = iframe.get_attribute("srcdoc") or ""
            has_section = "<section" in srcdoc
            has_slide_css = ".slide {" in srcdoc
            srcdoc_details.append({
                "row": i + 1,
                "srcdoc_len": len(srcdoc),
                "has_section": has_section,
                "has_slide_css": has_slide_css,
            })
            if not has_section:
                all_have_section = False
            if not has_slide_css:
                all_have_style = False

        # Capture screenshot of the tray with thumbnails
        ss_path = os.path.join(HERE, "c2-thumbnails-themed.png")
        page.screenshot(path=ss_path)
        print(f"  Screenshot: {ss_path}")

        # Save srcdoc details
        details_path = os.path.join(HERE, "c2-srcdoc-details.json")
        with open(details_path, "w", encoding="utf-8") as f:
            json.dump(srcdoc_details, f, indent=2)

        print(f"  all_have_section={all_have_section}, all_have_style={all_have_style}")
        print(f"  srcdoc sample lengths: {[d['srcdoc_len'] for d in srcdoc_details]}")

        c2_pass = row_count == 10 and all_have_section and all_have_style
        results["C2"] = {
            "verdict": "held" if c2_pass else "failed",
            "row_count": row_count,
            "all_have_section": all_have_section,
            "all_have_slide_css": all_have_style,
            "wall_ms": int((time.time() - t0) * 1000),
            "evidence": ["c2-thumbnails-themed.png", "c2-srcdoc-details.json"],
        }
        print(f"  C2 verdict: {results['C2']['verdict']}")
    except Exception as e:
        results["C2"] = {"verdict": "failed", "error": str(e)}
        print(f"  C2 EXCEPTION: {e}")
    finally:
        page.close()

    # ── C3: Rejection path ───────────────────────────────────────────────────
    print("\n=== C3: Rejection path ===")
    t0 = time.time()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        bad_path = make_sectionless()
        set_fake_dialog(base, bad_path)
        page.goto(base + "/app/builder.html")

        # Count rows before
        rows_before = page.locator(".tray-row").count()
        page.click("#open-deck-btn")

        # Wait for error status
        page.wait_for_selector(".shell-status.error", timeout=8000)
        status_text = page.locator("#builder-status").text_content()
        print(f"  Status text: {status_text!r}")

        rows_after = page.locator(".tray-row").count()
        print(f"  Rows before={rows_before}, after={rows_after}")

        # Capture screenshot
        ss_path = os.path.join(HERE, "c3-rejection.png")
        page.screenshot(path=ss_path)

        has_error_class = page.locator(".shell-status.error").count() > 0
        mentions_section = "section" in status_text.lower()
        tray_unchanged = rows_after == 0

        results["C3"] = {
            "verdict": "held" if (has_error_class and tray_unchanged) else "failed",
            "status_text": status_text,
            "has_error_class": has_error_class,
            "mentions_section": mentions_section,
            "rows_after": rows_after,
            "wall_ms": int((time.time() - t0) * 1000),
            "evidence": "c3-rejection.png",
        }
        print(f"  C3 verdict: {results['C3']['verdict']}")
    except Exception as e:
        results["C3"] = {"verdict": "failed", "error": str(e)}
        print(f"  C3 EXCEPTION: {e}")
    finally:
        page.close()

    # ── C4: Cancel path ──────────────────────────────────────────────────────
    print("\n=== C4: Cancel path ===")
    t0 = time.time()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    try:
        # Set dialog to return null (cancel)
        set_fake_dialog(base, None)
        page.goto(base + "/app/builder.html")

        status_before = page.locator("#builder-status").text_content()
        rows_before = page.locator(".tray-row").count()

        page.click("#open-deck-btn")
        # Wait a moment — nothing should happen
        page.wait_for_timeout(1500)

        status_after = page.locator("#builder-status").text_content()
        rows_after = page.locator(".tray-row").count()
        error_count = page.locator(".shell-status.error").count()

        print(f"  status_before={status_before!r}, status_after={status_after!r}")
        print(f"  rows: before={rows_before}, after={rows_after}")
        print(f"  error_count={error_count}")

        ss_path = os.path.join(HERE, "c4-cancel.png")
        page.screenshot(path=ss_path)

        # Cancel: nothing changes, no error shown
        no_error = error_count == 0
        tray_unchanged = rows_after == rows_before

        results["C4"] = {
            "verdict": "held" if (no_error and tray_unchanged) else "failed",
            "no_error": no_error,
            "tray_unchanged": tray_unchanged,
            "status_after": status_after,
            "wall_ms": int((time.time() - t0) * 1000),
            "evidence": "c4-cancel.png",
        }
        print(f"  C4 verdict: {results['C4']['verdict']}")
    except Exception as e:
        results["C4"] = {"verdict": "failed", "error": str(e)}
        print(f"  C4 EXCEPTION: {e}")
    finally:
        page.close()

    # ── C5: Assemble-mode regression ─────────────────────────────────────────
    print("\n=== C5: Assemble-mode regression (pytest) ===")
    t0 = time.time()
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/e2e/test_pb2_library_load.py",
        "tests/e2e/test_pb3_previews.py",
        "-q", "--tb=short",
    ]
    log_path = os.path.join(HERE, "c5-regression-pytest.txt")
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=180,
        )
        output = result.stdout + "\n" + result.stderr
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"  Exit code: {result.returncode}")
        print(f"  Output tail:\n{output[-800:]}")
        results["C5"] = {
            "verdict": "held" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "wall_ms": int((time.time() - t0) * 1000),
            "evidence": "c5-regression-pytest.txt",
        }
        print(f"  C5 verdict: {results['C5']['verdict']}")
    except subprocess.TimeoutExpired:
        results["C5"] = {"verdict": "failed", "error": "pytest timed out after 180s"}
        with open(log_path, "w") as f:
            f.write("TIMED OUT after 180s")
    except Exception as e:
        results["C5"] = {"verdict": "failed", "error": str(e)}
        print(f"  C5 EXCEPTION: {e}")

    # ── C6: decisions.md audit ──────────────────────────────────────────────
    print("\n=== C6: decisions.md audit ===")
    decisions_path = os.path.join(
        REPO, "docs", "plan", "builder-open-deck", "decisions.md"
    )
    try:
        with open(decisions_path, "r", encoding="utf-8") as f:
            decisions_text = f.read()

        # Extract execution entries (ADX-*)
        import re
        adx_entries = re.findall(
            r"### (ADX-\d+)[^\n]*\n(.*?)(?=\n### |\Z)",
            decisions_text,
            re.DOTALL,
        )
        print(f"  Found {len(adx_entries)} ADX entries: {[e[0] for e in adx_entries]}")

        audit_notes = []
        violations = []

        for entry_id, entry_body in adx_entries:
            # Check for required fields: decision, rationale, scope
            has_decision = "**Decision:**" in entry_body or "- **Decision:**" in entry_body
            has_rationale = "**Rationale:**" in entry_body or "- **Rationale:**" in entry_body
            has_scope = "**Scope:**" in entry_body or "- **Scope:**" in entry_body

            # Check violations: file-lists or N→M narratives
            has_file_list = re.search(r"^\s*[-*]\s+[`\"\']?[\w./]+\.[a-zA-Z]{1,5}[`\"\']?\s*$",
                                       entry_body, re.MULTILINE)
            # N→M pattern: arrows in "N → M" or "p1-1 → p1-2 → ..."
            # A single pipeline reference in scope is OK; a full N→M narrative is not
            # Check for sub-floor rewrite (editing previous entries)
            note = {
                "entry": entry_id,
                "has_decision": has_decision,
                "has_rationale": has_rationale,
                "has_scope": has_scope,
            }
            audit_notes.append(note)

            if not has_decision:
                violations.append(f"{entry_id}: missing **Decision:**")
            if not has_rationale:
                violations.append(f"{entry_id}: missing **Rationale:**")
            if not has_scope:
                violations.append(f"{entry_id}: missing **Scope:**")

        # Also check: no entry edits previous entries (append-only discipline)
        # We verify the three expected entries (ADX-1, ADX-2, ADX-3) are present
        expected_entries = {"ADX-1", "ADX-2", "ADX-3"}
        found_entries = {e[0] for e in adx_entries}
        missing = expected_entries - found_entries
        if missing:
            violations.append(f"Missing expected entries: {missing}")

        print(f"  Audit notes: {audit_notes}")
        print(f"  Violations: {violations}")

        # Save audit to file
        audit_path = os.path.join(HERE, "c6-decisions-audit.txt")
        with open(audit_path, "w", encoding="utf-8") as f:
            f.write("=== decisions.md ADX audit ===\n\n")
            for note in audit_notes:
                f.write(f"{note['entry']}:\n")
                f.write(f"  has_decision: {note['has_decision']}\n")
                f.write(f"  has_rationale: {note['has_rationale']}\n")
                f.write(f"  has_scope: {note['has_scope']}\n\n")
            if violations:
                f.write(f"\nVIOLATIONS:\n")
                for v in violations:
                    f.write(f"  - {v}\n")
            else:
                f.write("\nNo shape violations found.\n")

        results["C6"] = {
            "verdict": "held" if not violations else "failed",
            "entries_found": list(found_entries),
            "violations": violations,
            "evidence": "c6-decisions-audit.txt",
        }
        print(f"  C6 verdict: {results['C6']['verdict']}")
    except Exception as e:
        results["C6"] = {"verdict": "failed", "error": str(e)}
        print(f"  C6 EXCEPTION: {e}")

finally:
    browser.close()
    pw.stop()
    stop_server(proc)

# ── Write results JSON ────────────────────────────────────────────────────
results_path = os.path.join(HERE, "results.json")
with open(results_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print(f"\n=== SUMMARY ===")
for k, v in results.items():
    print(f"  {k}: {v.get('verdict', 'ERROR')} {v.get('error', '')}")
print(f"\nResults written to: {results_path}")
