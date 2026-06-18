"""Consult assembly: scan, classify, hash, and emit the frozen JSON envelope."""

from __future__ import annotations

import dataclasses
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from safe_move import classify, code_matcher, hashing, matchers, replace, scope


class ConsultError(Exception):
    """Raised when consult cannot produce a valid result."""


def build_consult_result(
    old: str,
    new: str,
    *,
    scope_root: str | Path | None = None,
    exclude: list[str] | tuple[str, ...] = (),
    read_only: list[str] | tuple[str, ...] = (),
    include_archive: bool = False,
    generated: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return the contract-shaped consult JSON object."""
    root = scope.resolve_scope_root(old, scope_root)
    old_rel = matchers._normalize_old(old, root)
    new_rel = matchers._normalize_old(new, root)

    old_abs = (root / old_rel).resolve()
    if not old_abs.exists():
        raise ConsultError(f"old path does not exist: {old}")

    walk_warnings: list[scope.WalkWarning] = []
    walked = list(
        scope.walk_scope(
            root,
            exclude=exclude,
            read_only=read_only,
            generated=generated,
            include_archive=include_archive,
            warnings=walk_warnings,
        )
    )
    warnings = [_warning_from_walk(w) for w in walk_warnings]
    # One provider shared across the non-code and code scans so each scoped file
    # is read exactly once per run (folder moves no longer re-read per sub-target).
    provider = scope.ContentProvider()
    nested: list[Path] = []
    if old_abs.is_dir():
        references, folder_cascade, candidate_warnings, nested = _build_folder_references(
            old_rel, new_rel, old_abs, root, walked, provider
        )
        _maybe_warn_index_cascade(old_abs, new_rel, root, warnings)
    else:
        operation = classify.classify_operation(old_rel, new_rel)
        references, candidate_warnings = _build_file_references(
            old_rel, new_rel, operation, root, walked, provider
        )
        folder_cascade = None
    warnings.extend(candidate_warnings)
    warnings.extend(_non_utf8_warnings(provider))

    git_method, method_warnings = compute_git_move_method(old_abs, root / new_rel, root)
    warnings.extend(method_warnings)
    if old_abs.is_dir() and nested:
        if git_method == "git mv":
            git_method = "mv"
            warnings.append(
                {
                    "kind": "history-loss",
                    "message": (
                        "falling back to plain mv because the folder contains "
                        "a nested git repository"
                    ),
                    "file": _display_path(old_abs, root),
                    "ref_id": None,
                }
            )
    if old_rel == new_rel:
        warnings.append(
            {
                "kind": "no-op",
                "message": "new path equals old path; no move is needed",
                "file": None,
                "ref_id": None,
            }
        )

    return {
        "git_move_method": git_method,
        "references": references,
        "warnings": warnings,
        "folder_cascade": folder_cascade,
    }


def _reference_record(
    ref_id: str,
    candidate: matchers.Candidate,
    proposed: str,
    ref_class: str,
) -> dict[str, Any]:
    """Return a contract-shaped reference record."""
    return {
        "id": ref_id,
        "file": candidate.file,
        "line": candidate.line,
        "match": candidate.match,
        "context": candidate.context,
        "syntax": candidate.syntax,
        "proposed": proposed,
        "class": ref_class,
        "hash": hashing.compute_hash(candidate),
        "offset": candidate.offset,
    }


def _compute_code_proposed(
    candidate: matchers.Candidate,
    old_rel: str,
    new_rel: str,
    scope_root: Path,
) -> str | None:
    """Compute the operation-aware replacement for a ``code-import`` specifier.

    The new specifier is the path from the referring file's directory to the
    moved target, preserving the original's extension convention and a leading
    ``./`` style when present.
    """
    root = scope_root.expanduser().resolve()
    new_abs = (root / new_rel).resolve()
    ref_dir = (root / Path(candidate.file).parent).resolve()

    try:
        rel = os.path.relpath(new_abs, ref_dir)
    except ValueError:
        return None

    rel_posix = rel.replace(os.sep, "/")
    original = candidate.match

    # Preserve the original's relative-marker style when the recomputed path
    # is in the same package/directory.
    if not rel_posix.startswith("."):
        if original.startswith("./"):
            rel_posix = f"./{rel_posix}"
        elif original.startswith("."):
            # Python-style relative module imports (``.foo``).
            rel_posix = f".{rel_posix}"

    # Preserve the original form's extension convention.  Use a pure POSIX
    # path so Windows does not rewrite ``/`` to ``\``.
    original_suffix = PurePosixPath(original).suffix
    proposed_path = PurePosixPath(rel_posix)
    if not original_suffix and proposed_path.suffix:
        had_dot_slash = rel_posix.startswith("./")
        rel_posix = str(proposed_path.with_suffix(""))
        if had_dot_slash and not rel_posix.startswith("./"):
            rel_posix = f"./{rel_posix}"

    # Directory-via-index imports: if the original specifier resolved through
    # an index file and did not name ``index``, point at the directory.
    resolved_target = candidate.target or ""
    resolved_name = PurePosixPath(resolved_target).name
    if (
        resolved_name
        and PurePosixPath(resolved_name).stem == "index"
        and "index" not in PurePosixPath(original).name
    ):
        rel_posix = str(PurePosixPath(rel_posix).parent)

    return rel_posix


def _candidate_at_new_path(
    candidate: matchers.Candidate,
    old_rel: str,
    new_rel: str,
) -> matchers.Candidate:
    """Return a candidate whose containing file is remapped under ``new_rel``.

    For references that live inside files being moved as part of a folder
    move, replacements must be computed relative to the file's post-move
    location.  The original candidate (used for hashing and the returned
    record) is left unchanged.
    """
    if candidate.file == old_rel:
        return dataclasses.replace(candidate, file=new_rel)
    if candidate.file.startswith(old_rel + "/"):
        new_file = new_rel + candidate.file[len(old_rel):]
        return dataclasses.replace(candidate, file=new_file)
    return candidate


def _build_file_references(
    old_rel: str,
    new_rel: str,
    operation: str,
    scope_root: Path,
    walked: list[scope.WalkedFile],
    provider: scope.ContentProvider,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Discover and classify references for a single-file target."""
    references: list[dict[str, Any]] = []
    candidate_warnings: list[dict[str, Any]] = []
    all_candidates = list(
        matchers.find_candidates(old_rel, walked, scope_root, provider=provider)
    )
    code_candidates, code_warnings = code_matcher.find_code_candidates(
        old_rel, walked, scope_root, provider=provider
    )
    all_candidates.extend(code_candidates)
    all_candidates.sort(key=lambda c: (c.file, c.line, c.match))
    candidate_warnings.extend(code_warnings)

    for index, candidate in enumerate(all_candidates, 1):
        ref_id = f"ref-{index:04d}"
        if candidate.syntax == "code-import":
            proposed = _compute_code_proposed(candidate, old_rel, new_rel, scope_root)
            if candidate.resolves_to == 0:
                # D8 unresolved static import: surface with no proposed rewrite.
                proposed = ""
                ref_class = classify.CLASS_SURFACE
            else:
                ref_class = classify.classify(candidate, operation, scope_root=scope_root)
        else:
            proposed = replace.compute_proposed(
                candidate,
                old_rel,
                new_rel,
                operation,
                scope_root=scope_root,
            )
            ref_class = classify.classify(candidate, operation, scope_root=scope_root)
        if proposed is None or proposed == "":
            proposed = ""
            ref_class = classify.CLASS_SURFACE
        references.append(_reference_record(ref_id, candidate, proposed, ref_class))
        candidate_warnings.extend(_warnings_for_candidate(candidate, ref_id))
    return references, candidate_warnings


def _build_folder_references(
    old_rel: str,
    new_rel: str,
    old_abs: Path,
    scope_root: Path,
    walked: list[scope.WalkedFile],
    provider: scope.ContentProvider,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]], list[Path]]:
    """Discover and classify references for a folder target.

    Builds sub-targets for the folder path itself and every contained file,
    scans the haystack ONCE (non-code + code), matches every sub-target against
    that single scan in memory, deduplicates across sub-targets, and populates
    the folder-cascade block. ast-grep runs once total — not once per sub-target
    — and each scoped file is read once.
    """
    sub_targets: list[tuple[str, str]] = [(old_rel, new_rel)]
    for path in sorted(old_abs.rglob("*")):
        if path.is_file():
            rel = path.relative_to(old_abs).as_posix()
            sub_targets.append((f"{old_rel}/{rel}", f"{new_rel}/{rel}"))

    # Scan the haystack ONCE, then match each sub-target against it in memory.
    sub_olds = [sub_old for sub_old, _ in sub_targets]
    non_code_by_target = matchers.find_candidates_multi(
        sub_olds, walked, scope_root, provider=provider
    )
    code_sites, code_warnings = code_matcher.scan_code_references(
        walked, scope_root, provider=provider
    )

    seen: set[tuple[str, int, int, str]] = set()
    collected: list[tuple[matchers.Candidate, str, str, str, str]] = []
    # code_warnings (backend-unavailable / unsupported-language) are scan-wide,
    # so they are added once here rather than once per sub-target.
    candidate_warnings: list[dict[str, Any]] = list(code_warnings)
    for (sub_old, sub_new), nc_candidates in zip(sub_targets, non_code_by_target):
        sub_op = classify.classify_operation(sub_old, sub_new)
        is_folder_path = sub_old == old_rel
        folder_basename = Path(old_rel).name

        sub_candidates = list(nc_candidates)
        sub_candidates.extend(code_matcher.match_code_sites(sub_old, code_sites))

        for candidate in sub_candidates:
            key = (candidate.file, candidate.line, candidate.offset, candidate.match)
            if key in seen:
                continue
            seen.add(key)

            # Basename-resolved references to the folder path itself should count
            # the folder as a resolution target; the matcher only sees files.
            class_candidate = candidate
            if is_folder_path and candidate.syntax in ("wikilink", "frontmatter-field"):
                if matchers._case_equal(candidate.target, folder_basename):
                    class_candidate = dataclasses.replace(
                        candidate, resolves_to=candidate.resolves_to + 1
                    )

            # References inside files that move with the folder must be recomputed
            # relative to the file's NEW location, not its old one.
            replace_candidate = _candidate_at_new_path(candidate, old_rel, new_rel)
            if candidate.syntax == "code-import":
                proposed = _compute_code_proposed(
                    replace_candidate, sub_old, sub_new, scope_root
                )
                if candidate.resolves_to == 0:
                    # D8 unresolved static import: surface with no proposed rewrite.
                    proposed = ""
                    ref_class = classify.CLASS_SURFACE
                else:
                    ref_class = classify.classify(
                        candidate, sub_op, scope_root=scope_root
                    )
            else:
                proposed = replace.compute_proposed(
                    replace_candidate,
                    sub_old,
                    sub_new,
                    sub_op,
                    scope_root=scope_root,
                )
                ref_class = classify.classify(
                    class_candidate, sub_op, scope_root=scope_root
                )
            if proposed is None or proposed == "":
                proposed = ""
                ref_class = classify.CLASS_SURFACE
            collected.append((candidate, sub_old, sub_new, proposed, ref_class))

    collected.sort(key=lambda item: (item[0].file, item[0].line, item[0].match))

    references: list[dict[str, Any]] = []
    folder_path_refs: list[str] = []
    contained_file_refs: list[str] = []
    for index, (candidate, sub_old, sub_new, proposed, ref_class) in enumerate(collected, 1):
        ref_id = f"ref-{index:04d}"
        references.append(_reference_record(ref_id, candidate, proposed, ref_class))
        candidate_warnings.extend(_warnings_for_candidate(candidate, ref_id))
        if sub_old == old_rel:
            folder_path_refs.append(ref_id)
        else:
            contained_file_refs.append(ref_id)

    from safe_move.move import nested_repos

    nested = nested_repos(old_abs)
    nested_set = set(nested)

    def _is_under_nested_repo(path: Path) -> bool:
        return any(
            path == nested_path or nested_path in path.parents
            for nested_path in nested_set
        )

    if nested:
        candidate_warnings.append(
            {
                "kind": "nested-repo",
                "message": (
                    "folder contains nested git repository(s) that were not "
                    "folded into the outer move: "
                    + ", ".join(_display_path(p, scope_root) for p in nested)
                ),
                "file": _display_path(old_abs, scope_root),
                "ref_id": None,
            }
        )

    moved_files = [
        path.relative_to(scope_root).as_posix()
        for path in sorted(old_abs.rglob("*"))
        if path.is_file() and not _is_under_nested_repo(path)
    ]
    folder_cascade = {
        "moved_files": moved_files,
        "folder_path_refs": folder_path_refs,
        "contained_file_refs": contained_file_refs,
    }
    return references, folder_cascade, candidate_warnings, nested


