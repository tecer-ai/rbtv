#!/usr/bin/env python3
"""elevenlabs — ElevenLabs speech-to-text and text-to-speech for this workspace.

Four verbs, JSON on stdout, and one language key both transcribe and tts read.
The command inventory lives in the parser below and nowhere else: `--help` and
`<verb> --help` are the documentation (elevenlabs.md, the tool's one page,
points here rather than restating flags, which is how a second copy goes stale).

The language the verbs run in is the INSTALLATION's, never this source tree's:
a value written into the source would leak into every installation and be
rewritten by the next pull. Config is JSON, read with the standard library.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent

PROG = "elevenlabs"                 # the command name on PATH once installed

INSTALL_RECORD_REL = Path(".rbtv") / "config" / "install.json"
ENV_FILE_REL = Path(".rbtv") / "config" / "env" / ".env"
CONFIG_REL = Path(".rbtv") / "config" / "elevenlabs" / "config.json"


def _install_file(rel, start=None):
    # A file of the installation. The installation is the first folder, from
    # the working folder upward, that holds the installer's record
    # `.rbtv/config/install.json`. None when the working folder is inside no
    # installation (the process environment is then the only key source, and
    # the language is the default — a persistent write is refused).
    folder = Path(start or Path.cwd()).resolve()
    for p in (folder, *folder.parents):
        if (p / INSTALL_RECORD_REL).is_file():
            return p / rel
    return None


ENV_FILE = _install_file(ENV_FILE_REL)
CONFIG = _install_file(CONFIG_REL)
KEY_ENV = "ELEVENLABS_API_KEY"
API_URL_ENV = "ELEVENLABS_API_URL"  # off-network test hook; overrides the base

# The one home of a language value in this file. Every other
# mention interpolates this constant — a literal language code anywhere else in
# this source is a defect, and `grep` for one is a done-contract criterion.
LANGUAGE_KEY = "language"
DEFAULT_LANGUAGE = "pt"
# ISO-639-1 (2 letters) or ISO-639-3 (3 letters) — the two forms the API accepts
# (openapi.json, `language_code`: "An ISO-639-1 or ISO-639-3 language_code").
# A SHAPE, not a value: it names no language.
LANGUAGE_RE = re.compile(r"[a-z]{2,3}\Z")

# Provider endpoints and default models.
API = os.environ.get(API_URL_ENV, "https://api.elevenlabs.io").rstrip("/")
STT_URL = f"{API}/v1/speech-to-text"
STT_MODEL = "scribe_v2"
AUTH_HEADER = "xi-api-key"        # raw key, no Bearer

TTS_URL = f"{API}/v1/text-to-speech"      # + /<voice_id>
VOICES_URL = f"{API}/v2/voices"
# The default TTS model is the flash one and NOT `eleven_multilingual_v2`,
# which the docs recommend for quality — because `language_code` "is not
# supported for multilingual_v2 models" (docs/api-reference/text-to-speech/
# convert), and a default under which the config key could not reach TTS would
# defeat the key's whole purpose. flash_v2_5 covers
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
    print(f"{PROG}: {what}", file=sys.stderr)
    print(f"  why: {why}", file=sys.stderr)
    print(f"  fix: {fix}", file=sys.stderr)
    sys.exit(code)


def emit(**payload):
    """The machine-readable half: one JSON object on stdout, nothing else."""
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


# ────────────────────────────────────────────────────────────── key and config

def api_key(required=True):
    """The process environment FIRST (`$ELEVENLABS_API_KEY` — the workspace's
    root rule: scripts read the OS variable before any file), then the
    installation's environment file (`.rbtv/config/env/.env`, owner-ruled
    2026-09-27), its `ELEVENLABS_API_KEY` line.

    Returns (key, source); (None, None) when none is configured and
    `required` is False — help and the language verb run keyless. Refuses
    naming BOTH places when neither has one."""
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key, "env"
    if ENV_FILE and ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?" + KEY_ENV + r"\s*=\s*(.*)$", line)
            if m:
                key = m.group(1).strip().strip("'\"")
                if key:
                    return key, "env-file"
    if required:
        no_key_refusal()
    return None, None


def no_key_refusal():
    if ENV_FILE is not None:
        why = (f"${KEY_ENV} is unset or empty, and {ENV_FILE} holds no {KEY_ENV} "
               "line — transcribe, tts and voices call the ElevenLabs API")
        fix = (f"export {KEY_ENV}=<key>, or add a line {KEY_ENV}=<key> to {ENV_FILE}")
    else:
        why = (f"${KEY_ENV} is unset or empty, and this folder is inside no rbtv "
               f"installation (no folder above it holds {INSTALL_RECORD_REL.as_posix()}), "
               "so there is no environment file to fall back to — transcribe, tts and "
               "voices call the ElevenLabs API")
        fix = (f"export {KEY_ENV}=<key>, or run from a folder inside the installation "
               f"whose {ENV_FILE_REL.as_posix()} holds a line {KEY_ENV}=<key>")
    die("no ElevenLabs API key", why,
        f"{fix}; the language verb and --help need no key")


def key_sources():
    """Where `api_key` reads the key, in its order, as words for help and
    refusals. Outside an installation there is no environment file to name."""
    if ENV_FILE is None:
        return f"${KEY_ENV} (the process environment; this folder is inside no rbtv installation)"
    return f"${KEY_ENV} first, {KEY_ENV} in {ENV_FILE} when the environment holds none"


def config_read():
    """The installation's config as a dict. No installation, or a missing file,
    is not an error — the default is the default. A corrupt file IS an error:
    silently falling back would hide a language the caller believes they set."""
    if CONFIG is None or not CONFIG.is_file():
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
    """Update the language key in the INSTALLATION's config — never this
    source tree's, which the next pull would overwrite into every install."""
    if CONFIG is None:
        die("cannot persist the language",
            f"no folder above {Path.cwd()} holds {INSTALL_RECORD_REL.as_posix()} — "
            "the live language config belongs to the installation, and this "
            "folder is inside none",
            "run this from a folder inside the installation, or edit its "
            f"{CONFIG_REL.as_posix()} by hand")
    data = config_read()
    data[LANGUAGE_KEY] = code
    body = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG.open("w", encoding="utf-8") as fh:
            fh.write(body)
    except OSError as exc:
        die(f"cannot write {CONFIG}", str(exc),
            "check that the config file and its directory are writable")


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
            "401 means the key is invalid or revoked — check the key: "
            f"{key_sources()}; 4xx otherwise means the request was; 5xx means retry",
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
            "pass the path of an audio file — `slack download` is what puts a "
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
        # Never exit 0 with an empty transcript: a caller that pipes this into
        # a prompt would act on nothing.
        die(f"{source} produced an empty transcript",
            "the API returned no speech — a silent, near-silent or "
            "speech-free recording",
            "check the recording is audible, then retry", code=EXIT_FAILED)
    emit(text=text, language=body.get("language_code") or lang,
         language_requested=lang, model_id=args.model, source=str(source),
         key_source=source_of_key, chars=len(text),
         next=f"pipe .text where it is needed — dictated text carries "
              "self-corrections and mangled names, so apply the workspace "
              f"glossary before acting on it; `{PROG} language` shows the "
              "language this ran in")


