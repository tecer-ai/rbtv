#!/usr/bin/env python3
"""per-meeting-job — one meeting in, exactly one corrected summary out.

The job goal.md's opening paragraph describes: take ONE meeting's artifacts,
cross-reference them into one text, route it, and let the owner's own summarizer
skill write the summary in the skill's OWN format. This module adds no format,
no section and no field of its own, and it never re-implements a step of either
skill — it composes four pieces that already exist:

  artifact_reader       the bytes, and the artifact-kind / legibility verdicts
  transcript_merge      clause 5: Meet wording wins every differing utterance
  destination_resolver  clause 6: where it goes, read from owner config
  channel_protocol      clauses 7/10/12: the ask, and the one note per meeting

The rule the rest of the file is arranged around: **nothing is written to a
destination before its ask is answered** (clause 7). That is why resolution runs
BEFORE a single byte is prepared for the summarizer, and why the ask paths
return without ever reaching the invocation.

Run with --help for the command surface.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import artifact_reader
import channel_protocol
import destination_resolver
import publish_job
import transcript_merge
from source_adapter import NOTES_SOURCE

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_SEAMS = TOOL_DIR.parent / "seams"
CONFIG_KEY = "summarize"

EXIT_OK = 0
EXIT_VERDICT = 1  # ran fine, the meeting did not produce a summary
EXIT_REFUSED = 2  # could not run

# The durable settlement record. A meeting with a row here is FINISHED: it is
# never re-asked and never re-noted. Rows are pure seam objects — the
# per-meeting-outcome shape in `outcomes.jsonl`, the completion-record shape in
# `completions.jsonl` — so this module invents no record of its own.
OUTCOMES = "outcomes.jsonl"
COMPLETIONS = "completions.jsonl"

# The summarize -> channel handoff. One row per summary that was written AND
# carries at least one doubt marker; the channel cycle reads this file and asks
# the owner about each term. The row is born HERE because this is where the
# summary is written and where its markers first exist on disk — the channel
# cannot derive it, and a translator on the channel side would be a second
# producer of a fact this step already holds.
DOUBTS = "doubts.jsonl"

# The line a notes-only summary carries under its title (clause 19 as amended
# 2026-09-27) — a reader must see the summary was built from notes, not speech.
# Where Google Meet's transcript, split out of a Gemini notes document, is staged.
GOOGLE_TRANSCRIPT_SUFFIX = "-transcript-google.md"

# Clause 5 for a Google transcript beside a second one (owner ruling
# r-google-transcript-in-notes): Google's wording wins, the other is noted, and no
# quote is ever assembled from the two.
RECONCILE_RULE = (
    "Both transcripts record the same speech. Where they cover the same words and disagree, "
    "use the Google Meet wording and note the other version beside it once, e.g. "
    "`ativar (Tactiq: \"desativar\")`. Use the second transcript only for speech the Google one "
    "does not have. NEVER combine the two into a quote that neither transcript contains.")

# The closing line the content-routing model answers on (see classify_content).
ROUTE_KEY = "ENTITY"

NOTES_ONLY_LABEL = "> Source: Gemini notes only — no transcript."

# The marker grammar is FIXED by the doubt-flag-marker seam's `marker-syntax`
# const. This regex reads it; the const itself is never typed here — it is read
# from the schema and the assembled row is validated against that schema before
# it is appended, so a grammar change fails loudly instead of silently emitting
# rows nothing can parse.
DOUBT_MARKER_RE = re.compile(r"\{\{doubt\|term=([^|}]+)\|guess=([^|}]*)\}\}")

# The grammar's OWN metavariables, as they appear inside the seam's
# `marker-syntax` const. Every summary that carries at least one doubt also
# carries the skill's explanation line (the ra-1 byte-exact template), whose
# markers are these placeholders — the notation being DOCUMENTED, not used. A
# term called `<term>` is not a term any meeting produced and not one the owner
# can resolve, so it is never a doubt. Pinned to the const by the summarize
# suite (test_doubts_handoff.py), so a grammar change fails a test, not an owner.
LEGEND_TERM = "<term>"
LEGEND_GUESS = "<best-guess>"

# The owner reply that means "file nothing for this meeting" (clause 24).
SKIP_ANSWER = "skip"

REPORT_KEYS = ("GLOSSARY-LOADED", "CLASSIFIED", "DESTINATION", "SUMMARY",
               "TRANSCRIPT-WRITEBACK", "GLOSSARY-WRITEBACK", "DOUBTS",
               "PROPAGATED", "OWNER-TURNS", "OUTCOME")


def refuse(what: str, fix: str) -> None:
    print(f"per-meeting-job refused: {what}\n  fix: {fix}", file=sys.stderr)
    raise SystemExit(EXIT_REFUSED)


def now_stamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        refuse(f"no such file: {path}", "pass a path that exists")
    except (OSError, json.JSONDecodeError) as exc:
        refuse(f"{path} is not readable JSON: {exc}", "fix the file, then re-run")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------- config
def load_config(config_root: Path) -> dict:
    """The one config datum this job reads of its own: `summarize`.

    Two declared things live in it — the display-name markers that tell an
    auxiliary notes artifact from a transcript, and which summarizer skill an
    entity's meetings are written by. Both are OWNER values and neither is ever
    typed into this file.
    """
    path = config_root / f"{CONFIG_KEY}.json"
    if not path.is_file():
        refuse(f"the config key '{CONFIG_KEY}' names {path}, which does not exist",
               f"create {path}, or point --config-root at the config-module home that has it")
    data = read_json(path)
    for section in ("artifact-kinds", "skill-bindings"):
        if not isinstance(data.get(section), dict):
            refuse(f"{path} declares no '{section}' object",
                   f"add a '{section}' section; see the file's own _this-file note")
    return data


def skill_for(entity: str, bindings: dict) -> str:
    """The skill file an entity's meetings are summarized by, from config.

    A `default` is honoured only if the owner declared one. With neither an
    entity binding nor a default, the job fails loudly rather than picking a
    skill — choosing a summarizer for the owner is a guess, and clause 7's
    prohibition on guessing a destination has no reason to stop at the folder.
    """
    chosen = bindings.get("by-entity", {}).get(entity) or bindings.get("default")
    if not chosen:
        refuse(f"no summarizer skill is declared for entity '{entity}'",
               "add it under skill-bindings.by-entity, or declare skill-bindings.default")
    return chosen


# --------------------------------------------------------------- the channel
class Bus:
    """The channel, as this job uses it: post one message, read what was posted."""

    def __init__(self, root: Path, seams: Path, store: Path):
        # Nothing is created here. A meeting the job says nothing about must leave
        # the channel untouched — a count of write operations, and a directory
        # created just in case is one of them.
        self.root = Path(root)
        self.seams = channel_protocol.Seams(seams)
        self.store = Path(store)

    def emit(self, payload: dict) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        result = channel_protocol.op_emit(payload, self.seams,
                                          channel_protocol.Channel(self.root), self.store)
        if result.get("error") or not result.get("ok"):
            refuse(f"the channel refused the payload: {json.dumps(result)[:400]}",
                   "fix the payload; it must validate against its seam schema")
        return result

    def messages(self, meeting_key: str) -> list[dict]:
        return [row for row in channel_protocol.Channel(self.root).messages()
                if row.get("meeting-key") == meeting_key]

    def answers(self, meeting_key: str, kind: str) -> list[dict]:
        result = channel_protocol.op_ingest(self.seams, channel_protocol.Channel(self.root),
                                            self.store)
        return [answer for answer in result.get("owner-answers", [])
                if answer.get("meeting-key") == meeting_key and answer.get("kind") == kind]


# ------------------------------------------------------------- the settlement
def settled(state: Path, meeting_key: str) -> dict | None:
    for row in read_jsonl(state / OUTCOMES):
        if row.get("meeting-key") == meeting_key:
            return row
    return None


def settle(state: Path, meeting_key: str, outcome: str, destination=None,
           content_entity: str | None = None) -> dict:
    row = {"kind": "per-meeting-outcome", "meeting-key": meeting_key,
           "outcome": outcome, "at": now_stamp()}
    if destination:
        row["destination"] = destination
    if content_entity:
        # Durable: the publish stage re-resolves the route and must reach the SAME
        # answer, so the content pick travels with the settlement, not in memory.
        row["content-entity"] = content_entity
    append_jsonl(state / OUTCOMES, row)
    return row


def parse_doubts(text: str) -> list[dict]:
    """Every doubt marker in a written summary, in the seam's `doubt` shape.

    One entry per DISTINCT term — the same term marked twice in one summary is
    one doubt, because the owner is asked about a term and not about a line. The
    excerpt is the first line carrying that term's marker.

    The legend's own placeholder pair is skipped: a marker whose term and guess
    are exactly the grammar's metavariables is a line ABOUT the notation, never
    a doubt a meeting produced. The exclusion is structural — it matches the
    legend's markers, never an owner's real terms.
    """
    found: dict[str, dict] = {}
    for line in text.splitlines():
        for term, guess in DOUBT_MARKER_RE.findall(line):
            if term == LEGEND_TERM and guess == LEGEND_GUESS:
                continue
            if term not in found:
                found[term] = {"term": term, "guess": guess or term,
                               "excerpt": line.strip()}
    return list(found.values())


def hand_off_doubts(state: Path, seams: Path, *, meeting_key: str, entity: str,
                    work: Path, transcript: Path, destination: dict,
                    summary_path: Path) -> dict | None:
    """Append this meeting's summarize -> channel handoff row, or nothing.

    Returns the row it appended, or None when the summary carries no doubt.
    A summary with no marker produces NO row: the channel's quiet is the
    product's stated payoff, and an empty row would be a message with nothing
    in it.
    """
    try:
        text = Path(summary_path).read_text(encoding="utf-8")
    except OSError as exc:
        refuse(f"the summarizer reported a summary at {summary_path} that cannot be read: {exc}",
               "the skill's SUMMARY path must name the file it wrote")
    doubts = parse_doubts(text)
    if not doubts:
        return None

    seam_set = channel_protocol.Seams(seams)
    schema, error = seam_set.schema("doubt-flag-marker.schema.json")
    if error:
        refuse(f"the doubt-flag-marker seam schema is unreadable: {error}",
               "point this job at the seam set with --seams DIR")
    marker = {
        "summary": destination,
        # Read from the seam, never typed: the schema fixes this value by const.
        "marker-syntax": schema["properties"]["marker-syntax"]["const"],
        "doubts": doubts,
    }
    problems = seam_set.errors(marker, schema)
    if problems:
        refuse("the doubt handoff this job assembled does not validate against the "
               f"doubt-flag-marker seam: {'; '.join(problems[:3])}",
               "the marker grammar or the seam changed; reconcile them before running")
    row = {"meeting-key": meeting_key, "entity": entity, "work": str(work),
           "transcript": f"./{Path(transcript).name}", "marker": marker}
    append_jsonl(state / DOUBTS, row)
    return row


def complete(state: Path, meeting_key: str, answered_kind: str) -> dict:
    row = {"meeting-key": meeting_key, "answered-kind": answered_kind,
           "completed-at": now_stamp()}
    append_jsonl(state / COMPLETIONS, row)
    return row


# ------------------------------------------------------------ the invocation
def report_block(text: str) -> dict:
    """The skill's own closing report. Its keys, not ours — we add none."""
    found: dict = {}
    for line in (text or "").splitlines():
        key, sep, value = line.partition(":")
        key = key.strip().lstrip("`*# ").strip()
        if sep and key in REPORT_KEYS:
            found[key] = value.strip().strip("`")
    return found


