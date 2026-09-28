"""Replay harness for the m5 channel suite.

One session-scoped replay: the seeded stream of stream.py is driven through the
registered channel-protocol CLI against a scratch channel (tmp-path injected —
channel dir AND map-store path), and every test asserts over the one replayed
result. CHANNEL_SUITE_MUTATE=<name> applies a named falsifier (authoring-time
red-proof); unset, the true stream replays.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import stream


CLI = stream.workflow_root() / "tools" / "channel_protocol.py"
MUTATE = os.environ.get("CHANNEL_SUITE_MUTATE", "")
if MUTATE and MUTATE not in stream.ALL_MUTATIONS:
    raise RuntimeError(f"unknown CHANNEL_SUITE_MUTATE {MUTATE!r}; "
                       f"known: {sorted(stream.ALL_MUTATIONS)}")


def run_cli(op, payload=None, *, channel, store, tmpdir, expect_rc=0):
    """One CLI invocation, JSON surface. Refusals fail the replay loudly."""
    cmd = [sys.executable, str(CLI), op]
    if payload is not None:
        pfile = Path(tmpdir) / "payload.json"
        pfile.write_text(json.dumps(payload), encoding="utf-8")
        cmd.append(str(pfile))
    cmd += ["--channel", str(channel), "--store", str(store), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == expect_rc, (
        f"{op} exited {proc.returncode} (wanted {expect_rc}):\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}")
    return json.loads(proc.stdout)


class Replay:
    def __init__(self, channel, store, steps, grounding, ingest, replies_posted):
        self.channel = channel
        self.store = store
        self.steps = dict(steps)            # label -> emit result
        self.step_order = [l for l, _ in steps]
        self.grounding = grounding          # [first result, second result]
        self.ingest = ingest                # ingest result
        self.replies_posted = replies_posted  # reply objects written to replies.jsonl

    # -- read-back surfaces (the channel is three readable files, per --help) --
    def log(self):
        text = (Path(self.channel) / "messages.jsonl").read_text(encoding="utf-8")
        return [json.loads(x) for x in text.splitlines()]

    def messages(self, mtype=None):
        return [m for m in self.log() if mtype is None or m["type"] == mtype]

    def map_records(self):
        p = Path(self.store)
        if not p.exists():
            return []
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]

    def token_files(self):
        tdir = Path(self.channel) / "tokens"
        if not tdir.is_dir():
            return []
        return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(tdir.glob("*.json"))]

    def thread_of(self, meeting_label):
        """The thread the map store binds to this meeting, unique or absent."""
        key = stream.MEETINGS[meeting_label]["key"]
        threads = {r["thread"] for r in self.map_records() if r["meeting-key"] == key}
        assert len(threads) <= 1, f"{meeting_label} holds {len(threads)} threads"
        return threads.pop() if threads else None


@pytest.fixture(scope="session")
def replay(tmp_path_factory):
    channel = tmp_path_factory.mktemp("channel")
    store = tmp_path_factory.mktemp("stores") / "thread-meeting-map.jsonl"
    tmpdir = tmp_path_factory.mktemp("payloads")

    steps = stream.build_stream()
    if MUTATE in stream.STREAM_MUTATIONS:
        steps = stream.STREAM_MUTATIONS[MUTATE](steps)

    results = []
    for label, payload in steps:
        results.append((label, run_cli("emit", payload, channel=channel,
                                       store=store, tmpdir=tmpdir)))

    # the one-time grounding note, invoked twice on purpose
    findings = stream.findings_payload()
    g1 = run_cli("grounding", findings, channel=channel, store=store, tmpdir=tmpdir)
    second_channel = channel
    if MUTATE == "grounding-fresh-channel":  # wrong invocation: idempotence red
        second_channel = tmp_path_factory.mktemp("wrong-channel")
    g2 = run_cli("grounding", findings, channel=second_channel, store=store,
                 tmpdir=tmpdir)

    # owner replies, one per thread kind, resolved to the replayed thread ids
    partial = Replay(channel, store, results, [g1, g2], None, [])
    replies = []
    for i, r in enumerate(stream.REPLIES):
        thread = partial.thread_of(r["meeting"])
        assert thread, f"no thread replayed for {r['meeting']}"
        replies.append({"id": f"reply-{i+1}", "thread": thread,
                        "text": r["text"], "at": r["at"]})
    if MUTATE == "unmapped-reply":  # mutated fixture: a reply nobody owns
        replies.append({"id": "reply-x", "thread": "thr-nobody-owns-this",
                        "text": "?", "at": "2026-08-14T16:00:00-03:00"})
    with open(Path(channel) / "replies.jsonl", "a", encoding="utf-8") as f:
        for r in replies:
            f.write(json.dumps(r) + "\n")

    ingest = run_cli("ingest", channel=channel, store=store, tmpdir=tmpdir)
    if MUTATE == "corrupt-answer-kind" and ingest.get("owner-answers"):
        ingest["owner-answers"][0]["kind"] = "not-a-real-kind"

    if MUTATE in stream.LOG_MUTATIONS:
        stream.LOG_MUTATIONS[MUTATE](channel)

    return Replay(channel, store, results, [g1, g2], ingest, replies)
