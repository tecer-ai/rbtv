#!/usr/bin/env python3
"""channel-protocol — the meeting-summarizer channel engine.

Turns one per-meeting payload or failure event into channel messages, ingests
owner replies into owner-answer objects, and posts the one-time grounding note.
Deterministic: file reads, JSON Schema validation against the seam set, string
scans. No network call, no chat-service call, no model call — anywhere.

Run with --help for the full command surface.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOL_FILE = Path(__file__).resolve()
TOOL_DIR = TOOL_FILE.parent
FIXTURE_DIR = TOOL_DIR / "fixture" / "channel"
DEFAULT_SEAMS = TOOL_DIR.parent / "seams"

# ------------------------------------------------------------ transport layout
# A file-backed scratch transport: one append-only ordered log, one reply file,
# one token file per write-gate release. Every path is derived from --channel;
# nothing here is a deployment value. The LIVE transport is out of scope: a live
# adapter binds at the three seam points marked TRANSPORT SEAM below and leaves
# every other line of this engine untouched.
MESSAGE_LOG = "messages.jsonl"  # TRANSPORT SEAM: ordered message append + read
REPLY_LOG = "replies.jsonl"  # TRANSPORT SEAM: owner replies read
TOKEN_DIR = "tokens"  # TRANSPORT SEAM: write-gate token release

# The store's location is a CONFIG KEY, never a literal path (the store schema's
# container.location const, and its config-key contract).
STORE_KEY = "stores/thread-meeting-map"
CONFIG_ROOT_ENV = "MEETING_SUMMARIZER_CONFIG_ROOT"

MESSAGE_SCHEMA = "meeting-message-payload.schema.json"
FAILURE_SCHEMA = "failure-event-and-outcome.schema.json"
ANSWER_SCHEMA = "owner-answer.schema.json"
FINDINGS_SCHEMA = "findings-payload.schema.json"
STORE_SCHEMA = "thread-meeting-map-store.schema.json"

# payload kind -> the seam schema that is its validation authority
KIND_SCHEMA = {
    "filed-note": MESSAGE_SCHEMA,
    "doubt": MESSAGE_SCHEMA,
    "unroutable": MESSAGE_SCHEMA,
    "amendment": MESSAGE_SCHEMA,
    "failure-event": FAILURE_SCHEMA,
}
# an ask message type -> the owner-answer kind a reply to it carries
ANSWER_KIND = {"doubt-ask": "glossary-term", "routing-ask": "routing"}

MESSAGE_TYPES = (
    "filed-note",
    "doubt-ask",
    "routing-ask",
    "amendment",
    "failure-note",
    "grounding-note",
    "token-release",
)

EXIT_OK = 0
EXIT_VERDICT = 1  # ran fine, ok is false
EXIT_REFUSED = 2  # could not run: bad input, missing runtime, unreadable path

_JSON_MODE = False


# ------------------------------------------------------------------- plumbing
def refuse(what: str, why: str, fix: str, escape: str) -> None:
    """Environment refusal: what happened, why, how to fix, what the escape is."""
    if _JSON_MODE:
        json.dump(
            {"ok": False, "error": {"what": what, "why": why, "fix": fix, "escape": escape}},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        print(f"refused: {what}", file=sys.stderr)
        print(f"  why:    {why}", file=sys.stderr)
        print(f"  fix:    {fix}", file=sys.stderr)
        print(f"  escape: {escape}", file=sys.stderr)
    sys.exit(EXIT_REFUSED)


def refusal(what: str, why: str, fix: str, escape: str) -> dict:
    """Input refusal as a RESULT — the caller decides the exit code."""
    return {"ok": False, "error": {"what": what, "why": why, "fix": fix, "escape": escape}}


def load_validator():
    """jsonschema's draft 2020-12 validator class, or an environment refusal."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment refusal
        refuse(
            what="the jsonschema library is not importable",
            why=str(exc),
            fix="install it for this interpreter: python3 -m pip install jsonschema",
            escape="none — this engine never vendors a validator; every payload it "
            "accepts or emits is held to the seam schema by a real implementation",
        )
    return Draft202012Validator


def load_referencing():
    """(Registry, Resource, DRAFT202012), or an environment refusal."""
    try:
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError as exc:  # pragma: no cover - environment refusal
        refuse(
            what="the referencing library is not importable",
            why=str(exc),
            fix="install it for this interpreter: python3 -m pip install referencing",
            escape="none — the seam schemas cross-reference each other, and resolving "
            "those references by hand is exactly what this engine must not do",
        )
    return Registry, Resource, DRAFT202012


def read_json(path: Path):
    """(value, error-string). Never raises."""
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except UnicodeDecodeError as exc:
        return None, f"not utf-8: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc}"
    except OSError as exc:
        return None, f"cannot read {path}: {exc}"


