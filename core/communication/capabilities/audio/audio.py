#!/usr/bin/env python3
"""audio — ElevenLabs speech-to-text and text-to-speech for this workspace.

Three verbs, JSON on stdout, and one language key both of the first two read.
The command inventory lives in the parser below and nowhere else: `--help` and
`<verb> --help` are the documentation (README.md points here rather than
restating flags, which is how a second copy goes stale).

Never PyYAML: the workspace's private-scope floor masks `yaml/tokens.py`, which
bricks the import inside every cage. Config is JSON, read with the stdlib.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.json"


def _key_file():
    # The workspace key store: <workspace>/.user/config/env/elevenlabs.key, the
    # workspace found by walking up to the directory holding `.rbtv/`. Owner ruling
    # 2026-08-23 (supersedes `d-elevenlabs-key-location-2026-08-18` for this
    # workspace): the component now lives inside the rbtv REPO tree, and a secret
    # must never sit where a repo push can carry it — so the key moved out to the
    # workspace's own key store. None when no workspace root is found (the env
    # var is then the only source).
    for p in ROOT.parents:
        if (p / ".rbtv").is_dir():
            return p / ".user" / "config" / "env" / "elevenlabs.key"
    return None


KEY_FILE = _key_file()
KEY_ENV = "ELEVENLABS_API_KEY"

# The ONE home of a language value in this file (goal.md clause 11). Every other
# mention interpolates this constant — a literal language code anywhere else in
# this source is a defect, and `grep` for one is a done-contract criterion.
LANGUAGE_KEY = "language"
DEFAULT_LANGUAGE = "pt"
# ISO-639-1 (2 letters) or ISO-639-3 (3 letters) — the two forms the API accepts
# (openapi.json, `language_code`: "An ISO-639-1 or ISO-639-3 language_code").
# A SHAPE, not a value: it names no language.
LANGUAGE_RE = re.compile(r"[a-z]{2,3}\Z")

# ── The API, as sourced 2026-08-18 from api.elevenlabs.io/openapi.json and the
#    docs beside it (provenance: the seat's scratchpad/probes/elevenlabs-*).
API = "https://api.elevenlabs.io"
STT_URL = f"{API}/v1/speech-to-text"
STT_MODEL = "scribe_v2"           # scribe_v1 is deprecated (docs/overview/models)
AUTH_HEADER = "xi-api-key"        # raw key, no Bearer

TTS_URL = f"{API}/v1/text-to-speech"      # + /<voice_id>
VOICES_URL = f"{API}/v2/voices"
# The default TTS model is the flash one and NOT `eleven_multilingual_v2`,
# which the docs recommend for quality — because `language_code` "is not
# supported for multilingual_v2 models" (docs/api-reference/text-to-speech/
# convert), and a default under which the config key could not reach TTS would
# defeat the key's whole purpose (goal.md clauses 11-12). flash_v2_5 covers
# "all eleven_multilingual_v2 languages plus hu, no, vi" (docs/models), so it
# is pt-capable. A caller who wants the higher-fidelity model passes
# `--model eleven_multilingual_v2` and the language rides in the text instead.
TTS_MODEL = "eleven_flash_v2_5"
MULTILINGUAL_V2 = "multilingual_v2"       # the family that takes no language_code
# The output format is the --out extension's, so one file name cannot disagree
# with a --format flag. ElevenLabs spells ogg's codec `opus_*`, never `ogg_*`;
# the container it arrives in is undocumented, so `.ogg` is what this CLI calls
# it and sniffing `OggS` is the caller's check if it matters.
OUTPUT_FORMATS = {".mp3": "mp3_44100_128", ".ogg": "opus_48000_128",
                  ".opus": "opus_48000_128"}

EXIT_REFUSED = 2                  # local refusal: usage, missing key, bad input
EXIT_FAILED = 1                   # the remote call failed, or returned nothing usable


def die(what, why, fix, code=EXIT_REFUSED):
    """Every refusal teaches: what was refused, why, and the exact fix.

    stderr only, never a traceback, never the key. The caller reads stdout for
    JSON and stderr for this."""
    print(f"audio: {what}", file=sys.stderr)
    print(f"  why: {why}", file=sys.stderr)
    print(f"  fix: {fix}", file=sys.stderr)
    sys.exit(code)


def emit(**payload):
    """The machine-readable half: one JSON object on stdout, nothing else."""
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


# ────────────────────────────────────────────────────────────── key and config

def api_key():
    """The workspace key store FIRST (`_key_file` above — outside the repo tree,
    owner ruling 2026-08-23); the env var when it holds nothing.
    `ELEVENLABS_API_KEY` stays accepted as the override — inside a cage the key
    store is masked, so the env var is a caged seat's route.

    Returns (key, source). Refuses naming BOTH places when neither has one."""
    if KEY_FILE and KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key, "key-file"
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key, "env"
    die("no ElevenLabs API key",
        f"{KEY_FILE} holds no key and {KEY_ENV} is unset or empty — "
        "every verb of this CLI calls the ElevenLabs API",
        f"put the key in {KEY_FILE} (one line, the key itself, no trailing "
        f"newline needed), or export {KEY_ENV}; see {ROOT / 'README.md'} "
        "section 'The key'")


def config_read():
    """The config as a dict. A missing file is not an error — the default is the
    default. A corrupt one IS an error: silently falling back would hide a
    language the caller believes they set."""
    if not CONFIG.is_file():
        return {LANGUAGE_KEY: DEFAULT_LANGUAGE}
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        die(f"{CONFIG} is not readable JSON", str(exc),
            f'rewrite it as {{"{LANGUAGE_KEY}": "{DEFAULT_LANGUAGE}"}}, or delete '
            "it to fall back to that default")
    if not isinstance(data, dict):
        die(f"{CONFIG} is not a JSON object",
            f"read a {type(data).__name__} where the config must be an object",
            f'rewrite it as {{"{LANGUAGE_KEY}": "{DEFAULT_LANGUAGE}"}}')
    return data


def language():
    """The one language both transcribe and tts run in."""
    value = config_read().get(LANGUAGE_KEY) or DEFAULT_LANGUAGE
    return str(value)


def language_write(code):
    """Rewrite the language key IN PLACE — deliberately not a temp-file-plus-
    rename. The exposure manifest binds this FILE (not its directory) read-write
    into a seat's cage, so an atomic writer's sibling temp file meets EROFS on a
    read-only parent. Truncate-and-write is what actually lands there."""
    data = config_read()
    data[LANGUAGE_KEY] = code
    body = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with CONFIG.open("w", encoding="utf-8") as fh:
            fh.write(body)
    except OSError as exc:
        die(f"cannot write {CONFIG}", str(exc),
            "the config file must be writable — inside a cage that means the "
            "exposure row's `write-roots` cell must carry it, marked `!`")


# ─────────────────────────────────────────────────────────────── the API layer

def call(method, url, key, **kw):
    """One HTTP call, with every failure turned into a taught refusal.

    The response body is quoted on failure because ElevenLabs names the cause in
    it (`detail.message`); the key never is."""
    headers = {AUTH_HEADER: key}
    try:
        response = requests.request(method, url, headers=headers,
                                    timeout=kw.pop("timeout", 300), **kw)
    except requests.RequestException as exc:
        die("the ElevenLabs API call failed", f"{type(exc).__name__}: {exc}",
            "check network reachability, then retry", code=EXIT_FAILED)
    if response.status_code >= 400:
        die(f"ElevenLabs refused the request (HTTP {response.status_code})",
            api_error(response),
            "401 means the key is invalid or revoked — check the key in "
            f"{KEY_FILE}; 4xx otherwise means the request was; 5xx means retry",
            code=EXIT_FAILED)
    return response


def api_error(response):
    """The cause, out of either `detail` shape ElevenLabs uses: an object on the
    documented error pages, an array of validation items on a 422. Parsing only
    one of them crashes on the other."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        return (response.text or "").strip()[:400] or "(empty response body)"
    if isinstance(detail, dict):
        return " ".join(str(detail.get(f)) for f in ("code", "message")
                        if detail.get(f)) or json.dumps(detail)[:400]
    if isinstance(detail, list):
        return "; ".join(str(item.get("msg", item)) for item in detail)[:400]
    return json.dumps(detail)[:400] if detail else response.text[:400]


