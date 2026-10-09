#!/usr/bin/env python3
"""The checks for elevenlabs.py — `python3 test_elevenlabs.py`, no framework, no network.

Two halves:

- In-process arms replace the HTTP layer wholesale: `elevenlabs.requests` becomes a stub whose
  `request()` signature and return type match the real one, and which RAISES on any URL a test
  did not declare. A stub that quietly answered an undeclared call is how a suite goes green over
  a live request.
- Subprocess arms run the real CLI end-to-end inside a temporary installation against a local stub
  HTTP server, with sentinel keys only (never a real one) and the API base pointed at the stub via
  ELEVENLABS_API_URL. Nothing here reads the installation's real .env.

Every arm this file asserts is one the CLI's own live probes cannot reach without an ElevenLabs
key: the 401, the silent recording, the two shapes of `detail`, and whether `language_code` is
sent for a given model.
"""

import http.server
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("elevenlabs_cli", HERE / "elevenlabs.py")
elevenlabs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(elevenlabs)

SENTINEL_ENV = "sentinel-env-key"       # stands in for $ELEVENLABS_API_KEY
SENTINEL_FILE = "sentinel-file-key"     # stands in for the env file's key


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
    """Stands in for the `requests` module inside elevenlabs.py."""

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


def run(argv, routes, key=SENTINEL_ENV, env_file=None, config=None):
    """Run the CLI in-process. Returns (exit_code, stdout, stderr, stub).

    `env_file`/`config` patch the installation paths; None means "no such file"
    (a missing temp path) — the OS environment then carries the key."""
    stub, real = Stub(routes), elevenlabs.requests
    elevenlabs.requests = stub
    out, err, code = io.StringIO(), io.StringIO(), 0
    envfile, cfg = elevenlabs.ENV_FILE, elevenlabs.CONFIG
    elevenlabs.ENV_FILE = env_file or Path(tempfile.gettempdir()) / "no-such-env-file"
    elevenlabs.CONFIG = config or Path(tempfile.gettempdir()) / "no-such-config"
    previous = os.environ.get(elevenlabs.KEY_ENV)
    if key is None:
        os.environ.pop(elevenlabs.KEY_ENV, None)
    else:
        os.environ[elevenlabs.KEY_ENV] = key
    try:
        with redirect_stdout(out), redirect_stderr(err):
            elevenlabs.main(argv)
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        elevenlabs.requests, elevenlabs.ENV_FILE, elevenlabs.CONFIG = real, envfile, cfg
        if previous is None:
            os.environ.pop(elevenlabs.KEY_ENV, None)
        else:
            os.environ[elevenlabs.KEY_ENV] = previous
    return code, out.getvalue(), err.getvalue(), stub


def temp_install(with_key_file=True, language=None):
    """A temporary installation: install record, env file, elevenlabs config, work dir."""
    root = Path(tempfile.mkdtemp(prefix="el-install-")).resolve()
    cfg_dir = root / ".rbtv" / "config"
    (cfg_dir / "elevenlabs").mkdir(parents=True)
    (cfg_dir / "install.json").write_text("{}", encoding="utf-8")
    env_file = cfg_dir / "env" / ".env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text(
        f"{elevenlabs.KEY_ENV}={SENTINEL_FILE}\n" if with_key_file else "", encoding="utf-8")
    cfg = cfg_dir / "elevenlabs" / "config.json"
    if language is not None:
        cfg.write_text(json.dumps({"language": language}) + "\n", encoding="utf-8")
    work = root / "work"
    work.mkdir()
    return root, work, cfg


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


# ─────────────────────────────────────────────────── in-process: the remote arms

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
    assert body["model_id"] == elevenlabs.STT_MODEL, body
    assert body["key_source"] == "env", body
    sent = stub.calls[0]["data"]
    assert sent["model_id"] == elevenlabs.STT_MODEL, sent
    # the language reaching the API is the config's, never a literal
    assert sent["language_code"] == elevenlabs.language(), sent


@check
def a_silent_recording_is_a_failure_not_an_empty_success():
    src = Path(tempfile.mkdtemp()) / "silence.mp3"
    src.write_bytes(b"bytes")
    code, out, err, _ = run(
        ["transcribe", str(src)],
        {("POST", "/v1/speech-to-text"): Response(body={"text": "   "})})
    assert code == elevenlabs.EXIT_FAILED, code
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
    assert code == elevenlabs.EXIT_FAILED, code
    assert out == "", out
    assert "401" in err and "invalid_api_key" in err, err
    assert SENTINEL_ENV not in err, "the key must never reach stderr"


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
    assert code == elevenlabs.EXIT_FAILED, code
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
    assert post["params"]["output_format"] == elevenlabs.OUTPUT_FORMATS[".mp3"], post
    # the default model takes language_code, so the config's language IS sent
    assert post["json"]["language_code"] == elevenlabs.language(), post


