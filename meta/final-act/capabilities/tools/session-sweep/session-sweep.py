#!/usr/bin/env python3
"""session-sweep: the exact steps of the compound sweep over one session's record.

Verbs: locate (find this session's record by a marker), extract (the moments
a labeler reads), transcript (the visible events a checker reads), check (one
well-formed label file per chunk). Result fields print on standard output as
`name value` lines; a failed run prints nothing there and `error:` / `next:`
on standard error. Exit 0 success, 1 failed, 2 invalid invocation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

CHUNK_MOMENTS = 30
TRANSCRIPT_CHARS = 30000
TEXT_CAP = 2500
RESULT_CAP = 1500
REPORT_CAP = 6000
EDGE = 600  # a failure shows at the head or the tail of a result; prose in the middle is file content

# Patterns are the signals the compound method names. A match makes a moment;
# the labeler decides whether the match is a real signal or a word in a file.
DANGEROUS = re.compile(
    r"git\s+(pull|push|rebase|reset\s+--hard|checkout\s+--\s+\.|clean|stash|"
    r"filter-branch|commit\s+--amend)|--force(-with-lease)?\b|\brm\s+-[a-z]*r[a-z]*f?\b|"
    r"\bprintenv\b|(^|[;&|(]\s*)env\s*($|\|)|Format-Volume|Clear-Disk|\bdiskpart\b",
    re.IGNORECASE | re.MULTILINE)
REFUSED = re.compile(
    r"^REFUSED\b|\bpermission denied\b|\bnot allowed\b|\bnot permitted\b|\bok-already-used\b|"
    r"\b(was|were|is|are) (refused|denied|blocked|rejected)\b|\brefused (to|the|by|it)\b|\brejected\b|"
    r"\bdenied\b.*\b(permission|access|request)\b|\b(permission|access|request)\b.*\bdenied\b|"
    r"\buser (declined|rejected|denied)\b", re.IGNORECASE | re.MULTILINE)
FAILED = re.compile(
    r"^(error|fatal|Traceback|Exception|panic)\b|\berror:|\bfailed\b.*\b(with|to|exit|code|status)\b|"
    r"\bexit(ed)? (code |status )?[1-9]\d*\b|\bcommand not found\b|\bno such file\b|\bENOENT\b|"
    r"\buncertain\b|\bnot sent\b|\bTraceback \(most recent call last\)",
    re.IGNORECASE | re.MULTILINE)
WORKAROUND = re.compile(
    r"\bwork(ed|ing)? around\b|\bworkaround\b|\binstead,? i (ran|used|wrote|read|built|did|edited)\b|"
    r"\bcould ?n[o']t (find|locate)\b|\bcan ?n[o']t (find|locate)\b|\bno (such )?tool (for|exists|does)\b|"
    r"\bi skipped\b|\bskipping (the|that|this)\b|\bdid not load\b|\bwithout loading\b|"
    r"\bhad to (build|write|deduce|guess|work out)\b|\bbuilt it myself\b", re.IGNORECASE)


class Failure(Exception):
    def __init__(self, error: str, nxt: str):
        super().__init__(error)
        self.error = error
        self.next = nxt


def fail(error: str, nxt: str) -> int:
    sys.stderr.write(f"error: {error}\nnext: {nxt}\n")
    return 1


def out(name: str, value) -> None:
    print(f"{name} {value}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clip(text: str, cap: int) -> str:
    text = text or ""
    return text if len(text) <= cap else text[:cap] + " […]"


def iso(value) -> str:
    """One time form for every harness: ISO-8601 in UTC, or the value as given."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1e11 else value
        return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


# ---------------------------------------------------------------- records

def harness_of(record: str) -> str:
    """The harness a record spec belongs to, from its place and shape."""
    if "#" in record and record.split("#", 1)[0].endswith(".db"):
        return "opencode"
    path = Path(record)
    if not path.is_file():
        raise Failure(f"record not found: {record}", "pass the path the harness wrote, or run locate")
    parts = {p.lower() for p in path.parts}
    if path.suffix == ".jsonl":
        if ".codex" in parts:
            return "codex"
        if ".claude" in parts:
            return "claude"
        return sniff_jsonl(path)
    if path.suffix == ".md":
        return "ignite"
    raise Failure(f"cannot tell the harness of {record}",
                  "pass a Claude Code or Codex .jsonl, an Ignite history.md, or PATH.db#SESSION")