def _maybe_warn_index_cascade(
    old_abs: Path,
    new_rel: str,
    scope_root: Path,
    warnings: list[dict[str, Any]],
) -> None:
    """Warn when the folder contains a `<basename>.md` index that may need renaming."""
    if Path(new_rel).name == old_abs.name:
        return
    index_candidate = old_abs / (old_abs.name + ".md")
    if index_candidate.is_file():
        warnings.append(
            {
                "kind": "index-cascade",
                "message": "folder contains an index file that may need renaming after the folder rename",
                "file": _display_path(index_candidate, scope_root),
                "ref_id": None,
            }
        )


def compute_git_move_method(
    old_abs: Path,
    new_abs: Path,
    scope_root: Path,
) -> tuple[str, list[dict[str, Any]]]:
    """Return ``git mv`` for tracked same-repo moves, otherwise ``mv`` plus warnings."""
    old_repo = scope.git_toplevel(old_abs.parent if old_abs.is_file() else old_abs)
    new_repo = scope.git_toplevel(_nearest_existing_parent(new_abs))
    warnings: list[dict[str, Any]] = []

    if old_repo is not None and new_repo is not None and old_repo != new_repo:
        warnings.append(
            {
                "kind": "history-loss",
                "message": "cross-repo move uses mv; git history does not follow",
                "file": _display_path(old_abs, scope_root),
                "ref_id": None,
            }
        )
        return "mv", warnings

    if old_repo is not None and _is_tracked(old_abs, old_repo):
        return "git mv", warnings
    return "mv", warnings


