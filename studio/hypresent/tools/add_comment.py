#!/usr/bin/env python3
"""add_comment.py — add a hypresent review comment to an HTML deck.

The agent supplies ONLY a CSS selector (the element to comment on) and the
comment text. This tool drives the REAL hypresent runtime headlessly to:
  1. open the deck in the app,
  2. select the element matched by the selector,
  3. add the comment through the real comment UI (the runtime computes the
     anchor — no hand-math, no anchor code to read), and
  4. save through the app's own save handler (so the #hyp-comments island and
     any agent-instruction head block are always valid — never hand-written).

Why this shape: anchor computation and island serialization stay inside the
runtime that normally produces valid files, so a comment can never load
"unanchored" (invisible) and the file can never be written in a form hypresent
cannot parse. The agent never reads runtime code.

Usage:
  python tools/add_comment.py --file deck.html --selector "#screen-overview .slide-title" \
      --body "Tighten this heading" --author "Vivian (designer agent)" [--agent] [--out new.html]

Exit 0 on success (prints the new comment id + resolved anchor). Non-zero with a
clear message on any failure (selector not unique, element not commentable,
comment loaded unanchored, save failed).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))   # hypresent/


# --- minimal app-driving helpers (kept self-contained; mirror tests/e2e) ---

def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(port):
    env = dict(os.environ)
    env["HYP_TEST_DIALOG"] = "1"   # enables the fake-dialog seam used to open/save by path
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=REPO, env=env,
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
    raise RuntimeError(f"hypresent server did not start on {port}")


def _post_json(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def _set_fake_dialog(base, path_or_none):
    return _post_json(base, "/api/_test/set-dialog", {"path": path_or_none})


def _doc_eval(page, body):
    """Run a JS function body (receiving doc, win) against the deck iframe."""
    return page.evaluate(
        """(body) => {
            const f = document.querySelector('iframe.doc-frame');
            const doc = f.contentDocument, win = f.contentWindow;
            const fn = new Function('doc','win', body);
            return fn(doc, win);
        }""",
        body,
    )


def _fail(msg, code=2):
    print(f"add_comment: ERROR — {msg}", file=sys.stderr)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(description="Add a hypresent review comment to an HTML deck.")
    ap.add_argument("--file", required=True, help="Path to the HTML deck to comment on.")
    ap.add_argument("--selector", required=True,
                    help="CSS selector for the target element (must match exactly one element in the deck).")
    ap.add_argument("--body", required=True, help="The comment text.")
    ap.add_argument("--author", default="Agent",
                    help="Comment author identity, e.g. 'Vivian (designer agent)'.")
    ap.add_argument("--agent", action="store_true",
                    help="Mark the comment as an agent instruction (adds data-hyp-agent + head block).")
    ap.add_argument("--out", default=None,
                    help="Optional output path. Default: save in place (overwrites --file).")
    args = ap.parse_args()

    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        _fail(f"file not found: {src}")
    out = os.path.abspath(args.out) if args.out else src

    # Conforming-deck precheck (the server rejects non-<section> HTML on load).
    with open(src, encoding="utf-8") as f:
        if "<section" not in f.read():
            _fail("not a conforming hypresent deck — no <section> slides found. "
                  "Hypresent only opens decks built from <section> blocks.")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _fail("playwright is not installed in this environment.", code=3)

    proc, base = _start_server(_free_port())
    pw = browser = None
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        # Seed the author so the runtime never prompts.
        page.add_init_script(
            "window.localStorage.setItem('hypresent-comment-author', %s);" % json.dumps(args.author)
        )
        page.goto(base + "/app/")

        # Open the deck by path via the fake-dialog seam, wait for the runtime.
        _set_fake_dialog(base, src)
        page.click("#open-btn")
        page.wait_for_function(
            """() => { const f = document.querySelector('iframe.doc-frame');
                       return f && f.contentWindow && f.contentWindow.hyp; }""",
            timeout=20000,
        )

        # Snapshot original page visibility. Paged decks hide inactive screens via
        # [hidden]; commenting reveals the target's screen, so we restore this exact
        # state before saving — a reveal must never leak into the saved file.
        sections_hidden = _doc_eval(
            page, "return [...doc.querySelectorAll('section')].map(s => s.hasAttribute('hidden'));")

        # Selector must resolve to exactly one element inside the deck.
        count = _doc_eval(page, f"return doc.querySelectorAll({json.dumps(args.selector)}).length;")
        if count == 0:
            _fail(f"selector matched no element in the deck: {args.selector!r}")
        if count > 1:
            _fail(f"selector matched {count} elements — it must be unique: {args.selector!r}")

        # Count rendered comment markers BEFORE — the visible in-document indicators.
        markers_before = _doc_eval(page, "return doc.querySelectorAll('.hyp-comment-marker').length;")

        # Resolve the target to its selectable unit (nearest data-hyp-id ancestor-or-self),
        # then select it through the runtime's OWN 'select' command. That command runs
        # revealPagedAncestors first — navigating to a hidden/inactive screen via the deck's
        # own nav — so a Playwright actionability click (which times out on hidden elements)
        # is never needed. Works for visible elements too (reveal is a no-op).
        hyp_id = _doc_eval(page, f"""
            let el = doc.querySelector({json.dumps(args.selector)});
            while (el && !el.getAttribute('data-hyp-id')) el = el.parentElement;
            return el ? el.getAttribute('data-hyp-id') : null;
        """)
        if not hyp_id:
            _fail(f"target is not commentable — no editable (data-hyp-id) element at or above {args.selector!r}.")
        page.evaluate(
            """(hypId) => {
                const f = document.querySelector('iframe.doc-frame');
                f.contentWindow.postMessage(
                    { source: 'hyp', kind: 'command', type: 'select', payload: { hypId }, id: 'tool-select' },
                    location.origin);
            }""",
            hyp_id,
        )
        page.wait_for_timeout(450)   # reveal (page nav) + select + scroll-into-view
        page.click("#comment-btn")
        composer = page.wait_for_selector(".hyp-composer-textarea", timeout=5000)
        if composer is None:
            _fail("comment composer did not open — the element may not be commentable.")

        if args.agent:
            page.check(".hyp-composer-agent input")
            page.focus(".hyp-composer-textarea")
        page.fill(".hyp-composer-textarea", args.body)
        page.keyboard.press("Control+Enter")
        page.wait_for_selector("#comment-threads .comment-thread", timeout=5000)
        page.wait_for_timeout(200)

        # Read back the thread the runtime just created (toJson = the persisted island).
        data = _doc_eval(page, "return win.hyp.comments.toJson();")
        if not data:
            _fail("no comment thread was created.")
        new = data[-1]

        # Confirm a NEW visible marker rendered — proof the comment anchored (an
        # unanchored thread renders no marker and would be invisible to the owner).
        markers_after = _doc_eval(page, "return doc.querySelectorAll('.hyp-comment-marker').length;")
        if markers_after <= markers_before:
            _fail("the comment was created but rendered NO marker (loaded unanchored / invisible). "
                  "Pick a more specific element selector.")

        # Restore original page visibility before serializing, so commenting on a
        # hidden screen never changes which screen the saved deck opens on.
        _doc_eval(
            page,
            "const want = " + json.dumps(sections_hidden) + ";"
            " const secs = doc.querySelectorAll('section');"
            " secs.forEach((s, i) => { if (want[i]) s.setAttribute('hidden', '');"
            " else s.removeAttribute('hidden'); });"
            " return true;",
        )

        # Save through the app's own handler.
        if out != src:
            _set_fake_dialog(base, out)
            page.click("#save-as-btn")
        else:
            page.click("#save-btn")
        page.wait_for_function(
            "() => document.getElementById('doc-state')?.textContent === 'Saved'",
            timeout=8000,
        )

        # Confirm the saved file carries the island with the new comment.
        with open(out, encoding="utf-8") as f:
            saved = f.read()
        if 'id="hyp-comments"' not in saved:
            _fail("save completed but the saved file has no #hyp-comments island.")

        print(json.dumps({
            "ok": True,
            "file": out,
            "comment_id": new.get("id"),
            "author": new.get("author"),
            "agentInstruction": bool(new.get("agentInstruction")),
            "anchor": new.get("anchor"),
            "anchored": True,
            "marker_rendered": True,
            "contextText": new.get("contextText"),
        }, indent=2))
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
