#!/usr/bin/env python3
"""The checks for asaas.py: `python3 test_asaas.py`, no framework, no network.

Every arm runs the real CLI as a subprocess inside a temporary installation,
against a local stub HTTP server (ASAAS_API_URL) that records each request and
answers only the paths a test declares. Keys are sentinels, never a real one.
The pay arms ask Ignite's real payment gate (ASAAS_IGNITE runs this repository's
Ignite cli.js with node) in a temporary installation; a test stands in for
Ignite's waking service where one is needed. No money moves.
"""

import http.server
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CLI = Path(__file__).resolve().parent / "asaas.py"
IGNITE = Path(__file__).resolve().parents[5] / "core" / "ignite" / "capabilities" / "tools" / "ignite"
CONVERSATION = "T1:C1:1.1"
# The endpoints that move money. Only `pay execute` may call one.
PAYING = {("POST", "/v3/transfers"), ("POST", "/v3/bill"), ("POST", "/v3/pix/qrCodes/pay"), ("POST", "/v3/mobilePhoneRecharges")}
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

    def do_DELETE(self):
        self._answer("DELETE")

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


AMBIENT = ("ASAAS_API_KEY", "ASAAS_IGNITE", "ASAAS_GATE_WAIT", "RBTV_AGENT_HOME", "IGNITE_CONVERSATION")


def run(work, server, *args, env_key=None, extra=None, stdin=None):
    env = {k: v for k, v in os.environ.items() if k not in AMBIENT}
    env["ASAAS_API_URL"] = f"http://127.0.0.1:{server.server_port}/v3"
    if env_key is not None:
        env["ASAAS_API_KEY"] = env_key
    env.update(extra or {})
    p = subprocess.run([sys.executable, str(CLI), *args], cwd=work, env=env, input=stdin,
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return p.returncode, p.stdout, p.stderr


def node(script):
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True, timeout=30)


def ignite_installation(home):
    """Ignite config with a payments section, the agent sara and its conversation."""
    cfg = home / ".rbtv" / "config" / "ignite"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.json").write_text(json.dumps({
        "slack": {"team": "T1", "botUserId": "UBOT", "ownerUserId": "UOWNER", "appTokenEnv": "A", "botTokenEnv": "B",
                  "ownerTokenEnv": "C", "stoolsWorkspace": "w"},
        "tools": {"cast": "cast", "stools": "stools", "audio": "audio"}, "routes": {"C1": "sara"}, "payments": {}}), encoding="utf-8")
    agent = home / ".rbtv" / "agents" / "sara"
    node(f"""const {{ Store }} = require({json.dumps(str(IGNITE / 'store.js'))});
const s = new Store({json.dumps(str(agent / 'runtime' / 'ignite' / 'state.sqlite'))});
s.upsertConversation({{ key: {json.dumps(CONVERSATION)}, agent: 'sara', workspace: 'T1', channel: 'C1', rootTs: '1.1', activated: true }});
s.close();""")
    return {"RBTV_AGENT_HOME": str(agent), "IGNITE_CONVERSATION": CONVERSATION, "ASAAS_IGNITE": str(IGNITE / "cli.js"),
            "ASAAS_GATE_WAIT": "0"}


def gate_do(home, body):
    """Runs JavaScript with `gate`, the installation's payment gate, standing in for the owner or the service."""
    node(f"""const {{ Gate }} = require({json.dumps(str(IGNITE / 'payments.js'))});
const gate = new Gate({{ workspace: {json.dumps(str(home))} }});
{body}
gate.close();""")


def ledger(home, rid):
    path = home / ".rbtv" / "runtime" / "ignite" / "payments.sqlite"
    if not path.is_file():
        return {}
    db = sqlite3.connect(str(path))
    try:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM payments WHERE id=?", (rid,)).fetchone()
        return dict(row) if row else {}
    finally:
        db.close()