def sniff_jsonl(path: Path) -> str:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"session_meta"' in line or '"response_item"' in line:
                return "codex"
            if '"sessionId"' in line or '"isSidechain"' in line:
                return "claude"
    raise Failure(f"{path} is neither a Claude Code nor a Codex record",
                  "pass the record the harness wrote for this session")


def blocks_text(content, kinds=("text", "input_text", "output_text")) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") in kinds)
    return ""


def events_claude(path: Path) -> list[dict]:
    events = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"user"' not in line and '"assistant"' not in line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = d.get("type")
            if kind not in ("user", "assistant") or d.get("isMeta"):
                continue
            content = (d.get("message") or {}).get("content")
            base = {"t": iso(d.get("timestamp")), "sidechain": bool(d.get("isSidechain"))}
            if kind == "assistant" and isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "text" and b.get("text"):
                        events.append({**base, "role": "agent", "text": b["text"]})
                    elif b.get("type") == "tool_use":
                        events.append({**base, "role": "tool_call", "name": b.get("name", ""),
                                       "text": json.dumps(b.get("input", {}), ensure_ascii=False,
                                                          sort_keys=True)})
            elif kind == "user":
                if isinstance(content, list):
                    for b in content:
                        if not isinstance(b, dict):
                            continue
                        if b.get("type") == "tool_result":
                            events.append({**base, "role": "tool_result",
                                           "text": blocks_text(b.get("content"))})
                        elif b.get("type") == "text":
                            text = b.get("text", "")
                            if owner_text(text):
                                events.append({**base, "role": "owner", "text": text})
                elif isinstance(content, str):
                    typed = d.get("promptSource") in ("typed", "queued")
                    if typed or owner_text(content):
                        events.append({**base, "role": "owner", "text": content})
    return events


def owner_text(text: str) -> bool:
    """A user message the person wrote, not a harness insertion."""
    t = (text or "").strip()
    return bool(t) and not t.startswith("<") and not t.startswith("[Request interrupted") \
        and not t.startswith("# AGENTS.md instructions")


def events_codex(path: Path) -> list[dict]:
    events = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "response_item":
                continue
            p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
            base = {"t": iso(d.get("timestamp")), "sidechain": False}
            ptype = p.get("type")
            if ptype == "message":
                text = blocks_text(p.get("content"))
                if p.get("role") == "assistant" and text:
                    events.append({**base, "role": "agent", "text": text})
                elif p.get("role") == "user" and owner_text(text):
                    events.append({**base, "role": "owner", "text": text})
            elif ptype in ("function_call", "custom_tool_call"):
                events.append({**base, "role": "tool_call", "name": p.get("name", ""),
                               "text": str(p.get("arguments") or p.get("input") or "")})
            elif ptype in ("function_call_output", "custom_tool_call_output"):
                output = p.get("output")
                events.append({**base, "role": "tool_result",
                               "text": output if isinstance(output, str) else blocks_text(output)})
    return events


def events_opencode(spec: str) -> list[dict]:
    db, _, session = spec.partition("#")
    if not session:
        raise Failure("an OpenCode record is PATH.db#SESSION_ID",
                      "run `session-sweep locate --marker TEXT` to get the full spec")
    con = sqlite3.connect(f"file:{Path(db).as_posix()}?mode=ro", uri=True)
    q = ("select m.data, p.data, p.time_created from message m join part p on p.message_id = m.id "
         "where m.session_id = ? order by m.time_created, p.id")
    events = []
    for md, pd, ts in con.execute(q, (session,)):
        try:
            md, pd = json.loads(md), json.loads(pd)
        except json.JSONDecodeError:
            continue
        base = {"t": iso(ts), "sidechain": False}
        role = md.get("role")
        if pd.get("type") == "text" and not pd.get("synthetic"):
            text = pd.get("text", "")
            if role == "assistant" and text:
                events.append({**base, "role": "agent", "text": text})
            elif role == "user" and owner_text(text):
                events.append({**base, "role": "owner", "text": text})
        elif pd.get("type") == "tool":
            state = pd.get("state") or {}
            events.append({**base, "role": "tool_call", "name": pd.get("tool", ""),
                           "text": json.dumps(state.get("input", {}), ensure_ascii=False,
                                              sort_keys=True)})
            if state.get("output") is not None:
                events.append({**base, "role": "tool_result", "text": str(state.get("output"))})
    con.close()
    return events


