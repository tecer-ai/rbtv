"""Stdlib unittest coverage for cli_preview.py (init/check/build).

Run: python test_cli_preview.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
CLI = str(HERE / "cli_preview.py")


def run(args, cwd=None):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True, cwd=cwd)


# Bare command paths (no flags) per the corrected contract; both declared
# commands get a real -h/--help screen, and List (success) is separate from
# List help, so Help: yes is never used to label a success screen.
GOOD_REVIEW = """# Review: Demo

Fixture: one item installed.

## Command inventory

- `demo`
- `demo list`
"""

GOOD_SCREENS = """## 1. Root help

Category: Help
Command: `demo -h`
Terminal width: 100
Scenario: fresh
Exit code: 0
Command-path: demo
Help: yes

```text
usage: demo
```

## 5. List help

Category: Help
Command: `demo list -h`
Terminal width: 100
Scenario: fresh
Exit code: 0
Command-path: demo list
Help: yes

```json
{"count": 1}
```
"""


class TempFolder:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "review"
        self.path.mkdir()
        return self.path

    def __exit__(self, *exc):
        self.tmp.cleanup()


def write_good(folder: Path):
    (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
    (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")


def issue_messages(payload):
    return [i["message"] for i in payload["issues"]]


class TestInit(unittest.TestCase):
    def test_init_creates_files_from_other_cwd(self):
        with TempFolder() as base:
            target = base / "new"
            r = run(["init", str(target), "--json"], cwd=str(HERE.parent))
            self.assertEqual(r.returncode, 0, r.stderr)
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue((target / "review.md").is_file())
            self.assertTrue((target / "01-screens.md").is_file())

    def test_init_refuses_nonempty_existing_folder(self):
        with TempFolder() as base:
            target = base / "existing"
            target.mkdir()
            (target / "stray.txt").write_text("x", encoding="utf-8")
            r = run(["init", str(target), "--json"])
            self.assertEqual(r.returncode, 1)
            self.assertEqual(sorted(p.name for p in target.iterdir()), ["stray.txt"])

    def test_init_on_existing_file_refuses_cleanly(self):
        # Regression: init used to call folder.iterdir() unconditionally,
        # crashing with NotADirectoryError when the path is a plain file.
        with TempFolder() as base:
            target = base / "afile"
            target.write_text("x", encoding="utf-8")
            r = run(["init", str(target), "--json"])
            self.assertEqual(r.returncode, 1)
            self.assertNotIn("Traceback", r.stderr)
            payload = json.loads(r.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(target.read_text(encoding="utf-8"), "x")

    def test_init_output_passes_check_unmodified(self):
        # Run init -> check exactly as delivered, no fixture edits.
        with TempFolder() as base:
            target = base / "new"
            run(["init", str(target)])
            r = run(["check", str(target), "--json"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_init_output_builds_and_help_screens_are_real_help(self):
        with TempFolder() as base:
            target = base / "new"
            run(["init", str(target)])
            result_check = json.loads(run(["check", str(target), "--json"]).stdout)
            self.assertEqual(result_check["screen_count"], 3)
            out = target / "preview.html"
            r = run(["build", str(target), "--out", str(out), "--json"])
            self.assertEqual(r.returncode, 0, r.stdout)
            html = out.read_text(encoding="utf-8")
            # The plain "list" success screen must NOT be counted as help
            # coverage for "example list" — only the "-h" screen does.
            self.assertIn("example list -h", html)
            self.assertIn("ID    Description", html)

    def test_init_text_mode_prints_visible_result(self):
        # Regression: text-mode init/check/build used to print nothing.
        with TempFolder() as base:
            target = base / "new"
            r = run(["init", str(target)])
            self.assertEqual(r.returncode, 0)
            self.assertTrue(r.stdout.strip(), "init produced no visible text output")
            self.assertIn(str(target), r.stdout)
            self.assertIn("next", r.stdout.lower())


class TestCheck(unittest.TestCase):
    def test_good_folder_passes(self):
        with TempFolder() as folder:
            write_good(folder)
            r = run(["check", str(folder), "--json"], cwd=str(HERE.parent))
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 0)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["screen_count"], 2)

    def test_check_text_mode_prints_visible_result_on_success_and_failure(self):
        with TempFolder() as folder:
            write_good(folder)
            r_ok = run(["check", str(folder)])
            self.assertEqual(r_ok.returncode, 0)
            self.assertIn("OK", r_ok.stdout)

            r_missing = run(["check", str(folder / "does-not-exist")])
            self.assertEqual(r_missing.returncode, 1)
            self.assertTrue(r_missing.stdout.strip(), "check refusal produced no visible text output")
            self.assertIn("fix", r_missing.stdout.lower())

    def test_missing_review_md(self):
        with TempFolder() as folder:
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("review.md not found" in m for m in issue_messages(payload)))

    def test_duplicate_ids_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            dup = GOOD_SCREENS.replace("## 5. List help", "## 1. List help")
            (folder / "01-screens.md").write_text(dup, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("duplicate screen id" in m for m in issue_messages(payload)))

    def test_screen_id_zero_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("## 1. Root help", "## 0. Root help")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("must be a positive integer" in m for m in issue_messages(payload)))

    def test_missing_help_screen_for_declared_command(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            no_help = GOOD_SCREENS.replace("Help: yes", "Help: no")
            (folder / "01-screens.md").write_text(no_help, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("no help screen declared" in m for m in issue_messages(payload)))

    def test_help_yes_without_help_token_rejected(self):
        # Regression: a plain success screen must not satisfy coverage just
        # because it says Help: yes.
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Command: `demo list -h`", "Command: `demo list`")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("no -h/--help token" in m for m in issue_messages(payload)))

    def test_undeclared_command_path_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Command-path: demo list", "Command-path: demo nope")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("not in review.md's command inventory" in m for m in issue_messages(payload)))

    def test_missing_command_path_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Command-path: demo\n", "")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("missing required field 'Command-path'" in m for m in issue_messages(payload)))

    def test_invalid_json_fence_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace('{"count": 1}', '{count: 1,}')
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("not valid strict JSON" in m for m in issue_messages(payload)))

    def test_nan_infinity_json_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace('{"count": 1}', '{"count": NaN}')
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("non-strict JSON token" in m for m in issue_messages(payload)))

    def test_terminal_width_must_be_positive_integer(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Terminal width: 100\nScenario: fresh\nExit code: 0\nCommand-path: demo\n",
                                        "Terminal width: 0\nScenario: fresh\nExit code: 0\nCommand-path: demo\n")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("Terminal width" in m and "positive integer" in m for m in issue_messages(payload)))

    def test_exit_code_out_of_range_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Exit code: 0\nCommand-path: demo\n", "Exit code: 999\nCommand-path: demo\n")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("Exit code" in m and "0-255" in m for m in issue_messages(payload)))

    def test_missing_required_field_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Exit code: 0\nCommand-path: demo\n", "Command-path: demo\n")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("missing required field 'Exit code'" in m for m in issue_messages(payload)))

    def test_unknown_field_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Category: Help", "Category: Help\nBogus: x")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("unknown field 'Bogus'" in m for m in issue_messages(payload)))

    def test_duplicate_field_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace("Category: Help", "Category: Help\nCategory: Help2")
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("duplicate field 'Category'" in m for m in issue_messages(payload)))

    def test_extra_trailing_content_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            bad = GOOD_SCREENS.replace(
                '{"count": 1}\n```\n',
                '{"count": 1}\n```\nsurprise trailing text\n',
            )
            (folder / "01-screens.md").write_text(bad, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("unexpected content after fenced block" in m for m in issue_messages(payload)))

    def test_noncontiguous_ids_allowed(self):
        # GOOD_SCREENS already uses ids 1 and 5 (a gap) — must pass.
        with TempFolder() as folder:
            write_good(folder)
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"], payload)

    def test_literal_heading_inside_fence_is_preserved_not_split(self):
        # Regression: a screen splitter that ignores fence state would treat
        # this literal "## heading" line, inside the payload, as a new screen.
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = GOOD_SCREENS.replace("usage: demo", "usage: demo\n## 99. not a real heading\nmore output")
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["screen_count"], 2)  # still 2, not 3

    def test_stray_leading_content_before_first_heading_rejected(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = "This is not a comment and not blank.\n" + GOOD_SCREENS
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("before the first screen heading" in m for m in issue_messages(payload)))

    def test_html_comment_before_first_heading_allowed(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = "<!-- authoring notes for humans only -->\n\n" + GOOD_SCREENS
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"], payload)

    def test_inventory_prose_before_bullets_allowed_but_trailing_junk_rejected(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW.replace(
                "## Command inventory\n\n- `demo`",
                "## Command inventory\n\nSome intro prose describing scope.\n\n- `demo`",
            )
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertTrue(payload["ok"], payload)

            review_bad = GOOD_REVIEW.replace("- `demo list`\n", "- `demo list`\nstray trailing prose\n")
            (folder / "review.md").write_text(review_bad, encoding="utf-8")
            r2 = run(["check", str(folder), "--json"])
            payload2 = json.loads(r2.stdout)
            self.assertEqual(r2.returncode, 1)
            self.assertTrue(any("trailing content after command inventory bullets" in m for m in issue_messages(payload2)))

    def test_multiple_titles_and_inventory_sections_rejected(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW + "\n# Another title\n\n## Command inventory\n\n- `x`\n"
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            msgs = issue_messages(payload)
            self.assertTrue(any("multiple top-level" in m for m in msgs))
            self.assertTrue(any("multiple '## Command inventory'" in m for m in msgs))

    def test_unsupported_section_after_inventory_rejected(self):
        # Regression: a '## ' heading after the inventory used to silently
        # stop the bullet scan with no reported issue at all.
        with TempFolder() as folder:
            review = GOOD_REVIEW + "\n## Notes\n\nSome extra content that should not be silently dropped.\n"
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("unsupported section" in m and "Notes" in m for m in issue_messages(payload)))

    def test_unsupported_section_between_title_and_inventory_rejected(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW.replace(
                "## Command inventory",
                "## Extra\n\nsome content\n\n## Command inventory",
            )
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("unsupported section" in m and "Extra" in m for m in issue_messages(payload)))

    def test_empty_title_rejected(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW.replace("# Review: Demo", "# Review:")
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("review title is empty" in m for m in issue_messages(payload)))

    def test_whitespace_only_inventory_entry_rejected(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW.replace("- `demo`\n", "- `   `\n")
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("empty or whitespace-only" in m for m in issue_messages(payload)))

    def test_empty_fixture_description_rejected(self):
        with TempFolder() as folder:
            review = "# Review: Demo\n\n## Command inventory\n\n- `demo`\n- `demo list`\n"
            (folder / "review.md").write_text(review, encoding="utf-8")
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 1)
            self.assertTrue(any("fixture description is empty" in m for m in issue_messages(payload)))

    def test_backticks_stripped_from_command(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "preview.html"
            run(["build", str(folder), "--out", str(out)])
            html = out.read_text(encoding="utf-8")
            start = html.index('id="screen-data">') + len('id="screen-data">')
            end = html.index("</script>", start)
            embedded = json.loads(html[start:end])
            self.assertEqual(embedded[0]["command"], "demo -h")  # no surrounding backticks

    def test_dual_stream_screen_keeps_payloads_separate(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = GOOD_SCREENS.replace(
                "Command-path: demo list\nHelp: yes\n\n```json\n{\"count\": 1}\n```\n",
                "Command-path: demo list\nHelp: yes\nStream: both\n\nStdout:\n```text\nok\n```\nStderr:\n```text\nwarn: x\n```\n",
            )
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            r = run(["check", str(folder), "--json"])
            self.assertTrue(json.loads(r.stdout)["ok"])

            out = folder / "preview.html"
            run(["build", str(folder), "--out", str(out)])
            html = out.read_text(encoding="utf-8")
            start = html.index('id="screen-data">') + len('id="screen-data">')
            end = html.index("</script>", start)
            embedded = json.loads(html[start:end])
            dual = embedded[1]
            self.assertEqual(dual["content"], "ok")
            self.assertEqual(dual["stderrContent"], "warn: x")
            # Never invented-concatenated into one copyable blob.
            self.assertNotIn("ok\nwarn: x", json.dumps(embedded))
            self.assertIn("Simulated terminal output — stdout", html)
            self.assertIn("Simulated terminal output — stderr", html)

    def test_single_stream_stderr_labeled_in_metadata(self):
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = GOOD_SCREENS.replace("Command-path: demo list\nHelp: yes\n",
                                            "Command-path: demo list\nHelp: yes\nStream: stderr\n")
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out)])
            self.assertEqual(r.returncode, 0)
            html = out.read_text(encoding="utf-8")
            self.assertIn('metaItem("Stream", s.stream)', html)


class TestBuild(unittest.TestCase):
    def test_build_writes_html_and_check_passes_first(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out), "--json"], cwd=str(HERE.parent))
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(out.is_file())
            html = out.read_text(encoding="utf-8")
            self.assertIn("Demo", html)
            self.assertIn("usage: demo", html)
            start = html.index('id="screen-data">') + len('id="screen-data">')
            end = html.index("</script>", start)
            embedded = json.loads(html[start:end])
            self.assertEqual(embedded[1]["content"], '{"count": 1}')

    def test_build_no_output_on_failed_check(self):
        with TempFolder() as folder:
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")  # no review.md
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out), "--json"])
            self.assertEqual(r.returncode, 1)
            self.assertFalse(out.exists())

    def test_build_text_mode_prints_visible_refusal_with_fix(self):
        with TempFolder() as folder:
            (folder / "01-screens.md").write_text(GOOD_SCREENS, encoding="utf-8")  # no review.md
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out)])
            self.assertEqual(r.returncode, 1)
            self.assertTrue(r.stdout.strip())
            self.assertIn("fix", r.stdout.lower())

    def test_build_refuses_overwrite_without_force(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "preview.html"
            out.write_text("existing", encoding="utf-8")
            r = run(["build", str(folder), "--out", str(out), "--json"])
            self.assertEqual(r.returncode, 1)
            self.assertEqual(out.read_text(encoding="utf-8"), "existing")

    def test_build_force_overwrites(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "preview.html"
            out.write_text("existing", encoding="utf-8")
            r = run(["build", str(folder), "--out", str(out), "--force", "--json"])
            self.assertEqual(r.returncode, 0)
            self.assertIn("Demo", out.read_text(encoding="utf-8"))

    def test_build_rejects_output_colliding_with_input(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "review.md"
            r = run(["build", str(folder), "--out", str(out), "--force", "--json"])
            self.assertEqual(r.returncode, 1)

    def test_build_escapes_title_and_payload(self):
        with TempFolder() as folder:
            review = GOOD_REVIEW.replace("# Review: Demo", "# Review: Demo <script>alert(1)</script>")
            (folder / "review.md").write_text(review, encoding="utf-8")
            screens = GOOD_SCREENS.replace("usage: demo", "usage: demo </script><b>x</b> and <!--<script>evil</script>-->")
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out), "--json"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            html = out.read_text(encoding="utf-8")
            self.assertNotIn("<title>Demo <script>", html)
            self.assertIn("&lt;script&gt;", html)
            # Screen payload travels through the JSON data island; no raw
            # "<" survives there at all (covers "</script>" AND "<!--").
            start = html.index('id="screen-data">') + len('id="screen-data">')
            end = html.index("</script>", start)
            raw_island = html[start:end]
            self.assertNotIn("<", raw_island)
            embedded = json.loads(raw_island)
            self.assertIn("</script><b>x</b> and <!--<script>evil</script>-->", embedded[0]["content"])

    def test_repeated_build_is_deterministic(self):
        with TempFolder() as folder:
            write_good(folder)
            out1 = folder / "a.html"
            out2 = folder / "b.html"
            run(["build", str(folder), "--out", str(out1)])
            run(["build", str(folder), "--out", str(out2)])
            self.assertEqual(out1.read_text(encoding="utf-8"), out2.read_text(encoding="utf-8"))

    def test_pager_and_status_use_array_position_not_id_arithmetic(self):
        # Regression: with a non-contiguous id set (1, 17 here), Previous/
        # Next used to compute s.id-1 / s.id+1 and look that up in byId, so
        # both were disabled on the last screen despite earlier ones
        # existing, and the status bar showed the raw id instead of position.
        with TempFolder() as folder:
            (folder / "review.md").write_text(GOOD_REVIEW, encoding="utf-8")
            screens = GOOD_SCREENS.replace("## 5. List help", "## 17. List help")
            (folder / "01-screens.md").write_text(screens, encoding="utf-8")
            out = folder / "preview.html"
            r = run(["build", str(folder), "--out", str(out)])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            html = out.read_text(encoding="utf-8")
            self.assertIn("idxById", html)
            self.assertNotIn("s.id - 1", html)
            self.assertNotIn("s.id + 1", html)
            self.assertIn('"Screen " + (idxById[id] + 1) + " of "', html)
            self.assertIn("var startId = screens[0].id;", html)

    def test_original_css_rules_unchanged(self):
        # Spot-check signature CSS rules from the original single-authored
        # template survive verbatim in generated output.
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "preview.html"
            run(["build", str(folder), "--out", str(out)])
            html = out.read_text(encoding="utf-8")
            for rule in (
                "--bg: #0c0f0c;",
                "--green: #39ff6a;",
                "pre.terminal-content {",
                "button.copy-btn:hover { background: #16210f; }",
                "@media (max-width: 760px) {",
            ):
                self.assertIn(rule, html)


class TestHelp(unittest.TestCase):
    def test_help_at_every_depth_no_files_needed(self):
        for args in (["-h"], ["--help"], ["init", "-h"], ["check", "-h"], ["build", "-h"]):
            r = run(args, cwd=str(HERE.parent))
            self.assertEqual(r.returncode, 0, f"{args}: {r.stderr}")
            self.assertIn("usage", r.stdout.lower())

    def test_help_before_and_after_positional(self):
        with TempFolder() as folder:
            r1 = run(["check", "-h", str(folder)])
            r2 = run(["check", str(folder), "-h"])
            self.assertEqual(r1.returncode, 0)
            self.assertEqual(r2.returncode, 0)
            self.assertIn("usage", r1.stdout.lower())
            self.assertIn("usage", r2.stdout.lower())

    def test_help_shows_examples_exit_codes_and_side_effects(self):
        for args, needles in (
            (["init", "-h"], ["example", "exit codes", "0 created"]),
            (["check", "-h"], ["example", "exit codes", "never writes"]),
            (["build", "-h"], ["example", "exit codes", "atomically"]),
        ):
            r = run(args)
            self.assertEqual(r.returncode, 0)
            low = r.stdout.lower()
            for needle in needles:
                self.assertIn(needle.lower(), low, f"{args}: missing {needle!r} in help text")

    def test_double_dash_terminator_respected(self):
        with TempFolder() as base:
            target = base / "-oddname"
            r = run(["init", "--", str(target)])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((target / "review.md").is_file())

    def test_out_equals_literal_dash_h_not_treated_as_help(self):
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "-h"
            r = run(["build", str(folder), f"--out={out}", "--json"])
            payload = json.loads(r.stdout)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(out.is_file())

    def test_out_missing_value_dash_h_shows_help_not_expected_argument_error(self):
        # Regression: argparse used to try consuming a bare -h as --out's
        # value and error "expected one argument" instead of showing help.
        with TempFolder() as folder:
            r = run(["build", str(folder), "--out", "-h"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("expected one argument", r.stderr)
            self.assertIn("usage: cli_preview.py build", r.stdout)

    def test_out_missing_value_dash_dash_help_shows_build_help(self):
        with TempFolder() as folder:
            r = run(["build", str(folder), "--out", "--help"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("usage: cli_preview.py build", r.stdout)

    def test_out_equals_dash_h_literal_still_not_help(self):
        # "--out=-h" is one token, a literal value assignment, not help.
        with TempFolder() as folder:
            write_good(folder)
            out = folder / "-h"
            r = run(["build", str(folder), "--out=-h"], cwd=str(folder))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(out.is_file())
            self.assertNotIn("usage:", r.stdout)

    def test_help_after_double_dash_terminator_is_literal_not_help(self):
        with TempFolder() as base:
            target = base / "-h"
            r = run(["init", "--", str(target)])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((target / "review.md").is_file())

    def test_missing_required_option_under_json_emits_one_json_failure_no_stderr_dup(self):
        r = run(["build", "somefolder", "--json"])  # --out is required
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stderr, "")
        payload = json.loads(r.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)

    def test_missing_required_option_without_json_goes_to_stderr(self):
        r = run(["build", "somefolder"])  # --out is required, no --json
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertTrue(r.stderr.strip())


if __name__ == "__main__":
    unittest.main()
