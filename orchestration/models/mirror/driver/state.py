"""state.py — the mirror driver's state layer over ``rbtv.json``.

This module owns the ``model_mirror`` block of a workspace's ``rbtv.json`` and the
ref-counted deletion logic that an ``--uninstall`` performs.  It is the
judgment-dense core of the driver: every other module (guidance/library/config)
only *renders* files and returns managed-file records; this module decides what
the persisted state should be and — on deselection — what may be safely deleted.

Responsibilities
----------------
1. Read ``rbtv.json`` and return the full document (every installer-owned key is
   preserved verbatim; only ``model_mirror`` is ever mutated).
2. Merge a freshly-rendered managed-file set into the ``model_mirror`` block,
   de-duping by ``path`` and writing the whole document back with all other keys
   intact and in their original order.
3. Drive ref-counted deletion: given a deselected package and the set of packages
   that remain elected, decide which managed-file records to remove —
     - records owned by the deselected package's config dir (``owner == package``),
     - a guidance-filename group (``agents-md`` / ``qwen-md``) ONLY when no
       remaining elected package still needs that group,
     - the ``shared`` ``.agents/`` library ONLY when no worker remains at all,
   then delete the corresponding files on disk — never touching a guidance file
   that lacks the engine's DO-NOT-EDIT banner (banner-guard).

Design constraints
------------------
- The driver writes ONLY the ``model_mirror`` key of ``rbtv.json``.  Every other
  key (``rbtv_version``, ``model_packages``, ``installed_files``, …) is read,
  carried through unchanged, and written back byte-for-byte from the parsed JSON.
- Source-agnostic: this module reads NO manifest.  Package→guidance-filename
  facts are passed in by the orchestrator (``__init__.py``), never read from a
  manifest or ``mirror-config.yaml``.
- ``rbtv.json`` lives at ``{target_root}/rbtv.json`` — the state file is resolved
  per target root, so a scratch workspace gets its own state file.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_FILENAME = "rbtv.json"
MIRROR_KEY = "model_mirror"

#: The banner sentinel that marks a guidance file as engine-generated.  A
#: guidance file whose head lacks this string is hand-authored and is NEVER
#: deleted by uninstall (banner-guard).  Matches mirror.py's run_uninstall guard.
BANNER_SENTINEL = "AUTO-GENERATED MIRROR — DO NOT EDIT"

#: How many leading bytes of a guidance file are scanned for the banner.
_BANNER_SCAN_BYTES = 200

#: Owner tags that denote a guidance-filename group (ref-counted by filename).
_GUIDANCE_GROUP_OWNERS = frozenset({"agents-md", "qwen-md"})

#: The owner tag for the shared ``.agents/`` library.
_SHARED_OWNER = "shared"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _state_path(target_root: Path) -> Path:
    return target_root / STATE_FILENAME


def _normalize_rel_path(value: str) -> str:
    """Normalise a workspace-relative path to forward-slash, no leading slash."""
    return value.strip().replace("\\", "/").strip("/")


# ---------------------------------------------------------------------------
# Read / write of the whole rbtv.json document (model_mirror is the only key
# this module ever mutates; all others are carried through unchanged)
# ---------------------------------------------------------------------------

def read_document(target_root: Path | str) -> dict:
    """Return the full ``rbtv.json`` document as a dict.

    Returns an empty dict if the file does not exist.  Raises ``ValueError`` if
    the file exists but is not valid JSON (a corrupt state file must fail loudly,
    never be silently clobbered).
    """
    target_root = Path(target_root).resolve()
    path = _state_path(target_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc


def read_mirror_block(target_root: Path | str) -> dict:
    """Return the ``model_mirror`` block (or an empty default) from ``rbtv.json``."""
    doc = read_document(target_root)
    block = doc.get(MIRROR_KEY)
    if not isinstance(block, dict):
        return {"excluded_paths": [], "managed_files": [], "last_run": None}
    # Ensure required sub-keys exist for callers.
    block.setdefault("excluded_paths", [])
    block.setdefault("managed_files", [])
    block.setdefault("last_run", None)
    return block


def managed_files(target_root: Path | str) -> list[dict]:
    """Return the recorded ``managed_files`` list (possibly empty)."""
    return list(read_mirror_block(target_root).get("managed_files", []))


def _dedupe_by_path(records: Iterable[dict]) -> dict[str, dict]:
    """Collapse records to a ``{path: record}`` dict (last write wins per path).

    A duplicate ``path`` in the rendered record stream — e.g. a
    ``.claude/skills/<name>/`` and a frontmatter-bearing
    ``.claude/commands/<stem>.md`` that resolve to the same skill name — must
    collapse to a single managed-file row.  This is the same de-dup the
    reference ``codex-mirror.py`` performs.
    """
    by_path: dict[str, dict] = {}
    for rec in records:
        by_path[rec["path"]] = rec
    return by_path


def write_mirror_block(
    target_root: Path | str,
    *,
    managed: Iterable[dict],
    excluded_paths: list[str],
    check: bool = False,
) -> tuple[bool, list[dict]]:
    """Merge ``managed`` into ``rbtv.json``'s ``model_mirror`` block and write it back.

    Only the ``model_mirror`` key is created/replaced; every other key in the
    document is preserved verbatim and in its original position.

    ``last_run`` is refreshed ONLY when the content (``excluded_paths`` or
    ``managed_files``) actually changed, so a no-op re-run does not churn the
    file (mirrors the reference's content-change detection).

    In ``check`` mode nothing is written; the function still returns the
    would-be managed list and a ``changed`` flag reflecting whether the on-disk
    block differs from what a write would produce.

    Returns ``(changed, managed_files_list)`` where ``managed_files_list`` is the
    de-duped, path-sorted record list that was (or would be) persisted.
    """
    target_root = Path(target_root).resolve()
    path = _state_path(target_root)

    doc = read_document(target_root)

    by_path = _dedupe_by_path(managed)
    ordered_managed = [by_path[p] for p in sorted(by_path)]
    normalized_excluded = [_normalize_rel_path(p) for p in excluded_paths]

    existing_block = doc.get(MIRROR_KEY) if isinstance(doc.get(MIRROR_KEY), dict) else None
    existing_managed = existing_block.get("managed_files") if existing_block else None
    existing_excluded = existing_block.get("excluded_paths") if existing_block else None

    content_changed = (
        existing_block is None
        or existing_managed != ordered_managed
        or existing_excluded != normalized_excluded
    )

    if content_changed:
        last_run = _now_iso()
    else:
        last_run = existing_block.get("last_run") if existing_block else _now_iso()

    new_block = {
        "excluded_paths": normalized_excluded,
        "managed_files": ordered_managed,
        "last_run": last_run,
    }

    if check:
        return content_changed, ordered_managed

    if not content_changed and existing_block is not None:
        # Nothing to write — block is already current.
        return False, ordered_managed

    doc[MIRROR_KEY] = new_block
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return content_changed, ordered_managed


def remove_mirror_block(target_root: Path | str) -> bool:
    """Delete the ``model_mirror`` key entirely (used when the last worker is gone).

    Preserves every other key.  Returns True if the key was present and removed.
    """
    target_root = Path(target_root).resolve()
    path = _state_path(target_root)
    doc = read_document(target_root)
    if MIRROR_KEY not in doc:
        return False
    del doc[MIRROR_KEY]
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def write_managed_records(
    target_root: Path | str,
    records: Iterable[dict],
    *,
    excluded_paths: list[str] | None = None,
) -> None:
    """Persist an explicit managed-file record set into ``model_mirror``.

    Used by uninstall after pruning records: when records remain, write them
    back; when none remain, drop the whole ``model_mirror`` block.  ``last_run``
    is always refreshed here because an uninstall is, by definition, a state
    change.
    """
    target_root = Path(target_root).resolve()
    path = _state_path(target_root)
    doc = read_document(target_root)

    by_path = _dedupe_by_path(records)
    ordered = [by_path[p] for p in sorted(by_path)]

    if excluded_paths is None:
        prior = doc.get(MIRROR_KEY) if isinstance(doc.get(MIRROR_KEY), dict) else {}
        excluded_paths = prior.get("excluded_paths", []) if prior else []

    if not ordered:
        # No managed files remain — remove the block entirely.
        if MIRROR_KEY in doc:
            del doc[MIRROR_KEY]
            path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return

    doc[MIRROR_KEY] = {
        "excluded_paths": [_normalize_rel_path(p) for p in excluded_paths],
        "managed_files": ordered,
        "last_run": _now_iso(),
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Ref-counted deletion planning
# ---------------------------------------------------------------------------

def plan_uninstall_deletions(
    state_records: list[dict],
    deselected: Iterable[str],
    remaining_elected: Iterable[str],
    *,
    owner_to_guidance_group: dict[str, str],
) -> tuple[list[dict], list[dict]]:
    """Split recorded managed files into (to_delete, to_keep) for an uninstall.

    Ref-count rules (design §6 / spec Behavior #7):
      - A record owned by a **deselected package** (config dir; ``owner ==
        package``) is deleted.
      - A **guidance-filename group** record (``owner`` in
        ``{agents-md, qwen-md}``) is deleted ONLY when no remaining elected
        package still maps to that group.
      - A **shared** record (``owner == shared``) is deleted ONLY when no worker
        remains elected at all.

    Parameters
    ----------
    state_records:
        The ``managed_files`` list currently recorded in ``rbtv.json``.
    deselected:
        Package ids being removed in this uninstall (e.g. ``["codex-cli"]``).
    remaining_elected:
        Package ids that stay elected after this uninstall.
    owner_to_guidance_group:
        Mapping from package id → its guidance-group owner tag
        (e.g. ``{"codex-cli": "agents-md", "kimi-code-cli": "agents-md", "qwen-code-cli": "qwen-md"}``).
        Used to decide whether any remaining package still needs a guidance group.

    Returns
    -------
    (to_delete, to_keep):
        Two record lists.  ``to_delete`` records are candidates for on-disk
        removal (the banner-guard is applied at deletion time, not here, because
        only the file head reveals whether a guidance file is hand-authored).
    """
    deselected = set(deselected)
    remaining_elected = set(remaining_elected)

    # Which guidance groups are still required by a remaining elected package?
    required_groups: set[str] = {
        owner_to_guidance_group[pkg]
        for pkg in remaining_elected
        if pkg in owner_to_guidance_group
    }

    any_worker_remains = len(remaining_elected) > 0

    to_delete: list[dict] = []
    to_keep: list[dict] = []

    for rec in state_records:
        owner = rec.get("owner")

        if owner in deselected:
            # Config dir owned by a deselected package — always removed.
            to_delete.append(rec)
        elif owner in _GUIDANCE_GROUP_OWNERS:
            # Guidance-filename group — remove only if no remaining package needs it.
            if owner in required_groups:
                to_keep.append(rec)
            else:
                to_delete.append(rec)
        elif owner == _SHARED_OWNER:
            # Shared .agents/ library — remove only if no worker remains.
            if any_worker_remains:
                to_keep.append(rec)
            else:
                to_delete.append(rec)
        else:
            # Owned by a package that is NOT being deselected (e.g. uninstalling
            # codex while kimi remains, and the record is a kimi config file).
            to_keep.append(rec)

    return to_delete, to_keep


def apply_deletions(
    target_root: Path | str,
    to_delete: list[dict],
) -> tuple[list[str], list[str]]:
    """Delete the on-disk files for ``to_delete`` records, honoring the banner-guard.

    Files are removed longest-path-first so emptied parent directories can be
    pruned bottom-up.  A guidance record (``kind == "guidance"``) whose on-disk
    file lacks the DO-NOT-EDIT banner is SPARED (left untouched) — a hand-authored
    guidance file is never destroyed.

    Returns ``(deleted, spared)`` — lists of workspace-relative paths.

    Containment guard: a record whose ``path`` resolves OUTSIDE ``target_root``
    (e.g. a ``..`` segment in a corrupted/hand-edited ``rbtv.json`` managed_files
    row) is REFUSED — never unlinked — and the escape is reported loudly on
    stderr.  This is irreversible deletion code; a state record must never delete
    a file the workspace does not own.
    """
    target_root = Path(target_root).resolve()

    # Longest path first so child files go before their (now-empty) parent dirs.
    ordered = sorted(to_delete, key=lambda r: len(r["path"]), reverse=True)

    deleted: list[str] = []
    spared: list[str] = []

    for rec in ordered:
        rel = _normalize_rel_path(rec["path"])
        abs_path = (target_root / rel).resolve()

        # Containment guard — refuse any path that escapes the workspace root.
        if not _within(abs_path, target_root):
            print(
                f"refused: managed path {rec['path']!r} resolves outside the "
                f"workspace root ({abs_path}) — NOT deleting",
                file=sys.stderr,
            )
            continue

        if not abs_path.exists() or not abs_path.is_file():
            continue

        if rec.get("kind") == "guidance" and not _has_banner(abs_path):
            # Hand-authored guidance file — banner-guard spares it.
            spared.append(rel)
            continue

        abs_path.unlink()
        deleted.append(rel)
        _prune_empty_dirs(abs_path.parent, stop=target_root)

    return sorted(deleted), sorted(spared)


def _within(path: Path, root: Path) -> bool:
    """True if *path* is *root* itself or lies beneath it (both resolved)."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _has_banner(path: Path) -> bool:
    """True if the file head carries the engine's DO-NOT-EDIT banner sentinel."""
    try:
        head = path.read_text(encoding="utf-8")[:_BANNER_SCAN_BYTES]
    except OSError:
        return False
    return BANNER_SENTINEL in head


def _prune_empty_dirs(directory: Path, *, stop: Path) -> None:
    """Remove ``directory`` and empty ancestors, walking up until ``stop`` (exclusive)."""
    stop = stop.resolve()
    current = directory
    while current.resolve() != stop and current.exists():
        try:
            current.rmdir()  # only succeeds when empty
        except OSError:
            break
        current = current.parent


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """UTC timestamp (``…Z``) for the ``last_run`` field.

    ``last_run`` is state metadata, not part of the byte-identical guidance
    contract — a timestamp here is fine (guidance files themselves carry no
    timestamp, preserving idempotency).
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
