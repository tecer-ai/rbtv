#!/usr/bin/env python3
"""capture.py — fetch a URL (or route a local file) and save readable prose to disk.

CLI:
    capture.py --url URL   [--out FILE | --out-dir DIR] [options]
    capture.py --file PATH [--out FILE | --out-dir DIR] [options]

    --file PATH may be "-" to read the content from stdin (then --title is
    REQUIRED, since there is no filename to derive a slug from).

Exactly one of --out / --out-dir is required, except under --dry-run where both
may be omitted (nothing is written, so there is nothing to place).

WHAT THIS TOOL IS FOR
    One fetch, one content decision, one file. The interesting parts are not the
    download — they are (a) deciding whether what came back is actually an
    article rather than a bot wall or a JavaScript shell, and (b) getting the
    prose out of it. Both are documented in place below, because both are full
    of non-obvious ordering that looks arbitrary until you know which false
    positive it was written against.

THE EXTRACTOR CHAIN
    --extractor auto tries three extractors IN ORDER and stops at the first
    whose output clears the rich-prose threshold (_PROSE_OK_CHARS):

      1. defuddle  — the installed `defuddle` CLI (node). Run against the
         ALREADY-FETCHED body written to a temp file, NEVER against the URL:
         one fetch only, so the PDF check, the captcha check and the saved
         sidecar all see the same bytes the extractor saw. A missing binary or
         a non-zero exit means this rung is simply unavailable — fall through
         silently, it is not an error.
      2. trafilatura — lazy optional import; a purpose-built readability
         library that handles diverse layouts.
      3. bs4 — lazy optional import; richest-container selection (see
         _extract_bs4). Last resort is a regex tag-strip, dependency-free.

    "Stop at the first that clears the threshold" — not "first that returns
    anything" — because a rung can return a thin husk (a nav-only fragment) and
    still be non-empty. If NO rung clears the threshold, the LONGEST result is
    kept and handed to the content gate, which rules on it. That way a genuinely
    short article still gets captured, and a genuinely empty shell still gets
    blocked, without the chain having to tell those two apart itself.

    --extractor <name> (anything but auto) runs ONLY that rung. If it is
    unavailable that is a HARD ERROR: the caller named a specific extractor, so
    silently substituting a different one would be lying about what produced the
    output.

PDFs
    A response whose first kilobyte carries the %PDF- magic header, or a local
    file with a .pdf extension, is BINARY-COPIED — never decoded to text and
    dumped into a .md. That decoding path is a false-success generator: the
    decoded bytes go through the HTML extractor, produce enough garbage to pass
    the content gate as "rich prose", and get written out as a captured article
    with zero real prose in it. --title is REQUIRED for a PDF (the filename is
    the title slug, with no date prefix) and an existing PDF at the destination
    is NEVER overwritten. --pdf-text additionally writes a text companion via
    pypdf; a failure there is reported but never blocks the PDF capture itself.

OUTPUT
    Exactly one JSON object on stdout, success or failure. Diagnostics go to
    stderr. Exit 0 when state=captured, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Content-gate constants
# ---------------------------------------------------------------------------

# Fetched body below this many bytes is immediately blocked (byte floor).
# Catches 0-byte and a-few-junk-bytes responses (truncated/empty body). A real
# HTML response — even a one-paragraph article — is always well above this once
# wrapped in <html>/<head> markup, so this floor never false-fails a genuine
# page. Local files are exempt from the density/captcha checks but still pass
# this floor (a 0-byte local file is still a non-capture).
_BODY_MIN_BYTES = 16

# Extracted prose below this many characters is a density failure regardless of
# body size. Catches pure JS shells / Next.js self.__next_f.push() fragment soup
# that yield ~0 prose characters after boilerplate is stripped (measured: a
# 377 KB Next.js soup extracts 0 chars). A genuine article — even a terse
# one-sentence breaking-news item — clears this floor.
# Local-file and PDF paths are EXEMPT (the user already vetted the content).
_PROSE_MIN_CHARS = 25

# Density-ratio floor (extracted-prose chars / total body bytes), applied ONLY to
# bodies at or above _DENSITY_RATIO_BODY_BYTES. This is the gate that catches a
# LARGE-but-contentless shell whose stray visible text (a "Loading..." splash, a
# cookie banner, nav chrome) survives stripping and clears the absolute prose
# floor: a 100-389 KB JS shell measures ratio ~0.0003-0.0005, while a genuine
# article — even one buried in heavy inline-CSS chrome — measures >=0.04. The
# 0.005 floor sits ~10x above observed shells and ~8x below the lightest genuine
# multi-paragraph article. Small bodies (< _DENSITY_RATIO_BODY_BYTES) skip this
# gate: a tiny real page has few absolute prose chars but cannot be a "large
# contentless shell", and the absolute floor already guards near-empty bodies.
_DENSITY_MIN_RATIO = 0.005
_DENSITY_RATIO_BODY_BYTES = 2048

# Extracted-prose ceiling above which the captcha and ratio gates are SKIPPED: a
# body that yields this many characters of clean article prose IS a successful
# capture, however much markup surrounded it. This prevents the ratio gate from
# false-blocking a genuine multi-MB page that server-renders a real article
# alongside a large client-hydration payload (a Next.js article page carrying
# ~2 MB of self.__next_f.push() soup: the article extracts cleanly to ~500
# chars, but prose/body ratio is ~0.0002 because the soup dwarfs it). Observed
# shells sit far below this (stray-text shells extract <=140 chars), so the
# ceiling never lets a shell through. After extraction the prose IS the captured
# content, so prose volume — not raw body size — is the right signal once it is
# substantial. This same constant is the extractor chain's accept threshold.
_PROSE_OK_CHARS = 400

# CAPTCHA / bot-wall fingerprint patterns (case-insensitive substring scan).
# Matches interstitial challenges served with HTTP 200 on real article URLs.
# CONTENT-GATED: this scan runs ONLY when extracted prose is thin
# (< _PROSE_OK_CHARS). A content-rich body — even one whose page chrome happens
# to contain a challenge word (Wikipedia's logged-out signup UI carries the word
# "Captcha") — is accepted before this scan ever runs, because a real bot-wall
# REPLACES the content with a short challenge page; it never ships 40 KB of
# article prose alongside the challenge. Patterns are therefore specific
# challenge PHRASES, not bare interstitial words, as defense in depth on the
# thin-prose path (a bare "captcha" still matched legitimate signup/login chrome
# on thin pages).
_CAPTCHA_PATTERNS = [
    r"verify you are (?:a )?human",
    r"verify that you are (?:a )?human",
    r"are you a robot",
    r"i(?:'| a)m not a robot",
    r"complete the captcha",
    r"solve the captcha",
    r"captcha challenge",
    r"please complete the captcha",
    r"cloudflare-challenge",
    r"cf-challenge",
    r"challenge-form",
    r"checking your browser before",
    r"please wait\.\.\. \|",  # Cloudflare "One moment" splash
    r"<title>access denied</title>",
    r"<title>just a moment\.\.\.</title>",
    r"<title>attention required",
    r"window\._cf_chl",           # Cloudflare JS challenge variable
    r"window\.__aw_",             # Imperva AW challenge
    r"_imperva_",                 # Imperva challenge marker (specific token)
    r"incapsula incident id",     # Imperva/Incapsula block page
]
_CAPTCHA_RE = re.compile("|".join(_CAPTCHA_PATTERNS), re.IGNORECASE | re.DOTALL)


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

# Tags whose entire subtree is boilerplate; stripped before prose extraction.
_STRIP_TAGS = {
    "script", "style", "noscript", "template",
    "nav", "header", "footer", "aside",
    "form", "button", "iframe", "svg", "canvas",
}

# Candidate main-content container selectors. ALL matching containers are
# evaluated (not just the first) and the one yielding the MOST prose wins —
# `<body>` is always evaluated as an additional candidate. First-match-wins was
# a regression: a page carrying an EMPTY semantic wrapper (a bare `<article>`
# shell whose paragraphs live in a sibling `.post-content`) matched the first
# selector, short-circuited the loop on a 0-prose container, and the body
# fallback never fired — a content-rich server-rendered article extracted 0
# chars and was false-blocked by the density gate.
_CONTENT_SELECTORS = [
    "article",
    "main",
    '[role="main"]',
    ".article-body",
    ".post-content",
    ".entry-content",
    ".article__body",
    ".story-body",
    ".content-body",
    "#content",
    "#main-content",
    ".main-content",
]

EXTRACTORS = ("defuddle", "trafilatura", "bs4")


def _extract_defuddle(html_body: str) -> str:
    """Run the `defuddle` CLI on the already-fetched body. "" if unavailable.

    The body is written to a temp file and defuddle is pointed at the FILE, never
    at the URL — defuddle would happily fetch the URL itself, but that would be a
    second fetch, and a second fetch can return different bytes than the ones the
    PDF check and the captcha scan ruled on. One fetch, one set of bytes.

    A missing binary, a crash, or a non-zero exit all mean the same thing: this
    rung is unavailable. Return "" and let the caller fall through.
    """
    import tempfile

    exe = shutil.which("defuddle")
    if exe is None:
        return ""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(html_body)
        tmp_path = Path(tmp.name)
    try:
        # `defuddle parse <source>`; -m asks for markdown, which keeps links and
        # headings intact instead of flattening them to plain text.
        proc = subprocess.run(
            [exe, "parse", str(tmp_path), "-m"],
            capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", errors="replace").strip()


def _extract_trafilatura(html_body: str) -> str:
    """Lazy trafilatura extraction. "" when the package is not installed."""
    try:
        import trafilatura  # type: ignore
    except ImportError:
        return ""
    result = trafilatura.extract(
        html_body, include_comments=False, include_tables=True, no_fallback=False
    )
    return (result or "").strip()


def _root_to_markdown(root) -> str:
    """Render a bs4 element subtree to clean markdown-flavored prose.

    Preserves paragraph/heading/list/quote breaks. Returns "" when the subtree
    holds no block-level text — the signal the richest-container comparison and
    the density gate both key on (an empty wrapper or a JS shell yields "").
    """
    lines: list[str] = []
    for elem in root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "td", "th"],
        recursive=True,
    ):
        text = elem.get_text(separator=" ", strip=True)
        if not text:
            continue
        name = elem.name
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lines.append("#" * int(name[1]) + " " + text)
        elif name == "li":
            lines.append("- " + text)
        elif name == "blockquote":
            lines.append("> " + text)
        else:
            lines.append(text)
    return "\n\n".join(lines)


def _extract_bs4(html_body: str) -> str:
    """Richest-container extraction via BeautifulSoup4 (lazy optional import).

    Strips boilerplate subtrees, then evaluates EVERY matching content selector
    AND <body>, keeping whichever yields the most characters. NEVER break on the
    first match: an empty semantic wrapper would short-circuit the real article
    living in a sibling container. If bs4 itself is missing, a regex tag-strip
    runs as the last resort — crude, but dependency-free, and a genuine JS shell
    still yields ~0 prose from it, so the density gate keeps blocking it.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        # Drop <script>/<style> SUBTREES (not just their tags) before stripping
        # markup: their bodies are not markup, so a bare tag-strip leaves raw CSS
        # and JS behind as "prose". That inflates the character count, which is
        # exactly the number the chain's longest-wins tiebreak and the density
        # gate both read — a page of stylesheet would out-measure a real article.
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html_body)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        return "\n".join(l.strip() for l in text.splitlines() if l.strip())

    soup = BeautifulSoup(html_body, "html.parser")
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    body = soup.find("body")
    candidates = []
    for sel in _CONTENT_SELECTORS:
        candidates.extend(soup.select(sel))
    if body is not None:
        candidates.append(body)

    markdown = ""
    for root in candidates:
        cand = _root_to_markdown(root)
        if len(cand.strip()) > len(markdown.strip()):
            markdown = cand
    if not markdown.strip():
        root = body if body is not None else soup
        markdown = root.get_text(separator="\n", strip=True)
    return markdown.strip()


