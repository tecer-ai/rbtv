#!/usr/bin/env python3
"""Fixtures for every record format through every verb of session-sweep."""
import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("session_sweep", HERE / "session-sweep.py")
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)


def run(argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = ss.main(argv)
    fields = {}
    for line in buf.getvalue().splitlines():
        name, _, value = line.partition(" ")
        fields.setdefault(name, []).append(value)
    return code, fields, err.getvalue()


def claude_line(kind, content, **extra):
    d = {"type": kind, "timestamp": "2026-10-15T01:00:00Z", "isSidechain": False,
         "sessionId": "s1", "cwd": "/work", "message": {"role": kind, "content": content}}
    d.update(extra)
    return json.dumps(d)


def claude_record(folder: Path, marker="sweep-marker abc123") -> Path:
    lines = [
        json.dumps({"type": "mode", "mode": "normal"}),
        claude_line("user", "<local-command-caveat>ignored</local-command-caveat>", isMeta=True),
        claude_line("user", "please fix the counter", promptSource="typed"),
        claude_line("assistant", [{"type": "text", "text": "I will read it first."},
                                  {"type": "tool_use", "name": "Bash", "input": {"command": "git pull"}}]),
        claude_line("user", [{"type": "tool_result", "content": "fatal: not a git repository"}]),
        claude_line("assistant", [{"type": "tool_use", "name": "Bash", "input": {"command": "cat a.md"}}]),
        claude_line("user", [{"type": "tool_result", "content": "ok"}]),
        claude_line("assistant", [{"type": "tool_use", "name": "Bash", "input": {"command": "cat a.md"}}]),
        claude_line("user", [{"type": "tool_result", "content": "ok"}]),
        claude_line("assistant", [{"type": "text", "text": "I could not find the tool, so I worked around it. " + marker}]),
        claude_line("user", "i told you not to pull in the vault", promptSource="typed"),
        claude_line("user", [{"type": "text", "text": "[Request interrupted by user]"}]),
    ]
    p = folder / ".claude" / "projects" / "-work" / "s1.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def codex_record(folder: Path) -> Path:
    def item(payload):
        return json.dumps({"type": "response_item", "timestamp": "2026-10-15T01:00:00Z", "payload": payload})
    lines = [
        json.dumps({"type": "session_meta", "payload": {"cwd": "/work"}}),
        item({"type": "message", "role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions for /x\nskip"}]}),
        item({"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Resume your task"}]}),
        item({"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Reading."}]}),
        item({"type": "custom_tool_call", "name": "exec", "input": "env | grep TOKEN"}),
        item({"type": "custom_tool_call_output", "output": [{"type": "input_text", "text": "permission denied"}]}),
    ]
    p = folder / ".codex" / "sessions" / "2026" / "r.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def ignite_record(folder: Path) -> Path:
    text = ("# T:C:1\n\n## 1792018250217 assistant\n"
            + json.dumps({"replies": [{"text": "Sent the quote."}]})
            + "\n\n## 1792022824304 owner\nnão foi isso que eu pedi\n\n## 1792022851005 assistant\n"
            + json.dumps({"replies": [{"text": "Corrected."}]}) + "\n")
    p = folder / "agent" / "runtime" / "ignite" / "conversations" / "T-C-1" / "history.md"
    p.parent.mkdir(parents=True)
    p.write_text(text, encoding="utf-8")
    return p


def opencode_record(folder: Path, marker="sweep-marker oc9") -> str:
    db = folder / ".local" / "share" / "opencode" / "opencode.db"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(str(db))
    con.execute("create table session (id text, directory text)")
    con.execute("create table message (id text, session_id text, time_created integer, data text)")
    con.execute("create table part (id integer, message_id text, session_id text, time_created integer, data text)")
    con.execute("insert into session values ('S', '/work')")
    rows = [("m1", "S", 1, {"role": "user"}, 1, {"type": "text", "text": "do it"}),
            ("m2", "S", 2, {"role": "assistant"}, 2, {"type": "text", "text": "done " + marker}),
            ("m3", "S", 3, {"role": "assistant"}, 3, {"type": "tool", "tool": "bash",
                                                       "state": {"input": {"command": "git push --force"},
                                                                 "output": "rejected"}})]
    for mid, sid, t, md, pid, pd in rows:
        con.execute("insert into message values (?,?,?,?)", (mid, sid, t, json.dumps(md)))
        con.execute("insert into part values (?,?,?,?,?)", (pid, mid, sid, t, json.dumps(pd)))
    con.commit()
    con.close()
    return f"{db}#S"