def summary_path_only(reported: str) -> str:
    """The SUMMARY report line's leading path, trailing prose stripped.

    The skill's own report sentence is free text after the path — e.g.
    "SUMMARY: /repo/file.md (existing; amended in place, 0 changes)" — and
    `report_block()` keeps the whole rest of the line as the value. A path in
    this tree never contains whitespace (the vault's own filename rules), so
    the first whitespace-delimited token is the path and everything after it
    is commentary, never part of the path itself.
    """
    return reported.strip().split()[0] if reported.strip() else ""


def invocation_of(config: dict) -> dict:
    """Which harness, model and effort run the product's unattended agent turns.

    OWNER configuration (`summarize` → `invocation`), never a vendor typed into
    code: the turn goes through `cast`, the workspace's harness-neutral launcher.
    """
    chosen = config.get("invocation") or {}
    missing = [key for key in ("harness", "model", "effort") if not chosen.get(key)]
    if missing:
        refuse(f"the summarize config declares no invocation {missing}",
               "add 'invocation': {'harness', 'model', 'effort'} — see `cast -h` for the choices")
    return chosen


def invoke_agent(prompt: str, cwd: Path, log_dir: Path, timeout: int,
                 invocation: dict) -> dict:
    """ONE unattended agent turn through `cast`, standard input closed to EOF.

    The ONE place the product starts a model: the summarizer skill, the content
    router and the channel's amendment re-entry all come through here. Nothing
    here re-implements a step of a skill; the prompt names the skill file.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    argv = ["cast", invocation["harness"], invocation["model"], str(invocation["effort"]),
            str(cwd), "-p", prompt]
    try:
        with open(os.devnull, "rb") as closed_stdin:
            finished = subprocess.run(argv, cwd=str(cwd), stdin=closed_stdin,
                                      capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        (log_dir / "stderr.txt").write_text(str(exc), encoding="utf-8")
        return {"exit": EXIT_REFUSED, "text": "", "why": str(exc)}
    (log_dir / "stdout.txt").write_text(finished.stdout or "", encoding="utf-8")
    (log_dir / "stderr.txt").write_text(finished.stderr or "", encoding="utf-8")
    return {"exit": finished.returncode, "text": finished.stdout or ""}


def stage_sources(work: Path, key: str, merged: dict | None, notes: list[dict],
                  google: str | None = None) -> tuple[Path | None, Path | None, list[Path]]:
    """Write the merged Tactiq/Meet transcript (None when there is none), Google's
    transcript from the notes document (None when absent) and the notes into the
    job's work folder. Idempotent: routing and summarizing may both need them."""
    work.mkdir(parents=True, exist_ok=True)
    transcript_path = google_path = None
    if merged is not None:
        transcript_path = work / f"{key}-transcript.md"
        transcript_path.write_text(merged["text"], encoding="utf-8")
    if google:
        google_path = work / f"{key}{GOOGLE_TRANSCRIPT_SUFFIX}"
        google_path.write_text(google, encoding="utf-8")
    note_paths = []
    for index, note in enumerate(notes, start=1):
        note_path = work / f"{key}-notes-{index}.md"
        note_path.write_text(note["text"], encoding="utf-8")
        note_paths.append(note_path)
    return transcript_path, google_path, note_paths