def read_jsonl(path: Path) -> list[dict]:
    """Every parseable object in a JSONL file, in file order. Missing file = []."""
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def append_jsonl(path: Path, record: dict) -> None:
    """Append ONE record durably: the line is on disk before this returns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Seams:
    """The seam set as a validation authority: schemas plus a $ref registry."""

    def __init__(self, seams_dir: Path):
        self.dir = seams_dir
        Registry, Resource, DRAFT202012 = load_referencing()
        self.validator_cls = load_validator()
        registry = Registry()
        for path in sorted(seams_dir.rglob("*.schema.json")):
            contents, error = read_json(path)
            if error or not isinstance(contents, dict):
                continue
            resource = Resource.from_contents(contents, default_specification=DRAFT202012)
            keys = sorted({path.name, path.relative_to(seams_dir).as_posix()})
            registry = registry.with_resources([(key, resource) for key in keys])
        self.registry = registry
        self._cache: dict = {}

    def schema(self, name: str):
        if name not in self._cache:
            self._cache[name] = read_json(self.dir / name)
        return self._cache[name]

    def errors(self, instance, schema) -> list[str]:
        """Every validation message, outermost first. Never raises on ordering."""
        validator = self.validator_cls(schema, registry=self.registry)
        found = sorted(validator.iter_errors(instance), key=lambda err: str(list(err.path)))
        return [
            f"{'/'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
            for err in found
        ]


# ------------------------------------------------------------------ transport
class Channel:
    """The file-backed scratch transport rooted at one directory."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.log = self.root / MESSAGE_LOG
        self.reply_log = self.root / REPLY_LOG
        self.token_dir = self.root / TOKEN_DIR
        self._messages = None

    def messages(self) -> list[dict]:
        if self._messages is None:
            self._messages = read_jsonl(self.log)
        return self._messages

    def post(self, kind: str, text: str, *, thread=None, meeting_key=None, reply_to=None,
             extra: dict | None = None) -> dict:
        """Append ONE message to the ordered log and return the stored record."""
        messages = self.messages()
        seq = len(messages) + 1
        record = {
            "id": f"msg-{seq:04d}",
            "seq": seq,
            "type": kind,
            "thread": thread,
            "reply-to": reply_to,
            "meeting-key": meeting_key,
            "text": text,
            "at": now_stamp(),
        }
        if extra:
            record.update(extra)
        append_jsonl(self.log, record)
        messages.append(record)
        return record

    def replies(self) -> list[dict]:
        return read_jsonl(self.reply_log)

    def in_thread(self, thread: str) -> list[dict]:
        return [msg for msg in self.messages() if msg.get("thread") == thread]

    def of_type(self, kind: str) -> list[dict]:
        return [msg for msg in self.messages() if msg.get("type") == kind]

    def filed_note_for(self, meeting_key: str):
        for msg in self.messages():
            if msg.get("type") == "filed-note" and msg.get("meeting-key") == meeting_key:
                return msg
        return None

    def release_token(self, meeting_key: str, after: dict) -> tuple[dict, dict]:
        """Mint the write-gate token release — ONLY after `after` is on disk.

        The ask is already durable when this runs (post fsyncs before it
        returns), and the release is itself appended to the ordered log, so the
        ordering the contract demands is checkable in one place:
        seq(ask) < seq(release), in the transport's own message order.
        """
        release = self.post(
            "token-release",
            f"write-gate released for {meeting_key} after {after['id']}",
            meeting_key=meeting_key,
            extra={"after-message": after["id"], "after-seq": after["seq"]},
        )
        token = {
            "token": f"tok-{release['id']}",
            "kind": "write-gate-release",
            "meeting-key": meeting_key,
            "after-message": after["id"],
            "after-seq": after["seq"],
            "release-message": release["id"],
            "release-seq": release["seq"],
            "released-at": release["at"],
        }
        self.token_dir.mkdir(parents=True, exist_ok=True)
        path = self.token_dir / f"{token['token']}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(token, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return dict(token, file=str(path)), release

    def tokens(self) -> list[dict]:
        if not self.token_dir.is_dir():
            return []
        found = []
        for path in sorted(self.token_dir.glob("*.json")):
            value, error = read_json(path)
            if not error and isinstance(value, dict):
                found.append(dict(value, file=str(path)))
        return found


# ------------------------------------------------------------ the thread store
def resolve_store(explicit, config_dir, channel: Channel) -> tuple[Path, str]:
    """(path, how) for the thread<->meeting map store.

    Resolution order — no deployment literal at any step:
      1. --store PATH                                        (injectable)
      2. the config key `stores/thread-meeting-map`, read as
         <config-dir>/stores.json -> {"thread-meeting-map": PATH}, where
         config-dir is the explicit --config-dir, else `MEETING_SUMMARIZER_CONFIG_ROOT`
      3. the key's own relative form under the caller's channel:
         <channel>/stores/thread-meeting-map.jsonl
    """
    if explicit:
        return Path(explicit).expanduser().resolve(), "flag"
    group, _, leaf = STORE_KEY.partition("/")
    if config_dir is None:
        env = os.environ.get(CONFIG_ROOT_ENV)
        config_dir = Path(env) if env else None
    if config_dir is not None:
        value, error = read_json(Path(config_dir) / f"{group}.json")
        if not error and isinstance(value, dict) and isinstance(value.get(leaf), str):
            return Path(value[leaf]).expanduser().resolve(), f"config key {STORE_KEY}"
    return (channel.root / group / f"{leaf}.jsonl").resolve(), "channel-local default"


def store_records(path: Path) -> list[dict]:
    return read_jsonl(path)


def thread_id_for(meeting_key: str) -> str:
    """Deterministic, opaque, per-meeting. Replayable — never a random id."""
    return "thr-" + hashlib.sha256(meeting_key.encode("utf-8")).hexdigest()[:12]


def thread_of_meeting(records: list[dict], meeting_key: str):
    for record in records:
        if record.get("meeting-key") == meeting_key:
            return record.get("thread")
    return None


def open_or_reuse_thread(seams: Seams, store: Path, meeting_key: str):
    """(thread, created, problems). A mapped meeting gets ZERO new threads."""
    existing = thread_of_meeting(store_records(store), meeting_key)
    if existing:
        return existing, False, []
    thread = thread_id_for(meeting_key)
    record = {"thread": thread, "meeting-key": meeting_key, "created-at": now_stamp()}
    problems = []
    schema, error = seams.schema(STORE_SCHEMA)
    if error:
        problems.append(f"{STORE_SCHEMA}: {error}")
    else:
        sub = (schema.get("properties") or {}).get("record")
        if not isinstance(sub, dict):
            problems.append(f"{STORE_SCHEMA} declares no `record` sub-schema")
        else:
            problems += [f"store record {message}" for message in seams.errors(record, sub)]
    if not problems:
        append_jsonl(store, record)
    return thread, True, problems


# ---------------------------------------------------------------- message text
def file_ref(ref) -> str:
    if isinstance(ref, dict):
        return f"{ref.get('repo')}:{ref.get('path')}"
    return str(ref)


def leaf_values(node) -> list[str]:
    """Every scalar leaf of a payload, as text — the field-for-field checklist."""
    if isinstance(node, dict):
        out = []
        for key in sorted(node):
            out += leaf_values(node[key])
        return out
    if isinstance(node, list):
        out = []
        for item in node:
            out += leaf_values(item)
        return out
    return [str(node)]