def paying(seen):
    return [(x["method"], x["path"]) for x in seen if (x["method"], x["path"]) in PAYING]


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
    check("decode prints amount and payable, and that pay does not pay QR codes", code == 0 and "R$ 99,00" in out
          and "Payable   yes at Asaas; asaas pay does not pay QR codes in this version" in out.splitlines(), out)

    code, out, err = run(work, server, "transfer")
    check("an unknown command exits 2", code == 2, err)

    pay_checks(server, home, work, R)

    server.shutdown()
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


def pay_checks(server, home, work, R):
    turn = ignite_installation(home)
    R[("GET", "/v3/pix/addressKeys/external")] = (200, {"key": "kenu@example.com", "type": "EMAIL",
        "owner": {"name": "KENU EXAMPLE SILVA", "cpfCnpj": "***.123.456-**"}, "financialInstitution": {"name": "Nubank"}})
    line = "23793381286001234107143000012345890460000002000"
    R[("POST", "/v3/bill/simulate")] = (200, {"minimumScheduleDate": "2026-10-15", "fee": 1.99, "bankSlipInfo": {
        "identificationField": line, "value": 20.0, "dueDate": "2026-10-20", "companyName": "ENEL",
        "beneficiaryName": "ENEL DISTRIBUICAO", "beneficiaryCpfCnpj": "**.123.456/0001-**", "bank": "237"}})
    Stub.seen.clear()
    try:
        pay_commands(server, home, work, R, turn, line)
    finally:
        check("no pay command called a paying endpoint", paying(Stub.seen) == [], paying(Stub.seen))
    service_commands(server, home, work, R, turn, line)


