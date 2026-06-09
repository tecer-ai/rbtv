"""guidance.py — render guidance files for every CLAUDE.md in a workspace.

This module is the guidance-render leg of the mirror driver. It walks a target
workspace recursively, finds every CLAUDE.md that is not excluded or inside a
nested git repository, and writes a sibling guidance file (e.g. AGENTS.md or
QWEN.md) using the banner/compose primitives from the parent mirror.py engine
so that driver output is byte-identical to mirror.py output for the same source.

Public API
----------
    render_guidance(target_root, guidance_filename, *, check, excluded_paths,
                    banner_label="")
        -> list[dict[str, str]]   # managed guidance-file records

Each record has the shape:
    { "path": "<workspace-relative posix path>",
      "kind": "guidance",
      "owner": "agents-md" | "qwen-md" }

The ``owner`` field encodes which guidance-filename group owns the file so the
state layer (p1-4) can implement ref-counted uninstall by filename.

Design constraints (from decisions.md)
--------------------------------------
- NEVER read module-manifest.json or sb-os.json — source-agnostic by design.
- Banner is ALWAYS produced by mirror.py's ``make_banner`` — never re-implemented.
- Nested git repos (a directory that contains ``.git`` but is NOT the workspace
  root) receive no guidance file.
- ``excluded_paths`` entries are workspace-root-relative posix strings.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import the shared primitive from the sibling mirror.py so output is
# byte-identical to mirror.py for the same source.  The driver dir sits at
# orchestration/models/mirror/driver/ — mirror.py is one level up.
# ---------------------------------------------------------------------------
_MIRROR_DIR = Path(__file__).resolve().parent.parent  # .../models/mirror/
sys.path.insert(0, str(_MIRROR_DIR))
from mirror import make_banner, write_if_changed  # noqa: E402  (path manipulation above)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKIP_DIR_NAMES: frozenset[str] = frozenset({".git", "node_modules"})

ROOT_PREAMBLE = """\
# Mandatory Rule Loading — Read Before ANY Action

Before performing ANY action in this workspace — including but not limited to:

- reading any file
- writing or editing any file
- running any tool, script, or shell command
- dispatching any sub-agent
- responding to the user (questions, clarifications, summaries — anything)

…you MUST first read EVERY file under `.agents/behavior-rules/` and treat its
contents as **unconditional, non-negotiable rules** that govern this session.

These rules are not advisory. They cannot be overridden, deferred, or skipped
because the task seems simple, mechanical, or urgent. They apply to every turn,
every tool call, every sub-agent dispatch, and every response — for the entire
session.

After loading the rules, follow the project instructions below.

---