def render_grounding(payload: dict) -> str:
    """The grounding note: every field of the payload, field-for-field."""
    lines = [
        "grounding — source verification findings",
        f"verified-at: {payload['verified-at']}",
    ]
    for account in sorted(payload.get("accounts") or {}):
        lines.append(f"account {account}:")
        preconditions = (payload["accounts"][account] or {}).get("preconditions") or {}
        for name in sorted(preconditions):
            entry = preconditions[name] or {}
            detail = entry.get("detail")
            lines.append(f"  {name}: {entry.get('verdict')}" + (f" — {detail}" if detail else ""))
    dead = payload.get("dead-sources") or []
    lines.append(f"dead sources ({len(dead)}):")
    if not dead:
        lines.append("  none — every source live")
    for entry in dead:
        lines.append(f"  {entry.get('account')} / {entry.get('layout')} — {entry.get('why')}")
    return "\n".join(lines)


# ------------------------------------------------------------------- tallying
def tally(messages: list[dict]) -> dict:
    counts = {f"{kind}s": 0 for kind in MESSAGE_TYPES}
    for message in messages:
        key = f"{message.get('type')}s"
        if key in counts:
            counts[key] += 1
    return counts


def channel_totals(channel: Channel, store: Path) -> dict:
    totals = tally(channel.messages())
    records = store_records(store)
    totals["owner-need-threads"] = len({r.get("thread") for r in records if r.get("thread")})
    totals["replies"] = len(channel.replies())
    totals["messages"] = len(channel.messages())
    return totals


def envelope(operation: str, channel: Channel, store: Path, **fields) -> dict:
    result = {
        "tool": "channel-protocol",
        "operation": operation,
        "channel": str(channel.root),
        "store": str(store),
    }
    result.update(fields)
    result["channel-totals"] = channel_totals(channel, store)
    return result


# -------------------------------------------------------------- operation: emit
def op_emit(payload, seams: Seams, channel: Channel, store: Path) -> dict:
    """One validated payload -> its channel messages. Never guesses a kind."""
    if not isinstance(payload, dict):
        return refusal(
            what="the payload is not a JSON object",
            why=f"read a {type(payload).__name__}, and every seam payload is an object",
            fix="pass one payload object: channel_protocol.py emit PATH --channel DIR",
            escape="`selftest` runs the whole behavior against the bundled fixture",
        )
    kind = payload.get("kind")
    schema_name = KIND_SCHEMA.get(kind)
    if schema_name is None:
        return refusal(
            what=f"kind {kind!r} is not a channel payload",
            why="emit handles exactly: " + ", ".join(sorted(KIND_SCHEMA)),
            fix="send a meeting-message-payload or a failure-event",
            escape="none — a kind this engine does not handle is never guessed into a message",
        )
    schema, error = seams.schema(schema_name)
    if error:
        refuse(
            what=f"the seam schema {schema_name} is unreadable",
            why=error,
            fix=f"point the engine at the seam set: --seams DIR (looked in {seams.dir})",
            escape="none — this engine validates every payload against its seam schema",
        )
    problems = seams.errors(payload, schema)
    if problems:
        return refusal(
            what=f"the {kind} payload does not validate against {schema_name}",
            why="; ".join(problems[:5]),
            fix="correct the payload against the seam schema, then emit again",
            escape="none — an invalid payload never reaches the channel",
        )

    meeting_key = payload.get("meeting-key")
    messages, threads, tokens = [], [], []

    if kind == "filed-note":
        messages.append(channel.post(
            "filed-note",
            f"filed → {file_ref(payload['destination'])}",
            meeting_key=meeting_key,
        ))

    elif kind in ("doubt", "unroutable"):
        thread, created, store_problems = open_or_reuse_thread(seams, store, meeting_key)
        if store_problems:
            return refusal(
                what="the thread<->meeting map record does not validate",
                why="; ".join(store_problems[:5]),
                fix=f"check {STORE_SCHEMA} against the record this engine writes",
                escape="none — an unmapped thread makes an owner reply unresolvable",
            )
        threads.append({"thread": thread, "meeting-key": meeting_key, "created": created})
        if kind == "doubt":
            messages.append(channel.post(
                "doubt-ask",
                f"doubt: term {payload['term']!r}, standing guess {payload['guess']!r} "
                f"— flagged in {file_ref(payload['summary'])}",
                thread=thread,
                meeting_key=meeting_key,
            ))
        else:
            signals = payload["signals"]
            excerpts = signals.get("excerpts") or []
            ask = channel.post(
                "routing-ask",
                "unroutable: where does this go? title {0!r}, participants {1}{2}".format(
                    signals.get("title"),
                    ", ".join(signals.get("participants") or []),
                    ("; excerpts: " + " | ".join(excerpts)) if excerpts else "",
                ),
                thread=thread,
                meeting_key=meeting_key,
            )
            messages.append(ask)
            # The ask is durable here (post fsyncs). ONLY now is the gate released.
            token, release = channel.release_token(meeting_key, ask)
            tokens.append(token)
            messages.append(release)

    elif kind == "amendment":
        filed = channel.filed_note_for(meeting_key)
        if filed is None:
            return refusal(
                what=f"no filed-note for meeting {meeting_key!r} to amend",
                why="an amendment is a REPLY to that meeting's filed-note message, and "
                "this channel carries none for it",
                fix="emit the meeting's filed-note first, then the amendment",
                escape="none — an amendment never opens a thread and never mints a map record",
            )
        messages.append(channel.post(
            "amendment",
            f"summary amended — {payload['what-changed']}",
            reply_to=filed["id"],
            meeting_key=meeting_key,
        ))

    elif kind == "failure-event":
        messages.append(channel.post(
            "failure-note",
            f"failure ({payload['scope']}): {payload['cause']}",
            meeting_key=meeting_key,
        ))

    counts = tally(messages)
    counts["threads-created"] = sum(1 for entry in threads if entry["created"])
    counts["threads-reused"] = sum(1 for entry in threads if not entry["created"])
    return envelope(
        "emit", channel, store,
        kind=kind, messages=messages, threads=threads, tokens=tokens, counts=counts, ok=True,
    )


# ------------------------------------------------------------ operation: ingest
def resolve_ask(channel: Channel, thread: str, reply: dict):
    """The ask a reply answers: the one it names, else the thread's latest ask."""
    named = reply.get("in-reply-to")
    if named:
        for message in channel.messages():
            if message.get("id") == named:
                if message.get("thread") != thread or message.get("type") not in ANSWER_KIND:
                    return None
                return message
        return None
    asks = [msg for msg in channel.in_thread(thread) if msg.get("type") in ANSWER_KIND]
    return asks[-1] if asks else None


