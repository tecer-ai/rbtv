import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FIXTURE = os.path.join(REPO, "tecer-gsmm-introduction.html")
PORT = 8789
BASE = f"http://127.0.0.1:{PORT}"
NO_OPEN_PORT = 8790   # dedicated fresh-server port for the HTTP no-open test (U-SAVE-2, R15)


def _post_base(base, path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def _post(path, payload):
    return _post_base(BASE, path, payload)


def _start_server(port):
    proc = subprocess.Popen([sys.executable, "server/server.py", "127.0.0.1", str(port)], cwd=REPO)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base + "/app/", timeout=1):
                return proc, base
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"server did not start on {port}")


def _stop_server(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


class SaveRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Fail loud if the canonical fixture is absent (gitignored per U10a; never skip-green, R07).
        if not os.path.exists(FIXTURE):
            raise AssertionError(
                f"Required fixture missing: {FIXTURE} (gitignored per U10a; restore it locally before running tests)"
            )
        cls.proc, _ = _start_server(PORT)

    @classmethod
    def tearDownClass(cls):
        _stop_server(cls.proc)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _copy(self, name="a.html"):
        dst = os.path.join(self.tmp, name)
        shutil.copy(FIXTURE, dst)
        return dst

    def test_open_then_save(self):                            # U-SAVE-1
        f = self._copy()
        s, _ = _post("/api/open", {"path": f})
        self.assertEqual(s, 200)
        s, resp = _post("/api/save", {"html": "<edited/>"})
        self.assertEqual(s, 200)
        self.assertTrue(resp.get("ok"))
        with open(f, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "<edited/>")

    def test_save_no_open_on_fresh_server(self):              # U-SAVE-2 (R15, HTTP-level)
        # A genuinely fresh server that has NEVER received /api/open must return
        # no_open_file over HTTP. Use a dedicated port so this is order-independent.
        proc, base = _start_server(NO_OPEN_PORT)
        try:
            status, resp = _post_base(base, "/api/save", {"html": "x"})
            self.assertEqual(status, 200)
            self.assertTrue(resp.get("no_open_file"))
        finally:
            _stop_server(proc)

    def test_open_b_then_save_targets_b(self):                # U-SAVE-3
        a = self._copy("a.html")
        b = self._copy("b.html")
        _post("/api/open", {"path": a})
        _post("/api/open", {"path": b})
        _post("/api/save", {"html": "<b/>"})
        with open(b, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "<b/>")
        with open(a, encoding="utf-8") as fh:
            self.assertNotEqual(fh.read(), "<b/>")


if __name__ == "__main__":
    unittest.main()
