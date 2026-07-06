import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).parent
FIXTURE = TOOLS_DIR / "fixtures" / "write-deck.html"


def playwright_available():
    return importlib.util.find_spec("playwright") is not None


def copy_fixture(tmp_path, name):
    dst = tmp_path / name
    shutil.copy(FIXTURE, dst)
    return dst


def run_cmd(*args):
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=TOOLS_DIR.parent,
        text=True,
        capture_output=True,
        timeout=30,
    )


def parse_json(stdout):
    return json.loads(stdout)


def normalize_add_comment(payload):
    normalized = dict(payload)
    normalized["file"] = "<file>"
    normalized["comment_id"] = "<generated>"
    anchor = dict(normalized["anchor"])
    for key in ("contentHash", "path", "siblingIndex"):
        if key in anchor:
            anchor[key] = "<generated>"
    normalized["anchor"] = anchor
    return normalized


def normalize_reply(payload):
    normalized = dict(payload)
    normalized["file"] = "<file>"
    return normalized


def assert_success(proc):
    assert proc.returncode == 0, proc.stderr
    payload = parse_json(proc.stdout)
    assert payload["ok"] is True
    return payload


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_add_comment_matches_legacy_fields_and_saves_runtime_island(tmp_path):
    legacy_file = copy_fixture(tmp_path, "legacy-add.html")
    cli_file = copy_fixture(tmp_path, "cli-add.html")

    legacy = run_cmd(
        "tools/add_comment.py",
        "--file",
        legacy_file,
        "--selector",
        "#target-copy",
        "--body",
        "Tighten this copy.",
        "--author",
        "Vivian",
        "--agent",
    )
    new = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        cli_file,
        "--selector",
        "#target-copy",
        "--body",
        "Tighten this copy.",
        "--author",
        "Vivian",
        "--agent",
    )

    legacy_payload = assert_success(legacy)
    new_payload = assert_success(new)
    assert set(new_payload) == {
        "ok",
        "file",
        "comment_id",
        "author",
        "agentInstruction",
        "anchor",
        "anchored",
        "marker_rendered",
        "contextText",
    }
    assert normalize_add_comment(new_payload) == normalize_add_comment(legacy_payload)
    assert 'id="hyp-comments"' in cli_file.read_text(encoding="utf-8")


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_reply_matches_legacy_fields_and_saves_runtime_island(tmp_path):
    legacy_file = copy_fixture(tmp_path, "legacy-reply.html")
    cli_file = copy_fixture(tmp_path, "cli-reply.html")

    legacy = run_cmd(
        "tools/reply_comment.py",
        "--file",
        legacy_file,
        "--comment-id",
        "c-existing",
        "--reply",
        "Working on it.",
        "--author",
        "Agent",
        "--set-agent",
    )
    new = run_cmd(
        "tools/hypresent.py",
        "reply",
        "--file",
        cli_file,
        "--comment-id",
        "c-existing",
        "--reply",
        "Working on it.",
        "--author",
        "Agent",
        "--set-agent",
    )

    legacy_payload = assert_success(legacy)
    new_payload = assert_success(new)
    assert set(new_payload) == {
        "ok",
        "file",
        "comment_id",
        "reply_added",
        "reply_author",
        "reply_body",
        "agent_instruction",
        "replies_count",
        "thread_count",
    }
    assert normalize_reply(new_payload) == normalize_reply(legacy_payload)
    assert 'id="hyp-comments"' in cli_file.read_text(encoding="utf-8")


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
@pytest.mark.parametrize(
    ("legacy_args", "new_args", "cause"),
    [
        (
            ["tools/add_comment.py", "--selector", ".dupe", "--body", "Body", "--author", "Agent"],
            ["tools/hypresent.py", "add-comment", "--selector", ".dupe", "--body", "Body", "--author", "Agent"],
            "selector matched 2 elements",
        ),
        (
            ["tools/reply_comment.py", "--comment-id", "missing", "--reply", "Body"],
            ["tools/hypresent.py", "reply", "--comment-id", "missing", "--reply", "Body"],
            "no comment thread with id",
        ),
    ],
)
def test_failure_class_matches_legacy_for_browser_failures(tmp_path, legacy_args, new_args, cause):
    legacy_file = copy_fixture(tmp_path, "legacy-fail.html")
    cli_file = copy_fixture(tmp_path, "cli-fail.html")
    legacy = run_cmd(*legacy_args[:1], "--file", legacy_file, *legacy_args[1:])
    new = run_cmd(*new_args[:2], "--file", cli_file, *new_args[2:])

    assert legacy.returncode == 2
    assert new.returncode == 2
    assert cause in legacy.stderr
    assert cause in new.stderr


def test_failure_class_matches_legacy_for_non_conforming_deck(tmp_path):
    bad_legacy = tmp_path / "legacy-bad.html"
    bad_new = tmp_path / "new-bad.html"
    bad_legacy.write_text("<html><body><p>No slides.</p></body></html>", encoding="utf-8")
    bad_new.write_text("<html><body><p>No slides.</p></body></html>", encoding="utf-8")

    legacy = run_cmd(
        "tools/add_comment.py",
        "--file",
        bad_legacy,
        "--selector",
        "p",
        "--body",
        "Body",
        "--author",
        "Agent",
    )
    new = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        bad_new,
        "--selector",
        "p",
        "--body",
        "Body",
        "--author",
        "Agent",
    )

    assert legacy.returncode == 2
    assert new.returncode == 2
    assert "no <section> slides found" in legacy.stderr
    assert "no <section> slides found" in new.stderr


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_add_comment_out_writes_new_file_and_leaves_source_untouched(tmp_path):
    src_file = copy_fixture(tmp_path, "src.html")
    out_file = tmp_path / "out.html"
    original = src_file.read_text(encoding="utf-8")

    proc = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        src_file,
        "--selector",
        "#target-copy",
        "--body",
        "Save-as path.",
        "--author",
        "Vivian",
        "--out",
        out_file,
    )

    payload = assert_success(proc)
    assert Path(payload["file"]) == out_file.resolve()
    assert out_file.exists()
    saved = out_file.read_text(encoding="utf-8")
    assert 'id="hyp-comments"' in saved
    assert payload["comment_id"] in saved
    # save-as must not mutate the source deck
    assert src_file.read_text(encoding="utf-8") == original


def test_write_verbs_and_session_module_do_not_import_playwright_at_module_import():
    hypresent_source = (TOOLS_DIR / "hypresent.py").read_text(encoding="utf-8")
    session_source = (TOOLS_DIR / "deck_session.py").read_text(encoding="utf-8")
    assert "playwright.sync_api" not in hypresent_source
    assert "playwright.sync_api" in session_source
    assert "from playwright.sync_api" not in session_source.split("def start_browser", 1)[0]


def test_new_helper_definitions_have_single_session_site():
    session_source = (TOOLS_DIR / "deck_session.py").read_text(encoding="utf-8")
    assert session_source.count("def free_port") == 1
    assert session_source.count("def start_server") == 1
    assert session_source.count("def post_json") == 1
    assert session_source.count("def set_fake_dialog") == 1
    assert session_source.count("def doc_eval") == 1