def op_ingest(seams: Seams, channel: Channel, store: Path) -> dict:
    """Owner replies -> owner-answer objects. A reply nobody mapped is REPORTED."""
    schema, error = seams.schema(ANSWER_SCHEMA)
    if error:
        refuse(
            what=f"the seam schema {ANSWER_SCHEMA} is unreadable",
            why=error,
            fix=f"point the engine at the seam set: --seams DIR (looked in {seams.dir})",
            escape="none — every emitted owner-answer is held to its seam schema",
        )
    mapped = {r.get("thread"): r.get("meeting-key") for r in store_records(store) if r.get("thread")}
    answers, provenance, unmapped, problems = [], [], [], []
    replies = channel.replies()
    for reply in replies:
        identity = {"reply": reply.get("id"), "thread": reply.get("thread")}
        thread = reply.get("thread")
        if thread not in mapped:
            unmapped.append(dict(identity, why="thread is not in the thread<->meeting map store"))
            continue
        text = reply.get("text")
        if not isinstance(text, str) or not text:
            unmapped.append(dict(identity, why="reply carries no text"))
            continue
        ask = resolve_ask(channel, thread, reply)
        if ask is None:
            unmapped.append(dict(identity, why="no ask on that thread for this reply to answer"))
            continue
        answer = {
            "thread": thread,
            "meeting-key": mapped[thread],
            "kind": ANSWER_KIND[ask["type"]],
            "answer-text": text,
        }
        if isinstance(reply.get("at"), str):
            answer["answered-at"] = reply["at"]
        found = seams.errors(answer, schema)
        if found:
            problems.append(f"answer for {thread}: {'; '.join(found[:3])}")
            continue
        # The EMITTED object stays schema-pure: owner-answer.schema.json sets
        # additionalProperties=false, so provenance travels BESIDE the answer,
        # never inside it (arm `answer-schema` holds this).
        answers.append(answer)
        provenance.append({
            "from-reply": reply.get("id"),
            "answers-message": ask["id"],
            "thread": thread,
        })

    return envelope(
        "ingest", channel, store,
        **{"owner-answers": answers, "answer-provenance": provenance},
        unmapped=unmapped,
        problems=problems,
        counts={
            "replies": len(replies),
            "owner-answers": len(answers),
            "unmapped-replies": len(unmapped),
        },
        ok=not problems,
    )


# --------------------------------------------------------- operation: grounding
def op_grounding(payload, seams: Seams, channel: Channel, store: Path) -> dict:
    """ONE grounding note per channel. A second call refuses the duplicate, ok."""
    existing = channel.of_type("grounding-note")
    if existing:
        return envelope(
            "grounding", channel, store,
            **{"already-posted": True},
            messages=[], note=existing[0]["id"], counts={"grounding-notes": 0}, ok=True,
        )
    schema, error = seams.schema(FINDINGS_SCHEMA)
    if error:
        refuse(
            what=f"the seam schema {FINDINGS_SCHEMA} is unreadable",
            why=error,
            fix=f"point the engine at the seam set: --seams DIR (looked in {seams.dir})",
            escape="none — the grounding note carries a validated findings payload or none",
        )
    if not isinstance(payload, dict):
        return refusal(
            what="the findings payload is not a JSON object",
            why=f"read a {type(payload).__name__}",
            fix="pass one findings-payload object: grounding PATH --channel DIR",
            escape="`selftest` runs the same arm against the bundled fixture",
        )
    problems = seams.errors(payload, schema)
    if problems:
        return refusal(
            what=f"the findings payload does not validate against {FINDINGS_SCHEMA}",
            why="; ".join(problems[:5]),
            fix="correct the payload against the seam schema, then post again",
            escape="none — an unvalidated grounding note is exactly the silence clause 17 forbids",
        )
    note = channel.post("grounding-note", render_grounding(payload))
    return envelope(
        "grounding", channel, store,
        **{"already-posted": False},
        messages=[note], note=note["id"], counts={"grounding-notes": 1}, ok=True,
    )


# --------------------------------------------------------------------- selftest
FIXTURE_STREAM = (
    "01-filed-note.json",
    "02-doubt.json",
    "03-doubt-again.json",
    "04-unroutable.json",
    "05-amendment.json",
    "06-failure-event.json",
)
FIXTURE_REFUSED = ("invalid-payload.json", "unhandled-kind.json")
FIXTURE_FINDINGS = "findings.json"
FIXTURE_REPLIES = "replies.jsonl"


def _fixture(name: str):
    value, error = read_json(FIXTURE_DIR / name)
    if error:
        refuse(
            what=f"the bundled fixture is incomplete: {name}",
            why=error,
            fix=f"restore {FIXTURE_DIR / name}",
            escape="none — selftest proves this engine against its own fixture or not at all",
        )
    return value


def _meeting(name: str) -> str:
    return _fixture(name)["meeting-key"]


def _config_of(root: Path) -> Path:
    """The selftest's own config root for one channel — a temp dir, never the live one."""
    return root / "config"


def _store_of(root: Path) -> Path:
    """The store as the selftest resolves it: through the channel's OWN temp config
    root (a `stores.json` beside the channel, planted by `_build_channel`), so the
    config-key resolution path runs against temp paths and the LIVE store is never
    read or written by a selftest."""
    return resolve_store(None, _config_of(root), Channel(root))[0]


def _build_channel(seams: Seams, root: Path) -> dict:
    """Run the whole fixture stream into a fresh channel; return the raw results."""
    root.mkdir(parents=True, exist_ok=True)
    config = _config_of(root)
    config.mkdir(parents=True, exist_ok=True)
    (config / "stores.json").write_text(
        json.dumps({"thread-meeting-map": str(root / "stores" / "thread-meeting-map.jsonl")}),
        encoding="utf-8",
    )
    channel = Channel(root)
    store = _store_of(root)
    shutil.copyfile(FIXTURE_DIR / FIXTURE_REPLIES, root / REPLY_LOG)
    emitted = [op_emit(_fixture(name), seams, channel, store) for name in FIXTURE_STREAM]
    refused = [op_emit(_fixture(name), seams, channel, store) for name in FIXTURE_REFUSED]
    grounding = op_grounding(_fixture(FIXTURE_FINDINGS), seams, channel, store)
    return {"emitted": emitted, "refused": refused, "grounding": grounding}


