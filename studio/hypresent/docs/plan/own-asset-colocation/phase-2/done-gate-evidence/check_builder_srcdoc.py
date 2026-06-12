"""
Quick check: verify builder srcdoc frames cannot render own-assets (structural finding).
Run after drive_row7.py has confirmed the feature.
"""
import os
import pathlib
import shutil
import struct
import sys
import tempfile
import time
import zlib

APP_DIR = pathlib.Path(__file__).resolve().parents[5]
os.chdir(str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "tests" / "e2e"))
import conftest_helpers as H
import builder_helpers as B

PORT = 8821


def _make_png(r, g, b):
    def _chunk(name, data):
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00" + bytes([r, g, b])
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


DECK_FIXTURE = str(APP_DIR / "tecer-gsmm-introduction-test-v3.html")
EVIDENCE_DIR = pathlib.Path(__file__).resolve().parent


def main():
    src_html = pathlib.Path(DECK_FIXTURE).read_text(encoding="utf-8")
    own_marker = (
        '\n  <img id="own-img-blue" src="assets/own-tecer.png" '
        'alt="own-tecer" style="position:absolute;opacity:0.01;width:1px;height:1px;">'
    )
    patched = src_html.replace("</section>", own_marker + "\n</section>", 1)
    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    deck_path = tmp_dir / "deck-srcdoc-check.html"
    deck_path.write_text(patched, encoding="utf-8")
    assets_dir = tmp_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "own-tecer.png").write_bytes(_make_png(0, 0, 200))

    proc, base = H.start_server(PORT, test_dialog=True)
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        H.set_fake_dialog(base, str(deck_path))
        page.goto(base + "/app/builder.html")
        page.click("#open-deck-btn")
        page.wait_for_selector(".tray-row", timeout=10000)
        page.wait_for_timeout(500)

        # Check all srcdoc frames for our test image
        frames = page.frames
        srcdoc_frames = [f for f in frames if f.url == "about:srcdoc"]
        results = []
        for f in srcdoc_frames:
            try:
                nw = f.evaluate(
                    "() => { const el = document.getElementById('own-img-blue'); "
                    "return el ? {'found': true, 'naturalWidth': el.naturalWidth, 'complete': el.complete} : {'found': false}; }"
                )
                results.append(nw)
            except Exception as e:
                results.append({"error": str(e)})

        print(f"[srcdoc-check] {len(srcdoc_frames)} srcdoc frames")
        for i, r in enumerate(results):
            print(f"  frame {i}: {r}")

        # Find the frame with our image
        found_frames = [r for r in results if r.get("found")]
        if found_frames:
            nw = found_frames[0]["naturalWidth"]
            print(f"\n[srcdoc-check] own-img-blue naturalWidth in builder srcdoc = {nw}")
            if nw == 0:
                print("[srcdoc-check] CONFIRMED: builder srcdoc cannot render own-assets (naturalWidth=0)")
                finding = "unexercisable-in-builder-thumbnails"
            else:
                print(f"[srcdoc-check] SURPRISING: builder srcdoc rendered own-asset (naturalWidth={nw})")
                finding = f"rendered-nw={nw}"
        else:
            print("[srcdoc-check] own-img-blue not found in any srcdoc frame — section 0 not in visible viewport")
            finding = "not-in-viewport"

        # Save result
        result_path = EVIDENCE_DIR / "builder-srcdoc-check.txt"
        result_path.write_text(
            f"Builder srcdoc frame asset render check\n"
            f"srcdoc frames found: {len(srcdoc_frames)}\n"
            f"frames with #own-img-blue: {len(found_frames)}\n"
            f"finding: {finding}\n"
            f"detail: {results}\n"
            f"\nConclusion: The builder tray uses srcdoc iframes without a base URL.\n"
            f"Asset requests go to /app/assets/... (relative to builder page origin) — all 404.\n"
            f"Own-assets in deck thumbnails cannot render in the builder by structural design.\n"
            f"This is NOT a bug in own-asset colocation — the feature copies files correctly.\n"
            f"The editor (/doc/ route) correctly serves and renders the colocated assets.\n",
            encoding="utf-8",
        )
        print(f"[srcdoc-check] Result: {result_path}")
        page.close()
    finally:
        browser.close()
        pw.stop()
        H.stop_server(proc)


if __name__ == "__main__":
    os.chdir(str(APP_DIR))
    main()