def pay_commands(server, home, work, R, turn, line):
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "99", "--note", "Owed to Kenu")
    check("pay outside a turn is refused before any call", code == 1 and "inside an Ignite turn" in err and not Stub.seen, out + err)
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "99.999", "--note", "x", extra=turn)
    check("a malformed amount exits 2 before any call", code == 2 and "not an amount in reais" in err and not Stub.seen, err)
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "1", "--note", "x" * 141, extra=turn)
    check("a note over 140 characters exits 2", code == 2 and not Stub.seen, err)
    code, out, err = run(work, server, "pay", "bill", "1234", "--note", "x", extra=turn)
    check("a bill line that is not 47 or 48 digits exits 2", code == 2 and not Stub.seen, err)
    code, out, err = run(work, server, "pay", "pix", "00020126580014br.gov.bcb.pix0136a1b2", "35", "--note", "Bread", extra=turn)
    check("a QR code given as a key is refused as a QR code, before any call", code == 1 and not Stub.seen
          and "asaas: this is a Pix QR code (copy and paste), not a Pix key" in err and "fix: ask the owner to pay it" in err, err)

    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "99", "--note", "Owed to Kenu", extra=turn)
    check("off: the gate refuses and pay exits 1", code == 1 and out.splitlines() == [
        "Recipient   KENU EXAMPLE SILVA · ***.123.456-** · Nubank",
        "Amount      R$ 99,00",
        "State       refused: payments are off",
        "Request     P-0001"], out + err)
    row = ledger(home, "P-0001")
    check("the gate recorded the looked-up recipient and the agent's conversation",
          row and row["recipient_key"] == "kenu@example.com" and row["recipient_key_type"] == "EMAIL"
          and row["agent"] == "sara" and row["conversation_key"] == CONVERSATION and row["amount_cents"] == 9900, row)

    gate_do(home, "gate.saveSettings({ mode: 'automatic', limits: { week: 15000 } });")
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "70,00", "--note", "Lunch", extra=turn)
    check("automatic within the limit: approved, Ignite sends it", code == 0 and out.splitlines()[2:] == [
        "State       approved: Ignite is sending it",
        "Request     P-0002, the outcome arrives in this conversation",
        "Next        asaas payment P-0002 shows when it is sent"], out + err)
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "99.00", "--note", "Owed to Kenu", extra=turn)
    check("over the weekly limit: the specification's example, then the next step, exit 0", code == 0 and out.splitlines() == [
        "Recipient   KENU EXAMPLE SILVA · ***.123.456-** · Nubank",
        "Amount      R$ 99,00",
        "State       pending: over the weekly limit (R$ 80,00 left of R$ 150,00)",
        "Request     P-0003, sent to the owner for approval",
        "Next        end this turn waiting_workers: Ignite wakes this conversation with the owner's decision; asaas payment P-0003 shows it meanwhile"], out + err)
    code, out, err = run(work, server, "--json", "pay", "pix", "kenu@example.com", "99", "--note", "Again", extra=turn)
    body = json.loads(out) if code == 0 else {}
    check("--json gives the gate's request as fixed fields", body.get("id") == "P-0004" and body.get("state") == "pending"
          and body.get("reason") == "over the weekly limit (R$ 80,00 left of R$ 150,00)", out + err)

    def service():
        for _ in range(200):
            row = ledger(home, "P-0005")
            if row.get("state") == "approved":
                gate_do(home, "gate.claim('P-0005'); gate.sent('P-0005', { providerId: 'tr_5', providerStatus: 'PENDING' });")
                return
            time.sleep(0.05)
    helper = threading.Thread(target=service)
    helper.start()
    code, out, err = run(work, server, "pay", "pix", "kenu@example.com", "1", "--note", "Coffee", extra={**turn, "ASAAS_GATE_WAIT": "10"})
    helper.join()
    check("pay waits for Ignite to send an approved payment and prints it sent", code == 0 and out.splitlines()[2:] == [
        "State       sent: approved by rule (within the limits)",
        "Request     P-0005, Asaas id tr_5"], out + err)

    code, out, err = run(work, server, "pay", "bill", line[:5] + "." + line[5:], "--note", "Electricity", extra=turn)
    sim = [x for x in Stub.seen if x["path"] == "/v3/bill/simulate"]
    row = ledger(home, "P-0006")
    check("pay bill simulates first and asks the gate for the amount plus the fee",
          code == 0 and sim and sim[-1]["body"] == {"identificationField": line}
          and out.splitlines()[:2] == ["Recipient   ENEL DISTRIBUICAO · **.123.456/0001-** · 237", "Amount      R$ 20,00 + fee R$ 1,99"]
          and row.get("amount_cents") == 2000 and row.get("fee_cents") == 199 and row.get("recipient_key") == line and row.get("method") == "bill", out + err)


    code, out, err = run(work, server, "payments", "--state", "pending", extra=turn)
    check("payments lists this agent's requests", code == 0 and out.splitlines()[0].startswith("P-0004  pending")
          and "P-0003  pending" in out, out + err)
    code, out, err = run(work, server, "payment", "P-0005", extra=turn)
    check("payment shows the state and the Asaas id", code == 0 and "State       sent: approved by rule (within the limits)" in out
          and "Asaas id    tr_5 (PENDING)" in out, out + err)
    code, out, err = run(work, server, "cancel", "P-0004", extra=turn)
    check("cancel withdraws a pending request", code == 0 and out.strip() == "Cancelled   P-0004: withdrawn before the owner decided"
          and ledger(home, "P-0004").get("state") == "cancelled", out + err)
    code, out, err = run(work, server, "cancel", "P-0004", extra=turn)
    check("cancel refuses a request with nothing to cancel", code == 1 and "P-0004 is cancelled: nothing to cancel" in err, out + err)
    code, out, err = run(work, server, "payment", "P-0999", extra=turn)
    check("an unknown id names the gate's reason and this tool's fix", code == 1 and err.splitlines() == [
        "asaas: Ignite's payment gate: unknown payment request: P-0999",
        "  why: nothing was recorded or changed",
        "  fix: asaas payments lists this agent's request ids; an id it does not list is another agent's or does not exist"], err)
    code, out, err = run(work, server, "payments", "--state", "failed", extra=turn)
    check("an empty filtered list names the filter", code == 0 and out.strip() == "No failed payment requests.", out + err)
    R[("DELETE", "/v3/transfers/tr_5/cancel")] = (200, {"id": "tr_5", "status": "CANCELLED"})
    code, out, err = run(work, server, "cancel", "P-0005", extra=turn)
    check("cancel of a sent payment cancels it at Asaas", code == 0 and out.splitlines()[0] == "Cancelled   P-0005 at Asaas (tr_5): CANCELLED", out + err)


