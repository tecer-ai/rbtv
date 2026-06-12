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


def _html_outside_spans(html: str, spans: list[tuple[int, int]]) -> str:
    """Return document chrome preserved by recompose: head, separators, tail."""
    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(html[cursor:start])
        cursor = end
    parts.append(html[cursor:])
    return "".join(parts)


def _rewrite_referenced_assets(html: str, replacements: dict[str, str]) -> str:
    """Rewrite only complete asset refs captured by _ASSET_RE."""
    if not replacements:
        return html

    def _replace(match: re.Match) -> str:
        rel_path = match.group(1) or match.group(2)
        replacement = replacements.get(rel_path)
        if not replacement:
            return match.group(0)
        return match.group(0).replace(rel_path, replacement, 1)

    return _ASSET_RE.sub(_replace, html)


def _unique_asset_path(rel_path: str, out_dir: pathlib.Path, allocated: set[str]) -> str:
    """Return assets/name-{n}.ext, free in out_dir and this save."""
    rel = pathlib.PurePosixPath(rel_path)
    for n in range(1, 1000000):
        if rel.suffix:
            candidate = rel.with_name(f"{rel.stem}-{n}{rel.suffix}")
        else:
            candidate = rel.with_name(f"{rel.name}-{n}")
        candidate_str = candidate.as_posix()
        if candidate_str in allocated:
            continue
        if (out_dir / candidate_str).exists():
            continue
        return candidate_str
    raise RuntimeError(f"Unable to allocate unique asset path for {rel_path}")


def colocate_own_assets(html: str, source_root: pathlib.Path, out_dir: pathlib.Path):
    """Copy referenced own assets without rewriting refs."""
    assets_copied: list[str] = []
    assets_skipped: list[str] = []
    assets_missing: list[str] = []
    assets_missing_seen: set[str] = set()
    source_root = pathlib.Path(source_root).resolve()

    for rel_path in _find_referenced_assets(html):
        src_asset = source_root / rel_path
        if not src_asset.exists() or not src_asset.is_file():
            if rel_path not in assets_missing_seen:
                assets_missing_seen.add(rel_path)
                assets_missing.append(rel_path)
            continue

        dst_asset = out_dir / rel_path
        if dst_asset.exists():
            assets_skipped.append(str(rel_path))
            continue

        try:
            dst_asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_asset), str(dst_asset))
        except Exception:
            if rel_path not in assets_missing_seen:
                assets_missing_seen.add(rel_path)
                assets_missing.append(rel_path)
            continue
        assets_copied.append(str(rel_path))

    return assets_copied, assets_skipped, assets_missing


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
            try:
                fragment_spans = split_sections(fragment_html)
            except RecomposeError as exc:
                return (500, {"error": f"Invalid fragment: {exc}"})
            if len(fragment_spans) != 1:
                return (
                    500,
                    {
                        "error": "library fragment must contain exactly one top-level section"
                    },
                )
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

    # Copy referenced assets from libraries.
    assets_copied: list[str] = []
    assets_skipped: list[str] = []
    assets_renamed: list[dict[str, str]] = []
    assets_missing: list[str] = []
    assets_missing_seen: set[str] = set()

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

    # Copy referenced own-assets from preserved source sections when saving
    # to a different directory. Collisions are handled by overriding only the
    # affected existing section HTML before recompose splices it.
    source_root = pathlib.Path(source_path).resolve().parent
    out_root = out_dir.resolve()
    if source_root != out_root:
        asset_targets: dict[str, str] = {}
        allocated: set[str] = set()
        updated_items: list[dict] = []

        for item in recompose_items:
            if item.get("kind") != "existing":
                updated_items.append(item)
                continue

            idx = item["index"]
            start, end = spans[idx]
            section_html = html[start:end]
            replacements: dict[str, str] = {}

            for rel_path in _find_referenced_assets(section_html):
                src_asset = source_root / rel_path
                if not src_asset.exists() or not src_asset.is_file():
                    if rel_path not in assets_missing_seen:
                        assets_missing_seen.add(rel_path)
                        assets_missing.append(rel_path)
                    continue

                target_rel = asset_targets.get(rel_path)
                if target_rel is None:
                    dst_asset = out_dir / rel_path
                    if dst_asset.exists():
                        target_rel = _unique_asset_path(
                            rel_path,
                            out_dir,
                            allocated,
                        )
                        target_asset = out_dir / target_rel
                        target_asset.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src_asset), str(target_asset))
                        assets_renamed.append(
                            {"from": str(rel_path), "to": target_rel}
                        )
                    else:
                        target_rel = rel_path
                        dst_asset.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(src_asset), str(dst_asset))
                        assets_copied.append(str(rel_path))
                    allocated.add(target_rel)
                    asset_targets[rel_path] = target_rel

                if target_rel != rel_path:
                    replacements[rel_path] = target_rel

            if replacements:
                updated_item = dict(item)
                updated_item["html"] = _rewrite_referenced_assets(
                    section_html,
                    replacements,
                )
                updated_items.append(updated_item)
            else:
                updated_items.append(item)

        recompose_items = updated_items

        chrome_copied, chrome_skipped, chrome_missing = colocate_own_assets(
            _html_outside_spans(html, spans),
            source_root,
            out_dir,
        )
        assets_copied.extend(chrome_copied)
        assets_skipped.extend(chrome_skipped)
        for rel_path in chrome_missing:
            if rel_path not in assets_missing_seen:
                assets_missing_seen.add(rel_path)
                assets_missing.append(rel_path)

    # Build final HTML.
    try:
        result = recompose(html, recompose_items)
    except RecomposeError as exc:
        return (500, {"error": str(exc)})

    # Write output.
    try:
        pathlib.Path(out_path).write_text(result, encoding="utf-8")
    except Exception as exc:
        return (500, {"error": str(exc)})

    response: dict = {
        "ok": True,
        "path": out_path,
        "assets_copied": assets_copied,
        "assets_missing": assets_missing,
    }
    if assets_skipped:
        response["assets_skipped"] = assets_skipped
    if assets_renamed:
        response["assets_renamed"] = assets_renamed
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
