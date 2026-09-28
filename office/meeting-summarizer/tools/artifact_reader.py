#!/usr/bin/env python3
"""artifact-reader — the artifact-content reader protocol.

Turns one opaque `drive-ref` into a seam-valid `read-result`: the decoded text
plus the two verdicts the consumer cannot re-derive from the bytes alone —
WHICH KIND of artifact it is (a transcript, or auxiliary meeting notes) and
whether it is LEGIBLE. goal.md clause 19 turns on the kind and clause 5 on
legibility, so both are decided here, once.

Deterministic: file reads and string scans. No network, no model call. Where the
bytes physically come from is a BINDING, declared in a map file and passed in;
this module resolves no Drive reference of its own.

Run with --help for the command surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_SEAMS = TOOL_DIR.parent / "seams"
SEAM_ENTRY = "artifact-content"

EXIT_OK = 0
EXIT_VERDICT = 1  # ran fine, the read is not usable
EXIT_REFUSED = 2  # could not run

# One utterance line: "HH:MM:SS Speaker: text". The third and last kind signal,
# used only when nothing named the artifact — see kind_of().
UTTERANCE = re.compile(r"^\s*(\d{1,2}:)?\d{1,2}:\d{2}\s+([^:]{1,60}):\s*(.*)$")
FRONTMATTER_KIND = re.compile(r"^\s*type\s*:\s*[\"']?([a-z-]+)[\"']?\s*$", re.M)

# Frontmatter `type:` values, mapped onto the seam's artifact-kind enum. A value
# outside this map names itself and is not silently read as a transcript.
DECLARED_KIND = {
    "transcript": "transcript",
    "meeting-notes": "meeting-notes",
    "notes": "meeting-notes",
}


def refuse(what: str, fix: str) -> None:
    print(f"artifact-reader refused: {what}\n  fix: {fix}", file=sys.stderr)
    raise SystemExit(EXIT_REFUSED)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        refuse(f"no such file: {path}", "pass a path that exists")
    except (OSError, json.JSONDecodeError) as exc:
        refuse(f"{path} is not readable JSON: {exc}", "fix the file, then re-run")


def utterances(text: str) -> list[dict]:
    """Every utterance line, in order. Continuation lines fold into the previous."""
    out: list[dict] = []
    for line in (text or "").splitlines():
        match = UTTERANCE.match(line)
        if match:
            out.append({"at": line[: line.index(match.group(2))].strip(),
                        "speaker": match.group(2).strip(),
                        "text": match.group(3).strip()})
        elif out and line.strip() and line.startswith((" ", "\t")):
            out[-1]["text"] = (out[-1]["text"] + " " + line.strip()).strip()
    return out


def kind_of(text: str, name: str, markers: dict) -> str:
    """The artifact-kind verdict, by three signals in order of authority.

    1. The artifact DECLARES its type in frontmatter — the pipeline's own files do.
    2. The artifact's display NAME carries a marker the config declares. Notes
       markers are consulted before transcript markers: a notes file named after
       its meeting can carry the meeting's own word for "transcript", never the
       other way round.
    3. The body carries at least one utterance line.
    Nothing matched is `undetermined` — a caller's failure event, never a default
    to transcript, because defaulting is what makes clause 19 breakable.
    """
    declared = FRONTMATTER_KIND.search(text or "")
    if declared:
        mapped = DECLARED_KIND.get(declared.group(1))
        if mapped:
            return mapped
    lowered = (name or "").casefold()
    for kind in ("meeting-notes", "transcript"):
        for marker in markers.get(kind, {}).get("name-contains", []):
            if marker.casefold() in lowered:
                return kind
    return "transcript" if utterances(text) else "undetermined"


# A line that is someone speaking: "<speaker>: <words>", where the speaker holds a
# letter (a bare "00:00:01" clock line is not speech).
SPEECH_LINE = re.compile(r"^(?=[^:\n]*[^\W\d_])[^:\n]{1,60}:\s*\S", re.M)


def split_notes(text: str, headings: list[str]) -> tuple[str, str | None]:
    """A Gemini notes document -> (Gemini's summary, Google Meet's transcript or None).

    Google writes its OWN verbatim transcript into the notes document, under a
    heading such as "📖 Transcrição", whenever Meet transcription was on for the
    meeting (owner ruling r-google-transcript-in-notes, 2026-09-27). That section
    is speech, not a model's summary, so it is split off and returned apart. No
    heading, or a heading with no speech under it, is None: the document is
    Gemini's summary only, exactly as before. The headings are Google's words in
    the account's language, so they are configuration, never typed here.
    """
    lines = (text or "").splitlines(keepends=True)
    wanted = [h.strip() for h in headings if h.strip()]
    for index, line in enumerate(lines):
        if any(line.strip().startswith(heading) for heading in wanted):
            spoken = "".join(lines[index:])
            if SPEECH_LINE.search("".join(lines[index + 1:])):
                return "".join(lines[:index]), spoken
            return text, None
    return text, None


def load_markers(path: Path | None) -> dict:
    """The declared name markers. Absent config means no name signal, never a guess."""
    if path is None:
        return {}
    data = read_json(path)
    return {kind: data.get(kind, {}) for kind in ("meeting-notes", "transcript")}


def read_artifact(ref: str, binding: dict, markers: dict) -> dict:
    """One `read-result`. A binding names where the bytes are and what the source called them."""
    location = binding.get("location")
    if not location:
        refuse(f"the binding for {ref} declares no 'location'",
               "give every artifact binding a 'location'")
    media_type = binding.get("media-type") or "application/octet-stream"
    result = {"kind": "read-result", "ref": ref, "media-type": media_type}
    try:
        raw = Path(location).read_bytes()
    except OSError as exc:
        return {**result, "artifact-kind": "undetermined", "text": "",
                "sha256": hashlib.sha256(b"").hexdigest(), "legible": False,
                "illegible-reason": f"the artifact could not be fetched: {exc}"}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {**result, "artifact-kind": "undetermined", "text": "",
                "sha256": hashlib.sha256(raw).hexdigest(), "legible": False,
                "illegible-reason": f"the bytes are not text: {exc}"}
    return {**result,
            "artifact-kind": kind_of(text, binding.get("name", ""), markers),
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "legible": True}


def validate(result: dict, seams: Path) -> list[str]:
    """Hold a read-result to the seam. A reader that emits off-seam is the defect."""
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - environment, not logic
        refuse(f"the JSON Schema runtime is missing: {exc}", "pip install jsonschema referencing")
    registry = Registry()
    for schema_file in sorted(seams.glob("*.schema.json")):
        registry = registry.with_resource(
            schema_file.name, Resource.from_contents(json.loads(schema_file.read_text("utf-8"))))
    schema = json.loads((seams / f"{SEAM_ENTRY}.schema.json").read_text("utf-8"))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in Draft202012Validator(schema, registry=registry).iter_errors(result)]


def read_map(path: Path) -> dict:
    """The binding table: `artifacts` maps a drive-ref to where its bytes are."""
    data = read_json(path)
    if not isinstance(data.get("artifacts"), dict):
        refuse(f"{path} declares no 'artifacts' object",
               "the map is {'artifacts': {'<drive-ref>': {'location': ..., 'name': ...}}}")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="artifact_reader",
        description="The artifact-content reader protocol: one drive-ref -> one seam-valid "
                    "read-result carrying the decoded text, the artifact-kind verdict and the "
                    "legibility verdict.")
    parser.add_argument("--ref", required=True, help="the drive-ref to read")
    parser.add_argument("--map", required=True, type=Path,
                        help="binding table: {'artifacts': {'<drive-ref>': {...}}}")
    parser.add_argument("--kinds", type=Path,
                        help="artifact-kinds config declaring the display-name markers")
    parser.add_argument("--seams", type=Path, default=DEFAULT_SEAMS,
                        help="seam set the result is held to (default: ../seams beside this tool)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    bindings = read_map(args.map)["artifacts"]
    if args.ref not in bindings:
        refuse(f"the map carries no binding for {args.ref}",
               "add the artifact to the map, or pass a ref the map declares")
    result = read_artifact(args.ref, bindings[args.ref], load_markers(args.kinds))
    problems = validate(result, args.seams)
    print(json.dumps({"result": result, "problems": problems, "ok": not problems},
                     ensure_ascii=False, indent=2))
    return EXIT_OK if not problems and result["legible"] else EXIT_VERDICT


if __name__ == "__main__":
    raise SystemExit(main())