_EXTRACTOR_FUNCS = {
    "defuddle": _extract_defuddle,
    "trafilatura": _extract_trafilatura,
    "bs4": _extract_bs4,
}


def _extract_article(
    html_body: str, choice: str = "auto", funcs: Optional[dict] = None
) -> tuple[str, Optional[str]]:
    """Return (prose, extractor_name) — the chain described in the module docstring.

    ``funcs`` exists so the selection logic can be driven with fake extractors in
    tests; production always uses the real table.

    Raises RuntimeError when an EXPLICITLY named extractor is unavailable. A
    named extractor that silently falls back would misreport which tool produced
    the output, and the whole point of naming one is to know that.
    """
    funcs = funcs or _EXTRACTOR_FUNCS
    if choice != "auto":
        prose = funcs[choice](html_body).strip()
        if not prose:
            raise RuntimeError(
                f"extractor {choice!r} produced nothing — it is either not "
                f"installed or failed on this body. Install it, or use "
                f"--extractor auto to fall through the chain."
            )
        return prose, choice

    best, best_name = "", None
    for name in EXTRACTORS:
        prose = funcs[name](html_body).strip()
        if len(prose) >= _PROSE_OK_CHARS:
            # Clears the rich-prose bar — no reason to keep asking.
            return prose, name
        if len(prose) > len(best):
            best, best_name = prose, name
    # Nothing cleared the bar. Hand the longest result to the content gate and
    # let IT decide: a short-but-real article passes, a shell does not.
    return best, best_name


