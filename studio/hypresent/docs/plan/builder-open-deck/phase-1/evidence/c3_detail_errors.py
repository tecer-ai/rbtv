"""Get detailed console errors with URL info from both source and output decks."""
import os
import pathlib
import sys
import time

EVIDENCE = pathlib.Path(__file__).resolve().parent

src_copy = (EVIDENCE / ".c3-srcpath").read_text().strip()
out_path = (EVIDENCE / ".c3-outpath").read_text().strip()

from playwright.sync_api import sync_playwright


def get_console_with_requests(file_path, label):
    """Open file in headed browser, capture console + network failures."""
    console_msgs = []
    network_failures = []

    file_url = "file:///" + file_path.replace("\\", "/").replace(" ", "%20")
    print(f"\n=== {label}: {file_url} ===")

    t0 = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        def on_console(msg):
            console_msgs.append({"type": msg.type, "text": msg.text})

        def on_request_failed(req):
            network_failures.append({
                "url": req.url,
                "failure": req.failure,
            })

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)
        page.goto(file_url, wait_until="load")
        page.wait_for_timeout(3000)
        wall_ms = int((time.time() - t0) * 1000)
        browser.close()

    print(f"Wall time: {wall_ms}ms")
    print(f"Console messages ({len(console_msgs)}):")
    for msg in console_msgs:
        print(f"  [{msg['type'].upper()}] {msg['text']}")
    print(f"Network failures ({len(network_failures)}):")
    for nf in network_failures:
        print(f"  FAIL: {nf['url']} ({nf['failure']})")
    return console_msgs, network_failures, wall_ms


# Run on both
src_console, src_net, src_wall = get_console_with_requests(src_copy, "SOURCE (pre-recompose)")
out_console, out_net, out_wall = get_console_with_requests(out_path, "OUTPUT (post-recompose)")

# Compare
print("\n=== COMPARISON ===")
print(f"Source: {len(src_console)} console msgs, {len(src_net)} network failures")
print(f"Output: {len(out_console)} console msgs, {len(out_net)} network failures")

new_errors = len(out_console) - len(src_console)
new_failures = len(out_net) - len(src_net)
print(f"NEW errors introduced by recompose: {new_errors}")
print(f"NEW network failures introduced by recompose: {new_failures}")

# Find URLs unique to output
src_urls = set(nf['url'] for nf in src_net)
out_urls = set(nf['url'] for nf in out_net)
new_urls = out_urls - src_urls
removed_urls = src_urls - out_urls
print(f"\nURLs only in output (new after recompose): {new_urls}")
print(f"URLs only in source (removed by recompose): {removed_urls}")

verdict = "PASS" if new_errors <= 0 and new_failures <= 0 else "FAIL"
print(f"\nVERDICT: {verdict} — recompose-introduced errors = {new_errors}")

# Write summary
with open(str(EVIDENCE / "c3-detail-comparison.txt"), "w", encoding="utf-8") as f:
    f.write("SOURCE (pre-recompose) network failures:\n")
    for nf in src_net:
        f.write(f"  {nf['url']} ({nf['failure']})\n")
    f.write("\nOUTPUT (post-recompose) network failures:\n")
    for nf in out_net:
        f.write(f"  {nf['url']} ({nf['failure']})\n")
    f.write(f"\nNew errors introduced by recompose: {new_errors}\n")
    f.write(f"New network failures: {new_failures}\n")
    f.write(f"VERDICT: {verdict}\n")

print("Saved to c3-detail-comparison.txt")
