#!/usr/bin/env python3
"""Exemplar-screenshot capture capability.

Captures screenshots of URLs and lands them in a reference set's exemplars/
folder with manifest rows appended.

Dependencies: playwright, Pillow (pre-installed in this environment).
Install extra deps with: python -m pip install --user <pkg>
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_PAGE_HEIGHT = 16000  # sane cap for extremely long pages
VIEWPORT_DEFAULT = (1440, 900)
OVERLAY_FLAG = "overlay-present"

# Common cookie / consent overlay selectors for best-effort dismissal
CONSENT_SELECTORS = [
    "button[id*='accept']",
    "button[class*='accept']",
    "button[aria-label*='Accept']",
    "button[aria-label*='accept']",
    "[id*='onetrust-accept']",
    "[id*='cookie-accept']",
    "[class*='cookie-banner'] button",
    "[class*='consent'] button",
]


def parse_viewport(s: str):
    m = re.match(r"^(\d+)x(\d+)$", s.strip().lower())
    if not m:
        raise ValueError(f"Viewport must be WxH, got: {s}")
    return int(m.group(1)), int(m.group(2))


def sanitize_filename(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or "unknown"
    host = re.sub(r"^www\.", "", host)
    path = parsed.path.strip("/")
    base = host
    if path:
        base += "-" + path.replace("/", "-")
    base = re.sub(r"[^a-zA-Z0-9._-]+", "-", base).strip("-.")
    base = re.sub(r"-+", "-", base)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{base}-{today}.png"


def resolve_filename(exemplars_dir: Path, base_name: str) -> Path:
    """Never overwrite: versioned filename on collision."""
    candidate = exemplars_dir / base_name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    version = 2
    while True:
        candidate = exemplars_dir / f"{stem}-v{version}{suffix}"
        if not candidate.exists():
            return candidate
        version += 1


def dismiss_overlays(page):
    """Best-effort cookie/consent dismissal. Returns True if any overlay likely survived."""
    survived = False
    for sel in CONSENT_SELECTORS:
        try:
            els = page.locator(sel).all()
            for el in els:
                if el.is_visible():
                    try:
                        el.click(timeout=500)
                        page.wait_for_timeout(300)
                    except Exception:
                        pass
        except Exception:
            pass
    # Heuristic: if a large fixed-position element still covers the viewport, flag it
    try:
        overlay_els = page.locator(
            "div[style*='position: fixed'], div[style*='position:fixed'], "
            "div[class*='overlay'], div[class*='modal'], div[class*='banner']"
        ).all()
        for el in overlay_els:
            if el.is_visible():
                box = el.bounding_box()
                if box and box.get("height", 0) > 100 and box.get("width", 0) > 300:
                    survived = True
                    break
    except Exception:
        pass
    return survived


def capture_single(
    url: str,
    refs_path: Path,
    viewport: tuple[int, int],
    selector: str | None,
    dry_run: bool = False,
):
    exemplars_dir = refs_path / "exemplars"
    manifest_path = exemplars_dir / "manifest.md"
    exemplars_dir.mkdir(parents=True, exist_ok=True)

    base_name = sanitize_filename(url)
    out_path = resolve_filename(exemplars_dir, base_name)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()

        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except PWTimeout:
            browser.close()
            sys.stderr.write(f"ERROR: Timeout reaching {url}\n")
            return False, "timeout"
        except Exception as e:
            browser.close()
            sys.stderr.write(f"ERROR: Failed to load {url}: {e}\n")
            return False, str(e)

        page.wait_for_timeout(1000)  # let JS settle
        overlay_present = dismiss_overlays(page)

        # Determine scope string
        if selector:
            scope = f"section ({selector})"
        else:
            scope = "full-page"

        try:
            if selector:
                el = page.locator(selector).first
                if not el or not el.is_visible():
                    browser.close()
                    sys.stderr.write(f"ERROR: Selector not found or not visible: {selector}\n")
                    return False, "selector not found"
                el.screenshot(path=str(out_path))
            else:
                page.screenshot(path=str(out_path), full_page=True)
                # Cap extremely long pages
                with Image.open(out_path) as img:
                    w, h = img.size
                    if h > MAX_PAGE_HEIGHT:
                        cropped = img.crop((0, 0, w, MAX_PAGE_HEIGHT))
                        cropped.save(out_path)
                        scope += f" | height-capped-at-{MAX_PAGE_HEIGHT}px"
        except Exception as e:
            browser.close()
            sys.stderr.write(f"ERROR: Screenshot failed for {url}: {e}\n")
            return False, str(e)

        browser.close()

    if overlay_present:
        scope += f" | {OVERLAY_FLAG}"

    # Verify dimensions
    with Image.open(out_path) as img:
        actual_w, actual_h = img.size

    out_hash = file_hash(out_path)
    for existing_path in exemplars_dir.glob("*.png"):
        if existing_path.resolve() == out_path.resolve():
            continue
        if file_hash(existing_path) == out_hash:
            sys.stderr.write(
                "WARN: duplicate-capture: "
                f"{out_path.name} is byte-identical to existing {existing_path.name}\n"
            )
            break

    # Append manifest row
    if not dry_run:
        append_manifest_row(
            manifest_path,
            filename=out_path.name,
            source_url=url,
            capture_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            viewport=f"{viewport[0]}×{viewport[1]}",
            scope=scope,
        )

    print(f"OK: {out_path.name} ({actual_w}x{actual_h}) from {url}")
    return True, None


def append_manifest_row(manifest_path: Path, filename: str, source_url: str, capture_date: str, viewport: str, scope: str):
    """Append a row to the Exemplars table in manifest.md."""
    if not manifest_path.exists():
        # Create minimal manifest if missing
        manifest_path.write_text(
            "# Exemplar Manifest\n\n## Exemplars\n\n"
            "| filename | source_url | capture_date | viewport | scope |\n"
            "|----------|-----------|--------------|----------|-------|\n",
            encoding="utf-8",
        )

    text = manifest_path.read_text(encoding="utf-8")
    row = f"| {filename} | {source_url} | {capture_date} | {viewport} | {scope} |"

    lines = text.splitlines()
    insert_idx = None
    in_exemplars = False
    for i, line in enumerate(lines):
        if line.strip().startswith("## Exemplars"):
            in_exemplars = True
            continue
        if in_exemplars and (re.match(r"^\|[-\s|]+\|$", line) or re.match(r"^\|[-]+\|", line)):
            insert_idx = i + 1
            break

    if insert_idx is None:
        lines.append(row)
    else:
        lines.insert(insert_idx, row)

    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(description="Capture exemplar screenshots.")
    parser.add_argument("--url", action="append", required=True, help="URL to capture (repeatable)")
    parser.add_argument("--refs", required=True, help="Path to reference set (contains exemplars/)")
    parser.add_argument("--viewport", default="1440x900", help="Viewport WxH (default 1440x900)")
    parser.add_argument("--selector", default=None, help="CSS selector for section capture")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files or manifest rows")
    args = parser.parse_args()

    refs_path = Path(args.refs).resolve()
    viewport = parse_viewport(args.viewport)

    exit_code = 0
    for url in args.url:
        ok, reason = capture_single(url, refs_path, viewport, args.selector, dry_run=args.dry_run)
        if not ok:
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
