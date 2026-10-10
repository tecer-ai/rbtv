"""Unit and runner tests for the Gemini image client and the image runner.

NO network, NO spend. The client's HTTP call (requests.post) is mocked; the
runner tests inject a fake ProviderClient (same pattern as test_run_integration).
No live image call is made here: these tests pin the two halves a live call
exercises, the request modality and the parsing of inline images.
"""
import json
import sys
import types

import pytest

import run
from clients.base import (
    Message,
    ProviderClient,
    ProviderConfig,
    ProviderName,
    RequestOptions,
    Response,
)
from clients.gemini import GeminiClient


# ---------------------------------------------------------------------------
# Fake HTTP plumbing for the client (mocks requests.post)
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data
        self.text = ""

    def json(self):
        return self._json


def _gemini_data(text_parts, finish="STOP"):
    """A minimal Gemini generateContent response with the given text parts."""
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": t} for t in text_parts]},
                "finishReason": finish,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 1,
            "candidatesTokenCount": 2,
            "totalTokenCount": 3,
        },
        "modelVersion": "gemini-3.1-flash-image",
    }


class CapturePost:
    """Captures each POST body and returns a canned Gemini response."""

    def __init__(self, response_json):
        self.response_json = response_json
        self.bodies = []

    def __call__(self, url, headers=None, json=None, timeout=None, **kwargs):
        self.bodies.append(json)
        return FakeResponse(200, self.response_json)


def make_client():
    c = GeminiClient()
    c.initialize(ProviderConfig(api_key="test-key"))
    return c


# ---------------------------------------------------------------------------
# Client tests — the request payload and the parsing of the reply
# ---------------------------------------------------------------------------
def test_explicit_max_tokens_is_sent(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.1-flash-image", max_tokens=2000),
    )
    assert post.bodies[0]["generationConfig"]["maxOutputTokens"] == 2000