class SessionSweep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self._home = os.environ.get("HOME"), os.environ.get("USERPROFILE")
        os.environ["HOME"] = os.environ["USERPROFILE"] = str(self.home)
        os.environ.pop("RBTV_AGENT_HOME", None)
        os.environ.pop("IGNITE_CONVERSATION", None)

    def tearDown(self):
        for key, value in zip(("HOME", "USERPROFILE"), self._home):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def test_claude_extract_and_check(self):
        record = claude_record(self.home)
        report = self.home / "report.md"
        report.write_text("Skipped the review step.", encoding="utf-8")
        out = self.home / "run"
        code, f, err = run(["extract", str(record), "--out", str(out), "--report", str(report)])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["owner_moments"], ["2"])
        self.assertEqual(f["reports"], ["1"])
        moments = json.loads((out / "moments.json").read_text(encoding="utf-8"))["moments"]
        matched = [tuple(m["matched"]) for m in moments if m["kind"] == "signal"]
        self.assertIn(("dangerous",), matched)        # git pull
        self.assertIn(("failed",), matched)           # fatal: not a git repository
        self.assertIn(("repeated",), matched)         # cat a.md twice
        self.assertIn(("workaround",), matched)       # could not find / worked around
        owner = [m for m in moments if m["kind"] == "owner"]
        self.assertTrue(owner[1]["agent_before"].startswith("I could not find"))
        chunk = (out / "chunks" / "chunk-001.md").read_text(encoding="utf-8")
        self.assertIn("## Moment 1 · owner", chunk)
        # a well-formed label file passes check; a bad label is named
        labels = ["COUNTS owner=2 signal=%d report=1" % len(matched)]
        for m in moments:
            label = {"owner": "B", "signal": "none", "report": "skipped"}[m["kind"]]
            labels.append(f"{m['id']} | {m['kind']} | {label} | did x | \"words\" | high")
        label_file = out / "labels" / "chunk-001.txt"
        label_file.parent.mkdir()
        label_file.write_text("\n".join(labels) + "\n", encoding="utf-8")
        code, f, err = run(["check", str(out)])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["owner:B"], ["2"])
        label_file.write_text("\n".join(labels[:-1]) + "\n", encoding="utf-8")
        code, f, err = run(["check", str(out)])
        self.assertEqual(code, 1)
        self.assertIn("moments without a line", err)
        self.assertEqual(f, {})

    def test_codex_ignite_opencode(self):
        codex = codex_record(self.home)
        code, f, err = run(["extract", str(codex), "--out", str(self.home / "c")])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["harness"], ["codex"])
        self.assertEqual(f["owner_moments"], ["1"])       # the AGENTS.md injection is skipped
        self.assertEqual(f["signals"], ["2"])             # env | grep, permission denied
        ignite = ignite_record(self.home)
        code, f, err = run(["extract", str(ignite), "--out", str(self.home / "i")])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["harness"], ["ignite"])
        moments = json.loads((self.home / "i" / "moments.json").read_text(encoding="utf-8"))["moments"]
        self.assertEqual(moments[0]["agent_before"], "Sent the quote.")
        self.assertEqual(moments[0]["text"], "não foi isso que eu pedi")
        oc = opencode_record(self.home)
        code, f, err = run(["extract", oc, "--out", str(self.home / "o")])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["harness"], ["opencode"])
        self.assertEqual(f["signals"], ["2"])             # --force, rejected

    def test_locate_and_transcript(self):
        claude_record(self.home)
        codex_record(self.home)
        opencode_record(self.home)
        code, f, err = run(["locate", "--marker", "sweep-marker abc123"])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["records"], ["1"])
        self.assertEqual(f["harness"], ["claude"])
        self.assertEqual(f["cwd"], ["/work"])
        code, f, err = run(["locate", "--marker", "sweep-marker oc9"])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["harness"], ["opencode"])
        code, f, err = run(["locate", "--marker", "nowhere-zzz"])
        self.assertEqual(code, 1)
        self.assertIn("no session record", err)
        ignite = ignite_record(self.home)
        os.environ["RBTV_AGENT_HOME"] = str(self.home / "agent")
        os.environ["IGNITE_CONVERSATION"] = "T:C:1"
        code, f, err = run(["locate", "--marker", "nowhere-zzz"])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["record"], [str(ignite)])
        code, f, err = run(["transcript", str(self.home / ".claude/projects/-work/s1.jsonl"), str(ignite),
                            "--out", str(self.home / "t")])
        self.assertEqual(code, 0, err)
        self.assertEqual(f["records"], ["2"])
        text = (self.home / "t" / "chunks" / "chunk-001.md").read_text(encoding="utf-8")
        self.assertIn("USER: please fix the counter", text)
        self.assertIn("CALL Bash:", text)
        self.assertRegex(text, r"^00001: # claude", )

    def test_failures_print_nothing_on_stdout(self):
        code, f, err = run(["extract", str(self.home / "missing.jsonl"), "--out", str(self.home / "x")])
        self.assertEqual(code, 1)
        self.assertEqual(f, {})
        self.assertIn("next:", err)
        code, f, err = run(["check", str(self.home / "nope")])
        self.assertEqual(code, 1)
        self.assertIn("no moments.json", err)


if __name__ == "__main__":
    unittest.main()
