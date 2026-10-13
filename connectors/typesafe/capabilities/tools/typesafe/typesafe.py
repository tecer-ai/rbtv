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
EXIT_BELOW = 3                      # every item answered, and none qualified

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
                  f"set {KEY_ENV} in the environment, or {where}; create a key at https://console.typesafe.ai/")


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


def given_text(args):
    if args.given is None:
        return None
    try:
        return Path(args.given).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Failure("input", f"cannot read {args.given} as UTF-8 text ({exc})",
                      "name an existing text file after --given")


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


def check_thresholds(args, top):
    for edge in ([] if args.at_least is None else [args.at_least]) + (args.tiers or []):
        if not 0 <= edge <= top:
            raise Failure("usage", f"threshold {edge:g} is outside 0 to {top}, the range of this answer",
                          f"give thresholds from 0 to {top}")


def yesno_questions(args):
    check_thresholds(args, 1)
    question = {"type": "noul", "instructions": args.question}
    criteria = {name: text for name, text in (("true", args.yes_means), ("false", args.no_means)) if text}
    if criteria:
        question["criteria"] = criteria
    return {SHORTCUT_ID: question}


def choice_questions(args):
    criteria = {}
    for option in args.option:
        name, eq, meaning = option.partition("=")
        criteria[name.strip()] = meaning.strip() if eq else None
    if len(criteria) < 2 or "" in criteria:
        raise Failure("usage", "a choice needs at least two different, named options",
                      "repeat --option, once per option: --option billing --option technical")
    if args.expect is not None and args.expect not in criteria:
        raise Failure("usage", f"--expect {args.expect} is not one of the options given",
                      f"expect one of: {', '.join(criteria)}")
    return {SHORTCUT_ID: {"type": "choice", "instructions": args.question, "criteria": criteria}}


def score_questions(args):
    top = len(args.level) - 1
    if top < 1:
        raise Failure("usage", "a score needs at least two levels",
                      "repeat --level from lowest to highest: --level calm --level annoyed --level furious")
    check_thresholds(args, top)
    return {SHORTCUT_ID: {"type": "score", "instructions": args.question, "criteria": args.level}}


# ───────────────────────────────────────────────────────────────── the results

def value_of(answer):
    return answer[answer["type"]]       # the number of a yes/no or score answer


def marks(args, answers):
    """What the caller's thresholds say about the one answer: {"passed": bool}
    under --at-least or --expect, {"tier": N} under --tiers, else nothing."""
    at_least, expect, tiers = (getattr(args, name, None) for name in ("at_least", "expect", "tiers"))
    if at_least is not None:
        return {"passed": value_of(answers[SHORTCUT_ID]) >= at_least}
    if expect is not None:
        return {"passed": answers[SHORTCUT_ID]["choice"] == expect}
    if tiers:
        return {"tier": 1 + sum(value_of(answers[SHORTCUT_ID]) < edge for edge in tiers)}
    return {}


def criterion(args):
    """The --at-least or --expect condition in words."""
    if getattr(args, "expect", None) is not None:
        return f"expected {args.expect}"
    return f"at least {args.at_least:g}"


def edges_text(args):
    return ", ".join(f"{edge:g}" for edge in args.tiers)


def check_options(args, many):
    tiers, list_tier = getattr(args, "tiers", None), getattr(args, "list_tier", None)
    if list_tier is not None and not (tiers and many and not args.json and 1 <= list_tier <= len(tiers) + 1):
        raise Failure("usage", "--list-tier N prints the items of one tier as plain names",
                      "give it with --tiers, with --each or --each-file, without --json, "
                      "and N from 1 to the number of tiers")
    if getattr(args, "sort", None) and not many:
        raise Failure("usage", "--sort orders many items", "add --each or --each-file")


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


def mark_rows(args, answers, mark):
    if "tier" in mark:
        return [("tier", f"{mark['tier']} of {len(args.tiers) + 1} (tiers at {edges_text(args)})")]
    if "passed" not in mark:
        return []
    word = "yes" if mark["passed"] else "no"
    if getattr(args, "expect", None) is not None:
        return [("passed", f"{word} ({criterion(args)})")]
    sign = ">=" if mark["passed"] else "<"
    return [("passed", f"{word} ({value_of(answers[SHORTCUT_ID]):.2f} {sign} {args.at_least:g})")]


def footer(model, usage):
    return [("model", model or "unknown"),
            ("tokens", f"{usage.get('input_tokens', 0)} in, {usage.get('output_tokens', 0)} out")]


