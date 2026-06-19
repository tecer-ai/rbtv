"""Structural code-reference matcher using ast-grep.

Finds static import/require/export references to a moved target by matching
AST nodes, never by raw text/regex.  Emits ``code-import`` candidates that
flow through the same consult record pipeline as non-code references.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from safe_move.matchers import Candidate, _case_equal
from safe_move.scope import ContentProvider, WalkedFile


#: ast-grep --lang value for each supported file extension.
LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".ts": "ts",
    ".tsx": "tsx",
    ".py": "py",
    ".go": "go",
    ".rs": "rs",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "cs",
    ".rb": "rb",
}

#: Extensions recognized as code but not supported by the current backend map.
#: These produce an unsupported-language warning instead of being silently
#: dropped, so the owner knows a structural match was not attempted.
UNSUPPORTED_CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".swift",
        ".kt",
        ".kts",
        ".php",
        ".scala",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".elm",
        ".clj",
        ".erl",
        ".ex",
        ".exs",
        ".ml",
        ".fs",
        ".fsx",
        ".groovy",
        ".gradle",
    }
)

#: AST patterns per language.  Each pattern uses the ``$SRC`` metavariable to
#: capture the import/require/export specifier string.
LANGUAGE_PATTERNS: dict[str, list[str]] = {
    "js": [
        "import $_ from '$SRC'",
        "require('$SRC')",
        "export { $_ } from '$SRC'",
        "export * from '$SRC'",
    ],
    "ts": [
        "import $_ from '$SRC'",
        "require('$SRC')",
        "export { $_ } from '$SRC'",
        "export * from '$SRC'",
    ],
    "tsx": [
        "import $_ from '$SRC'",
        "require('$SRC')",
        "export { $_ } from '$SRC'",
        "export * from '$SRC'",
    ],
    "py": [
        "from $SRC import $_",
        "import $SRC",
    ],
    "go": [
        'import "$SRC"',
    ],
    "rs": [
        "mod $SRC",
    ],
    "java": [
        "import $SRC",
    ],
    "c": [
        '#include "$SRC"',
    ],
    "cpp": [
        '#include "$SRC"',
    ],
    "cs": [
        "using $SRC",
    ],
    "rb": [
        "require '$SRC'",
        "require_relative '$SRC'",
    ],
}

#: Dynamic import patterns per language.  These match literal-string dynamic
#: imports and are NEVER classed ``auto``.
DYNAMIC_LANGUAGE_PATTERNS: dict[str, list[str]] = {
    "js": ["import('$SRC')", 'import("$SRC")'],
    "ts": ["import('$SRC')", 'import("$SRC")'],
    "tsx": ["import('$SRC')", 'import("$SRC")'],
}

#: Extensions tried when a relative specifier omits one.
_CODE_EXTENSIONS: tuple[str, ...] = tuple(
    ext
    for ext in LANGUAGE_BY_EXTENSION
    if ext not in {".h", ".hpp"}
)

#: Index file names tried when a specifier resolves to a directory.
_INDEX_FILES: tuple[str, ...] = tuple(f"index{ext}" for ext in _CODE_EXTENSIONS)


#: Pinned ast-grep package + version. The package is resolved once per run to a
#: directly-runnable binary; the version is verified before any direct binary is
#: trusted, so a different ast-grep on PATH can never silently change matching.
_AST_GREP_PKG: str = "@ast-grep/cli@0.43.0"
_AST_GREP_VERSION: str = "0.43.0"

#: Subprocess timeouts (seconds) for the once-per-run resolution probes.
_DISCOVERY_TIMEOUT: int = 120
_VERSION_TIMEOUT: int = 30


def _find_npx() -> str | None:
    """Return the path to an ``npx`` executable on PATH, or ``None``."""
    return shutil.which("npx")


def _binary_is_pinned(prefix: list[str]) -> bool:
    """Return True when ``prefix`` runs and reports the pinned ast-grep version.

    Guards every direct-binary fast path: a binary is trusted only when
    ``<prefix> --version`` exits 0 and names ``_AST_GREP_VERSION``, so a
    different ast-grep on PATH or a broken cache entry is never used (it falls
    back to the pinned npx path instead).
    """
    try:
        result = subprocess.run(
            list(prefix) + ["--version"],
            capture_output=True,
            text=True,
            timeout=_VERSION_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and _AST_GREP_VERSION in (result.stdout or "")


def _resolve_cached_binary(npx: str) -> str | None:
    """Resolve the directly-runnable ast-grep binary npx caches for the pin.

    Asks npx ONCE where it puts the pinned package's ``.bin`` directory (the
    first runnable ``ast-grep`` on the child PATH npx prepends), then prefers the
    platform-native executable — avoiding the per-call cmd.exe shim on Windows —
    and falls back to the ``.bin`` entry. Returns an absolute path, or ``None``
    when discovery fails (the caller then keeps the per-call npx path).
    """
    try:
        proc = subprocess.run(
            [
                npx,
                "--yes",
                "-p",
                _AST_GREP_PKG,
                "node",
                "-e",
                "process.stdout.write(process.env.PATH)",
            ],
            capture_output=True,
            text=True,
            timeout=_DISCOVERY_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    child_path = proc.stdout.strip()
    shim = shutil.which("ast-grep", path=child_path) or shutil.which(
        "sg", path=child_path
    )
    if not shim:
        return None
    node_modules = os.path.dirname(os.path.dirname(shim))
    native_name = "ast-grep.exe" if os.name == "nt" else "ast-grep"
    for cand in sorted(
        glob.glob(os.path.join(node_modules, "@ast-grep", "cli-*", native_name))
    ):
        if os.path.isfile(cand):
            return cand
    return shim


def _resolve_ast_grep_prefix() -> list[str] | None:
    """Resolve, ONCE per run, the command prefix used to invoke ast-grep.

    Returns a list whose elements precede the ``run …`` arguments. The ladder
    prefers a directly-runnable, pin-verified binary so the scan pays no npx
    package-resolution cold-start per call:

    1. A pinned ``ast-grep``/``sg`` already on PATH (e.g. a global install).
    2. The pinned binary npx already caches (resolved + verified once).
    3. Per-call ``npx`` (today's behavior) when no direct binary is trusted.

    Returns ``None`` only when npx itself is unavailable — the caller then emits
    the ``code-backend-unavailable`` warning.
    """
    for name in ("ast-grep", "sg"):
        binary = shutil.which(name)
        if binary and _binary_is_pinned([binary]):
            return [binary]

    npx = _find_npx()
    if npx is None:
        return None

    cached = _resolve_cached_binary(npx)
    if cached and _binary_is_pinned([cached]):
        return [cached]

    return [npx, "--yes", "-p", _AST_GREP_PKG, "ast-grep"]


class CodeMatchError(Exception):
    """Raised when the structural backend cannot be invoked."""


def _ast_grep_command(
    prefix: list[str],
    lang: str,
    pattern: str,
    file_paths: Iterable[Path],
) -> list[str]:
    """Return the ast-grep invocation for a language/pattern over paths.

    ``prefix`` is the once-per-run resolved invocation head from
    ``_resolve_ast_grep_prefix`` — a direct binary, or the per-call npx fallback.
    """
    return list(prefix) + [
        "run",
        "--lang",
        lang,
        "--pattern",
        pattern,
        "--json=compact",
    ] + [str(p) for p in file_paths]


def _strip_quotes(text: str) -> str:
    """Remove a single pair of surrounding single or double quotes."""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _run_ast_grep(
    prefix: list[str],
    file_paths: list[Path],
    lang: str,
    patterns: list[str],
    kind: str = "static",
) -> list[dict[str, Any]]:
    """Run ast-grep patterns against ``file_paths`` and return raw matches.

    One subprocess is spawned per pattern over the whole path list; results
    are merged.  Parse failures or empty matches return an empty list rather
    than crashing the scan.  Each match is tagged with ``_kind`` so the
    builder can tell static from dynamic import patterns.
    """
    matches: list[dict[str, Any]] = []
    for pattern in patterns:
        cmd = _ast_grep_command(prefix, lang, pattern, file_paths)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        if not result.stdout.strip():
            continue
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for match in data:
                match["_kind"] = kind
            matches.extend(data)
    return matches


def _line_context(content: str, line_no: int) -> str:
    """Return the full text of the 1-based ``line_no`` (without trailing newline)."""
    lines = content.splitlines()
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1]
    return ""


def _offset_in_line(context: str, match: str, fallback: int) -> int:
    """Return the 0-based column of ``match`` in ``context``.

    Falls back to the ast-grep-reported column when the literal text is not
    found (e.g. normalization differences).
    """
    idx = context.find(match)
    if idx != -1:
        return idx
    return fallback


def _specifier_basename_stem(specifier: str, lang: str | None = None) -> str | None:
    """Return the extension-stripped final segment of a specifier, or None.

    For dotted module paths (Python/Java/C#), the final segment is the last
    dot-separated part; for other specifier forms it is the path basename.
    """
    if not specifier:
        return None
    if lang in ("py", "java", "cs"):
        segment = specifier.split(".")[-1]
    else:
        segment = Path(specifier).name
    if not segment:
        return None
    return Path(segment).stem


def _target_stem(target_rel: str) -> str:
    """Return the extension-stripped basename of the moved target."""
    return Path(Path(target_rel).name).stem


def _is_relative_specifier(lang: str, specifier: str) -> bool:
    """Return True when the specifier is a relative file path for the language.

    Only relative specifiers may be resolved to filesystem paths and reach
    ``auto``; every other specifier form is surfaced for manual review.
    """
    if lang == "py":
        return specifier.startswith(".")
    return specifier.startswith(("./", "../"))


def _resolve_relative_specifier(
    specifier: str,
    importer_dir: Path,
    scope_root: Path,
) -> list[str]:
    """Resolve a relative code specifier to scope-relative file paths.

    Handles extensionless imports and directory/index imports.  Returns all
    candidate files the specifier could name, so multiplicity can be reported
    for ambiguous cases.
    """
    if not specifier.startswith(("./", "../")):
        return []

    root = scope_root.expanduser().resolve()
    base = (root / importer_dir).resolve()
    literal = (base / specifier).resolve()

    candidates: set[Path] = set()

    if literal.is_file():
        candidates.add(literal)
    elif literal.is_dir():
        for idx_name in _INDEX_FILES:
            candidate = literal / idx_name
            if candidate.is_file():
                candidates.add(candidate)
    else:
        for ext in _CODE_EXTENSIONS:
            candidate = Path(f"{literal}{ext}")
            if candidate.is_file():
                candidates.add(candidate)

    result: list[str] = []
    for candidate in candidates:
        try:
            rel = candidate.relative_to(root).as_posix()
        except ValueError:
            continue
        result.append(rel)
    return result


def _python_relative_to_path(specifier: str) -> str | None:
    """Convert a Python relative module specifier to a file-relative path."""
    if not specifier.startswith("."):
        return None
    dot_count = 0
    for ch in specifier:
        if ch == ".":
            dot_count += 1
        else:
            break
    name = specifier[dot_count:]
    if dot_count == 1:
        return f"./{name}"
    return "../" * (dot_count - 1) + f"./{name}"


def _resolve_python_specifier(
    specifier: str,
    importer_dir: Path,
    scope_root: Path,
) -> list[str]:
    """Resolve a Python module specifier (dotted or relative) to file paths."""
    if not specifier:
        return []

    if specifier.startswith("."):
        path_form = _python_relative_to_path(specifier)
        if path_form is None:
            return []
        return _resolve_relative_specifier(path_form, importer_dir, scope_root)

    if "." in specifier:
        # Package import: convert dots to path separators.
        parts = specifier.split(".")
        module_path = "/".join(parts)
        candidates: set[Path] = set()
        root = scope_root.expanduser().resolve()

        # Scope-root-relative package import.
        package_root = root / module_path
        package_init = package_root / "__init__.py"
        module_file = Path(f"{package_root}.py")
        if module_file.is_file():
            candidates.add(module_file)
        if package_init.is_file():
            candidates.add(package_init)

        result: list[str] = []
        for candidate in candidates:
            try:
                rel = candidate.relative_to(root).as_posix()
            except ValueError:
                continue
            result.append(rel)
        return result

    return []


def _resolve_specifier(
    lang: str,
    specifier: str,
    importer_dir: Path,
    scope_root: Path,
) -> list[str]:
    """Dispatch specifier resolution by language."""
    if lang == "py":
        return _resolve_python_specifier(specifier, importer_dir, scope_root)
    return _resolve_relative_specifier(specifier, importer_dir, scope_root)


def _chunk_paths(paths: list[Path], max_chars: int = 7500) -> list[list[Path]]:
    """Split ``paths`` into chunks whose joined string length stays under limit.

    The limit targets the OS command-line length consumed by the path
    arguments; the base ast-grep command overhead is reserved separately.
    """
    chunks: list[list[Path]] = []
    current: list[Path] = []
    current_len = 0
    for path in paths:
        s = str(path)
        add_len = len(s) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            chunks.append(current)
            current = [path]
            current_len = len(s)
        else:
            current.append(path)
            current_len += add_len
    if current:
        chunks.append(current)
    return chunks


@dataclass(frozen=True, slots=True)
class _CodeSite:
    """A target-independent structural code-import site found by ast-grep.

    The expensive work — running ast-grep and resolving the specifier to
    filesystem paths — happens once per site; ``match_code_sites`` then checks a
    site against any number of move targets with no further subprocess or I/O.
    """

    file: str
    line: int
    context: str
    raw_specifier: str
    specifier: str
    is_dynamic: bool
    offset: int
    resolved: tuple[str, ...]
    spec_stem: str | None
    read_only: bool
    generated: bool
    boundary: Path | None


def _site_from_match(
    match: dict[str, Any],
    abs_lookup: dict[str, WalkedFile],
    provider: ContentProvider,
    scope_root: Path,
    lang: str,
) -> _CodeSite | None:
    """Map one ast-grep match (with a ``file`` field) to a target-independent site."""
    file_str = match.get("file")
    if not file_str:
        return None
    wf = abs_lookup.get(Path(file_str).expanduser().resolve().as_posix())
    if wf is None:
        return None
    content = provider.get(wf)
    if content is None:
        return None

    src = match.get("metaVariables", {}).get("single", {}).get("SRC")
    if not src:
        return None
    raw_specifier = src.get("text", "")
    if not raw_specifier:
        return None

    is_dynamic = match.get("_kind") == "dynamic"
    specifier = _strip_quotes(raw_specifier) if is_dynamic else raw_specifier
    if not specifier:
        return None

    start_info = match.get("range", {}).get("start", {})
    line_no = start_info.get("line", 0) + 1  # ast-grep is 0-based
    context = _line_context(content, line_no)
    offset = _offset_in_line(context, raw_specifier, start_info.get("column", 0))

    # FIX 1 (D9): only relative specifiers may be resolved to filesystem paths
    # and reach ``auto``.  Non-relative forms route through the D8 basename path.
    importer_dir = Path(wf.path).parent
    if is_dynamic or _is_relative_specifier(lang, specifier):
        resolved = _resolve_specifier(lang, specifier, importer_dir, scope_root)
    else:
        resolved = []

    return _CodeSite(
        file=wf.path,
        line=line_no,
        context=context,
        raw_specifier=raw_specifier,
        specifier=specifier,
        is_dynamic=is_dynamic,
        offset=offset,
        resolved=tuple(resolved),
        spec_stem=_specifier_basename_stem(specifier, lang),
        read_only=wf.read_only,
        generated=wf.generated,
        boundary=wf.boundary,
    )


def _code_candidate(site: _CodeSite, resolves_to: int) -> Candidate:
    """Build a ``code-import`` Candidate from a matched site."""
    return Candidate(
        file=site.file,
        line=site.line,
        match=site.raw_specifier,
        context=site.context,
        syntax="code-import",
        target=site.specifier,
        fragment=None,
        alias=None,
        encoding="plain",
        resolves_to=resolves_to,
        offset=site.offset,
        read_only=site.read_only,
        generated=site.generated,
        boundary=site.boundary,
    )


def match_code_sites(target_rel: str, sites: Iterable[_CodeSite]) -> list[Candidate]:
    """Return code-import Candidates from pre-scanned ``sites`` for ``target_rel``.

    Pure in-memory: no subprocess, no file reads. Classification matches the
    single-pass path exactly — a resolved static import becomes auto-eligible
    (``resolves_to`` = match count); a literal dynamic import is emitted only on
    direct resolution as surface (``resolves_to`` = 0); a static import that did
    not resolve but whose basename matches the target is surfaced
    (``resolves_to`` = 0).
    """
    target_rel_norm = target_rel.replace(os.sep, "/")
    target_stem = _target_stem(target_rel_norm)
    candidates: list[Candidate] = []
    for site in sites:
        if any(_case_equal(r, target_rel_norm) for r in site.resolved):
            resolves_to = 0 if site.is_dynamic else len(site.resolved)
            candidates.append(_code_candidate(site, resolves_to))
        elif site.is_dynamic:
            # Dynamic imports are emitted only on direct resolution.
            continue
        elif site.spec_stem is not None and _case_equal(site.spec_stem, target_stem):
            candidates.append(_code_candidate(site, 0))
    candidates.sort(key=lambda c: (c.file, c.line, c.match))
    return candidates


def scan_code_references(
    walked: Iterable[WalkedFile],
    scope_root: str | Path,
    *,
    provider: ContentProvider | None = None,
) -> tuple[list[_CodeSite], list[dict[str, Any]]]:
    """Scan the haystack ONCE for structural code-import sites via ast-grep.

    ast-grep is invoked O(languages × patterns) times over the whole file set,
    independent of how many move targets are later matched against the result.
    Returns target-independent sites (each specifier already resolved) plus
    backend-unavailable / unsupported-language warnings. ``match_code_sites``
    filters these for a given target with no further subprocess or I/O — so a
    folder move scans the scope once instead of once per contained file.
    """
    scope_root_path = Path(scope_root).expanduser().resolve()
    sites: list[_CodeSite] = []
    warnings: list[dict[str, Any]] = []
    if provider is None:
        provider = ContentProvider()

    prefix = _resolve_ast_grep_prefix()
    if os.environ.get("SAFE_MOVE_AST_GREP_TRACE"):
        summary = "unavailable" if prefix is None else " ".join(prefix)
        print(f"[safe-move] ast-grep backend: {summary}", file=sys.stderr)
    if prefix is None:
        warnings.append(
            {
                "kind": "code-backend-unavailable",
                "message": (
                    "structural code matching is unavailable: no ast-grep binary "
                    "on PATH and npx was not found. Install Node.js/npm (or run "
                    "`npm i -g @ast-grep/cli@0.43.0`) to enable ast-grep code "
                    "discovery."
                ),
                "file": None,
                "ref_id": None,
            }
        )
        return sites, warnings

    # Group supported files by language and collect unsupported warnings in
    # walk order.
    files_by_lang: dict[str, list[WalkedFile]] = {}
    unsupported_files: list[WalkedFile] = []
    for wf in walked:
        ext = Path(wf.path).suffix.lower()
        if ext in LANGUAGE_BY_EXTENSION:
            files_by_lang.setdefault(LANGUAGE_BY_EXTENSION[ext], []).append(wf)
        elif ext in UNSUPPORTED_CODE_EXTENSIONS:
            unsupported_files.append(wf)

    # Resolve absolute paths once; build lookup keyed by resolved posix path.
    abs_lookup: dict[str, WalkedFile] = {}
    paths_by_lang: dict[str, list[Path]] = {}
    for lang, files in files_by_lang.items():
        paths: list[Path] = []
        for wf in files:
            try:
                path = wf.abs_path.expanduser().resolve()
            except (OSError, ValueError):
                continue
            abs_lookup[path.as_posix()] = wf
            paths.append(path)
        if paths:
            paths_by_lang[lang] = paths

    for lang, paths in paths_by_lang.items():
        static_patterns = LANGUAGE_PATTERNS.get(lang, [])
        dynamic_patterns = DYNAMIC_LANGUAGE_PATTERNS.get(lang, [])
        if not static_patterns and not dynamic_patterns:
            continue

        for chunk in _chunk_paths(paths):
            if static_patterns:
                for match in _run_ast_grep(
                    prefix, chunk, lang, static_patterns, kind="static"
                ):
                    site = _site_from_match(
                        match, abs_lookup, provider, scope_root_path, lang
                    )
                    if site is not None:
                        sites.append(site)
            if dynamic_patterns:
                for match in _run_ast_grep(
                    prefix, chunk, lang, dynamic_patterns, kind="dynamic"
                ):
                    site = _site_from_match(
                        match, abs_lookup, provider, scope_root_path, lang
                    )
                    if site is not None:
                        sites.append(site)

    for wf in unsupported_files:
        warnings.append(
            {
                "kind": "code-unsupported-language",
                "message": (
                    f"structural code matching is not supported for "
                    f"{Path(wf.path).suffix.lower()} files; "
                    f"any references in {wf.path} were not discovered"
                ),
                "file": wf.path,
                "ref_id": None,
            }
        )

    return sites, warnings


def find_code_candidates(
    target_rel: str,
    walked: Iterable[WalkedFile],
    scope_root: str | Path,
    *,
    provider: ContentProvider | None = None,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """Return structural code references to ``target_rel`` plus warnings.

    Single-target convenience wrapper: scan the haystack, then match the one
    target. Folder moves instead call ``scan_code_references`` once and
    ``match_code_sites`` per sub-target, so ast-grep runs once total.
    """
    sites, warnings = scan_code_references(walked, scope_root, provider=provider)
    return match_code_sites(target_rel, sites), warnings
