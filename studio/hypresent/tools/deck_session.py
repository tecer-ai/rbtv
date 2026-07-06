"""Shared browser session for hypresent write commands."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


class DeckSessionError(RuntimeError):
    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return int(port)


def start_server(port: int) -> tuple[subprocess.Popen[Any], str]:
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=REPO,
        env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise DeckSessionError(f"hypresent server did not start on {port}")


def post_json(base: str, path: str, payload: dict[str, Any]) -> tuple[int, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def set_fake_dialog(base: str, path_or_none: str | None) -> tuple[int, Any]:
    return post_json(base, "/api/_test/set-dialog", {"path": path_or_none})


def doc_eval(page: Any, body: str) -> Any:
    return page.evaluate(
        """(body) => {
            const f = document.querySelector('iframe.doc-frame');
            const doc = f.contentDocument, win = f.contentWindow;
            const fn = new Function('doc','win', body);
            return fn(doc, win);
        }""",
        body,
    )


def find_thread(comments: list[dict[str, Any]], comment_id: str) -> dict[str, Any] | None:
    for thread in comments:
        if thread.get("id") == comment_id:
            return thread
    return None


def precheck_deck(src: Path) -> None:
    if not src.is_file():
        raise DeckSessionError(f"file not found: {src}")
    if "<section" not in src.read_text(encoding="utf-8"):
        raise DeckSessionError(
            "not a conforming hypresent deck — no <section> slides found. "
            "Hypresent only opens decks built from <section> blocks."
        )


class DeckSession:
    def __init__(self, src: Path, out: Path, author: str) -> None:
        self.src = src.resolve()
        self.out = out.resolve()
        self.author = author
        self.proc: subprocess.Popen[Any] | None = None
        self.base: str | None = None
        self.pw: Any = None
        self.browser: Any = None
        self.page: Any = None

    def __enter__(self) -> "DeckSession":
        try:
            self.proc, self.base = start_server(free_port())
            self.start_browser()
            self.open_deck()
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def start_browser(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise DeckSessionError("playwright is not installed in this environment.", code=3) from exc
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.add_init_script(
            "window.localStorage.setItem('hypresent-comment-author', %s);" % json.dumps(self.author)
        )
        self.page.goto(self.require_base() + "/app/")

    def require_base(self) -> str:
        if self.base is None:
            raise DeckSessionError("hypresent server is not running")
        return self.base

    def open_deck(self) -> None:
        set_fake_dialog(self.require_base(), os.fspath(self.src))
        self.page.click("#open-btn")
        self.page.wait_for_function(
            """() => { const f = document.querySelector('iframe.doc-frame');
                       return f && f.contentWindow && f.contentWindow.hyp; }""",
            timeout=20000,
        )

    def eval_doc(self, body: str) -> Any:
        return doc_eval(self.page, body)

    def read_comments(self) -> list[dict[str, Any]]:
        return self.eval_doc("return win.hyp.comments.toJson();")

    def wait_and_confirm(
        self,
        predicate: Callable[[list[dict[str, Any]]], bool],
        tries: int = 2,
        delay_ms: int = 400,
    ) -> list[dict[str, Any]] | None:
        for _ in range(tries):
            self.page.wait_for_timeout(delay_ms)
            comments = self.read_comments()
            if predicate(comments):
                return comments
        return None

    def post_command(self, command_type: str, payload: dict[str, Any]) -> None:
        self.page.evaluate(
            """(args) => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', type: args.type, payload: args.payload, id: 'tool-' + args.type },
                    location.origin);
            }""",
            {"type": command_type, "payload": payload},
        )

    def snapshot_hidden(self) -> list[bool]:
        return self.eval_doc("return [...doc.querySelectorAll('section')].map(s => s.hasAttribute('hidden'));")

    def restore_hidden(self, sections_hidden: list[bool]) -> None:
        self.eval_doc(
            "const want = " + json.dumps(sections_hidden) + ";"
            " const secs = doc.querySelectorAll('section');"
            " secs.forEach((s, i) => { if (want[i]) s.setAttribute('hidden', '');"
            " else s.removeAttribute('hidden'); });"
            " return true;"
        )

    def save(self) -> None:
        if self.out != self.src:
            set_fake_dialog(self.require_base(), os.fspath(self.out))
            self.page.click("#save-as-btn")
        else:
            self.page.click("#save-btn")
        self.page.wait_for_function(
            "() => document.getElementById('doc-state')?.textContent === 'Saved'",
            timeout=8000,
        )
        saved = self.out.read_text(encoding="utf-8")
        if 'id="hyp-comments"' not in saved:
            raise DeckSessionError("save completed but the saved file has no #hyp-comments island.")

    def add_comment(self, selector: str, body: str, agent: bool) -> dict[str, Any]:
        sections_hidden = self.snapshot_hidden()
        count = self.eval_doc(f"return doc.querySelectorAll({json.dumps(selector)}).length;")
        if count == 0:
            raise DeckSessionError(f"selector matched no element in the deck: {selector!r}")
        if count > 1:
            raise DeckSessionError(f"selector matched {count} elements — it must be unique: {selector!r}")

        markers_before = self.eval_doc("return doc.querySelectorAll('.hyp-comment-marker').length;")
        hyp_id = self.eval_doc(
            f"""
            let el = doc.querySelector({json.dumps(selector)});
            while (el && !el.getAttribute('data-hyp-id')) el = el.parentElement;
            return el ? el.getAttribute('data-hyp-id') : null;
        """
        )
        if not hyp_id:
            raise DeckSessionError(
                f"target is not commentable — no editable (data-hyp-id) element at or above {selector!r}."
            )
        self.post_command("select", {"hypId": hyp_id})
        self.page.wait_for_timeout(450)
        self.page.click("#comment-btn")
        composer = self.page.wait_for_selector(".hyp-composer-textarea", timeout=5000)
        if composer is None:
            raise DeckSessionError("comment composer did not open — the element may not be commentable.")

        if agent:
            self.page.check(".hyp-composer-agent input")
            self.page.focus(".hyp-composer-textarea")
        self.page.fill(".hyp-composer-textarea", body)
        self.page.keyboard.press("Control+Enter")
        self.page.wait_for_selector("#comment-threads .comment-thread", timeout=5000)
        self.page.wait_for_timeout(200)

        data = self.read_comments()
        if not data:
            raise DeckSessionError("no comment thread was created.")
        new = data[-1]
        markers_after = self.eval_doc("return doc.querySelectorAll('.hyp-comment-marker').length;")
        if markers_after <= markers_before:
            raise DeckSessionError(
                "the comment was created but rendered NO marker (loaded unanchored / invisible). "
                "Pick a more specific element selector."
            )

        self.restore_hidden(sections_hidden)
        self.save()
        return {
            "ok": True,
            "file": os.fspath(self.out),
            "comment_id": new.get("id"),
            "author": new.get("author"),
            "agentInstruction": bool(new.get("agentInstruction")),
            "anchor": new.get("anchor"),
            "anchored": True,
            "marker_rendered": True,
            "contextText": new.get("contextText"),
        }

    def reply(
        self,
        comment_id: str,
        reply_body: str | None,
        set_agent: bool,
        clear_agent: bool,
    ) -> dict[str, Any]:
        comments = self.read_comments()
        thread_before = find_thread(comments, comment_id)
        if thread_before is None:
            raise DeckSessionError(f"no comment thread with id {comment_id!r} in the deck")

        thread_count_before = len(comments)
        replies_before = len(thread_before.get("replies") or [])
        resolved_before = bool(thread_before.get("resolved"))
        agent_before = bool(thread_before.get("agentInstruction"))

        reply_added = False
        reply_author_out = None
        reply_body_out = None
        agent_instruction_out = agent_before

        if reply_body:
            if not reply_body.strip():
                raise DeckSessionError("--reply body must be non-empty")
            self.post_command(
                "reply-comment",
                {"commentId": comment_id, "body": reply_body, "author": self.author},
            )

            def reply_confirmed(next_comments: list[dict[str, Any]]) -> bool:
                thread = find_thread(next_comments, comment_id)
                if thread is None or len(next_comments) != thread_count_before:
                    return False
                replies = thread.get("replies") or []
                if len(replies) != replies_before + 1:
                    return False
                last = replies[-1]
                return (
                    last.get("author") == self.author
                    and last.get("body") == reply_body
                    and bool(thread.get("resolved")) == resolved_before
                )

            confirmed = self.wait_and_confirm(reply_confirmed)
            if confirmed is None:
                raise DeckSessionError(f"reply-comment command was not confirmed for thread {comment_id!r}")
            comments = confirmed
            thread_after = find_thread(comments, comment_id)
            last_reply = thread_after.get("replies")[-1] if thread_after else {}
            reply_added = True
            reply_author_out = last_reply.get("author")
            reply_body_out = last_reply.get("body")
            agent_instruction_out = bool(thread_after.get("agentInstruction")) if thread_after else False

        if set_agent or clear_agent:
            want_agent = bool(set_agent)
            self.post_command("tag-agent", {"commentId": comment_id, "agentInstruction": want_agent})

            def tag_confirmed(next_comments: list[dict[str, Any]]) -> bool:
                thread = find_thread(next_comments, comment_id)
                return thread is not None and bool(thread.get("agentInstruction")) == want_agent

            confirmed = self.wait_and_confirm(tag_confirmed)
            if confirmed is None:
                raise DeckSessionError(f"tag-agent command was not confirmed for thread {comment_id!r}")
            comments = confirmed
            thread_after = find_thread(comments, comment_id)
            agent_instruction_out = bool(thread_after.get("agentInstruction")) if thread_after else False

        self.save()
        thread_final = find_thread(comments, comment_id)
        return {
            "ok": True,
            "file": os.fspath(self.out),
            "comment_id": comment_id,
            "reply_added": reply_added,
            "reply_author": reply_author_out,
            "reply_body": reply_body_out,
            "agent_instruction": agent_instruction_out,
            "replies_count": len(thread_final.get("replies") or []) if thread_final else None,
            "thread_count": len(comments),
        }


def add_comment(
    file: str,
    selector: str,
    body: str,
    author: str,
    agent: bool,
    out: str | None,
) -> dict[str, Any]:
    src = Path(file).resolve()
    precheck_deck(src)
    out_path = Path(out).resolve() if out else src
    with DeckSession(src, out_path, author) as session:
        return session.add_comment(selector, body, agent)


def reply(
    file: str,
    comment_id: str,
    reply_body: str | None,
    author: str,
    set_agent: bool,
    clear_agent: bool,
    out: str | None,
) -> dict[str, Any]:
    if not reply_body and not set_agent and not clear_agent:
        raise DeckSessionError("at least one action is required: --reply, --set-agent, or --clear-agent")
    src = Path(file).resolve()
    precheck_deck(src)
    out_path = Path(out).resolve() if out else src
    with DeckSession(src, out_path, author) as session:
        return session.reply(comment_id, reply_body, set_agent, clear_agent)
