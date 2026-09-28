"""The seeded stream for milestone m5's acceptance suite — the ONE fixture module.

N, D, U, F and every payload of the stream are stated here and nowhere else; every
threshold assertion in the suite is arithmetic over these constants. Payloads are
derived from the seam reference instances at <workflow>/seams/instances/ — each
builder loads the instance and overrides only what distinguishes its meeting, so
the fixtures stay schema-shaped by construction.

MUTATIONS holds the authoring-time falsifiers: each key names the contract arm it
breaks, and running the suite with CHANNEL_SUITE_MUTATE=<key> must turn that arm's
test red. Normal runs leave the variable unset and replay the true stream.
"""

import json
import re
from pathlib import Path


def workflow_root():
    """The transcript-summarizer workflow folder (holds tools/ and seams/).

    Resolved by walking up from this file — the suite's landed home is
    <workflow>/tests/channel/. CHANNEL_PROTOCOL_WORKFLOW overrides for
    out-of-tree runs (test-infra escape hatch, no owner value).
    """
    import os
    for p in Path(__file__).resolve().parents:
        if (p / "tools" / "channel_protocol.py").exists():
            return p
    env = os.environ.get("CHANNEL_PROTOCOL_WORKFLOW")
    if env and (Path(env) / "tools" / "channel_protocol.py").exists():
        return Path(env)
    raise RuntimeError(
        "cannot locate the workflow folder (tools/channel_protocol.py) above this "
        "suite, and CHANNEL_PROTOCOL_WORKFLOW is not set to one"
    )


def _instance(name):
    path = workflow_root() / "seams" / "instances" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the constants

N = 3  # meetings whose outcome is filed/amended (the processed count of clause 10)
D = 2  # of the N, meetings carrying a glossary doubt (M2 twice — second-doubt case)
U = 1  # unroutable meetings — withheld, DISJOINT from the N, no filed-note
F = 2  # failure events

# The meetings. Destinations derive from the reference instances' repo/path
# vocabulary; keys are fixture-fresh so no replayed channel collides with the
# instances' own examples.
MEETINGS = {
    "M1": {  # clean: filed, later amended (the >=1 amendment on a filed meeting)
        "key": "mtg-t5aa0001",
        "title": "Tecer <> Inni — weekly",
        "destination": {"repo": "EXAMPLE-corp",
                        "path": "clients/EXAMPLE-client/meetings/2026-08-14-weekly-resumo.md"},
    },
    "M2": {  # doubted twice: the SECOND doubt must reuse the thread
        "key": "mtg-t5aa0002",
        "title": "Tecer <> Vetta — kickoff",
        "destination": {"repo": "EXAMPLE-corp",
                        "path": "prospects/vetta/meetings/2026-08-14-kickoff-resumo.md"},
        "doubts": [
            {"term": "Quenu", "guess": "Kenu"},
            {"term": "Bortolucci", "guess": "Bertolucci"},
        ],
    },
    "M3": {  # doubted once
        "key": "mtg-t5aa0003",
        "title": "Sessão — acompanhamento",
        "destination": {"repo": "second-brain",
                        "path": "areas/EXAMPLE-wellbeing/2026/encontros/2026-08-14-acompanhamento-resumo.md"},
        "doubts": [
            {"term": "Zilboorg", "guess": "Zilborg"},
        ],
    },
    "M4": {  # unroutable: withheld — never gets a filed-note in this stream
        "key": "mtg-t5aa0004",
        "title": "Alinhamento — projeto novo",
    },
}

FILED = ["M1", "M2", "M3"]      # len == N
DOUBTED = ["M2", "M3"]          # len == D
UNROUTABLE = ["M4"]             # len == U
SECOND_DOUBT_MEETING = "M2"     # the already-threaded meeting doubted again
AMENDED_MEETING = "M1"          # the filed meeting that receives the amendment

FAILURE_EVENTS = [
    {"cause": "Drive auth refused for account tecer (token revoked)",
     "scope": "account", "account": "tecer", "at": "2026-08-14T11:10:04-03:00"},
    {"cause": "poll aborted: Drive API 503 on changes.list",
     "scope": "poll", "at": "2026-08-14T12:10:09-03:00"},
]
assert len(FAILURE_EVENTS) == F

