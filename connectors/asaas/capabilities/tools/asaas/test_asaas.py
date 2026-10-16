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
        ctype, data = payload if isinstance(payload, tuple) else ("application/json", json.dumps(payload).encode("utf-8"))
        self.send_response(status)
        self.send_header("Content-Type", ctype)
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


def js(text):
    """stdout as JSON, or None: a check of a command's JSON fails by name instead of stopping the run."""
    try:
        return json.loads(text)
    except ValueError:
        return None


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
    check("decode prints amount and payable, and the command that pays it", code == 0 and "R$ 99,00" in out
          and "Payable   yes: pay qr --from asaas pays it through Ignite's payment gate" in out.splitlines(), out)

    receipt_checks(server, work, R)

    code, out, err = run(work, server, "transfer")
    check("an unknown command exits 2", code == 2, err)

    retired_pay_checks(server)
    pay_checks(server, home, work, R)

    server.shutdown()
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


def receipt_checks(server, work, R):
    site = {"ASAAS_RECEIPT_URL": f"http://127.0.0.1:{server.server_port}"}
    link = f"http://127.0.0.1:{server.server_port}/comprovantes/h/ABC"
    pdf = b"%PDF-1.4 receipt"
    R[("GET", "/comprovantes/h/ABC")] = (200, ("text/html", b'<a href="/transactionReceipt/pdf/42">PDF</a>'))
    R[("GET", "/transactionReceipt/pdf/42")] = (200, ("application/pdf", pdf))
    code, out, err = run(work, server, "--json", "receipt", link, extra=site)
    saved = work / "receipt-42.pdf"
    check("receipt follows the page's PDF link and saves the PDF", code == 0 and saved.read_bytes() == pdf
          and json.loads(out)["bytes"] == len(pdf), out + err)
    code, out, err = run(work, server, "receipt", link, extra=site)
    check("receipt never writes over a file", code == 1 and "already exists" in err and saved.read_bytes() == pdf, out + err)
    code, out, err = run(work, server, "receipt", "https://evil.example/comprovantes/h/ABC", "--out", "x.pdf", extra=site)
    check("receipt refuses a link outside Asaas, with no file", code == 1 and "receipt link starts with" in err
          and not (work / "x.pdf").exists(), out + err)
    R[("GET", "/transactionReceipt/pdf/42")] = (200, ("text/html", b"<html>login</html>"))
    code, out, err = run(work, server, "receipt", link, "--out", "y.pdf", extra=site)
    check("receipt refuses what is not a PDF, with no file", code == 1 and "did not return a PDF" in err
          and not (work / "y.pdf").exists(), out + err)
    R[("GET", "/comprovantes/h/ABC")] = (200, ("text/html", b"<html>no link</html>"))
    code, out, err = run(work, server, "receipt", link, "--out", "z.pdf", extra=site)
    check("receipt names the page change when the PDF link is gone", code == 1 and "no PDF link" in err, out + err)


MOVED_WHY = ("paying goes through the payments port command, which holds the gate call for every bank; "
             "asaas keeps reading, cancelling, receipts and the waking service's verbs")
PAY_SENTENCE = ("Ignite's waking service's verbs: resolve, execute, status (request on stdin). "
                "An agent pays with pay pix|qr|bill|recharge --from asaas …")


def moved(verb, fix):
    return [f"asaas: pay {verb} moved to the pay command", f"  why: {MOVED_WHY}", f"  fix: {fix}"]


def retired_home():
    home = Path(tempfile.mkdtemp())
    (home / ".rbtv" / "config" / "env").mkdir(parents=True)
    (home / ".rbtv" / "config" / "install.json").write_text("{}", encoding="utf-8")
    (home / ".rbtv" / "config" / "env" / ".env").write_text(f"ASAAS_API_KEY={SENTINEL_KEY}\n", encoding="utf-8")
    work = home / "work"
    work.mkdir()
    return home, work


