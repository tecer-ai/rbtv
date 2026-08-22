#!/usr/bin/env python3
"""delta-anchors — verify an authoring seat's delta file against its target files, and apply it.

A delta names its target and quotes the text it replaces VERBATIM out of that target. No line
numbers: a line number is a pointer that re-derives between authoring and application, and that
re-derivation is what this tool exists to delete. See the capability card for the format.
"""
import argparse
import json
import os
import re
import sys

HEADING_RE = re.compile(r"^#{1,6} \S", re.M)


class Broken(Exception):
    """A precondition failed — exit 2, nothing was checked."""


def parse_deltas(path):
    """Return [{id, target, source, from, to, errors}] from a delta file."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        raise Broken("delta file unreadable: %s" % exc)
    blocks, cur = [], None
    for line in text.splitlines(keepends=True):
        m = re.match(r"^##\s+delta\s+(\S+)\s*$", line)
        if m:
            cur = {"id": m.group(1), "target": None, "source": None, "body": ""}
            blocks.append(cur)
        elif cur is not None:
            cur["body"] += line
    if not blocks:
        raise Broken("no `## delta <id>` section found in %s" % path)
    for b in blocks:
        b["errors"] = []
        for key in ("target", "source"):
            m = re.search(r"^%s:[ \t]*(.+?)[ \t]*$" % key, b["body"], re.M)
            if m:
                b[key] = m.group(1)
        for fence in ("from", "to"):
            b[fence] = _fenced(b["body"], fence, b["errors"])
        if not b["target"]:
            b["errors"].append("missing `target:`")
        if b["from"] is not None and b["from"].strip() == "":
            b["errors"].append("empty `from` block")
    return blocks


def _fenced(body, name, errors):
    """Extract the ```<name> block. Content may not itself contain a bare ``` line."""
    m = re.search(r"^```%s[ \t]*\n(.*?)^```[ \t]*$" % name, body, re.M | re.S)
    if not m:
        errors.append("missing or unterminated ```%s block" % name)
        return None
    content = m.group(1)
    return content[:-1] if content.endswith("\n") else content


def resolve(goal, rel):
    """Resolve a target path inside the goal folder. Refuses any escape."""
    goal_abs = os.path.realpath(goal)
    full = os.path.realpath(os.path.join(goal_abs, rel))
    if full != goal_abs and not full.startswith(goal_abs + os.sep):
        return None
    return full


def check_delta(d, goal, texts):
    """Return [(code, detail)] for one delta. Every finding, never first-failure."""
    out = []
    if d["errors"]:
        return [("malformed-delta", "; ".join(d["errors"]))]
    full = resolve(goal, d["target"])
    if full is None or not os.path.isfile(full):
        return [("target-missing", "%s does not resolve to a file under the goal folder" % d["target"])]
    if d["target"].startswith("planning/current/seats/"):
        src = d["source"] or ""
        ok = src.startswith("none —") or src.startswith("none -")
        if not ok and src:
            ok = resolve(goal, src) is not None and os.path.isfile(resolve(goal, src))
        if not ok:
            out.append(("source-not-routed", "a seat file is a rendering: name the `source:` "
                        "artifact this change must also land in, or `source: none — <reason>`"))
    text = texts.setdefault(full, open(full, encoding="utf-8").read())
    n_from = text.count(d["from"])
    n_to = text.count(d["to"]) if d["to"] else 0
    if n_from == 0 and n_to > 0:
        out.append(("already-applied", "the `to` text is already present and the `from` text is not"))
    elif n_from != 1:
        if n_from == 0:
            out.append(("anchor-absent", "the `from` text does not occur in %s" % d["target"]))
        else:
            out.append(("anchor-ambiguous", "the `from` text occurs %d times in %s" % (n_from, d["target"])))
    return out


def section_of(text, index):
    heads = [m for m in HEADING_RE.finditer(text) if m.start() <= index]
    return text[heads[-1].start():text.index("\n", heads[-1].start())] if heads else ""


def run_check(deltas, goal):
    texts, findings = {}, []
    for d in deltas:
        for code, detail in check_delta(d, goal, texts):
            findings.append((d["id"], d["target"] or "?", code, detail))
    return findings


def emit(findings, n):
    for did, target, code, detail in findings:
        print("FAIL %-24s delta %-4s %s: %s" % (code, did, target, detail))
    print("%d delta(s) checked, %d finding(s)" % (n, len(findings)))


def run_apply(deltas, goal, delta_path):
    m = re.search(r"round-(\d+)", os.path.basename(delta_path))
    if not m:
        raise Broken("delta filename must carry `round-<n>`: %s" % os.path.basename(delta_path))
    findings = run_check(deltas, goal)
    if findings:
        emit(findings, len(deltas))
        print("REFUSED — apply is all-or-nothing; no target was modified.")
        return 1
    originals = {}

    def origin(d):
        full = resolve(goal, d["target"])
        return (full, originals.setdefault(full, open(full, encoding="utf-8").read()).index(d["from"]))

    bufs, record = {}, []
    for d in sorted(deltas, key=origin):
        full = resolve(goal, d["target"])
        text = bufs.setdefault(full, open(full, encoding="utf-8").read())
        if text.count(d["from"]) != 1:
            emit([(d["id"], d["target"], "anchor-ambiguous" if text.count(d["from"]) else "anchor-absent",
                   "an earlier delta in this file changed the anchor")], len(deltas))
            print("REFUSED — apply is all-or-nothing; no target was modified.")
            return 1
        start = text.index(d["from"])
        new = text[:start] + d["to"] + text[start + len(d["from"]):]
        bufs[full] = new
        record.append({"target": d["target"], "source": d["source"],
                       "start_line": new.count("\n", 0, start) + 1,
                       "end_line": new.count("\n", 0, start + len(d["to"])) + 1,
                       "section": section_of(new, start)})
    for full, text in bufs.items():
        open(full, "w", encoding="utf-8").write(text)
    out = os.path.join(goal, "planning", "current", "applied-deltas-round-%s.json" % m.group(1))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    print("applied %d delta(s) to %d file(s); wrote %s" % (len(deltas), len(bufs), out))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["check", "apply"])
    ap.add_argument("delta_file")
    ap.add_argument("--goal", required=True, help="the goal folder every `target:` resolves under")
    args = ap.parse_args(argv)
    try:
        if not os.path.isdir(args.goal):
            raise Broken("goal folder not found: %s" % args.goal)
        deltas = parse_deltas(args.delta_file)
        if args.command == "apply":
            return run_apply(deltas, args.goal, args.delta_file)
        findings = run_check(deltas, args.goal)
        emit(findings, len(deltas))
        return 1 if findings else 0
    except Broken as exc:
        print("BLOCKED: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
