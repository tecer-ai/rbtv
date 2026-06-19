"""Tests for structural code-reference discovery (ast-grep backed)."""

from __future__ import annotations

import subprocess

from safe_move.classify import CLASS_AUTO, CLASS_SURFACE
from safe_move.consult import build_consult_result
from safe_move.scope import WalkedFile


def _code_refs(result: dict) -> list[dict]:
    return [r for r in result["references"] if r["syntax"] == "code-import"]


def test_static_js_import_is_ast_confirmed_code_reference(repo_builder):
    fix = repo_builder(
        "code-static-import",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["line"] == 1
    assert refs[0]["match"] == "./foo"
    assert refs[0]["context"] == "import { foo } from './foo';"
    assert refs[0]["syntax"] == "code-import"
    assert refs[0]["proposed"] == "./bar"
    assert refs[0]["class"] == CLASS_AUTO
    assert refs[0]["offset"] == 21


def test_string_literal_mention_is_not_a_code_reference(repo_builder):
    fix = repo_builder(
        "code-string-mention",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const path = './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert refs == []


def test_literal_dynamic_import_is_surfaced_with_dynamic_warning(repo_builder):
    fix = repo_builder(
        "code-dynamic-import-surfaced",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const load = () => import('./foo');\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "./foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""
    warning = next(
        (w for w in result["warnings"] if w["kind"] == "code-dynamic-import"),
        None,
    )
    assert warning is not None
    assert warning["file"] == "src/a.ts"
    assert warning["ref_id"] == refs[0]["id"]


def test_double_quoted_literal_dynamic_import_is_surfaced(repo_builder):
    fix = repo_builder(
        "code-dynamic-import-double",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": 'const m = import("./foo");\n',
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "./foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""
    assert any(
        w["kind"] == "code-dynamic-import" and w["ref_id"] == refs[0]["id"]
        for w in result["warnings"]
    )


def test_require_call_is_a_code_reference(repo_builder):
    fix = repo_builder(
        "code-require",
        {
            "src/foo.js": "module.exports.foo = 1;\n",
            "src/a.js": "const { foo } = require('./foo');\n",
        },
        tracked=["src/foo.js", "src/a.js"],
    )

    result = build_consult_result(
        "src/foo.js",
        "src/bar.js",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["match"] == "./foo"
    assert refs[0]["proposed"] == "./bar"


def test_re_export_is_a_code_reference(repo_builder):
    fix = repo_builder(
        "code-reexport",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "export { foo } from './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/baz.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["match"] == "./foo"
    assert refs[0]["proposed"] == "./baz"


def test_code_specifier_recomputed_per_referring_file_on_move(repo_builder):
    fix = repo_builder(
        "code-move-depth",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "lib/a.ts": "import { foo } from '../src/foo';\n",
        },
        tracked=["src/foo.ts", "lib/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "dst/foo.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "lib/a.ts"
    assert refs[0]["match"] == "../src/foo"
    assert refs[0]["proposed"] == "../dst/foo"


def test_code_import_preserves_extensionless_form(repo_builder):
    fix = repo_builder(
        "code-extensionless",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["match"] == "./foo"
    assert refs[0]["proposed"] == "./bar"


def test_code_import_preserves_explicit_extension(repo_builder):
    fix = repo_builder(
        "code-with-extension",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from './foo.ts';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["match"] == "./foo.ts"
    assert refs[0]["proposed"] == "./bar.ts"


def test_python_relative_import_is_discovered_and_auto(repo_builder):
    fix = repo_builder(
        "code-python-relative-auto",
        {
            "src/foo.py": "foo = 1\n",
            "src/a.py": "from .foo import foo\n",
        },
        tracked=["src/foo.py", "src/a.py"],
    )

    result = build_consult_result(
        "src/foo.py",
        "src/bar.py",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.py"
    assert refs[0]["match"] == ".foo"
    assert refs[0]["proposed"] == ".bar"
    assert refs[0]["class"] == CLASS_AUTO


def test_python_absolute_import_is_surface_not_auto(repo_builder):
    """D9: a Python dotted absolute import must never be classed auto."""
    fix = repo_builder(
        "code-python-absolute-surface",
        {
            "pkg/__init__.py": "",
            "pkg/foo.py": "VALUE = 1\n",
            "main.py": "from pkg.foo import VALUE\n",
        },
        tracked=["pkg/__init__.py", "pkg/foo.py", "main.py"],
    )

    result = build_consult_result(
        "pkg/foo.py",
        "pkg/bar.py",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "main.py"
    assert refs[0]["match"] == "pkg.foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""
    warning = next(
        (w for w in result["warnings"] if w["kind"] == "code-unresolved-import"),
        None,
    )
    assert warning is not None
    assert warning["file"] == "main.py"
    assert warning["ref_id"] == refs[0]["id"]


def test_code_reference_in_folder_move_is_recomputed(repo_builder):
    fix = repo_builder(
        "code-folder-move",
        {
            "old/utils.ts": "export const x = 1;\n",
            "src/app.ts": "import { x } from '../old/utils';\n",
        },
        tracked=["old/utils.ts", "src/app.ts"],
    )

    result = build_consult_result(
        "old",
        "new",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/app.ts"
    assert refs[0]["match"] == "../old/utils"
    assert refs[0]["proposed"] == "../new/utils"
    assert refs[0]["class"] == CLASS_AUTO


def test_code_matcher_batches_ast_grep_by_language(tmp_path, monkeypatch):
    """p6-5: ast-grep is invoked O(languages * patterns * chunks),
    not O(files * patterns).
    """
    import safe_move.code_matcher as cm

    (tmp_path / "foo.ts").write_text("export const foo = 1;\n", encoding="utf-8")

    num_files = 20
    walked: list[WalkedFile] = []
    for i in range(num_files):
        rel = f"src/f{i:02d}.ts"
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("import { foo } from './foo';\n", encoding="utf-8")
        walked.append(
            WalkedFile(
                path=rel,
                abs_path=path,
                read_only=False,
                generated=False,
                boundary=None,
            )
        )

    walked.append(
        WalkedFile(
            path="foo.ts",
            abs_path=tmp_path / "foo.ts",
            read_only=False,
            generated=False,
            boundary=None,
        )
    )

    calls: list[list[str]] = []

    class FakeSubprocess:
        def run(self, cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="[]", stderr=""
            )

    monkeypatch.setattr(cm, "_resolve_ast_grep_prefix", lambda: ["ast-grep"])
    monkeypatch.setattr(cm, "subprocess", FakeSubprocess())

    candidates, warnings = cm.find_code_candidates(
        "foo.ts", walked, scope_root=tmp_path
    )

    assert candidates == []
    assert warnings == []

    num_static = len(cm.LANGUAGE_PATTERNS["ts"])
    num_dynamic = len(cm.DYNAMIC_LANGUAGE_PATTERNS.get("ts", []))
    # Short paths fit in one chunk; allow two chunks for margin.
    max_expected = (num_static + num_dynamic) * 2
    assert len(calls) <= max_expected
    assert len(calls) < num_files  # per-file engine would be num_files * (static+dynamic)


# ---------------------------------------------------------------------------
# Backend resolution: a directly-runnable, pin-verified binary is preferred,
# the per-call npx path is the fallback, and absence degrades gracefully.
# ---------------------------------------------------------------------------


def test_resolve_prefix_prefers_pinned_path_binary(monkeypatch):
    """A pinned ast-grep already on PATH is used directly — no npx prefix."""
    import safe_move.code_matcher as cm

    monkeypatch.setattr(
        cm.shutil,
        "which",
        lambda name, path=None: "/usr/bin/ast-grep" if name == "ast-grep" else None,
    )
    monkeypatch.setattr(cm, "_binary_is_pinned", lambda prefix: True)

    assert cm._resolve_ast_grep_prefix() == ["/usr/bin/ast-grep"]


def test_resolve_prefix_rejects_unpinned_path_binary(monkeypatch):
    """A wrong-version ast-grep on PATH is never used; falls back to pinned npx."""
    import safe_move.code_matcher as cm

    monkeypatch.setattr(
        cm.shutil,
        "which",
        lambda name, path=None: "/usr/bin/ast-grep"
        if name in ("ast-grep", "sg")
        else None,
    )
    monkeypatch.setattr(cm, "_binary_is_pinned", lambda prefix: False)
    monkeypatch.setattr(cm, "_find_npx", lambda: "/usr/bin/npx")
    monkeypatch.setattr(cm, "_resolve_cached_binary", lambda npx: None)

    assert cm._resolve_ast_grep_prefix() == [
        "/usr/bin/npx",
        "--yes",
        "-p",
        cm._AST_GREP_PKG,
        "ast-grep",
    ]


def test_resolve_prefix_uses_cached_binary_when_pinned(monkeypatch):
    """With nothing on PATH, the pinned binary npx caches is used directly."""
    import safe_move.code_matcher as cm

    monkeypatch.setattr(cm.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(cm, "_find_npx", lambda: "/usr/bin/npx")
    monkeypatch.setattr(cm, "_resolve_cached_binary", lambda npx: "/cache/.bin/ast-grep")
    monkeypatch.setattr(cm, "_binary_is_pinned", lambda prefix: True)

    assert cm._resolve_ast_grep_prefix() == ["/cache/.bin/ast-grep"]


def test_resolve_prefix_none_when_no_backend(monkeypatch):
    """No PATH binary and no npx → None (caller emits the unavailable warning)."""
    import safe_move.code_matcher as cm

    monkeypatch.setattr(cm.shutil, "which", lambda name, path=None: None)
    monkeypatch.setattr(cm, "_find_npx", lambda: None)

    assert cm._resolve_ast_grep_prefix() is None


def test_scan_emits_backend_unavailable_when_unresolved(repo_builder, monkeypatch):
    """No ast-grep backend resolves → the consult warns, does not crash, and
    non-code references are still discovered (graceful degradation)."""
    import safe_move.code_matcher as cm

    monkeypatch.setattr(cm, "_resolve_ast_grep_prefix", lambda: None)
    fix = repo_builder(
        "code-backend-unavailable",
        {
            "src/foo.ts": "export const x = 1;\n",
            "src/a.ts": "import { x } from './foo';\n",
            "note.md": "See [foo](src/foo.ts).\n",
        },
        tracked=["src/foo.ts", "src/a.ts", "note.md"],
    )

    result = build_consult_result("src/foo.ts", "src/bar.ts", scope_root=fix.repo)

    assert any(w["kind"] == "code-backend-unavailable" for w in result["warnings"])
    assert _code_refs(result) == []
    assert any(r["file"] == "note.md" for r in result["references"])
