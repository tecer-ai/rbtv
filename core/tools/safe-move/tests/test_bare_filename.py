"""Exercises for the unique-bare-filename matcher (2026-06-19).

The defect: a UNIQUE bare filename (a name carrying an extension, NO path
separator) referenced as a backtick span name.md or as a bare name.md in plain
prose was MISSED — a false-clean rename that left dead references behind. The
frontmatter matcher already treats a bare ``x.md`` as a file reference; this
mirrors that rule into the inline-code and prose matchers, gated on the basename
resolving to exactly one scope file (the basename-collision guard).

Pins:
  * unique bare filename surfaced as a backtick span (inline-code-basename) and as
    a bare token in prose (prose-filename), each with a correct proposed;
  * ZERO false positives: a colliding basename is left unmatched; a non-path
    backtick word (``npx``) is never matched;
  * the surfaced refs apply correctly on ``act`` (round-trip).
"""

from __future__ import annotations

from safe_move import classify
from safe_move.cli import main
from safe_move.consult import build_consult_result


def _refs(consulted):
    return consulted["references"]


def test_unique_bare_filename_surfaced_inline_code_and_prose(repo_builder):
    files = {
        "A/uniq-name.md": "# the moved file\n",
        "A/index.md": "# index\n",
        # Backtick basename, no separator.
        "C/ref.md": "see `uniq-name.md` for details\n",
        # Bare filename in plain prose, no backticks, no separator.
        "C/notes.md": "keep uniq-name.md (the live one) around\n",
    }
    fix = repo_builder("bare-unique", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "uniq-name.md"),
        str(fix.repo / "A" / "renamed.md"),
        scope_root=str(fix.repo),
    )
    rows = {(r["file"], r["syntax"]): r for r in _refs(consulted)}

    inline = rows.get(("C/ref.md", "inline-code-basename"))
    assert inline is not None
    assert inline["class"] == classify.CLASS_SURFACE
    assert inline["match"] == "uniq-name.md"
    assert inline["proposed"] == "renamed.md"

    prose = rows.get(("C/notes.md", "prose-filename"))
    assert prose is not None
    assert prose["class"] == classify.CLASS_SURFACE
    assert prose["match"] == "uniq-name.md"
    assert prose["proposed"] == "renamed.md"


def test_colliding_basename_is_left_unmatched(repo_builder):
    # Two files share the basename -> a bare reference is ambiguous and must be
    # left unmatched (zero false positives), as before this fix.
    files = {
        "A/dup.md": "# A copy\n",
        "B/dup.md": "# B copy\n",
        "C/ref.md": "see `dup.md` and bare dup.md here\n",
    }
    fix = repo_builder("bare-collision", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "dup.md"),
        str(fix.repo / "A" / "dup-renamed.md"),
        scope_root=str(fix.repo),
    )
    bare = [
        r
        for r in _refs(consulted)
        if r["syntax"] in ("inline-code-basename", "prose-filename")
    ]
    assert bare == []


def test_non_path_backtick_word_is_not_matched(repo_builder):
    # A backtick word with no extension (a command) is never a bare filename, even
    # when a scope file happens to share its stem.
    files = {
        "A/npx.md": "# unrelated file whose stem is npx\n",
        "C/ref.md": "run `npx` to start; also a bare npx token\n",
    }
    fix = repo_builder("bare-npx", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "npx.md"),
        str(fix.repo / "A" / "npx-renamed.md"),
        scope_root=str(fix.repo),
    )
    bare = [
        r
        for r in _refs(consulted)
        if r["syntax"] in ("inline-code-basename", "prose-filename")
    ]
    assert bare == []


def test_path_form_not_double_counted_as_bare(repo_builder):
    # An inline-code path WITH a separator is the inline-code-PATH matcher's job;
    # the bare matcher must not also count its tail basename.
    files = {
        "A/uniq-name.md": "# moved\n",
        "C/ref.md": "see `A/uniq-name.md` here\n",
    }
    fix = repo_builder("bare-nodup", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "uniq-name.md"),
        str(fix.repo / "A" / "renamed.md"),
        scope_root=str(fix.repo),
    )
    syntaxes = sorted(r["syntax"] for r in _refs(consulted) if r["file"] == "C/ref.md")
    # Exactly one reference for that file: the inline-code PATH, never a bare twin.
    assert syntaxes == ["inline-code-path"]


def test_bare_filename_refs_apply_on_act(repo_builder):
    files = {
        "A/uniq-name.md": "# moved\n",
        "C/ref.md": "see `uniq-name.md` and bare uniq-name.md too\n",
    }
    fix = repo_builder("bare-apply", files, tracked=list(files))
    old = str(fix.repo / "A" / "uniq-name.md")
    new = str(fix.repo / "A" / "renamed.md")

    consulted = build_consult_result(old, new, scope_root=str(fix.repo))
    apply_pairs = ",".join(
        f"{r['id']}:{r['hash']}"
        for r in _refs(consulted)
        if r["syntax"] in ("inline-code-basename", "prose-filename")
    )
    assert apply_pairs  # both surfaced refs exist

    code = main(
        ["act", old, new, "--apply", apply_pairs, "--scope-root", str(fix.repo)]
    )
    assert code == 0

    after = (fix.repo / "C" / "ref.md").read_text(encoding="utf-8")
    assert after == "see `renamed.md` and bare renamed.md too\n"
    # The file actually moved.
    assert (fix.repo / "A" / "renamed.md").exists()
    assert not (fix.repo / "A" / "uniq-name.md").exists()


def test_pure_move_keeps_bare_basename_unchanged(repo_builder):
    # A pure move (dir change, same name) leaves the basename — and the reference —
    # unchanged: the bare ref is surfaced with proposed == match (no edit).
    files = {
        "A/uniq-name.md": "# moved\n",
        "C/ref.md": "see `uniq-name.md` here\n",
    }
    fix = repo_builder("bare-puremove", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "uniq-name.md"),
        str(fix.repo / "B" / "uniq-name.md"),
        scope_root=str(fix.repo),
    )
    inline = [
        r for r in _refs(consulted) if r["syntax"] == "inline-code-basename"
    ]
    assert len(inline) == 1
    assert inline[0]["class"] == classify.CLASS_SURFACE
    assert inline[0]["proposed"] == inline[0]["match"] == "uniq-name.md"


def test_bare_filename_in_log_line_is_protected(repo_builder):
    # A bare filename inside a blockquote (a recorded line) is protected, never
    # edited — the classifier's protected-region rule applies to the new syntaxes.
    files = {
        "A/uniq-name.md": "# moved\n",
        "C/ref.md": "> historical: uniq-name.md was the old name\n",
    }
    fix = repo_builder("bare-protected", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "A" / "uniq-name.md"),
        str(fix.repo / "A" / "renamed.md"),
        scope_root=str(fix.repo),
    )
    prose = [r for r in _refs(consulted) if r["syntax"] == "prose-filename"]
    assert len(prose) == 1
    assert prose[0]["class"] == classify.CLASS_PROTECTED
