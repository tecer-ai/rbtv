"""Conductor reconciliation (B12 fix return): deterministic section-order proof.

Compares top-level <section> sequences across the fix run's three on-disk files:
  deck.html (source copy) -> crossing-1.html (after reorder, STE save)
  -> crossing-2.html (after editor edit, OIB save).
Expected: crossing-1 = deck with sections 0,1 swapped; crossing-2 = crossing-1 order
with the [CV-B12] marker added in section 0 (and editor serialization differences only).
"""
import re, hashlib
from pathlib import Path

FILES = {
    "deck":      Path(r"C:\Users\henri\AppData\Local\Temp\tmpz04943zn\deck.html"),
    "crossing1": Path(r"C:\Users\henri\AppData\Local\Temp\tmp849q5hd0\crossing-1.html"),
    "crossing2": Path(r"C:\Users\henri\AppData\Local\Temp\tmp3avlf2eb\crossing-2.html"),
}

def top_level_sections(html):
    spans, depth, start = [], 0, None
    for m in re.finditer(r"<section\b|</section>", html):
        if m.group(0).startswith("<section"):
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append(html[start:m.end()])
                start = None
    return spans

def text_sig(section_html, strip_marker=False):
    t = re.sub(r"<[^>]+>", " ", section_html)
    t = t.replace("&nbsp;", " ")
    if strip_marker:
        t = t.replace("[CV-B12]", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:90]

out = []
secs = {}
for name, p in FILES.items():
    html = p.read_text(encoding="utf-8")
    s = top_level_sections(html)
    secs[name] = s
    out.append(f"{name}: {p}  ({len(s)} top-level sections)")

for name in FILES:
    out.append(f"\n--- {name} section text signatures (marker-stripped, normalized) ---")
    for i, s in enumerate(secs[name]):
        out.append(f"  [{i}] {text_sig(s, strip_marker=True)}")

deck_sigs = [text_sig(s, True) for s in secs["deck"]]
c1_sigs   = [text_sig(s, True) for s in secs["crossing1"]]
c2_sigs   = [text_sig(s, True) for s in secs["crossing2"]]

expected_swap = [deck_sigs[1], deck_sigs[0]] + deck_sigs[2:]
swap_ok   = (c1_sigs == expected_swap)
order_ok  = (c2_sigs == c1_sigs)
not_orig  = (c2_sigs != deck_sigs)
marker_in_c2_s0 = "[CV-B12]" in secs["crossing2"][0]
marker_count_c2 = sum("[CV-B12]" in s for s in secs["crossing2"])
marker_in_c1 = any("[CV-B12]" in s for s in secs["crossing1"])

out.append("\n=== VERDICTS (computed) ===")
out.append(f"crossing1_order_equals_deck_with_0_1_swapped : {swap_ok}")
out.append(f"crossing2_order_equals_crossing1             : {order_ok}")
out.append(f"crossing2_order_differs_from_original_deck   : {not_orig}")
out.append(f"marker_[CV-B12]_in_crossing2_section0        : {marker_in_c2_s0}")
out.append(f"marker_[CV-B12]_sections_in_crossing2 (count): {marker_count_c2}")
out.append(f"marker_[CV-B12]_anywhere_in_crossing1        : {marker_in_c1}  (expected False)")

report = "\n".join(out)
Path("c1-fix-conductor-order-check.txt").write_text(report, encoding="utf-8")
print(report)