# ---------------------------------------------------------------------------
# Content gate
# ---------------------------------------------------------------------------

def _validate_body(body: str, prose_chars: int, *, is_local: bool = False) -> tuple[bool, str]:
    """Validate a body before writing it out. Returns (ok, failure_reason).

    Gate ORDER is the load-bearing part:
      0. Byte floor — catches the 0-byte / truncated response. Applies to
         everything, local files included.
      1. Rich-prose accept — substantial prose IS a successful capture, and it
         returns BEFORE the captcha and density gates ever run. A real bot-wall
         REPLACES the article with a short challenge page; it never ships
         substantial article prose alongside the challenge. So a content-rich
         body cannot be a wall, and any challenge words in it are page chrome.
         Without this ordering, the substring scan false-blocks legitimate
         articles whose chrome mentions a captcha.
      2. CAPTCHA / bot-wall fingerprints — THIN prose only. The body is short
         enough that a challenge page is plausible.
      3. Density — THIN prose only. Two complementary floors: an absolute prose
         floor catches a shell yielding ~0 prose at any size, and a size-gated
         prose/body RATIO floor catches a large shell whose stray visible text
         clears the absolute floor.
    Local files are exempt from 2 and 3 (the user already vetted the content);
    only the byte floor applies to them.
    """
    body_bytes = len(body.encode("utf-8"))
    if body_bytes < _BODY_MIN_BYTES:
        return False, f"body_too_small: {body_bytes} bytes < {_BODY_MIN_BYTES} byte floor"

    if is_local:
        return True, ""

    if prose_chars >= _PROSE_OK_CHARS:
        return True, ""

    m = _CAPTCHA_RE.search(body)
    if m:
        matched = m.group(0)[:60].replace("\n", " ")
        return False, f"captcha_or_bot_wall: interstitial marker detected: {matched!r}"

    if prose_chars < _PROSE_MIN_CHARS:
        return False, (
            f"low_content_density: extracted prose {prose_chars} chars < "
            f"{_PROSE_MIN_CHARS} minimum; body is likely a JS shell or landing page"
        )

    if body_bytes >= _DENSITY_RATIO_BODY_BYTES:
        ratio = prose_chars / body_bytes
        if ratio < _DENSITY_MIN_RATIO:
            return False, (
                f"low_content_density: prose/body ratio {ratio:.5f} < "
                f"{_DENSITY_MIN_RATIO} on a {body_bytes}-byte body "
                f"({prose_chars} prose chars); body is likely a large JS shell "
                "or landing page with negligible article content"
            )

    return True, ""