def _observe(seams: Seams, root: Path, built: dict) -> dict:
    """Every fact the arms judge, read back from the transport as it stands."""
    store = _store_of(root)
    return {
        "root": root,
        "seams": seams,
        "messages": Channel(root).messages(),
        "store": store_records(store),
        "tokens": Channel(root).tokens(),
        "ingest": op_ingest(seams, Channel(root), store),
        "grounding-again": op_grounding(_fixture(FIXTURE_FINDINGS), seams, Channel(root), store),
        "built": built,
    }


def _of(obs, kind):
    return [message for message in obs["messages"] if message.get("type") == kind]


# ------------------------------------------------------------- arm predicates
def _arm_filed_note(obs) -> bool:
    notes = _of(obs, "filed-note")
    payload = _fixture(FIXTURE_STREAM[0])
    return (
        len(notes) == 1
        and notes[0]["thread"] is None
        and len(notes[0]["text"].splitlines()) == 1
        and file_ref(payload["destination"]) in notes[0]["text"]
    )


def _arm_doubt_ask(obs) -> bool:
    asks = _of(obs, "doubt-ask")
    payloads = [_fixture(FIXTURE_STREAM[1]), _fixture(FIXTURE_STREAM[2])]
    if len(asks) != len(payloads):
        return False
    return all(
        payload["term"] in ask["text"]
        and payload["guess"] in ask["text"]
        and file_ref(payload["summary"]) in ask["text"]
        and ask["thread"] == thread_id_for(payload["meeting-key"])
        for ask, payload in zip(asks, payloads)
    )


def _arm_thread_reuse(obs) -> bool:
    """Two doubts on one meeting share ONE thread; the store maps that meeting once."""
    doubt_meeting = _meeting(FIXTURE_STREAM[1])
    records = [r for r in obs["store"] if r.get("meeting-key") == doubt_meeting]
    threads = {ask["thread"] for ask in _of(obs, "doubt-ask")}
    return len(records) == 1 and len(threads) == 1 and len(obs["store"]) == 2


def _arm_token_order(obs) -> bool:
    """The routing ask is appended STRICTLY before the write-gate token release."""
    asks = _of(obs, "routing-ask")
    releases = _of(obs, "token-release")
    if len(asks) != 1 or len(releases) != 1:
        return False
    return (
        asks[0]["seq"] < releases[0]["seq"]
        and releases[0].get("after-message") == asks[0]["id"]
        and asks[0]["thread"] == thread_id_for(_meeting(FIXTURE_STREAM[3]))
    )


def _arm_token_file(obs) -> bool:
    asks = _of(obs, "routing-ask")
    if len(obs["tokens"]) != 1 or len(asks) != 1:
        return False
    token = obs["tokens"][0]
    return (
        token.get("kind") == "write-gate-release"
        and token.get("after-message") == asks[0]["id"]
        and token.get("after-seq") < token.get("release-seq")
    )


def _arm_amendment(obs) -> bool:
    """A one-liner REPLY to the filed-note — never a thread, never in the map."""
    amendments = _of(obs, "amendment")
    filed = _of(obs, "filed-note")
    payload = _fixture(FIXTURE_STREAM[4])
    if len(amendments) != 1 or len(filed) != 1:
        return False
    amendment = amendments[0]
    return (
        amendment["reply-to"] == filed[0]["id"]
        and amendment["thread"] is None
        and payload["what-changed"] in amendment["text"]
        and len(amendment["text"].splitlines()) == 1
        and all(r.get("meeting-key") != amendment["meeting-key"] or r.get("thread")
                for r in obs["store"])
    )


def _arm_failure_note(obs) -> bool:
    notes = _of(obs, "failure-note")
    payload = _fixture(FIXTURE_STREAM[5])
    return (
        len(notes) == 1
        and notes[0]["thread"] is None
        and payload["cause"] in notes[0]["text"]
    )


def _arm_refusal(obs) -> bool:
    """An invalid payload and an unhandled kind are both refused, named."""
    refused = obs["built"]["refused"]
    return len(refused) == 2 and all(
        result.get("ok") is False and result.get("error", {}).get("what") for result in refused
    )


def _arm_ingest(obs) -> bool:
    """Answers == replies on mapped threads, exactly; the rest is REPORTED."""
    result = obs["ingest"]
    answers = result["owner-answers"]
    if not result["ok"] or len(answers) != 2 or len(result["unmapped"]) != 1:
        return False
    by_meeting = {answer["meeting-key"]: answer for answer in answers}
    doubt, unroutable = _meeting(FIXTURE_STREAM[1]), _meeting(FIXTURE_STREAM[3])
    return (
        set(by_meeting) == {doubt, unroutable}
        and by_meeting[doubt]["kind"] == "glossary-term"
        and by_meeting[unroutable]["kind"] == "routing"
        and all(answer["answer-text"] for answer in answers)
    )


def _arm_answer_schema(obs) -> bool:
    """Every EMITTED owner-answer validates against owner-answer.schema.json.

    The engine validates the answer it BUILDS; this arm judges the object it
    HANDS OUT, which is the one contract 2 is about. Never vacuously green: no
    answers at all fails the arm.
    """
    seams = obs["seams"]
    schema, error = seams.schema(ANSWER_SCHEMA)
    if error:
        return False
    answers = obs["ingest"]["owner-answers"]
    return bool(answers) and all(not seams.errors(answer, schema) for answer in answers)


def _arm_grounding_note(obs) -> bool:
    """ONE note carrying every field of the payload, every dead source named."""
    notes = _of(obs, "grounding-note")
    if len(notes) != 1:
        return False
    text = notes[0]["text"]
    payload = _fixture(FIXTURE_FINDINGS)
    if any(value not in text for value in leaf_values(payload)):
        return False
    # Named IN the dead-sources roll, by its own line — a `why` that merely
    # recurs as some precondition's detail is not that source being named.
    lines = text.splitlines()
    dead = payload["dead-sources"]
    if f"dead sources ({len(dead)}):" not in lines:
        return False
    return all(
        f"  {entry['account']} / {entry['layout']} — {entry['why']}" in lines
        for entry in dead
    )


