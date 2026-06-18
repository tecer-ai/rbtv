"""Tests for the code-reference precision line (auto vs surface)."""

from __future__ import annotations

from safe_move.classify import CLASS_AUTO, CLASS_SURFACE
from safe_move.consult import build_consult_result


def _code_refs(result: dict) -> list[dict]:
    return [r for r in result["references"] if r["syntax"] == "code-import"]


def test_static_single_target_import_is_auto(repo_builder):
    fix = repo_builder(
        "code-static-auto",
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
    assert refs[0]["match"] == "./foo"
    assert refs[0]["proposed"] == "./bar"
    assert refs[0]["class"] == CLASS_AUTO


def test_python_relative_import_is_auto(repo_builder):
    fix = repo_builder(
        "code-python-auto",
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
    assert refs[0]["match"] == ".foo"
    assert refs[0]["proposed"] == ".bar"
    assert refs[0]["class"] == CLASS_AUTO


def test_folder_move_static_import_is_auto(repo_builder):
    fix = repo_builder(
        "code-folder-auto",
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


def test_ambiguous_same_basename_is_surface(repo_builder):
    # Two files share the specifier basename; resolves_to > 1.
    fix = repo_builder(
        "code-ambiguous",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/foo.js": "module.exports.foo = 1;\n",
            "src/a.ts": "import { foo } from './foo';\n",
        },
        tracked=["src/foo.ts", "src/foo.js", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["match"] == "./foo"
    assert refs[0]["class"] == CLASS_SURFACE


def test_literal_dynamic_import_is_surfaced(repo_builder):
    fix = repo_builder(
        "code-dynamic-surfaced",
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
    assert any(
        w["kind"] == "code-dynamic-import" and w["ref_id"] == refs[0]["id"]
        for w in result["warnings"]
    )


def test_path_alias_import_is_surfaced_with_unresolved_warning(repo_builder):
    fix = repo_builder(
        "code-alias-surface",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "import { foo } from '@app/foo';\n",
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
    assert refs[0]["match"] == "@app/foo"
    assert refs[0]["class"] == CLASS_SURFACE
    assert any(
        w["kind"] == "code-unresolved-import" and w["ref_id"] == refs[0]["id"]
        for w in result["warnings"]
    )


def test_string_built_path_is_not_emitted(repo_builder):
    fix = repo_builder(
        "code-string-built-not-emitted",
        {
            "src/foo.ts": "export const foo = 1;\n",
            "src/a.ts": "const mod = './fo' + 'o';\n",
        },
        tracked=["src/foo.ts", "src/a.ts"],
    )

    result = build_consult_result(
        "src/foo.ts",
        "src/bar.ts",
        scope_root=fix.repo,
    )

    assert _code_refs(result) == []


def test_regex_only_string_mention_is_not_emitted(repo_builder):
    fix = repo_builder(
        "code-string-mention-not-emitted",
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

    assert _code_refs(result) == []


def test_read_only_code_reference_is_surface(repo_builder):
    fix = repo_builder(
        "code-readonly-surface",
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
        read_only=["src/a.ts"],
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["class"] == CLASS_SURFACE


def test_generated_code_reference_is_surface(repo_builder):
    fix = repo_builder(
        "code-generated-surface",
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
        generated=["src/a.ts"],
    )

    refs = _code_refs(result)
    assert len(refs) == 1
    assert refs[0]["class"] == CLASS_SURFACE


def test_unsupported_language_emits_warning_and_no_code_ref(repo_builder):
    fix = repo_builder(
        "code-unsupported",
        {
            "src/foo.swift": "let foo = 1\n",
            "src/a.swift": "import foo\n",
        },
        tracked=["src/foo.swift", "src/a.swift"],
    )

    result = build_consult_result(
        "src/foo.swift",
        "src/bar.swift",
        scope_root=fix.repo,
    )

    assert _code_refs(result) == []
    kinds = {w["kind"] for w in result["warnings"]}
    assert "code-unsupported-language" in kinds