# ---------------------------------------------------------------------------
# Dates, slugs, filenames
# ---------------------------------------------------------------------------

# Implausible year sentinels: year 0000, year 9999, pre-1800 dates.
_DATE_MIN_YEAR = 1800
_DATE_MAX_YEAR = 2200

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# A staged/clipped filename opens with its capture (clip) date — the date the
# source was originally saved (YYYY-MM-DD-slug). Routing such a file MUST
# preserve that date rather than re-stamp today; see _resolve_capture_date.
_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")

# Title-slug algorithm: lowercase; each run of whitespace and + / : – — becomes a
# single "-"; remaining punctuation is removed; consecutive "-" collapse. This is
# the PDF filename, with NO date prefix (unlike the date-prefixed saves _filename
# produces).
_TITLE_HYPHEN_RE = re.compile(r"[\s+/:–—]+")
_TITLE_DROP_RE = re.compile(r"[^a-z0-9-]")


def _parse_published_date(raw: object) -> Optional[str]:
    """Defensive lenient date parser. Returns an ISO date string, or None.

    Accepts a date object or an ISO 'YYYY-MM-DD' string (a longer timestamp is
    truncated to its date part). Returns None on malformed, empty, or
    implausible input (year outside [1800, 2200] — 0000-12-31 and 9999-xx-xx are
    the sentinels real feeds actually emit) and NEVER raises: a bad date must
    degrade to "no date", not crash a capture.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, date):
        return raw.isoformat() if _DATE_MIN_YEAR <= raw.year <= _DATE_MAX_YEAR else None
    s = str(raw).strip()
    if not s:
        return None
    try:
        d = date.fromisoformat(s[:10])
    except (ValueError, IndexError):
        return None
    return d.isoformat() if _DATE_MIN_YEAR <= d.year <= _DATE_MAX_YEAR else None


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower().strip()).strip("-")[:80]


def _title_slug(title: str) -> str:
    """Kebab-slug of a document title — the PDF filename."""
    s = _TITLE_HYPHEN_RE.sub("-", title.lower())
    s = _TITLE_DROP_RE.sub("", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def _resolve_capture_date(explicit: Optional[str], local_file: Optional[Path]) -> str:
    """Resolve the date prefix for a date-stamped filename.

    Precedence:
      1. --capture-date (validated here; an implausible value falls through).
      2. The YYYY-MM-DD prefix of a local --file's stem — preserves a staged
         file's ORIGINAL clip date when it is routed somewhere else, instead of
         silently re-dating it to today.
      3. Today — a fresh fetch. A URL capture passes no local file, so it is
         always dated today unless --capture-date overrides.
    """
    if explicit:
        iso = _parse_published_date(explicit)
        if iso:
            return iso
    if local_file is not None:
        m = _DATE_PREFIX_RE.match(Path(local_file).stem)
        if m:
            return m.group(1)
    return date.today().isoformat()


def _filename(title: str, source: str, ext: str, capture_date: str) -> str:
    slug = _slugify(title) if title else _slugify(source.split("//")[-1])
    return f"{capture_date}-{slug}.{ext}"


# ---------------------------------------------------------------------------
# PDF handling
# ---------------------------------------------------------------------------

# Below this many extracted characters the PDF is treated as scanned/image-only
# and the --pdf-text companion is NOT written (a husk would let a grep-based
# verification pass on nothing).
_PDF_TEXT_MIN_CHARS = 200

# Latin typographic ligatures pypdf emits as a single codepoint from academic
# fonts ("Staﬀ", "Aﬀairs"). Expanded to ASCII so the text stays grep-able.
_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}
_LIGATURE_TABLE = {ord(k): v for k, v in _LIGATURES.items()}


def _normalize_pdf_text(text: str) -> str:
    """Expand the seven Latin typographic ligatures to ASCII.

    Surgical by design — touches ONLY those codepoints, never math symbols or
    accents. A blanket NFKC would alter those too.
    """
    return text.translate(_LIGATURE_TABLE)


def _is_pdf_path(path: Path) -> bool:
    """Detect a PDF by .pdf extension OR %PDF- magic bytes (mislabeled files)."""
    if path.suffix.lower() == ".pdf":
        return True
    try:
        with path.open("rb") as fh:
            return fh.read(5) == b"%PDF-"
    except OSError:
        return False


def _is_pdf_body(body: str, raw: bytes) -> bool:
    """True when a fetched response is a PDF.

    Keyed on the %PDF- magic header in the first kilobyte — strictly more
    reliable than Content-Type, which servers routinely mislabel as
    application/octet-stream. The decoded-text arm covers the case where only a
    decoded body is available. Magic-byte detection, not text decoding, is what
    stops a fetched PDF from being run through the HTML extractor and
    false-succeeding as an article.
    """
    return b"%PDF-" in raw[:1024] or "%PDF-" in body[:1024]


def _extract_pdf_text(src: Path) -> tuple[str, str]:
    """Return (extracted_text, error). pypdf is a lazy optional dependency."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return "", "pypdf is required for --pdf-text. Install it: pip install pypdf"
    try:
        reader = PdfReader(str(src))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return _normalize_pdf_text(text), ""
    except Exception as exc:  # pypdf raises a wide family on malformed files
        return "", f"pypdf extraction failed: {exc}"


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