def owner_named_entity(bus, meeting_key: str, choices: list[dict]) -> str | None:
    """The declared entity the owner's latest routing answer names, or None."""
    if not choices:
        return None
    answers = bus.answers(meeting_key, "routing")
    if not answers:
        return None
    text = answers[-1]["answer-text"].strip().casefold()
    return next((c["entity"] for c in choices if c["entity"].casefold() == text), None)


def classify_content(sources: list[Path], choices: list[dict], work: Path, log_dir: Path,
                     timeout: int, invoke) -> str | None:
    """Which declared destination this meeting's CONTENT belongs to, or None.

    Pass two of routing (owner ruling r-route-by-content-not-account). A model reads
    the staged sources and picks ONE declared entity; "unsure", an entity nobody
    declared, or a failed run is None — and None is asked, never defaulted.
    """
    entities = [choice["entity"] for choice in choices]
    lines = ["You are deciding where ONE meeting's summary is filed. Read the meeting:"]
    lines += [f"- ./{path.name}" for path in sources]
    lines += ["", "The destinations, each with what its meetings are about:"]
    lines += [f"- {choice['entity']}: {choice['content']}" for choice in choices]
    lines += ["",
              "Pick the ONE destination the meeting's CONTENT clearly belongs to. If it could "
              "belong to more than one, or to none, the answer is unsure — a wrong pick files "
              "private material in the wrong place, and unsure only asks the owner.",
              "Write no file. End with exactly one line:",
              f"{ROUTE_KEY}: <one of {', '.join(entities)}, or unsure>"]
    outcome = invoke("\n".join(lines), work, log_dir, timeout)
    if outcome["exit"] != 0:
        return None
    answers = [line.partition(":")[2].strip().strip("`*").strip()
               for line in (outcome["text"] or "").splitlines()
               if line.strip().lstrip("`*# ").startswith(f"{ROUTE_KEY}:")]
    return answers[-1] if answers and answers[-1] in entities else None


