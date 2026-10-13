#!/usr/bin/env python3
"""The checks for typesafe.py — `python test_typesafe.py`, no framework, no network.

Every arm runs the real CLI as a subprocess inside a temporary installation,
against a local stub HTTP server reached through TYPESAFE_BASE_URL, with a
sentinel key only. Nothing here reads a real environment file or a real key.
The stub answers from the request it received, so a wrong request body shows
up as a wrong answer, and it records every request for the arms that count them.
"""

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

CLI = Path(__file__).resolve().parent / "typesafe.py"
SENTINEL = "sentinel-typesafe-key"
MODEL = "jev-test-1"

requests_seen = []
fail_next = []          # statuses the stub answers before it answers normally


def noul_for(state):
    """The stub's yes-probability: decided by the content, so each item differs."""
    text = json.dumps(state)
    return 0.95 if "urgent" in text else 0.10


class Stub(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, body, headers=()):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        if self.headers.get("Authorization") == f"Bearer {SENTINEL}":
            return True
        self.reply(401, {"error": "invalid key"})
        return False

    def do_GET(self):
        requests_seen.append(("GET", self.path, None))
        if self.authorized():
            self.reply(200, {"models": [{"name": "jev-latest", "release_date": "2026-01-01",
                                         "description": "stub flagship"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
        requests_seen.append(("POST", self.path, body))
        if not self.authorized():
            return
        if fail_next:
            return self.reply(fail_next.pop(0), {"error": "busy"}, [("Retry-After", "0")])
        if "too long" in json.dumps(body["state"]):
            return self.reply(422, {"detail": "state exceeds the context length"})
        answers = {}
        for qid, question in body["questions"].items():
            if question["type"] == "noul":
                answers[qid] = {"type": "noul", "noul": noul_for(body["state"])}
            elif question["type"] == "choice":
                names = list(question["criteria"])
                answers[qid] = {"type": "choice", "choice": names[0], "confidence": 0.81,
                                "probabilities": {n: (0.9 if i == 0 else 0.1 / (len(names) - 1))
                                                  for i, n in enumerate(names)}}
            else:
                levels = question["criteria"]
                answers[qid] = {"type": "score", "score": 1.05, "confidence": 0.92,
                                "legend": {str(i): t for i, t in enumerate(levels)},
                                "probabilities": {str(i): (0.95 if i == 1 else 0.05 / (len(levels) - 1))
                                                  for i in range(len(levels))}}
        self.reply(200, {"model": MODEL, "answers": answers,
                         "usage": {"input_tokens": 100, "output_tokens": 10}})


def run(argv, stdin="", key=SENTINEL, cwd=None, env_file_key=None, base=None):
    """Run the CLI. Returns (exit status, stdout, stderr)."""
    with tempfile.TemporaryDirectory() as home:
        folder = Path(cwd or home)
        if env_file_key is not None:
            (folder / ".rbtv" / "config" / "env").mkdir(parents=True)
            (folder / ".rbtv" / "config" / "install.json").write_text("{}", encoding="utf-8")
            (folder / ".rbtv" / "config" / "env" / ".env").write_text(
                f"# keys\nOTHER_TYPESAFE_API_KEY=wrong\nTYPESAFE_API_KEY='{env_file_key}'\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith("TYPESAFE_")}
        env["TYPESAFE_BASE_URL"] = base or BASE
        if key:
            env["TYPESAFE_API_KEY"] = key
        done = subprocess.run([sys.executable, str(CLI), *argv], input=stdin.encode("utf-8"),
                              capture_output=True, cwd=folder, env=env, timeout=60)
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")


def check_single_answers():
    code, out, err = run(["yesno", "Is this urgent?"], "urgent: payouts failing")
    assert (code, err) == (0, ""), (code, err)
    assert out.splitlines() == ["answer  probability-of-yes 0.95", f"model   {MODEL}", "tokens  100 in, 10 out"], out
    assert requests_seen[-1] == ("POST", "/v1/systemone", {
        "state": "urgent: payouts failing", "model": "jev-latest",
        "questions": {"answer": {"type": "noul", "instructions": "Is this urgent?"}}}), requests_seen[-1]

    code, out, _ = run(["choice", "Which team?", "--criteria", "billing=payments, refunds",
                        "--criteria", "technical", "--model", "jev-1.13.0", "--json"], "text")
    assert code == 0 and json.loads(out)["answers"]["answer"]["choice"] == "billing", out
    sent = requests_seen[-1][2]
    assert sent["model"] == "jev-1.13.0" and sent["questions"]["answer"]["criteria"] == {
        "billing": "payments, refunds", "technical": None}, sent

    code, out, _ = run(["score", "How angry?", "--criteria", "calm", "--criteria", "angry"], "text")
    assert code == 0 and out.startswith("answer  1.05  confidence 0.92  (0: 0.05, 1: 0.95)"), out
    assert requests_seen[-1][2]["questions"]["answer"]["criteria"] == ["calm", "angry"]


def check_ask_and_structured_state():
    with tempfile.TemporaryDirectory() as folder:
        questions = {"urgent": {"type": "noul", "instructions": "Urgent?"},
                     "team": {"type": "choice", "instructions": "Team?", "criteria": {"a": None, "b": None}}}
        path = Path(folder) / "q s.json"                      # a path with a space
        path.write_text(json.dumps({"questions": questions}), encoding="utf-8")
        code, out, _ = run(["ask", "--request", str(path), "--state-json"], '{"ticket": "urgent"}')
        assert code == 0 and out.splitlines()[:2] == [
            "urgent  probability-of-yes 0.95", "team    a  confidence 0.81  (a 0.90, b 0.10)"], out
        assert requests_seen[-1][2]["state"] == {"ticket": "urgent"}
        assert requests_seen[-1][2]["questions"] == questions

        code, out, err = run(["ask", "--request", str(path), "--state-json"], "not json")
        assert code == 2 and out == "" and "--state-json" in err, (code, out, err)
    code, _, err = run(["ask", "--request", "missing.json"], "text")
    assert code == 2 and "missing.json" in err, err


def check_json_request_and_files():
    with tempfile.TemporaryDirectory() as folder:
        for name, text in (("statement.csv", "urgent: 3 unmatched lines"), ("ledger.csv", "ledger rows"),
                           ("routing.md", "billing owns payments"), ("candidate.json", "a candidate record")):
            (Path(folder) / name).write_text(text, encoding="utf-8")
        request = {"state": {"statement": {"$file": "statement.csv"}, "ledger": {"$file": "ledger.csv"}},
                   "model": "jev-1.13.0",
                   "questions": {"flag": {"type": "noul", "instructions": "Urgent?"},
                                 "owner": {"type": "choice", "criteria": {"billing": None, "treasury": None},
                                           "instructions": {"question": "Who owns this, by `policy`?",
                                                            "policy": {"$file": "routing.md"}}}}}
        code, out, err = run(["ask", "--json"], json.dumps(request), cwd=folder)     # the whole request on stdin
        assert code == 0 and err == "" and json.loads(out)["answers"]["flag"]["noul"] == 0.95, (code, out, err)
        sent = requests_seen[-1][2]
        assert sent["state"] == {"statement": "urgent: 3 unmatched lines", "ledger": "ledger rows"}, sent["state"]
        assert sent["questions"]["owner"]["instructions"]["policy"] == "billing owns payments"
        assert sent["model"] == "jev-1.13.0" and set(sent) == {"state", "model", "questions"}, sent
        run(["ask", "--model", "jev-latest"], json.dumps(request), cwd=folder)       # the flag outranks the request
        assert requests_seen[-1][2]["model"] == "jev-latest"

        before = len(requests_seen)
        (Path(folder) / "full.json").write_text(json.dumps(request), encoding="utf-8")
        for argv, stdin, word in ((["ask"], json.dumps({"questions": request["questions"]}), "no \"state\""),
                                  (["ask"], json.dumps({"state": "x", "questions": {}}), "questions"),
                                  (["ask"], "not json", "not a JSON request"),
                                  (["ask"], json.dumps({"state": {"$file": "gone.csv"}, "questions": request["questions"]}),
                                   "gone.csv"),
                                  (["ask", "--request", "full.json", "--each"], '"x"\n', "its own state")):
            code, out, err = run(argv, stdin, cwd=folder)
            assert code == 2 and out == "" and word in err and len(requests_seen) == before, (argv, code, err)

        # the short verbs: several whole files in the state, and files in one question's instructions
        code, _, err = run(["yesno", "Does `statement` match `ledger`?", "--state", "statement=statement.csv",
                            "--state", "ledger=ledger.csv"], "", cwd=folder)
        assert code == 0, err
        assert requests_seen[-1][2]["state"] == {"statement": "urgent: 3 unmatched lines", "ledger": "ledger rows"}
        run(["yesno", "Is the state a duplicate of `candidate`?", "--instructions", "candidate=candidate.json"],
            "a record", cwd=folder)
        assert requests_seen[-1][2]["state"] == "a record" and requests_seen[-1][2]["questions"]["answer"][
            "instructions"] == {"question": "Is the state a duplicate of `candidate`?",
                                "candidate": "a candidate record"}, requests_seen[-1][2]
        run(["yesno", "Urgent?", "--each", "--state", "ledger=ledger.csv"], '{"id": 1}\n', cwd=folder)
        assert requests_seen[-1][2]["state"] == {"item": {"id": 1}, "ledger": "ledger rows"}
        for bad in ("ledger", "stdin=ledger.csv", "=ledger.csv"):
            code, _, err = run(["yesno", "Urgent?", "--state", bad], "x", cwd=folder)
            assert code == 2 and "NAME=FILE" in err, (bad, err)


def check_threshold_exit():
    assert run(["yesno", "Urgent?", "--at-least", "0.8"], "urgent")[0] == 0
    code, out, _ = run(["yesno", "Urgent?", "--at-least", "0.8"], "calm note")
    assert code == 3 and "passed  no (0.10 < 0.8)" in out, (code, out)
    code, out, _ = run(["yesno", "Urgent?", "--at-least", "0.8", "--json"], "calm note")
    assert code == 3 and json.loads(out)["passed"] is False, out
    assert run(["score", "How angry?", "--criteria", "a", "--criteria", "b", "--at-least", "1"], "x")[0] == 0
    before = len(requests_seen)
    code, _, err = run(["yesno", "Urgent?", "--at-least", "8"], "urgent")
    assert code == 2 and "outside 0 to 1" in err and len(requests_seen) == before, err


def check_many_items():
    lines = '"urgent: outage"\n\n{"note": "calm"}\nnot json\n"this is too long"\n'
    code, out, err = run(["yesno", "Urgent?", "--each", "--at-least", "0.8", "--json"], lines)
    result = json.loads(out)
    assert code == 0 and err == "", (code, err)             # an item passed, so the gate opens
    assert result["summary"] == {"items": 4, "answered": 2, "failed": 2, "passed": 1}, result["summary"]
    assert [r["item"] for r in result["results"]] == ["line 1", "line 2", "line 3", "line 4"]
    assert result["results"][0]["passed"] is True and result["results"][1]["passed"] is False
    assert result["results"][2]["error"]["kind"] == "input"
    assert result["results"][3]["error"]["status"] == 422
    assert result["usage"] == {"input_tokens": 200, "output_tokens": 20}

    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "a.md").write_text("urgent: outage — now", encoding="utf-8")
        (Path(folder) / "b.md").write_text("calm", encoding="utf-8")
        code, out, err = run(["yesno", "Urgent?", "--each-file", "--at-least", "0.8"],
                           "a.md\r\nb.md\ngone.md\n", cwd=folder)
        assert code == 0 and "gone.md failed" in err and out.splitlines()[:4] == [
            "3 items: 2 answered, 1 failed, 1 passed (at least 0.8)",
            "a.md     passed  probability-of-yes 0.95", "b.md     -       probability-of-yes 0.10"] + [out.splitlines()[3]], out
        assert out.splitlines()[3].startswith("gone.md  failed: cannot read gone.md"), out
        code, out, _ = run(["yesno", "Urgent?", "--each-file", "--at-least", "0.8"], "b.md\n", cwd=folder)
        assert code == 3 and out.startswith("1 item: 1 answered, 0 failed, 0 passed"), (code, out)
        code, out, err = run(["yesno", "Urgent?", "--each-file", "--at-least", "0.8"], "b.md\ngone.md\n", cwd=folder)
        assert code == 1 and err == "", (code, err)         # a failure and no pass: never a clean "no"
    sent = [body["state"] for _, _, body in requests_seen if body and isinstance(body["state"], dict)
            and body["state"].get("path") == "a.md"]
    assert sent and sent[0]["content"] == "urgent: outage — now", sent

    code, out, _ = run(["yesno", "Urgent?", "--each"], "")
    assert code == 0 and out.strip() == "0 items: 0 answered, 0 failed", (code, out)


def check_tiers_sort_and_given():
    lines = '"calm a"\n"urgent b"\nnot json\n"calm c"\n'
    code, out, err = run(["yesno", "Urgent?", "--each", "--tiers", "0.9,0.05", "--sort", "high", "--json"], lines)
    result = json.loads(out)
    assert code == 1 and result["summary"]["tiers"] == {"1": 1, "2": 2, "3": 0}, (code, result["summary"])
    assert [(r["item"], r.get("tier")) for r in result["results"]] == [
        ("line 2", 1), ("line 1", 2), ("line 4", 2), ("line 3", None)], result["results"]
    code, out, _ = run(["yesno", "Urgent?", "--each", "--tiers", "[0.9, 0.5]", "--sort", "low"], '"urgent b"\n"calm a"\n')
    assert code == 0 and out.splitlines()[:3] == [
        "2 items: 2 answered, 0 failed; tier 1: 1, tier 2: 0, tier 3: 1 (tiers at 0.9, 0.5)",
        "line 2  tier 3  probability-of-yes 0.10", "line 1  tier 1  probability-of-yes 0.95"], out

    code, out, err = run(["yesno", "Urgent?", "--each", "--tiers", "0.9,0.05", "--list-tier", "2"], lines)
    assert code == 0 and out.splitlines() == ["line 1", "line 4"] and "line 3 failed" in err, (code, out, err)
    code, out, _ = run(["yesno", "Urgent?", "--each", "--tiers", "0.9,0.05", "--list-tier", "3"], '"calm a"\n')
    assert (code, out) == (3, ""), (code, out)              # an empty tier: nothing to feed onward
    code, out, _ = run(["yesno", "Urgent?", "--tiers", "0.9,0.05"], "calm")
    assert code == 0 and "tier    2 of 3 (tiers at 0.9, 0.05)" in out, out
    before = len(requests_seen)
    for argv in (["--tiers", "0.5,0.9"], ["--tiers", "0.9,x"], ["--tiers", "0.9", "--at-least", "0.5"],
                 ["--tiers", "2,0.5"], ["--list-tier", "1"], ["--sort", "high"],
                 ["--each", "--tiers", "0.9", "--list-tier", "3"]):
        code, _, err = run(["yesno", "Urgent?", *argv], "calm")
        assert code == 2 and err and len(requests_seen) == before, (argv, code, err)

    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / "goal.txt").write_text("plan the outage review", encoding="utf-8")
        (Path(folder) / "a.md").write_text("calm", encoding="utf-8")
        assert run(["yesno", "Helps `goal`?", "--state", "goal=goal.txt"], "urgent", cwd=folder)[0] == 0
        assert requests_seen[-1][2]["state"] == {"stdin": "urgent", "goal": "plan the outage review"}
        assert run(["yesno", "Helps `goal`?", "--state", "goal=goal.txt", "--each-file"], "a.md\n", cwd=folder)[0] == 0
        assert requests_seen[-1][2]["state"] == {"path": "a.md", "content": "calm", "goal": "plan the outage review"}
        code, _, err = run(["yesno", "Helps?", "--state", "goal=gone.txt"], "urgent", cwd=folder)
        assert code == 2 and "gone.txt" in err, err


def check_shortcut_options():
    argv = ["choice", "Team?", "--criteria", "billing", "--criteria", "tech", "--criteria", "sales"]
    code, out, _ = run(argv, "x")                           # every option shown, zeros included
    assert code == 0 and out.startswith("answer  billing  confidence 0.81  (billing 0.90, tech 0.05, sales 0.05)"), out
    code, out, _ = run([*argv, "--top", "1"], "x")
    assert code == 0 and out.startswith("answer  billing  confidence 0.81  (billing 0.90, +2 more)"), out
    assert len(json.loads(run([*argv, "--top", "1", "--json"], "x")[1])["answers"]["answer"]["probabilities"]) == 3
    assert run([*argv, "--top", "0"], "x")[0] == 2

    run(["yesno", "Urgent?", "--criteria", "true=needs action today", "--criteria", "false=can wait"], "x")
    assert run(["yesno", "Urgent?", "--criteria", "maybe=perhaps"], "x")[0] == 2
    assert requests_seen[-1][2]["questions"]["answer"]["criteria"] == {
        "true": "needs action today", "false": "can wait"}, requests_seen[-1][2]
    code, out, _ = run(["choice", "Team?", "--criteria", "billing", "--criteria", "sales", "--expect", "billing"], "x")
    assert code == 0 and "passed  yes (expected billing)" in out, (code, out)
    code, out, _ = run(["choice", "Team?", "--criteria", "billing", "--criteria", "sales", "--expect", "sales"], "x")
    assert code == 3 and "passed  no (expected sales)" in out, (code, out)
    code, _, err = run(["choice", "Team?", "--criteria", "billing", "--criteria", "sales", "--expect", "ops"], "x")
    assert code == 2 and "billing, sales" in err, err


def check_failures():
    before = len(requests_seen)
    code, out, err = run(["yesno", "Urgent?"], "text", key=None)
    assert code == 2 and out == "" and "TYPESAFE_API_KEY" in err and len(requests_seen) == before, err
    code, out, err = run(["yesno", "Urgent?", "--json"], "text", key=None)
    assert code == 2 and err == "" and json.loads(out)["error"]["kind"] == "key", (out, err)

    code, out, err = run(["yesno", "Urgent?"], "text", key="wrong-key")
    assert code == 1 and out == "" and "401" in err, (code, err)
    assert "wrong-key" not in err and SENTINEL not in err

    code, out, err = run(["yesno", "Urgent?", "--json"], "this is too long")
    error = json.loads(out)["error"]
    assert code == 1 and err == "" and error["status"] == 422 and "context length" in error["detail"]["detail"]

    code, out, err = run(["yesno", "Urgent?"], "")
    assert code == 2 and "empty" in err, err
    code, out, err = run(["choice", "Which?", "--criteria", "only"], "text")
    assert code == 2 and "two" in err, err
    code, out, err = run(["yesno", "--json"], "text")           # usage error under --json
    assert code == 2 and err == "" and json.loads(out)["error"]["kind"] == "usage", (out, err)
    code, out, err = run(["yesno", "--bogus", "--", "--json"], "text")   # after -- it is a question, not a flag
    assert code == 2 and out == "" and "--bogus" in err, (out, err)

    closed = socket.socket()                                    # a port nothing listens on
    closed.bind(("127.0.0.1", 0))
    dead = f"http://127.0.0.1:{closed.getsockname()[1]}"
    closed.close()
    code, out, err = run(["yesno", "Urgent?"], "text", base=dead)
    assert code == 1 and out == "" and "could not reach" in err and SENTINEL not in err, (code, err)
    code, out, err = run(["models", "--json"], base=dead)
    assert code == 1 and err == "" and json.loads(out)["error"]["kind"] == "network", (out, err)


def check_retry_and_key_file():
    fail_next.extend([429, 529])
    before = len(requests_seen)
    code, out, _ = run(["yesno", "Urgent?"], "urgent")
    assert code == 0 and len(requests_seen) == before + 3, (code, out)

    code, out, err = run(["yesno", "Urgent?"], "urgent", key=None, env_file_key=SENTINEL)
    assert code == 0, err                                       # the exact-name line of the environment file


def check_models_and_help():
    code, out, _ = run(["models"])
    assert code == 0 and out.strip() == "jev-latest  2026-01-01  stub flagship", out
    assert json.loads(run(["models", "--json"])[1])["models"][0]["name"] == "jev-latest"
    before = len(requests_seen)
    for argv in (["-h"], ["--help"], ["yesno", "-h"], ["yesno", "q", "--help"], ["ask", "-h"],
                 ["choice", "-h"], ["score", "-h"], ["models", "-h"]):
        code, out, err = run(argv, key=None)
        assert code == 0 and out.startswith("usage: typesafe") and err == "", (argv, code, err)
    assert len(requests_seen) == before                          # help contacts nothing, needs no key
    code, out, _ = run(["yesno", "--", "-h"], "urgent")           # a literal question that looks like help
    assert code == 0 and requests_seen[-1][2]["questions"]["answer"]["instructions"] == "-h", out


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    BASE = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    checks = [check_single_answers, check_ask_and_structured_state, check_json_request_and_files,
              check_threshold_exit, check_many_items,
              check_tiers_sort_and_given, check_shortcut_options, check_failures, check_retry_and_key_file,
              check_models_and_help]
    for check in checks:
        check()
        print(f"ok  {check.__name__}")
    server.shutdown()
    print(f"{len(checks)} checks passed")
