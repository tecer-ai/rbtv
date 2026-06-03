"""hypresent static server — stdlib only."""

import http.server
import json
import mimetypes
import pathlib
import sys
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_ROOT = (REPO_ROOT / "app").resolve()
RUNTIME_ROOT = (REPO_ROOT / "runtime").resolve()

# ---------------------------------------------------------------------------
# Mutable /doc/ root
# ---------------------------------------------------------------------------
_doc_root = {"path": None}


def set_doc_root(path):
    """Expose a setter so api.py can re-point the /doc/ root."""
    _doc_root["path"] = pathlib.Path(path).resolve() if path else None


# ---------------------------------------------------------------------------
# API handlers
# ---------------------------------------------------------------------------
# Import api after defining set_doc_root so api.py can register the callback.
# The try/except handles both "python server/server.py" (absolute import)
# and "python -m server.server" (relative import).
try:
    from . import api
except ImportError:
    import api

api.register_set_doc_root(set_doc_root)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    """Explicit routing for GET static files and POST API calls."""

    # -- helpers ------------------------------------------------------------

    def _send_json(self, status, data):
        """Write a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status, data, content_type):
        """Write a raw bytes response."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _guess_type(self, path: pathlib.Path):
        """Return Content-Type for *path*, overriding a few extensions."""
        suffix = path.suffix.lower()
        if suffix == ".js":
            return "text/javascript"
        if suffix == ".css":
            return "text/css"
        if suffix == ".json":
            return "application/json"
        guessed, _ = mimetypes.guess_type(str(path))
        return guessed or "application/octet-stream"

    def _serve_static(self, root: pathlib.Path, rel: str):
        """Safely serve a file under *root*."""
        rel = rel.strip("/")
        # Reject any '..' component to prevent directory traversal.
        if ".." in rel.split("/"):
            self._send_json(404, {"error": "Invalid path"})
            return

        target = (root / rel).resolve()

        # Ensure the resolved path is still inside *root*.
        try:
            target.relative_to(root)
        except ValueError:
            self._send_json(404, {"error": "Path traversal blocked"})
            return

        if target.is_dir():
            target = target / "index.html"

        if not target.exists() or not target.is_file():
            self._send_json(404, {"error": "File not found"})
            return

        content = target.read_bytes()
        ct = self._guess_type(target)
        self._send_bytes(200, content, ct)

    # -- GET ----------------------------------------------------------------

    def do_GET(self):
        try:
            path = unquote(self.path.split("?", 1)[0])

            if path.startswith("/app/"):
                self._serve_static(APP_ROOT, path[len("/app/"):])
            elif path.startswith("/runtime/"):
                self._serve_static(RUNTIME_ROOT, path[len("/runtime/"):])
            elif path.startswith("/doc/"):
                doc_root = _doc_root["path"]
                if doc_root is None:
                    self._send_json(404, {"error": "No document open"})
                    return
                self._serve_static(doc_root, path[len("/doc/"):])
            else:
                self._send_json(404, {"error": "Not found"})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    # -- POST ---------------------------------------------------------------

    def do_POST(self):
        try:
            path = unquote(self.path.split("?", 1)[0])
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body) if body else {}

            if path == "/api/open":
                status, resp = api.handle_open(payload)
                self._send_json(status, resp)
            elif path == "/api/save-as":
                status, resp = api.handle_save_as(payload)
                self._send_json(status, resp)
            else:
                self._send_json(404, {"error": "Not found"})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------
def run(host="127.0.0.1", port=8765):
    """Start the threaded HTTP server and block forever."""
    with http.server.ThreadingHTTPServer((host, port), Handler) as server:
        print(f"Serving on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    _host = "127.0.0.1"
    _port = 8765
    if len(sys.argv) > 1:
        _host = sys.argv[1]
    if len(sys.argv) > 2:
        _port = int(sys.argv[2])
    run(_host, _port)