def artifact_kind(item: dict) -> str:
    """Transcript or notes. A record the sweep classified as notes IS notes.

    The reader's byte-level verdict can call a notes file a transcript — a Gemini
    notes file can carry timestamped lines — and a notes file taken for a
    transcript would be merged, quoted and glossary-corrected as spoken words.
    So the record's own source outranks the reader in that one direction; a
    transcript record still needs the reader to agree before it is a transcript.
    """
    if item["record"]["source"] == NOTES_SOURCE:
        return "meeting-notes"
    return item["read"]["artifact-kind"]


def build_prompt(skill: str, transcript: Path | None, notes: list[Path], routed: dict,
                 checkout_root: Path, token: str, targets: dict,
                 google: Path | None = None) -> str:
    """The invocation text. Every line of it is addressing the skill's OWN gates.

    `google` is Google Meet's verbatim transcript split out of a Gemini notes
    document — speech, and the PRIMARY wording (clause 5). `transcript` is the
    merged Tactiq/Meet transcript. Both None is a notes-only meeting (clause 19):
    the notes are the only source, and the summary must say so where a reader
    sees it. Every source is named for what it is, so the summary can too.
    """
    destination = routed["destination"]
    repo_root = checkout_root / destination["repo"]
    lines = [
        f"Read and execute {skill}",
        "",
        "Operating scope: the CLAUDE.md in the current working directory. Its `## Name Glossary`",
        "section declares the glossary this run must load.",
        "",
    ]
    if transcript is None and google is None:
        lines += [f"Meeting notes (the ONLY source — no transcript exists): ./{note.name}"
                  for note in notes]
        lines += [
            "These are model-written notes (Gemini), not spoken words: never quote them as "
            "speech, and never glossary-correct, rename or write back to them.",
            "LABEL the summary: its first line under the title must read exactly "
            f"`{NOTES_ONLY_LABEL}`.",
        ]
    else:
        if google is not None:
            lines.append(f"Transcript — Google Meet's own verbatim transcript (speech; the "
                         f"PRIMARY wording): ./{google.name}")
        if transcript is not None:
            lines.append(f"Transcript — {'second transcript of the same speech (Tactiq/Meet)' if google else 'verbatim'}: ./{transcript.name}")
        if google is not None and transcript is not None:
            lines.append(RECONCILE_RULE)
        if google is not None:
            lines.append("In the summary's source line, name each source for what it is: "
                         "Google Meet's transcript and any second transcript are speech; "
                         "Gemini's notes are a model-written summary.")
    for note in notes if (transcript is not None or google is not None) else []:
        lines.append(
            f"Auxiliary meeting notes: ./{note.name} — use it for DISAMBIGUATION and CURATION "
            "only (who was in the room, which name is which, which decisions were actually "
            "taken). It never overrides the transcript's raw wording. It is a model-written "
            "summary, not spoken words: never quote it as speech, and never glossary-correct, "
            "rename or write back to it.")
    # The summarizer writes the FINAL, discriminated name itself, so publication
    # files that very file and no undiscriminated draft is left behind.
    if destination.get("placement") == "template":
        target = repo_root / publish_job.discriminate(destination["path"], token, targets)
        lines += [f"Destination folder: {target.parent}",
                  f"Summary filename: {target.name}"]
    else:
        lines += [f"Destination repo: {repo_root}",
                  "Placement inside that repo is decided by that repo's own CLAUDE.md — read it "
                  "and follow it.",
                  f"Then append `-{token}` (the meeting's start time) to the summary file name's "
                  f"stem, e.g. `x-summary.md` -> `x-summary-{token}.md`: it keeps two same-day "
                  "meetings apart. Use that name everywhere the repo's rules reference the file."]
    lines += [f"Meeting entity: {routed['entity']}.",
              "Leave the source files where they are — do not move or rename them.",
              "",
              "Execute in **unattended mode**."]
    return "\n".join(lines)


