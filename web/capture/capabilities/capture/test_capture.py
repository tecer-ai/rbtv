#!/usr/bin/env python3
"""Runnable checks for capture.py: `python3 test_capture.py`. No network, no pytest."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import capture as c


# --- content gate -----------------------------------------------------------
# The ordering is the thing under test: rich prose must win over a captcha
# phrase, and the ratio gate must only fire on large thin-prose bodies.

def test_gate():
    ok, why = c._validate_body("x" * 8, 0)
    assert not ok and "body_too_small" in why, why

    # Rich prose accepted even though the body carries a challenge phrase —
    # a real wall never ships an article alongside the challenge.
    body = "<html>verify you are human" + "z" * 5000 + "</html>"
    ok, why = c._validate_body(body, c._PROSE_OK_CHARS)
    assert ok, why

    # Same phrase, thin prose -> blocked.
    ok, why = c._validate_body(body, 300)
    assert not ok and "captcha_or_bot_wall" in why, why

    # Absolute prose floor.
    ok, why = c._validate_body("<html>" + "z" * 5000, 10)
    assert not ok and "low_content_density" in why and "minimum" in why, why

    # Ratio gate: 100 prose chars in a big body fails...
    ok, why = c._validate_body("z" * 100000, 100)
    assert not ok and "ratio" in why, why
    # ...but the same ratio in a body under the size gate passes.
    ok, why = c._validate_body("z" * 1000, 100)
    assert ok, why

    # Local files skip captcha + density entirely.
    ok, why = c._validate_body("verify you are human" + "z" * 5000, 0, is_local=True)
    assert ok, why


# --- slugs, dates, filenames ------------------------------------------------

def test_naming():
    assert c._slugify("Hello, World! 2024") == "hello-world-2024"
    assert len(c._slugify("x " * 200)) <= 80
    assert c._title_slug("Staff Report: A/B — Notes+More") == "staff-report-a-b-notes-more"
    assert c._title_slug("!!!") == ""

    assert c._filename("My Title", "u", "md", "2024-01-02") == "2024-01-02-my-title.md"
    # No title -> slug of the URL's host+path.
    assert c._filename("", "https://ex.com/a", "md", "2024-01-02") == "2024-01-02-ex-com-a.md"

    assert c._parse_published_date("0000-12-31") is None
    assert c._parse_published_date("garbage") is None
    assert c._parse_published_date("") is None
    assert c._parse_published_date("2024-03-04T10:00:00Z") == "2024-03-04"
    assert c._parse_published_date(date(2024, 3, 4)) == "2024-03-04"

    # --capture-date wins; else a local file's existing date prefix is PRESERVED
    # (routing a staged clip must not re-date it); else today.
    assert c._resolve_capture_date("2020-01-01", Path("2019-05-05-x.md")) == "2020-01-01"
    assert c._resolve_capture_date(None, Path("2019-05-05-x.md")) == "2019-05-05"
    assert c._resolve_capture_date(None, Path("no-date.md")) == date.today().isoformat()
    assert c._resolve_capture_date(None, None) == date.today().isoformat()
    # A bogus override falls through to the prefix rather than crashing.
    assert c._resolve_capture_date("0000-01-01", Path("2019-05-05-x.md")) == "2019-05-05"


# --- extractor chain --------------------------------------------------------

def test_chain():
    def fake(text):
        return lambda body: text

    rich = "p" * c._PROSE_OK_CHARS
    # First rung clears the bar -> later rungs never run.
    funcs = {"defuddle": fake(rich), "trafilatura": fake("x" * 9999),
             "bs4": fake("x" * 9999)}
    assert c._extract_article("<html/>", "auto", funcs) == (rich, "defuddle")

    # defuddle unavailable ("" = this rung does not exist) -> trafilatura.
    funcs = {"defuddle": fake(""), "trafilatura": fake(rich), "bs4": fake("x")}
    assert c._extract_article("<html/>", "auto", funcs)[1] == "trafilatura"

    # Nobody clears the bar -> the LONGEST result is kept for the gate to rule on.
    funcs = {"defuddle": fake("aa"), "trafilatura": fake("bbbb"), "bs4": fake("c")}
    assert c._extract_article("<html/>", "auto", funcs) == ("bbbb", "trafilatura")

    # All empty -> nothing, and the gate will block it.
    assert c._extract_article("<html/>", "auto",
                              {k: fake("") for k in c.EXTRACTORS}) == ("", None)

    # A NAMED extractor runs alone and hard-errors when unavailable — no silent
    # substitution, or the reported extractor would be a lie.
    funcs = {"defuddle": fake(""), "trafilatura": fake(rich), "bs4": fake(rich)}
    assert c._extract_article("<html/>", "trafilatura", funcs)[1] == "trafilatura"
    try:
        c._extract_article("<html/>", "defuddle", funcs)
    except RuntimeError as exc:
        assert "defuddle" in str(exc)
    else:
        raise AssertionError("named-but-unavailable extractor must raise")


# --- PDF detection ----------------------------------------------------------

def test_pdf(tmp: Path):
    assert c._is_pdf_body("", b"%PDF-1.7\n...")
    assert c._is_pdf_body("%PDF-1.4", b"")
    assert not c._is_pdf_body("<html>", b"<html>")
    # Magic bytes beyond the first KB are NOT a PDF (that's article text).
    assert not c._is_pdf_body("x" * 2000 + "%PDF-", b"x" * 2000 + b"%PDF-")

    named = tmp / "a.pdf"
    named.write_bytes(b"not really")
    assert c._is_pdf_path(named)          # extension
    mislabeled = tmp / "b.bin"
    mislabeled.write_bytes(b"%PDF-1.5 x")
    assert c._is_pdf_path(mislabeled)     # magic bytes
    plain = tmp / "c.html"
    plain.write_bytes(b"<html/>")
    assert not c._is_pdf_path(plain)
    assert not c._is_pdf_path(tmp / "missing")

    assert c._normalize_pdf_text("Staﬀ Aﬃrms ﬁne") == "Staff Affirms fine"

    # PDF save: title-slug name, no date prefix, and a re-run is REFUSED rather
    # than overwriting the first capture.
    res = c._capture_pdf(raw=b"%PDF-1.4 body", source_key="url", source_val="u",
                         title="My Doc", out=None, out_dir=tmp, dry_run=False,
                         pdf_text=False, mode="markdown")
    assert res["state"] == "captured" and res["path"] == str(tmp / "my-doc.pdf")
    assert (tmp / "my-doc.pdf").read_bytes() == b"%PDF-1.4 body"
    res = c._capture_pdf(raw=b"x", source_key="url", source_val="u", title="My Doc",
                         out=None, out_dir=tmp, dry_run=False, pdf_text=False,
                         mode="markdown")
    assert res["state"] == "blocked" and "collision" in res["failure_reason"]
    # --title is required for a PDF.
    res = c._capture_pdf(raw=b"x", source_key="url", source_val="u", title="",
                         out=None, out_dir=tmp, dry_run=False, pdf_text=False,
                         mode="markdown")
    assert res["state"] == "blocked" and "--title" in res["failure_reason"]


# --- result shape -----------------------------------------------------------

def test_result_keys():
    r = c._result(state="captured", url="u")
    assert set(r) == {"state", "url", "path", "sidecar", "title", "extractor",
                      "mode", "bytes", "prose_chars", "failure_reason",
                      "transform_error", "transform_warning"}, sorted(r)
    assert "url" not in c._result(file="f")


if __name__ == "__main__":
    import tempfile
    test_gate()
    test_naming()
    test_chain()
    test_result_keys()
    with tempfile.TemporaryDirectory() as d:
        test_pdf(Path(d))
    print("OK — all checks passed")
