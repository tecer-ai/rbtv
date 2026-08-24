#!/usr/bin/env python3
"""The checks for audio.py — `python3 test_audio.py`, no framework, no network.

Every arm this file asserts is one the CLI's own live probes cannot reach
without an ElevenLabs key: the 401, the silent recording, the two shapes of
`detail`, and whether `language_code` is sent for a given model. The arms that
ARE reachable keyless (missing key, unreadable input, the language round trip)
are proven by running the CLI itself and are not restated here.

The HTTP layer is replaced wholesale — `audio.requests` becomes a stub whose
`request()` signature and return type match the real one, and which RAISES on
any URL a test did not declare. A stub that quietly answered an undeclared call
is how a suite goes green over a live request.
"""

import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("audio_cli", HERE / "audio.py")
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class Response:
    """Matches what `requests` hands back at the two attributes call() reads."""

    def __init__(self, status_code=200, body=None, content=b"", text=None):
        self.status_code = status_code
        self._body = body
        self.content = content
        self.text = text if text is not None else (
            json.dumps(body) if body is not None else "")

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body


class Stub:
    """Stands in for the `requests` module inside audio.py."""

    RequestException = Exception

    def __init__(self, routes):
        self.routes = routes          # (method, url-suffix) -> Response
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        for (want_method, suffix), response in self.routes.items():
            if method == want_method and url.endswith(suffix):
                return response
        raise AssertionError(f"undeclared call: {method} {url}")


def run(argv, routes, key="test-key"):
    """Run the CLI in-process. Returns (exit_code, stdout, stderr, stub)."""
    stub, real = Stub(routes), audio.requests
    audio.requests = stub
    out, err, code = io.StringIO(), io.StringIO(), 0
    keyfile = audio.KEY_FILE
    audio.KEY_FILE = Path(tempfile.gettempdir()) / "no-such-key-file"
    import os
    previous = os.environ.get(audio.KEY_ENV)
    os.environ[audio.KEY_ENV] = key
    try:
        with redirect_stdout(out), redirect_stderr(err):
            audio.main(argv)
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        audio.requests, audio.KEY_FILE = real, keyfile
        if previous is None:
            os.environ.pop(audio.KEY_ENV, None)
        else:
            os.environ[audio.KEY_ENV] = previous
    return code, out.getvalue(), err.getvalue(), stub


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def transcribe_returns_the_text():
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")
    code, out, _, stub = run(
        ["transcribe", str(src)],
        {("POST", "/v1/speech-to-text"):
         Response(body={"text": " ola ", "language_code": "por"})})
    assert code == 0, code
    body = json.loads(out)
    assert body["text"] == "ola", body
    assert body["model_id"] == audio.STT_MODEL, body
    sent = stub.calls[0]["data"]
    assert sent["model_id"] == audio.STT_MODEL, sent
    # the language reaching the API is the config's, never a literal
    assert sent["language_code"] == audio.language(), sent


@check
def a_silent_recording_is_a_failure_not_an_empty_success():
    src = Path(tempfile.mkdtemp()) / "silence.mp3"
    src.write_bytes(b"bytes")
    code, out, err, _ = run(
        ["transcribe", str(src)],
        {("POST", "/v1/speech-to-text"): Response(body={"text": "   "})})
    assert code == audio.EXIT_FAILED, code
    assert out == "", out               # never a JSON object with empty text
    assert "empty transcript" in err, err
    assert "Traceback" not in err, err


@check
def an_invalid_key_names_the_cause():
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")
    code, out, err, _ = run(
        ["transcribe", str(src)],
        {("POST", "/v1/speech-to-text"): Response(
            status_code=401,
            body={"detail": {"type": "authentication_error",
                             "code": "invalid_api_key",
                             "message": "The provided API key is invalid."}})})
    assert code == audio.EXIT_FAILED, code
    assert out == "", out
    assert "401" in err and "invalid_api_key" in err, err
    assert "test-key" not in err, "the key must never reach stderr"


@check
def the_other_detail_shape_does_not_crash():
    """A 422 carries `detail` as a LIST of {loc,msg,type}; the documented error
    envelope carries it as an OBJECT. Parsing one shape crashes on the other."""
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")
    code, _, err, _ = run(
        ["transcribe", str(src)],
        {("POST", "/v1/speech-to-text"): Response(
            status_code=422,
            body={"detail": [{"loc": ["body", "model_id"],
                              "msg": "field required", "type": "missing"}]})})
    assert code == audio.EXIT_FAILED, code
    assert "field required" in err, err
    assert "Traceback" not in err, err