@check
def tts_omits_the_language_for_the_model_that_refuses_it():
    """docs: "This parameter is not supported for multilingual_v2 models"."""
    out_file = Path(tempfile.mkdtemp()) / "answer.ogg"
    code, out, _, stub = run(
        ["tts", "--text", "ola", "--out", str(out_file),
         "--model", "eleven_" + elevenlabs.MULTILINGUAL_V2, "--voice", "pinned"],
        {("POST", "/v1/text-to-speech/pinned"): Response(content=b"OggS")})
    assert code == 0, code
    post = stub.calls[0]
    assert "language_code" not in post["json"], post
    assert post["params"]["output_format"] == elevenlabs.OUTPUT_FORMATS[".ogg"], post
    assert len(stub.calls) == 1, "a pinned --voice must not list voices"
    assert json.loads(out)["voice_source"] == "flag", out


@check
def an_account_with_no_voice_is_refused():
    out_file = Path(tempfile.mkdtemp()) / "answer.mp3"
    code, out, err, _ = run(
        ["tts", "--text", "ola", "--out", str(out_file)],
        {("GET", "/v2/voices"): Response(body={"voices": []})})
    assert code == elevenlabs.EXIT_FAILED, code
    assert out == "" and not out_file.exists()
    assert "no voice" in err, err


@check
def an_empty_audio_body_is_never_a_written_file():
    out_file = Path(tempfile.mkdtemp()) / "answer.mp3"
    code, _, err, _ = run(
        ["tts", "--text", "ola", "--out", str(out_file), "--voice", "v"],
        {("POST", "/v1/text-to-speech/v"): Response(content=b"")})
    assert code == elevenlabs.EXIT_FAILED, code
    assert not out_file.exists(), "a 0-byte file would read as a success"
    assert "no audio" in err, err


@check
def a_transport_failure_is_a_taught_refusal():
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")

    class Boom(Stub):
        def request(self, *a, **kw):
            raise self.RequestException("connection reset")

    stub, real = Boom({}), elevenlabs.requests
    elevenlabs.requests = stub
    err, code = io.StringIO(), 0
    previous = os.environ.pop(elevenlabs.KEY_ENV, None)
    os.environ[elevenlabs.KEY_ENV] = SENTINEL_ENV
    try:
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            elevenlabs.main(["transcribe", str(src)])
    except SystemExit as exc:
        code = exc.code
    finally:
        elevenlabs.requests = real
        if previous is None:
            os.environ.pop(elevenlabs.KEY_ENV, None)
        else:
            os.environ[elevenlabs.KEY_ENV] = previous
    assert code == elevenlabs.EXIT_FAILED, code
    assert "connection reset" in err.getvalue(), err.getvalue()
    assert "Traceback" not in err.getvalue()


@check
def voices_lists_the_account():
    code, out, _, stub = run(
        ["voices"],
        {("GET", "/v2/voices"): Response(body={"voices": [
            {"voice_id": "v1", "name": "First", "language": "pt",
             "description": " the one "},
            {"name": "no id, dropped"},
            {"voice_id": "v2", "name": "Second", "language": "en"}]})})
    assert code == 0, code
    body = json.loads(out)
    assert body["count"] == 2, body
    assert body["voices"][0] == {"voice_id": "v1", "name": "First",
                                 "language": "pt", "description": "the one"}, body
    assert stub.calls[0]["method"] == "GET", stub.calls


@check
def an_empty_account_is_a_valid_voice_list():
    code, out, err, _ = run(["voices"],
                            {("GET", "/v2/voices"): Response(body={"voices": []})})
    assert code == 0 and err == "", (code, err)
    assert json.loads(out)["voices"] == []


@check
def voices_preserves_pagination():
    code, out, err, stub = run(["voices", "--page-token", "page-two"],
        {("GET", "/v2/voices"): Response(body={"voices": [], "has_more": True, "next_page_token": "page-three"})})
    assert code == 0 and err == "", (code, err)
    assert json.loads(out)["next_page_token"] == "page-three"
    assert json.loads(out)["has_more"] is True
    assert stub.calls[0]["params"] == {"page_size": 100, "next_page_token": "page-two"}


