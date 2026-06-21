"""Builder API handlers — stdlib only.

Handlers shell out to the slide-library engine; the server never parses manifests.
"""

import filecmp
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading

# ---------------------------------------------------------------------------
# Decompose engine import (headless, stdlib only)
# ---------------------------------------------------------------------------
try:
    from . import decompose
except ImportError:
    import decompose

# ---------------------------------------------------------------------------
# Folder dialog (build-spec S-B9.1) — mirror the live file-dialog idiom
# ---------------------------------------------------------------------------
_FOLDER_LOCK = threading.Lock()
_folder_dialog_launcher = None  # tests inject via set_folder_dialog_launcher


def set_folder_dialog_launcher(fn):
    """Inject a fake launcher fn() -> path:str|None."""
    global _folder_dialog_launcher
    _folder_dialog_launcher = fn


_FOLDER_PS = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.WindowState = 'Minimized'
$owner.Opacity = 0
$owner.Show()
try {
  $d = New-Object System.Windows.Forms.FolderBrowserDialog
  $d.Description = 'Select slide library folder'
  if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }
} finally {
  $owner.Close()
  $owner.Dispose()
}
"""


def _run_folder_dialog_default():
    candidates = ["pwsh", "powershell.exe"] if sys.platform == "win32" else ["pwsh"]
    last_exc = None
    with _FOLDER_LOCK:
        for exe in candidates:
            try:
                r = subprocess.run([exe, "-STA", "-NoProfile", "-NonInteractive", "-Command", _FOLDER_PS],
                                   capture_output=True, text=True, encoding="utf-8", timeout=300)
            except FileNotFoundError as exc:
                last_exc = exc
                continue
            path = (r.stdout or "").strip()
            return path if path else None
    raise last_exc if last_exc is not None else FileNotFoundError("No PowerShell executable found")


def _launch_folder_dialog():
    fn = _folder_dialog_launcher if _folder_dialog_launcher is not None else _run_folder_dialog_default
    return fn()


def handle_dialog_folder():
    try:
        path = _launch_folder_dialog()
    except Exception as exc:
        return (500, {"error": f"Dialog failed: {exc}"})
    if not path:
        return (200, {"cancelled": True})
    return (200, {"path": path})


# ---------------------------------------------------------------------------
# Engine subprocess helper (ADX-2)
# ---------------------------------------------------------------------------
def _run_engine(library_path, args, engine="assemble.py"):
    """Run the library's vendored engine; return (returncode, stdout, stderr)."""
    engine_path = os.path.join(library_path, engine)
    if not os.path.isfile(engine_path):
        return (None, "", f"no {engine} in library: {library_path}")
    proc = subprocess.run([sys.executable, engine_path, *args],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=library_path)
    return (proc.returncode, proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# Theme/library-ref helpers (multi-theme assembly, §5.E/F)
# ---------------------------------------------------------------------------
def _repo_root(start_path):
    """Walk up from start_path to the nearest ancestor containing a .git entry.

    start_path may be a file or directory. Returns the absolute path of the
    ancestor directory, or None if no .git ancestor is found before the root.
    """
    current = os.path.abspath(start_path)
    if os.path.isfile(current):
        current = os.path.dirname(current)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _library_ref(library_path, out_path):
    """Compute a repo-root-relative reference from the deck to the library.

    Returns a forward-slash normalized relative path, or "" when the deck is
    not in a repo or the library lives outside that repo root.
    """
    repo_root = _repo_root(os.path.dirname(out_path))
    if repo_root is None:
        return ""
    library_abs = os.path.abspath(library_path)
    repo_root_abs = os.path.abspath(repo_root)
    ref = os.path.relpath(library_abs, repo_root_abs).replace("\\", "/")
    if ref.startswith(".."):
        return ""
    return ref


# ---------------------------------------------------------------------------
# handle_library_load (build-spec S-B9.2) — passthrough of the engine envelope
# ---------------------------------------------------------------------------
def handle_library_load(payload):
    path = payload.get("path")
    if not path:
        return (500, {"error": "Missing 'path'"})
    rc, out, err = _run_engine(path, ["--catalog-data", "--json"])
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(out)
    except Exception:
        return (500, {"error": f"engine did not return JSON: {err or out[:200]}"})
    return (200, envelope)  # ok:false (invalid library) passes through as 200; the GUI shows it


# ---------------------------------------------------------------------------
# handle_library_validate_target — lightweight validation for an EXPORT TARGET
# ---------------------------------------------------------------------------
def handle_library_validate_target(payload):
    """Validate a folder as an export-TARGET library WITHOUT running its engine.

    The Export-to-library "Choose…" picker needs only the target folder PATH,
    validated against what the export actually requires (handle_deck_export):
      1. library.json exists and parses (decompose.load_library_json reads it);
      2. manifest.md exists and has a "## Slides" section with a table
         (exported rows are appended there via _append_rows_to_slides_table).

    It deliberately does NOT run the target's vendored assemble.py engine: the
    export pipeline never invokes it, so requiring it here wrongly rejects valid
    export targets that do not vendor the engine binary. The left-rail browse
    picker still uses the full catalog load (handle_library_load) — it genuinely
    needs the parsed slide catalog to render the grid.

    Returns (200, {"ok": True, "path": path}) on success, or
            (200, {"ok": False, "errors": [...]}) listing every defect.
    The GUI shows ok:false as an invalid-target message; HTTP stays 200 so the
    client treats it as a clean rejection, never a thrown network error.
    """
    path = payload.get("path")
    if not path:
        return (500, {"error": "Missing 'path'"})

    root = pathlib.Path(path)
    errors: list[str] = []

    if not root.is_dir():
        return (200, {"ok": False, "errors": [f"Not a folder: {path}"]})

    # 1. library.json must exist and parse.
    library_json_path = root / "library.json"
    if not library_json_path.is_file():
        errors.append("library.json not found — not a slide library.")
    else:
        try:
            json.loads(library_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"library.json is not valid JSON: {exc}")

    # 2. manifest.md must exist and carry a "## Slides" table (where exported
    #    rows are appended). Reuse the same structural scan the export append uses.
    manifest_path = root / "manifest.md"
    if not manifest_path.is_file():
        errors.append("manifest.md not found — nowhere to record exported slides.")
    else:
        try:
            lines = manifest_path.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            errors.append(f"manifest.md could not be read: {exc}")
            lines = []
        slides_start = None
        for i, line in enumerate(lines):
            if line.strip() == "## Slides":
                slides_start = i
                break
        if slides_start is None:
            errors.append("manifest.md has no '## Slides' section — cannot place exported rows.")
        else:
            has_table_row = False
            for line in lines[slides_start + 1:]:
                stripped = line.strip()
                if stripped.startswith("## "):
                    break
                if "|" in line:
                    has_table_row = True
                    break
            if not has_table_row:
                errors.append("manifest.md '## Slides' section has no table — cannot place exported rows.")

    if errors:
        return (200, {"ok": False, "errors": errors})
    return (200, {"ok": True, "path": path})


# ---------------------------------------------------------------------------
# handle_library_asset (build-spec S-B9.3) — serve theme.css / slides/{id}.html
# ---------------------------------------------------------------------------
def handle_library_asset(payload):
    path = payload.get("path"); name = payload.get("name")
    if not path or not name:
        return (500, {"error": "Missing 'path' or 'name'"})
    if ".." in name.replace("\\", "/").split("/"):
        return (400, {"error": "Invalid name"})
    root = pathlib.Path(path).resolve()
    target = (root / name).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return (400, {"error": "Path traversal blocked"})
    if not target.is_file():
        return (404, {"error": f"Not found: {name}"})
    return (200, {"content": target.read_text(encoding="utf-8")})


# ---------------------------------------------------------------------------
# Theme asset URL extraction (copy-on-need, §7)
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r'url\(\s*(["\']?)([^"\')]+)\1\s*\)', re.IGNORECASE)


