"""Deck API handlers — load, save, path dialogs."""

import pathlib
import re
import shutil

try:
    from .api import _launch_dialog
    from .recompose import RecomposeError, recompose, split_sections
except ImportError:
    from api import _launch_dialog
    from recompose import RecomposeError, recompose, split_sections


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_head(html: str) -> str | None:
    """Extract inner HTML of <head>...</head>, or None if not found."""
    lowered = html.lower()
    head_start = lowered.find("<head>")
    if head_start == -1:
        head_start = lowered.find("<head ")
    if head_start == -1:
        return None
    tag_end = html.find(">", head_start)
    if tag_end == -1:
        return None
    head_close = lowered.find("</head>")
    if head_close == -1:
        return None
    return html[tag_end + 1 : head_close]


def _strip_scripts_from_head(head_html: str) -> str:
    """Remove <script>...</script> blocks from head HTML."""
    return re.sub(
        r"<script\b[^>]*>.*?</script>",
        "",
        head_html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _resolve_library_fragment(library_path: str, slide_id: str) -> str:
    """Read a library slide fragment, with path-traversal guard."""
    name = f"slides/{slide_id}.html"
    if ".." in name.replace("\\", "/").split("/"):
        raise ValueError("Invalid slide_id")
    root = pathlib.Path(library_path).resolve()
    target = (root / name).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("Path traversal blocked")
    if not target.is_file():
        raise FileNotFoundError(f"Fragment not found: {name}")
    return target.read_text(encoding="utf-8")


_ASSET_RE = re.compile(
    r'(?:src|href)\s*=\s*["\']?(assets/[^"\'>\s]+)["\']?'
    r'|'
    r'url\(\s*["\']?(assets/[^"\'>\s]+)["\']?\s*\)',
    re.IGNORECASE,
)


def _find_referenced_assets(fragment_html: str) -> list[str]:
    """Return unique relative asset paths referenced in fragment HTML."""
    seen: set[str] = set()
    assets: list[str] = []
    for m in _ASSET_RE.finditer(fragment_html):
        path = m.group(1) or m.group(2)
        if path and path not in seen:
            seen.add(path)
            assets.append(path)
    return assets


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def handle_deck_load(payload):
    """Load a deck and return its head (script-free) and ordered sections.

    Returns a (status_int, response_dict) tuple.
    """
    path_str = payload.get("path")
    if not path_str:
        return (500, {"error": "Missing 'path'"})

    p = pathlib.Path(path_str)
    if not p.exists() or not p.is_file():
        return (500, {"error": f"File not found: {path_str}"})

    try:
        html = p.read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read file: {exc}"})

    try:
        spans = split_sections(html)
    except RecomposeError as exc:
        return (500, {"error": str(exc)})

    if not spans:
        return (
            500,
            {"error": "no <section> slides found — not a conforming deck"},
        )

    head = _extract_head(html)
    if head is None:
        head = ""
    else:
        head = _strip_scripts_from_head(head)

    sections = []
    for idx, (start, end) in enumerate(spans):
        sections.append({"index": idx, "html": html[start:end]})

    return (
        200,
        {
            "ok": True,
            "name": p.name,
            "dir": str(p.parent.resolve()),
            "head": head,
            "sections": sections,
        },
    )


def handle_deck_save(payload):
    """Save a restructured deck using recompose.

    Payload:
        {
            "source_path": str,
            "out_path": str,
            "items": [...],
            "libraries": {"<libraryPath>": true}   # optional
        }

    Items:
        {"kind": "existing", "index": int}
        {"kind": "library", "library_path": str, "slide_id": str}
        {"kind": "blank"}

    Returns a (status_int, response_dict) tuple.
    """
    source_path = payload.get("source_path")
    out_path = payload.get("out_path")
    items = payload.get("items")

    if not source_path or not out_path or items is None:
        return (
            500,
            {"error": "Missing 'source_path', 'out_path', or 'items'"},
        )

    if not isinstance(items, list):
        return (500, {"error": "'items' must be a list"})

    src = pathlib.Path(source_path)
    if not src.exists() or not src.is_file():
        return (500, {"error": f"Source file not found: {source_path}"})

    try:
        html = src.read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read source: {exc}"})

    # Pre-validate source has sections.
    try:
        spans = split_sections(html)
    except RecomposeError as exc:
        return (500, {"error": str(exc)})
    if not spans:
        return (
            500,
            {"error": "no <section> slides found — not a conforming deck"},
        )

    # Validate items and resolve fragments (all-or-nothing).
    recompose_items: list[dict] = []
    resolved_fragments: list[tuple[str, str]] = []  # (library_path, slide_id)

    for item in items:
        kind = item.get("kind")
        if kind == "existing":
            idx = item.get("index")
            if not isinstance(idx, int) or idx < 0 or idx >= len(spans):
                return (
                    500,
                    {
                        "error": f"section index {idx} out of range (0-{len(spans) - 1})"
                    },
                )
            recompose_items.append({"kind": "existing", "index": idx})
        elif kind == "library":
            library_path = item.get("library_path")
            slide_id = item.get("slide_id")
            if not library_path or not slide_id:
                return (
                    500,
                    {
                        "error": "library item missing 'library_path' or 'slide_id'"
                    },
                )
            try:
                fragment_html = _resolve_library_fragment(library_path, slide_id)
            except Exception as exc:
                return (500, {"error": f"Failed to load fragment: {exc}"})
            recompose_items.append({"kind": "fragment", "html": fragment_html})
            resolved_fragments.append((library_path, slide_id))
        elif kind == "blank":
            recompose_items.append({"kind": "blank"})
        else:
            return (500, {"error": f"unknown item kind: {kind}"})

    # Parent directory must exist (same refusal as handle_save_as).
    out_dir = pathlib.Path(out_path).parent
    if not out_dir.exists():
        return (
            500,
            {"error": f"Parent directory does not exist: {out_dir}"},
        )

    # Build final HTML.
    try:
        result = recompose(html, recompose_items)
    except RecomposeError as exc:
        return (500, {"error": str(exc)})

    # Copy referenced assets from libraries.
    assets_copied: list[str] = []
    assets_skipped: list[str] = []

    for library_path, slide_id in resolved_fragments:
        fragment_html = _resolve_library_fragment(library_path, slide_id)
        asset_paths = _find_referenced_assets(fragment_html)
        lib_root = pathlib.Path(library_path).resolve()
        for rel_path in asset_paths:
            src_asset = lib_root / rel_path
            if not src_asset.exists() or not src_asset.is_file():
                continue
            dst_asset = out_dir / rel_path
            if dst_asset.exists():
                assets_skipped.append(str(rel_path))
                continue
            dst_asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_asset), str(dst_asset))
            assets_copied.append(str(rel_path))

    # Write output.
    try:
        pathlib.Path(out_path).write_text(result, encoding="utf-8")
    except Exception as exc:
        return (500, {"error": str(exc)})

    response: dict = {
        "ok": True,
        "path": out_path,
        "assets_copied": assets_copied,
    }
    if assets_skipped:
        response["assets_skipped"] = assets_skipped
    return (200, response)


def handle_dialog_open_path():
    """Show a native open dialog and return the chosen path only.

    Returns a (status_int, response_dict) tuple.
    """
    try:
        path = _launch_dialog("open")
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    return (200, {"path": path})


def handle_dialog_save_path():
    """Show a native save dialog and return the chosen path only.

    Returns a (status_int, response_dict) tuple.
    """
    try:
        path = _launch_dialog("save")
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    return (200, {"path": path})