# ───────────────────────────────────────────────────────────────────── the verbs

def cmd_transcribe(args):
    source = Path(args.file)
    # The input is validated BEFORE the key on purpose: an unreadable file is
    # the caller's own mistake and naming it costs no round trip — and it keeps
    # this arm provable on a machine that has no key at all.
    if not source.is_file():
        die(f"cannot read {source}",
            "no such file, or it is a directory" if not source.exists()
            else "it is not a regular file",
            "pass the path of an audio file — `stools download` is what puts a "
            "Slack voice note on disk")
    try:
        with source.open("rb"):
            pass
    except OSError as exc:
        die(f"cannot read {source}", str(exc),
            "fix the permissions, or pass a file this process can read")
    if source.stat().st_size == 0:
        die(f"{source} is empty", "a 0-byte file carries no audio "
            "(the API's own minimum is 100ms)",
            "check the download that produced it")

    key, source_of_key = api_key()
    lang = language()
    with source.open("rb") as fh:
        response = call("POST", STT_URL, key,
                        files={"file": (source.name, fh)},
                        data={"model_id": args.model, "language_code": lang},
                        timeout=args.timeout)
    try:
        body = response.json()
    except ValueError:
        die("the ElevenLabs response was not JSON",
            (response.text or "")[:400] or "(empty body)",
            "retry; if it repeats, the API contract has moved and this CLI "
            "needs re-sourcing", code=EXIT_FAILED)
    text = (body.get("text") or "").strip()
    if not text:
        # Clause 10's silence arm. Never exit 0 with an empty transcript: a
        # caller that pipes this into a prompt would act on nothing.
        die(f"{source} produced an empty transcript",
            "the API returned no speech — a silent, near-silent or "
            "speech-free recording",
            "check the recording is audible, then retry", code=EXIT_FAILED)
    emit(text=text, language=body.get("language_code") or lang,
         language_requested=lang, model_id=args.model, source=str(source),
         key_source=source_of_key, chars=len(text),
         next=f"pipe .text where it is needed; `{Path(__file__).name} "
              "language` shows the language this ran in")