# Declared default UA — fair-access endpoints (SEC EDGAR and friends) 403 blank
# or default-library UAs. Override with --user-agent when an endpoint's policy
# requires a contact-bearing UA (e.g. "Name contact@example.com").
DEFAULT_USER_AGENT = "capture/1.0 (+article capture tool)"


def _extract_title(body: str) -> str:
    """Return the <title> text if present, else ""."""
    m = re.search(r"<title[^>]*>([^<]+)</title>", body, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, str, bytes]:
    """Fetch via urllib. Returns (body_text, page_title, raw_bytes). Raises on error.

    ``raw_bytes`` is the UNDECODED body, kept so a PDF response can be saved
    byte-identically instead of being lossily decoded into a text file.
    """
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — caller-supplied URL is the point
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    body = raw.decode(charset, errors="replace")
    return body, _extract_title(body), raw


def _curl_fetch_url(url: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, str, bytes]:
    """Fetch via subprocess curl with the same User-Agent.

    The fallback for transport-level blocks: curl's HTTP stack and TLS
    fingerprint pass some bot walls that reject a Python client outright. The
    binary is resolved explicitly via shutil.which, never through a shell alias
    (PowerShell aliases `curl` to Invoke-WebRequest, which takes none of these
    flags). Raises RuntimeError on any failure.
    """
    curl_bin = shutil.which("curl")
    if curl_bin is None:
        raise RuntimeError("curl binary not found on PATH")
    cmd = [
        curl_bin, "--silent", "--show-error", "--fail", "--location",
        "--max-time", "30", "--user-agent", user_agent, url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"curl invocation failed: {exc}")
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"curl exit {proc.returncode}: {stderr or 'no stderr'}")
    raw = bytes(proc.stdout or b"")
    return raw.decode("utf-8", errors="replace"), _extract_title(raw.decode("utf-8", "replace")), raw