IGNITE_HEADING = re.compile(r"^## (\d+) (owner|assistant)\s*$")


def events_ignite(path: Path) -> list[dict]:
    events = []
    current = None
    body: list[str] = []

    def flush():
        if current is None:
            return
        ms, who = current
        text = "\n".join(body).strip()
        base = {"t": iso(int(ms)), "sidechain": False}
        if who == "owner":
            if text:
                events.append({**base, "role": "owner", "text": text})
            return
        try:
            d = json.loads(text)
            replies = d.get("replies") or []
            text = "\n".join(r.get("text", "") for r in replies if isinstance(r, dict))
        except (json.JSONDecodeError, AttributeError):
            pass
        if text:
            events.append({**base, "role": "agent", "text": text})

    for line in read_text(path).splitlines():
        m = IGNITE_HEADING.match(line)
        if m:
            flush()
            current = (m.group(1), m.group(2))
            body = []
        else:
            body.append(line)
    flush()
    return events


def events_of(record: str) -> tuple[str, list[dict]]:
    harness = harness_of(record)
    if harness == "opencode":
        return harness, events_opencode(record)
    reader = {"claude": events_claude, "codex": events_codex, "ignite": events_ignite}[harness]
    return harness, reader(Path(record))


# ---------------------------------------------------------------- locate

def locate(marker: str) -> list[dict]:
    found = []
    home = Path.home()
    agent_home, conversation = os.environ.get("RBTV_AGENT_HOME"), os.environ.get("IGNITE_CONVERSATION")
    if agent_home and conversation:
        for key in (conversation, conversation.replace(":", "-")):
            p = Path(agent_home) / "runtime" / "ignite" / "conversations" / key / "history.md"
            if p.is_file():
                found.append({"record": str(p), "harness": "ignite", "cwd": agent_home})
                break
    for pattern, harness in (("*/*.jsonl", "claude"),):
        for p in (home / ".claude" / "projects").glob(pattern):
            cwd = file_has(p, marker, cwd_key='"cwd"')
            if cwd is not None:
                found.append({"record": str(p), "harness": harness, "cwd": cwd})
    for p in (home / ".codex" / "sessions").glob("**/*.jsonl"):
        cwd = file_has(p, marker, cwd_key='"cwd"')
        if cwd is not None:
            found.append({"record": str(p), "harness": "codex", "cwd": cwd})
    db = home / ".local" / "share" / "opencode" / "opencode.db"
    if db.is_file():
        try:
            con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
            rows = con.execute(
                "select distinct p.session_id, s.directory from part p join session s on s.id = p.session_id "
                "where p.data like ?", (f"%{marker}%",)).fetchall()
            con.close()
            for sid, directory in rows:
                found.append({"record": f"{db}#{sid}", "harness": "opencode", "cwd": directory or ""})
        except sqlite3.Error:
            pass
    return found


def file_has(path: Path, marker: str, *, cwd_key: str) -> str | None:
    """The record's working folder when the file holds the marker, else None."""
    cwd = ""
    hit = False
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not cwd and cwd_key in line:
                    m = re.search(r'"cwd":\s*("(?:[^"\\]|\\.)*")', line)
                    if m:
                        cwd = json.loads(m.group(1))  # decoded: a Windows path keeps single backslashes
                if marker in line:
                    hit = True
                    if cwd:
                        break
    except OSError:
        return None
    return cwd if hit else None


# ---------------------------------------------------------------- moments

