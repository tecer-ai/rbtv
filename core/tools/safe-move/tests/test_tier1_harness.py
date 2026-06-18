"""Seed tests for the Tier-1 synthetic fixture harness."""

import pytest

from tests.harness import assert_untouched, snapshot


def test_harness_builds_markdown_link_fixture(repo_builder):
    """A simple markdown link fixture builds and ``git init`` succeeds."""
    fx = repo_builder(
        "markdown_link",
        {
            "index.md": "See [the target](old.md) for details.\n",
            "old.md": "# Old\ncontent\n",
        },
        tracked=["index.md", "old.md"],
    )
    assert (fx.repo / ".git").is_dir()
    assert fx.before["index.md"] == "See [the target](old.md) for details.\n"
    assert (fx.repo / "old.md").read_text(encoding="utf-8") == fx.before["old.md"]


def test_harness_builds_substring_collision_fixture(repo_builder):
    """A substring-collision fixture has both files and the right reference."""
    fx = repo_builder(
        "substring_collision",
        {
            "index.md": "- [[agent.md]]\n- subagent.md\n",
            "agent.md": "# Agent\n",
            "subagent.md": "# Subagent\n",
        },
        tracked=["index.md", "agent.md", "subagent.md"],
    )
    content = (fx.repo / "index.md").read_text(encoding="utf-8")
    assert "[[agent.md]]" in content
    assert "subagent.md" in content


def test_must_not_touch_helper_passes_when_unchanged(repo_builder):
    """``assert_untouched`` succeeds when protected files are not modified."""
    fx = repo_builder(
        "untouched",
        {
            "transcript.md": "Speaker: see old.md for context.\n",
            "log.md": "- moved old.md to new.md\n",
        },
    )
    assert_untouched(fx.repo, ["transcript.md", "log.md"], fx.before)


def test_must_not_touch_helper_fails_when_changed(repo_builder):
    """``assert_untouched`` raises ``AssertionError`` when a protected file changes."""
    fx = repo_builder(
        "touched",
        {
            "transcript.md": "Speaker: see old.md for context.\n",
        },
    )
    (fx.repo / "transcript.md").write_text("modified", encoding="utf-8")
    with pytest.raises(AssertionError):
        assert_untouched(fx.repo, ["transcript.md"], fx.before)


def test_snapshot_helper_captures_before_state(repo_builder):
    """``snapshot()`` captures the current state for exact before/after comparisons."""
    fx = repo_builder(
        "snapshot",
        {
            "a.md": "alpha\n",
            "b.md": "beta\n",
        },
    )
    after = snapshot(fx.repo, ["a.md", "b.md"])
    assert after == fx.before
    (fx.repo / "a.md").write_text("changed\n", encoding="utf-8")
    after = snapshot(fx.repo, ["a.md", "b.md"])
    assert after["a.md"] == "changed\n"
    assert after["b.md"] == "beta\n"
