"""Mocked unit tests for the Manus client artifact-fetch + structured-output path.

NO network. NO spend. Every HTTP call (requests.post / requests.get) is mocked.

Download-auth contract (revised 2026-06-11 after a 40-call live probe —
`2-areas/rbtv/orchestration/manus-artifact-fetch/auth-probe/summary.md`): Manus
serves every output artifact via a CloudFront *presigned* URL whose query
signature carries the authorization; the `x-manus-api-key` header is ignored by
the CDN. The client does a SINGLE GET (key header retained as zero-cost
insurance for a hypothetical api-gated artifact) and FAILS LOUD on any non-200
— there is no with-key/no-key fallback and no login-page heuristic (a presigned
URL returns a 403 on an invalid/expired signature, never a 200 login page).
"""
import json

import pytest

from clients.base import Message, ProviderConfig, RequestOptions
from clients.manus import ManusClient


# --------------------------------------------------------------------------
# Fake HTTP plumbing
# --------------------------------------------------------------------------
class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code=200, json_data=None, content=b"", text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content
        self.text = text
        self.headers = headers or {}

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


class ManusHTTP:
    """Routes mocked POST/GET calls for a Manus task lifecycle.

    post(task.create) -> {"task_id": ...}
    get(task.detail)  -> status stopped
    get(task.listMessages) -> the supplied messages payload
    get(<attachment url>)  -> bytes OR a callable(headers)->FakeResponse
    """

    def __init__(self, list_messages_payload, downloads=None, detail_status="stopped"):
        self.list_messages_payload = list_messages_payload
        self.downloads = downloads or {}
        self.detail_status = detail_status
        self.create_bodies = []   # captured POST json bodies to task.create
        self.download_calls = []  # (url, had_key_header)

    def post(self, url, headers=None, json=None, timeout=None, **kwargs):
        if url.endswith("/task.create"):
            self.create_bodies.append(json)
            return FakeResponse(200, {"task_id": "task-abc"})
        raise AssertionError(f"unexpected POST {url}")

    def get(self, url, headers=None, params=None, timeout=None, **kwargs):
        if url.endswith("/task.detail"):
            return FakeResponse(200, {"task": {"status": self.detail_status}})
        if url.endswith("/task.listMessages"):
            return FakeResponse(200, self.list_messages_payload)
        # otherwise: an attachment download URL
        had_key = bool(headers and "x-manus-api-key" in headers)
        self.download_calls.append((url, had_key))
        handler = self.downloads.get(url)
        if handler is None:
            raise AssertionError(f"unexpected GET (no download handler) {url}")
        if callable(handler):
            return handler(headers or {})
        return FakeResponse(200, content=handler)


def make_client():
    client = ManusClient()
    client.initialize(ProviderConfig(api_key="test-key"))
    return client


def assistant_event(content="", attachments=None):
    return {
        "type": "assistant_message",
        "assistant_message": {
            "content": content,
            "attachments": attachments or [],
        },
    }


# --------------------------------------------------------------------------
# Test 1 — attachments parsed + downloaded (one GET per url, WITH key)
# --------------------------------------------------------------------------
def test_attachments_parsed_and_downloaded(monkeypatch):
    file_url = "https://private-us-east-1.manuscdn.com/report.pdf?Signature=x"
    image_url = "https://private-us-east-1.manuscdn.com/chart.png?Signature=y"
    attachments = [
        {"type": "file", "filename": "report.pdf", "url": file_url,
         "content_type": "application/pdf"},
        {"type": "image", "filename": "chart.png", "url": image_url,
         "content_type": "image/png"},
    ]
    payload = {"messages": [assistant_event("Here is your report.", attachments)]}
    http = ManusHTTP(
        payload,
        downloads={file_url: b"PDFBYTES-1", image_url: b"PNGBYTES-2"},
    )
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="make a report")])

    assert resp.artifacts is not None
    assert len(resp.artifacts) == 2
    by_name = {a.filename: a for a in resp.artifacts}
    assert by_name["report.pdf"].content == b"PDFBYTES-1"
    assert by_name["report.pdf"].content_type == "application/pdf"
    assert by_name["report.pdf"].source_url == file_url
    assert by_name["chart.png"].content == b"PNGBYTES-2"
    # exactly one GET per url, each carrying the key header
    assert http.download_calls == [(file_url, True), (image_url, True)]
    # narration still captured
    assert resp.content == "Here is your report."