def _arm_grounding_once(obs) -> bool:
    again = obs["grounding-again"]
    return (
        again.get("already-posted") is True
        and again["counts"]["grounding-notes"] == 0
        and again["ok"] is True
        and len(_of(obs, "grounding-note")) == 1
    )


# -------------------------------------------------------------- arm breakers
def _rewrite_log(root: Path, transform) -> None:
    path = root / MESSAGE_LOG
    records = transform(read_jsonl(path))
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def _break_filed_note(root: Path) -> None:
    """A second filed-note for the same meeting: the count stops holding."""
    def transform(records):
        extra = copy.deepcopy(next(r for r in records if r["type"] == "filed-note"))
        extra["id"] = "msg-dup"
        return records + [extra]
    _rewrite_log(root, transform)


def _break_doubt_ask(root: Path) -> None:
    """Drop one of the two doubt asks: one doubt no longer carries its ask."""
    def transform(records):
        dropped = False
        kept = []
        for record in records:
            if record["type"] == "doubt-ask" and not dropped:
                dropped = True
                continue
            kept.append(record)
        return kept
    _rewrite_log(root, transform)


def _break_thread_reuse(root: Path) -> None:
    """A second map record for the doubt meeting: the reuse claim stops holding."""
    append_jsonl(_store_of(root), {
        "thread": "thr-second-for-one-meeting",
        "meeting-key": _meeting(FIXTURE_STREAM[1]),
    })


def _break_token_order(root: Path) -> None:
    """Swap the two seqs: the release now precedes the ask it must follow."""
    def transform(records):
        ask = next(r for r in records if r["type"] == "routing-ask")
        release = next(r for r in records if r["type"] == "token-release")
        ask["seq"], release["seq"] = release["seq"], ask["seq"]
        return records
    _rewrite_log(root, transform)


def _break_token_file(root: Path) -> None:
    for path in (root / TOKEN_DIR).glob("*.json"):
        path.unlink()


def _break_amendment(root: Path) -> None:
    def transform(records):
        for record in records:
            if record["type"] == "amendment":
                record["reply-to"] = None
        return records
    _rewrite_log(root, transform)


def _break_failure_note(root: Path) -> None:
    def transform(records):
        for record in records:
            if record["type"] == "failure-note":
                record["text"] = "failure (account): [cause withheld]"
        return records
    _rewrite_log(root, transform)


def _break_ingest(root: Path) -> None:
    """Drop one thread's map record: its reply can no longer become an answer."""
    store = _store_of(root)
    kept = [r for r in store_records(store) if r.get("meeting-key") != _meeting(FIXTURE_STREAM[1])]
    store.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in kept), encoding="utf-8"
    )


def _break_grounding_note(root: Path) -> None:
    def transform(records):
        for record in records:
            if record["type"] == "grounding-note":
                record["text"] = record["text"].split("dead sources")[0]
        return records
    _rewrite_log(root, transform)


def _break_grounding_once(root: Path) -> None:
    """Hide the posted note: a second call would then post a second one."""
    def transform(records):
        for record in records:
            if record["type"] == "grounding-note":
                record["type"] = "grounding-note-hidden"
        return records
    _rewrite_log(root, transform)


# Two breakers cannot work by mutating the channel on disk — they break what the
# engine HANDS BACK, not what it wrote. They are marked, and take (obs, seams, root).
def _break_refusal(obs, seams: Seams, root: Path) -> dict:
    """Feed the refusal arm a VALID payload — its claim must stop holding."""
    root.mkdir(parents=True, exist_ok=True)
    valid = op_emit(_fixture(FIXTURE_STREAM[5]), seams, Channel(root), _store_of(root))
    return dict(obs, built=dict(obs["built"], refused=[valid, valid]))


def _break_answer_schema(obs, seams: Seams, root: Path) -> dict:
    """Leak provenance back INTO the emitted answers — the exact regression this
    arm exists to catch (measured 2026-08-17: `answers-message` and `from-reply`
    rode inside the object, which additionalProperties=false forbids)."""
    result = obs["ingest"]
    leaked = [dict(answer, **{"answers-message": "msg-0003"})
              for answer in result["owner-answers"]]
    return dict(obs, ingest=dict(result, **{"owner-answers": leaked}))


_break_refusal.breaks_obs = True
_break_answer_schema.breaks_obs = True


ARMS = (
    ("filed-note",
     "exactly ONE one-line note naming the destination path, on no thread",
     _arm_filed_note, _break_filed_note),
    ("doubt-ask",
     "each doubt posts an ask carrying its term, guess and summary path, in the meeting's thread",
     _arm_doubt_ask, _break_doubt_ask),
    ("thread-reuse",
     "a meeting already mapped gets ZERO new threads — 2 doubts, 1 thread, 2 map records in all",
     _arm_thread_reuse, _break_thread_reuse),
    ("token-order",
     "the routing ask is appended STRICTLY before the write-gate token release",
     _arm_token_order, _break_token_order),
    ("token-file",
     "one token file beside the channel log, naming the ask it followed",
     _arm_token_file, _break_token_file),
    ("amendment",
     "ONE one-liner REPLY to the meeting's filed-note — no thread, no map record",
     _arm_amendment, _break_amendment),
    ("failure-note",
     "exactly ONE channel note naming the failure event's cause, no thread",
     _arm_failure_note, _break_failure_note),
    ("refusal",
     "an invalid payload and an unhandled kind are both refused with a named error",
     _arm_refusal, _break_refusal),
    ("ingest",
     "answers == replies on mapped threads exactly; the unmapped reply is reported, never guessed",
     _arm_ingest, _break_ingest),
    ("answer-schema",
     "every EMITTED owner-answer validates against owner-answer.schema.json",
     _arm_answer_schema, _break_answer_schema),
    ("grounding-note",
     "ONE note carrying every payload field field-for-field, every dead source named",
     _arm_grounding_note, _break_grounding_note),
    ("grounding-once",
     "a second grounding call adds no note and reports already-posted, exit 0",
     _arm_grounding_once, _break_grounding_once),
)