def _save(dest: Path, content: str, dry_run: bool) -> int:
    """Write content to dest (parents created). Returns the byte length."""
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------

def _result(**kw) -> dict:
    """Build the single JSON object this tool prints. Every key always present."""
    out = {
        "state": "blocked", "url": None, "file": None, "path": None,
        "sidecar": None, "title": "", "extractor": None, "mode": "markdown",
        "bytes": 0, "prose_chars": 0, "failure_reason": None,
        "transform_error": None, "transform_warning": None,
    }
    out.update(kw)
    # Only one of url/file applies; drop the irrelevant one so the object matches
    # the documented contract exactly.
    if out["url"] is None:
        out.pop("url")
    else:
        out.pop("file")
    return out


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def _pdf_dest(out: Optional[Path], out_dir: Optional[Path], title: str) -> tuple[Optional[Path], str]:
    """Resolve where a PDF goes. Returns (dest, error). --title is REQUIRED."""
    if not title:
        return None, (
            "PDF capture requires --title: the filename is the kebab-slug of the "
            'document\'s printed title. Re-run with --title "<document title>".'
        )
    slug = _title_slug(title)
    if not slug:
        return None, f"--title {title!r} yields an empty title-slug; pass the printed title."
    if out is not None:
        return out, ""
    if out_dir is not None:
        return out_dir / f"{slug}.pdf", ""
    return None, ""  # dry-run with no destination


def _capture_pdf(
    *, raw: bytes, source_key: str, source_val: str, title: str,
    out: Optional[Path], out_dir: Optional[Path], dry_run: bool, pdf_text: bool,
    mode: str,
) -> dict:
    """Save PDF bytes verbatim. Never decoded, never overwritten."""
    base = {source_key: source_val, "title": title, "mode": mode, "bytes": len(raw)}
    dest, err = _pdf_dest(out, out_dir, title)
    if err:
        return _result(failure_reason=err, **base)
    if dest is None:  # dry-run, no destination named
        return _result(state="captured", **base)
    if dest.exists():
        return _result(
            failure_reason=(
                f"collision: {dest} already exists — a captured PDF is never "
                "overwritten (that would destroy the earlier capture silently)."
            ),
            **base,
        )
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)

    res = _result(state="captured", path=str(dest), **base)
    if not pdf_text:
        return res

    # --pdf-text: a companion text file, so the capture is grep-able. Problems
    # here are REPORTED, never fatal — the PDF itself is already captured.
    companion = dest.with_suffix(".md")
    if companion.exists():
        res["transform_error"] = f"companion exists, not overwritten: {companion}"
        return res
    if dry_run:
        res["sidecar"] = str(companion)
        return res
    text, transform_error = _extract_pdf_text(dest)
    if transform_error:
        res["transform_error"] = transform_error
        return res
    stripped = text.strip()
    if len(stripped) < _PDF_TEXT_MIN_CHARS:
        res["transform_warning"] = (
            f"extracted text is near-empty ({len(stripped)} chars < "
            f"{_PDF_TEXT_MIN_CHARS}) — likely a scanned/image PDF; companion NOT written"
        )
        return res
    header = (
        f"<!-- text extracted from {dest.name} by pypdf; captured "
        f"{date.today().isoformat()} from {source_val} -->\n\n"
    )
    res["bytes"] += _save(companion, header + text, dry_run)
    res["sidecar"] = str(companion)
    res["prose_chars"] = len(stripped)
    return res


