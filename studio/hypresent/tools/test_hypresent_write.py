import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

TOOLS_DIR = Path(__file__).parent
FIXTURE = TOOLS_DIR / "fixtures" / "write-deck.html"


def playwright_available():
    return importlib.util.find_spec("playwright") is not None


def load_island(path):
    """Parse the saved #hyp-comments island into its thread list.

    Parsing (not substring-matching) is required: the runtime serializes the
    island COMPACT, and a raw extraction would false-positive on the
    agent-instruction head comment that mentions the island tag.
    """
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    tag = soup.find("script", id="hyp-comments")
    assert tag is not None, "saved deck has no #hyp-comments island"
    return json.loads(tag.string)


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
        encoding="utf-8",
        timeout=30,
    )


def parse_json(stdout):
    return json.loads(stdout)


def assert_success(proc):
    assert proc.returncode == 0, proc.stderr
    payload = parse_json(proc.stdout)
    assert payload["ok"] is True
    return payload


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_add_comment_returns_contract_fields_and_saves_runtime_island(tmp_path):
    cli_file = copy_fixture(tmp_path, "cli-add.html")

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
    assert new_payload["file"] == str(cli_file.resolve())
    assert new_payload["comment_id"] == "1"
    assert new_payload["author"] == "Vivian"
    assert new_payload["agentInstruction"] is True
    assert new_payload["anchored"] is True
    assert new_payload["marker_rendered"] is True
    assert new_payload["contextText"] == "Target copy for a new comment."
    assert new_payload["anchor"]["nativeId"] == "target-copy"
    assert new_payload["anchor"]["hook"] is None
    saved = cli_file.read_text(encoding="utf-8")
    assert 'id="hyp-comments"' in saved
    threads = load_island(cli_file)
    thread = next(t for t in threads if t["id"] == "1")
    assert thread["body"] == "Tighten this copy."
    assert thread["author"] == "Vivian"
    assert thread["agentInstruction"] is True


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_reply_returns_contract_fields_and_saves_runtime_island(tmp_path):
    cli_file = copy_fixture(tmp_path, "cli-reply.html")

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
    assert new_payload == {
        "ok": True,
        "file": str(cli_file.resolve()),
        "comment_id": "c-existing",
        "reply_added": True,
        "reply_author": "Agent",
        "reply_body": "Working on it.",
        "agent_instruction": True,
        "replies_count": 1,
        "thread_count": 1,
    }
    saved = cli_file.read_text(encoding="utf-8")
    assert 'id="hyp-comments"' in saved
    threads = load_island(cli_file)
    thread = next(t for t in threads if t["id"] == "c-existing")
    assert thread["agentInstruction"] is True
    reply = thread["replies"][-1]
    assert reply["author"] == "Agent"
    assert reply["body"] == "Working on it."


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
@pytest.mark.parametrize(
    ("new_args", "cause"),
    [
        (
            ["tools/hypresent.py", "add-comment", "--selector", ".dupe", "--body", "Body", "--author", "Agent"],
            "selector matched 2 elements",
        ),
        (
            ["tools/hypresent.py", "reply", "--comment-id", "missing", "--reply", "Body"],
            "no comment thread with id",
        ),
    ],
)
def test_browser_failures_return_exit_2_and_contract_prefix(tmp_path, new_args, cause):
    cli_file = copy_fixture(tmp_path, "cli-fail.html")
    new = run_cmd(*new_args[:2], "--file", cli_file, *new_args[2:])

    assert new.returncode == 2
    # The dev server logs HTTP requests to stderr before the error line, so the
    # contract prefix begins the ERROR line, not stderr[0]. Locate that line.
    prefix = f"hypresent {new_args[1]}: ERROR —"
    error_line = next((ln for ln in new.stderr.splitlines() if ln.startswith(prefix)), None)
    assert error_line is not None, new.stderr
    assert cause in error_line


def test_non_conforming_deck_returns_exit_2_and_contract_prefix(tmp_path):
    bad_new = tmp_path / "new-bad.html"
    bad_new.write_text("<html><body><p>No slides.</p></body></html>", encoding="utf-8")

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

    assert new.returncode == 2
    assert new.stderr.startswith("hypresent add-comment: ERROR —")
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