# ----------------------------------------------------------------- the job
def run(job: dict, *, artifacts: dict, config_root: Path, checkout_root: Path,
        channel_root: Path, state: Path, work: Path, seams: Path,
        store: Path, timeout: int = 900, invoke=None) -> dict:
    """One meeting, start to finish. Returns what happened and what it wrote."""
    key = job["meeting-key"]
    config = load_config(config_root)
    if invoke is None:
        # Resolved at call time: a meeting that never reaches a model needs none.
        def invoke(prompt, cwd, log_dir, timeout):
            outcome = invoke_agent(prompt, cwd, log_dir, timeout, invocation_of(config))
            return {**outcome, "report": report_block(outcome["text"])}
    bus = Bus(channel_root, seams, store)
    verdict = {"meeting-key": key, "wrote-summary": False, "messages": 0,
               "asked": False, "settled": False}

    # The spine computes the disposition from the durable processed record and is
    # its one home; this job obeys it rather than recomputing it. `amend` falls
    # through to the same path as `new` on purpose — the skill's own `## Amendment
    # Mode` / re-run safety rewrites an existing summary IN PLACE, and a second
    # implementation of that here would be the private fork the owner ruled out.
    if job.get("disposition") == "already-done":
        return {**verdict, "action": "nothing-to-do",
                "why": "the job arrived with disposition `already-done`: every source in this "
                       "meeting's set is already covered by a processed record"}

    already = settled(state, key)
    if already:
        return {**verdict, "action": "already-settled", "outcome": already["outcome"],
                "why": "this meeting carries a settlement record; it is neither re-asked "
                       "nor re-noted"}

    # 1 · the bytes, and the two verdicts only the reader can give
    markers = config["artifact-kinds"]
    bindings = artifacts.get("artifacts", {})
    reads = []
    for record in job["source-set"]:
        ref = record["drive-ref"]
        if ref not in bindings:
            refuse(f"the artifact map carries no binding for {ref}",
                   "bind every drive-ref in the source set before running the job")
        reads.append({"record": record,
                      "read": artifact_reader.read_artifact(ref, bindings[ref], markers)})
    auxiliary = [artifact_reader.read_artifact(ref, bindings[ref], markers)
                 for ref in artifacts.get("auxiliary", {}).get(key, []) if ref in bindings]

    # 2 · clause 19 — notes alone are summarized FROM the notes, labelled as such
    #     (owner ruling r-gemini-notes-alone-triggers-summary, 2026-09-27); detection
    #     decides which notes-only meetings reach this job at all
    transcripts = [item for item in reads
                   if artifact_kind(item) == "transcript" and item["read"]["legible"]]
    notes = [item["read"] for item in reads
             if artifact_kind(item) == "meeting-notes" and item["read"]["legible"]]
    notes += [note for note in auxiliary if note["legible"]]
    # Clause 19 (owner ruling r-google-transcript-in-notes): a Gemini notes document
    # may carry Google Meet's own verbatim transcript. That part is SPEECH — split
    # off and passed as the primary transcript; the rest stays Gemini's summary.
    headings = config["artifact-kinds"].get("meeting-notes", {}).get("transcript-headings", [])
    google = []
    for index, note in enumerate(notes):
        summary_part, spoken = artifact_reader.split_notes(note["text"], headings)
        if spoken:
            google.append(spoken)
            notes[index] = {**note, "text": summary_part}
    google_text = "\n\n".join(google) or None
    verdict["google-transcript"] = bool(google_text)
    notes_only = not transcripts and not google_text
    merged = None
    if not transcripts:
        # "No transcript" has TWO causes and they end differently. Everything read
        # cleanly as notes is clause 19's case: the notes are the source. Anything
        # else — an artifact nothing identified, or one that IS a transcript but
        # could not be decoded — is a transcript the pipeline saw and did not
        # process, which clause 12 says must never be silent.
        unread = [item for item in reads
                  if not (artifact_kind(item) == "meeting-notes" and item["read"]["legible"])]
        if unread:
            causes = "; ".join(sorted({
                item["read"].get("illegible-reason")
                or f"the artifact at {item['read']['ref']} could not be identified as a "
                   f"transcript or as notes"
                for item in unread}))
            bus.emit({"kind": "failure-event", "scope": "meeting", "meeting-key": key,
                      "cause": f"no usable transcript for this meeting: {causes}",
                      "at": now_stamp()})
            return {**verdict, "action": "unreadable", "messages": 1, "outcome": "failed",
                    "unread": [item["read"]["ref"] for item in unread]}
        verdict["notes-only"] = notes_only
    else:
        # 3 · clause 5 — Meet wording wins every utterance the two sources differ on
        merged = transcript_merge.merge(
            {item["record"]["source"]: item["read"]["text"] for item in transcripts})
        verdict["merge"] = {k: v for k, v in merged.items() if k not in ("text", "decisions")}
        verdict["merge-decisions"] = merged["decisions"]

    # 4 · clause 25a — nothing was said, so there is nothing to summarize
    if merged is not None and merged["utterances"] == 0 and not google_text:
        bus.emit({"kind": "failure-event", "scope": "meeting", "meeting-key": key,
                  "cause": "the transcript carries zero utterances; there is nothing to summarize",
                  "at": now_stamp()})
        settle(state, key, "unprocessable")
        return {**verdict, "action": "zero-utterance", "messages": 1, "settled": True,
                "outcome": "unprocessable"}

    # 5 · clause 6/7 — where it goes: facts first, then the owner's answer or the
    #     content, else ASKED. BEFORE any destination write.
    routed_job = job
    routed = destination_resolver.resolve(job, config_root)
    choices = destination_resolver.content_routes(config_root) if routed["kind"] != "routed" else []
    answered = owner_named_entity(bus, key, choices)
    if answered:
        # The owner's reply to this meeting's routing ask names a destination: it is
        # applied exactly as a content pick, and completes the ask.
        routed_job = {**job, "content-entity": answered}
        routed = destination_resolver.resolve(routed_job, config_root)
        complete(state, key, "routing")
    elif routed["kind"] != "routed" and choices:
        transcript_path, google_path, note_paths = stage_sources(work, key, merged, notes,
                                                                 google_text)
        picked = classify_content([p for p in (google_path, transcript_path) if p] or note_paths,
                                  choices, work, state / "runs" / key / "route", timeout, invoke)
        verdict["content-routing"] = picked or "unsure"
        if picked:
            routed_job = {**job, "content-entity": picked}
            routed = destination_resolver.resolve(routed_job, config_root)
    if routed["kind"] != "routed":
        return ask_or_apply(job, routed, bus, state, verdict)

    # 6 · the sources, staged in the job's own work folder (never a destination)
    transcript_path, google_path, note_paths = stage_sources(work, key, merged, notes, google_text)

    # 7 · the summary, in the skill's own format — and a record of every
    #     destination path the sitting changed, so publication commits the
    #     summarizer's propagation with it (owner ruling, 2026-09-27)
    targets = publish_job.load_targets(config_root)
    token = publish_job.discriminator(job, targets, destination_resolver.load_routing(config_root))
    prompt = build_prompt(skill_for(routed["entity"], config["skill-bindings"]),
                          transcript_path, note_paths, routed, checkout_root, token, targets,
                          google=google_path)
    repo_root = checkout_root / routed["destination"]["repo"]
    # Only a clone the workflow OWNS: in a shared vault a peer's concurrent write
    # would land in the diff, so there only publication's own paths are committed.
    target = publish_job.target_for(routed["destination"]["repo"], targets)
    watched = target["regime"] == "git" and (repo_root / ".git").is_dir()
    if watched:
        # Pull BEFORE the summarizer writes: its propagation then edits the files
        # as the remote has them, and publication's push never meets a stale tree.
        verdict["synced"] = publish_job.sync(target, repo_root)
    before = publish_job.dirty_paths(repo_root) if watched else set()
    outcome = invoke(prompt, work, state / "runs" / key, timeout)
    if watched:
        record = state / "runs" / key / publish_job.PROPAGATED_FILE
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(
            {"paths": sorted(publish_job.dirty_paths(repo_root) - before)}) + "\n",
            encoding="utf-8")
    reported = outcome["report"]
    if outcome["exit"] != 0 or reported.get("OUTCOME") not in ("filed", "amended"):
        bus.emit({"kind": "failure-event", "scope": "meeting", "meeting-key": key,
                  "cause": f"the summarizer did not file: {reported.get('OUTCOME') or 'no report'}",
                  "at": now_stamp()})
        return {**verdict, "action": "summarize-failed", "messages": 1,
                "outcome": "failed", "skill-report": reported}
    written = summary_path_only(reported.get("SUMMARY") or "")
    destination = {"repo": routed["destination"]["repo"],
                   "path": relative_to_repo(written, checkout_root,
                                            routed["destination"]["repo"])}
    settle(state, key, reported["OUTCOME"], destination, routed_job.get("content-entity"))
    handoff = hand_off_doubts(state, seams, meeting_key=key, entity=routed["entity"],
                              work=work,
                              transcript=transcript_path or google_path or note_paths[0],
                              destination=destination, summary_path=written)
    return {**verdict, "action": "summarized", "wrote-summary": True, "settled": True,
            "outcome": reported["OUTCOME"], "destination": destination,
            "skill-report": reported, "summary-file": written,
            "doubts-handed-off": len(handoff["marker"]["doubts"]) if handoff else 0}