def cmd_language(args):
    # This verb touches no network — and still demands the key, because the
    # contract this component is built to says EVERY verb refuses without one
    # (goal.md clause 9: "qualquer verbo sai exit != 0"; m2 probe (e) runs the
    # absence arm over every verb). Deliberate, not incidental: a caller who
    # switches the language of an integration that cannot run is being told the
    # integration cannot run. Reading the language of a keyless install is done
    # by reading config.json, which is one JSON object.
    _, source_of_key = api_key()
    current = language()
    if args.code is None:
        emit(**{LANGUAGE_KEY: current, "config": str(CONFIG),
                "default": DEFAULT_LANGUAGE, "key_source": source_of_key,
                "next": f"{Path(__file__).name} language <code> changes it for "
                        "BOTH transcribe and tts"})
        return
    code = args.code.strip().lower()
    if not LANGUAGE_RE.match(code):
        die(f"'{args.code}' is not a language code",
            "the ElevenLabs API takes ISO-639-1 (2 letters) or ISO-639-3 "
            "(3 letters), lowercase — a region subtag is not accepted here",
            "pass a 2- or 3-letter code")
    language_write(code)
    written = language()
    if written != code:
        die(f"{CONFIG} did not take the new value",
            f"wrote '{code}', read back '{written}'",
            "check the file is writable and not being rewritten by something "
            "else", code=EXIT_FAILED)
    emit(**{LANGUAGE_KEY: code, "previous": current, "config": str(CONFIG),
            "changed": code != current, "key_source": source_of_key,
            "next": "both transcribe and tts now run in it — no other flag or "
                    "file pins a language"})