# ────────────────────────────────────────────────── in-process: key and config

@check
def the_installation_is_found_from_inside():
    """Install files resolve from a folder inside the installation; not outside one."""
    root, work, cfg = temp_install()
    for rel in (elevenlabs.ENV_FILE_REL, elevenlabs.CONFIG_REL):
        assert elevenlabs._install_file(rel, work) == root / rel, rel
        assert elevenlabs._install_file(rel, root) == root / rel, rel
    outside = Path(tempfile.mkdtemp(prefix="el-outside-")).resolve()
    assert elevenlabs._install_file(elevenlabs.ENV_FILE_REL, outside) is None


@check
def the_environment_variable_beats_the_env_file():
    """Root-rule precedence: $ELEVENLABS_API_KEY first, the installation env file second."""
    root, _, _ = temp_install()
    previous = os.environ.pop(elevenlabs.KEY_ENV, None)
    envfile, cfg = elevenlabs.ENV_FILE, elevenlabs.CONFIG
    try:
        elevenlabs.ENV_FILE = root / ".rbtv" / "config" / "env" / ".env"
        elevenlabs.CONFIG = None
        os.environ[elevenlabs.KEY_ENV] = SENTINEL_ENV
        assert elevenlabs.api_key() == (SENTINEL_ENV, "env")
        os.environ.pop(elevenlabs.KEY_ENV)
        assert elevenlabs.api_key() == (SENTINEL_FILE, "env-file")
    finally:
        elevenlabs.ENV_FILE, elevenlabs.CONFIG = envfile, cfg
        if previous is not None:
            os.environ[elevenlabs.KEY_ENV] = previous


@check
def no_key_anywhere_refuses_naming_both_places():
    root, _, _ = temp_install(with_key_file=False)
    src = Path(tempfile.mkdtemp()) / "note.mp3"
    src.write_bytes(b"bytes")
    err, code = io.StringIO(), 0
    envfile, cfg = elevenlabs.ENV_FILE, elevenlabs.CONFIG
    previous = os.environ.pop(elevenlabs.KEY_ENV, None)
    try:
        elevenlabs.ENV_FILE = root / ".rbtv" / "config" / "env" / ".env"
        elevenlabs.CONFIG = None
        with redirect_stderr(err):
            elevenlabs.main(["transcribe", str(src)])
    except SystemExit as exc:
        code = exc.code
    finally:
        elevenlabs.ENV_FILE, elevenlabs.CONFIG = envfile, cfg
        if previous is not None:
            os.environ[elevenlabs.KEY_ENV] = previous
    assert code == elevenlabs.EXIT_REFUSED, code
    text = err.getvalue()
    assert elevenlabs.KEY_ENV in text and str(root / ".rbtv" / "config" / "env" / ".env") \
        in text, text
    assert "sentinel" not in text


@check
def the_language_verb_needs_no_key():
    root, work, cfg = temp_install(with_key_file=False, language="en")
    code, out, err, _ = run(["language"], {}, key=None,
                            env_file=root / ".rbtv" / "config" / "env" / ".env",
                            config=cfg)
    assert code == 0 and err == "", (code, err)
    body = json.loads(out)
    assert body["language"] == "en" and body["config"] == str(cfg), body
    assert body["key_source"] is None, body


@check
def a_language_write_lands_in_the_installation_config():
    root, work, cfg = temp_install()
    code, out, err, _ = run(["language", "en"], {}, key=None,
                            env_file=root / ".rbtv" / "config" / "env" / ".env",
                            config=cfg)
    assert code == 0 and err == "", (code, err)
    body = json.loads(out)
    assert body["changed"] is True and body["previous"] == elevenlabs.DEFAULT_LANGUAGE, body
    assert json.loads(cfg.read_text(encoding="utf-8"))["language"] == "en"


@check
def a_language_write_outside_an_installation_is_refused():
    """No installation above → clear error; the SOURCE config is never written."""
    before = (HERE / "config.json").read_bytes() if (HERE / "config.json").exists() else None
    err = io.StringIO()
    envfile, config_path = elevenlabs.ENV_FILE, elevenlabs.CONFIG
    previous = os.environ.pop(elevenlabs.KEY_ENV, None)
    try:
        elevenlabs.ENV_FILE = None
        elevenlabs.CONFIG = None
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                elevenlabs.main(["language", "en"])
        except SystemExit as exc:
            assert exc.code == elevenlabs.EXIT_REFUSED
        else:
            raise AssertionError("no refusal")
    finally:
        elevenlabs.ENV_FILE, elevenlabs.CONFIG = envfile, config_path
        if previous is not None:
            os.environ[elevenlabs.KEY_ENV] = previous
    assert "install.json" in err.getvalue(), err.getvalue()
    after = (HERE / "config.json").read_bytes() if (HERE / "config.json").exists() else None
    assert after == before, "the source config must never be created or written"


