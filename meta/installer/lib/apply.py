"""Writing the planned set to disk, and removing exactly what the book
records.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery import Refuse

from .constants import BASIS_NONE, FENCE_ID, GUIDANCE_NAMES
from .claims import (
    _block_del,
    _block_set,
    _claim_id,
    _fence,
    _jdel,
    _jget,
    _jset,
)
from .content import _is_ours
from .state import known_claims, known_files


def apply(target: Path, files: dict[str, str], claims: list[dict], state: dict,
          dry_run: bool, protect: frozenset[str] = frozenset()) -> dict:
    """Write the planned set and remove what the previous book held but the plan
    no longer does. Every collision (D6) refuses BEFORE the first write.

    `protect` names paths that MUST NOT be deleted however the book reads them.
    It exists for the D13 basis flip: yesterday's generated mirror can be
    today's hand-authored basis under the same name, and the book alone cannot
    tell those apart — "never written" has to mean "never removed" too."""
    ours_files = known_files(state)
    ours_claims = known_claims(state)

    # D12/D13 ADOPTION — a planned path that exists and is not in our book, but
    # whose own head PROVES a tool wrote it (our ownership marker, or a
    # generated-mirror banner) is taken over and booked. The collision refusal
    # exists to protect HAND-AUTHORED files; a file that says on its face it was
    # generated is not one. Without that proof it still refuses.
    collisions, adopted = [], []
    for rel in files:
        if rel in ours_files or not (target / rel).exists():
            continue
        if _is_ours(target, rel):
            adopted.append(rel)
            continue
        collisions.append(rel)
    collisions.sort()
    adopted.sort()
    # Key-level collisions inside shared files (D12).
    for claim in claims:
        cid = _claim_id(claim["path"], claim["key"])
        if cid in ours_claims:
            continue
        path = target / claim["path"]
        if not path.is_file():
            continue
        if claim["fmt"] == "json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            except ValueError as exc:
                raise Refuse(
                    "shared-file-unparseable",
                    f"{claim['path']} exists but is not readable JSON ({exc}) "
                    "— refusing before any write rather than replacing a file "
                    "this installer did not create",
                    str(path)) from exc
            if _jget(doc, claim["key"])[1]:
                collisions.append(f"{claim['path']}::"
                                  + ".".join(claim["key"]))
        else:
            start, _ = _fence(claim["comment"])
            if start in path.read_text(encoding="utf-8"):
                collisions.append(f"{claim['path']}::{FENCE_ID}-block")
    if collisions:
        collisions = sorted(set(collisions))
        # D13 — a root guidance file collides for its own reason, and the
        # generic "move or remove it" advice would tell the user to delete
        # hand-authored guidance. Say what this file actually is instead.
        mirrors = [rel for rel in collisions
                   if rel.rsplit("/", 1)[-1] in GUIDANCE_NAMES]
        if mirrors:
            raise Refuse(
                "guidance-mirror-collision",
                f"{', '.join(mirrors)} already exists and "
                "this installer did not write it — it is either hand-authored "
                "guidance or a mirror rendered by another tool (install.py's "
                "`model_mirror` renders one beside every CLAUDE.md). This run "
                f"would generate it from the basis. DO NOT delete it: either "
                f"`rbtv install set artifact {BASIS_NONE}` to leave both root "
                "guidance files alone, or point the basis at the file you "
                "author and retire the other tool's copy of the one it "
                "generates. "
                "Nothing was written",
                mirrors[0])
        raise Refuse(
            "collision",
            "the install root already carries content this run would write and "
            "this installer did not write it (the old installer's, or "
            "hand-placed): " + ", ".join(collisions) + " — refusing before any "
            "write; move or remove it, or narrow --component/--harness",
            collisions[0])

    # D12 RELEASE — a booked file whose marker is gone was taken over by a
    # human between runs. It leaves the book (`_rebook` recomputes from the
    # plan) but is NEVER deleted; the caller reports it instead.
    stale = sorted(ours_files - set(files) - protect)
    released = [rel for rel in stale
                if (target / rel).is_file() and not _is_ours(target, rel)]
    stale_files = [rel for rel in stale if rel not in released]
    planned_claims = {_claim_id(c["path"], c["key"]) for c in claims}
    stale_claims = sorted(ours_claims - planned_claims)

    if dry_run:
        return {"written": [], "skipped": sorted(files), "deleted": stale_files,
                "shared": sorted(planned_claims), "adopted": adopted,
                "released": released,
                "shared_removed": stale_claims, "dry_run": True}

    written, skipped = [], []
    for rel in sorted(files):
        path, body = target / rel, files[rel]
        # D15 — a copied skill folder may carry a binary asset, so a planned
        # file is bytes OR text; everything else on this path is text.
        if path.is_file() and _same(path, body):
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8", newline="\n")
        written.append(rel)

    deleted = []
    for rel in stale_files:
        path = target / rel
        if path.is_file():
            path.unlink()
            deleted.append(rel)
        _prune(target, path.parent)

    _apply_shared(target, claims, stale_claims)
    return {"written": written, "skipped": skipped, "deleted": deleted,
            "shared": sorted(planned_claims), "shared_removed": stale_claims,
            "adopted": adopted, "released": released, "dry_run": False}


def _same(path: Path, body: str | bytes) -> bool:
    """Is the file already exactly this content? Bytes compare as bytes; text
    compares as text (an unreadable file is simply not equal)."""
    try:
        return (path.read_bytes() == body if isinstance(body, bytes)
                else path.read_text(encoding="utf-8") == body)
    except (OSError, UnicodeDecodeError):
        return False


def _apply_shared(target: Path, claims: list[dict],
                  stale_claims: list[str]) -> None:
    """Set every planned claim and drop every stale one — key by key, block by
    block (D12). A shared file is deleted only when NOTHING is left in it."""
    touched: dict[str, dict] = {}
    for claim in claims:
        touched.setdefault(claim["path"], {"fmt": claim["fmt"],
                                           "comment": claim.get("comment", "#"),
                                           "set": [], "del": []})
        touched[claim["path"]]["set"].append(claim)
    for cid in stale_claims:
        rel, _, keypart = cid.partition("::")
        fmt = "json" if keypart != "#block" else "text"
        entry = touched.setdefault(rel, {"fmt": fmt, "comment": "#",
                                         "set": [], "del": []})
        entry["del"].append(None if keypart == "#block" else json.loads(keypart))

    for rel, work in touched.items():
        path = target / rel
        if work["fmt"] == "json":
            doc = {}
            if path.is_file():
                doc = json.loads(path.read_text(encoding="utf-8") or "{}")
            for key in work["del"]:
                _jdel(doc, key)
            for claim in work["set"]:
                _jset(doc, claim["key"], claim["value"])
            text = json.dumps(doc, indent=2, sort_keys=True) + "\n" if doc else ""
        else:
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            if work["del"]:
                text = _block_del(text, work["comment"])
            for claim in work["set"]:
                text = _block_set(text, claim["value"], work["comment"])
            if not text.strip():
                text = ""
        if not text:
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
            continue
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def _clean_bases(target: Path, report: dict, dry_run: bool) -> None:
    """Write back the bases whose stale GENERATED banner we removed (D13, the
    empty-target flip). Never booked — a basis on the book is a basis on some
    later uninstall's delete set."""
    debanner = report.pop("_debanner", None) or {}
    if not dry_run:
        for rel, text in debanner.items():
            (target / rel).write_text(text, encoding="utf-8", newline="\n")
    report["guidance_debannered"] = sorted(debanner)


def _prune(target: Path, directory: Path) -> None:
    """Remove directories our deletion emptied — never above the target."""
    target = target.resolve()
    current = directory.resolve()
    while current != target and target in current.parents:
        try:
            next(current.iterdir())
            return
        except StopIteration:
            current.rmdir()
        except OSError:
            return
        current = current.parent