def relative_to_repo(written: str, checkout_root: Path, repo: str) -> str:
    """The summary as a repo-relative path — the seam's shape, never an absolute one."""
    try:
        return Path(written).resolve().relative_to((checkout_root / repo).resolve()).as_posix()
    except (ValueError, OSError):
        return Path(written).name


def ask_or_apply(job: dict, routed: dict, bus: Bus, state: Path, verdict: dict) -> dict:
    """An unroutable meeting: ask, or apply the answer already in hand.

    NOTHING here writes to a destination, on any branch. That is the whole point
    of reaching this function before the summarizer is prepared, let alone run.
    """
    key = job["meeting-key"]
    answers = bus.answers(key, "routing")
    if not answers:
        asked = [row for row in bus.messages(key) if row.get("type") == "routing-ask"]
        if asked:
            return {**verdict, "action": "awaiting-answer", "asked": True,
                    "why": "this meeting's routing ask is already standing; the owner answers "
                           "a thing once", "outcome": "withheld-unroutable"}
        result = bus.emit({"kind": "unroutable", "meeting-key": key,
                           "signals": routed["signals"]})
        return {**verdict, "action": "asked", "asked": True,
                "messages": len(result.get("messages", [])),
                "outcome": "withheld-unroutable"}

    answer = answers[-1]
    if answer["answer-text"].strip().casefold() == SKIP_ANSWER:
        settle(state, key, "skipped")
        complete(state, key, "routing")
        return {**verdict, "action": "skipped", "settled": True, "asked": True,
                "outcome": "skipped",
                "why": "the owner answered `skip`: nothing is filed, the meeting is recorded "
                       "processed, and it is never asked again"}
    return {**verdict, "action": "answered-unknown-destination", "asked": True,
            "outcome": "withheld-unroutable", "answer": answer["answer-text"],
            "why": "the owner's answer names no declared destination entity (nor `skip`); "
                   "nothing is written and the ask stays standing"}