def _collect_css_asset_basenames(css_text):
    """Return unique basenames referenced by url(...) in *css_text*.

    Ignores data: URIs and absolute http(s) URLs. Paths are normalized with
    forward slashes before basename extraction so backslash URLs behave.
    """
    basenames = []
    seen = set()
    for _, url in _URL_RE.findall(css_text):
        url = url.strip()
        if not url or url.lower().startswith(("data:", "http://", "https://")):
            continue
        base = os.path.basename(url.replace("\\", "/"))
        if not base or base in seen:
            continue
        seen.add(base)
        basenames.append(base)
    return basenames


# ---------------------------------------------------------------------------
# handle_resolve_library (editor support, §5.G)
# ---------------------------------------------------------------------------
def handle_resolve_library(payload):
    """Resolve a deck's repo-root-relative library reference to its themes.

    Payload:
        {
            "deck_path": str,    # absolute path to the open deck file
            "library_ref": str,  # the deck's data-theme-library value
        }

    Returns (status_int, response_dict).
    """
    deck_path = payload.get("deck_path")
    library_ref = payload.get("library_ref") or ""
    if not library_ref:
        return (200, {"resolved": False, "reason": "no library reference stamped"})
    if not deck_path:
        return (500, {"error": "Missing 'deck_path'"})

    repo_root = _repo_root(os.path.dirname(deck_path))
    if repo_root is None:
        return (200, {"resolved": False, "reason": "deck not in a repo"})

    candidate = os.path.normpath(os.path.join(repo_root, library_ref))
    library_json_path = os.path.join(candidate, "library.json")
    if not os.path.isdir(candidate) or not os.path.isfile(library_json_path):
        return (200, {"resolved": False, "reason": f"library not found at {candidate}"})

    try:
        with open(library_json_path, "r", encoding="utf-8") as f:
            library_data = json.load(f)
    except Exception as exc:
        return (200, {"resolved": False, "reason": f"library.json unreadable: {exc}"})

    contract_version = library_data.get("contract_version", "1.0")
    themes = [
        {
            "name": "default",
            "label": "Default",
            "contract_version": contract_version,
        }
    ]
    for theme in library_data.get("themes", []):
        themes.append(
            {
                "name": theme.get("name"),
                "label": theme.get("label", theme.get("name", "")),
                "contract_version": theme.get("contract_version", contract_version),
            }
        )

    return (
        200,
        {
            "resolved": True,
            "library_path": candidate,
            "themes": themes,
            "default_theme": library_data.get("default_theme", "default"),
        },
    )