def retired_pay_checks(server):
    """The four paying verbs refuse. They do not resolve a recipient or record a request."""
    home, work = retired_home()
    spec_fix = 'pay pix --from asaas --to pia@example.com --amount 18,00 --note "Aula"   (pay -h)'
    Stub.seen.clear()
    code, out, err = run(work, server, "pay", "pix", "pia@example.com", "18,00", "--note", "Aula")
    check("asaas pay pix pia@example.com 18,00 --note Aula refuses with the spec's three lines",
          code == 2 and out == "" and err.splitlines() == moved("pix", spec_fix) and not Stub.seen,
          f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "--json", "pay", "pix", "pia@example.com", "18,00", "--note", "Aula")
    check("pay pix --json refuses with the same three lines and no stdout",
          code == 2 and out == "" and err.splitlines() == moved("pix", spec_fix), f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "qr", "00020126580014br.gov.bcb.pix", "--amount", "35,00", "--note", "Pão")
    check("pay qr refuses and names pay qr --from asaas",
          code == 2 and out == "" and err.splitlines() == moved(
              "qr", 'pay qr --from asaas --code 00020126580014br.gov.bcb.pix --amount 35,00 --note "Pão"   (pay -h)'),
          f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "bill", "23793.38128 60012.341071", "--note", "Luz")
    check("pay bill refuses and names pay bill --from asaas",
          code == 2 and out == "" and err.splitlines() == moved(
              "bill", 'pay bill --from asaas --line "23793.38128 60012.341071" --note "Luz"   (pay -h)'),
          f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "recharge", "11912345678", "20")
    check("pay recharge refuses and names pay recharge --from asaas",
          code == 2 and out == "" and err.splitlines() == moved(
              "recharge", "pay recharge --from asaas --number 11912345678 --amount 20   (pay -h)"),
          f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "pix", "pia@example.com", "18,00", "--note=Aula")
    check("pay pix accepts --note= as the old parser did",
          code == 2 and out == "" and err.splitlines() == moved("pix", spec_fix), f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "pix", "-h")
    check("pay pix -h refuses instead of printing the old usage",
          code == 2 and out == "" and err.splitlines()[0] == "asaas: pay pix moved to the pay command", f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "pix", "11912345678", "20", "--note", "x", "--type", "PHONE")
    check("pay pix keeps --type in the fix line",
          code == 2 and err.splitlines()[-1] == '  fix: pay pix --from asaas --to 11912345678 --amount 20 --note "x" --type PHONE   (pay -h)',
          err)
    turn = ignite_installation(home)
    before = len(Stub.seen)
    code, out, err = run(work, server, "pay", "pix", "pia@example.com", "18,00", "--note", "Aula", extra=turn)
    check("pay pix inside a turn refuses and records nothing",
          code == 2 and out == "" and err.splitlines() == moved("pix", spec_fix)
          and len(Stub.seen) == before and not ledger(home, "P-0001"), f"exit {code}\n{out}{err}")
    code, out, err = run(work, server, "pay", "-h")
    listed = [ln.strip().split()[0] for ln in out.splitlines()
              if ln.strip().split()[:1] and ln.strip().split()[0] in ("pix", "qr", "bill", "recharge", "resolve", "execute", "status")]
    check("asaas pay -h matches the spec sentence and lists only the waking service verbs",
          code == 0 and PAY_SENTENCE in out and listed == ["resolve", "execute", "status"], out)
    for verb in ("resolve", "execute", "status"):
        code, out, err = run(work, server, "pay", verb, "-h")
        check(f"pay {verb} -h still answers", code == 0 and "Ignite's waking service" in out, out + err)
    code, out, err = run(work, server, "-h")
    check("asaas -h keeps the reads and does not tell an agent to pay with asaas pay pix",
          code == 0 and all(name in out for name in ("balance", "statement", "pix", "payments", "payment", "cancel", "receipt"))
          and "asaas pay pix" not in out and "pay pix KEY" not in out, out)


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
    R[("POST", "/v3/pix/qrCodes/decode")] = (200, QR_DECODED)
    service_commands(server, home, work, R, turn, line)


