"""Orchestration model-package install behavior (D18).

The `rbtv-orchestrating` skill ships per-model DOC PACKAGES under
`orchestration/models/<model>/` (manifest, delta, rendered manual, mirror
config). Unlike skills/commands, these packages are NOT copied into the target
`.claude/` — they are read just-in-time from the RBTV source repo (`{rbtv_path}`),
exactly like the cards. "Installing a model package" therefore means TWO things:

  1. Recording which packages the workspace elects (persisted in rbtv.json), so a
     re-install remembers the selection — the per-model conditional install flag.
  2. Baking the resulting availability line into the skill-loaded core
     (`core-protocol.md`) between the `ORCH:AVAILABILITY` markers, so the
     always-loaded capability summary names what is present and what is absent in
     THIS workspace.

Plus a render-freshness check: the rendered manuals are generated from the
dispatch-wrapper template + each delta; this verifies they are not stale relative
to their sources (it calls `render-manuals.py --check`).

Single-shared-source caveat: the `ORCH:AVAILABILITY` markers live in the repo's
`core-protocol.md`, which every workspace's installed SKILL.md loads BY REFERENCE
(it is not copied per workspace). The bake writes the line into that one shared
file. When a single RBTV source repo serves multiple workspaces, the LAST install
wins the availability line. The markers are preserved so re-install is idempotent.
This is the same single-source property the cards and rendered manuals already
have (one repo, N workspaces by reference); per-workspace divergence is out of
D18's scope.

No external dependencies — Python 3.11+ only (the manifest read is a single line
scan, not a YAML parse).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Where the model packages live, relative to the RBTV repo root.
MODELS_RELATIVE = Path("orchestration") / "models"
# The skill-loaded core that carries the availability marker region.
CORE_PROTOCOL_RELATIVE = (
    Path("orchestration") / "skills" / "orchestrating" / "core-protocol.md"
)
# The render script whose --check reports manual drift.
RENDER_SCRIPT_RELATIVE = MODELS_RELATIVE / "render-manuals.py"

# A directory under orchestration/models/ is a MODEL PACKAGE iff it carries a
# manifest.yaml. Infra dirs (_fixture, mirror) are not packages and are skipped.
PACKAGE_MARKER_FILE = "manifest.yaml"

# Availability marker region (namespace ORCH:, distinct from the render script's
# RENDER: namespace). Decision recorded in shape.md (p2-7 core-protocol). The
# installer replaces ONLY the content BETWEEN these markers; the markers
# themselves are preserved so re-install is idempotent.
AVAILABILITY_BEGIN = "<!-- ORCH:AVAILABILITY:BEGIN -->"
AVAILABILITY_END = "<!-- ORCH:AVAILABILITY:END -->"
_AVAILABILITY_RE = re.compile(
    re.escape(AVAILABILITY_BEGIN) + r".*?" + re.escape(AVAILABILITY_END),
    re.DOTALL,
)


def discover_model_packages(rbtv_root: Path) -> list[str]:
    """Return the sorted names of every model package present in the repo.

    A package = a directory under orchestration/models/ that carries a
    manifest.yaml. Returns [] if the models folder is absent (the orchestration
    module may be installed before any package ships).
    """
    models_dir = rbtv_root / MODELS_RELATIVE
    if not models_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in models_dir.iterdir()
        if d.is_dir() and (d / PACKAGE_MARKER_FILE).is_file()
    )


def read_model_display(rbtv_root: Path, pkg: str) -> str:
    """Return a package's human-facing display label (its manifest `display:` field).

    Falls back to the package folder name when the field is absent. Single-line
    scan, no YAML parse — matches discover_model_packages' stdlib-only posture.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("display:"):
                val = stripped[len("display:"):].strip()
                if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                    val = val[1:-1]
                return val or pkg
    except OSError:
        pass
    return pkg


def discover_model_displays(rbtv_root: Path) -> dict[str, str]:
    """Map every model package folder name → its display label (manifest `display:`)."""
    return {pkg: read_model_display(rbtv_root, pkg) for pkg in discover_model_packages(rbtv_root)}


def resolve_selected_packages(
    available: list[str], requested: tuple[str, ...] | None
) -> tuple[list[str], list[str], list[str]]:
    """Split the available packages into (installed, absent, unknown).

    - requested is None  -> elect ALL available packages (default: full install).
    - requested is a set -> elect only the named ones that actually exist;
      names that do not exist are returned as `unknown` (caller warns).

    `installed` = elected AND present; `absent` = present but NOT elected (so the
    core's availability line can name them as absent in this workspace).
    """
    if requested is None:
        return list(available), [], []
    requested_set = list(dict.fromkeys(requested))  # de-dup, preserve order
    installed = [m for m in available if m in requested_set]
    absent = [m for m in available if m not in requested_set]
    unknown = [m for m in requested_set if m not in available]
    return installed, absent, unknown