def moments_of(events: list[dict], record: str) -> list[dict]:
    moments = []
    agent_before = ""
    last_call = None
    seen_calls: set[str] = set()
    seen_owner: set[str] = set()
    for e in events:
        role = e["role"]
        base = {"time": e["t"], "source": record, "sidechain": e.get("sidechain", False)}
        if role == "owner":
            key = hashlib.sha1(e["text"].strip().encode("utf-8")).hexdigest()
            if key in seen_owner:
                continue
            seen_owner.add(key)
            moments.append({**base, "kind": "owner", "matched": [],
                            "agent_before": clip(agent_before[-1200:], 1200),
                            "text": clip(e["text"], TEXT_CAP)})
        elif role == "agent":
            agent_before = e["text"]
            if WORKAROUND.search(e["text"]):
                moments.append({**base, "kind": "signal", "matched": ["workaround"],
                                "text": clip(e["text"], TEXT_CAP)})
        elif role == "tool_call":
            last_call = e
            matched = []
            if DANGEROUS.search(e["text"]):
                matched.append("dangerous")
            key = hashlib.sha1((e.get("name", "") + e["text"]).encode("utf-8")).hexdigest()
            if key in seen_calls:
                matched.append("repeated")
            seen_calls.add(key)
            if matched:
                moments.append({**base, "kind": "signal", "matched": matched,
                                "command": e.get("name", ""), "text": clip(e["text"], RESULT_CAP)})
        elif role == "tool_result":
            matched = []
            edges = e["text"] if len(e["text"]) <= 2 * EDGE else e["text"][:EDGE] + "\n" + e["text"][-EDGE:]
            if REFUSED.search(edges):
                matched.append("refused")
            if FAILED.search(edges):
                matched.append("failed")
            if matched:
                moments.append({**base, "kind": "signal", "matched": matched,
                                "command": (last_call or {}).get("name", ""),
                                "command_input": clip((last_call or {}).get("text", ""), 600),
                                "text": clip(e["text"], RESULT_CAP)})
    return moments


def report_moments(reports: list[str]) -> list[dict]:
    moments = []
    for r in reports:
        p = Path(r)
        if not p.is_file():
            raise Failure(f"report not found: {r}", "pass the path of the sub-agent's final report")
        moments.append({"time": "", "source": str(p), "sidechain": False, "kind": "report",
                        "matched": [], "text": clip(read_text(p), REPORT_CAP)})
    return moments


def render_moment(m: dict) -> str:
    head = f"## Moment {m['id']} · {m['kind']}\n"
    head += f"time: {m['time'] or '-'} | source: {m['source']}"
    if m.get("sidechain"):
        head += " | sidechain: yes"
    if m["matched"]:
        head += " | matched: " + ", ".join(m["matched"])
    head += "\n\n"
    if m["kind"] == "owner":
        return head + f"### Agent just before\n{m['agent_before'] or '(none)'}\n\n### Owner\n{m['text']}\n\n"
    if m["kind"] == "signal":
        body = ""
        if m.get("command"):
            body += f"### Command ({m['command']})\n{m.get('command_input') or m['text']}\n\n"
        if "workaround" in m["matched"]:
            body += f"### Agent text\n{m['text']}\n\n"
        elif m.get("command_input") is not None and "command" in m:
            body += f"### Result\n{m['text']}\n\n"
        return head + body
    return head + f"### Report\n{m['text']}\n\n"


def cmd_extract(args) -> int:
    harness, events = events_of(args.record)
    moments = moments_of(events, args.record) + report_moments(args.report or [])
    for i, m in enumerate(moments, 1):
        m["id"] = i
    outdir = Path(args.out)
    write_text(outdir / "moments.json",
               json.dumps({"record": args.record, "harness": harness, "moments": moments},
                          ensure_ascii=False, indent=1))
    chunks = 0
    for k in range(0, len(moments), CHUNK_MOMENTS):
        chunks += 1
        write_text(outdir / "chunks" / f"chunk-{chunks:03d}.md",
                   "".join(render_moment(m) for m in moments[k:k + CHUNK_MOMENTS]))
    out("harness", harness)
    out("events", len(events))
    out("moments", len(moments))
    out("owner_moments", sum(m["kind"] == "owner" for m in moments))
    out("signals", sum(m["kind"] == "signal" for m in moments))
    out("reports", sum(m["kind"] == "report" for m in moments))
    out("chunks", chunks)
    out("out", outdir)
    return 0


# ---------------------------------------------------------------- transcript

def one_line(text: str) -> str:
    return " ⏎ ".join(part for part in (text or "").split("\n"))


