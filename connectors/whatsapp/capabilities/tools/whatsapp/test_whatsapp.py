#!/usr/bin/env python3
"""Checks the wrapper's trimming of outgoing text and its store lookup; reaches no account."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("whatsapp", Path(__file__).with_name("whatsapp.py"))
whatsapp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(whatsapp)


class TrimOutgoing(unittest.TestCase):
    def test_message_with_equals_loses_final_newline(self):
        self.assertEqual(whatsapp.trim_outgoing(["--json", "send", "text", "--to=1", "--message=<sara>\noi\n\n"]),
                         ["--json", "send", "text", "--to=1", "--message=<sara>\noi"])

    def test_separate_message_value_is_trimmed(self):
        self.assertEqual(whatsapp.trim_outgoing(["send", "text", "--message", "oi \n"]),
                         ["send", "text", "--message", "oi"])

    def test_caption_is_trimmed(self):
        self.assertEqual(whatsapp.trim_outgoing(["send", "file", "--file=a.jpg", "--caption=foto\n"]),
                         ["send", "file", "--file=a.jpg", "--caption=foto"])

    def test_inner_blank_lines_and_leading_text_are_kept(self):
        self.assertEqual(whatsapp.trim_outgoing(["send", "text", "--message=a\n\nb\n"]),
                         ["send", "text", "--message=a\n\nb"])

    def test_other_commands_are_untouched(self):
        self.assertEqual(whatsapp.trim_outgoing(["messages", "search", "--message=x\n"]),
                         ["messages", "search", "--message=x\n"])


@unittest.skipIf(os.name == "nt", "the stand-in wacli is a POSIX shell script")
class StoreLookup(unittest.TestCase):
    """Ignite's service runs from the user's home, outside the installation, and names the store."""

    def run_wrapper(self, *arguments, env=None):
        with tempfile.TemporaryDirectory() as outside:
            fake = Path(outside, "bin")
            fake.mkdir()
            wacli = fake / "wacli"
            wacli.write_text('#!/bin/sh\necho "store=$WACLI_STORE_DIR args=$*"\n')
            wacli.chmod(0o755)
            environment = {**os.environ, "PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"}
            environment.pop("WACLI_STORE_DIR", None)
            environment.update(env or {})
            return subprocess.run([sys.executable, str(Path(__file__).with_name("whatsapp.py")), *arguments],
                                  cwd=outside, env=environment, capture_output=True, text=True)

    def test_named_store_runs_outside_an_installation(self):
        result = self.run_wrapper("--store", "/s/whatsapp", "--json", "auth", "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("args=--store /s/whatsapp --json auth status", result.stdout)

    def test_store_from_environment_runs_outside_an_installation(self):
        result = self.run_wrapper("--version", env={"WACLI_STORE_DIR": "/s/env"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("store=/s/env", result.stdout)

    def test_no_store_outside_an_installation_is_refused(self):
        result = self.run_wrapper("--version")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-installation", result.stderr)


if __name__ == "__main__":
    unittest.main()
