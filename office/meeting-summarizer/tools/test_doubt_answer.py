"""Tests for doubt_answer.py — the owner-doubt ledger with no chat transport.

Isolates the shim's own control flow (ledger reads/writes, the amendment call
sequence) from the real subprocess/git side effects: `per_meeting_job.invoke_agent`
and every `publish_job` git call are monkeypatched, since exercising a real `cast`
launch and a real git remote belongs to the product's own integration suite, not
to a unit test of this shim's orchestration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import doubt_answer  # noqa: E402
import per_meeting_job  # noqa: E402
import publish_job  # noqa: E402


def _write_doubts_row(state: Path, *, meeting_key="m1", entity="tecer",
                      terms=(("Quill", "quill-guess"),)) -> None:
    row = {
        "meeting-key": meeting_key, "entity": entity, "work": str(state / "work" / meeting_key),
        "transcript": "./m1-transcript.md",
        "marker": {
            "summary": {"repo": "tecer-biz", "path": "meetings/2026-09-28-m1.md"},
            "marker-syntax": "{{doubt|term=<term>|guess=<best-guess>}}",
            "doubts": [{"term": term, "guess": guess, "excerpt": f"... {term} ..."}
                      for term, guess in terms],
        },
    }
    (state / "work" / meeting_key).mkdir(parents=True, exist_ok=True)
    per_meeting_job.append_jsonl(state / per_meeting_job.DOUBTS, row)


def test_list_open_reports_unasked_unresolved_doubts(tmp_path):
    state = tmp_path / "state"
    _write_doubts_row(state, meeting_key="m1", terms=(("Quill", "quill-guess"),
                                                       ("Bramble", "bramble-guess")))

    open_doubts = doubt_answer.list_open(state)

    assert {(d["meeting-key"], d["term"]) for d in open_doubts} == {
        ("m1", "Quill"), ("m1", "Bramble")}


def test_list_open_excludes_asked_and_resolved(tmp_path):
    state = tmp_path / "state"
    _write_doubts_row(state, meeting_key="m1", terms=(("Quill", "quill-guess"),
                                                       ("Bramble", "bramble-guess")))
    doubt_answer.mark_asked(state, "m1", "Quill")
    per_meeting_job.append_jsonl(state / doubt_answer.RESOLVED,
                                 {"meeting-key": "m1", "term": "Bramble",
                                  "answer-text": "x", "resolved-at": "t", "published": True})

    assert doubt_answer.list_open(state) == []


def test_apply_answer_refuses_unknown_meeting(tmp_path):
    state = tmp_path / "state"
    result = doubt_answer.apply_answer(
        meeting_key="ghost", term="Quill", answer_text="Quill is correct",
        config_root=tmp_path / "config", checkout_root=tmp_path / "checkout", state=state)
    assert result["landed"] is False
    assert "no doubts handoff row" in result["why"]


def test_apply_answer_lands_and_records_resolution(tmp_path, monkeypatch):
    state = tmp_path / "state"
    checkout_root = tmp_path / "checkout"
    config_root = tmp_path / "config"
    _write_doubts_row(state, meeting_key="m1", terms=(("Quill", "quill-guess"),))

    summary = checkout_root / "tecer-biz" / "meetings" / "2026-09-28-m1.md"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("Summary text with {{doubt|term=Quill|guess=quill-guess}}.\n",
                       encoding="utf-8")

    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / "summarize.json").write_text(json.dumps({
        "artifact-kinds": {}, "skill-bindings": {"by-entity": {"tecer": "workflow.md"}},
        "invocation": {"harness": "claude", "model": "sonnet", "effort": "low"},
    }), encoding="utf-8")

    landed_state = {"applied": False}

    def fake_invoke_agent(prompt, cwd, log_dir, timeout, invocation):
        landed_state["applied"] = True
        summary.write_text("Summary text with Quill correctly named.\n", encoding="utf-8")
        return {"exit": 0, "text": "ok"}

    monkeypatch.setattr(per_meeting_job, "invoke_agent", fake_invoke_agent)
    monkeypatch.setattr(publish_job, "load_targets",
                        lambda config_root: {"targets": {"tecer-biz": {
                            "regime": "git", "remote": "origin", "branch": "main"}},
                            "discriminator": {"format": "%Y-%m-%d"}})
    monkeypatch.setattr(publish_job, "sync", lambda target, checkout: {"fetched": True})
    monkeypatch.setattr(publish_job, "dirty_paths", lambda checkout: set())
    monkeypatch.setattr(publish_job, "commit",
                        lambda target, checkout, paths, message: {"committed": True, "head": "abc123"})
    monkeypatch.setattr(publish_job, "head_unpublished", lambda target, checkout: "abc123")
    push_calls = []
    monkeypatch.setattr(publish_job, "push",
                        lambda target, checkout, own: push_calls.append(own) or
                        {"pushed": True, "via": "direct"})

    import contextlib
    monkeypatch.setattr(publish_job, "checkout_lock",
                        lambda checkout: contextlib.nullcontext())

    result = doubt_answer.apply_answer(
        meeting_key="m1", term="Quill", answer_text="Quill is correct",
        config_root=config_root, checkout_root=checkout_root, state=state)

    assert landed_state["applied"] is True
    assert result["landed"] is True
    assert result["published"]["pushed"] is True
    assert push_calls == [["abc123"]]  # push was actually reached, not the already-current path
    resolved = per_meeting_job.read_jsonl(state / doubt_answer.RESOLVED)
    assert resolved == [{"meeting-key": "m1", "term": "Quill", "answer-text": "Quill is correct",
                         "resolved-at": resolved[0]["resolved-at"], "published": True}]


def test_apply_answer_does_not_record_when_marker_survives(tmp_path, monkeypatch):
    state = tmp_path / "state"
    checkout_root = tmp_path / "checkout"
    config_root = tmp_path / "config"
    _write_doubts_row(state, meeting_key="m1", terms=(("Quill", "quill-guess"),))

    summary = checkout_root / "tecer-biz" / "meetings" / "2026-09-28-m1.md"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("Summary text with {{doubt|term=Quill|guess=quill-guess}}.\n",
                       encoding="utf-8")

    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / "summarize.json").write_text(json.dumps({
        "artifact-kinds": {}, "skill-bindings": {"by-entity": {"tecer": "workflow.md"}},
        "invocation": {"harness": "claude", "model": "sonnet", "effort": "low"},
    }), encoding="utf-8")

    # The invocation reports success but never touches the file — the marker survives.
    monkeypatch.setattr(per_meeting_job, "invoke_agent",
                        lambda prompt, cwd, log_dir, timeout, invocation: {"exit": 0, "text": "ok"})
    monkeypatch.setattr(publish_job, "load_targets",
                        lambda config_root: {"targets": {"tecer-biz": {
                            "regime": "git", "remote": "origin", "branch": "main"}},
                            "discriminator": {"format": "%Y-%m-%d"}})
    monkeypatch.setattr(publish_job, "sync", lambda target, checkout: {"fetched": True})
    monkeypatch.setattr(publish_job, "dirty_paths", lambda checkout: set())
    import contextlib
    monkeypatch.setattr(publish_job, "checkout_lock",
                        lambda checkout: contextlib.nullcontext())

    result = doubt_answer.apply_answer(
        meeting_key="m1", term="Quill", answer_text="Quill is correct",
        config_root=config_root, checkout_root=checkout_root, state=state)

    assert result["landed"] is False
    assert "still in the summary" in result["why"]
    assert per_meeting_job.read_jsonl(state / doubt_answer.RESOLVED) == []


def test_apply_answer_treats_nothing_to_commit_as_already_published(tmp_path, monkeypatch):
    """The sibling of publish_job.py's M1/M2 bug: a correction whose bytes
    already match the fetched remote (this correction was already committed
    and pushed by an earlier, interrupted `apply`) must land as published, not
    be silently re-pushed or reported as a failure — and `push()` must not be
    called at all, since there is nothing local ahead of the remote."""
    state = tmp_path / "state"
    checkout_root = tmp_path / "checkout"
    config_root = tmp_path / "config"
    _write_doubts_row(state, meeting_key="m1", terms=(("Quill", "quill-guess"),))

    summary = checkout_root / "tecer-biz" / "meetings" / "2026-09-28-m1.md"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text("Summary text with {{doubt|term=Quill|guess=quill-guess}}.\n",
                       encoding="utf-8")

    config_root.mkdir(parents=True, exist_ok=True)
    (config_root / "summarize.json").write_text(json.dumps({
        "artifact-kinds": {}, "skill-bindings": {"by-entity": {"tecer": "workflow.md"}},
        "invocation": {"harness": "claude", "model": "sonnet", "effort": "low"},
    }), encoding="utf-8")

    def fake_invoke_agent(prompt, cwd, log_dir, timeout, invocation):
        summary.write_text("Summary text with Quill correctly named.\n", encoding="utf-8")
        return {"exit": 0, "text": "ok"}

    monkeypatch.setattr(per_meeting_job, "invoke_agent", fake_invoke_agent)
    monkeypatch.setattr(publish_job, "load_targets",
                        lambda config_root: {"targets": {"tecer-biz": {
                            "regime": "git", "remote": "origin", "branch": "main"}},
                            "discriminator": {"format": "%Y-%m-%d"}})
    monkeypatch.setattr(publish_job, "sync", lambda target, checkout: {"fetched": True})
    monkeypatch.setattr(publish_job, "dirty_paths", lambda checkout: set())
    monkeypatch.setattr(publish_job, "commit",
                        lambda target, checkout, paths, message: {"committed": False})
    monkeypatch.setattr(publish_job, "head_unpublished", lambda target, checkout: None)
    push_calls = []
    monkeypatch.setattr(publish_job, "push",
                        lambda target, checkout, own: push_calls.append(own) or
                        {"pushed": True, "via": "direct"})

    import contextlib
    monkeypatch.setattr(publish_job, "checkout_lock",
                        lambda checkout: contextlib.nullcontext())

    result = doubt_answer.apply_answer(
        meeting_key="m1", term="Quill", answer_text="Quill is correct",
        config_root=config_root, checkout_root=checkout_root, state=state)

    assert result["landed"] is True
    assert result["published"] == {"pushed": True, "via": "already-current"}
    assert push_calls == []  # push() is never called when nothing is ahead of the remote
    resolved = per_meeting_job.read_jsonl(state / doubt_answer.RESOLVED)
    assert resolved[0]["published"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