def seed_reads(home):
    """Rows for the read and cancel verbs. The paying verbs no longer record a request."""
    key = json.dumps(CONVERSATION)
    gate_do(home, f"""
const who = {{ name: 'KENU EXAMPLE SILVA', key: 'kenu@example.com', keyType: 'EMAIL', document: '***.123.456-**', bank: 'Nubank' }};
const ask = (method, recipient, amount, note) => gate.request({{
  agent: 'sara', conversationKey: {key}, connector: 'asaas', method, recipient, amountCents: amount, feeCents: 0, note }});
gate.saveSettings({{ mode: 'case_by_case', limits: {{}} }});
ask('pix', who, 9900, 'Owed to Kenu');
ask('pix', who, 1800, 'Aula');
gate.saveSettings({{ mode: 'automatic', limits: {{ week: 1500000 }} }});
ask('pix', who, 100, 'Coffee');
if (!gate.claim('P-0003')) throw new Error('claim P-0003');
gate.sent('P-0003', {{ connectorId: 'tr_5', connectorStatus: 'PENDING' }});
ask('qr', {{ name: 'PADARIA PAO BOM', key: '000201', keyType: 'QR' }}, 3500, 'Bread');
if (!gate.claim('P-0004')) throw new Error('claim P-0004');
gate.sent('P-0004', {{ connectorId: 'pq_7' }});
""")


def pay_commands(server, home, work, R, turn, line):
    seed_reads(home)
    code, out, err = run(work, server, "payments", "--state", "pending", extra=turn)
    check("payments lists this agent's requests", code == 0 and out.splitlines()[0].startswith("P-0002  pending")
          and "P-0001  pending" in out, out + err)
    code, out, err = run(work, server, "payment", "P-0003", extra=turn)
    check("payment shows the state and the Asaas id", code == 0 and "State       sent: approved by rule (within the limits)" in out
          and "Asaas id    tr_5 (PENDING)" in out, out + err)
    code, out, err = run(work, server, "cancel", "P-0002", extra=turn)
    check("cancel withdraws a pending request", code == 0 and out.strip() == "Cancelled   P-0002: withdrawn before the owner decided"
          and ledger(home, "P-0002").get("state") == "cancelled", out + err)
    code, out, err = run(work, server, "cancel", "P-0002", extra=turn)
    check("cancel refuses a request with nothing to cancel", code == 1 and "P-0002 is cancelled: nothing to cancel" in err, out + err)
    code, out, err = run(work, server, "payment", "P-0999", extra=turn)
    check("an unknown id names the gate's reason and this tool's fix", code == 1 and err.splitlines() == [
        "asaas: Ignite's payment gate: unknown payment request: P-0999",
        "  why: nothing was recorded or changed",
        "  fix: asaas payments lists this agent's request ids; an id it does not list is another agent's or does not exist"], err)
    code, out, err = run(work, server, "payments", "--state", "failed", extra=turn)
    check("an empty filtered list names the filter", code == 0 and out.strip() == "No failed payment requests.", out + err)
    R[("DELETE", "/v3/transfers/tr_5/cancel")] = (200, {"id": "tr_5", "status": "CANCELLED"})
    code, out, err = run(work, server, "cancel", "P-0003", extra=turn)
    check("cancel of a sent payment cancels it at Asaas", code == 0 and out.splitlines()[0] == "Cancelled   P-0003 at Asaas (tr_5): CANCELLED", out + err)
    before = len(Stub.seen)
    code, out, err = run(work, server, "cancel", "P-0004", extra=turn)
    check("cancel refuses a sent QR payment, naming who can cancel it", code == 1 and err.splitlines() == [
        "asaas: P-0004 is a qr payment Asaas already has", "  why: this tool cancels Pix key transfers and bills only",
        "  fix: ask the owner to cancel it in the Asaas app while Asaas allows it"] and len(Stub.seen) == before, err)


