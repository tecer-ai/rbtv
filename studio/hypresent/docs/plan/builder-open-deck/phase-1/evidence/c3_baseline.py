"""Check the original deck for baseline console errors (for comparison with c3 output).

Opens the ORIGINAL deck (from temp copy) directly in a headed browser to see
if the ERR_FILE_NOT_FOUND errors pre-exist before any recompose.
"""
import os
import pathlib
import sys
import time

EVIDENCE = pathlib.Path(__file__).resolve().parent

# Read the source path from the previous exercise
src_path_file = EVIDENCE / ".c3-srcpath"
if not src_path_file.exists():
    print("ERROR: .c3-srcpath not found — run c3_exercise.py first")
    sys.exit(1)

src_copy = src_path_file.read_text().strip()
print(f"Source copy path: {src_copy}")
if not os.path.exists(src_copy):
    print("ERROR: source copy file not found")
    sys.exit(1)

console_msgs = []
console_log_file = str(EVIDENCE / "c3-baseline-console.log")

from playwright.sync_api import sync_playwright

file_url = "file:///" + src_copy.replace("\\", "/").replace(" ", "%20")
print(f"Opening: {file_url}")

t0 = time.time()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def on_console(msg):
        console_msgs.append({
            "type": msg.type,
            "text": msg.text,
        })

    page.on("console", on_console)
    page.goto(file_url, wait_until="load")
    page.wait_for_timeout(3000)
    wall_ms = int((time.time() - t0) * 1000)
    browser.close()

with open(console_log_file, "w", encoding="utf-8") as f:
    f.write(f"Browser wall time: {wall_ms}ms\n")
    f.write(f"Total console messages: {len(console_msgs)}\n\n")
    for msg in console_msgs:
        f.write(f"[{msg['type'].upper()}] {msg['text']}\n")

print(f"Wall time: {wall_ms}ms")
print(f"Console messages: {len(console_msgs)}")
for msg in console_msgs:
    print(f"  [{msg['type'].upper()}] {msg['text']}")
print(f"Saved to {console_log_file}")