"""

# guidance_filename → owner tag recorded in the state's managed_files list.
# Unknown filenames fall back to the filename stem lowercased.
_OWNER_MAP: dict[str, str] = {
    "AGENTS.md": "agents-md",
    "QWEN.md": "qwen-md",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_rel_path(value: str) -> str:
    """Normalise a workspace-relative path to a forward-slash, no-leading-slash string."""
    return value.strip().replace("\\", "/").strip("/")


def _is_excluded(
    path: Path,
    target_root: Path,
    excluded_prefixes: list[str],
) -> bool:
    """Return True if *path* (a file or directory) should be skipped.

    Reasons to skip:
    - Any path component is in SKIP_DIR_NAMES (.git, node_modules).
    - The workspace-relative path matches or starts with an excluded prefix.
    """
    try:
        rel_parts = path.relative_to(target_root).parts
    except ValueError:
        return True  # outside target_root — skip

    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return True

    rel_posix = "/".join(rel_parts)
    for prefix in excluded_prefixes:
        prefix = _normalize_rel_path(prefix)
        if rel_posix == prefix or rel_posix.startswith(prefix + "/"):
            return True

    return False


def _is_nested_repo_dir(directory: Path, target_root: Path) -> bool:
    """Return True if *directory* is a nested git repository.

    A nested repo is any directory that contains a ``.git`` entry and is NOT
    the workspace root itself.  Such directories must not receive guidance
    files.
    """
    if directory.resolve() == target_root.resolve():
        return False
    return (directory / ".git").exists()


def _walk_claude_mds(
    target_root: Path,
    excluded_prefixes: list[str],
) -> list[Path]:
    """Recursively find all CLAUDE.md files to mirror.

    Yields absolute paths, sorted for deterministic output.  Skips:
    - Directories whose name is in SKIP_DIR_NAMES.
    - Directories that match an excluded_prefix (the CLAUDE.md inside is also skipped).
    - Directories that are nested git repos (contain .git and are not target_root).
    """
    found: list[Path] = []

    def _recurse(current_dir: Path) -> None:
        # Check skip conditions for current_dir (not for target_root itself)
        if current_dir != target_root:
            if _is_excluded(current_dir, target_root, excluded_prefixes):
                return
            if _is_nested_repo_dir(current_dir, target_root):
                return

        try:
            entries = sorted(current_dir.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                _recurse(entry)
            elif entry.is_file() and entry.name == "CLAUDE.md":
                # Double-check the file itself is not excluded
                if not _is_excluded(entry, target_root, excluded_prefixes):
                    found.append(entry)

    _recurse(target_root)
    return sorted(found)


def _compose_guidance_content(
    target_root: Path,
    claude_md_path: Path,
    guidance_filename: str,
    banner_label: str,
) -> str:
    """Compose banner + optional root preamble + CLAUDE.md body.

    The banner is produced by ``make_banner`` from mirror.py (imported above)
    so the output is byte-identical to mirror.py for the same source.

    The root preamble is prepended only when ``claude_md_path`` is the
    workspace-root CLAUDE.md (i.e. its parent is target_root).
    """
    source_rel = claude_md_path.relative_to(target_root).as_posix()

    # Build a minimal config dict that satisfies make_banner's requirements.
    # make_banner reads: config["banner_label"]  (only this key).
    config: dict[str, str] = {
        "banner_label": banner_label,
        # mirror.py's make_banner also uses SCRIPT_PATH (from mirror.py's module
        # scope) to compute the regen command — no local override needed.
    }

    banner = make_banner(config, source_rel, guidance_filename)

    body = claude_md_path.read_text(encoding="utf-8")

    # Strip leading blank lines from the body (mirrors mirror.py's compose_guidance).
    body_stripped = body.lstrip("\n")

    # Root preamble — only for the workspace-root CLAUDE.md.
    is_root = claude_md_path.parent.resolve() == target_root.resolve()
    preamble = ROOT_PREAMBLE if is_root else ""

    content = banner + preamble + body_stripped
    if not content.endswith("\n"):
        content += "\n"
    return content


def _guidance_owner(guidance_filename: str) -> str:
    """Map a guidance filename to its state-layer owner tag."""
    return _OWNER_MAP.get(guidance_filename, guidance_filename.split(".")[0].lower())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_guidance(
    target_root: Path | str,
    guidance_filename: str,
    *,
    check: bool,
    excluded_paths: list[str],
    banner_label: str = "",
) -> list[dict[str, str]]:
    """Render guidance files beside every CLAUDE.md in *target_root*.

    Parameters
    ----------
    target_root:
        The workspace root to walk.  All paths in returned records are relative
        to this directory.
    guidance_filename:
        The sibling filename to create beside each CLAUDE.md
        (e.g. ``"AGENTS.md"`` for codex/kimi, ``"QWEN.md"`` for qwen).
    check:
        If True, run in read-only staleness-check mode: no files are written;
        ``write_if_changed`` returns ``"stale"`` for missing or drifted files.
    excluded_paths:
        List of workspace-root-relative path prefixes (posix) that should be
        skipped when walking for CLAUDE.md files.
    banner_label:
        Short human label naming the consuming worker, interpolated into the
        DO-NOT-EDIT banner by ``make_banner`` (e.g. ``"the Codex CLI worker"``).
        When empty the banner will render with an empty label — callers SHOULD
        always supply this.

    Returns
    -------
    list[dict[str, str]]
        One record per guidance file managed by this call:
            ``{"path": "<workspace-relative posix>",
               "kind": "guidance",
               "owner": "<agents-md|qwen-md|...>"}``
        Records are sorted by path for deterministic state-layer writes.
    """
    target_root = Path(target_root).resolve()
    excluded_prefixes = [_normalize_rel_path(p) for p in excluded_paths]
    owner_tag = _guidance_owner(guidance_filename)

    claude_mds = _walk_claude_mds(target_root, excluded_prefixes)

    managed: list[dict[str, str]] = []
    stale_paths: list[str] = []

    for claude_md in claude_mds:
        content = _compose_guidance_content(
            target_root, claude_md, guidance_filename, banner_label
        )
        guidance_path = claude_md.with_name(guidance_filename)
        status = write_if_changed(guidance_path, content, check=check)

        rel_posix = guidance_path.relative_to(target_root).as_posix()
        managed.append({
            "path": rel_posix,
            "kind": "guidance",
            "owner": owner_tag,
        })

        if check and status == "stale":
            stale_paths.append(rel_posix)

    managed.sort(key=lambda r: r["path"])

    if check and stale_paths:
        for p in stale_paths:
            print(f"stale: {p} is missing or differs from its CLAUDE.md source")

    return managed
