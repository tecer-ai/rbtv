"""Criterion 3 exercise: real-deck proof at the floor via /api/deck-save.

Boots the server, makes a complex recompose save (reorder + remove + duplicate +
blank + library fragment), then opens the saved file in a headed Playwright browser,
captures screenshot and console log.

Run from the workspace root:
    python docs/plan/builder-open-deck/phase-1/evidence/c3_exercise.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = pathlib.Path(__file__).resolve().parents[5]  # hypresent/
REAL_DECK_SRC = WORKSPACE / "tecer-gsmm-introduction-test-v3.html"
FIXTURE_LIB = WORKSPACE / "tests" / "e2e" / "fixtures" / "builder-lib"
EVIDENCE = HERE

# ---------------------------------------------------------------------------
# Server helpers
# ---------------------------------------------------------------------------

def start_server(port: int):
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=str(WORKSPACE), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError(f"Server did not start on port {port}")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def post_json(base: str, path: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Main exercise
# ---------------------------------------------------------------------------

def main():
    # 1. Prepare temp copy of the real deck
    tmpdir = tempfile.mkdtemp(prefix="hyp-c3-")
    src_copy = os.path.join(tmpdir, "deck.html")
    shutil.copy(str(REAL_DECK_SRC), src_copy)
    out_path = os.path.join(tmpdir, "c3-out.html")

    print(f"Temp dir: {tmpdir}")
    print(f"Source copy: {src_copy}")
    print(f"Output path: {out_path}")

    # 2. Build complex payload:
    #    - reorder: put section 3 first (existing index 3), then 0, 1, 2, 4..9
    #    - remove: skip section 5 (it will not appear)
    #    - duplicate: include index 0 twice
    #    - blank: one blank item
    #    - library: intro-e2e fragment from fixture library
    #
    # Layout: [existing:3, existing:0, blank, existing:0(duplicate), library:intro-e2e,
    #          existing:1, existing:2, existing:4, existing:6, existing:7, existing:8, existing:9]
    # (section 5 is omitted → removed)
    items = [
        {"kind": "existing", "index": 3},
        {"kind": "existing", "index": 0},
        {"kind": "blank"},
        {"kind": "existing", "index": 0},  # duplicate of index 0
        {"kind": "library", "library_path": str(FIXTURE_LIB), "slide_id": "intro-e2e"},
        {"kind": "existing", "index": 1},
        {"kind": "existing", "index": 2},
        {"kind": "existing", "index": 4},
        # index 5 is intentionally missing → removed
        {"kind": "existing", "index": 6},
        {"kind": "existing", "index": 7},
        {"kind": "existing", "index": 8},
        {"kind": "existing", "index": 9},
    ]

    # 3. Start server
    PORT = 8866
    print(f"\nStarting server on port {PORT}...")
    proc, base = start_server(PORT)
    print(f"Server up at {base}")

    try:
        # 4. POST to /api/deck-save
        print("\nPOSTing to /api/deck-save...")
        t0 = time.time()
        status, resp = post_json(base, "/api/deck-save", {
            "source_path": src_copy,
            "out_path": out_path,
            "items": items,
            "libraries": {str(FIXTURE_LIB): True},
        })
        api_wall_ms = int((time.time() - t0) * 1000)
        print(f"API response ({api_wall_ms}ms): status={status}, resp={json.dumps(resp, indent=2)}")

        # Save response JSON to evidence
        resp_file = str(EVIDENCE / "c3-save-response.json")
        with open(resp_file, "w", encoding="utf-8") as f:
            json.dump({"status": status, "response": resp, "api_wall_ms": api_wall_ms}, f, indent=2)
        print(f"Saved API response to {resp_file}")

        if status != 200:
            print(f"ERROR: API returned {status}: {resp}")
            sys.exit(1)

        # 5. Open saved file in headed Playwright browser
        print("\nOpening saved file in headed Playwright browser...")
        from playwright.sync_api import sync_playwright

        saved_file_url = "file:///" + out_path.replace("\\", "/").replace(" ", "%20")
        print(f"File URL: {saved_file_url}")

        console_msgs = []
        screenshot_file = str(EVIDENCE / "c3-screenshot.png")
        console_log_file = str(EVIDENCE / "c3-console.log")

        t_browser_start = time.time()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Capture all console messages
            def on_console(msg):
                console_msgs.append({
                    "type": msg.type,
                    "text": msg.text,
                })

            page.on("console", on_console)

            page.goto(saved_file_url, wait_until="load")
            # Settle: wait for any scripts to run
            page.wait_for_timeout(3000)

            # Capture full-page screenshot
            page.screenshot(path=screenshot_file, full_page=True)
            print(f"Screenshot saved to {screenshot_file}")

            browser_wall_ms = int((time.time() - t_browser_start) * 1000)
            browser.close()

        # 6. Write console log
        recompose_errors = []
        with open(console_log_file, "w", encoding="utf-8") as f:
            f.write(f"Browser wall time: {browser_wall_ms}ms\n")
            f.write(f"Total console messages: {len(console_msgs)}\n\n")
            for msg in console_msgs:
                line = f"[{msg['type'].upper()}] {msg['text']}"
                f.write(line + "\n")
                # Identify recompose-attributable errors: JS errors from the deck's own scripts
                # (not favicon 404s or external resource errors)
                if msg["type"] in ("error", "warning"):
                    text_lower = msg["text"].lower()
                    # Exclude favicon/icon 404s and other cosmetic external errors
                    if "favicon" not in text_lower and "icon" not in text_lower:
                        recompose_errors.append(msg)

            f.write(f"\nRecompose-attributable errors (non-favicon): {len(recompose_errors)}\n")
            for err in recompose_errors:
                f.write(f"  [{err['type'].upper()}] {err['text']}\n")

            if len(recompose_errors) == 0:
                f.write("\nVERDICT: PASS — zero recompose-attributable console errors\n")
            else:
                f.write("\nVERDICT: FAIL — recompose-attributable console errors present\n")

        print(f"Console log saved to {console_log_file}")
        print(f"Browser wall time: {browser_wall_ms}ms")
        print(f"Recompose-attributable errors: {len(recompose_errors)}")

        print(f"\n=== CRITERION 3 RESULT ===")
        print(f"API status: {status}")
        print(f"Output file exists: {os.path.exists(out_path)}")
        print(f"Recompose errors: {len(recompose_errors)}")
        verdict = "PASS" if (status == 200 and len(recompose_errors) == 0) else "FAIL"
        print(f"VERDICT: {verdict}")

    finally:
        stop_server(proc)
        print("Server stopped.")
        # Do NOT remove tmpdir here — we need the output for criterion 5
        print(f"Temp dir retained for criterion 5: {tmpdir}")
        # Write the tmpdir path to a file for criterion 5 to pick up
        with open(str(EVIDENCE / ".c3-tmpdir"), "w") as f:
            f.write(tmpdir)
        with open(str(EVIDENCE / ".c3-outpath"), "w") as f:
            f.write(out_path)
        with open(str(EVIDENCE / ".c3-srcpath"), "w") as f:
            f.write(src_copy)


if __name__ == "__main__":
    main()
