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
    _instruction_block_valid,
    _jdel,
    _jget,
    _jset,
)
from .content import _is_ours
from .fsio import write_file
from .state import known_claims, known_files


def _instruction_fence(path: Path, rel: str) -> bool:
    """Validate the one root instruction section before any file changes."""
    if not path.is_file():
        return False
    text = path.read_bytes().decode("utf-8")
    return _instruction_block_valid(text, rel, path)


def apply(target: Path, files: dict[str, str], claims: list[dict], state: dict,
          dry_run: bool, protect: frozenset[str] = frozenset(),
          extra_files: set[str] | None = None,
          extra_claims: set[str] | None = None) -> dict:
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
    collisions, adopted, adopted_sections = [], [], []
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
        cid = _claim_id(claim["path"], claim["key"], claim.get("label"))
        path = target / claim["path"]
        if not path.is_file():
            continue
        guidance_section = (claim["path"] in GUIDANCE_NAMES
                            and claim["fmt"] == "text"
                            and claim["comment"] == "<!--"
                            and claim["key"] is None)
        instruction = guidance_section and not claim.get("label")
        # A rule section is the installer's own too: its label names the rule.
        rule_section = guidance_section and str(claim.get("label") or "").startswith("rule ")
        if instruction:
            valid_fence = _instruction_fence(path, claim["path"])
            if (valid_fence and cid not in ours_claims
                    and not _is_ours(target, claim["path"])):
                adopted_sections.append(claim["path"])
        if cid in ours_claims:
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
            start, _ = _fence(claim["comment"], claim.get("label"))
            text = path.read_text(encoding="utf-8")
            if claim["comment"] == "#":
                # whole line only: `# rbtv:start` prefixes `# rbtv:start <label>`
                present = start + "\n" in text or text.endswith(start)
            else:
                present = start in text
            if (present
                    and not instruction and not rule_section
                    and not _is_ours(target, claim["path"])):
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
                f"`rbtv install configure --guidance {BASIS_NONE}` to leave both root "
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
    stale = sorted((ours_files | set(extra_files or ())) - set(files) - protect)
    released = [rel for rel in stale
                if (target / rel).is_file() and not _is_ours(target, rel)]
    stale_files = [rel for rel in stale if rel not in released]
    planned_claims = {_claim_id(c["path"], c["key"], c.get("label"))
                      for c in claims}
    stale_claims = sorted((ours_claims | set(extra_claims or ())) - planned_claims)
    for cid in stale_claims:
        rel, _, key = cid.partition("::")
        if rel in GUIDANCE_NAMES and key == "#block":
            _instruction_fence(target / rel, rel)
    file_write = sorted(rel for rel, body in files.items()
                        if not (target / rel).is_file()
                        or not _same(target / rel, body))
    file_unchanged = sorted(set(files) - set(file_write))
    file_delete = sorted(rel for rel in stale_files
                         if (target / rel).is_file())
    shared_rendered, shared_bases = _render_shared(
        target, claims, stale_claims, files, set(file_delete))
    shared_write, shared_delete, shared_unchanged = _shared_delta(
        shared_rendered, shared_bases)

    if dry_run:
        return {"written": [], "skipped": file_unchanged, "deleted": [],
                "shared": sorted(planned_claims), "adopted": adopted,
                "adopted_sections": sorted(adopted_sections),
                "released": released,
                "shared_removed": stale_claims, "dry_run": True,
                "planned_changes": {
                    "write_files": file_write,
                    "delete_files": file_delete,
                    "unchanged_files": file_unchanged,
                    "write_shared_files": shared_write,
                    "delete_shared_files": shared_delete,
                    "unchanged_shared_files": shared_unchanged}}

    written, skipped = [], []
    for rel in sorted(files):
        path, body = target / rel, files[rel]
        # D15 — a copied skill folder may carry a binary asset, so a planned
        # file is bytes OR text; everything else on this path is text.
        if path.is_file() and _same(path, body):
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        write_file(path, body, newline="\n")
        written.append(rel)

    deleted = []
    for rel in stale_files:
        path = target / rel
        if path.is_file():
            path.unlink()
            deleted.append(rel)
        _prune(target, path.parent)

    _apply_shared(target, shared_rendered)
    return {"written": written, "skipped": skipped, "deleted": deleted,
            "shared": sorted(planned_claims), "shared_removed": stale_claims,
            "shared_written": shared_write, "shared_deleted": shared_delete,
            "shared_skipped": shared_unchanged,
            "adopted": adopted, "adopted_sections": sorted(adopted_sections),
            "released": released, "dry_run": False}