# One reply per thread kind: a glossary doubt's thread and a routing ask's thread.
# Thread ids exist only after replay, so replies name their MEETING; the harness
# resolves the thread. Reply texts derive from the owner-answer instances.
REPLIES = [
    {"meeting": "M2", "expected-kind": "glossary-term",
     "text": _instance("owner-answer-glossary")["answer-text"],
     "at": "2026-08-14T14:02:00-03:00"},
    {"meeting": "M4", "expected-kind": "routing",
     "text": _instance("owner-answer-routing")["answer-text"],
     "at": "2026-08-14T15:20:00-03:00"},
]

def findings_payload():
    """The fixture findings-payload — the m2 reference instance, verbatim."""
    return _instance("findings-payload")


# ---------------------------------------------------------------- the builders

def filed_note(m):
    p = _instance("message-filed-note")
    p["meeting-key"] = m["key"]
    p["destination"] = m["destination"]
    p["meeting-title"] = m["title"]
    return p


def doubt(m, d):
    p = _instance("message-doubt")
    p["meeting-key"] = m["key"]
    p["term"] = d["term"]
    p["guess"] = d["guess"]
    p["summary"] = m["destination"]
    return p


def unroutable(m):
    p = _instance("message-unroutable")
    p["meeting-key"] = m["key"]
    p["signals"]["title"] = m["title"]
    return p


def amendment(m):
    p = _instance("message-amendment")
    p["meeting-key"] = m["key"]
    p["what-changed"] = "second source arrived"
    p["summary"] = m["destination"]
    return p


def failure_event(ev):
    p = _instance("failure-event")
    p.clear()
    p.update({"kind": "failure-event", **ev})
    return p


def build_stream():
    """The ordered emit stream. Ship-then-correct order: a doubted meeting's
    filed-note precedes its doubt; the second doubt lands after another meeting
    threaded in between, so reuse is proven against a non-adjacent state."""
    M = MEETINGS
    return [
        ("filed:M1", filed_note(M["M1"])),
        ("filed:M2", filed_note(M["M2"])),
        ("doubt:M2:1", doubt(M["M2"], M["M2"]["doubts"][0])),
        ("filed:M3", filed_note(M["M3"])),
        ("doubt:M3:1", doubt(M["M3"], M["M3"]["doubts"][0])),
        ("doubt:M2:2", doubt(M["M2"], M["M2"]["doubts"][1])),  # the SECOND doubt
        ("unroutable:M4", unroutable(M["M4"])),
        ("amendment:M1", amendment(M["M1"])),
        ("failure:1", failure_event(FAILURE_EVENTS[0])),
        ("failure:2", failure_event(FAILURE_EVENTS[1])),
    ]


# ------------------------------------------------- authoring-time falsifiers
#
# Stream mutations transform the step list before replay; log mutations rewrite
# the replayed channel afterwards; replay flags flip harness behavior. Each entry
# names the test it must turn red. None runs unless CHANNEL_SUITE_MUTATE names it.

def _drop(label):
    def f(steps):
        return [s for s in steps if s[0] != label]
    return f


STREAM_MUTATIONS = {
    # test_filed_notes_count_and_destinations
    "drop-filed-note": _drop("filed:M3"),
    # test_owner_need_threads_count_and_scope
    "skip-doubt": _drop("doubt:M3:1"),
    # test_second_doubt_reuses_thread
    "fresh-key-second-doubt": lambda steps: [
        (l, {**p, "meeting-key": "mtg-t5aaffff"} if l == "doubt:M2:2" else p)
        for l, p in steps
    ],
    # test_failure_notes_count_and_causes (count half)
    "drop-failure": _drop("failure:2"),
}


def _rewrite_log(channel_dir, fn):
    log = Path(channel_dir) / "messages.jsonl"
    msgs = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    log.write_text("".join(json.dumps(m) + "\n" for m in fn(msgs)), encoding="utf-8")


def _swap_token_order(msgs):
    ask = next(m for m in msgs if m["type"] == "routing-ask")
    tok = next(m for m in msgs if m["type"] == "token-release")
    ask["seq"], tok["seq"] = tok["seq"], ask["seq"]
    tok["after-seq"] = ask["seq"]
    return msgs


def _scrub_failure_cause(msgs):
    for m in msgs:
        if m["type"] == "failure-note":
            m["text"] = "failure (poll): something went wrong"
            break
    return msgs


def _tamper_grounding(msgs):
    for m in msgs:
        if m["type"] == "grounding-note":
            m["text"] = "\n".join(l for l in m["text"].splitlines()
                                  if "tactiq-autosave" not in l)
    return msgs