# ---------------------------------------------------------------------------
# handle_copy_theme_assets (editor support, §5.G)
# ---------------------------------------------------------------------------
def handle_copy_theme_assets(payload):
    """Copy a theme's referenced background assets into the deck's assets/.

    Payload:
        {
            "deck_path": str,     # absolute path to the deck HTML file
            "library_path": str,  # absolute path to the resolved library
            "theme_name": str,    # theme name to copy assets for
        }

    Returns (status_int, response_dict) with {"copied": [...], "missing": [...]}.
    Assets already present beside the deck are never overwritten.
    """
    deck_path = payload.get("deck_path")
    library_path = payload.get("library_path")
    theme_name = payload.get("theme_name")
    if not deck_path or not library_path or not theme_name:
        return (500, {"error": "Missing 'deck_path', 'library_path', or 'theme_name'"})

    library_root = os.path.abspath(library_path)
    library_json_path = os.path.join(library_root, "library.json")
    library_data = {}
    if os.path.isfile(library_json_path):
        try:
            with open(library_json_path, "r", encoding="utf-8") as f:
                library_data = json.load(f)
        except Exception:
            pass

    if theme_name == "default":
        theme_file = "theme.css"
    else:
        theme_file = f"themes/{theme_name}.css"
        for theme in library_data.get("themes", []):
            if theme.get("name") == theme_name:
                theme_file = theme.get("file", theme_file)
                break

    theme_css_path = os.path.join(library_root, theme_file)
    if not os.path.isfile(theme_css_path):
        return (200, {"copied": [], "missing": [], "error": "theme css not found"})

    try:
        css_text = pathlib.Path(theme_css_path).read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read theme css: {exc}"})

    basenames = _collect_css_asset_basenames(css_text)
    deck_assets_dir = os.path.join(os.path.dirname(os.path.abspath(deck_path)), "assets")
    os.makedirs(deck_assets_dir, exist_ok=True)

    extra_root = None
    extra_asset_root = library_data.get("extra_asset_root")
    if extra_asset_root:
        extra_root = os.path.normpath(os.path.join(library_root, extra_asset_root))

    copied = []
    missing = []
    for base in basenames:
        if os.path.sep in base or "/" in base or base == ".." or base.endswith("."):
            missing.append(base)
            continue
        dst = os.path.join(deck_assets_dir, base)
        if os.path.isfile(dst):
            continue
        src = os.path.join(library_root, "assets", base)
        if not os.path.isfile(src) and extra_root:
            src = os.path.join(extra_root, base)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, dst)
                copied.append(base)
            except Exception:
                missing.append(base)
        else:
            missing.append(base)

    return (200, {"copied": copied, "missing": missing})