def selftest(seams: Seams) -> dict:
    """Prove every arm green AND red against the bundled fixture."""
    if not FIXTURE_DIR.is_dir():
        return {
            "tool": "channel-protocol", "operation": "selftest", "fixture": str(FIXTURE_DIR),
            "cases": [], "problems": [f"fixture directory missing: {FIXTURE_DIR}"], "ok": False,
        }
    cases = []
    with tempfile.TemporaryDirectory(prefix="channel-protocol-selftest-") as tmpdir:
        tmp = Path(tmpdir)
        base_root = tmp / "base"
        built = _build_channel(seams, base_root)
        base = _observe(seams, base_root, built)
        for name, expectation, predicate, breaker in ARMS:
            green = bool(predicate(base))
            if getattr(breaker, "breaks_obs", False):
                broken = breaker(base, seams, tmp / f"red-{name}")
            else:
                red_root = tmp / f"red-{name}"
                shutil.copytree(base_root, red_root)
                breaker(red_root)
                broken = _observe(seams, red_root, built)
            red = not bool(predicate(broken))
            cases.append({
                "arm": name,
                "expectation": expectation,
                "green": green,
                "red-when-broken": red,
                "pass": green and red,
                "detail": "" if green and red else (
                    "arm did not hold on the good fixture" if not green
                    else "arm STILL held on the broken fixture — a check that cannot fail"
                ),
            })
        totals = channel_totals(Channel(base_root), _store_of(base_root))
    return {
        "tool": "channel-protocol",
        "operation": "selftest",
        "fixture": str(FIXTURE_DIR),
        "cases": cases,
        "channel-totals": totals,
        "discriminating": all(case["red-when-broken"] for case in cases),
        "ok": all(case["pass"] for case in cases),
    }


# ----------------------------------------------------------------------- output
def print_result(result: dict) -> None:
    if result.get("error"):
        error = result["error"]
        print(f"refused: {error['what']}", file=sys.stderr)
        print(f"  why:    {error['why']}", file=sys.stderr)
        print(f"  fix:    {error['fix']}", file=sys.stderr)
        print(f"  escape: {error['escape']}", file=sys.stderr)
        return
    if result["operation"] == "selftest":
        for case in result["cases"]:
            print(f"  {'PASS' if case['pass'] else 'FAIL'}  {case['arm']}")
            print(f"        expect: {case['expectation']}")
            if not case["pass"]:
                print(f"        observed: green={case['green']} "
                      f"red-when-broken={case['red-when-broken']} — {case['detail']}")
        print(f"discriminating: {result['discriminating']}")
        print("ok" if result["ok"] else "NOT ok")
        return
    for message in result.get("messages", []):
        thread = f" thread={message['thread']}" if message.get("thread") else ""
        reply = f" reply-to={message['reply-to']}" if message.get("reply-to") else ""
        head = message["text"].splitlines()[0]
        print(f"  {message['id']} {message['type']}{thread}{reply}: {head}")
    for token in result.get("tokens", []):
        print(f"  {token['token']} released after {token['after-message']} -> {token['file']}")
    for answer in result.get("owner-answers", []):
        print(f"  answer {answer['kind']} on {answer['thread']} "
              f"({answer['meeting-key']}): {answer['answer-text']}")
    for entry in result.get("unmapped", []):
        print(f"  unmapped reply {entry['reply']} on {entry['thread']}: {entry['why']}")
    if result.get("already-posted"):
        print(f"  already-posted: {result['note']} — no second grounding note")
    for problem in result.get("problems", []):
        print(f"  problem: {problem}")
    print("ok" if result["ok"] else "NOT ok")


