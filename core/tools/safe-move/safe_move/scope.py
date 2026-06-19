"""Scope layer: resolve search root and walk files with tagging."""

from __future__ import annotations

import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ScopeError(Exception):
    """Raised when scope resolution or the walk cannot proceed."""


@dataclass(frozen=True, slots=True)
class WalkedFile:
    """One text file discovered under the scope root."""

    path: str  # relative to scope root, POSIX separators
    abs_path: Path
    read_only: bool
    generated: bool
    boundary: Path | None  # top level of a different git repo, when applicable


@dataclass(frozen=True, slots=True)
class WalkWarning:
    """A non-fatal issue encountered while walking."""

    kind: str
    message: str
    file: str | None = None


# Directories that are part of VCS, dependency, or build tooling.
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".eggs",
        "dist",
        "build",
        "target",
    }
)

# Generated dependency lockfiles that should not be patched.
LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "cargo.lock",
        "poetry.lock",
        "pipfile.lock",
        "uv.lock",
        "composer.lock",
        "gemfile.lock",
        "mix.lock",
        "go.sum",
        "go.mod",
    }
)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def git_toplevel(cwd: Path) -> Path | None:
    # A concurrent move can delete ``cwd`` (e.g. the folder being moved) between
    # an earlier existence check and this probe; passing a non-existent directory
    # as the subprocess ``cwd`` raises ``NotADirectoryError``/``FileNotFoundError``
    # (Windows WinError 267). Treat an absent ``cwd`` as "no repository" rather
    # than letting a raw traceback escape the read-only consult.
    cwd = Path(cwd)
    if not cwd.is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except OSError:
        # ``cwd`` vanished between the is_dir() check and process spawn (a TOCTOU
        # race with a concurrent move). Only swallow when that is what happened,
        # so a genuinely missing ``git`` executable still surfaces as before.
        if not cwd.is_dir():
            return None
        raise
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _match_glob(relpath: str, pattern: str) -> bool:
    """Return True if ``pattern`` matches ``relpath`` or any ancestor directory."""
    if fnmatch.fnmatch(relpath, pattern):
        return True
    parts = relpath.split("/")
    for i in range(1, len(parts)):
        ancestor = "/".join(parts[:i])
        if fnmatch.fnmatch(ancestor, pattern):
            return True
    return False


def _matches_any(relpath: str, patterns: Iterable[str]) -> bool:
    return any(_match_glob(relpath, pat) for pat in patterns)


def is_binary(path: Path, chunk_size: int = 8192) -> bool:
    """Return True if ``path`` appears to be a binary file."""
    with path.open("rb") as fh:
        chunk = fh.read(chunk_size)
    return b"\x00" in chunk


def read_text_safe(path: Path) -> str | None:
    """Read ``path`` as UTF-8 text, or return ``None`` when it cannot be read.

    Returns ``None`` for a non-UTF-8 / undecodable file — a binary file that
    slipped past the walk-time NUL-byte filter (e.g. a NUL-free PDF) or a
    genuinely non-UTF-8 text file (e.g. Windows-1252) — and for any OS read
    error. Callers treat ``None`` as "not a readable UTF-8 text file" and skip
    it as a reference source, so a single non-UTF-8 file can no longer crash a
    ``consult``/``act`` run. (``UnicodeDecodeError`` is a ``ValueError``, not an
    ``OSError``, so it must be caught explicitly.)
    """
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


#: Sentinel distinguishing "not cached" from a cached ``None`` (undecodable).
_MISSING = object()


class ContentProvider:
    """Read each scoped file once and cache its text by absolute path.

    A single provider shared across the non-code matchers and the code matcher
    guarantees the haystack is read once per run (not re-read per sub-target on
    a folder move). Undecodable files are cached as ``None`` and their
    scope-relative paths recorded in ``undecodable`` so the caller can surface a
    single aggregated warning instead of per-file noise.
    """

    __slots__ = ("_cache", "undecodable")

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}
        self.undecodable: list[str] = []

    def get(self, wf: WalkedFile) -> str | None:
        """Return ``wf``'s UTF-8 text (read once and cached), or ``None``."""
        key = wf.abs_path.as_posix()
        cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return cached
        content = read_text_safe(wf.abs_path)
        self._cache[key] = content
        if content is None:
            self.undecodable.append(wf.path)
        return content


def resolve_scope_root(
    old: str | Path, scope_root_override: str | Path | None = None
) -> Path:
    """Resolve the search root for a move operation.

    The root is ``scope_root_override`` when provided, otherwise the git top
    level of ``old``. Raises ``ScopeError`` with a clear message when neither
    resolves to a usable directory.
    """
    if scope_root_override is not None:
        root = Path(scope_root_override).expanduser().resolve()
        if not root.is_dir():
            raise ScopeError(
                f"--scope-root does not exist or is not a directory: {scope_root_override}"
            )
        return root

    old_path = Path(old).expanduser().resolve()
    if not old_path.exists():
        raise ScopeError(f"old path does not exist: {old}")

    cwd = old_path if old_path.is_dir() else old_path.parent
    top = git_toplevel(cwd)
    if top is None:
        raise ScopeError(
            f"old path is not inside a git repository: {old}\n"
            "Use --scope-root to specify a search root."
        )
    return top


