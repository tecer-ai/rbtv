"""The root guidance mirror: one file is authored, the others are generated
from it.
"""
from __future__ import annotations

from pathlib import Path

from discovery import Refuse

from .constants import (
    BASIS_NONE,
    GENERATED_MARKERS,
    GUIDANCE_ALWAYS_EXCLUDED,
    INSTALLER_NAME,
    GUIDANCE_FILE,
    GUIDANCE_NAMES,
    GUIDANCE_SKIP_DIRS,
    STATE_REL,
)
from .claims import _block_del


def resolve_basis(stored, override: str | None) -> str | None:
    """The basis in force for this run: the override when one was passed, else
    what the book holds. Returns None for "no mirror"; refuses anything that is
    neither a known basis name nor `none` — including a hand-edited book."""
    value = override if override is not None else stored
    if value is None or value == BASIS_NONE or value == "":
        return None
    if value not in GUIDANCE_NAMES:
        raise Refuse(
            "guidance-basis-invalid",
            f"guidance basis {value!r} is neither {BASIS_NONE!r} nor one of "
            + " · ".join(GUIDANCE_NAMES)
            + " — refusing before any write (D13)")
    return value


def mirror_targets(harnesses, basis: str) -> list[str]:
    """The guidance filenames this run generates: CMP-12's filename for every
    INSTALLED harness, minus the basis (never written). Harnesses sharing a
    filename collapse to one target; a set that reads only the basis yields
    NOTHING — the claude-only case (D13)."""
    return sorted({GUIDANCE_FILE[h] for h in harnesses if h in GUIDANCE_FILE}
                  - {basis})


def _norm_prefix(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def walk_bases(target: Path, basis: str,
               excludes: list[str] | tuple[str, ...] = ()) -> list[Path]:
    """Every basis file the recursive mirror covers, root first, sorted (D13).

    Skips `GUIDANCE_SKIP_DIRS`, nested git repos, the always-excluded prefixes
    and the workspace's configured excludes. Symlinks are never followed."""
    prefixes = [p for p in
                (_norm_prefix(x) for x in (*excludes, *GUIDANCE_ALWAYS_EXCLUDED))
                if p]

    def excluded(rel: str) -> bool:
        return any(rel == p or rel.startswith(p + "/") for p in prefixes)

    found: list[Path] = []

    def walk(directory: Path) -> None:
        if directory != target:
            rel = directory.relative_to(target).as_posix()
            if (directory.name in GUIDANCE_SKIP_DIRS or excluded(rel)
                    or (directory / ".git").exists()):
                return
        source = directory / basis
        if source.is_file() and not source.is_symlink() \
                and not excluded(source.relative_to(target).as_posix()):
            found.append(source)
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                walk(entry)

    walk(target)
    return found


def strip_generated_banner(body: str) -> tuple[str, bool]:
    """Drop a leading GENERATED-mirror banner from *body*, if it carries one.

    A basis file CAN legitimately be somebody's generated mirror: the ruled
    recovery from a deleted basis is to repoint at the surviving generated file.
    Re-mirroring it verbatim would stack banner on banner on every run — the
    old driver's defect (task 7.623(a)). We strip instead of refusing, so the
    recovery still works and the body stays stable across runs.

    Recognized shapes: this installer's one-comment banner, and mirror.py's
    comment + `> [!danger]` blockquote + `---` rule.
    """
    head = body[:400]
    if not (head.lstrip().startswith("<!--")
            and any(m in head for m in GENERATED_MARKERS)):
        return body, False
    rest = body.split("-->", 1)[1].lstrip("\n") if "-->" in body else ""
    lines = rest.split("\n")
    while lines and (lines[0].startswith(">") or not lines[0].strip()):
        lines.pop(0)
    if lines and lines[0].strip() == "---":
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines), True


