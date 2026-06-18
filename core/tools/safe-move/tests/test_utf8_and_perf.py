"""Regression tests for two real-corpus defects (rbtv-safe-move-tasks.md):

* BUG — ``consult``/``act`` crashed with ``UnicodeDecodeError`` on any non-UTF-8
  file in the scan scope.
* BUG/PERF — folder ``consult``/``act`` re-scanned the haystack and re-invoked
  ast-grep once per contained file, making real folder moves take minutes.

These tests also serve as the done-gate seams for the criteria that are not
observable from the CLI output: the ast-grep invocation count (C4) and the
once-per-run file-read count (C5).
"""

from __future__ import annotations

import subprocess
from collections import Counter

from safe_move.consult import build_consult_result
from safe_move.scope import walk_scope


# ---------------------------------------------------------------------------
# BUG: non-UTF-8 / binary files must not crash the scan (C1, C2)
# ---------------------------------------------------------------------------

def test_consult_ignores_binary_and_non_utf8_files(repo_builder):
    """A binary file and a non-UTF-8 text file in scope: no crash, both ignored."""
    fix = repo_builder(
        "utf8-safety",
        {
            "docs/old.md": "old\n",
            "note.md": "See [[old]] and [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    # Binary file with NUL bytes early — caught by the walk-time binary filter.
    (fix.repo / "image.png").write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    )
    # NUL-free, non-UTF-8 (Windows-1252) text: bytes 0xE9 ("é") and 0x97 ("—")
    # are invalid UTF-8. This slipped past the NUL filter and crashed the
    # matcher's read_text(encoding="utf-8") before the fix.
    (fix.repo / "win1252.txt").write_bytes("café — old notes\n".encode("cp1252"))

    # Must not raise UnicodeDecodeError.
    result = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)

    ref_files = {ref["file"] for ref in result["references"]}
    # The legitimate references are still found.
    assert "note.md" in ref_files
    # Neither the binary nor the non-UTF-8 file is ever a reference candidate.
    assert "image.png" not in ref_files
    assert "win1252.txt" not in ref_files

    # The NUL-free non-UTF-8 file is surfaced via ONE aggregated warning (the
    # PNG was filtered silently at walk time, so it is not in the warning).
    non_utf8 = [w for w in result["warnings"] if w["kind"] == "non-utf8-skipped"]
    assert len(non_utf8) == 1
    assert "win1252.txt" in non_utf8[0]["message"]
    assert non_utf8[0]["file"] is None and non_utf8[0]["ref_id"] is None


def test_walk_then_consult_no_excludes_needed_for_binaries(repo_builder):
    """consult completes with NO --exclude flags despite binary/non-UTF-8 files."""
    fix = repo_builder(
        "utf8-no-excludes",
        {"a/old.md": "old\n", "ref.md": "[[old]]\n"},
        tracked=["a/old.md", "ref.md"],
    )
    (fix.repo / "blob.bin").write_bytes(bytes(range(256)) * 4)  # has NUL
    (fix.repo / "latin.log").write_bytes(b"erro: \xe7\xe3o invalida\n")  # NUL-free, non-UTF-8

    # No exclude= argument at all — the whole point of the fix.
    result = build_consult_result("a/old.md", "a/new.md", scope_root=fix.repo)
    assert any(r["file"] == "ref.md" for r in result["references"])


# ---------------------------------------------------------------------------
# BUG/PERF: scan the haystack once, invoke ast-grep O(languages) (C4, C5)
# ---------------------------------------------------------------------------

def test_folder_consult_invokes_ast_grep_once_per_language_not_per_file(
    repo_builder, monkeypatch
):
    """A folder move must invoke ast-grep O(languages x patterns), not O(files)."""
    import safe_move.code_matcher as cm

    files = {f"pkg/m{i}.ts": f"export const x{i} = {i};\n" for i in range(8)}
    files["app.ts"] = "import a from './pkg/m0';\n"
    fix = repo_builder("perf-astgrep", files, tracked=list(files))

    calls: list[list[str]] = []

    class FakeSubprocess:
        def run(self, cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="[]", stderr=""
            )

    monkeypatch.setattr(cm, "_find_npx", lambda: "npx")
    monkeypatch.setattr(cm, "subprocess", FakeSubprocess())

    build_consult_result("pkg", "renamed", scope_root=fix.repo)

    num_sub_targets = 1 + 8  # the folder path + its 8 contained files
    per_scan = len(cm.LANGUAGE_PATTERNS["ts"]) + len(
        cm.DYNAMIC_LANGUAGE_PATTERNS.get("ts", [])
    )
    # ast-grep runs once per (pattern x chunk) for the whole scan — short paths
    # fit one chunk; allow two chunks of margin.
    assert len(calls) <= per_scan * 2
    # A per-sub-target engine would invoke it num_sub_targets x more.
    assert len(calls) < num_sub_targets * per_scan


def test_folder_consult_reads_each_file_once(repo_builder, monkeypatch):
    """A folder move must read each scoped file exactly once, not once per sub-target."""
    import safe_move.scope as scope_mod

    files = {
        "pkg/a.md": "# A\n",
        "pkg/b.md": "# B\n",
        "pkg/c.md": "# C\n",
        "ref1.md": "See [the folder](pkg).\n",
        "ref2.md": "Link [[a]] and [[b]].\n",
        "ref3.md": "Unrelated text.\n",
    }
    fix = repo_builder("perf-reads", files, tracked=list(files))

    reads: list[str] = []
    original = scope_mod.read_text_safe

    def counting_read(path):
        reads.append(path.as_posix())
        return original(path)

    monkeypatch.setattr(scope_mod, "read_text_safe", counting_read)

    build_consult_result("pkg", "renamed", scope_root=fix.repo)

    scoped = list(walk_scope(fix.repo))
    counts = Counter(reads)
    # Every scoped file read exactly once despite the move expanding to four
    # sub-targets (the folder + its three files).
    assert all(n == 1 for n in counts.values()), counts
    assert len(counts) == len(scoped)
