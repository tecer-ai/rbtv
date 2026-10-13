#!/usr/bin/env python3
"""typesafe — TypeSafe typed judgments from one command.

The service has two operations: judge content against typed questions
(POST /v1/systemone) and list models (GET /v1/models). `ask` sends any
questions the service accepts; `yesno`, `choice` and `score` build the same
request for one question. The content to judge always arrives on standard
input, so every verb sits in a pipe.

The command inventory lives in the parser below and nowhere else: `--help`
and `<verb> --help` are the interface reference.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROG = "typesafe"                   # the command name on PATH once installed

INSTALL_RECORD_REL = Path(".rbtv") / "config" / "install.json"
ENV_FILE_REL = Path(".rbtv") / "config" / "env" / ".env"
KEY_ENV = "TYPESAFE_API_KEY"
BASE_URL_ENV = "TYPESAFE_BASE_URL"  # the provider SDKs' name; tests point it at a stub
DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"

SHORTCUT_ID = "answer"              # the question id yesno, choice and score send
TIMEOUT = 30                        # seconds per request
RETRY_STATUSES = (429, 529)         # rate limit and overload: the provider asks for backoff
RETRY_DELAYS = (1, 2, 4, 8)         # seconds, when the answer carries no Retry-After
PARALLEL = 8                        # requests in flight for --each and --each-file

EXIT_OK = 0
EXIT_FAILED = 1                     # the service call failed, for the run or for an item
EXIT_REFUSED = 2                    # refused before any call: usage, key, input
EXIT_BELOW = 3                      # answered, and no answer reached --at-least

STATUS_FIX = {
    401: f"check the value of {KEY_ENV}; create a key at https://console.typesafe.ai/",
    400: "correct what the detail names; `typesafe models` lists model names",
    422: "correct the request field the detail names; `typesafe ask --help` shows a questions file",
    429: "the rate limit held through every retry; run again later or send fewer items",
    529: "TypeSafe stayed overloaded through every retry; run again later",
}


class Failure(Exception):
    """A refusal or a failed call: what happened, the fix, and the exit status."""

    def __init__(self, kind, message, fix, status=None, detail=None):
        super().__init__(message)
        self.kind, self.message, self.fix = kind, message, fix
        self.status, self.detail = status, detail
        self.code = EXIT_FAILED if kind in ("service", "network") else EXIT_REFUSED

    def as_dict(self):
        return {"kind": self.kind, "message": self.message, "fix": self.fix,
                "status": self.status, "detail": self.detail}


# ───────────────────────────────────────────────────────────────────── the key

def env_file():
    """The installation's environment file: the installation is the first
    folder, from the working folder upward, holding `.rbtv/config/install.json`.
    None when the working folder is inside no installation."""
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if (folder / INSTALL_RECORD_REL).is_file():
            return folder / ENV_FILE_REL
    return None


def key_sources():
    path = env_file()
    if path is None:
        return f"${KEY_ENV} (this folder is inside no rbtv installation, so no environment file is read)"
    return f"${KEY_ENV} first, then the {KEY_ENV} line of {path}"


def api_key():
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key
    path = env_file()
    if path is not None and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?" + KEY_ENV + r"\s*=\s*(.*)$", line)
            if m and m.group(1).strip().strip("'\""):
                return m.group(1).strip().strip("'\"")
    where = f"add a line {KEY_ENV}=<key> to {path}" if path is not None else \
        f"run from a folder inside an rbtv installation whose {ENV_FILE_REL.as_posix()} holds {KEY_ENV}=<key>"
    raise Failure("key", f"no TypeSafe API key: {KEY_ENV} is empty in the environment and in the environment file",
                  f"export {KEY_ENV}=<key>, or {where}; create a key at https://console.typesafe.ai/")


# ───────────────────────────────────────────────────────────────── the service

def call(method, path, body=None):
    """One request to the service, retried on rate limit and overload."""
    key = api_key()
    base = (os.environ.get(BASE_URL_ENV, "").strip() or DEFAULT_BASE_URL).rstrip("/")
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Accept": "application/json", "User-Agent": f"rbtv-{PROG}"}
    for delay in (*RETRY_DELAYS, None):
        request = urllib.request.Request(base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")
            if exc.code in RETRY_STATUSES and delay is not None:
                after = exc.headers.get("Retry-After", "")
                time.sleep(float(after) if re.fullmatch(r"\d+(\.\d+)?", after) else delay)
                continue
            try:
                detail = json.loads(text)
            except ValueError:
                detail = text.strip() or None
            raise Failure("service", f"TypeSafe answered {exc.code} {exc.reason}",
                          STATUS_FIX.get(exc.code, "run again; if it repeats, read https://docs.typesafe.ai/api"),
                          status=exc.code, detail=detail)
        except ValueError:
            raise Failure("service", f"{base + path} answered with something that is not JSON",
                          f"check {BASE_URL_ENV}, which must be unset or the TypeSafe API root")
        except OSError as exc:                  # URLError, timeouts, refused connections
            raise Failure("network", f"could not reach {base}: {getattr(exc, 'reason', exc)}",
                          "check the network and run again")


# ────────────────────────────────────────────────────────────────── the inputs

def stdin_text():
    if sys.stdin.isatty():
        raise Failure("input", "nothing arrived on standard input",
                      f"pipe the content in: `cat FILE | {PROG} ...` or `{PROG} ... < FILE`")
    try:
        return sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Failure("input", f"standard input is not UTF-8 text ({exc.reason})",
                      "convert the content to UTF-8 text; the service takes text only")


def items(args):
    """The states to judge as (item label, state or Failure). One item unless
    --each or --each-file names many."""
    text = stdin_text()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if args.each:
        found = []
        for number, line in enumerate(lines, 1):
            try:
                found.append((f"line {number}", json.loads(line)))
            except ValueError as exc:
                found.append((f"line {number}", Failure(
                    "input", f"line {number} is not a JSON value ({exc})",
                    'write one JSON value per line, text as a quoted string: "some text"')))
        return found
    if args.each_file:
        found = []
        for line in lines:
            try:
                found.append((line, {"path": line, "content": Path(line).read_text(encoding="utf-8")}))
            except (OSError, UnicodeDecodeError) as exc:
                found.append((line, Failure("input", f"cannot read {line} as UTF-8 text ({exc})",
                                            "name existing text files, one path per line")))
        return found
    if not text.strip():
        raise Failure("input", "standard input is empty", "pipe in the content to judge")
    if args.state_json:
        try:
            return [(None, json.loads(text))]
        except ValueError as exc:
            raise Failure("input", f"--state-json was given and standard input is not JSON ({exc})",
                          "drop --state-json to send the content as text")
    return [(None, text)]


def questions_from_file(args):
    try:
        loaded = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise Failure("input", f"cannot read {args.questions} as JSON ({exc})",
                      f"write a JSON object of questions; `{PROG} ask --help` shows one")
    if not isinstance(loaded, dict) or not loaded:
        raise Failure("input", f"{args.questions} must hold a JSON object with at least one question",
                      f"`{PROG} ask --help` shows one")
    return loaded


def yesno_questions(args):
    if args.at_least is not None and not 0 <= args.at_least <= 1:
        raise Failure("usage", f"--at-least {args.at_least:g} is outside 0 to 1",
                      "give the lowest probability of yes that passes, such as 0.8")
    return {SHORTCUT_ID: {"type": "noul", "instructions": args.question}}


def choice_questions(args):
    criteria = {}
    for option in args.option:
        name, eq, meaning = option.partition("=")
        criteria[name.strip()] = meaning.strip() if eq else None
    if len(criteria) < 2 or "" in criteria:
        raise Failure("usage", "a choice needs at least two different, named options",
                      "repeat --option, once per option: --option billing --option technical")
    return {SHORTCUT_ID: {"type": "choice", "instructions": args.question, "criteria": criteria}}


def score_questions(args):
    top = len(args.level) - 1
    if top < 1:
        raise Failure("usage", "a score needs at least two levels",
                      "repeat --level from lowest to highest: --level calm --level annoyed --level furious")
    if args.at_least is not None and not 0 <= args.at_least <= top:
        raise Failure("usage", f"--at-least {args.at_least:g} is outside 0 to {top}, the levels given",
                      "levels count from 0 in the order given; give the lowest score that passes")
    return {SHORTCUT_ID: {"type": "score", "instructions": args.question, "criteria": args.level}}


# ───────────────────────────────────────────────────────────────── the results

def passes(args, answers):
    """Whether the one answer reaches --at-least; None when no threshold was given."""
    threshold = getattr(args, "at_least", None)
    if threshold is None:
        return None
    answer = answers[SHORTCUT_ID]
    return answer[answer["type"]] >= threshold


def answer_text(answer):
    kind = answer.get("type")
    if kind == "noul":
        return f"probability-of-yes {answer['noul']:.2f}"
    if kind == "choice":
        ranked = sorted(answer["probabilities"].items(), key=lambda pair: -pair[1])
        shown = ", ".join(f"{name} {p:.2f}" for name, p in ranked if p >= 0.01)
        return f"{answer['choice']}  confidence {answer['confidence']:.2f}  ({shown})"
    if kind == "score":
        shown = ", ".join(f"{level}: {p:.2f}" for level, p in answer["probabilities"].items())
        return f"{answer['score']:.2f}  confidence {answer['confidence']:.2f}  ({shown})"
    return json.dumps(answer, ensure_ascii=False)


def rows(pairs, indent=""):
    width = max(len(name) for name, _ in pairs)
    return [f"{indent}{name.ljust(width)}  {value}" for name, value in pairs]


def passed_text(args, answers, passed):
    answer = answers[SHORTCUT_ID]
    return f"{'yes' if passed else 'no'} ({answer[answer['type']]:.2f} {'>=' if passed else '<'} {args.at_least:g})"


def footer(model, usage):
    return [("model", model or "unknown"),
            ("tokens", f"{usage.get('input_tokens', 0)} in, {usage.get('output_tokens', 0)} out")]


def run_judgment(args):
    questions = args.build(args)
    states = items(args)
    many = args.each or args.each_file

    def judge(item):
        label, state = item
        try:
            if isinstance(state, Failure):
                raise state
            return label, call("POST", "/v1/systemone",
                               {"state": state, "model": args.model, "questions": questions})
        except Failure as failure:
            if not many:
                raise
            return label, failure

    with ThreadPoolExecutor(PARALLEL) as pool:
        judged = list(pool.map(judge, states))

    if not many:
        response = judged[0][1]
        passed = passes(args, response["answers"])
        if args.json:
            print(json.dumps(response if passed is None else {**response, "passed": passed}, ensure_ascii=False))
        else:
            pairs = [(qid, answer_text(answer)) for qid, answer in response["answers"].items()]
            if passed is not None:
                pairs.append(("passed", passed_text(args, response["answers"], passed)))
            print("\n".join(rows(pairs + footer(response.get("model"), response.get("usage", {})))))
        return EXIT_BELOW if passed is False else EXIT_OK

    results, usage, model = [], {"input_tokens": 0, "output_tokens": 0}, None
    for index, (label, outcome) in enumerate(judged, 1):
        if isinstance(outcome, Failure):
            results.append({"item": label, "index": index, "error": outcome.as_dict()})
            continue
        model = outcome.get("model", model)
        for field in usage:
            usage[field] += outcome.get("usage", {}).get(field, 0)
        result = {"item": label, "index": index, "answers": outcome["answers"]}
        passed = passes(args, outcome["answers"])
        if passed is not None:
            result["passed"] = passed
        results.append(result)

    failed = sum("error" in result for result in results)
    summary = {"items": len(results), "answered": len(results) - failed, "failed": failed}
    gated = getattr(args, "at_least", None) is not None
    if gated:
        summary["passed"] = sum(result.get("passed", False) for result in results)
    if args.json:
        print(json.dumps({"summary": summary, "results": results, "model": model, "usage": usage},
                         ensure_ascii=False))
    else:
        lead = f"{summary['items']} items: {summary['answered']} answered, {failed} failed"
        if gated:
            lead += f", {summary['passed']} passed (at least {args.at_least:g})"
        out = [lead]
        single = len(questions) == 1
        if single and results:
            pairs = []
            for result in results:
                if "error" in result:
                    pairs.append((result["item"], f"failed: {result['error']['message']}"))
                else:
                    text = answer_text(next(iter(result["answers"].values())))
                    if gated:
                        text = f"{'passed' if result['passed'] else '-':6}  {text}"
                    pairs.append((result["item"], text))
            out += rows(pairs)
        elif results:
            for result in results:
                out.append(result["item"])
                if "error" in result:
                    out.append(f"  failed: {result['error']['message']}")
                else:
                    out += rows([(qid, answer_text(a)) for qid, a in result["answers"].items()], "  ")
        if summary["answered"]:
            out += rows(footer(model, usage))
        print("\n".join(out))
    if failed:
        return EXIT_FAILED
    return EXIT_BELOW if gated and not summary["passed"] else EXIT_OK


def run_models(args):
    listed = call("GET", "/v1/models")
    if args.json:
        print(json.dumps(listed, ensure_ascii=False))
    elif not listed.get("models"):
        print("no models listed for this key")
    else:
        print("\n".join(rows([(str(model.get("name")), f"{model.get('release_date', '')}  {model.get('description', '')}".strip())
                              for model in listed["models"]])))
    return EXIT_OK


# ────────────────────────────────────────────────────────────────── the parser

class Parser(argparse.ArgumentParser):
    def error(self, message):
        # A usage refusal is a Failure like any other, so --json callers get one JSON value.
        fail(Failure("usage", message, f"`{self.prog} --help` shows the accepted forms"),
             "--json" in sys.argv[1:])
        sys.exit(EXIT_REFUSED)


def fail(failure, as_json):
    if as_json:
        print(json.dumps({"error": failure.as_dict()}, ensure_ascii=False))
        return
    print(f"{PROG}: {failure.message}", file=sys.stderr)
    if failure.detail is not None:
        print(f"  detail: {json.dumps(failure.detail, ensure_ascii=False)}", file=sys.stderr)
    print(f"  fix: {failure.fix}", file=sys.stderr)


EXITS = """exit status:
  0  the service answered (and, with --at-least, an answer passed)
  1  the service call failed, for the run or for at least one item
  2  refused before any call: usage, missing key, unreadable input
  3  answered, and no answer reached --at-least"""

INPUT = """content:
  The content to judge arrives on standard input and is sent as text.
  --state-json   standard input is one JSON value; send it structured
  --each         standard input is JSON Lines; each line is one item to judge
  --each-file    standard input is file paths, one per line; each file is one
                 item, sent as {"path": ..., "content": ...}
  Items are judged up to 8 at a time and reported in input order."""

ASK_EXAMPLE = """a questions file is a JSON object; you choose each key, and the answer
comes back under it. The three question types:
  {
    "urgent":      {"type": "noul",   "instructions": "Does this convey urgency?"},
    "department":  {"type": "choice", "instructions": "Which team should handle this?",
                    "criteria": {"billing": "payments, refunds", "technical": null}},
    "frustration": {"type": "score",  "instructions": "How frustrated is the writer?",
                    "criteria": ["calm", "frustrated", "very angry"]}
  }