@check
def no_language_literal_lives_outside_the_one_constant():
    """Asserted on the source rather than trusted: the only quoted language value
    in elevenlabs.py is DEFAULT_LANGUAGE's own."""
    import re
    source = (HERE / "elevenlabs.py").read_text(encoding="utf-8")
    codes = r"pt|en|es|fr|de|it|ja|zh|ru|pt-BR|pt-PT|en-US|en-GB|por|eng"
    hits = [m.group(0) for m in
            re.finditer(rf"""["']({codes})["']""", source)]
    assert hits == [f'"{elevenlabs.DEFAULT_LANGUAGE}"'], hits


# ─────────────────────────────────────────────────────── the real-CLI lifecycle

class _Handler(http.server.BaseHTTPRequestHandler):
    """Canned ElevenLabs answers. `server.state` holds the mode and seen requests."""

    def _reply(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _seen(self):
        return {"method": self.command, "path": self.path,
                "key": self.headers.get("xi-api-key")}

    def _read_body(self):
        size = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(size) if size else b""

    def do_POST(self):
        st = self.server.state
        self._read_body()
        st["seen"].append(self._seen())
        if self.path.startswith("/v1/speech-to-text"):
            if st["st"] == "empty":
                self._reply(200, json.dumps({"text": "  "}).encode())
            elif st["st"] == 401:
                self._reply(401, json.dumps(
                    {"detail": {"code": "invalid_api_key",
                                "message": "The provided API key is invalid."}}).encode())
            else:
                self._reply(200, json.dumps({"text": " ola "}).encode())
        elif "/v1/text-to-speech/" in self.path:
            self._reply(200, b"ID3audio", ctype="audio/mpeg")
        else:
            self._reply(404, b"{}")

    def do_GET(self):
        st = self.server.state
        st["seen"].append(self._seen())
        if self.path.startswith("/v2/voices"):
            self._reply(200, json.dumps({"voices": [
                {"voice_id": "sv1", "name": "Stub One", "language": "pt",
                 "description": "first"}]}).encode())
        else:
            self._reply(404, b"{}")

    def log_message(self, *a):
        pass


def cli(args, cwd, extra_env=None, stdin=None):
    """Run the real CLI as a subprocess. Returns (code, stdout, stderr)."""
    env = {k: v for k, v in os.environ.items() if k != elevenlabs.KEY_ENV}
    env.update(extra_env or {})
    proc = subprocess.run(
        [sys.executable, str(HERE / "elevenlabs.py"), *args],
        cwd=cwd, env=env, input=stdin, capture_output=True, text=True,
        timeout=60)
    return proc.returncode, proc.stdout, proc.stderr


@check
def the_real_cli_lifecycle_under_a_temporary_installation():
    root, work, cfg = temp_install()
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler) as httpd:
        httpd.state = {"st": "ok", "seen": []}
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{httpd.server_address[1]}"
        env = {elevenlabs.API_URL_ENV: url}

        def fresh():
            httpd.state["seen"].clear()

        # 1. every help, keyless
        for args in (["--help"], ["transcribe", "--help"], ["tts", "--help"],
                    ["voices", "--help"], ["language", "--help"], ["--help", "tts"]):
            code, out, err = cli(args, work, env)
            assert code == 0, (args, err)
            assert "elevenlabs" in out and "ElevenLabs" in out, (args, out)
            if args == ["--help", "tts"]:
                assert out.startswith("usage: elevenlabs tts"), out

        # 2. missing key refuses locally, naming the precedence in order
        no_key = {elevenlabs.API_URL_ENV: url}
        root_env = root / ".rbtv" / "config" / "env" / ".env"
        root_env.write_text("", encoding="utf-8")
        note = work / "note.mp3"
        note.write_bytes(b"bytes")
        code, out, err = cli(["transcribe", str(note)], work, no_key)
        assert code == 2 and out == "", (code, out, err)
        assert f"${elevenlabs.KEY_ENV}" in err and str(root_env) in err, err
        root_env.write_text(f"{elevenlabs.KEY_ENV}={SENTINEL_FILE}\n", encoding="utf-8")

        # 3. precedence: the environment beats the env file
        fresh()
        code, out, err = cli(["transcribe", str(note)], work,
                             {**env, elevenlabs.KEY_ENV: SENTINEL_ENV})
        assert code == 0, err
        assert json.loads(out)["key_source"] == "env", out
        assert httpd.state["seen"][0]["key"] == SENTINEL_ENV

        # 4. the env file serves when the environment holds none
        fresh()
        code, out, _ = cli(["transcribe", str(note)], work, env)
        assert code == 0
        assert json.loads(out)["key_source"] == "env-file", out
        assert httpd.state["seen"][0]["key"] == SENTINEL_FILE

        # 5. remote results: normal, empty transcript, 401 — no secret leaks
        fresh()
        httpd.state["st"] = "empty"
        code, out, err = cli(["transcribe", str(note)], work, env)
        assert code == 1 and "empty transcript" in err, (code, err)
        httpd.state["st"] = 401
        code, out, err = cli(["transcribe", str(note)], work, env)
        assert code == 1 and "401" in err, (code, err)
        assert SENTINEL_FILE not in err and SENTINEL_ENV not in err, err
        httpd.state["st"] = "ok"

        # 6. tts: --file, stdin, and both output formats
        text_file = work / "say.txt"
        text_file.write_text("bom dia", encoding="utf-8")
        for out_name, fmt in (("answer.mp3", "mp3_44100_128"),
                              ("answer.ogg", "opus_48000_128")):
            fresh()
            code, out, err = cli(["tts", "--file", str(text_file),
                                  "--out", str(work / out_name)], work, env)
            assert code == 0, err
            body = json.loads(out)
            assert body["output_format"] == fmt and body["bytes"] == 8, body
            assert (work / out_name).read_bytes() == b"ID3audio"
        fresh()
        code, out, err = cli(["tts", "--file", "-", "--out", str(work / "stdin.mp3")],
                             work, env, stdin="lido do stdin")
        assert code == 0, err
        assert json.loads(out)["chars"] == len("lido do stdin"), out

        # 7. tts refusals: bad extension, no text
        code, out, err = cli(["tts", "--text", "ola", "--out", str(work / "a.wav")],
                             work, env)
        assert code == 2 and ".mp3" in err and ".opus" in err, (code, err)
        code, out, err = cli(["tts", "--out", str(work / "a.mp3")], work, env)
        assert code == 2 and ("--text" in err or "--file" in err), (code, err)

        # 8. voices through the real CLI
        fresh()
        code, out, err = cli(["voices"], work, env)
        assert code == 0, err
        body = json.loads(out)
        assert body["voices"][0]["voice_id"] == "sv1" and body["count"] == 1, body
        fresh()
        code, out, err = cli(["tts", "--text", "ola", "--out", str(work / "v.mp3"),
                              "--voice", "sv1"], work, env)
        assert code == 0, err
        assert json.loads(out)["voice_source"] == "flag", out

        # 9. language: read, change, no-op
        code, out, err = cli(["language"], work, {})
        assert code == 0, err
        assert json.loads(out)["language"] == elevenlabs.DEFAULT_LANGUAGE, out
        code, out, err = cli(["language", "en"], work, {})
        assert code == 0 and json.loads(out)["changed"] is True, (out, err)
        code, out, err = cli(["language", "en"], work, {})
        assert code == 0 and json.loads(out)["changed"] is False, (out, err)
        assert json.loads((root / ".rbtv" / "config" / "elevenlabs" /
                           "config.json").read_text(encoding="utf-8")
                          )["language"] == "en"
        code, out, err = cli(["language", "pt-BR"], work, {})
        assert code == 2 and "not a language code" in err, (code, err)

        # 10. outside an installation: read shows the default, write refuses
        outside = Path(tempfile.mkdtemp(prefix="el-outside-")).resolve()
        code, out, err = cli(["language"], outside, {})
        assert code == 0, err
        assert json.loads(out)["config"] is None, out
        code, out, err = cli(["language", "en"], outside, {})
        assert code == 2 and "install.json" in err, (code, err)

        httpd.shutdown()


def main():
    failures = []
    for fn in CHECKS:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as exc:
            failures.append((fn.__name__, exc))
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 — a crash is a failure, not a abort
            failures.append((fn.__name__, exc))
            print(f"FAIL {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(CHECKS) - len(failures)}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
