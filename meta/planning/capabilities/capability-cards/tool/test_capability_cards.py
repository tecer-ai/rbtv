#!/usr/bin/env python3
"""Self-test for capability_cards.py — assert-based, no framework."""

import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True  # the mirror is read-only: never drop __pycache__ in it
sys.path.insert(0, os.path.dirname(__file__))
import capability_cards as cc

HEADER = "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"


def run(*argv):
    """Return (exit_code, stdout, stderr) of one CLI invocation."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cc.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def component(root, rel, manifest=None):
    """Create a component folder under root, optionally with an exposure.csv."""
    comp = Path(root) / rel
    comp.mkdir(parents=True)
    (comp / "component.md").write_text("x")
    if manifest is not None:
        (comp / "exposure.csv").write_text(manifest)


def test_malformed_header():
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/badcomp", "wrong,header\nfoo,bar\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, "malformed header keeps exit 0"
        assert "unrecognized header, skipped" in err, err
        assert out == "0 cards\n", f"skipped rows must render no cards, got {out!r}"


def test_leading_comment_manifest():
    """ADX-1: '#' lines before the header are skipped, cards render, line numbers still true."""
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/commented",
                  "# a note, with a comma\n#\n" + HEADER
                  + "cid,capability,skill,exhibit,browse.md,routes to three CLIs\n"
                  + "shorty,two\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, code
        assert "unrecognized header" not in err, err
        assert "part-id: cid" in out, out
        assert "short row at line 5" in err, f"line numbers must count the comments: {err!r}"


def test_blank_line_before_header():
    """ADX-3(1): blank lines before the header are skipped too, and line numbers still count them."""
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/gapped",
                  "# a note\n\n" + HEADER
                  + "gid,capability,skill,exhibit,gapped.md,renders\n"
                  + "shorty,two\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, code
        assert "unrecognized header" not in err, f"the blank line is not the header: {err!r}"
        assert "part-id: gid" in out, out
        assert "short row at line 5" in err, f"line numbers must count the blank: {err!r}"


def test_blank_data_row_skipped():
    """ADX-3(2): a blank line among the rows is not a part — warn, and no card."""
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/blankrow", HEADER + "\nbid,capability,skill,exhibit,b.md,ok\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, code
        assert "blank row at line 2, skipped" in err, err
        assert "short row at line 2" not in err, f"a blank line is a blank row, not a short row: {err!r}"
        assert out.count("part-id:") == 1, f"only the real row renders: {out!r}"
        assert "part-id: —" not in out, "a blank line must not render an eight-dash card"


def test_empty_fields_render_dash():
    """ADX-3(3): ANY empty field renders '—', not only description."""
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/holes", HEADER + "hid,,skill,,entry,,\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, code
        assert "short row" not in err, f"all seven fields present, none missing: {err!r}"
        for expected in ("part-id: hid", "part-kind: —", "rbtv-cli: —",
                         "entry-point: entry", "description: —"):
            assert expected in out, f"{expected!r} missing from {out!r}"


def test_short_row():
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/shortcomp", HEADER + "only,three,values\n")
        code, out, err = run("list", "--root", root)
        assert code == 0, "short row keeps exit 0"
        assert "short row at line 2" in err, err
        assert "method: values" in out and "entry-point: —" in out, out


def test_empty_root():
    with tempfile.TemporaryDirectory() as root:
        code, out, _ = run("list", "--root", root)
        assert code == 0 and out == "0 cards\n", out


def test_missing_manifest_warning():
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/nomanifest")
        code, _, err = run("list", "--root", root)
        assert code == 0
        assert err == "warn: meta/nomanifest has no exposure manifest\n", err


def test_duplicate_part_id_and_sort():
    with tempfile.TemporaryDirectory() as root:
        # created out of order on purpose: the ordering must come from the sort, not from readdir
        component(root, "office/z", HEADER + "dup,kind,method,cli,entry,later\n")
        component(root, "meta/a", HEADER + "dup,kind,method,cli,entry,first\n")
        code, out, _ = run("show", "--root", root, "dup")
        assert code == 0
        assert out.count("part-id: dup") == 2, "show prints ALL matches"
        assert out.index("description: first") < out.index("description: later"), out
        _, out, _ = run("list", "--root", root)
        assert out.index("module: meta") < out.index("module: office"), out


def test_show_missing():
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/x", HEADER + "a,b,c,d,e,f\n")
        code, _, err = run("show", "--root", root, "missing")
        assert code == 1
        assert "no exposed part 'missing'" in err, err


def test_missing_root():
    code, _, err = run("list", "--root", "/does/not/exist")
    assert code == 2
    assert err.startswith("error:"), err


def test_json_fields():
    with tempfile.TemporaryDirectory() as root:
        component(root, "meta/x", HEADER + "a,b,c,d,e,f\n")
        component(root, "meta/nomanifest")  # its warn must not reach stdout
        code, out, err = run("list", "--root", root, "--json")
        assert code == 0
        assert "warn:" in err and "warn:" not in out, "warns are stderr-only"
        data = json.loads(out)
        assert len(data) == 1
        assert set(data[0].keys()) == set(cc.CARD_FIELDS)


def main_test():
    test_malformed_header()
    test_leading_comment_manifest()
    test_blank_line_before_header()
    test_blank_data_row_skipped()
    test_empty_fields_render_dash()
    test_short_row()
    test_empty_root()
    test_missing_manifest_warning()
    test_duplicate_part_id_and_sort()
    test_show_missing()
    test_missing_root()
    test_json_fields()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main_test())