def walk_scope(
    scope_root: str | Path,
    *,
    exclude: Iterable[str] = (),
    read_only: Iterable[str] = (),
    generated: Iterable[str] = (),
    include_archive: bool = False,
    descend_nested_repos: bool = False,
    warnings: list[WalkWarning] | None = None,
) -> Iterable[WalkedFile]:
    """Yield text files under ``scope_root`` with scope tags attached.

    Skips ``.git``, dependency/build directories, binary files, and generated
    lockfiles. Honors ``--exclude`` unless ``include_archive`` is set.

    A nested git repository (a sub-directory that is its own git top level) is
    NOT descended into by default: its files are a separate project with their
    own history and references, and reading them is a surprising, often unsafe
    default (sensitive sibling repos, slow scans). Pass
    ``descend_nested_repos=True`` to walk them as before, tagging each contained
    file with the foreign top-level path as its ``boundary`` so the classifier
    surfaces (never auto-applies) cross-repo references.

    Tags ``read_only`` and ``generated`` matches for later classification.

    Non-fatal issues (permission denied, unreadable files) are appended to
    ``warnings`` rather than crashing the walk.
    """
    root = Path(scope_root).expanduser().resolve()
    if not root.is_dir():
        raise ScopeError(f"scope root is not a directory: {scope_root}")

    exclude_patterns = list(exclude)
    read_only_patterns = list(read_only)
    generated_patterns = list(generated)
    if warnings is None:
        warnings = []

    return _walk_dir(
        root,
        root,
        None,
        exclude_patterns,
        read_only_patterns,
        generated_patterns,
        include_archive,
        descend_nested_repos,
        warnings,
    )


def iter_subtree_text_files(
    subtree: str | Path,
    scope_root: str | Path,
    *,
    skip_subtrees: Iterable[Path] = (),
) -> Iterable[WalkedFile]:
    """Yield text files under ``subtree`` ignoring ``SKIP_DIR_NAMES`` (except ``.git``).

    Used to scan a MOVED folder's OWN files for self-references: a project's
    ``build/`` / ``dist/`` / ``target/`` records are hand-authored content being
    relocated, not regenerated artifacts, so the skip-dir heuristic (correct for
    the broad scope) must not hide them from the self-reference sweep. Still
    skips ``.git`` internals, the nested-repo subtrees in ``skip_subtrees``,
    binaries, and generated lockfiles. Paths are relative to ``scope_root``;
    scope tags are neutral (``read_only`` / ``generated`` / ``boundary`` unset) —
    the sweep that consumes these only surfaces matches, never auto-applies.
    """
    root = Path(scope_root).expanduser().resolve()
    base = Path(subtree).expanduser().resolve()
    skip = {Path(p).resolve() for p in skip_subtrees}
    for path in sorted(base.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if any(path == s or s in path.parents for s in skip):
            continue
        if path.name.lower() in LOCKFILE_NAMES:
            continue
        try:
            if is_binary(path):
                continue
        except OSError:
            continue
        yield WalkedFile(
            path=_rel(path, root),
            abs_path=path,
            read_only=False,
            generated=False,
            boundary=None,
        )


def _walk_dir(
    dirpath: Path,
    root: Path,
    boundary: Path | None,
    exclude_patterns: list[str],
    read_only_patterns: list[str],
    generated_patterns: list[str],
    include_archive: bool,
    descend_nested_repos: bool,
    warnings: list[WalkWarning],
) -> Iterable[WalkedFile]:
    try:
        entries = sorted(os.scandir(dirpath), key=lambda e: e.name)
    except OSError as exc:
        warnings.append(
            WalkWarning(
                "unreadable",
                f"cannot list directory: {exc}",
                file=_rel(dirpath, root),
            )
        )
        return

    for entry in entries:
        # Do not follow symlinks: they may point outside the scope or into
        # another repository. Skip them without crashing.
        if entry.is_symlink():
            continue

        abspath = Path(entry.path)
        relpath = _rel(abspath, root)

        if entry.is_dir(follow_symlinks=False):
            name = entry.name
            if name == ".git":
                continue
            if name in SKIP_DIR_NAMES:
                continue
            if _matches_any(relpath, exclude_patterns) and not include_archive:
                continue

            dir_boundary = boundary
            if (abspath / ".git").exists():
                top = git_toplevel(abspath)
                if top is not None and top != root:
                    # A nested git repository. By default it is a walk boundary:
                    # do NOT descend into a separate repo's files. Only descend
                    # (tagging the foreign top level) when explicitly opted in.
                    if not descend_nested_repos:
                        continue
                    dir_boundary = top

            yield from _walk_dir(
                abspath,
                root,
                dir_boundary,
                exclude_patterns,
                read_only_patterns,
                generated_patterns,
                include_archive,
                descend_nested_repos,
                warnings,
            )
        else:
            if entry.name.lower() in LOCKFILE_NAMES:
                continue
            if _matches_any(relpath, exclude_patterns) and not include_archive:
                continue

            try:
                binary = is_binary(abspath)
            except OSError as exc:
                warnings.append(
                    WalkWarning(
                        "unreadable",
                        f"cannot read file: {exc}",
                        file=relpath,
                    )
                )
                continue
            if binary:
                continue

            yield WalkedFile(
                path=relpath,
                abs_path=abspath,
                read_only=_matches_any(relpath, read_only_patterns),
                generated=_matches_any(relpath, generated_patterns),
                boundary=boundary,
            )
