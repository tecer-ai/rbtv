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


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_write_verb_output_is_agent_clean(tmp_path):
    """Output contract: stdout carries ONLY the JSON result; stderr is empty on
    success and exactly the one ERROR line on failure — no server log noise."""
    cli_file = copy_fixture(tmp_path, "clean-out.html")

    ok = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        cli_file,
        "--selector",
        "#target-copy",
        "--body",
        "Clean output.",
        "--author",
        "Agent",
    )
    assert ok.returncode == 0
    json.loads(ok.stdout)  # stdout is pure JSON, parseable as-is
    assert ok.stderr.strip() == ""

    fail = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        cli_file,
        "--selector",
        ".dupe",
        "--body",
        "Body",
        "--author",
        "Agent",
    )
    assert fail.returncode == 2
    lines = [ln for ln in fail.stderr.splitlines() if ln.strip()]
    assert len(lines) == 1, fail.stderr
    assert lines[0].startswith("hypresent add-comment: ERROR —")


def island_threads(path):
    """Parse the saved island into its thread list, or ``[]`` when the store is
    empty (the serializer suppresses the island entirely at zero threads)."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    tag = soup.find("script", id="hyp-comments")
    return json.loads(tag.string) if tag is not None else []


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_delete_comment_removes_one_thread_and_keeps_the_rest(tmp_path):
    cli_file = copy_fixture(tmp_path, "cli-delete-one.html")

    # Add a second thread so a thread SURVIVES the delete — proves the island
    # still parses without the deleted thread (not just the empties path).
    added = run_cmd(
        "tools/hypresent.py",
        "add-comment",
        "--file",
        cli_file,
        "--selector",
        "#title-one",
        "--body",
        "Keep me.",
        "--author",
        "Agent",
    )
    kept_id = assert_success(added)["comment_id"]

    proc = run_cmd(
        "tools/hypresent.py",
        "delete-comment",
        "--file",
        cli_file,
        "--comment-id",
        "c-existing",
    )

    payload = assert_success(proc)
    assert set(payload) == {"ok", "file", "deleted_ids", "deleted_count", "thread_count"}
    assert payload["file"] == str(cli_file.resolve())
    assert payload["deleted_ids"] == ["c-existing"]
    assert payload["deleted_count"] == 1
    assert payload["thread_count"] == 1

    threads = island_threads(cli_file)
    ids = {t["id"] for t in threads}
    assert "c-existing" not in ids  # proven by parsing, not substring
    assert kept_id in ids
    # the deleted thread's durable cid tag is gone from the element
    saved = cli_file.read_text(encoding="utf-8")
    assert 'data-hyp-cid="c-existing"' not in saved


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_delete_comment_all_empties_the_island(tmp_path):
    cli_file = copy_fixture(tmp_path, "cli-delete-all.html")

    proc = run_cmd(
        "tools/hypresent.py",
        "delete-comment",
        "--file",
        cli_file,
        "--all",
    )

    payload = assert_success(proc)
    assert payload["deleted_ids"] == ["c-existing"]
    assert payload["deleted_count"] == 1
    assert payload["thread_count"] == 0
    # zero remaining threads → serializer suppresses the island; no thread survives
    assert island_threads(cli_file) == []


@pytest.mark.skipif(not playwright_available(), reason="playwright is absent; write verbs exit 3 by contract")
def test_delete_comment_unknown_id_returns_exit_2_and_lists_available_ids(tmp_path):
    cli_file = copy_fixture(tmp_path, "cli-delete-missing.html")

    proc = run_cmd(
        "tools/hypresent.py",
        "delete-comment",
        "--file",
        cli_file,
        "--comment-id",
        "does-not-exist",
    )

    assert proc.returncode == 2
    lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
    assert len(lines) == 1, proc.stderr
    assert lines[0].startswith("hypresent delete-comment: ERROR —")
    assert "comment id not found" in lines[0]
    assert "c-existing" in lines[0]  # lists available ids, read's convention


@pytest.mark.parametrize("extra", [["--comment-id", "c-existing", "--all"], []])
def test_delete_comment_arg_validation_exits_2_without_a_server(tmp_path, extra):
    """--comment-id XOR --all, one required — argparse rejects both/neither at
    exit 2 before any browser or server work (no playwright needed)."""
    cli_file = copy_fixture(tmp_path, "cli-delete-argval.html")

    proc = run_cmd("tools/hypresent.py", "delete-comment", "--file", cli_file, *extra)

    assert proc.returncode == 2
    assert "delete-comment" in proc.stderr
    # argparse validation error, not the runtime ERROR contract line
    assert "ERROR —" not in proc.stderr


def test_delete_comment_non_conforming_deck_returns_exit_2_and_contract_prefix(tmp_path):
    bad = tmp_path / "delete-bad.html"
    bad.write_text("<html><body><p>No slides.</p></body></html>", encoding="utf-8")

    proc = run_cmd(
        "tools/hypresent.py",
        "delete-comment",
        "--file",
        bad,
        "--comment-id",
        "c-existing",
    )

    assert proc.returncode == 2
    assert proc.stderr.startswith("hypresent delete-comment: ERROR —")
    assert "no <section> slides found" in proc.stderr
