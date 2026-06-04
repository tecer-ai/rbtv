"""Shared helpers for hypresent Playwright e2e suites (stdlib + playwright only)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))   # hypresent/
FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction.html")


def start_server(port, test_dialog=False):
    env = dict(os.environ)
    if test_dialog:
        env["HYP_TEST_DIALOG"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "server/server.py", "127.0.0.1", str(port)],
        cwd=REPO, env=env,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 6
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"server did not start on {port}")


def stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def copy_fixture():
    """Copy the sample into a fresh tempdir; return the absolute path of the copy."""
    d = tempfile.mkdtemp()
    dst = os.path.join(d, "deck.html")
    shutil.copy(FIXTURE, dst)
    return dst


def post_json(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def set_fake_dialog(base, path_or_none):
    """Install the server-side fake dialog launcher (requires HYP_TEST_DIALOG=1)."""
    return post_json(base, "/api/_test/set-dialog", {"path": path_or_none})


def preset_author(page):
    """Seed localStorage so the comment author prompt never blocks tests."""
    page.add_init_script("window.localStorage.setItem('hypresent-comment-author','Tester');")


def open_via_dialog_ui(page, base, file_path):
    """Set the fake dialog to file_path and click the Open button; wait for runtime ready."""
    set_fake_dialog(base, file_path)
    page.click("#open-btn")
    wait_runtime_ready(page)


def wait_runtime_ready(page, timeout=8000):
    """Wait until the iframe document has the runtime (window.hyp) loaded."""
    page.wait_for_function(
        """() => {
            const f = document.querySelector('iframe.doc-frame');
            return f && f.contentWindow && f.contentWindow.hyp;
        }""",
        timeout=timeout,
    )


def doc_eval(page, expr):
    """Evaluate an expression against the iframe document. `expr` is a JS function body
    receiving (doc, win) and returning a JSON-serializable value."""
    return page.evaluate(
        """(body) => {
            const f = document.querySelector('iframe.doc-frame');
            const doc = f.contentDocument, win = f.contentWindow;
            const fn = new Function('doc','win', body);
            return fn(doc, win);
        }""",
        expr,
    )