def _permute_grounding_accounts(msgs):
    """Rotate each account block's precondition lines onto the NEXT account.

    Every line of the note stays PRESENT — only its owner changes — so an
    assertion that tests membership against the whole note text survives this
    and a per-account binding does not.
    """
    for m in msgs:
        if m["type"] != "grounding-note":
            continue
        lines = m["text"].splitlines()
        heads = [i for i, l in enumerate(lines) if l.startswith("account ")]
        assert len(heads) >= 2, "fewer than 2 account blocks to permute"
        bodies = []
        for i in heads:
            j = i + 1
            while j < len(lines) and lines[j].startswith("  "):
                j += 1
            bodies.append((i + 1, j, lines[i + 1:j]))
        rotated = [b[2] for b in bodies[1:]] + [bodies[0][2]]
        assert rotated != [b[2] for b in bodies], "permutation is a no-op"
        out, prev = [], 0
        for (start, end, _), new in zip(bodies, rotated):
            out += lines[prev:start] + new
            prev = end
        out += lines[prev:]
        text = "\n".join(out)
        assert text != m["text"], "mutation left the note unchanged"
        assert sorted(text.splitlines()) == sorted(lines), "not a permutation"
        m["text"] = text
    return msgs


def _name_a_live_source_dead(msgs):
    """Add ONE line to the dead-sources roll, naming a source the payload calls LIVE.

    Every real dead source stays named and every payload value stays present, so
    a membership-only assertion ("each declared dead source appears in the note")
    passes this unchanged. Only an assertion that bounds the roll — the roll IS
    the payload's dead sources, no more — can see it. That is the difference
    between reporting a missed outage and inventing one.
    """
    payload = findings_payload()
    live = None
    for account, body in payload["accounts"].items():
        for name, pv in body["preconditions"].items():
            if pv["verdict"] == "live":
                live = f"  {account} / {name} — fabricated: this source is LIVE"
                break
        if live:
            break
    assert live, "the fixture payload declares no live precondition to misreport"
    for m in msgs:
        if m["type"] != "grounding-note":
            continue
        lines = m["text"].splitlines()
        head = next(i for i, l in enumerate(lines)
                    if re.fullmatch(r"dead sources \(\d+\):", l))
        lines.insert(head + 1, live)
        m["text"] = "\n".join(lines)
    return msgs


def _detach_amendment(msgs):
    for m in msgs:
        if m["type"] == "amendment":
            m["reply-to"] = None
    return msgs


LOG_MUTATIONS = {
    # test_unroutable_ask_precedes_token_release
    "swap-token-order": lambda ch: _rewrite_log(ch, _swap_token_order),
    # test_failure_notes_count_and_causes (names-its-cause half)
    "scrub-failure-cause": lambda ch: _rewrite_log(ch, _scrub_failure_cause),
    # test_grounding_note_field_for_field_and_once (field-for-field half)
    "tamper-grounding": lambda ch: _rewrite_log(ch, _tamper_grounding),
    # test_grounding_note_field_for_field_and_once (per-account attribution half)
    "permute-grounding-accounts": lambda ch: _rewrite_log(
        ch, _permute_grounding_accounts),
    # test_amendments_attach_and_add_no_threads
    "detach-amendment": lambda ch: _rewrite_log(ch, _detach_amendment),
    # test_grounding_note_field_for_field_and_once (dead-roll BOUNDING half —
    # m8 criterion 9: the membership-only assertion this replaced could not see
    # a note that names a live source as dead)
    "dead-roll-names-a-live-source": lambda ch: _rewrite_log(
        ch, _name_a_live_source_dead),
}

# Replay-behavior falsifiers, handled inside the harness:
#   grounding-fresh-channel  — the second grounding call runs against an empty
#                              channel (wrong invocation), so already-posted is
#                              False: test_grounding (posted-once half) goes red.
#   unmapped-reply           — one extra reply on a thread no meeting owns:
#                              ingested answers != replies posted goes red.
#   corrupt-answer-kind      — one ingested answer's kind is rewritten to a value
#                              outside the schema enum: schema-validity goes red.
REPLAY_MUTATIONS = {"grounding-fresh-channel", "unmapped-reply", "corrupt-answer-kind"}

ALL_MUTATIONS = (set(STREAM_MUTATIONS) | set(LOG_MUTATIONS) | REPLAY_MUTATIONS)