def cmd_language(args):
    # This verb touches no network and needs no key: reading or rewriting a
    # local JSON value is not an API operation.
    source_of_key = None
    current = language()
    if args.code is None:
        emit(**{LANGUAGE_KEY: current, "config": str(CONFIG) if CONFIG else None,
                "default": DEFAULT_LANGUAGE, "key_source": source_of_key,
                "next": f"{PROG} language <code> changes it for BOTH "
                        "transcribe and tts"})
        return
    code = args.code.strip().lower()
    if not LANGUAGE_RE.match(code):
        die(f"'{args.code}' is not a language code",
            "the ElevenLabs API takes ISO-639-1 (2 letters) or ISO-639-3 "
            "(3 letters); uppercase is normalized, but a region subtag is refused "
            "here, before anything is written",
            "pass a 2- or 3-letter lowercase code")
    language_write(code)
    written = language()
    if written != code:
        die(f"{CONFIG} did not take the new value",
            f"wrote '{code}', read back '{written}'",
            "check the file is writable and not being rewritten by something "
            "else", code=EXIT_FAILED)
    emit(**{LANGUAGE_KEY: code, "previous": current,
            "config": str(CONFIG) if CONFIG else None,
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
            "to an ElevenLabs output format — an unsupported extension is "
            "refused before any request is made",
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
         next=f"write for the ear, not for the eye — speak outcomes and "
              "reasoning, and leave paths, ids and copyable tokens in the "
              f"accompanying text; `slack upload` puts {out.name} in a Slack "
              "channel")


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


def account_voices(key, timeout=60, page_token=None):
    """Return one provider page, preserving its continuation information."""
    params = {"page_size": 100}
    if page_token:
        params["next_page_token"] = page_token
    response = call("GET", VOICES_URL, key, timeout=timeout, params=params)
    try:
        page = response.json()
    except ValueError:
        die("the ElevenLabs response was not JSON",
            "the voices listing came back unreadable",
            "retry; if it repeats, the API contract has moved and this CLI "
            "needs re-sourcing", code=EXIT_FAILED)
    return page


def voice_row(voice):
    """The fields that make a voice choosable: what --voice takes, what it is
    called, and the language it speaks."""
    return {"voice_id": voice.get("voice_id"),
            "name": voice.get("name") or "",
            "language": voice.get("language") or "",
            "description": (voice.get("description") or "").strip()}


def first_voice(key):
    """Resolve the default from the account instead of hardcoding a voice id."""
    for voice in account_voices(key).get("voices", []):
        if voice.get("voice_id"):
            return voice["voice_id"]
    die("this ElevenLabs account exposes no voice",
        f"GET {VOICES_URL} returned no voice carrying a voice_id",
        "add a voice to the account, or pass --voice <id> explicitly",
        code=EXIT_FAILED)


def cmd_voices(args):
    key, source_of_key = api_key()
    page = account_voices(key, timeout=args.timeout, page_token=args.page_token)
    rows = [voice_row(v) for v in page.get("voices", [])
            if v.get("voice_id")]
    emit(voices=rows, count=len(rows), key_source=source_of_key,
         has_more=bool(page.get("has_more")), next_page_token=page.get("next_page_token"),
         next=(f"pass next_page_token to `{PROG} voices --page-token TOKEN`"
               if page.get("has_more") else
               f"copy a voice_id into `{PROG} tts --voice <id>`" if rows else
               "No voices found; add a voice in the ElevenLabs dashboard."))


# ──────────────────────────────────────────────────────────────────── the parser

def build_parser():
    parser = argparse.ArgumentParser(
        prog=PROG, description=__doc__.splitlines()[0],
        epilog=f"key: {key_sources()} — no key is needed for --help or the "
               f"language verb.\n"
               f"language: the '{LANGUAGE_KEY}' key of the installation's "
               f"{CONFIG_REL.as_posix()} (default '{DEFAULT_LANGUAGE}') — the "
               "language verb changes it for transcribe and tts.\n"
               "every verb prints one JSON object on stdout; refusals go to "
               "stderr and exit non-zero.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")

    transcribe = verbs.add_parser(
        "transcribe", help="an audio file -> its text",
        description="Transcribe an audio file through ElevenLabs Scribe and "
                    "print the text as JSON.\nThe language is the config's, not "
                    "a flag. `slack download` is what puts a Slack voice note "
                    "on disk.",
        epilog=f"example:\n  {PROG} transcribe ./voice-note.m4a\n\n"
               "next: read .text from the JSON — it is dictated text carrying "
               "self-corrections and mangled names, so apply the workspace "
               "glossary before acting on it; a silent or speech-free recording "
               "exits non-zero rather than printing an empty transcript.",
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
        epilog=f"example:\n  {PROG} tts --text \"...\" --out ./answer.mp3\n\n"
               "next: write for the ear, not for the eye — speak outcomes and "
               "reasoning, leave paths, ids and copyable tokens in the "
               "accompanying text. `slack upload` posts the file to a Slack "
               "channel.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    source = tts.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", metavar="TEXT",
                        help="the text to speak (the shell mangles backticks, "
                             "quotes and $(...) — prefer --file for prose)")
    source.add_argument("--file", metavar="PATH",
                        help="read the text from a file, or from stdin with -")
    tts.add_argument("--out", required=True, metavar="PATH",
                     help="where to write the audio; the extension picks the "
                          f"format ({', '.join(sorted(OUTPUT_FORMATS))}) — an "
                          "unsupported extension is refused before any request")
    tts.add_argument("--voice", metavar="ID",
                     help=f"voice id — `{PROG} voices` lists the account's "
                          "(default: the account's first voice — this CLI "
                          "compiles none in, the vendor's own default voices "
                          "expire)")
    tts.add_argument("--model", default=TTS_MODEL, metavar="ID",
                     help=f"ElevenLabs TTS model (default: {TTS_MODEL})")
    tts.add_argument("--timeout", type=float, default=300, metavar="SEC",
                     help="HTTP timeout in seconds (default: 300)")
    tts.set_defaults(run=cmd_tts)

    voices = verbs.add_parser(
        "voices", help="list the account's voices, with their ids",
        description="List the account's voices from ElevenLabs: voice_id, "
                    "name, language and description — the ids the tts verb's "
                    "--voice takes.",
        epilog=f"example:\n  {PROG} voices\n\n"
               f"next: copy a voice_id into `{PROG} tts --voice <id>`; pick a "
               "voice whose language matches the one the language verb holds.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    voices.add_argument("--timeout", type=float, default=60, metavar="SEC",
                        help="HTTP timeout in seconds (default: 60)")
    voices.add_argument("--page-token", help="Continue from next_page_token in the previous JSON result; up to 100 voices per page (the first page may include additional default voices)")
    voices.set_defaults(run=cmd_voices)

    lang = verbs.add_parser(
        "language", help=f"read or rewrite the one {LANGUAGE_KEY} key",
        description=f"Print the {LANGUAGE_KEY} transcribe and tts run in, or "
                    "rewrite it.\nIt is the ONLY place a language is set for "
                    "this component's whole ElevenLabs integration, it lives "
                    "in the installation's config, and this verb needs no API "
                    "key.",
        epilog=f"example:\n  {PROG} language            (read)\n"
               f"  {PROG} language <code>     (rewrite)\n\n"
               "code: a 2-letter (ISO-639-1) or 3-letter (ISO-639-3) lowercase "
               "code — anything else is refused before anything is written.\n"
               "next: the change is immediate and persists — the next "
               "transcribe or tts reads it from the installation's config. "
               "Outside an installation this reads the default and refuses "
               "to write.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    lang.add_argument("code", nargs="?",
                      help="a 2- or 3-letter lowercase language code; omit to "
                           "read")
    lang.set_defaults(run=cmd_language)
    return parser


def main(argv=None):
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    verbs = next(action.choices for action in parser._actions
                 if isinstance(action, argparse._SubParsersAction))
    if len(argv) > 1 and argv[0] in ("-h", "--help") and argv[1] in verbs:
        argv = [argv[1], argv[0], *argv[2:]]
    args = parser.parse_args(argv)
    args.run(args)


if __name__ == "__main__":
    main()
