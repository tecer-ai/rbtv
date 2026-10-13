#!/usr/bin/env python3
"""Runnable checks for research_check.py: `python3 test_research_check.py`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import research_check as rc

GOOD = f"""# Question

{rc.LEGEND}

The market reached $2.3B in 2025 [1]. A second estimate gives $2.1B [2].

## Sources

[1] Report A — https://a.example/r — 2026-10-13 — 2025-11-15 — TS:9 (AT:10 TR:9 TM:8) — ✓ Verified
[2] Report B — https://b.example/r — 2026-10-13 — undated — TS:7.3 (AT:7 TR:7 TM:8) — ⚠ Redirect → https://b.example/new

## Sources Discarded

{rc.NONE_DISCARDED}
"""


def messages(text):
    return " | ".join(m for _, m in rc.check(text))


def test_pass():
    assert rc.check(GOOD) == [], rc.check(GOOD)
    assert rc.check(GOOD.replace("\n", "\r\n")) == []
    table = "| Source | TS | Reason |\n|---|---|---|\n| [X](https://x.example) | 5.3 | Low authority (AT:4) |"
    assert rc.check(GOOD.replace(rc.NONE_DISCARDED, table)) == []


def test_each_finding():
    cases = {
        "legend line": GOOD.replace("Threshold: TS ≥ 6", "Threshold: 6"),
        "not in the form": GOOD.replace(" — ✓ Verified", ""),
        "not the average": GOOD.replace("TS:9 (AT:10", "TS:8 (AT:10"),
        "below 6": GOOD.replace("TS:7.3 (AT:7 TR:7 TM:8)", "TS:5.3 (AT:5 TR:5 TM:6)"),
        "no line in Sources": GOOD.replace("$2.1B [2]", "$2.1B [3]"),
        "cited nowhere": GOOD.replace(" [2].", "."),
        "no '## Sources Discarded'": GOOD.replace("## Sources Discarded", "## Rejected"),
        "neither the table": GOOD.replace(rc.NONE_DISCARDED, "None."),
        "prohibited term": GOOD.replace("The market", "The revolutionary market"),
        "no '## Sources' section": GOOD.replace("## Sources\n", "## References\n"),
        "between 1 and 10": GOOD.replace("AT:10 TR:9 TM:8", "AT:11 TR:9 TM:7"),
        "already listed": GOOD.replace("[2] Report B", "[1] Report B"),
    }
    for expected, text in cases.items():
        assert text != GOOD, expected
        assert expected in messages(text), (expected, messages(text))


def test_cli(tmp: Path):
    good = tmp / "good.md"
    good.write_text(GOOD, encoding="utf-8")
    assert rc.main([str(good)]) == 0
    bad = tmp / "bad.md"
    bad.write_text(GOOD.replace("[1].", "."), encoding="utf-8")
    assert rc.main([str(bad)]) == 1
    assert rc.main([str(tmp / "absent.md")]) == 2


if __name__ == "__main__":
    import tempfile
    test_pass()
    test_each_finding()
    with tempfile.TemporaryDirectory() as d:
        test_cli(Path(d))
    print("OK — all checks passed")
