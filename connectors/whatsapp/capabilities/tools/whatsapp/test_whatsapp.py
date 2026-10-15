#!/usr/bin/env python3
"""Checks the wrapper's trimming of outgoing text; reaches no account."""

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