def _availability_block(
    installed: list[str], absent: list[str], displays: dict[str, str] | None = None
) -> str:
    """The two-line availability block written between the ORCH markers.

    Names render as their human-facing display labels (manifest `display:`) when a
    `displays` map is supplied, falling back to the folder name otherwise.
    Format matches the marker region's fallback shape (two blockquote lines):
        > **Model packages installed:** a, b
        > **Absent:** c, d
    """
    displays = displays or {}
    def _fmt(names: list[str]) -> str:
        return ", ".join(displays.get(n, n) for n in names) if names else "_(none)_"
    installed_text = _fmt(installed)
    absent_text = _fmt(absent)
    return (
        f"{AVAILABILITY_BEGIN}\n"
        f"> **Model packages installed:** {installed_text}\n"
        f"> **Absent:** {absent_text}\n"
        f"{AVAILABILITY_END}"
    )


def bake_availability_line(
    rbtv_root: Path, installed: list[str], absent: list[str]
) -> tuple[bool, str]:
    """Replace the content between the ORCH:AVAILABILITY markers in core-protocol.md.

    Returns (changed, message). Idempotent: the markers are preserved and an
    unchanged line rewrites nothing. Fails soft (returns False + a message) when
    the core file or the markers are absent — never raises, so an install of a
    workspace without the orchestration skill core still completes.
    """
    core_path = rbtv_root / CORE_PROTOCOL_RELATIVE
    if not core_path.is_file():
        return False, f"availability bake skipped: {CORE_PROTOCOL_RELATIVE.as_posix()} not found"

    text = core_path.read_text(encoding="utf-8")
    if AVAILABILITY_BEGIN not in text or AVAILABILITY_END not in text:
        return False, (
            f"availability bake skipped: ORCH:AVAILABILITY markers not found in "
            f"{CORE_PROTOCOL_RELATIVE.as_posix()}"
        )

    new_block = _availability_block(installed, absent, discover_model_displays(rbtv_root))
    new_text, n = _AVAILABILITY_RE.subn(new_block, text)
    if n == 0:
        # Markers present individually but not as an ordered pair — leave untouched.
        return False, (
            f"availability bake skipped: ORCH:AVAILABILITY:BEGIN/END not a matched "
            f"pair in {CORE_PROTOCOL_RELATIVE.as_posix()}"
        )
    if new_text == text:
        return False, (
            f"availability line already current "
            f"(installed: {', '.join(installed) or 'none'}; absent: {', '.join(absent) or 'none'})"
        )
    core_path.write_text(new_text, encoding="utf-8")
    return True, (
        f"availability line baked into {CORE_PROTOCOL_RELATIVE.as_posix()} "
        f"(installed: {', '.join(installed) or 'none'}; absent: {', '.join(absent) or 'none'})"
    )


def check_manual_render(rbtv_root: Path) -> tuple[str, str]:
    """Run the render-freshness check (render-manuals.py --check).

    Returns (status, message) where status is one of:
      - 'fresh'   : all manuals consistent with template + deltas (render exit 0)
      - 'stale'   : at least one manual is stale relative to its sources (exit 1)
      - 'error'   : the render check could not run / malformed markers (exit 2+)
      - 'skipped' : the render script is not present

    NON-FATAL by design (matches the installer's _check_plugin_prereqs warn-not-
    abort convention): the caller WARNS on 'stale'/'error' and proceeds. Manuals
    are read JIT from {rbtv_path}, so a stale manual degrades gracefully — the
    routing card already trusts the live folder over any baked line.
    """
    script = rbtv_root / RENDER_SCRIPT_RELATIVE
    if not script.is_file():
        return "skipped", f"render check skipped: {RENDER_SCRIPT_RELATIVE.as_posix()} not found"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=str(rbtv_root),
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # pragma: no cover - environment failure
        return "error", f"render check could not run: {exc}"

    detail = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        return "fresh", "render check: all manuals fresh"
    if proc.returncode == 1:
        return "stale", "render check: STALE manual(s) — manuals are out of date with their sources:\n" + detail
    return "error", f"render check: ERROR (exit {proc.returncode}) — manuals could not be verified:\n" + detail