def test_parse_concatenates_all_candidate_parts(monkeypatch):
    # Commentary can arrive as multiple text parts — all must be joined.
    post = CapturePost(_gemini_data(["Part A. ", "Part B. ", "Part C."]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    assert resp.content == "Part A. Part B. Part C."


def test_parse_handles_missing_parts(monkeypatch):
    # A candidate with no parts (e.g. a thinking-only overrun) must not crash.
    post = CapturePost({"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]})
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    assert resp.content == ""
    assert resp.raw_response["choices"][0]["finish_reason"] == "length"


# ---------------------------------------------------------------------------
# Runner tests (fake client injected)
# ---------------------------------------------------------------------------
class FakeGemini(ProviderClient):
    """A real ProviderClient subclass so run.main()'s discovery loop selects it.

    Records the messages it received and returns canned content + finish_reason.
    """

    _content = ""
    _finish = "stop"
    _artifacts = None
    received = []

    @property
    def name(self) -> ProviderName:
        return ProviderName.GEMINI

    def initialize(self, config) -> None:
        pass

    def chat(self, messages, options=None) -> Response:
        FakeGemini.received = messages
        return Response(
            content=FakeGemini._content,
            raw_response={"choices": [{"finish_reason": FakeGemini._finish}]},
            artifacts=FakeGemini._artifacts,
        )


def _run_gemini(monkeypatch, tmp_path, *, content, finish="stop", artifacts=None):
    FakeGemini._content = content
    FakeGemini._finish = finish
    FakeGemini._artifacts = artifacts
    FakeGemini.received = []

    prompt = tmp_path / "p.md"
    prompt.write_text("a red bicycle", encoding="utf-8")
    out = tmp_path / "out"

    fake_mod = types.ModuleType("clients.gemini")
    fake_mod.TheClient = FakeGemini
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    monkeypatch.setattr(run, "_resolve_key", lambda provider, launch_dir: "fake-key")

    argv = [
        "run.py",
        "--provider", "gemini",
        "--model", "gemini-3.1-flash-image",
        "--prompt-file", str(prompt),
        "--output-folder", str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        run.main()
    return exc.value.code, out


# ---------------------------------------------------------------------------
# Image generation: the request modality, the inline images, the run's result
# ---------------------------------------------------------------------------
def test_image_payload_asks_for_the_image_modality(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="a red bicycle")],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    body = post.bodies[0]
    assert body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    # an image call asks for no JSON envelope and no search tool ...
    assert "responseMimeType" not in body["generationConfig"]
    assert "tools" not in body
    # ... and NO token cap: an image's cost is not a token budget.
    assert "maxOutputTokens" not in body["generationConfig"]


def test_extra_params_are_sent_as_provider_parameters(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.1-flash-image", extra_params={"safetySettings": []}),
    )
    assert post.bodies[0]["safetySettings"] == []


def test_parse_extracts_inline_images_as_artifacts(monkeypatch):
    import base64 as _b64
    png = b"\x89PNG\r\n\x1a\nfake-bytes"
    data = _gemini_data(["here it is"])
    data["candidates"][0]["content"]["parts"].append(
        {"inlineData": {"mimeType": "image/png", "data": _b64.b64encode(png).decode()}}
    )
    data["candidates"][0]["content"]["parts"].append(
        {"inline_data": {"mime_type": "image/jpeg", "data": _b64.b64encode(b"jpg-bytes").decode()}}
    )
    post = CapturePost(data)
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    assert resp.content == "here it is", "text parts still concatenate normally"
    assert [a.filename for a in resp.artifacts] == ["image-1.png", "image-2.jpg"]
    assert resp.artifacts[0].content == png, "the bytes are decoded, not the base64 string"
    assert resp.artifacts[1].content == b"jpg-bytes"


def test_parse_without_inline_data_has_no_artifacts(monkeypatch):
    post = CapturePost(_gemini_data(["plain text"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat([Message(role="user", content="q")], RequestOptions(model="m"))
    assert resp.artifacts is None


def test_image_run_writes_the_image_and_asks_for_no_envelope(monkeypatch, tmp_path):
    from clients.base import Artifact
    code, out = _run_gemini(
        monkeypatch, tmp_path, content="",
        artifacts=[Artifact(filename="image-1.png", content=b"PNGDATA", content_type="image/png")],
    )
    assert code == 0
    assert (out / "image-1.png").read_bytes() == b"PNGDATA"
    rj = json.loads((out / "return.json").read_text(encoding="utf-8"))
    assert rj["status"] == "DONE"
    assert rj["landed"] == ["image-1.png"]
    assert not (out / "raw-output.md").exists(), "no commentary was sent, so no note file"
    # an image call sends NO system message: the prompt is the whole instruction
    assert [m for m in FakeGemini.received if m.role == "system"] == []


def test_image_run_without_an_image_says_so_instead_of_claiming_done(monkeypatch, tmp_path):
    code, out = _run_gemini(
        monkeypatch, tmp_path, content="I cannot draw that.",
        artifacts=None,
    )
    assert code == 0
    rj = json.loads((out / "return.json").read_text(encoding="utf-8"))
    assert rj["status"] == "DONE_WITH_NOTES", "an image run with no image is never a clean DONE"
    assert (out / "raw-output.md").read_text(encoding="utf-8") == "I cannot draw that."
    assert any("no inline image data" in c for c in rj["concerns"]), rj["concerns"]


# ---------------------------------------------------------------------------
# Input images (added 2026-09-15): --input-image sends existing image
# files IN alongside the prompt. Message.content becomes the provider-neutral
# part-list form (clients/base.py); only gemini.py knows the Google wire shape.
# ---------------------------------------------------------------------------
def test_input_image_payload_translates_to_inline_data(monkeypatch):
    import base64 as _b64
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    png_b64 = _b64.b64encode(b"png-bytes").decode()
    make_client().chat(
        [Message(role="user", content=[
            {"type": "text", "text": "restyle this logo"},
            {"type": "image", "mime_type": "image/png", "data": png_b64},
        ])],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    body = post.bodies[0]
    parts = body["contents"][0]["parts"]
    assert parts[0] == {"text": "restyle this logo"}
    assert parts[1] == {"inlineData": {"mimeType": "image/png", "data": png_b64}}


def test_input_image_payload_with_several_images_keeps_order(monkeypatch):
    import base64 as _b64
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    a_b64 = _b64.b64encode(b"aaa").decode()
    b_b64 = _b64.b64encode(b"bbb").decode()
    make_client().chat(
        [Message(role="user", content=[
            {"type": "text", "text": "combine these"},
            {"type": "image", "mime_type": "image/png", "data": a_b64},
            {"type": "image", "mime_type": "image/jpeg", "data": b_b64},
        ])],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    parts = post.bodies[0]["contents"][0]["parts"]
    assert parts == [
        {"text": "combine these"},
        {"inlineData": {"mimeType": "image/png", "data": a_b64}},
        {"inlineData": {"mimeType": "image/jpeg", "data": b_b64}},
    ]


def test_string_content_still_builds_a_single_text_part(monkeypatch):
    # No --input-image: Message.content is a plain string, sent as one text part.
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="a red bicycle")],
        RequestOptions(model="gemini-3.1-flash-image"),
    )
    assert post.bodies[0]["contents"][0]["parts"] == [{"text": "a red bicycle"}]


def test_unknown_part_type_raises_value_error(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    with pytest.raises(ValueError, match="unknown message part type"):
        make_client().chat(
            [Message(role="user", content=[{"type": "video", "data": "x"}])],
            RequestOptions(model="gemini-3.1-flash-image"),
        )


# ---------------------------------------------------------------------------
# Runner-level: --input-image wiring (run.py)
# ---------------------------------------------------------------------------
def test_input_image_bad_extension_is_refused(monkeypatch, tmp_path):
    prompt = tmp_path / "p.md"
    prompt.write_text("edit this", encoding="utf-8")
    bad = tmp_path / "ref.bmp"
    bad.write_bytes(b"BMPDATA")
    out = tmp_path / "out"

    fake_mod = types.ModuleType("clients.gemini")
    fake_mod.TheClient = FakeGemini
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    monkeypatch.setattr(run, "_resolve_key", lambda provider, launch_dir: "fake-key")
    argv = [
        "run.py",
        "--provider", "gemini",
        "--model", "gemini-3.1-flash-image",
        "--prompt-file", str(prompt),
        "--output-folder", str(out),
        "--input-image", str(bad),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 1


def test_input_image_missing_file_is_refused(monkeypatch, tmp_path):
    prompt = tmp_path / "p.md"
    prompt.write_text("edit this", encoding="utf-8")
    missing = tmp_path / "does-not-exist.png"
    out = tmp_path / "out"

    fake_mod = types.ModuleType("clients.gemini")
    fake_mod.TheClient = FakeGemini
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    monkeypatch.setattr(run, "_resolve_key", lambda provider, launch_dir: "fake-key")
    argv = [
        "run.py",
        "--provider", "gemini",
        "--model", "gemini-3.1-flash-image",
        "--prompt-file", str(prompt),
        "--output-folder", str(out),
        "--input-image", str(missing),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 1


def test_input_image_run_builds_list_form_message(monkeypatch, tmp_path):
    from clients.base import Artifact
    prompt = tmp_path / "p.md"
    prompt.write_text("restyle this logo", encoding="utf-8")
    img = tmp_path / "logo.png"
    img.write_bytes(b"\x89PNGfake")
    out = tmp_path / "out"

    FakeGemini._content = ""
    FakeGemini._finish = "stop"
    FakeGemini._artifacts = [Artifact(filename="image-1.png", content=b"OUT", content_type="image/png")]
    FakeGemini.received = []

    fake_mod = types.ModuleType("clients.gemini")
    fake_mod.TheClient = FakeGemini
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    monkeypatch.setattr(run, "_resolve_key", lambda provider, launch_dir: "fake-key")
    argv = [
        "run.py",
        "--provider", "gemini",
        "--model", "gemini-3.1-flash-image",
        "--prompt-file", str(prompt),
        "--output-folder", str(out),
        "--input-image", str(img),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 0

    user_msgs = [m for m in FakeGemini.received if m.role == "user"]
    assert len(user_msgs) == 1
    content = user_msgs[0].content
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "restyle this logo"}
    assert content[1]["type"] == "image"
    assert content[1]["mime_type"] == "image/png"
    import base64 as _b64
    assert _b64.b64decode(content[1]["data"]) == b"\x89PNGfake"