def _is_dynamic_import(candidate: matchers.Candidate) -> bool:
    """Return True when the candidate came from a literal dynamic import."""
    if candidate.syntax != "code-import":
        return False
    context = candidate.context or ""
    spec = candidate.match.strip("'\"")
    if not spec:
        return False
    for match in re.finditer(
        r"import\s*\(\s*['\"](?P<spec>[^'\"]+)['\"]\s*\)", context
    ):
        if match.group("spec") == spec:
            start, end = match.span()
            if start <= candidate.offset < end:
                return True
    return False


def _warnings_for_candidate(candidate: matchers.Candidate, ref_id: str) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if candidate.syntax == "footnote-citation":
        warnings.append(
            {
                "kind": "governed-handoff",
                "message": "governed reference surfaced for caller hand-off",
                "file": candidate.file,
                "ref_id": ref_id,
            }
        )
    if candidate.boundary is not None:
        warnings.append(
            {
                "kind": "cross-project",
                "message": "reference is inside a different git repository and was surfaced",
                "file": candidate.file,
                "ref_id": ref_id,
            }
        )
    if candidate.generated:
        warnings.append(
            {
                "kind": "regenerate",
                "message": "generated file reference surfaced; regenerate instead of patching",
                "file": candidate.file,
                "ref_id": ref_id,
            }
        )
    if candidate.syntax == "code-import":
        if _is_dynamic_import(candidate):
            warnings.append(
                {
                    "kind": "code-dynamic-import",
                    "message": (
                        "a dynamic import referencing the moved file — review manually"
                    ),
                    "file": candidate.file,
                    "ref_id": ref_id,
                }
            )
        elif candidate.resolves_to == 0:
            warnings.append(
                {
                    "kind": "code-unresolved-import",
                    "message": (
                        "a static import whose specifier could not be resolved but whose "
                        "basename matches the moved file — review manually"
                    ),
                    "file": candidate.file,
                    "ref_id": ref_id,
                }
            )
    return warnings