# ---------------------------------------------------------------------------
# handle_assemble (build-spec S-B9.4) — passthrough of the engine assemble envelope
# ---------------------------------------------------------------------------
def handle_assemble(payload):
    path = payload.get("path"); slides = payload.get("slides"); out = payload.get("out")
    if not path or not slides or not out:
        return (500, {"error": "Missing 'path', 'slides', or 'out'"})
    args = ["--slides", ",".join(slides), "--out", out, "--json"]
    for flag, key in (("--lang","lang"),("--title","title"),("--accent","accent"),("--client-logo","client_logo")):
        if payload.get(key):
            args += [flag, payload[key]]
    if payload.get("theme"):
        args += ["--theme", payload["theme"]]
    ref = _library_ref(path, out)
    if ref:
        args += ["--library-ref", ref]
    rc, eout, err = _run_engine(path, args)
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(eout)
    except Exception:
        return (500, {"error": f"engine did not return JSON: {err or eout[:200]}"})
    return (200, envelope)  # engine ok:false passes through


# ---------------------------------------------------------------------------
# Manifest id reader (mirrors engine/assemble.py parse_manifest scoping)
# ---------------------------------------------------------------------------
def _parse_manifest_ids(manifest_path):
    """Collect existing slide ids from a library manifest's ## Slides table.

    Mirrors the consuming engine (engine/assemble.py _find_section_rows +
    _split_row): find the "## Slides" heading, read pipe rows until the next
    "## " heading, drop the header + separator rows, and take each data row's
    first cell. Returns a set (empty on any read/parse failure — best-effort).
    """
    ids: set[str] = set()
    try:
        if not (manifest_path.exists() and manifest_path.is_file()):
            return ids
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ids

    in_slides = False
    rows: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped == "## Slides":
                in_slides = True
            elif in_slides:
                break
            continue
        if in_slides and "|" in line:
            rows.append(line)

    # rows[0] = header, rows[1] = separator; data starts at rows[2].
    for line in rows[2:]:
        cells = line.strip().split("|")
        if cells and cells[0].strip() == "":
            cells = cells[1:]
        if cells and cells[-1].strip() == "":
            cells = cells[:-1]
        if cells:
            first = cells[0].strip()
            if first:
                ids.add(first)
    return ids