QR = "00020126580014br.gov.bcb.pix0136a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d520400005303986540535.005802BR5907PADARIA6009SAO PAULO62070503***6304ABCD"
QR_DECODED = {"value": 35.0, "totalValue": 35.0, "canBePaid": True, "canBePaidWithDifferentValue": False,
              "receiver": {"name": "PADARIA PAO BOM", "cpfCnpj": "**.222.333/0001-**", "ispbName": "Banco Z"}}


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
        "provider_id": "tr_2", "status": "DONE", "final": True, "ok": True, "receipt_url": "https://r.example/2", "reason": None}, out + err)
    R[("GET", "/v3/transfers/tr_2")] = (200, {"id": "tr_2", "status": "FAILED", "failReason": "Chave inexistente"})
    code, out, err = run(work, server, "--json", "pay", "status", "P-0002", stdin=json.dumps({**request, "state": "sent", "provider_id": "tr_2"}))
    check("pay status calls FAILED final and not ok, with Asaas's reason", code == 0 and json.loads(out) == {
        "provider_id": "tr_2", "status": "FAILED", "final": True, "ok": False, "receipt_url": None, "reason": "Chave inexistente"}, out + err)
    service_new_methods(server, home, work, R, line)


def service_new_methods(server, home, work, R, line):
    base = {"provider": "asaas", "state": "approved", "fee_cents": 0, "details": {}}
    pix = {**base, "id": "P-0002", "method": "pix", "amount_cents": 7000, "note": "Lunch",
           "recipient": {"name": "SOMEONE ELSE", "key": "kenu@example.com", "key_type": "EMAIL"}}
    qr = {**base, "id": "P-0007", "method": "qr", "amount_cents": 3500, "note": "Bread", "recipient": {"name": "PADARIA", "key": QR, "key_type": "QR"}}
    bill = {**base, "id": "P-0006", "method": "bill", "amount_cents": 2000, "fee_cents": 199, "note": "Electricity",
            "recipient": {"name": "ENEL", "key": line, "key_type": None}}
    top = {**base, "id": "P-0009", "method": "recharge", "amount_cents": 2000, "note": None, "recipient": {"key": "11912345678", "key_type": "PHONE"}}

    Stub.seen.clear()
    resolved = {}
    for req in (pix, qr, bill, top):
        code, out, err = run(work, server, "--json", "pay", "resolve", req["id"], stdin=json.dumps({**req, "state": "pending"}))
        resolved[req["method"]] = json.loads(out) if code == 0 else out + err
    check("pay resolve reads a Pix key's owner from Asaas, not from the request", resolved["pix"] == {
        "name": "KENU EXAMPLE SILVA", "document": "***.123.456-**", "bank": "Nubank", "key": "kenu@example.com", "key_type": "EMAIL",
        "amount_cents": None, "fee_cents": None}, resolved["pix"])
    check("pay resolve decodes a QR code, with the amount it fixes", resolved["qr"] == {
        "name": "PADARIA PAO BOM", "document": "**.222.333/0001-**", "bank": "Banco Z", "key": QR, "key_type": "QR",
        "amount_cents": 3500, "fee_cents": None}, resolved["qr"])
    check("pay resolve simulates a bill, with its amount and fee", resolved["bill"] == {
        "name": "ENEL DISTRIBUICAO", "document": "**.123.456/0001-**", "bank": "237", "key": line, "key_type": None,
        "amount_cents": 2000, "fee_cents": 199}, resolved["bill"])
    check("pay resolve gives a top-up's phone with no call", resolved["recharge"] == {
        "name": None, "document": None, "bank": None, "key": "11912345678", "key_type": "PHONE", "amount_cents": None, "fee_cents": None},
          resolved["recharge"])
    check("pay resolve calls only lookup, decode and simulate", [(x["method"], x["path"]) for x in Stub.seen] == [
        ("GET", "/v3/pix/addressKeys/external"), ("POST", "/v3/pix/qrCodes/decode"), ("POST", "/v3/bill/simulate")], Stub.seen)

    # Phase 2 of the connector architecture: a gate row says connector, connector_id and connector_status; the
    # older spelling is still read, and `pay resolve draft` resolves for the pay port command before any request.
    renamed = {k: v for k, v in pix.items() if k != "provider"}
    renamed["connector"] = "asaas"
    code, out, err = run(work, server, "--json", "pay", "resolve", "P-0002", stdin=json.dumps({**renamed, "state": "pending"}))
    check("pay resolve reads a request that says connector instead of provider", code == 0 and json.loads(out)["name"] == "KENU EXAMPLE SILVA", out + err)
    code, out, err = run(work, server, "--json", "pay", "resolve", "P-0002", stdin=json.dumps({**renamed, "connector": "nubank", "state": "pending"}))
    check("pay resolve refuses a request of another connector, in the connector's word", code == 1 and "the id or the connector differs" in err, out + err)
    Stub.seen.clear()
    drafts = {}
    for req in (pix, qr, bill, top):
        draft = {"connector": "asaas", "method": req["method"], "recipient": {"key": req["recipient"]["key"], "key_type": req["recipient"].get("key_type")},
                 "amount_cents": req["amount_cents"], "note": req["note"]}
        code, out, err = run(work, server, "--json", "pay", "resolve", "draft", stdin=json.dumps(draft))
        drafts[req["method"]] = json.loads(out) if code == 0 else out + err
    check("pay resolve draft resolves a Pix key: the owner, no amount, nothing fixed", drafts["pix"] == {
        "recipient": {"name": "KENU EXAMPLE SILVA", "document": "***.123.456-**", "bank": "Nubank", "key": "kenu@example.com", "key_type": "EMAIL"},
        "amount_cents": None, "fee_cents": None, "changeable": None, "details": {}}, drafts["pix"])
    check("pay resolve draft decodes a QR code: the fixed amount and whether it may change", drafts["qr"] == {
        "recipient": {"name": "PADARIA PAO BOM", "document": "**.222.333/0001-**", "bank": "Banco Z", "key": QR, "key_type": "QR"},
        "amount_cents": 3500, "fee_cents": None, "changeable": False, "details": {}}, drafts["qr"])
    check("pay resolve draft simulates a bill: amount, fee and details", drafts["bill"] == {
        "recipient": {"name": "ENEL DISTRIBUICAO", "document": "**.123.456/0001-**", "bank": "237", "key": line, "key_type": None},
        "amount_cents": 2000, "fee_cents": 199, "changeable": False,
        "details": {"due_date": "2026-10-20", "company": "ENEL", "minimum_schedule_date": "2026-10-15"}}, drafts["bill"])
    check("pay resolve draft gives a top-up's phone as 11 digits with no call", drafts["recharge"] == {
        "recipient": {"name": None, "document": None, "bank": None, "key": "11912345678", "key_type": "PHONE"},
        "amount_cents": None, "fee_cents": None, "changeable": None, "details": {}}, drafts["recharge"])
    check("pay resolve draft calls only lookup, decode and simulate", [(x["method"], x["path"]) for x in Stub.seen] == [
        ("GET", "/v3/pix/addressKeys/external"), ("POST", "/v3/pix/qrCodes/decode"), ("POST", "/v3/bill/simulate")], Stub.seen)
    code, out, err = run(work, server, "--json", "pay", "resolve", "draft", stdin=json.dumps({"connector": "nubank", "method": "pix", "recipient": {"key": "a@b.c"}}))
    check("pay resolve draft refuses a draft for another connector", code == 1 and "stdin is not a draft for asaas" in err and out == "", out + err)
    code, out, err = run(work, server, "pay", "resolve", "draft", stdin="not json")
    check("pay resolve draft refuses an empty stdin, naming who runs it", code == 1 and "no draft on stdin" in err and "pay command" in err, out + err)

    R[("POST", "/v3/pix/qrCodes/pay")] = (200, {"id": "pq_1", "status": "AWAITING_REQUEST", "transactionReceiptUrl": None})
    R[("POST", "/v3/mobilePhoneRecharges")] = (200, {"id": "rc_1", "value": 20, "phoneNumber": "11912345678", "status": "PENDING"})
    Stub.seen.clear()
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0007", stdin=json.dumps(qr))
    check("pay execute pays a QR code with its payload and amount", code == 0 and Stub.seen and Stub.seen[0]["path"] == "/v3/pix/qrCodes/pay"
          and Stub.seen[0]["body"] == {"qrCode": {"payload": QR}, "value": 35.0, "description": "Bread"}
          and json.loads(out) == {"provider_id": "pq_1", "status": "AWAITING_REQUEST", "receipt_url": None}, out + err + str(Stub.seen))
    Stub.seen.clear()
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0009", stdin=json.dumps(top))
    check("pay execute tops up the phone with the amount", code == 0 and Stub.seen and Stub.seen[0]["path"] == "/v3/mobilePhoneRecharges"
          and Stub.seen[0]["body"] == {"value": 20.0, "phoneNumber": "11912345678"} and json.loads(out)["provider_id"] == "rc_1", out + err)

    R[("POST", "/v3/transfers")] = (400, {"errors": [{"code": "invalid_value", "description": "Saldo insuficiente"}]})
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0002", stdin=json.dumps(pix))
    check("pay execute says nothing was created when Asaas refuses the transfer", code == 1 and js(out) == {
        "created": False, "reason": "Asaas answered HTTP 400 on POST /transfers: invalid_value: Saldo insuficiente"}, out + err)
    R[("POST", "/v3/transfers")] = (502, {"errors": [{"code": "bad_gateway", "description": "upstream"}]})
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0002", stdin=json.dumps(pix))
    check("pay execute claims nothing when Asaas's answer leaves the outcome unknown", code == 1 and out == ""
          and "HTTP 502" in err, out + err)
    code, out, err = run(work, server, "--json", "pay", "execute", "P-0002", stdin=json.dumps({**pix, "state": "pending"}))
    check("pay execute says nothing was created for a request it will not send", code == 1 and js(out) == {
        "created": False, "reason": "P-0002 is pending: only an approved request is sent"}, out + err)

    R[("GET", "/v3/pix/transactions/pq_1")] = (200, {"id": "pq_1", "status": "DONE", "transactionReceiptUrl": "https://r.example/q"})
    code, out, err = run(work, server, "--json", "pay", "status", "P-0007", stdin=json.dumps({**qr, "state": "sent", "provider_id": "pq_1"}))
    check("pay status reads a QR payment as a Pix transaction", code == 0 and json.loads(out) == {
        "provider_id": "pq_1", "status": "DONE", "final": True, "ok": True, "receipt_url": "https://r.example/q", "reason": None}, out + err)
    code, out, err = run(work, server, "--json", "pay", "status", "P-0007", stdin=json.dumps({**{k: v for k, v in qr.items() if k != "provider"}, "connector": "asaas", "state": "sent", "connector_id": "pq_1"}))
    check("pay status reads connector_id from a renamed row", code == 0 and json.loads(out)["status"] == "DONE", out + err)
    R[("GET", "/v3/mobilePhoneRecharges/rc_1")] = (200, {"id": "rc_1", "status": "CANCELLED"})
    code, out, err = run(work, server, "--json", "pay", "status", "P-0009", stdin=json.dumps({**top, "state": "uncertain", "provider_id": "rc_1"}))
    check("pay status reads a top-up and calls CANCELLED final and not ok", code == 0 and json.loads(out) == {
        "provider_id": "rc_1", "status": "CANCELLED", "final": True, "ok": False, "receipt_url": None, "reason": None}, out + err)


if __name__ == "__main__":
    sys.exit(main())