def service_commands(server, home, work, R, turn, line):

    R[("POST", "/v3/transfers")] = (200, {"id": "tr_2", "status": "PENDING", "transactionReceiptUrl": None})
    Stub.seen.clear()
    request = {"id": "P-0002", "provider": "asaas", "method": "pix", "state": "approved", "amount_cents": 7000, "fee_cents": 0,
               "recipient": {"name": "KENU EXAMPLE SILVA", "key": "kenu@example.com", "key_type": "EMAIL"}, "note": "Lunch"}
    code, out, err = run(work, server, "pay", "execute", "P-0001", stdin=json.dumps(request))
    check("pay execute refuses a request whose id differs, with no call", code == 1 and not Stub.seen, out + err)
    code, out, err = run(work, server, "pay", "execute", "P-0002", stdin=json.dumps({**request, "state": "pending"}))
    check("pay execute refuses a request that is not approved, with no call", code == 1 and "only an approved request is sent" in err and not Stub.seen, out + err)
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0002", stdin=json.dumps(request))
    sent = Stub.seen[0] if Stub.seen else {}
    check("pay execute sends the exact fields with the request id as externalReference",
          code == 0 and (sent.get("method"), sent.get("path")) == ("POST", "/v3/transfers") and sent.get("body") == {
              "value": 70.0, "pixAddressKey": "kenu@example.com", "pixAddressKeyType": "EMAIL",
              "description": "Lunch", "externalReference": "P-0002"}
          and json.loads(out) == {"provider_id": "tr_2", "status": "PENDING", "receipt_url": None}, out + err + str(Stub.seen))
    R[("POST", "/v3/bill")] = (200, {"id": 623471, "status": "PENDING"})
    Stub.seen.clear()
    bill = {**request, "id": "P-0006", "method": "bill", "amount_cents": 2000, "fee_cents": 199, "note": "Electricity",
            "recipient": {"name": "ENEL", "key": line, "key_type": None}}
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0006", stdin=json.dumps(bill))
    check("pay execute pays a bill by its line with the request id as externalReference",
          code == 0 and Stub.seen and Stub.seen[0]["path"] == "/v3/bill" and Stub.seen[0]["body"] == {
              "identificationField": line, "description": "Electricity", "externalReference": "P-0006"}
          and json.loads(out)["provider_id"] == "623471", out + err)
    R[("GET", "/v3/transfers/tr_2")] = (200, {"id": "tr_2", "status": "DONE", "transactionReceiptUrl": "https://r.example/2"})
    code, out, err = run(work, server, "--json", "pay", "status", "P-0002", stdin=json.dumps({**request, "state": "sent", "provider_id": "tr_2"}))
    check("pay status reads the operation and calls DONE final", code == 0 and json.loads(out) == {
        "status": "DONE", "final": True, "ok": True, "receipt_url": "https://r.example/2", "reason": None}, out + err)
    R[("GET", "/v3/transfers/tr_2")] = (200, {"id": "tr_2", "status": "FAILED", "failReason": "Chave inexistente"})
    code, out, err = run(work, server, "--json", "pay", "status", "P-0002", stdin=json.dumps({**request, "state": "sent", "provider_id": "tr_2"}))
    check("pay status calls FAILED final and not ok, with Asaas's reason", code == 0 and json.loads(out) == {
        "status": "FAILED", "final": True, "ok": False, "receipt_url": None, "reason": "Chave inexistente"}, out + err)


if __name__ == "__main__":
    sys.exit(main())
