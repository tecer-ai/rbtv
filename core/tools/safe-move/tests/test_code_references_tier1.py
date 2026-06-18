"""Tier-1 end-to-end fixtures for the code-reference precision line + D8 surfacing.

These fixtures exercise real ast-grep against real source files in a fresh git
repo. They cover the matrix from the code-references spec reconciled with the
D8 owner ruling: static single-target imports auto-fix end-to-end, unresolved
static imports whose basename matches the target are surfaced with a warning,
truly opaque dynamic imports stay undetectable, and string-only / unsupported
references are never auto-edited.
"""

from __future__ import annotations

from safe_move.act import run_act
from safe_move.classify import CLASS_AUTO, CLASS_SURFACE
from safe_move.consult import build_consult_result


def _code_refs(result: dict) -> list[dict]:
    return [r for r in result["references"] if r["syntax"] == "code-import"]


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def test_static_single_target_import_auto_fixes_end_to_end(repo_builder):
    """Row 1: a static relative import is classed auto and act rewrites it."""
    fix = repo_builder(
        "tier1-static-auto",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "./foo"
    assert refs[0]["proposed"] == "./bar"
    assert refs[0]["class"] == CLASS_AUTO

    result = run_act(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
        apply=_apply_string(refs),
    )
    assert result.exit_code == 0
    assert not (fix.repo / "src" / "foo.ts").exists()
    assert (fix.repo / "src" / "bar.ts").read_text(encoding="utf-8") == (
        "export const foo = 1;\n"
    )
    assert (fix.repo / "src" / "a.ts").read_text(encoding="utf-8") == (
        "import { foo } from './bar';\n"
    )


def test_path_alias_import_surfaces_with_code_unresolved_warning(repo_builder):
    """Row 2 (D8): a path-alias import whose basename matches the target surfaces."""
    fix = repo_builder(
        "tier1-alias-surface",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from '@app/foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "@app/foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""

    warning = next(
        (w for w in consulted["warnings"] if w["kind"] == "code-unresolved-import"),
        None,
    )
    assert warning is not None
    assert warning["file"] == "src/a.ts"
    assert warning["ref_id"] == refs[0]["id"]


def test_bare_package_import_surfaces_with_code_unresolved_warning(repo_builder):
    """Row 3 (D8): a bare/package import whose basename matches the target surfaces."""
    fix = repo_builder(
        "tier1-package-surface",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from 'my-pkg/foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "my-pkg/foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""

    warning = next(
        (w for w in consulted["warnings"] if w["kind"] == "code-unresolved-import"),
        None,
    )
    assert warning is not None
    assert warning["file"] == "src/a.ts"
    assert warning["ref_id"] == refs[0]["id"]


def test_python_absolute_import_is_surface_and_not_rewritten(repo_builder):
    """D9 safety fix: a Python dotted absolute import never reaches auto."""
    fix = repo_builder(
        "tier1-python-absolute-surface",
        {
            "pkg/__init__.py": "",
            "pkg/foo.py": "VALUE = 1\n",
            "main.py": "from pkg.foo import VALUE\n",
        },
        tracked=["pkg/__init__.py", "pkg/foo.py", "main.py"],
    )

    consulted = build_consult_result(
        "pkg/foo.py", "pkg/bar.py", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert len(refs) == 1
    assert refs[0]["file"] == "main.py"
    assert refs[0]["match"] == "pkg.foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""
    assert any(
        w["kind"] == "code-unresolved-import" and w["ref_id"] == refs[0]["id"]
        for w in consulted["warnings"]
    )

    result = run_act(
        "pkg/foo.py",
        "pkg/bar.py",
        scope_root=fix.repo,
        apply="",
    )
    assert result.exit_code == 0
    assert (fix.repo / "pkg" / "bar.py").read_text(encoding="utf-8") == (
        "VALUE = 1\n"
    )
    assert (fix.repo / "main.py").read_text(encoding="utf-8") == (
        "from pkg.foo import VALUE\n"
    )
    assert "pkg/bar.py" not in (fix.repo / "main.py").read_text(encoding="utf-8")


def test_literal_dynamic_import_is_surface_and_not_rewritten(repo_builder):
    """D9 completeness fix: a literal dynamic import is surfaced, never auto."""
    fix = repo_builder(
        "tier1-dynamic-literal-surface",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const m = import('./foo');\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert len(refs) == 1
    assert refs[0]["file"] == "src/a.ts"
    assert refs[0]["match"] == "./foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert refs[0]["proposed"] == ""
    assert any(
        w["kind"] == "code-dynamic-import" and w["ref_id"] == refs[0]["id"]
        for w in consulted["warnings"]
    )

    result = run_act(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
        apply="",
    )
    assert result.exit_code == 0
    assert not (fix.repo / "src" / "foo.ts").exists()
    assert (fix.repo / "src" / "bar.ts").read_text(encoding="utf-8") == (
        "export const foo = 1;\n"
    )
    assert (fix.repo / "src" / "a.ts").read_text(encoding="utf-8") == (
        "const m = import('./foo');\n"
    )


def test_dynamic_import_with_variable_is_undetectable_and_not_surfaced(repo_builder):
    """Row 4: a dynamic import(expr) carries no static specifier — not surfaced."""
    fix = repo_builder(
        "tier1-dynamic-variable",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const mod = './foo';\nconst load = () => import(mod);\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    refs = _code_refs(consulted)
    assert refs == []
    # Documented limitation: the static matcher cannot tie a variable import to
    # the moved file, so the reference is correctly left for the agent to review.


def test_string_only_mention_is_not_code_reference_and_not_edited(repo_builder):
    """Row 5: a string literal mentioning the path is not a code reference."""
    fix = repo_builder(
        "tier1-string-mention",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const path = './foo';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    consulted = build_consult_result(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo
    )
    assert _code_refs(consulted) == []

    result = run_act(
        "src/foo.ts", "src/bar.ts", scope_root=fix.repo, apply=""
    )
    assert result.exit_code == 0
    assert (fix.repo / "src" / "a.ts").read_text(encoding="utf-8") == (
        "const path = './foo';\n"
    )


def test_unsupported_language_reference_surfaces_with_warning(repo_builder):
    """Row 6: a reference in an unsupported code language surfaces + warns."""
    fix = repo_builder(
        "tier1-unsupported",
        {
            "src/foo.swift": "let foo = 1\n",
            "src/a.swift": "import foo\n",
        },
        tracked=["src/foo.swift", "src/a.swift"],
    )

    consulted = build_consult_result(
        "src/foo.swift", "src/bar.swift", scope_root=fix.repo
    )
    assert _code_refs(consulted) == []
    kinds = {w["kind"] for w in consulted["warnings"]}
    assert "code-unsupported-language" in kinds

    result = run_act(
        "src/foo.swift", "src/bar.swift", scope_root=fix.repo, apply=""
    )
    assert result.exit_code == 0
    assert (fix.repo / "src" / "a.swift").read_text(encoding="utf-8") == (
        "import foo\n"
    )