def capture_url(
    *, url: str, mode: str, extractor: str, title: str, ext: str,
    out: Optional[Path], out_dir: Optional[Path], user_agent: str,
    curl_fallback: bool, pdf_text: bool, capture_date: Optional[str], dry_run: bool,
) -> dict:
    """Fetch a URL, gate it, extract it, write it."""
    try:
        body, page_title, raw = _fetch_url(url, user_agent)
    except Exception as exc:
        if not curl_fallback:
            return _result(url=url, mode=mode, failure_reason=str(exc))
        try:
            body, page_title, raw = _curl_fetch_url(url, user_agent)
        except Exception as curl_exc:
            return _result(
                url=url, mode=mode,
                failure_reason=f"urllib: {exc}; curl-fallback: {curl_exc}",
            )

    # PDF check runs BEFORE extraction: a PDF is not HTML, so it overrides the
    # requested mode entirely rather than being fed to an HTML extractor.
    if _is_pdf_body(body, raw):
        return _capture_pdf(
            raw=raw, source_key="url", source_val=url, title=title,
            out=out, out_dir=out_dir, dry_run=dry_run, pdf_text=pdf_text, mode=mode,
        )

    resolved_title = title or page_title or url
    body_bytes = len(body.encode("utf-8"))

    # html mode saves the raw page and never extracts — but it still gets a
    # content gate, and the gate needs prose. Extract anyway; only the SAVE
    # differs by mode.
    try:
        prose, used = _extract_article(body, extractor)
    except RuntimeError as exc:
        return _result(url=url, mode=mode, title=resolved_title,
                       bytes=body_bytes, failure_reason=str(exc))
    prose_chars = len(prose.strip())

    ok, failure_reason = _validate_body(body, prose_chars)
    if not ok:
        return _result(url=url, mode=mode, title=resolved_title, extractor=used,
                       bytes=body_bytes, prose_chars=prose_chars,
                       failure_reason=failure_reason)

    prefix = _resolve_capture_date(capture_date, None)
    written = 0
    path = sidecar = None
    if not (out is None and out_dir is None):  # dry-run may name no destination
        if mode == "html":
            dest = out or (out_dir / _filename(resolved_title, url, "html", prefix))
            written += _save(dest, body, dry_run)
            path = str(dest)
        else:
            dest = out or (out_dir / _filename(resolved_title, url, ext, prefix))
            written += _save(dest, prose, dry_run)
            path = str(dest)
            # Archival sidecar: the full page as fetched. The primary file is
            # readable prose, which is lossy by construction — the sidecar is
            # what lets a later re-extraction happen without re-fetching.
            side = (dest.with_suffix(".full.html") if out
                    else out_dir / _filename(resolved_title, url, "full.html", prefix))
            written += _save(side, body, dry_run)
            sidecar = str(side)

    return _result(state="captured", url=url, mode=mode, title=resolved_title,
                   extractor=used, path=path, sidecar=sidecar,
                   bytes=written or body_bytes, prose_chars=prose_chars)


