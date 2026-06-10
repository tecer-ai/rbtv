"""Mocked unit tests for the Manus client artifact-fetch + structured-output path.

NO network. NO spend. Every HTTP call (requests.post / requests.get) is mocked.
Covers spec test-plan items 1-6.
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
    get(<attachment url>)  -> bytes, honouring an optional auth-fallback rule
    """

    def __init__(self, list_messages_payload, downloads=None, detail_status="stopped"):
        self.list_messages_payload = list_messages_payload
        # downloads: {url: handler} where handler is bytes OR a callable(headers)->FakeResponse
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
# Test 1 — attachments parsed + downloaded
# --------------------------------------------------------------------------
def test_attachments_parsed_and_downloaded(monkeypatch):
    file_url = "https://files.manus.ai/report.pdf"
    image_url = "https://files.manus.ai/chart.png"
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
    assert by_name["chart.png"].content_type == "image/png"
    # narration still captured
    assert resp.content == "Here is your report."


# --------------------------------------------------------------------------
# Test 2 — download auth fallback (401 WITH header -> 200 WITHOUT header)
# --------------------------------------------------------------------------
def test_download_auth_fallback(monkeypatch):
    url = "https://api.manus.ai/files/secret.bin"

    def handler(headers):
        if "x-manus-api-key" in headers:
            return FakeResponse(401, text="unauthorized")
        return FakeResponse(200, content=b"SECRETBYTES")

    attachments = [{"type": "file", "filename": "secret.bin", "url": url,
                    "content_type": "application/octet-stream"}]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={url: handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    assert len(resp.artifacts) == 1
    assert resp.artifacts[0].content == b"SECRETBYTES"
    # fallback fired: two GETs to the same url, first WITH key, then WITHOUT
    assert http.download_calls == [(url, True), (url, False)]
    # success path recorded as header-less (no-auth) in raw_response
    auth_modes = http  # placeholder kept simple
    assert resp.raw_response.get("artifact_auth") == {url: "no-key"}


# --------------------------------------------------------------------------
# Test 3 — download failure is non-fatal
# --------------------------------------------------------------------------
def test_download_failure_non_fatal(monkeypatch):
    good_url = "https://files.manus.ai/good.txt"
    bad_url = "https://files.manus.ai/bad.txt"

    def bad_handler(headers):
        return FakeResponse(500, text="server error")

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
    assert "error" in errors[0]


# --------------------------------------------------------------------------
# Test 4 — narration preserved (C2 regression), no attachments
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
# Test 5 — structured_output_schema (C3)
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
# Test 6 — system message excluded from task.create description
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


# --------------------------------------------------------------------------
# Test 2b — login-redirect masked as 200+HTML WITH key -> retry WITHOUT key
# --------------------------------------------------------------------------
def test_download_login_redirect_fallback(monkeypatch):
    """A 302 login redirect is auto-followed to a 200 HTML page. The declared
    content_type is application/pdf, so the HTML body is a masked auth failure:
    the no-key retry must fire and capture the real bytes."""
    url = "https://api.manus.ai/files/report.pdf"

    def handler(headers):
        if "x-manus-api-key" in headers:
            # login page served as 200 + text/html (requests followed the 302)
            return FakeResponse(
                200, content=b"<html>login</html>",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        return FakeResponse(
            200, content=b"%PDF-realbytes",
            headers={"Content-Type": "application/pdf"},
        )

    attachments = [{"type": "file", "filename": "report.pdf", "url": url,
                    "content_type": "application/pdf"}]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={url: handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    # the masked login page was NOT saved; the real bytes were, via no-key path
    assert len(resp.artifacts) == 1
    assert resp.artifacts[0].content == b"%PDF-realbytes"
    assert http.download_calls == [(url, True), (url, False)]
    assert resp.raw_response.get("artifact_auth") == {url: "no-key"}


# --------------------------------------------------------------------------
# Test 3b — login redirect on BOTH paths -> recorded as error, NOT saved
# --------------------------------------------------------------------------
def test_download_login_redirect_both_paths_recorded(monkeypatch):
    """Both with-key and no-key GETs return a 200 HTML login page while the
    attachment declared a PDF. No bytes may be saved; the failure is recorded
    in artifact_errors so login-page HTML is never passed off as the artifact."""
    url = "https://api.manus.ai/files/report.pdf"

    def handler(headers):
        return FakeResponse(
            200, content=b"<html>login</html>",
            headers={"Content-Type": "text/html"},
        )

    attachments = [{"type": "file", "filename": "report.pdf", "url": url,
                    "content_type": "application/pdf"}]
    payload = {"messages": [assistant_event("done", attachments)]}
    http = ManusHTTP(payload, downloads={url: handler})
    monkeypatch.setattr("clients.manus.requests.post", http.post)
    monkeypatch.setattr("clients.manus.requests.get", http.get)

    client = make_client()
    resp = client.chat([Message(role="user", content="x")])

    # nothing saved; error recorded; both auth paths were attempted
    assert not resp.artifacts
    errors = resp.raw_response.get("artifact_errors", [])
    assert len(errors) == 1
    assert errors[0]["filename"] == "report.pdf"
    assert "login-redirect" in errors[0]["error"]
    assert http.download_calls == [(url, True), (url, False)]


# --------------------------------------------------------------------------
# Test 2c — a GENUINE HTML artifact (declared text/html) is NOT treated as login
# --------------------------------------------------------------------------
def test_download_genuine_html_artifact_not_login(monkeypatch):
    """When the attachment itself declares text/html, a 200 HTML body is the
    real artifact — the login-redirect heuristic must NOT fire."""
    url = "https://files.manus.ai/page.html"

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
    # captured on the first (with-key) attempt — no fallback needed
    assert http.download_calls == [(url, True)]
    assert resp.raw_response.get("artifact_auth") == {url: "with-key"}