def render_event(e: dict, record: str) -> str:
    role = e["role"]
    who = {"owner": "USER", "agent": "AGENT", "tool_call": "CALL", "tool_result": "RESULT"}[role]
    tag = f"[{e['t'] or '-'}] {who}" + (" (sidechain)" if e.get("sidechain") else "")
    if role == "tool_call":
        return f"{tag} {e.get('name', '')}: {one_line(clip(e['text'], 600))}"
    if role == "tool_result":
        return f"{tag}: {one_line(clip(e['text'], 400))}"
    return f"{tag}: {one_line(e['text'])}"


def cmd_transcript(args) -> int:
    lines: list[str] = []
    total = 0
    for record in args.record:
        harness, events = events_of(record)
        lines.append(f"# {harness} {record}")
        for e in events:
            lines.append(render_event(e, record))
        total += len(events)
    numbered = [f"{i:05d}: {line}" for i, line in enumerate(lines, 1)]
    outdir = Path(args.out)
    chunks, buf, size = 0, [], 0
    for line in numbered:
        if buf and size + len(line) > TRANSCRIPT_CHARS:
            chunks += 1
            write_text(outdir / "chunks" / f"chunk-{chunks:03d}.md", "\n".join(buf) + "\n")
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        chunks += 1
        write_text(outdir / "chunks" / f"chunk-{chunks:03d}.md", "\n".join(buf) + "\n")
    out("records", len(args.record))
    out("events", total)
    out("lines", len(numbered))
    out("chunks", chunks)
    out("out", outdir)
    return 0


# ---------------------------------------------------------------- check

OWNER_LABELS = set("ABCDEFG")
SIGNAL_LABELS = {"refused", "failed", "repeated", "dangerous", "workaround", "none"}
REPORT_LABELS = {"skipped", "none"}
COUNTS = re.compile(r"^COUNTS owner=(\d+) signal=(\d+) report=(\d+)\s*$")


def cmd_check(args) -> int:
    run = Path(args.run)
    moments_path = run / "moments.json"
    if not moments_path.is_file():
        raise Failure(f"no moments.json in {run}", f"session-sweep extract RECORD --out {run}")
    moments = json.loads(read_text(moments_path))["moments"]
    by_id = {m["id"]: m for m in moments}
    chunk_files = sorted((run / "chunks").glob("chunk-*.md"))
    problems: list[str] = []
    counts: dict[str, int] = {}
    for i, chunk in enumerate(chunk_files, 1):
        ids = [m["id"] for m in moments[(i - 1) * CHUNK_MOMENTS:i * CHUNK_MOMENTS]]
        label_file = run / "labels" / f"{chunk.stem}.txt"
        if not label_file.is_file():
            problems.append(f"{chunk.stem}: no label file at {label_file}")
            continue
        lines = [ln for ln in read_text(label_file).splitlines() if ln.strip()]
        if not lines or not COUNTS.match(lines[0]):
            problems.append(f"{chunk.stem}: first line is not `COUNTS owner=n signal=n report=n`")
            continue
        want = {k: sum(by_id[j]["kind"] == k for j in ids) for k in ("owner", "signal", "report")}
        got = dict(zip(("owner", "signal", "report"), map(int, COUNTS.match(lines[0]).groups())))
        if got != want:
            problems.append(f"{chunk.stem}: COUNTS {got} differ from the chunk's {want}")
        seen = set()
        for ln in lines[1:]:
            fields = [f.strip() for f in ln.split("|")]
            if len(fields) != 6:
                problems.append(f"{chunk.stem}: a line has {len(fields)} fields, not 6: {ln[:80]}")
                continue
            try:
                mid = int(fields[0])
            except ValueError:
                problems.append(f"{chunk.stem}: id is not a number: {fields[0]}")
                continue
            if mid not in ids:
                problems.append(f"{chunk.stem}: moment {mid} is not in this chunk")
                continue
            kind, label = by_id[mid]["kind"], fields[2]
            valid = {"owner": OWNER_LABELS, "signal": SIGNAL_LABELS, "report": REPORT_LABELS}[kind]
            if fields[1] != kind:
                problems.append(f"{chunk.stem}: moment {mid} is {kind}, line says {fields[1]}")
            if label not in valid:
                problems.append(f"{chunk.stem}: moment {mid} has label {label!r}, not one of {sorted(valid)}")
            if fields[5] not in ("high", "medium", "low"):
                problems.append(f"{chunk.stem}: moment {mid} confidence {fields[5]!r} is not high, medium or low")
            seen.add(mid)
            counts[f"{kind}:{label}"] = counts.get(f"{kind}:{label}", 0) + 1
        missing = sorted(set(ids) - seen)
        if missing:
            problems.append(f"{chunk.stem}: moments without a line: {missing}")
    if problems:
        raise Failure("; ".join(problems[:12]) + (" …" if len(problems) > 12 else ""),
                      "re-run the labeler of each named chunk, then `session-sweep check` again")
    out("chunks", len(chunk_files))
    out("labelled", sum(counts.values()))
    for key in sorted(counts):
        out(key, counts[key])
    return 0