def _same(path: Path, body: str | bytes) -> bool:
    """Is the file already exactly the bytes we would write? Text is written
    with newline="\\n" (no translation), so its bytes are body.encode("utf-8");
    comparing decoded text would fold CRLF and never match a CRLF source."""
    want = body if isinstance(body, bytes) else body.encode("utf-8")
    try:
        return path.read_bytes() == want
    except OSError:
        return False


def _render_shared(target: Path, claims: list[dict], stale_claims: list[str],
                   files: dict[str, str | bytes], deleted_files: set[str]
                   ) -> tuple[dict[str, str], dict[str, str | None]]:
    """Render over the post-file-plan body, as real apply would see it."""
    touched: dict[str, dict] = {}
    for claim in claims:
        touched.setdefault(claim["path"], {"fmt": claim["fmt"],
                                           "comment": claim.get("comment", "#"),
                                           "set": [], "del": []})
        touched[claim["path"]]["set"].append(claim)
    for cid in stale_claims:
        rel, _, keypart = cid.partition("::")
        block = keypart.startswith("#block")
        comment = "<!--" if rel.endswith(".md") else "#"
        entry = touched.setdefault(
            rel, {"fmt": "text" if block else "json", "comment": comment,
                  "set": [], "del": []})
        entry["del"].append(
            {"label": keypart[len("#block:"):] or None} if block
            else {"key": json.loads(keypart)})

    rendered: dict[str, str] = {}
    bases: dict[str, str | None] = {}
    for rel, work in touched.items():
        path = target / rel
        guidance = Path(rel).name in GUIDANCE_NAMES
        if rel in files:
            planned = files[rel]
            base = planned.decode("utf-8") if isinstance(planned, bytes) else planned
            on_disk = base
        elif rel in deleted_files:
            base = None
            on_disk = None
        else:
            on_disk = path.read_bytes().decode("utf-8") if path.is_file() else None
            base = (on_disk if guidance or on_disk is None else
                    path.read_text(encoding="utf-8"))
        bases[rel] = on_disk
        if work["fmt"] == "json":
            doc = json.loads(base or "{}")
            for gone in work["del"]:
                _jdel(doc, gone["key"])
            for claim in work["set"]:
                _jset(doc, claim["key"], claim["value"])
            text = json.dumps(doc, indent=2, sort_keys=True) + "\n" if doc else ""
        else:
            text = base or ""
            keep_outside = guidance and work["comment"] == "<!--"
            for gone in work["del"]:
                text = _block_del(text, work["comment"],
                                  preserve_outside=keep_outside,
                                  label=gone["label"])
            for claim in work["set"]:
                text = _block_set(text, claim["value"], work["comment"],
                                  preserve_outside=keep_outside,
                                  label=claim.get("label"),
                                  first=claim.get("first", False))
            if not text.strip() and not guidance:
                text = ""
        rendered[rel] = text
    return rendered, bases


def _shared_delta(rendered: dict[str, str], bases: dict[str, str | None]
                  ) -> tuple[list[str], list[str], list[str]]:
    """Sort the rendered shared files into the receipt's lists: to write, to
    delete, or an EXISTING file already up to date. A rendering that came up
    empty over an absent base is no remaining shared action — post-file-plan,
    the file plan itself already removes that file and no section survives —
    so it belongs to no list: reporting it "unchanged" would put the same
    name in one receipt under both deleted and unchanged."""
    write, delete, unchanged = [], [], []
    for rel, text in rendered.items():
        base = bases[rel]
        if text:
            (unchanged if base is not None and base == text else write).append(rel)
        elif base is not None:
            delete.append(rel)
    return sorted(write), sorted(delete), sorted(unchanged)


def _apply_shared(target: Path, rendered: dict[str, str]) -> None:
    """Write only shared bodies that differ, using the preview's rendering."""
    for rel, text in rendered.items():
        path = target / rel
        if not text:
            if path.is_file():
                path.unlink()
            _prune(target, path.parent)
        elif not (path.is_file() and _same(path, text)):
            path.parent.mkdir(parents=True, exist_ok=True)
            write_file(path, text, newline="\n")


def _clean_bases(target: Path, report: dict, dry_run: bool) -> None:
    """Write back the bases whose stale GENERATED banner we removed (D13, the
    empty-target flip). Never booked — a basis on the book is a basis on some
    later uninstall's delete set."""
    debanner = report.pop("_debanner", None) or {}
    if not dry_run:
        for rel, text in debanner.items():
            write_file(target / rel, text, newline="\n")
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