def capture_file(
    *, src: Path, display: str, mode: str, title: str, ext: str,
    out: Optional[Path], out_dir: Optional[Path], pdf_text: bool,
    capture_date: Optional[str], dry_run: bool,
) -> dict:
    """Route a local html/pdf/text file to the destination, content unchanged.

    A local file is content the user already vetted, so it is copied verbatim —
    no extraction, no captcha scan, no density gate. Only the byte floor applies.
    """
    if not src.is_file():
        return _result(file=display, mode=mode, failure_reason=f"--file not found: {src}")

    if _is_pdf_path(src):
        return _capture_pdf(
            raw=src.read_bytes(), source_key="file", source_val=display, title=title,
            out=out, out_dir=out_dir, dry_run=dry_run, pdf_text=pdf_text, mode=mode,
        )

    body = src.read_text(encoding="utf-8", errors="replace")
    resolved_title = title or _extract_title(body) or src.stem
    ok, failure_reason = _validate_body(body, 0, is_local=True)
    if not ok:
        return _result(file=display, mode=mode, title=resolved_title,
                       failure_reason=failure_reason)

    prefix = _resolve_capture_date(capture_date, src)
    path = None
    written = len(body.encode("utf-8"))
    if not (out is None and out_dir is None):
        dest = out or (out_dir / _filename(resolved_title, display, ext, prefix))
        written = _save(dest, body, dry_run)
        path = str(dest)
    return _result(state="captured", file=display, mode=mode, title=resolved_title,
                   path=path, bytes=written,
                   # The file IS the content here, so its own length is the prose
                   # count — nothing was extracted out of it.
                   prose_chars=len(body.strip()))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch a URL (or route a local file) and save readable prose to disk."
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="URL to capture")
    src.add_argument("--file", help="Local html/pdf/text file to route ('-' for stdin; --title required)")
    dest = p.add_mutually_exclusive_group()
    dest.add_argument("--out", help="Write exactly to this file (parents created)")
    dest.add_argument("--out-dir", help="Write into this directory under a generated YYYY-MM-DD-<slug>.<ext> name")
    p.add_argument("--mode", default="markdown", choices=["markdown", "html", "both"],
                   help="markdown: extracted prose (+ .full.html sidecar); html: the raw page; "
                        "both: prose file + .full.html sidecar")
    p.add_argument("--extractor", default="auto", choices=["auto", *EXTRACTORS],
                   help="auto walks defuddle -> trafilatura -> bs4 and stops at the first "
                        "clearing the rich-prose bar; a named extractor runs alone and is a "
                        "hard error when unavailable")
    p.add_argument("--title", default="", help="Override the extracted title for the filename slug (REQUIRED for PDFs)")
    p.add_argument("--ext", default="md", choices=["md", "html", "json"],
                   help="Extension for markdown-mode and local-file saves (default md). "
                        "Does not apply to PDF saves or the .full.html sidecar.")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT,
                   help="User-Agent header (use a contact-bearing UA for fair-access endpoints)")
    p.add_argument("--no-curl-fallback", action="store_true",
                   help="Disable the subprocess-curl retry on transport failure (on by default)")
    p.add_argument("--pdf-text", action="store_true",
                   help="For a PDF capture, also write a text companion extracted via pypdf")
    p.add_argument("--capture-date", default=None,
                   help="Override the filename date prefix (ISO YYYY-MM-DD). Without it, a local "
                        "--file whose stem already carries a YYYY-MM-DD prefix keeps that date; "
                        "otherwise today. Does not apply to PDF saves.")
    p.add_argument("--dry-run", action="store_true", help="Report what would be saved; write nothing")
    return p


def main(argv: Optional[list] = None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.dry_run and not (args.out or args.out_dir):
        print("ERROR: exactly one of --out / --out-dir is required (or use --dry-run).",
              file=sys.stderr)
        return 1
    if args.capture_date is not None and _parse_published_date(args.capture_date) is None:
        print(f"ERROR: --capture-date must be a plausible ISO date (YYYY-MM-DD), "
              f"got {args.capture_date!r}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else None
    out_dir = Path(args.out_dir) if args.out_dir else None

    stdin_tmp: Optional[Path] = None
    try:
        if args.url:
            result = capture_url(
                url=args.url, mode=args.mode, extractor=args.extractor,
                title=args.title, ext=args.ext, out=out, out_dir=out_dir,
                user_agent=args.user_agent, curl_fallback=not args.no_curl_fallback,
                pdf_text=args.pdf_text, capture_date=args.capture_date,
                dry_run=args.dry_run,
            )
        else:
            if args.file == "-":
                # stdin has no filename, so there is no slug and no date prefix
                # to recover from it — --title is the only source left.
                if not args.title:
                    print("ERROR: --file - (stdin) requires --title to derive the filename.",
                          file=sys.stderr)
                    return 1
                import tempfile
                data = sys.stdin.buffer.read()
                with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
                    tmp.write(data)
                    stdin_tmp = Path(tmp.name)
                result = capture_file(
                    src=stdin_tmp, display="-", mode=args.mode, title=args.title,
                    ext=args.ext, out=out, out_dir=out_dir, pdf_text=args.pdf_text,
                    capture_date=args.capture_date, dry_run=args.dry_run,
                )
            else:
                src = Path(args.file)
                result = capture_file(
                    src=src, display=str(src), mode=args.mode, title=args.title,
                    ext=args.ext, out=out, out_dir=out_dir, pdf_text=args.pdf_text,
                    capture_date=args.capture_date, dry_run=args.dry_run,
                )
    finally:
        if stdin_tmp is not None:
            try:
                stdin_tmp.unlink()
            except OSError:
                pass

    print(json.dumps(result, indent=2))
    return 0 if result.get("state") == "captured" else 1


if __name__ == "__main__":
    sys.exit(main())