# --------------------------------------------------------------------------
# Test 2 — single GET, no fallback, no artifact_auth recorded
# --------------------------------------------------------------------------
def test_single_get_no_fallback(monkeypatch):
    url = "https://private-us-east-1.manuscdn.com/data.bin?Signature=z"

    def handler(headers):
        return FakeResponse(200, content=b"PRESIGNEDBYTES")

    attachments = [{"type": "file", "filename": "data.bin", "url": url,
                    "content_type": "application/octet-stream"}]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={url: handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    assert len(resp.artifacts) == 1
    assert resp.artifacts[0].content == b"PRESIGNEDBYTES"
    # ONE GET, with the key header; no second attempt
    assert http.download_calls == [(url, True)]
    # the auth-mode map is gone — mode is constant (presigned), nothing to record
    assert "artifact_auth" not in resp.raw_response


# --------------------------------------------------------------------------
# Test 3 — a non-200 (e.g. expired presign 403) is a NON-FATAL recorded error
# --------------------------------------------------------------------------
def test_non_200_recorded_as_error_no_fallback(monkeypatch):
    good_url = "https://private-us-east-1.manuscdn.com/good.txt?Signature=a"
    bad_url = "https://private-us-east-1.manuscdn.com/bad.txt?Signature=b"

    def bad_handler(headers):
        return FakeResponse(403, text="expired signature")

    attachments = [
        {"type": "file", "filename": "good.txt", "url": good_url,
         "content_type": "text/plain"},
        {"type": "file", "filename": "bad.txt", "url": bad_url,
         "content_type": "text/plain"},
    ]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={good_url: b"GOOD", bad_url: bad_handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    # task still returns; good artifact present, bad one absent
    assert len(resp.artifacts) == 1
    assert resp.artifacts[0].filename == "good.txt"
    errors = resp.raw_response.get("artifact_errors", [])
    assert len(errors) == 1
    assert errors[0]["filename"] == "bad.txt"
    assert errors[0]["url"] == bad_url
    assert "403" in errors[0]["error"]
    # the failing URL was hit exactly once — no with-key/no-key retry
    assert http.download_calls.count((bad_url, True)) == 1
    assert (bad_url, False) not in http.download_calls


# --------------------------------------------------------------------------
# Test 4 — an HTML artifact (200 text/html) is saved as-is (no login heuristic)
# --------------------------------------------------------------------------
def test_html_artifact_downloaded_as_is(monkeypatch):
    url = "https://private-us-east-1.manuscdn.com/page.html?Signature=h"

    def handler(headers):
        return FakeResponse(
            200, content=b"<html>real content</html>",
            headers={"Content-Type": "text/html"},
        )

    attachments = [{"type": "file", "filename": "page.html", "url": url,
                    "content_type": "text/html"}]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={url: handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    assert len(resp.artifacts) == 1
    assert resp.artifacts[0].content == b"<html>real content</html>"
    assert http.download_calls == [(url, True)]


# --------------------------------------------------------------------------
# Test 5 — narration preserved (C2 regression), no attachments
# --------------------------------------------------------------------------
def test_narration_preserved_no_attachments(monkeypatch):
    payload = {
        "messages": [
            assistant_event("First line.", []),
            assistant_event("Second line.", []),
        ]
    }
    http = ManusHTTP(payload)
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="answer in text")])

    assert resp.content == "First line.\nSecond line."
    assert not resp.artifacts  # empty list or None


# --------------------------------------------------------------------------
# Test 6 — structured_output_schema (C3)
# --------------------------------------------------------------------------
def test_structured_output_schema(monkeypatch):
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
    structured_event = {
        "type": "structured_output_result",
        "structured_output_result": {
            "success": True,
            "value": {"answer": "42"},
            "error": None,
        },
    }
    payload = {
        "messages": [
            assistant_event("narration", []),
            structured_event,
        ]
    }
    http = ManusHTTP(payload)
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat(
        [Message(role="user", content="give me the answer")],
        RequestOptions(extra_params={"structured_output_schema": schema}),
    )

    # task.create body carried the schema
    assert len(http.create_bodies) == 1
    assert http.create_bodies[0].get("structured_output_schema") == schema
    # structured result captured
    assert resp.structured_result == {
        "success": True,
        "value": {"answer": "42"},
        "error": None,
    }


# --------------------------------------------------------------------------
# Test 7 — system message excluded from task.create description
# --------------------------------------------------------------------------
def test_system_message_excluded_from_description(monkeypatch):
    payload = {"messages": [assistant_event("ok", [])]}
    http = ManusHTTP(payload)
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    system_text = "Respond ONLY with a single JSON object {files:...}"
    user_text = "Build me a slide deck about whales."
    client = make_client()
    client.chat([
        Message(role="system", content=system_text),
        Message(role="user", content=user_text),
    ])

    assert len(http.create_bodies) == 1
    description = http.create_bodies[0]["message"]["content"]
    assert system_text not in description
    assert user_text in description