def cmd_locate(args) -> int:
    found = locate(args.marker)
    if not found:
        raise Failure(f"no session record holds the marker {args.marker!r}",
                      "wait for your message holding the marker to be recorded and run locate again, "
                      "or pass the record's path to extract")
    out("records", len(found))
    for f in found:
        out("record", f["record"])
        out("harness", f["harness"])
        out("cwd", f["cwd"])
    return 0


# ---------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="session-sweep",
        description="The exact steps of the compound sweep over one session's record: find the record, "
                    "cut its moments into chunks for labelers, render its transcript for checkers, "
                    "and check the label files. Result fields print as `name value` lines.",
        epilog="A failed run prints nothing on standard output and `error:` and `next:` on standard error. "
               "Exit 0 success, 1 failed, 2 invalid invocation.")
    sub = ap.add_subparsers(dest="verb", metavar="VERB", required=True)
    p = sub.add_parser("locate", help="find this session's record by a marker you wrote into it",
                       description="Search the session records the harnesses on this machine keep "
                                   "(Claude Code, Codex, OpenCode; an Ignite turn's own history when "
                                   "RBTV_AGENT_HOME and IGNITE_CONVERSATION are set) for the files holding MARKER. "
                                   "Prints `records N` and, per record, `record`, `harness` and `cwd`.")
    p.add_argument("--marker", required=True, help="text you wrote in your own message, unique to this session")
    p.set_defaults(fn=cmd_locate)
    p = sub.add_parser("extract", help="cut the record's moments into chunks for labelers",
                       description="Write OUT/moments.json and OUT/chunks/chunk-NNN.md (30 moments each): every "
                                   "message the user typed with the agent's message before it, every command or "
                                   "tool result matching a signal pattern, every passage where the agent says it "
                                   "worked around or could not find something, and every --report file. "
                                   "Prints harness, events, moments, owner_moments, signals, reports, chunks, out.")
    p.add_argument("record", metavar="RECORD",
                   help="a Claude Code or Codex .jsonl, an Ignite history.md, or PATH.db#SESSION for OpenCode")
    p.add_argument("--out", required=True, help="folder for moments.json and chunks/")
    p.add_argument("--report", action="append", metavar="PATH", help="a sub-agent's final report; repeatable")
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("transcript", help="render the visible events for the full tier's checkers",
                       description="Write OUT/chunks/chunk-NNN.md holding every visible event of each RECORD in "
                                   "order, one numbered line each (USER, AGENT, CALL, RESULT), about 30,000 "
                                   "characters per chunk. Prints records, events, lines, chunks, out.")
    p.add_argument("record", metavar="RECORD", nargs="+", help="records of the session and its sub-agents")
    p.add_argument("--out", required=True, help="folder for chunks/")
    p.set_defaults(fn=cmd_transcript)
    p = sub.add_parser("check", help="confirm one well-formed label file per chunk and count the labels",
                       description="Read RUN/moments.json, RUN/chunks/ and RUN/labels/chunk-NNN.txt. Each label "
                                   "file must open with `COUNTS owner=n signal=n report=n` matching its chunk and "
                                   "carry one six-field line per moment with a label valid for its kind. "
                                   "Prints chunks, labelled and one `kind:label N` line per label; a defect "
                                   "names its chunk and exits 1.")
    p.add_argument("run", metavar="RUN", help="the folder extract wrote (--out)")
    p.set_defaults(fn=cmd_check)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except Failure as f:
        return fail(f.error, f.next)


if __name__ == "__main__":
    sys.exit(main())
