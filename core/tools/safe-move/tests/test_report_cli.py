"""Report-file + summary + show surface: the agent-facing CLI contract."""

import json

from safe_move.cli import main


def _consult_files():
    return {
        "old.md": "old\n",
        "note.md": "See [[old]].\n",
        "prose.md": "mentions `old.md` in a span\n",
    }


def _run_consult(fix, capsys, *extra):
    code = main(
        [
            "consult",
            str(fix.repo / "old.md"),
            str(fix.repo / "new.md"),
            "--scope-root",
            str(fix.repo),
            *extra,
        ]
    )
    return code, capsys.readouterr()


def _report_path_from(stdout: str) -> str:
    lines = [ln for ln in stdout.splitlines() if ln.startswith("report: ")]
    assert len(lines) == 1, stdout
    return lines[0].removeprefix("report: ")


def test_consult_default_writes_report_and_prints_summary(repo_builder, capsys):
    fix = repo_builder("report-consult", _consult_files(), tracked=list(_consult_files()))

    code, captured = _run_consult(fix, capsys)
    assert code == 0

    out = captured.out
    # Compact summary, not the raw envelope.
    assert not out.lstrip().startswith("{")
    assert "references:" in out
    assert "move method:" in out

    # Surface records print inline as ready-to-paste id:hash pairs.
    assert "surface (pass id:hash to act --apply to also fix):" in out
    assert "ref-" in out and ":" in out

    # Report file exists at {repo}/.rbtv/runtime/safe-move/ and holds the envelope.
    report_path = _report_path_from(out)
    payload = json.loads(open(report_path, encoding="utf-8").read())
    assert payload["tool"] == "safe-move"
    assert payload["subcommand"] == "consult"
    assert set(payload["result"]) >= {"references", "warnings", "git_move_method"}
    assert str(fix.repo / ".rbtv" / "runtime" / "safe-move") in report_path.replace(
        "/", "\\"
    ) or "/.rbtv/runtime/safe-move/" in report_path.replace("\\", "/")

    # The runtime dir self-gitignores.
    gitignore = fix.repo / ".rbtv" / "runtime" / ".gitignore"
    assert gitignore.read_text(encoding="utf-8").strip() == "*"


def test_consult_json_flag_prints_envelope_and_writes_nothing(repo_builder, capsys):
    fix = repo_builder("report-json", _consult_files(), tracked=list(_consult_files()))

    code, captured = _run_consult(fix, capsys, "--json")
    assert code == 0
    payload = json.loads(captured.out)
    assert set(payload) == {"git_move_method", "references", "warnings", "folder_cascade"}
    assert not (fix.repo / ".rbtv").exists()


def test_show_slices_report(repo_builder, capsys):
    fix = repo_builder("report-show", _consult_files(), tracked=list(_consult_files()))
    _, captured = _run_consult(fix, capsys)
    report_path = _report_path_from(captured.out)

    # --class returns full records of that class only.
    code = main(["show", report_path, "--class", "surface"])
    out = capsys.readouterr().out
    assert code == 0
    records = json.loads(out)
    assert records and all(r["class"] == "surface" for r in records)
    assert {"id", "file", "line", "match", "proposed", "hash"} <= set(records[0])

    # --id returns exactly that record.
    ref_id = records[0]["id"]
    code = main(["show", report_path, "--id", ref_id])
    got = json.loads(capsys.readouterr().out)
    assert code == 0
    assert [r["id"] for r in got] == [ref_id]

    # Unknown id is an error, never an empty success.
    code = main(["show", report_path, "--id", "ref-9999"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ref-9999" in captured.err

    # No filters re-prints the summary.
    code = main(["show", report_path])
    out = capsys.readouterr().out
    assert code == 0
    assert "references:" in out

    # --warnings prints the warnings list as JSON.
    code = main(["show", report_path, "--warnings"])
    out = capsys.readouterr().out
    assert code == 0
    assert isinstance(json.loads(out), list)


def test_act_default_writes_report_and_compact_log(repo_builder, capsys):
    fix = repo_builder("report-act", _consult_files(), tracked=list(_consult_files()))

    code = main(
        [
            "act",
            str(fix.repo / "old.md"),
            str(fix.repo / "new.md"),
            "--apply",
            "",
            "--scope-root",
            str(fix.repo),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0

    out = captured.out
    assert "moved: old.md -> new.md" in out
    # Auto fixes collapse to a count; surfaced rows stay inline.
    assert "auto-fixed: " in out
    assert "surfaced (yours to resolve):" in out

    report_path = _report_path_from(out)
    payload = json.loads(open(report_path, encoding="utf-8").read())
    assert payload["subcommand"] == "act"
    assert payload["result"]["moved"]["method"] in ("git mv", "mv")

    # An act report still answers show (summary + warnings; record filters error).
    code = main(["show", report_path])
    assert code == 0
    assert "moved:" in capsys.readouterr().out
    code = main(["show", report_path, "--class", "surface"])
    captured = capsys.readouterr()
    assert code == 1
    assert "act report" in captured.err
