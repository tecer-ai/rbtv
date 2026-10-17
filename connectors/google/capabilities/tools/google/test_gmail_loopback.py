#!/usr/bin/env python3
"""Real gtools parsers against a loopback Gmail fixture. No live network."""
import base64, contextlib, datetime, io, json, os, pathlib, socket, sys, tempfile, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[3] / "repository"
SCRIPT_DIR = str(pathlib.Path(__file__).resolve().parent)
sys.path = [item for item in sys.path if item not in ("", SCRIPT_DIR)]
for site in (ROOT / ".venv" / "lib").glob("python*/site-packages"):
    sys.path.insert(0, str(site))
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import gtools, auth
from googleapiclient import discovery, discovery_cache
from google_auth_httplib2 import AuthorizedHttp
from httplib2 import Http

BASE = 1792195200
BODY = "Full owner request. " + ("Preserve this instruction. " * 40)
api = []
mode = "owner"

def message(i, full=False):
    sender = "other@example.com" if mode == "nonowner" else "owner@example.com"
    headers = [
        ("Delivered-To", "actual-agent@example.com"),
        ("Received", "from sender.example by mx.google.com with ESMTP id review"),
        ("Authentication-Results", "mx.google.com; dmarc=pass header.from=example.com; dkim=pass header.d=example.com"),
        ("From", sender),
        ("Date", datetime.datetime.fromtimestamp(BASE + i, datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")),
        ("Subject", "Review"),
    ]
    if mode == "missing":
        headers = [h for h in headers if h[0] != "Authentication-Results"]
    payload = {"headers": [{"name": k, "value": v} for k, v in headers], "mimeType": "text/plain"}
    if full:
        payload["body"] = {"data": base64.urlsafe_b64encode(BODY.encode()).decode()}
    return {"id": f"m{i}", "threadId": f"t{i}", "internalDate": str((BASE + i) * 1000),
            "snippet": "Full owner request. Preserve...", "labelIds": ["INBOX"], "payload": payload}

class Service(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return
    def handle_request(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")) or 0)
        api.append({"path": parsed.path, "query": query})
        path = parsed.path
        if path.endswith("/profile"):
            out = {"emailAddress": "actual-agent@example.com"}
        elif path.endswith("/messages"):
            rows = [{"id": f"m{i}", "threadId": f"t{i}"} for i in range(25, 0, -1)]
            offset = int(query.get("pageToken", ["0"])[0])
            size = int(query.get("maxResults", ["10"])[0])
            out = {"messages": rows[offset:offset + size]}
            if len(rows) > offset + size:
                out["nextPageToken"] = str(offset + size)
        elif "/messages/" in path:
            i = int(path.rsplit("/", 1)[1][1:])
            out = message(i, query.get("format", [""])[0] == "full")
        elif "/threads/" in path:
            out = {"id": "t1", "messages": [message(1, True)]}
        elif path.endswith("/drafts/send"):
            out = {"id": "sent-1", "threadId": "thread-sent-1", "labelIds": ["SENT"]}
        elif path.endswith("/drafts"):
            out = {"id": "draft-1", "message": {"id": "draft-message-1", "threadId": "thread-draft-1"}}
        else:
            out = {"error": path}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    do_GET = handle_request
    do_POST = handle_request

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    original = socket.socket.connect
    def local_only(sock, address):
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1"):
            raise RuntimeError("non-loopback connection refused")
        return original(sock, address)
    socket.socket.connect = local_only
    def build(api_name, version, credentials):
        document = json.loads(discovery_cache.get_static_doc(api_name, version))
        document["rootUrl"] = f"http://127.0.0.1:{server.server_port}/"
        document["baseUrl"] = document["rootUrl"] + document.get("servicePath", "")
        return discovery.build_from_document(document, http=AuthorizedHttp(credentials, http=Http(proxy_info=None)))
    auth.build = build
    def spawn(script, prog, args):
        target = ROOT / "scripts" / script
        sys.argv = [prog, *args]
        exec(compile(target.read_bytes(), str(target), "exec"), {"__name__": "__main__", "__file__": str(target)})
        return 0
    gtools.spawn = spawn
    failed = 0
    with tempfile.TemporaryDirectory(prefix="gmail-loopback-") as scratch:
        tmp = pathlib.Path(scratch)
        (tmp / "credentials").mkdir()
        (tmp / "credentials" / "token.json").write_text(json.dumps({
            "token": "fixture", "refresh_token": "fixture", "token_uri": "http://127.0.0.1/unused",
            "client_id": "fixture", "client_secret": "fixture", "expiry": "2099-01-01T00:00:00Z",
        }))
        cfg = tmp / "config.json"
        cfg.write_text(json.dumps({"accounts": {"review": {
            "email": "configured-agent@example.com", "display_name": "Review",
            "credentials_dir": str(tmp / "credentials"),
        }}, "scopes": ["https://www.googleapis.com/auth/gmail.modify"]}))
        os.environ["GOOGLE_TOOLS_CONFIG"] = str(cfg)
        def call(argv):
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    code = gtools.main(argv)
                except SystemExit as exc:
                    code = exc.code
            return code, stdout.getvalue(), stderr.getvalue()
        code, out, err = call(["--json", "gmail", "read", "--account", "review", "--query", "in:inbox"])
        if code == 0 or "unknown command '--json'" not in err:
            print("FAIL leading --json still accepted or not the grammar error", code, err)
            failed += 1
        else:
            print("PASS leading --json is rejected")
        code, out, err = call(["gmail", "read", "--account", "review", "--query", "in:inbox", "--verify-sender", "owner@example.com", "--limit", "100", "--json"])
        rows = json.loads(out)
        if code != 0 or len(rows) != 25 or not err.startswith("MAILBOX actual-agent@example.com"):
            print("FAIL search page", code, len(rows) if out.startswith("[") else out[:80], err[:80])
            failed += 1
        else:
            print("PASS search returns the full page and the authenticated mailbox")
        code, out, err = call(["gmail", "read", "--account", "review", "--message-id", "m25", "--verify-sender", "owner@example.com", "--json"])
        body = json.loads(out)
        if code != 0 or BODY not in body.get("body_plain", "") or not body.get("internalDate"):
            print("FAIL full body", code, body.get("body_plain", "")[:40])
            failed += 1
        else:
            print("PASS message read returns the full body and internalDate")
        code, out, err = call(["gmail", "send", "--account", "review", "--draft-id", "draft-1"])
        if code != 0 or "Message ID: sent-1" not in out or "Thread ID: thread-sent-1" not in out:
            print("FAIL send text", code, out)
            failed += 1
        else:
            print("PASS send prints Message ID and Thread ID")
    server.shutdown()
    print(f"gmail-loopback: {4 - failed} passed, {failed} failed")
    return failed

if __name__ == "__main__":
    sys.exit(main())