def _append_rows_to_slides_table(manifest_path, new_lines):
    """Insert new manifest rows at the end of the ## Slides table.

    The ## Slides table ends at the first blank line or the next "## " heading
    after its data rows. Rows are inserted immediately after the last existing
    pipe row in that section so assemble.py's parse_manifest (which reads only
    rows under "## Slides") sees them. Returns "" on success, or an error
    string if the manifest has no "## Slides" section.
    """
    text = manifest_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    slides_start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Slides":
            slides_start = i
            break
    if slides_start is None:
        return "manifest.md has no '## Slides' section — cannot place exported rows"

    # Find the last pipe (table) row within the ## Slides section.
    last_row_idx = None
    for i in range(slides_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            break
        if "|" in lines[i]:
            last_row_idx = i
    if last_row_idx is None:
        return "manifest.md '## Slides' section has no table — cannot place exported rows"

    insert_at = last_row_idx + 1
    new_lines_block = [ln.rstrip("\n") for ln in new_lines]
    merged = lines[:insert_at] + new_lines_block + lines[insert_at:]

    out = "\n".join(merged)
    if text.endswith("\n"):
        out += "\n"
    manifest_path.write_text(out, encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Deck-mode selected-id normalization (synthetic key -> engine-resolvable index)
# ---------------------------------------------------------------------------
_DECK_SECTION_PREFIX = "deck-section-"


def _normalize_deck_selected_id(sid):
    """Map a deck-mode synthetic key "deck-section-{idx}" to the numeric index
    string "{idx}" that decompose_deck resolves via its str(index) fallback.

    Strips the prefix ONLY when the remainder is a pure non-negative integer, so
    a real data-hyp-slide-id or a plain numeric id passes through unchanged.
    Non-string inputs are returned as-is (the engine handles malformed ids).
    """
    if not isinstance(sid, str):
        return sid
    if sid.startswith(_DECK_SECTION_PREFIX):
        suffix = sid[len(_DECK_SECTION_PREFIX):]
        if suffix.isdigit():
            return suffix
    return sid


# ---------------------------------------------------------------------------
# handle_deck_export — export selected slides to a target library via decompose.py
# ---------------------------------------------------------------------------
def handle_deck_export(payload):
    """Export selected deck slides into a target library.

    Payload:
        {
            "deck_path": str,      # absolute path to the deck HTML file
            "selected_ids": list[str],  # slide ids to export
            "library_path": str,   # absolute path to the target library directory
        }

    Returns (status_int, response_dict).
    """
    deck_path = payload.get("deck_path")
    selected_ids = payload.get("selected_ids")
    library_path = payload.get("library_path")

    if not deck_path or selected_ids is None or not library_path:
        return (500, {"error": "Missing 'deck_path', 'selected_ids', or 'library_path'"})

    if not isinstance(selected_ids, list):
        return (500, {"error": "'selected_ids' must be a list"})

    # Row 7 — empty selection is a clear no-op.
    if not selected_ids:
        return (200, {"ok": True, "message": "No slides selected — nothing exported."})

    # Deck-mode synthetic-key normalization.
    # In deck-mode the editor tray identifies each slide by the synthetic key
    # "deck-section-{idx}" (builder-main.js deck-open + tray.js rebase), where
    # {idx} is the slide's 0-based position in the deck's on-disk raw <section>
    # order. The decompose engine resolves a selected id ONLY as a
    # data-hyp-slide-id value or as a numeric str(index) fallback — it does not
    # know the "deck-section-" prefix. The editor serializer strips
    # data-hyp-slide-id on save, so the tray cannot read the real slide id and
    # always sends the synthetic key. Translate it here (the only producer of
    # synthetic keys) to the engine-resolvable numeric index, conservatively:
    # strip ONLY an exact "deck-section-" prefix that leaves a pure integer, so
    # real slide ids and plain numeric ids pass through untouched.
    selected_ids = [_normalize_deck_selected_id(sid) for sid in selected_ids]

    # 1. Read RAW on-disk deck HTML (data-hyp-* intact).
    deck_file = pathlib.Path(deck_path)
    if not deck_file.exists() or not deck_file.is_file():
        return (500, {"error": f"Deck file not found: {deck_path}"})
    try:
        deck_html = deck_file.read_text(encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to read deck: {exc}"})

    # 2. Load target library.json.
    try:
        library_json = decompose.load_library_json(library_path)
    except Exception as exc:
        return (500, {"error": f"Failed to load library.json: {exc}"})

    # 3. Enforce never-overwrite-ready: read existing manifest ids.
    # Parse the ## Slides table the SAME way the consuming assemble.py does
    # (engine/assemble.py _find_section_rows + _split_row): scope to the
    # "## Slides" heading, skip the header + separator rows structurally, and
    # take the first cell of each data row. A substring match on "id" is NOT
    # used — every data row's file cell contains "slides/" (sl-id-es), which
    # would skip every real row and miss the ids it must dedupe against.
    manifest_path = pathlib.Path(library_path) / "manifest.md"
    existing_ids: set[str] = _parse_manifest_ids(manifest_path)

    # 4. Compute deck_assets_dir (deck's own assets/ dir).
    deck_assets_dir = str(deck_file.parent / "assets")
    if not os.path.isdir(deck_assets_dir):
        deck_assets_dir = None

    # Call decompose engine.
    try:
        result = decompose.decompose_deck(
            deck_html=deck_html,
            selected_ids=selected_ids,
            library_json=library_json,
            deck_assets_dir=deck_assets_dir,
            existing_library_ids=existing_ids,
        )
    except decompose.DecomposeError as exc:
        return (500, {"error": str(exc)})
    except Exception as exc:
        return (500, {"error": f"Decompose engine failed: {exc}"})

    # 5. Write fragments, append manifest rows, copy assets.
    lib_root = pathlib.Path(library_path).resolve()
    slides_dir = lib_root / "slides"
    assets_dir = lib_root / "assets"
    slides_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    written_fragments: list[str] = []
    written_rows: list[str] = []
    copied_assets: list[str] = []
    skipped_assets: list[str] = []
    asset_clobber_concerns: list[str] = []
    new_manifest_lines: list[str] = []

    for export in result.exports:
        row = export.row
        fragment_path = slides_dir / f"{row.id}.html"
        try:
            fragment_path.write_text(export.fragment_html, encoding="utf-8")
            written_fragments.append(row.id)
        except Exception as exc:
            return (500, {"error": f"Failed to write fragment {row.id}: {exc}"})

        # Collect the manifest row; written into the ## Slides table below.
        new_manifest_lines.append(decompose.row_to_markdown(row))
        written_rows.append(row.id)

        # Copy assets (skip missing, do not abort).
        for asset_path in export.asset_paths:
            if not os.path.isfile(asset_path):
                skipped_assets.append(os.path.basename(asset_path))
                continue
            base = os.path.basename(asset_path)
            dst = assets_dir / base
            # Never silently clobber a curated library asset of the same name
            # from a different deck. Identical bytes → harmless no-op (re-export
            # of the same asset); differing bytes → skip + flag for human review.
            if dst.exists():
                try:
                    same = filecmp.cmp(asset_path, str(dst), shallow=False)
                except Exception:
                    same = False
                if not same:
                    asset_clobber_concerns.append(
                        f"Asset {base!r} already exists in the target library with "
                        f"different content; kept the existing curated asset and skipped "
                        f"the deck's copy. Resolve the name collision manually if the deck "
                        f"asset is the intended one."
                    )
                    skipped_assets.append(base)
                    continue
                # identical — already present, count as copied (idempotent)
                copied_assets.append(base)
                continue
            try:
                shutil.copy2(asset_path, dst)
                copied_assets.append(base)
            except Exception:
                skipped_assets.append(base)

    # Insert the new rows at the END of the ## Slides table (NOT the end of the
    # file). assemble.py's parse_manifest reads slide rows ONLY under the
    # "## Slides" heading; a row appended past "## Assets" is invisible at
    # re-assembly (the round-trip silently loses the exported slide) and would
    # be mis-read as an asset row.
    if new_manifest_lines:
        try:
            err = _append_rows_to_slides_table(manifest_path, new_manifest_lines)
        except Exception as exc:
            return (500, {"error": f"Failed to append manifest rows: {exc}"})
        if err:
            return (500, {"error": err})

    # 6. Register the deck's stamped theme into the target library, when new.
    try:
        theme_result = decompose.register_deck_theme(
            library_path, library_json, deck_html
        )
    except Exception as exc:
        return (500, {"error": f"Failed to register deck theme: {exc}"})

    # Build response.
    response: dict = {
        "ok": True,
        "exported": len(result.exports),
        "fragments": written_fragments,
        "manifest_rows": written_rows,
        "theme": theme_result,
    }
    all_concerns = list(result.concerns) + asset_clobber_concerns
    if all_concerns:
        response["concerns"] = all_concerns
    if copied_assets:
        response["assets_copied"] = copied_assets
    if skipped_assets:
        response["assets_skipped"] = skipped_assets

    return (200, response)


# ---------------------------------------------------------------------------
# Archive handlers — thin passthrough to the library's vendored archive.py
# ---------------------------------------------------------------------------
def handle_archive(payload):
    path = payload.get("path")
    slide_id = payload.get("slide_id")
    if not path or not slide_id:
        return (500, {"error": "Missing 'path' or 'slide_id'"})
    rc, out, err = _run_engine(path, [slide_id, "--json"], engine="archive.py")
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(out)
    except Exception:
        return (500, {"error": f"archive tool did not return JSON: {err or out[:200]}"})
    return (200, envelope)


def handle_unarchive(payload):
    path = payload.get("path")
    slide_id = payload.get("slide_id")
    if not path or not slide_id:
        return (500, {"error": "Missing 'path' or 'slide_id'"})
    rc, out, err = _run_engine(path, ["--unarchive", slide_id, "--json"], engine="archive.py")
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(out)
    except Exception:
        return (500, {"error": f"archive tool did not return JSON: {err or out[:200]}"})
    return (200, envelope)


def handle_archive_list(payload):
    path = payload.get("path")
    if not path:
        return (500, {"error": "Missing 'path'"})
    rc, out, err = _run_engine(path, ["--list", "--json"], engine="archive.py")
    if rc is None:
        return (500, {"error": err})
    try:
        envelope = json.loads(out)
    except Exception:
        return (500, {"error": f"archive tool did not return JSON: {err or out[:200]}"})
    return (200, envelope)


# ---------------------------------------------------------------------------
# handle_preset_save — append a new composition-only preset to presets.md
# ---------------------------------------------------------------------------
def handle_preset_save(payload):
    """Append a new named preset block to the library's presets.md.

    Payload:
        {
            "library_path": str,   # absolute path to the slide library directory
            "name": str,           # preset name (used as the ### heading + preset: key)
            "lang": str,           # current deck language (e.g. "en")
            "slides": [str, ...],  # ordered slide-id list from the tray
        }

    Writes a block of the form:

        ### {name}

        ```yaml
        preset: {name}
        lang: {lang}
        slides: [{slide1}, {slide2}, ...]
        ```

    to the library's presets.md (creating it with a "## Presets" header if absent).

    Composition-only scope (owner-decided 2026-06-18): captures slide order + lang;
    title/audience/accent are NOT written (the owner fills those manually if desired).

    Returns (200, {"ok": True, "name": name}) on success.
    """
    library_path = payload.get("library_path")
    name = payload.get("name", "").strip()
    lang = payload.get("lang", "").strip()
    slides = payload.get("slides")

    if not library_path:
        return (500, {"error": "Missing 'library_path'"})
    if not name:
        return (400, {"error": "Preset name must not be empty"})
    if not isinstance(slides, list):
        return (400, {"error": "'slides' must be a list"})

    lib_root = pathlib.Path(library_path).resolve()
    if not lib_root.is_dir():
        return (500, {"error": f"Library path is not a directory: {library_path}"})

    presets_path = lib_root / "presets.md"

    # Read existing content (or start fresh).
    if presets_path.exists():
        try:
            text = presets_path.read_text(encoding="utf-8")
        except Exception as exc:
            return (500, {"error": f"Failed to read presets.md: {exc}"})
    else:
        text = ""

    # Guard: duplicate name check.
    heading = f"### {name}"
    for line in text.splitlines():
        if line.strip() == heading:
            return (409, {"error": f"A preset named '{name}' already exists"})

    # Build the new block.
    slides_yaml = "[" + ", ".join(slides) + "]" if slides else "[]"
    block = (
        f"\n### {name}\n"
        f"\n"
        f"```yaml\n"
        f"preset: {name}\n"
        f"lang: {lang}\n"
        f"slides: {slides_yaml}\n"
        f"```\n"
    )

    # Ensure the file has a "## Presets" section.
    if "## Presets" not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n## Presets\n"

    # Append the block.
    if not text.endswith("\n"):
        text += "\n"
    text += block

    try:
        presets_path.write_text(text, encoding="utf-8")
    except Exception as exc:
        return (500, {"error": f"Failed to write presets.md: {exc}"})

    return (200, {"ok": True, "name": name})
