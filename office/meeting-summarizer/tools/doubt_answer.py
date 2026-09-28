#!/usr/bin/env python3
"""doubt-answer — the owner-doubt ledger for a chat-transport-free cycle runner.

The old channel_runtime.py asked a doubt and applied a settled answer through ITS
OWN chat bridge (channel_transport.py): a Slack thread per meeting, a message log,
a reply log. The 0.2 primary agent has no such bridge — the owner's answer arrives
as the agent's own next conversation turn, and the question is asked through the
agent's own `replies`. What survives the transport's removal is the bookkeeping
that was never Slack-shaped to begin with: `doubts.jsonl` (per_meeting_job.py's
handoff row, unchanged) says WHICH terms are open; this tool tracks which of them
the agent has already asked (`asked-doubts.jsonl`) and which are answered
(`resolved-doubts.jsonl`), and does the one non-trivial piece of "apply the
answer" — the same amendment re-entry channel_runtime.py's `_apply_one` used,
minus the chat message it posted around it.

Three commands:

  list-open   --state DIR
              every (meeting, term) with an open doubt, not yet asked and not
              yet resolved. The agent groups these into ONE `replies` question.

  mark-asked  --meeting-key K --term T --state DIR
              record that this cycle's grouped question covered this term, so a
              later cycle never asks it again while it is still unanswered.

  apply       --meeting-key K --term T --answer-text A
              --config-root DIR --checkout-root DIR --state DIR [--timeout N]
              correct the one summary that raised this doubt, through the
              summarizer skill's amendment mode (the same re-entry point
              per_meeting_job.py's first pass used), then commit and push in
              this call. Proof is the file: the doubt marker's absence on disk
              afterward, never the amendment turn's own report.

`amendment_prompt`, `still_carries`, `marker_for` and `summary_file` below are
moved here from the old channel_runtime.py (the Slack-orchestration module this
tool replaces the ask/apply half of) rather than imported from it: channel_runtime.py
carries no replacement need of its own — the 0.2 agent's `replies`/`post` cover
its Slack-posting half — so it is not part of this capability at all.

Run with --help for the command surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import per_meeting_job
import publish_job

# New stores this tool owns, beside per_meeting_job.py's doubts.jsonl in the same
# state directory. Locations are the caller's `--state`, never a literal here.
RESOLVED = "resolved-doubts.jsonl"
ASKED = "asked-doubts.jsonl"

EXIT_OK = 0
EXIT_VERDICT = 1   # ran fine, the doubt did not resolve
EXIT_REFUSED = 2   # could not run


def refuse(what: str, fix: str) -> None:
    print(f"doubt-answer refused: {what}\n  fix: {fix}", file=sys.stderr)
    raise SystemExit(EXIT_REFUSED)


# ------------------------------------------------------------------- the ledger
def list_open(state: Path) -> list[dict]:
    """Every open doubt: raised, not yet asked, not yet resolved."""
    resolved = {(r["meeting-key"], r["term"]) for r in per_meeting_job.read_jsonl(state / RESOLVED)}
    asked = {(r["meeting-key"], r["term"]) for r in per_meeting_job.read_jsonl(state / ASKED)}
    open_doubts = []
    for row in per_meeting_job.read_jsonl(state / per_meeting_job.DOUBTS):
        key = row["meeting-key"]
        for doubt in row["marker"]["doubts"]:
            term = doubt["term"]
            if (key, term) in resolved or (key, term) in asked:
                continue
            open_doubts.append({"meeting-key": key, "term": term, "guess": doubt["guess"],
                                "entity": row["entity"], "excerpt": doubt.get("excerpt", "")})
    return open_doubts


def mark_asked(state: Path, meeting_key: str, term: str) -> dict:
    row = {"meeting-key": meeting_key, "term": term, "asked-at": per_meeting_job.now_stamp()}
    per_meeting_job.append_jsonl(state / ASKED, row)
    return row


# -------------------------------------------------------- the amendment re-entry
def summary_file(checkout_root: Path, ref: dict) -> Path:
    return Path(checkout_root) / ref["repo"] / ref["path"]


def marker_for(term: str) -> str:
    """The marker's term field, per the doubt-flag-marker seam's const grammar."""
    return f"term={term}"


def still_carries(path: Path, term: str) -> bool:
    """Does the summary on disk STILL carry this term's doubt marker?

    The one test of whether an amendment landed. The skill's own closing report
    is not consulted: a run that says it amended and left the marker in place
    has not amended, and this is the assertion that says so.
    """
    try:
        return marker_for(term) in Path(path).read_text(encoding="utf-8")
    except OSError:
        return True


def amendment_prompt(skill: str, summary: Path, transcript: str,
                     answers: list[tuple[str, str]]) -> str:
    """The amendment-mode invocation text: the summary, the transcript, and one
    "Term in doubt" / "Owner's answer" pair per answered term."""
    pairs = [line for term, answer in answers
             for line in (f"Term in doubt: {term}", f"Owner's answer: {answer}")]
    return "\n".join([
        f"Read and execute {skill}",
        "",
        "Operating scope: the CLAUDE.md in the current working directory. Its `## Name Glossary`",
        "section declares the glossary this run must load and write back to.",
        "",
        "The owner has answered a term that was left in doubt when this meeting was",
        "summarized earlier.",
        "",
        f"Summary already written: {summary}",
        f"Transcript: {transcript}",
        *pairs,
        "",
        "Execute in **amendment mode**.",
    ])


# ------------------------------------------------------------------- the apply
def apply_answer(*, meeting_key: str, term: str, answer_text: str, config_root: Path,
                 checkout_root: Path, state: Path, timeout: int = 900) -> dict:
    """Correct the one summary that raised this doubt. Returns `landed` truthfully.

    Mirrors channel_runtime.py's `_apply_one`, narrowed to one (meeting, term)
    pair instead of a whole settled-terms sweep — the 0.2 agent has no per-meeting
    Slack thread to batch by, so it calls this once per answered term.
    """
    config_root, checkout_root, state = Path(config_root), Path(checkout_root), Path(state)
    row = next((r for r in per_meeting_job.read_jsonl(state / per_meeting_job.DOUBTS)
               if r["meeting-key"] == meeting_key), None)
    if row is None:
        return {"landed": False, "why": f"no doubts handoff row for meeting {meeting_key!r}"}
    if not any(d["term"] == term for d in row["marker"]["doubts"]):
        return {"landed": False,
                "why": f"meeting {meeting_key!r} carries no open doubt for term {term!r}"}

    summary = summary_file(checkout_root, row["marker"]["summary"])
    if not summary.is_file():
        return {"landed": False, "why": f"the summary is not on disk at {summary}"}
    work = Path(row["work"])
    if not work.is_dir():
        return {"landed": False, "why": f"the summarizer operating scope {work} does not exist"}

    config = per_meeting_job.load_config(config_root)
    skill = per_meeting_job.skill_for(row["entity"], config["skill-bindings"])
    prompt = amendment_prompt(skill, summary, row["transcript"],
                                              [(term, answer_text)])

    ref = row["marker"]["summary"]
    target = publish_job.target_for(ref["repo"], publish_job.load_targets(config_root))
    checkout = checkout_root / ref["repo"]
    owned = target["regime"] == "git"

    with publish_job.checkout_lock(checkout):
        if owned:
            publish_job.sync(target, checkout)
        before = publish_job.dirty_paths(checkout) if owned else set()
        invocation = per_meeting_job.invocation_of(config)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_dir = state / "amendments" / f"{meeting_key}-{term}-{stamp}"
        outcome = per_meeting_job.invoke_agent(prompt, work, log_dir, timeout, invocation)
        if outcome.get("exit") != 0:
            return {"landed": False,
                    "why": f"the amendment invocation exited {outcome.get('exit')}"
                           f"{': ' + outcome['why'] if outcome.get('why') else ''}"}
        if still_carries(summary, term):
            return {"landed": False,
                    "why": "the invocation reported no error but the doubt marker is still "
                           "in the summary on disk — the correction did not land"}

        dirty = publish_job.dirty_paths(checkout)
        summary_rel = Path(ref["path"])
        siblings = sorted(p for p in dirty if Path(p).parent == summary_rel.parent
                          and Path(p).name.startswith(summary_rel.stem
                                                      + publish_job.TRANSCRIPT_INFIX))
        changed = sorted(dirty - before) if owned else []
        paths = list(dict.fromkeys([ref["path"], *siblings, *changed]))
        committed = publish_job.commit(
            target, checkout, paths,
            f"correct term {term!r} in the summary of meeting {meeting_key}")
        published = publish_job.push(target, checkout,
                                     [committed["head"]] if committed.get("head") else [])

    resolved_row = {"meeting-key": meeting_key, "term": term, "answer-text": answer_text,
                    "resolved-at": per_meeting_job.now_stamp(),
                    "published": bool(published.get("pushed"))}
    per_meeting_job.append_jsonl(state / RESOLVED, resolved_row)
    return {"landed": True, "committed": committed, "published": published}


# --------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doubt_answer",
        description="The owner-doubt ledger for a cycle runner with no chat transport of its "
                    "own: which doubts are open, which have been asked, and applying an answer.")
    sub = parser.add_subparsers(dest="operation", required=True)

    listing = sub.add_parser("list-open", help="every doubt not yet asked or resolved")
    listing.add_argument("--state", required=True, type=Path)

    asked = sub.add_parser("mark-asked", help="record that this cycle asked this term")
    asked.add_argument("--meeting-key", required=True)
    asked.add_argument("--term", required=True)
    asked.add_argument("--state", required=True, type=Path)

    apply_cmd = sub.add_parser("apply", help="apply the owner's answer to one term")
    apply_cmd.add_argument("--meeting-key", required=True)
    apply_cmd.add_argument("--term", required=True)
    apply_cmd.add_argument("--answer-text", required=True)
    apply_cmd.add_argument("--config-root", required=True, type=Path)
    apply_cmd.add_argument("--checkout-root", required=True, type=Path)
    apply_cmd.add_argument("--state", required=True, type=Path)
    apply_cmd.add_argument("--timeout", type=int, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.operation == "list-open":
        result = list_open(args.state)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return EXIT_OK
    if args.operation == "mark-asked":
        result = mark_asked(args.state, args.meeting_key, args.term)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return EXIT_OK
    result = apply_answer(meeting_key=args.meeting_key, term=args.term,
                          answer_text=args.answer_text, config_root=args.config_root,
                          checkout_root=args.checkout_root, state=args.state,
                          timeout=args.timeout)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return EXIT_OK if result.get("landed") else EXIT_VERDICT


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
