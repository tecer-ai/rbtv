"""A missing --summary file is a typed refusal, never a raw crash (M2/M4).

Live evidence: `publish_job.py cycle --summary <stale path>` raised an unhandled
`FileNotFoundError` when the path a prior verdict named no longer existed (the
owner had moved the destination folder). The calling agent read that crash as
"the file was deleted" and asked the owner a question on a false premise
(M4) instead of simply re-summarizing. `_file_summarize` must REFUSE cleanly
(`Refused`, caught by `main()`'s own exception handling, `EXIT_REFUSED`) so the
skill can tell "stale reference, re-summarize" apart from an unhandled crash.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H       # noqa: E402
import publish_job as P  # noqa: E402


def test_file_summarize_refuses_a_missing_path_cleanly(tmp_path):
    summarize = P._file_summarize(tmp_path / "does-not-exist.md", None)

    with pytest.raises(P.Refused) as excinfo:
        summarize({"job": {}, "routed": {}, "decision": {}, "discriminator": "0000",
                  "checkout": tmp_path})

    assert "does-not-exist.md" in str(excinfo.value)
    assert "re-run per_meeting_job.py" in str(excinfo.value)


def test_file_summarize_still_reads_a_real_file(tmp_path):
    text_path = tmp_path / "summary.md"
    text_path.write_text("# resumo\n\nbody\n", encoding="utf-8")
    summarize = P._file_summarize(text_path, "notes/offered.md")

    answer = summarize({"job": {}, "routed": {}, "decision": {}, "discriminator": "0000",
                        "checkout": tmp_path})

    assert answer == {"text": "# resumo\n\nbody\n", "path": "notes/offered.md"}


def test_cli_cycle_refuses_instead_of_crashing_on_a_missing_summary(tmp_path):
    """The exact live failure mode: `main(["cycle", ...])` with a stale
    --summary path must exit EXIT_REFUSED, never raise past main()."""
    job_path = tmp_path / "job.json"
    job_path.write_text(
        '{"meeting-key": "mtg-x", "source-set": [{"account": "a@fixture.invalid", '
        '"source": "meet", "drive-ref": "drv:x", "title": "alpha sync", '
        '"start-time": "2026-01-01T10:00:00-03:00", "participants": []}]}',
        encoding="utf-8")
    argv = ["cycle", "--job", str(job_path), "--summary", str(tmp_path / "stale.md"),
           "--config-root", str(H.CONFIG_ROOT),
           "--checkout-root", str(tmp_path / "checkout"), "--state", str(tmp_path / "state")]

    exit_code = P.main(argv)

    assert exit_code == P.EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