def cmd_tts(args):
    text = read_text(args)
    out = Path(args.out)
    fmt = OUTPUT_FORMATS.get(out.suffix.lower())
    if fmt is None:
        die(f"cannot tell an audio format from '{out.name}'",
            f"the extension '{out.suffix or '(none)'}' is not one this CLI maps "
            "to an ElevenLabs output format",
            f"name the output file with one of: "
            f"{', '.join(sorted(OUTPUT_FORMATS))}")
    if not out.parent.is_dir():
        die(f"cannot write {out}", f"{out.parent} is not a directory",
            "pass --out under a directory that exists")

    key, source_of_key = api_key()
    voice = args.voice or first_voice(key)
    lang = language()
    body = {"text": text, "model_id": args.model}
    # Sourced 2026-08-18 (docs/api-reference/text-to-speech/convert): language_code
    # "is not supported for multilingual_v2 models" — and the docs contradict
    # themselves about whether an unsupported code is ignored or refused, so the
    # one model family documented as not taking it is not sent it. Every other
    # model gets the config's language, which is the whole point of the key.
    if MULTILINGUAL_V2 not in args.model:
        body["language_code"] = lang
    response = call("POST", f"{TTS_URL}/{voice}", key,
                    params={"output_format": fmt},
                    json=body, timeout=args.timeout)
    audio = response.content
    if not audio:
        die("ElevenLabs returned no audio",
            "HTTP 200 with an empty body — nothing to write",
            "retry; if it repeats, check the account's quota and the voice id",
            code=EXIT_FAILED)
    try:
        out.write_bytes(audio)
    except OSError as exc:
        die(f"cannot write {out}", str(exc),
            "pass --out somewhere this process can write")
    emit(path=str(out.resolve()), bytes=len(audio), output_format=fmt,
         voice_id=voice, voice_source="flag" if args.voice else "account",
         model_id=args.model, language=lang if MULTILINGUAL_V2 not in args.model
         else "(carried by the text — this model takes no language code)",
         key_source=source_of_key, chars=len(text),
         next=f"`stools upload` puts {out.name} in a Slack channel")


def read_text(args):
    """The text to speak — inline, from a file, or from stdin.

    A --file/- path exists because the shell mangles inline text carrying
    backticks, quotes or $(...) before this CLI ever sees it, and because the
    text this tool is given is prose in the owner's language, not a token."""
    if args.file is not None:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            path = Path(args.file)
            if not path.is_file():
                die(f"cannot read {path}", "no such file, or it is a directory",
                    "pass --file with a readable text file, or --file - to read "
                    "stdin")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                die(f"cannot read {path}", str(exc),
                    "the file must be readable UTF-8 text")
    else:
        text = args.text
    text = (text or "").strip()
    if not text:
        die("no text to speak",
            "the text is empty after stripping whitespace",
            "pass --text \"...\", or --file PATH, or pipe into --file -")
    return text


def first_voice(key):
    """A voice id from the account itself.

    Deliberately NOT a compiled-in default. ElevenLabs' own default voices
    ("George", `JBFqnCBsd6RMkjVDRZzb`, the id in every docs example) expire
    2026-12-31 and are unavailable to accounts created after March 2026
    (docs/help-center/product/voices/my-voices/what-are-default-voices) — a
    hardcoded id would ship broken for exactly the account this component is
    being provisioned for. The vendor's own instruction is to resolve it from
    the List voices endpoint, which is what this does."""
    response = call("GET", VOICES_URL, key, timeout=60)
    try:
        voices = response.json().get("voices") or []
    except ValueError:
        voices = []
    for voice in voices:
        if voice.get("voice_id"):
            return voice["voice_id"]
    die("this ElevenLabs account exposes no voice",
        f"GET {VOICES_URL} returned no voice carrying a voice_id",
        "add a voice to the account, or pass --voice <id> explicitly",
        code=EXIT_FAILED)