Every field the service accepts is passed through unchanged, including structured
instructions and criteria: https://docs.typesafe.ai/api

example:
  cat mail.txt | typesafe ask --questions triage.json"""

OUTPUT = """output:
  One line per question: its key, then the answer.
    probability-of-yes 0.95        a yes/no answer; 0.50 means undecided, not half true
    billing  confidence 0.81  (…)  a choice: the option, then each option's probability
    1.05  confidence 0.92  (…)     a score: the position on the levels, counted from 0
  --json prints one JSON value instead: the service's answer as it arrived (it
  calls a yes/no answer "noul": {"type": "noul", "noul": 0.95}), or
  for many items {"summary", "results", "model", "usage"}. A failure under
  --json is {"error": {"kind", "message", "fix", "status", "detail"}} on
  standard output; without --json it is text on standard error."""


def build_parser():
    root = Parser(
        prog=PROG, formatter_class=argparse.RawDescriptionHelpFormatter,
        description="TypeSafe typed judgments: ask yes/no, pick-one and rating questions about\n"
                    "a piece of content and get probabilities back, not prose.",
        epilog=f"first use:\n  cat mail.txt | {PROG} yesno \"Does this message need a reply today?\"\n"
               f"  {PROG} <verb> --help   inputs, output and examples of one verb\n\n"
               f"key: {key_sources()}.\n     --help needs no key.\n\n{EXITS}")
    verbs = root.add_subparsers(dest="verb", metavar="<verb>", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true", help="print one JSON value instead of text")
    judging = argparse.ArgumentParser(add_help=False, parents=[shared])
    judging.add_argument("--model", default=DEFAULT_MODEL, metavar="NAME",
                         help=f"the model that answers (default {DEFAULT_MODEL}; `{PROG} models` lists names)")
    source = judging.add_mutually_exclusive_group()
    source.add_argument("--state-json", action="store_true", help="send standard input as one JSON value")
    source.add_argument("--each", action="store_true", help="judge each JSON line of standard input")
    source.add_argument("--each-file", action="store_true", help="judge each file named on standard input")

    def verb(name, summary, build, epilog, gate=None):
        sub = verbs.add_parser(name, help=summary, description=summary[0].upper() + summary[1:] + ".",
                               parents=[judging], formatter_class=argparse.RawDescriptionHelpFormatter,
                               epilog=f"{epilog}\n\n{INPUT}\n\n{OUTPUT}\n\n{EXITS}")
        sub.set_defaults(run=run_judgment, build=build)
        if gate:
            sub.add_argument("--at-least", type=float, metavar="N", help=gate)
        return sub

    ask = verb("ask", "judge the content against every question in a file", questions_from_file, ASK_EXAMPLE)
    ask.add_argument("--questions", required=True, metavar="FILE", help="a JSON file of questions (see below)")

    yesno = verb("yesno", "ask one yes/no question about the content", yesno_questions,
                 "examples:\n  cat mail.txt | typesafe yesno \"Does this message need a reply today?\"\n"
                 "  cat mail.txt | typesafe yesno \"Is this urgent?\" --at-least 0.8 && echo urgent\n"
                 "  ls notes/*.md | typesafe yesno \"Would this file help plan a trip to Lisbon?\" --each-file",
                 gate="exit 0 when the probability of yes is at least N (0 to 1), else exit 3; "
                      "with many items, exit 0 when any item passes")
    yesno.add_argument("question", metavar="QUESTION", help="the yes/no question, as one quoted argument")

    choice = verb("choice", "pick one option for the content", choice_questions,
                  "example:\n  cat mail.txt | typesafe choice \"Which team should handle this?\" \\\n"
                  "      --option \"billing=payments, invoices, refunds\" --option technical --option sales")
    choice.add_argument("question", metavar="QUESTION", help="what to decide, as one quoted argument")
    choice.add_argument("--option", action="append", default=[], metavar="NAME[=MEANING]",
                        help="one option, repeated once per option (2 to 255); text after = says what the option means")

    score = verb("score", "rate the content on ordered levels", score_questions,
                 "example:\n  cat mail.txt | typesafe score \"How frustrated is the writer?\" \\\n"
                 "      --level calm --level frustrated --level \"very angry\"",
                 gate="exit 0 when the score is at least N (levels count from 0), else exit 3; "
                      "with many items, exit 0 when any item passes")
    score.add_argument("question", metavar="QUESTION", help="what to rate, as one quoted argument")
    score.add_argument("--level", action="append", default=[], metavar="TEXT",
                       help="one level, repeated from lowest to highest (2 to 10); each describes a concrete situation")

    models = verbs.add_parser("models", help="list the model names this key can use", parents=[shared],
                              description="List the model names this key can use in --model, with release date "
                                          "and description. A versioned name such as jev-1.13.0 is accepted "
                                          "even when only its alias is listed.",
                              formatter_class=argparse.RawDescriptionHelpFormatter,
                              epilog="exit status:\n  0  listed\n  1  the service call failed\n"
                                     "  2  refused before any call: usage, missing key")
    models.set_defaults(run=run_models)
    return root


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        return args.run(args)
    except Failure as failure:
        fail(failure, args.json)
        return failure.code


if __name__ == "__main__":
    sys.exit(main())
