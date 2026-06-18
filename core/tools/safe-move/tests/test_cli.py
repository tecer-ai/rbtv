"""Smoke tests for the safe_move CLI surface."""

import subprocess
import sys

import pytest

from safe_move.cli import build_parser, main

CONSULT_FLAGS = [
    "--scope-root",
    "--exclude",
    "--read-only",
    "--include-archive",
    "--generated",
]
ACT_FLAGS = CONSULT_FLAGS + ["--apply"]


def test_consult_help_shows_all_flags():
    result = subprocess.run(
        [sys.executable, "-m", "safe_move", "consult", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for flag in CONSULT_FLAGS:
        assert flag in result.stdout, f"Missing flag {flag} in consult --help"


def test_act_help_shows_all_flags():
    result = subprocess.run(
        [sys.executable, "-m", "safe_move", "act", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for flag in ACT_FLAGS:
        assert flag in result.stdout, f"Missing flag {flag} in act --help"


def test_consult_parser_accepts_full_arg_set():
    parser = build_parser()
    args = parser.parse_args(
        [
            "consult",
            "old/path",
            "new/path",
            "--scope-root",
            ".",
            "--exclude",
            "archive",
            "--read-only",
            "protected",
            "--include-archive",
            "--generated",
            "generated.txt",
        ]
    )
    assert args.subcommand == "consult"
    assert args.old == "old/path"
    assert args.new == "new/path"
    assert args.scope_root == "."
    assert args.exclude == ["archive"]
    assert args.read_only == ["protected"]
    assert args.generated == ["generated.txt"]
    assert args.include_archive is True


def test_act_parser_requires_apply():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["act", "old", "new"])


def test_act_parser_accepts_empty_apply():
    parser = build_parser()
    args = parser.parse_args(["act", "old", "new", "--apply", ""])
    assert args.apply == ""


def test_act_not_yet_implemented_signal():
    assert main(["act", "a", "b", "--apply", "ref-0001:deadbeef"]) == 1