# ──────────────────────────────────────────────────────────────────── the parser

def build_parser():
    parser = argparse.ArgumentParser(
        prog=Path(__file__).name, description=__doc__.splitlines()[0],
        epilog=f"key: {KEY_FILE} first, ${KEY_ENV} when it holds nothing.\n"
               f"language: the '{LANGUAGE_KEY}' key of {CONFIG.name} "
               f"(default '{DEFAULT_LANGUAGE}') — the language verb changes it "
               "for both other verbs.\nevery verb prints one JSON object on "
               "stdout; refusals go to stderr and exit non-zero.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")

    transcribe = verbs.add_parser(
        "transcribe", help="an audio file -> its text",
        description="Transcribe an audio file through ElevenLabs Scribe and "
                    "print the text as JSON.\nThe language is the config's, not "
                    "a flag. `stools download` is what puts a Slack voice note "
                    "on disk.",
        epilog=f"example:\n  %(prog)s ./voice-note.m4a\n\n"
               "next: read .text from the JSON; a silent or speech-free "
               "recording exits non-zero rather than printing an empty "
               "transcript.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    transcribe.add_argument("file", help="path to the audio file to transcribe")
    transcribe.add_argument("--model", default=STT_MODEL, metavar="ID",
                            help=f"ElevenLabs STT model (default: {STT_MODEL})")
    transcribe.add_argument("--timeout", type=float, default=300, metavar="SEC",
                            help="HTTP timeout in seconds (default: 300)")
    transcribe.set_defaults(run=cmd_transcribe)

    tts = verbs.add_parser(
        "tts", help="text -> a playable audio file",
        description="Synthesize speech through ElevenLabs and write it to "
                    "--out.\nThe output format follows the --out extension; the "
                    "language is the config's, not a flag; the voice comes from "
                    "the account unless --voice pins one.",
        epilog="example:\n  %(prog)s --text \"...\" --out ./answer.mp3\n\n"
               "next: `stools upload` posts the file to a Slack channel.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    source = tts.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", metavar="TEXT",
                        help="the text to speak (the shell mangles backticks, "
                             "quotes and $(...) — prefer --file for prose)")
    source.add_argument("--file", metavar="PATH",
                        help="read the text from a file, or from stdin with -")
    tts.add_argument("--out", required=True, metavar="PATH",
                     help="where to write the audio; the extension picks the "
                          f"format ({', '.join(sorted(OUTPUT_FORMATS))})")
    tts.add_argument("--voice", metavar="ID",
                     help="voice id (default: the account's first voice — this "
                          "CLI compiles none in, the vendor's own default "
                          "voices expire)")
    tts.add_argument("--model", default=TTS_MODEL, metavar="ID",
                     help=f"ElevenLabs TTS model (default: {TTS_MODEL})")
    tts.add_argument("--timeout", type=float, default=300, metavar="SEC",
                     help="HTTP timeout in seconds (default: 300)")
    tts.set_defaults(run=cmd_tts)

    lang = verbs.add_parser(
        "language", help=f"read or rewrite the one {LANGUAGE_KEY} key",
        description=f"Print the {LANGUAGE_KEY} both other verbs run in, or "
                    "rewrite it.\nIt is the ONLY place a language is set for "
                    "this component's whole ElevenLabs integration.",
        epilog="example:\n  %(prog)s            (read)\n"
               "  %(prog)s <code>     (rewrite: ISO-639-1 or ISO-639-3)\n\n"
               "next: the change is immediate and persists — the next "
               "transcribe or tts reads it from the config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    lang.add_argument("code", nargs="?",
                      help="a 2- or 3-letter language code; omit to read")
    lang.set_defaults(run=cmd_language)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