@check
def tts_writes_the_bytes_and_sends_the_language():
    out_file = Path(tempfile.mkdtemp()) / "answer.mp3"
    code, out, _, stub = run(
        ["tts", "--text", "ola", "--out", str(out_file)],
        {("GET", "/v2/voices"): Response(body={"voices": [{"voice_id": "v1"}]}),
         ("POST", "/v1/text-to-speech/v1"): Response(content=b"ID3audio")})
    assert code == 0, code
    assert out_file.read_bytes() == b"ID3audio"
    body = json.loads(out)
    assert body["voice_id"] == "v1" and body["bytes"] == 8, body
    post = stub.calls[1]
    assert post["params"]["output_format"] == audio.OUTPUT_FORMATS[".mp3"], post
    # the default model takes language_code, so the config's language IS sent
    assert post["json"]["language_code"] == audio.language(), post


@check
def tts_omits_the_language_for_the_model_that_refuses_it():
    """docs: "This parameter is not supported for multilingual_v2 models"."""
    out_file = Path(tempfile.mkdtemp()) / "answer.ogg"
    code, out, _, stub = run(
        ["tts", "--text", "ola", "--out", str(out_file),
         "--model", "eleven_" + audio.MULTILINGUAL_V2, "--voice", "pinned"],
        {("POST", "/v1/text-to-speech/pinned"): Response(content=b"OggS")})
    assert code == 0, code
    post = stub.calls[0]
    assert "language_code" not in post["json"], post
    assert post["params"]["output_format"] == audio.OUTPUT_FORMATS[".ogg"], post
    assert len(stub.calls) == 1, "a pinned --voice must not list voices"
    assert json.loads(out)["voice_source"] == "flag", out


@check
def an_account_with_no_voice_is_refused():
    out_file = Path(tempfile.mkdtemp()) / "answer.mp3"
    code, out, err, _ = run(
        ["tts", "--text", "ola", "--out", str(out_file)],
        {("GET", "/v2/voices"): Response(body={"voices": []})})
    assert code == audio.EXIT_FAILED, code
    assert out == "" and not out_file.exists()
    assert "no voice" in err, err


@check
def an_empty_audio_body_is_never_a_written_file():
    out_file = Path(tempfile.mkdtemp()) / "answer.mp3"
    code, _, err, _ = run(
        ["tts", "--text", "ola", "--out", str(out_file), "--voice", "v"],
        {("POST", "/v1/text-to-speech/v"): Response(content=b"")})
    assert code == audio.EXIT_FAILED, code
    assert not out_file.exists(), "a 0-byte file would read as a success"
    assert "no audio" in err, err


@check
def a_transport_failure_is_a_taught_refusal():
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")

    class Boom(Stub):
        def request(self, *a, **kw):
            raise self.RequestException("connection reset")

    stub, real = Boom({}), audio.requests
    audio.requests = stub
    err, code = io.StringIO(), 0
    import os
    os.environ[audio.KEY_ENV] = "test-key"
    try:
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            audio.main(["transcribe", str(src)])
    except SystemExit as exc:
        code = exc.code
    finally:
        audio.requests = real
        os.environ.pop(audio.KEY_ENV, None)
    assert code == audio.EXIT_FAILED, code
    assert "connection reset" in err.getvalue(), err.getvalue()
    assert "Traceback" not in err.getvalue()


@check
def no_language_literal_lives_outside_the_one_constant():
    """Clause 11's promise, asserted on the source rather than trusted: the only
    quoted language value in audio.py is DEFAULT_LANGUAGE's own."""
    import re
    source = (HERE / "audio.py").read_text(encoding="utf-8")
    codes = r"pt|en|es|fr|de|it|ja|zh|ru|pt-BR|pt-PT|en-US|en-GB|por|eng"
    hits = [m.group(0) for m in
            re.finditer(rf"""["']({codes})["']""", source)]
    assert hits == [f'"{audio.DEFAULT_LANGUAGE}"'], hits


def main():
    failures = []
    for fn in CHECKS:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as exc:
            failures.append((fn.__name__, exc))
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(CHECKS) - len(failures)}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
