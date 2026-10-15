#!/usr/bin/env python3
"""The checks for asaas.py: `python3 test_asaas.py`, no framework, no network.

Every arm runs the real CLI as a subprocess inside a temporary installation,
against a local stub HTTP server (ASAAS_API_URL) that records each request and
answers only the paths a test declares. Keys are sentinels, never a real one.
"""

import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CLI = Path(__file__).resolve().parent / "asaas.py"
# The guard for the "$" bug: an Asaas key starts with "$", and a shell that
# sources .env expands "$aact_..." to nothing. The literal below must arrive
# byte for byte in the access_token header.
SENTINEL_KEY = "$aact_prod_SENTINEL$notreal"


class Stub(http.server.BaseHTTPRequestHandler):
    routes, seen = {}, []

    def _answer(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else ""
        url = urlparse(self.path)
        Stub.seen.append({"method": method, "path": url.path, "query": parse_qs(url.query),
                          "body": json.loads(body) if body else None,
                          "token": self.headers.get("access_token"),
                          "agent": self.headers.get("User-Agent")})
        status, payload = Stub.routes.get((method, url.path), (599, {"errors": [{"code": "undeclared", "description": url.path}]}))
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._answer("GET")

    def do_POST(self):
        self._answer("POST")

    def log_message(self, *a):
        pass


def setup():
    server = http.server.HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    home = Path(tempfile.mkdtemp())
    (home / ".rbtv" / "config" / "env").mkdir(parents=True)
    (home / ".rbtv" / "config" / "install.json").write_text("{}", encoding="utf-8")
    (home / ".rbtv" / "config" / "env" / ".env").write_text(f"OTHER=1\nASAAS_API_KEY={SENTINEL_KEY}\n", encoding="utf-8")
    work = home / "agents" / "sara"
    work.mkdir(parents=True)
    return server, home, work


def run(work, server, *args, env_key=None):
    env = {k: v for k, v in os.environ.items() if k != "ASAAS_API_KEY"}
    env["ASAAS_API_URL"] = f"http://127.0.0.1:{server.server_port}/v3"
    if env_key is not None:
        env["ASAAS_API_KEY"] = env_key
    p = subprocess.run([sys.executable, str(CLI), *args], cwd=work, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return p.returncode, p.stdout, p.stderr


FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
    if not cond:
        FAILS.append(name)


def main():
    server, home, work = setup()
    R = Stub.routes

    R[("GET", "/v3/finance/balance")] = (200, {"balance": 1234.5})
    Stub.seen.clear()
    code, out, err = run(work, server, "balance")
    check("balance prints the amount in reais", code == 0 and out.strip() == "Balance  R$ 1.234,50", out + err)
    check("the $-key from .env arrives literally", Stub.seen and Stub.seen[0]["token"] == SENTINEL_KEY, Stub.seen)
    check("a User-Agent is sent", Stub.seen and Stub.seen[0]["agent"] == "rbtv-asaas", Stub.seen)

    code, out, err = run(work, server, "--json", "balance")
    check("--json before the command gives one object", code == 0 and json.loads(out) == {"balance": 1234.5}, out)
    code, out, err = run(work, server, "balance", "--json")
    check("--json after the command gives one object", code == 0 and json.loads(out) == {"balance": 1234.5}, out)

    Stub.seen.clear()
    code, out, err = run(work, server, "balance", env_key="$aact_prod_FROMENV")
    check("the process environment wins over .env", Stub.seen and Stub.seen[0]["token"] == "$aact_prod_FROMENV", Stub.seen)

    R[("GET", "/v3/finance/balance")] = (401, {"errors": [{"code": "invalid_access_token", "description": "bad"}]})
    code, out, err = run(work, server, "balance")
    check("401 exits 1 with nothing on stdout", code == 1 and out == "" and "401" in err and "fix:" in err, out + err)
    check("the key never appears in stderr", SENTINEL_KEY not in err, err)

    outside = Path(tempfile.mkdtemp())
    env = {k: v for k, v in os.environ.items() if k != "ASAAS_API_KEY"}
    env["ASAAS_API_URL"] = f"http://127.0.0.1:{server.server_port}/v3"
    p = subprocess.run([sys.executable, str(CLI), "balance"], cwd=outside, env=env, capture_output=True, text=True, timeout=30)
    check("no key outside an installation: exit 1 naming the fix", p.returncode == 1 and "ASAAS_API_KEY" in p.stderr and p.stdout == "", p.stderr)

    R[("GET", "/v3/financialTransactions")] = (200, {"hasMore": True, "totalCount": 3, "data": [
        {"id": "ftn_1", "date": "2026-10-15", "value": -20.0, "balance": 30.0, "type": "ASAAS_DEBIT_CARD_REQUEST_FEE", "description": "Taxa"}]})
    Stub.seen.clear()
    code, out, err = run(work, server, "statement", "--from", "2026-10-01", "--to", "2026-10-15", "--limit", "1")
    q = Stub.seen[0]["query"] if Stub.seen else {}
    check("statement sends the date range and limit", q.get("startDate") == ["2026-10-01"] and q.get("finishDate") == ["2026-10-15"] and q.get("limit") == ["1"], q)
    check("statement shows the row and the next page", code == 0 and "-R$ 20,00" in out and "--offset 1" in out, out)
    code, out, err = run(work, server, "statement", "--from", "15/10/2026")
    check("a non-ISO date is refused before any call", code == 1 and "YYYY-MM-DD" in err, err)

    R[("GET", "/v3/pix/addressKeys/external")] = (200, {"key": "a@b.com", "type": "EMAIL",
        "owner": {"name": "BAYER GARAGE", "cpfCnpj": "**.123.456/0001-**"}, "financialInstitution": {"name": "Banco X"}})
    Stub.seen.clear()
    code, out, err = run(work, server, "pix", "lookup", "a@b.com")
    q = Stub.seen[0]["query"] if Stub.seen else {}
    check("lookup detects an email key", q.get("type") == ["EMAIL"] and q.get("key") == ["a@b.com"], q)
    check("lookup prints the owner", code == 0 and "BAYER GARAGE" in out, out)
    Stub.seen.clear()
    code, out, err = run(work, server, "pix", "lookup", "12345678901")
    check("11 digits are refused as ambiguous, with no call", code == 1 and "--type CPF" in err and not Stub.seen, err)
    Stub.seen.clear()
    code, out, err = run(work, server, "pix", "lookup", "123.456.789-01", "--type", "CPF")
    q = Stub.seen[0]["query"] if Stub.seen else {}
    check("a CPF is sent as digits only", q.get("key") == ["12345678901"] and q.get("type") == ["CPF"], q)

    R[("POST", "/v3/pix/qrCodes/decode")] = (200, {"value": 99.0, "totalValue": 99.0, "canBePaid": True,
        "receiver": {"name": "KENU", "cpfCnpj": "***.1"}})
    Stub.seen.clear()
    code, out, err = run(work, server, "pix", "decode", "00020126PAYLOAD")
    check("decode posts the payload", Stub.seen and Stub.seen[0]["body"] == {"payload": "00020126PAYLOAD"}, Stub.seen)
    check("decode prints amount and payable", code == 0 and "R$ 99,00" in out and "Payable   yes" in out, out)

    code, out, err = run(work, server, "pay")
    check("an unknown command exits 2", code == 2, err)

    server.shutdown()
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