# --------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="per_meeting_job",
        description="One meeting's artifacts -> exactly one corrected summary in the summarizer "
                    "skill's own format, with unroutable and non-meeting cases asked before "
                    "anything is written.")
    parser.add_argument("--job", required=True, type=Path, help="a per-meeting-job JSON")
    parser.add_argument("--artifacts", required=True, type=Path,
                        help="the artifact binding table the reader resolves refs through")
    parser.add_argument("--config-root", required=True, type=Path,
                        help="the component config-module home")
    parser.add_argument("--checkout-root", required=True, type=Path,
                        help="where destination repos are checked out (deployment config)")
    parser.add_argument("--channel", required=True, type=Path, help="the channel directory")
    parser.add_argument("--state", required=True, type=Path,
                        help="where the settlement records and run logs live")
    parser.add_argument("--work", required=True, type=Path,
                        help="the summarizer's working directory (carries its operating scope)")
    parser.add_argument("--store", type=Path, help="thread<->meeting map store")
    parser.add_argument("--seams", type=Path, default=DEFAULT_SEAMS)
    parser.add_argument("--timeout", type=int, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run(read_json(args.job),
                 artifacts=read_json(args.artifacts),
                 config_root=args.config_root,
                 checkout_root=args.checkout_root,
                 channel_root=args.channel,
                 state=args.state,
                 work=args.work,
                 seams=args.seams,
                 store=args.store or (args.channel / "stores" / "thread-meeting-map.jsonl"),
                 timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK if result.get("wrote-summary") or result.get("settled") else EXIT_VERDICT


if __name__ == "__main__":
    raise SystemExit(main())