def plan_mirror(target: Path, basis: str | None, harnesses,
                excludes: list[str] | tuple[str, ...] = (),
                blocks: dict[str, str] | None = None
                ) -> tuple[dict[str, str], frozenset[str], list[str],
                           list[str], dict[str, str]]:
    """The mirror files the basis implies: one per TARGET NAME (D13, harness-
    keyed) beside EVERY basis file in the tree (recursive).

    Returns `(files, bases, stripped, targets, debanner)` — `bases` is the set
    of basis paths that must never be written or deleted (computed even when
    there is no target, because a basis flip can put a booked name on a
    hand-authored file); `stripped` names the bases whose own generated banner
    was removed before mirroring; `targets` is the resolved filename set;
    `debanner` maps a basis path to its cleaned body (see below).

    `blocks` maps a target filename to its exposure block (D8), placed at the
    ROOT only — nested mirrors are pure per-folder guidance.
    """
    if basis is None:
        return {}, frozenset(), [], [], {}
    blocks = blocks or {}
    targets = mirror_targets(harnesses, basis)
    root_source = target / basis
    if not root_source.is_file():
        if not targets:
            # Nothing would be rendered anyway — a missing basis is not this
            # run's problem, and there is no basis on disk to protect.
            return {}, frozenset(), [], [], {}
        other = " or ".join(n for n in GUIDANCE_NAMES if n != basis)
        raise Refuse(
            "guidance-basis-missing",
            f"the recorded guidance basis {basis!r} does not exist at the "
            "install root, so there is nothing to mirror. Recover with ONE of: "
            f"restore {basis}; or `rbtv install set artifact {other}` to make "
            f"the file you do have the basis; or `rbtv install set artifact "
            f"{BASIS_NONE}` to turn the mirror off. Nothing was written",
            str(root_source))
    files: dict[str, str] = {}
    bases: set[str] = set()
    stripped: list[str] = []
    debanner: dict[str, str] = {}
    for source in walk_bases(target, basis, excludes):
        rel = source.relative_to(target).as_posix()
        bases.add(rel)
        if not targets:
            # No mirror can be rendered under this name any more (every
            # installed harness reads the basis). A file that USED to be our
            # generated mirror is now the file the human authors, so our
            # DO-NOT-EDIT banner and fenced block are stale instructions on
            # their file — clean them off, in place, booking nothing. Guarded
            # by the machine-readable banner: a hand-authored basis has none
            # and is never touched.
            try:
                body = source.read_text(encoding="utf-8").lstrip("\n")
            except (OSError, UnicodeDecodeError):
                continue          # unreadable proves nothing — leave it alone
            cleaned, had_banner = strip_generated_banner(body)
            if had_banner:
                cleaned = _block_del(cleaned, "<!--").lstrip("\n")
                debanner[rel] = (cleaned if cleaned.endswith("\n")
                                 else cleaned + "\n")
            continue
        try:
            body = source.read_text(encoding="utf-8").lstrip("\n")
        except (OSError, UnicodeDecodeError) as exc:
            raise Refuse(
                "guidance-basis-unreadable",
                f"the guidance basis {rel!r} is not readable as UTF-8 text "
                f"({exc}) — a mirror of it would be garbage; refusing before "
                f"any write. Turn the mirror off with `rbtv install set "
                f"artifact {BASIS_NONE}` if this file is not meant to be "
                "guidance, or skip its directory with `rbtv install add "
                "artifact exclude <dir>`",
                str(source)) from exc
        body, stripped_banner = strip_generated_banner(body)
        if stripped_banner:
            stripped.append(rel)
        # A basis that used to be OUR generated file still carries the fenced
        # exposure block — drop it, or every flip would stack another copy.
        body = _block_del(body, "<!--")
        at_root = source.parent == target
        for mirror in targets:
            block = blocks.get(mirror, "") if at_root else ""
            text = (f"<!-- GENERATED by {INSTALLER_NAME} — DO NOT EDIT.\n"
                    f"     {mirror} mirrors {rel}, per the guidance basis "
                    f"recorded in {STATE_REL.as_posix()}.\n"
                    f"     Edit {rel}; re-run the installer to refresh this "
                    "file. -->\n\n") + (block + "\n" if block else "") + body
            mrel = (source.parent / mirror).relative_to(target).as_posix()
            files[mrel] = text if text.endswith("\n") else text + "\n"
    return files, frozenset(bases), sorted(stripped), targets, debanner
