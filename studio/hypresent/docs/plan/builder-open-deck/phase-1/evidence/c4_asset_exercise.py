"""Criterion 4: Asset copy exercise.

Builds a temp library with assets/probe.png and slides/asset-probe.html,
saves a deck including that slide via the API, verifies asset is copied,
then runs a second save to same folder to verify collision is NOT overwritten
and is reported in assets_skipped.
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

WORKSPACE = pathlib.Path(__file__).resolve().parents[5]  # hypresent/
REAL_DECK_SRC = WORKSPACE / "tecer-gsmm-introduction-test-v3.html"
EVIDENCE = pathlib.Path(__file__).resolve().parent


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


def main():
    lines = []

    # 1. Build temp library with probe asset
    tmpdir = tempfile.mkdtemp(prefix="hyp-c4-")
    lib_path = os.path.join(tmpdir, "probe-lib")
    os.makedirs(os.path.join(lib_path, "slides"), exist_ok=True)
    os.makedirs(os.path.join(lib_path, "assets"), exist_ok=True)

    # probe asset (minimal PNG-like bytes)
    probe_asset_content = b"\x89PNG\r\n\x1a\nPROBE"
    probe_asset_path = os.path.join(lib_path, "assets", "probe.png")
    with open(probe_asset_path, "wb") as f:
        f.write(probe_asset_content)

    # slide that references the probe asset
    fragment_html = '<section class="probe-slide"><img src="assets/probe.png"><p>Probe slide</p></section>'
    slide_path = os.path.join(lib_path, "slides", "asset-probe.html")
    with open(slide_path, "w", encoding="utf-8") as f:
        f.write(fragment_html)

    lines.append(f"Temp library built: {lib_path}")
    lines.append(f"  Probe asset: assets/probe.png ({len(probe_asset_content)} bytes)")
    lines.append(f"  Slide: slides/asset-probe.html")

    # 2. Prepare source deck copy and out dir
    src_copy = os.path.join(tmpdir, "source.html")
    shutil.copy(str(REAL_DECK_SRC), src_copy)
    out_dir = os.path.join(tmpdir, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "deck.html")

    # 3. Start server
    PORT = 8867
    print(f"Starting server on port {PORT}...")
    proc, base = start_server(PORT)
    print(f"Server up at {base}")

    try:
        # === FIRST SAVE ===
        items_1 = [
            {"kind": "library", "library_path": lib_path, "slide_id": "asset-probe"},
            {"kind": "existing", "index": 0},
        ]
        t0 = time.time()
        status1, resp1 = post_json(base, "/api/deck-save", {
            "source_path": src_copy,
            "out_path": out_path,
            "items": items_1,
            "libraries": {lib_path: True},
        })
        wall1 = int((time.time() - t0) * 1000)

        lines.append(f"\n=== FIRST SAVE ({wall1}ms) ===")
        lines.append(f"Status: {status1}")
        lines.append(f"Response: {json.dumps(resp1, indent=2)}")

        # Verify asset copied
        out_asset = os.path.join(out_dir, "assets", "probe.png")
        asset_exists = os.path.exists(out_asset)
        asset_bytes = open(out_asset, "rb").read() if asset_exists else None
        asset_matches = asset_bytes == probe_asset_content if asset_exists else False

        lines.append(f"\nAsset exists in out_dir: {asset_exists}")
        if asset_exists:
            lines.append(f"  Path: {out_asset}")
            lines.append(f"  Size: {len(asset_bytes)} bytes")
            lines.append(f"  Content matches original: {asset_matches}")
        lines.append(f"assets_copied in response: {'assets/probe.png' in resp1.get('assets_copied', [])}")
        lines.append(f"assets_skipped in response: {resp1.get('assets_skipped', 'NOT PRESENT')}")

        # Directory listing of out_dir
        lines.append(f"\nout_dir listing:")
        for root, dirs, files in os.walk(out_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, out_dir)
                lines.append(f"  {rel} ({os.path.getsize(fpath)} bytes)")

        # === SECOND SAVE (collision) ===
        t0 = time.time()
        status2, resp2 = post_json(base, "/api/deck-save", {
            "source_path": src_copy,
            "out_path": out_path,
            "items": items_1,
            "libraries": {lib_path: True},
        })
        wall2 = int((time.time() - t0) * 1000)

        lines.append(f"\n=== SECOND SAVE — COLLISION ({wall2}ms) ===")
        lines.append(f"Status: {status2}")
        lines.append(f"Response: {json.dumps(resp2, indent=2)}")

        # Verify original asset NOT overwritten
        if asset_exists:
            asset_bytes_after = open(out_asset, "rb").read()
            not_overwritten = asset_bytes_after == probe_asset_content
            lines.append(f"\nAsset NOT overwritten: {not_overwritten}")
            lines.append(f"  Content still matches original: {asset_bytes_after == probe_asset_content}")
        lines.append(f"assets_skipped in response: {'assets/probe.png' in resp2.get('assets_skipped', [])}")
        lines.append(f"assets_copied in response: {resp2.get('assets_copied', [])}")

        # Verdict
        pass_first = (
            status1 == 200
            and "assets/probe.png" in resp1.get("assets_copied", [])
            and "assets_skipped" not in resp1
            and asset_exists
            and asset_matches
        )
        pass_second = (
            status2 == 200
            and "assets/probe.png" in resp2.get("assets_skipped", [])
            and (asset_bytes_after == probe_asset_content if asset_exists else False)
        )

        lines.append(f"\n=== VERDICT ===")
        lines.append(f"First save (asset copied): {'PASS' if pass_first else 'FAIL'}")
        lines.append(f"Second save (collision skipped): {'PASS' if pass_second else 'FAIL'}")
        overall = "PASS" if (pass_first and pass_second) else "FAIL"
        lines.append(f"Overall: {overall}")

    finally:
        stop_server(proc)
        print("Server stopped.")
        # Write evidence file
        evidence_file = str(EVIDENCE / "c4-asset-copy.txt")
        with open(evidence_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Evidence written to {evidence_file}")
        # Print summary
        for line in lines:
            print(line)


if __name__ == "__main__":
    main()
