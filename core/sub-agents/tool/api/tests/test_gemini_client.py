"""Unit + runner tests for the Gemini client and the grounded dispatch path.

NO network, NO spend. The client's HTTP call (requests.post) is mocked; the
runner tests inject a fake ProviderClient (same pattern as test_run_integration).

Regression context (2026-06-24, rbtv-tasks "Gemini grounded returns
empty/truncated raw output"): a grounded dispatch returned an empty/truncated
raw-output.md because

  1. the default maxOutputTokens (4096) was consumed by the 3.x-flash extended-
     thinking budget (thinking tokens are billed against maxOutputTokens), so the
     visible answer was starved — truncated, or replaced by leaked reasoning; and
  2. run.py sent the JSON {files:...} envelope system message even in grounded
     mode, so the model wrapped its answer in JSON that then truncated, and a
     parse-success would have written a model-named file instead of raw-output.md.

Live repro confirmed: a grounded research brief spent 4727 thinking tokens,
overran the 4096 cap, and landed a 612-byte truncated dump; at the raised budget
the same call returned the full ~8.9KB answer in raw-output.md.

Fix: a larger grounded maxOutputTokens default (gemini.py) + grounded mode is a
raw-dump path — no envelope ask, output written verbatim to raw-output.md
(run.py).
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
from clients.gemini import (
    GeminiClient,
    _DEFAULT_MAX_OUTPUT_TOKENS,
    _GROUNDED_MAX_OUTPUT_TOKENS,
)


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
        "modelVersion": "gemini-3.5-flash",
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
# Client payload tests — the maxOutputTokens / grounding-mode regression
# ---------------------------------------------------------------------------
def test_grounded_payload_uses_large_budget_and_search_tool(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.5-flash", extra_params={"grounding": True}),
    )
    body = post.bodies[0]
    # grounded swaps JSON-mime for the search tool
    assert body["tools"] == [{"google_search": {}}]
    assert "responseMimeType" not in body["generationConfig"]
    # the budget is the grounded default ...
    assert body["generationConfig"]["maxOutputTokens"] == _GROUNDED_MAX_OUTPUT_TOKENS
    # ... and that default MUST stay well above the old thinking-starving 4096,
    # and above the non-grounded default (grounded needs thinking headroom).
    assert _GROUNDED_MAX_OUTPUT_TOKENS > 4096
    assert _GROUNDED_MAX_OUTPUT_TOKENS > _DEFAULT_MAX_OUTPUT_TOKENS


def test_default_payload_uses_json_mime_and_default_budget(monkeypatch):
    post = CapturePost(_gemini_data(["{}"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.5-flash"),
    )
    body = post.bodies[0]
    assert "tools" not in body
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["maxOutputTokens"] == _DEFAULT_MAX_OUTPUT_TOKENS
    # the non-grounded default also must not regress to the old starving value
    assert _DEFAULT_MAX_OUTPUT_TOKENS > 4096


def test_explicit_max_tokens_overrides_default(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.5-flash", max_tokens=2000, extra_params={"grounding": True}),
    )
    assert post.bodies[0]["generationConfig"]["maxOutputTokens"] == 2000


def test_parse_concatenates_all_candidate_parts(monkeypatch):
    # A grounded answer can arrive as multiple text parts — all must be joined.
    post = CapturePost(_gemini_data(["Part A. ", "Part B. ", "Part C."]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.5-flash", extra_params={"grounding": True}),
    )
    assert resp.content == "Part A. Part B. Part C."


def test_parse_handles_missing_parts(monkeypatch):
    # A candidate with no parts (e.g. a thinking-only overrun) must not crash.
    post = CapturePost({"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]})
    monkeypatch.setattr("clients.gemini.requests.post", post)
    resp = make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-3.5-flash"),
    )
    assert resp.content == ""
    assert resp.raw_response["choices"][0]["finish_reason"] == "length"


# ---------------------------------------------------------------------------
# Runner tests — the grounded raw-dump routing regression (fake client injected)
# ---------------------------------------------------------------------------
class FakeGemini(ProviderClient):
    """A real ProviderClient subclass so run.main()'s discovery loop selects it.

    Records the messages it received and returns canned content + finish_reason.
    """

    structured_output = True
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


def _run_gemini(monkeypatch, tmp_path, *, grounded, content, finish="stop",
                image=False, artifacts=None):
    FakeGemini._content = content
    FakeGemini._finish = finish
    FakeGemini._artifacts = artifacts
    FakeGemini.received = []

    prompt = tmp_path / "p.md"
    prompt.write_text("do research", encoding="utf-8")
    out = tmp_path / "out"

    fake_mod = types.ModuleType("clients.gemini")
    fake_mod.TheClient = FakeGemini
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    monkeypatch.setattr(run, "_resolve_key", lambda provider, api_dir: "fake-key")

    argv = [
        "run.py",
        "--provider", "gemini",
        "--model", "gemini-3.5-flash",
        "--prompt-file", str(prompt),
        "--output-folder", str(out),
    ]
    if grounded:
        argv.append("--grounded")
    if image:
        argv.append("--image")
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        run.main()
    return exc.value.code, out


def test_grounded_run_writes_raw_output_not_parsed_envelope(monkeypatch, tmp_path):
    # Even when the content is a VALID {files:...} envelope, grounded mode must NOT
    # parse it — it is dumped verbatim to raw-output.md (the documented surface).
    valid_envelope = '{"files": [{"path": "should_not_be_written.md", "content": "x"}]}'
    code, out = _run_gemini(monkeypatch, tmp_path, grounded=True, content=valid_envelope)
    assert code == 0
    assert (out / "raw-output.md").read_text(encoding="utf-8") == valid_envelope
    assert not (out / "should_not_be_written.md").exists()
    rj = json.loads((out / "return.json").read_text(encoding="utf-8"))
    assert rj["status"] == "DONE_WITH_NOTES"
    assert rj["landed"] == ["raw-output.md"]


def test_grounded_run_system_message_is_markdown_not_json(monkeypatch, tmp_path):
    _run_gemini(monkeypatch, tmp_path, grounded=True, content="# answer")
    sys_msgs = [m for m in FakeGemini.received if m.role == "system"]
    assert len(sys_msgs) == 1
    # grounded mode must NOT ask for the JSON files envelope ...
    assert '{"files"' not in sys_msgs[0].content
    # ... it asks for clean markdown instead
    assert "Markdown" in sys_msgs[0].content


def test_default_run_still_parses_envelope(monkeypatch, tmp_path):
    # Non-grounded path is unchanged: a valid envelope IS parsed and written.
    valid_envelope = (
        '{"files": [{"path": "deck.md", "content": "hello"}], '
        '"concerns": [], "open_questions": []}'
    )
    code, out = _run_gemini(monkeypatch, tmp_path, grounded=False, content=valid_envelope)
    assert code == 0
    assert (out / "deck.md").read_text(encoding="utf-8") == "hello"
    assert not (out / "raw-output.md").exists()
    rj = json.loads((out / "return.json").read_text(encoding="utf-8"))
    assert rj["status"] == "DONE"

    sys_msgs = [m for m in FakeGemini.received if m.role == "system"]
    assert '{"files"' in sys_msgs[0].content


# ---------------------------------------------------------------------------
# Image generation (added 2026-08-20, route redesign §7)
#
# NOT LIVE-VERIFIED: GEMINI_API_KEY is absent on this box, so no real image call
# has ever been made. These arms pin the two halves that a live call would
# exercise — the request MODALITY and the inline-image parsing — so the first
# real call fails on credentials or on the model id, never on our wiring.
# ---------------------------------------------------------------------------
def test_image_payload_asks_for_the_image_modality(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="a red bicycle")],
        RequestOptions(model="gemini-image", extra_params={"image": True}),
    )
    body = post.bodies[0]
    assert body["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]
    # an image call asks for no JSON envelope and no search tool ...
    assert "responseMimeType" not in body["generationConfig"]
    assert "tools" not in body
    # ... and NO token cap: an image's cost is not a token budget.
    assert "maxOutputTokens" not in body["generationConfig"]
    # the flag itself is consumed here, never forwarded as a provider parameter
    assert "image" not in body


def test_image_flag_is_not_forwarded_but_real_extras_are(monkeypatch):
    post = CapturePost(_gemini_data(["ok"]))
    monkeypatch.setattr("clients.gemini.requests.post", post)
    make_client().chat(
        [Message(role="user", content="q")],
        RequestOptions(model="gemini-image", extra_params={"image": True, "safetySettings": []}),
    )
    body = post.bodies[0]
    assert "image" not in body
    assert body["safetySettings"] == []


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
        RequestOptions(model="gemini-image", extra_params={"image": True}),
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
        monkeypatch, tmp_path, grounded=False, content="", image=True,
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
        monkeypatch, tmp_path, grounded=False, content="I cannot draw that.", image=True,
        artifacts=None,
    )
    assert code == 0
    rj = json.loads((out / "return.json").read_text(encoding="utf-8"))
    assert rj["status"] == "DONE_WITH_NOTES", "an image run with no image is never a clean DONE"
    assert (out / "raw-output.md").read_text(encoding="utf-8") == "I cannot draw that."
    assert any("no inline image data" in c for c in rj["concerns"]), rj["concerns"]


def test_image_and_grounded_together_are_refused(monkeypatch, tmp_path):
    code, _ = _run_gemini(monkeypatch, tmp_path, grounded=True, content="x", image=True)
    assert code == 1, "the two return surfaces are incompatible — the runner refuses, never guesses"
