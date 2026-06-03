"""Pure handlers for the hypresent API — stdlib only, no HTTP logic."""

import pathlib

# ---------------------------------------------------------------------------
# Shared-state callback
# ---------------------------------------------------------------------------
# server.py registers this callback so we can re-point the /doc/ root without
# importing server at the top level (avoids circular imports).
_set_doc_root = None


def register_set_doc_root(fn):
    global _set_doc_root
    _set_doc_root = fn


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
def handle_open(payload):
    """Open an HTML file and point /doc/ at its parent directory.

    Returns a (status_int, response_dict) tuple.
    """
    path_str = payload.get("path")
    if not path_str:
        return (404, {"error": "Missing 'path'"})

    p = pathlib.Path(path_str)
    if not p.exists() or not p.is_file():
        return (404, {"error": f"File not found or not readable: {path_str}"})

    try:
        html = p.read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read file: {exc}"})

    parent = p.parent.resolve()
    if _set_doc_root is not None:
        _set_doc_root(str(parent))

    return (200, {
        "html": html,
        "dir": str(parent),
        "name": p.name,
    })


def handle_save_as(payload):
    """Save HTML string to an absolute path.

    Returns a (status_int, response_dict) tuple.
    """
    path_str = payload.get("path")
    html = payload.get("html")
    if path_str is None or html is None:
        return (500, {"error": "Missing 'path' or 'html'"})

    target = pathlib.Path(path_str)
    parent = target.parent

    # v1 has no allow-root restriction, but we only write if the parent
    # directory already exists (we do not auto-create missing directories).
    if not parent.exists():
        return (500, {"error": f"Parent directory does not exist: {parent}"})

    try:
        target.write_text(html, encoding="utf-8")
    except Exception as exc:
        return (500, {"error": str(exc)})

    return (200, {"ok": True, "path": path_str})