def _warning_from_walk(warning: scope.WalkWarning) -> dict[str, Any]:
    return {
        "kind": warning.kind,
        "message": warning.message,
        "file": warning.file,
        "ref_id": None,
    }


def _non_utf8_warnings(provider: scope.ContentProvider) -> list[dict[str, Any]]:
    """Return a single aggregated warning for files skipped as non-UTF-8.

    Files that could not be read as UTF-8 (binary that slipped past the
    walk-time NUL filter, or genuinely non-UTF-8 text) are skipped as reference
    sources so they cannot crash the run. They are reported once, in aggregate,
    rather than one warning per file (a real vault scope contains thousands of
    binaries). Empty when every scanned file decoded cleanly.
    """
    paths = provider.undecodable
    if not paths:
        return []
    sample = ", ".join(paths[:5])
    suffix = "" if len(paths) <= 5 else f" (and {len(paths) - 5} more)"
    return [
        {
            "kind": "non-utf8-skipped",
            "message": (
                f"{len(paths)} file(s) could not be read as UTF-8 and were "
                f"skipped (not scanned for references): {sample}{suffix}"
            ),
            "file": None,
            "ref_id": None,
        }
    ]


def _nearest_existing_parent(path: Path) -> Path:
    current = path if path.exists() and path.is_dir() else path.parent
    while not current.exists() and current != current.parent:
        current = current.parent
    return current


def _is_tracked(path: Path, repo: Path) -> bool:
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _display_path(path: Path, scope_root: Path) -> str:
    try:
        return path.relative_to(scope_root).as_posix()
    except ValueError:
        return path.as_posix()