# ------------------------------------------------------------------------ main
HELP_EPILOG = """\
operations:
  emit [PATH]        one meeting-message-payload or failure-event -> channel messages
  ingest             owner replies on MAPPED threads -> owner-answer objects
  grounding [PATH]   the one-time findings grounding note (a second call posts none)
  selftest           prove every arm green AND red against the bundled fixture

what emit does, per validated payload kind:
  filed-note     ONE one-line note "filed -> repo:path". No thread.
  doubt          create-or-reuse THAT meeting's thread (looked up by meeting-key in
                 the map store), then post the ask: term, standing guess, summary
                 path. A meeting already mapped gets ZERO new threads.
  unroutable     create-or-reuse the thread, post the routing ask, and ONLY after
                 that message is durably appended, release the write-gate token —
                 so seq(ask) < seq(token-release) always holds in the log.
  amendment      ONE one-liner appended as a REPLY to that meeting's filed-note
                 message. Never a thread, never a map record.
  failure-event  ONE note naming the event's cause. No thread.
  Anything that does not validate against its seam schema is refused, named, exit 2.

the transport (--channel DIR), and where a live adapter binds:
  <channel>/messages.jsonl   the ordered log: id, seq, type, thread, reply-to,
                             meeting-key, text, at — one JSON object per line
  <channel>/replies.jsonl    owner replies read by `ingest`: one object per line,
                             {"id","thread","text","at"} plus optional
                             "in-reply-to" naming the ask being answered
  <channel>/tokens/*.json    one write-gate token release each
  This scratch transport is file-backed and fully replayable: the whole channel
  is three readable files. The LIVE transport is OUT OF SCOPE here — an adapter
  binds at the three points marked TRANSPORT SEAM in this file (ordered message
  append/read, reply read, token release) and changes no other line. This engine
  makes no network call of any kind.

the thread<->meeting map store, resolved in this order:
  1. --store PATH
  2. the config key `stores/thread-meeting-map`, read as
     <config-dir>/stores.json -> {"thread-meeting-map": PATH}
     (--config-dir, default: $MEETING_SUMMARIZER_CONFIG_ROOT)
  3. <channel>/stores/thread-meeting-map.jsonl
  Records are jsonl {thread, meeting-key, created-at}, each held to the store seam
  schema before it is written. Thread ids are derived from the meeting-key, so a
  replay of the same stream mints the same ids.

--json (every operation): the machine-readable surface a workflow edge reads.
  emit       messages[], threads[], tokens[], counts{}, channel-totals{}, ok
  ingest     owner-answers[] (each schema-pure), answer-provenance[] (the reply and
             ask each answer came from, kept OUT of the answer object), unmapped[],
             problems[], counts{}, channel-totals{}, ok
  grounding  messages[], note, already-posted, counts{}, channel-totals{}, ok
  selftest   cases[] (arm, green, red-when-broken), discriminating, ok
  counts are THIS invocation; channel-totals are the whole channel — filed-notes,
  doubt-asks, routing-asks, amendments, failure-notes, grounding-notes,
  token-releases, owner-need-threads, replies, messages.

exit codes: 0 ok · 1 ran, ok is false · 2 refused (bad input, missing runtime)

examples:
  channel_protocol.py emit payload.json --channel /tmp/ch --json
  cat payload.json | channel_protocol.py emit --channel /tmp/ch
  channel_protocol.py ingest --channel /tmp/ch --json
  channel_protocol.py grounding findings.json --channel /tmp/ch --json
  channel_protocol.py selftest
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="channel_protocol.py",
        description=(
            "The meeting-summarizer channel engine: per-meeting payloads and failure "
            "events become ordered channel messages, owner replies become owner-answer "
            "objects, and the findings grounding note is posted once. Deterministic — "
            "no network, no model call."
        ),
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true",
                        help="emit one JSON object on stdout (the surface a workflow edge reads)")
    subparsers = parser.add_subparsers(dest="operation")

    def channel_flags(sub) -> None:
        sub.add_argument("--channel", metavar="DIR", required=True,
                         help="the file-backed channel directory (created if absent)")
        sub.add_argument("--store", metavar="PATH", default=None,
                         help="thread<->meeting map store (default: the config key "
                              "stores/thread-meeting-map, else <channel>/stores/...jsonl)")
        sub.add_argument("--config-dir", metavar="DIR", default=None,
                         help="component config dir the store key resolves in "
                              f"(default: ${CONFIG_ROOT_ENV})")
        sub.add_argument("--seams", metavar="DIR", default=None,
                         help="seam set the payloads are validated against "
                              "(default: ../seams beside this tool)")
        sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                         help=argparse.SUPPRESS)  # SUPPRESS: never overwrite a --json
        # given BEFORE the operation — argparse copies subparser defaults up.

    emit_parser = subparsers.add_parser(
        "emit", help="one payload -> its channel messages",
        description="Validate ONE payload against its seam schema and post its messages.")
    emit_parser.add_argument("payload", nargs="?", default="-", metavar="PATH",
                             help="payload JSON file, or - for stdin (default: stdin)")
    channel_flags(emit_parser)

    ingest_parser = subparsers.add_parser(
        "ingest", help="owner replies -> owner-answer objects",
        description="Read replies from the transport; every reply on a MAPPED thread "
                    "becomes exactly one owner-answer. Replies on unmapped threads are "
                    "reported, never guessed into answers.")
    channel_flags(ingest_parser)

    grounding_parser = subparsers.add_parser(
        "grounding", help="post the one-time findings grounding note",
        description="Post ONE grounding note carrying the findings payload field-for-field. "
                    "A second call against the same channel posts nothing and reports "
                    "already-posted, exit 0.")
    grounding_parser.add_argument("findings", nargs="?", default="-", metavar="PATH",
                                  help="findings-payload JSON file, or - for stdin")
    channel_flags(grounding_parser)

    selftest_parser = subparsers.add_parser(
        "selftest", help="prove every arm green AND red against the bundled fixture",
        description="Runs the whole behavior against fixture/channel/ under this tool's "
                    "folder, in a temporary channel whose thread<->meeting store resolves "
                    "through the channel's OWN temporary config root — the live store is "
                    "never read or written. Exits 0 only if every arm held on the "
                    "good fixture AND stopped holding on a broken one — an arm that cannot "
                    "fail is not a check. Touches no channel of yours.")
    selftest_parser.add_argument("--seams", metavar="DIR", default=None,
                                 help="seam set to validate against (default: ../seams)")
    selftest_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                                 help=argparse.SUPPRESS)
    return parser


def read_payload(source: str):
    """(value, error). '-' reads stdin — free text never travels through argv."""
    if source == "-":
        try:
            return json.loads(sys.stdin.read()), None
        except json.JSONDecodeError as exc:
            return None, f"stdin is not valid JSON: {exc}"
    return read_json(Path(source).expanduser())


def open_seams(args) -> Seams:
    declared = getattr(args, "seams", None)
    seams_dir = Path(declared).resolve() if declared else DEFAULT_SEAMS.resolve()
    if not seams_dir.is_dir():
        refuse(
            what=f"no seam set at {seams_dir}",
            why="every payload this engine accepts or emits is validated against the "
                "seam schemas there",
            fix="point the engine at the seam set: --seams DIR",
            escape="none — an unvalidated payload never reaches the channel",
        )
    return Seams(seams_dir)


def main(argv: list[str]) -> int:
    global _JSON_MODE
    parser = build_parser()
    args = parser.parse_args(argv)
    _JSON_MODE = args.json
    if args.operation is None:
        parser.print_help()
        return EXIT_REFUSED

    seams = open_seams(args)

    if args.operation == "selftest":
        result = selftest(seams)
    else:
        root = Path(args.channel).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        channel = Channel(root)
        store, how = resolve_store(args.store, args.config_dir, channel)
        if args.operation == "emit":
            payload, error = read_payload(args.payload)
            result = refusal(
                what=f"cannot read the payload: {args.payload}",
                why=error,
                fix="pass a readable JSON payload file, or - for stdin",
                escape="`selftest` runs the whole behavior against the bundled fixture",
            ) if error else op_emit(payload, seams, channel, store)
        elif args.operation == "ingest":
            result = op_ingest(seams, channel, store)
        else:
            payload, error = read_payload(args.findings)
            result = refusal(
                what=f"cannot read the findings payload: {args.findings}",
                why=error,
                fix="pass a readable findings-payload JSON file, or - for stdin",
                escape="`selftest` runs the same arm against the bundled fixture",
            ) if error else op_grounding(payload, seams, channel, store)
        if not result.get("error"):
            result["store-resolved-by"] = how

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_result(result)
    if result.get("error"):
        return EXIT_REFUSED
    return EXIT_OK if result.get("ok") else EXIT_VERDICT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