def run_judgment(args):
    many = args.each or args.each_file
    check_options(args, many)
    questions = args.build(args)
    given = given_text(args)
    states = items(args)

    def judge(item):
        label, state = item
        try:
            if isinstance(state, Failure):
                raise state
            if given is not None:
                state = {"given": given, **state} if args.each_file else {"given": given, "content": state}
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
        mark = marks(args, response["answers"])
        if args.json:
            print(json.dumps({**response, **mark}, ensure_ascii=False))
        else:
            pairs = [(qid, answer_text(answer)) for qid, answer in response["answers"].items()]
            pairs += mark_rows(args, response["answers"], mark)
            print("\n".join(rows(pairs + footer(response.get("model"), response.get("usage", {})))))
        return EXIT_BELOW if mark.get("passed") is False else EXIT_OK

    results, usage, model = [], {"input_tokens": 0, "output_tokens": 0}, None
    for index, (label, outcome) in enumerate(judged, 1):
        if isinstance(outcome, Failure):
            results.append({"item": label, "index": index, "error": outcome.as_dict()})
            continue
        model = outcome.get("model", model)
        for field in usage:
            usage[field] += outcome.get("usage", {}).get(field, 0)
        results.append({"item": label, "index": index, "answers": outcome["answers"],
                        **marks(args, outcome["answers"])})

    order = getattr(args, "sort", None)
    if order:                           # failed items last, in input order
        sign = -1 if order == "high" else 1
        results.sort(key=lambda r: (1, 0) if "error" in r else (0, sign * value_of(r["answers"][SHORTCUT_ID])))
    failed = sum("error" in result for result in results)
    summary = {"items": len(results), "answered": len(results) - failed, "failed": failed}
    tiers, list_tier = getattr(args, "tiers", None), getattr(args, "list_tier", None)
    gated = getattr(args, "at_least", None) is not None or getattr(args, "expect", None) is not None
    if gated:
        summary["passed"] = sum(result.get("passed", False) for result in results)
    if tiers:
        summary["tiers"] = {str(n): sum(result.get("tier") == n for result in results)
                            for n in range(1, len(tiers) + 2)}
    qualified = summary["passed"] if gated else summary["tiers"][str(list_tier)] if list_tier else None
    if args.json:
        print(json.dumps({"summary": summary, "results": results, "model": model, "usage": usage},
                         ensure_ascii=False))
    elif list_tier:
        listed = [result["item"] for result in results if result.get("tier") == list_tier]
        if listed:
            print("\n".join(listed))
    else:
        lead = f"{summary['items']} item{'' if summary['items'] == 1 else 's'}: " \
               f"{summary['answered']} answered, {failed} failed"
        if gated:
            lead += f", {summary['passed']} passed ({criterion(args)})"
        if tiers:
            lead += "; " + ", ".join(f"tier {n}: {count}" for n, count in summary["tiers"].items()) + \
                    f" (tiers at {edges_text(args)})"
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
                    if tiers:
                        text = f"tier {result['tier']}  {text}"
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
    if failed and not args.json and (qualified or list_tier):
        for result in results:          # the failures a qualifying run would otherwise hide
            if "error" in result:
                print(f"{PROG}: {result['item']} failed: {result['error']['message']}", file=sys.stderr)
    if qualified:
        return EXIT_OK
    if failed:
        return EXIT_FAILED
    return EXIT_OK if qualified is None else EXIT_BELOW


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
        flags = sys.argv[1:]
        flags = flags[:flags.index("--")] if "--" in flags else flags    # after -- nothing is a flag
        fail(Failure("usage", message, f"`{self.prog} --help` shows the accepted forms"), "--json" in flags)
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
  0  the service answered; under --at-least, --expect or --list-tier, at least
     one item qualified (items that failed are then named on standard error)
  1  the service call failed: for the run, or for an item while none qualified
  2  refused before any call: usage, missing key, unreadable input
  3  every item was answered and none qualified"""

THRESHOLDS = """thresholds (one answer or many items):
  --at-least N     one line: pass or not, carried by the exit status
  --tiers N,N,...  sort answers into numbered tiers. Give the thresholds from
                   highest to lowest; tier 1 is at or above the first, tier 2
                   at or above the second, and the last tier is everything
                   below. Two thresholds make three tiers, and so on.
  --list-tier N    with --tiers and many items: print only the names of the
                   items in tier N, one per line, to feed another command
  --sort high|low  with many items: order them by the answer, highest or
                   lowest first; without it they keep the input order
  example: three tiers, then act on each
    ls matches/*.json | typesafe yesno "Do the two records describe the same payment?" \\
        --each-file --tiers 0.95,0.6 --json
    tier 1 (0.95 and up) can go through, tier 2 to a second check, tier 3 to a person"""

INPUT = """content:
  The content to judge arrives on standard input and is sent as text.
  --state-json   standard input is one JSON value; send it structured
  --each         standard input is JSON Lines; each line is one item to judge
  --each-file    standard input is file paths, one per line; each file is one
                 item, sent as {"path": ..., "content": ...}
  --given FILE   a text every item is judged against, such as a goal or a
                 policy. The content is then sent as {"given": ..., "content":
                 ...} and the question can name it: "Does this help with the
                 task in `given`?" Its tokens are paid once per item.
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
  A choice lists only the options with probability 0.01 or more; an option
  missing from the list was judged below that. --json carries every option.
  confidence, on a choice and a score, is not the probability of the answer.
  It says how far the probabilities are from an even split: 0 when every
  option is equally likely, 1 when one option holds all of it. With three
  options and the winner at 0.57, confidence is 0.35. Read the probability for
  how likely the answer is, and confidence for whether to act on it.
  --json prints one JSON value instead: the service's answer as it arrived (it
  calls a yes/no answer "noul": {"type": "noul", "noul": 0.95}), or
  for many items {"summary", "results", "model", "usage"}. A failure under
  --json is {"error": {"kind", "message", "fix", "status", "detail"}} on
  standard output; without --json it is text on standard error."""


def tier_edges(text):
    """--tiers: thresholds from highest to lowest, as 0.9,0.5 or the JSON list [0.9, 0.5]."""
    try:
        edges = [float(part) for part in text.strip("[] ").split(",")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a list of numbers such as 0.9,0.5")
    if edges != sorted(set(edges), reverse=True):
        raise argparse.ArgumentTypeError(f"{text!r} must go from highest to lowest, each number once")
    return edges


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
    judging.add_argument("--given", metavar="FILE", help="a text file sent with every item as `given`")

    def verb(name, summary, build, epilog, scale=None):
        sub = verbs.add_parser(name, help=summary, description=summary[0].upper() + summary[1:] + ".",
                               parents=[judging], formatter_class=argparse.RawDescriptionHelpFormatter,
                               epilog="\n\n".join(filter(None, [epilog, scale and THRESHOLDS, INPUT, OUTPUT, EXITS])))
        sub.set_defaults(run=run_judgment, build=build)
        if scale:                       # the verbs whose answer is a number
            bucket = sub.add_mutually_exclusive_group()
            bucket.add_argument("--at-least", type=float, metavar="N",
                                help=f"exit 0 when {scale} is at least N, else exit 3")
            bucket.add_argument("--tiers", type=tier_edges, metavar="N,N,...",
                                help="sort answers into numbered tiers by these thresholds, highest first")
            sub.add_argument("--list-tier", type=int, metavar="N", help="print only the names of the items in tier N")
            sub.add_argument("--sort", choices=("high", "low"), help="order many items by the answer")
        return sub

    ask = verb("ask", "judge the content against every question in a file", questions_from_file, ASK_EXAMPLE)
    ask.add_argument("--questions", required=True, metavar="FILE", help="a JSON file of questions (see below)")

    yesno = verb("yesno", "ask one yes/no question about the content", yesno_questions,
                 "examples:\n  cat mail.txt | typesafe yesno \"Does this message need a reply today?\"\n"
                 "  cat mail.txt | typesafe yesno \"Is this urgent?\" --at-least 0.8 && echo urgent\n"
                 "  ls notes/*.md | typesafe yesno \"Would this file help plan a trip to Lisbon?\" --each-file",
                 scale="the probability of yes (0 to 1)")
    yesno.add_argument("question", metavar="QUESTION", help="the yes/no question, as one quoted argument")
    yesno.add_argument("--yes-means", metavar="TEXT", help="what counts as a yes, when the question leaves room")
    yesno.add_argument("--no-means", metavar="TEXT", help="what counts as a no")

    choice = verb("choice", "pick one option for the content", choice_questions,
                  "example:\n  cat mail.txt | typesafe choice \"Which team should handle this?\" \\\n"
                  "      --option \"billing=payments, invoices, refunds\" --option technical --option sales")
    choice.add_argument("question", metavar="QUESTION", help="what to decide, as one quoted argument")
    choice.add_argument("--option", action="append", default=[], metavar="NAME[=MEANING]",
                        help="one option, repeated once per option (2 to 255); text after = says what the option means")
    choice.add_argument("--expect", metavar="NAME",
                        help="exit 0 when the option picked is NAME, else exit 3")

    score = verb("score", "rate the content on ordered levels", score_questions,
                 "example:\n  cat mail.txt | typesafe score \"How frustrated is the writer?\" \\\n"
                 "      --level calm --level frustrated --level \"very angry\"",
                 scale="the score (levels count from 0)")
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
