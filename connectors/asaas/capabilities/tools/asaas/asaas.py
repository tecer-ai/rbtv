#!/usr/bin/env python3
"""asaas — an Asaas bank account from one command, for agents.

Reads: balance, statement, Pix key lookup and Pix QR code decode, and saves a
payment receipt as PDF.
Pays only through Ignite's payment gate: `pay pix`, `pay qr`, `pay bill` and
`pay recharge` resolve the recipient, record a request with `ignite payment
request`, and print the gate's answer. They never call a paying endpoint. The
waking service runs the rest with the request on stdin: `pay resolve` reads the
recipient again before the owner sees it (`pay resolve draft` does the same for
the `pay` port command before any request exists), and `pay execute` alone calls
a paying endpoint (POST /transfers, /bill, /pix/qrCodes/pay, /mobilePhoneRecharges). A
transfer and a bill carry the request id as externalReference; a QR payment and
a top-up take none, so Ignite records the operation id `pay execute` prints.
Asaas then asks Ignite's withdrawal validation, which approves only that request
(its half for Asaas is lib/withdrawal-validation.js, which Ignite loads).
A gate row names its connector as `connector`, `connector_id` and
`connector_status`; the older spelling `provider*` is still read.

Key: $ASAAS_API_KEY from the process environment first, then the line
ASAAS_API_KEY=... of the installation's .rbtv/config/env/.env, read literally:
an Asaas key starts with "$", so a shell that sources the file expands it away.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROG = "asaas"
KEY_ENV = "ASAAS_API_KEY"
API_URL_ENV = "ASAAS_API_URL"          # test hook: points the tool at a stub server
API = os.environ.get(API_URL_ENV, "https://api.asaas.com/v3").rstrip("/")
USER_AGENT = "rbtv-asaas"              # required for accounts created after 2024-06-13
INSTALL_RECORD_REL = Path(".rbtv") / "config" / "install.json"
ENV_FILE_REL = Path(".rbtv") / "config" / "env" / ".env"
TIMEOUT = 20
RECEIPT_URL_ENV = "ASAAS_RECEIPT_URL"  # test hook: points receipt downloads at a stub server
RECEIPT_SITE = os.environ.get(RECEIPT_URL_ENV, "https://www.asaas.com").rstrip("/")
# The receipt page's own download link; Asaas documents no receipt-PDF endpoint.
RECEIPT_PDF_RE = re.compile(r'href="(/transactionReceipt/pdf/[0-9]+)"')
REQUEST_ID_RE = re.compile(r"P-\d+\Z")
IGNITE_ENV = "ASAAS_IGNITE"            # test hook: path of Ignite's cli.js, run with node, in place of `ignite`
GATE_WAIT_ENV = "ASAAS_GATE_WAIT"      # seconds `pay` waits for Ignite to send an approved payment (default 30)
CONNECTOR = "asaas"
NOTE_MAX = 140
QR_MAX = 2000
UNKNOWN_FIX = f"{PROG} payments lists this agent's request ids; an id it does not list is another agent's or does not exist"
TRANSFER_FINAL = {"DONE": True, "CANCELLED": False, "FAILED": False}
BILL_FINAL = {"PAID": True, "CANCELLED": False, "FAILED": False, "REFUNDED": False}
QR_FINAL = {"DONE": True, "REFUSED": False, "ERROR": False, "CANCELLED": False}
RECHARGE_FINAL = {"CONFIRMED": True, "CANCELLED": False, "REFUNDED": False, "FAILED": False}

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2

PIX_KEY_TYPES = ("CPF", "CNPJ", "EMAIL", "PHONE", "EVP")
EVP_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z", re.I)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class Refusal(Exception):
    """created: False when no operation can exist (Asaas answered an error, or no paying call was made);
    None when it is unknown (no answer, a server error)."""
    def __init__(self, what, why, fix, created=None):
        super().__init__(what)
        self.what, self.why, self.fix, self.created = what, why, fix, created


def fail(err):
    print(f"{PROG}: {err.what}", file=sys.stderr)
    print(f"  why: {err.why}", file=sys.stderr)
    print(f"  fix: {err.fix}", file=sys.stderr)
    return EXIT_FAILED


# ───────────────────────────────────────────────────────────── key

def env_file(start=None):
    folder = Path(start or Path.cwd()).resolve()
    for p in (folder, *folder.parents):
        if (p / INSTALL_RECORD_REL).is_file():
            return p / ENV_FILE_REL
    return None


def api_key():
    key = os.environ.get(KEY_ENV, "").strip()
    if key:
        return key
    path = env_file()
    if path and path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?" + KEY_ENV + r"\s*=\s*(.*?)\s*$", line)
            if m:
                value = m.group(1)
                if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
                    value = value[1:-1]
                if value:
                    return value
    where = f"{path}" if path else "no rbtv installation above this folder"
    raise Refusal("no Asaas API key",
                  f"${KEY_ENV} is unset and {where} holds no {KEY_ENV} line",
                  f"add a line {KEY_ENV}=<key> to .rbtv/config/env/.env of the installation", created=False)


# ───────────────────────────────────────────────────────────── HTTP

def call(method, path, query=None, body=None):
    url = API + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "access_token": api_key(), "User-Agent": USER_AGENT,
        "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        detail = asaas_errors(raw) or raw.strip()[:300] or "no body"
        answered = False if e.code < 500 else None
        if e.code == 401:
            raise Refusal("Asaas refused the key (401)", detail,
                          f"check {KEY_ENV}: a production key starts $aact_prod_, and an unused key is disabled after 3 months",
                          created=answered)
        if e.code == 429:
            raise Refusal("Asaas rate limit (429)", detail, "wait and run the same command again later", created=answered)
        raise Refusal(f"Asaas answered HTTP {e.code} on {method} {path}", detail,
                      "correct the input named above, or run again if Asaas was unavailable", created=answered)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Refusal(f"could not reach Asaas ({API})", str(getattr(e, "reason", e)),
                      "check the network and run the same command again")
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        raise Refusal("Asaas returned something that is not JSON", raw[:200], "run again; report it if it persists")


def asaas_errors(raw):
    try:
        errors = json.loads(raw).get("errors") or []
        return "; ".join(f"{x.get('code')}: {x.get('description')}" for x in errors)
    except (ValueError, AttributeError):
        return ""


# ───────────────────────────────────────────────────────────── formatting

def brl(value):
    if value is None:
        return "-"
    sign = "-" if value < 0 else ""
    whole, cents = f"{abs(value):,.2f}".split(".")
    return f"{sign}R$ {whole.replace(',', '.')},{cents}"


def brl_cents(cents):
    return "-" if cents is None else brl(cents / 100)


def out(args, payload, text_lines):
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print("\n".join(text_lines))


# ───────────────────────────────────────────────────────────── commands

def cmd_balance(args):
    data = call("GET", "/finance/balance")
    balance = data.get("balance")
    out(args, {"balance": balance}, [f"Balance  {brl(balance)}"])


def cmd_statement(args):
    for name in ("from_", "to"):
        value = getattr(args, name)
        if value and not DATE_RE.match(value):
            raise Refusal(f"--{name.rstrip('_')} {value} is not a date", "dates are YYYY-MM-DD",
                          f"{PROG} statement --from 2026-10-01 --to 2026-10-15")
    data = call("GET", "/financialTransactions", {
        "startDate": args.from_, "finishDate": args.to, "limit": args.limit,
        "offset": args.offset, "order": "desc"})
    rows = [{"id": t.get("id"), "date": t.get("date"), "value": t.get("value"),
             "balance": t.get("balance"), "type": t.get("type"),
             "description": t.get("description")} for t in data.get("data", [])]
    payload = {"transactions": rows, "has_more": bool(data.get("hasMore")),
               "total": data.get("totalCount"), "offset": args.offset}
    lines = [f"{r['date']}  {brl(r['value']):>14}  balance {brl(r['balance']):>12}  {r['type']}  {r['description'] or ''}"
             for r in rows] or ["No transactions in this range."]
    if payload["has_more"]:
        lines.append(f"More: {PROG} statement --offset {args.offset + len(rows)}"
                     + (f" --from {args.from_}" if args.from_ else "") + (f" --to {args.to}" if args.to else ""))
    out(args, payload, lines)


def pix_key_type(key, given):
    if given:
        return given
    k = key.strip()
    if "@" in k:
        return "EMAIL"
    if k.startswith("+"):
        return "PHONE"
    if EVP_RE.match(k):
        return "EVP"
    digits = re.sub(r"\D", "", k)
    if len(digits) == 14:
        return "CNPJ"
    if len(digits) == 11:
        raise Refusal(f"{key} could be a CPF or a phone number", "both have 11 digits",
                      f"{PROG} pix lookup {key} --type CPF   (or --type PHONE)")
    raise Refusal(f"cannot tell the type of Pix key {key}",
                  "it is not an email, +phone, random key (EVP), CPF or CNPJ",
                  f"{PROG} pix lookup KEY --type {'|'.join(PIX_KEY_TYPES)}")


def pix_owner(key, given_type):
    """The Pix key's owner as Asaas names it: name, masked document, bank, and the key in Asaas's form."""
    ktype = pix_key_type(key, given_type)
    query_key = re.sub(r"\D", "", key) if ktype in ("CPF", "CNPJ") else key.strip()
    data = call("GET", "/pix/addressKeys/external", {"type": ktype, "key": query_key})
    owner = data.get("owner") or {}
    inst = data.get("financialInstitution") or {}
    return {"name": owner.get("name"), "key": data.get("key") or query_key, "key_type": data.get("type") or ktype,
            "document": owner.get("cpfCnpj"), "bank": inst.get("name") or data.get("ispbName")}


def cmd_pix_lookup(args):
    owner = pix_owner(args.key, args.type)
    payload = {"key": owner["key"], "type": owner["key_type"], "owner_name": owner["name"],
               "owner_document": owner["document"], "bank": owner["bank"]}
    out(args, payload, [f"Owner     {payload['owner_name']}",
                        f"Document  {payload['owner_document']}",
                        f"Bank      {payload['bank']}",
                        f"Key       {payload['key']} ({payload['type']})"])


def cmd_pix_decode(args):
    data = call("POST", "/pix/qrCodes/decode", body={"payload": args.payload})
    receiver = data.get("receiver") or {}
    payload = {"value": data.get("value"), "total_value": data.get("totalValue"),
               "receiver_name": receiver.get("name"), "receiver_document": receiver.get("cpfCnpj"),
               "can_be_paid": data.get("canBePaid"), "cannot_be_paid_reason": data.get("cannotBePaidReason"),
               "can_change_value": data.get("canBePaidWithDifferentValue")}
    payable = ("yes: asaas pay qr pays it through Ignite's payment gate" if payload["can_be_paid"]
               else f"no: {payload['cannot_be_paid_reason']}")
    lines = [f"Receiver  {payload['receiver_name']}  {payload['receiver_document'] or ''}".rstrip(),
             f"Amount    {brl(payload['total_value'] if payload['total_value'] is not None else payload['value'])}",
             f"Payable   {payable}"]
    out(args, payload, lines)


# ───────────────────────────────────────────────────────────── payment gate

def amount_cents(text):
    m = re.match(r"(\d{1,9})(?:[.,](\d{1,2}))?\Z", str(text).strip())
    if not m or int(m.group(1) + (m.group(2) or "0").ljust(2, "0")) == 0:
        raise argparse.ArgumentTypeError(f"{text!r} is not an amount in reais, like 99 or 99,90")
    return int(m.group(1)) * 100 + int((m.group(2) or "0").ljust(2, "0"))


def note_text(text):
    value = str(text).strip()
    if not value or len(value) > NOTE_MAX or "\n" in value:
        raise argparse.ArgumentTypeError(f"the note must be one line of 1 to {NOTE_MAX} characters")
    return value


def bill_line(text):
    digits = re.sub(r"\D", "", str(text))
    if len(digits) not in (47, 48):
        raise argparse.ArgumentTypeError("the bill's digitable line (linha digitável) has 47 or 48 digits; "
                                         "a 44-digit barcode number (código de barras) is not accepted: copy the digitable line printed above it")
    return digits


def qr_payload(text):
    value = str(text).strip()
    if not value.startswith("000201") or len(value) > QR_MAX or "\n" in value:
        raise argparse.ArgumentTypeError("a Pix QR code's copy-and-paste text is one line that starts with 000201")
    return value


def phone_number(text):
    digits = re.sub(r"\D", "", str(text))
    if len(digits) == 13 and digits.startswith("55"):
        digits = digits[2:]
    if len(digits) != 11:
        raise argparse.ArgumentTypeError("a mobile number has 11 digits with its area code, like 11912345678 or \"11 91234-5678\" "
                                         "(quoted when it has spaces; +55 optional)")
    return digits


def field(row, *names):
    """The first of the named fields a gate row carries: `connector_id` or, from an older Ignite, `provider_id`."""
    for name in names:
        if row.get(name) is not None:
            return row.get(name)
    return None


def gate(*args, stdin=None, fix=None):
    """Runs `ignite --json payment ...`; returns its JSON. Ignite refusing is a Refusal with the caller's fix."""
    hook = os.environ.get(IGNITE_ENV)
    if hook:
        command = [shutil.which("node") or "node", hook]
    else:
        found = shutil.which("ignite")
        if not found:
            raise Refusal("the ignite command is not on PATH", "asaas pays only through Ignite's payment gate",
                          "run asaas pay inside an Ignite agent's turn")
        command = [found]
    try:
        p = subprocess.run([*command, "--json", "payment", *args], input=stdin, capture_output=True,
                           text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refusal("could not run Ignite's payment gate", str(e), "run the same command again; tell the owner if it persists")
    if p.returncode != 0:
        lines = [ln for ln in (p.stderr or p.stdout).strip().splitlines() if ln.strip()]
        raise Refusal(f"Ignite's payment gate: {lines[0] if lines else f'exit {p.returncode}'}",
                      "nothing was recorded or changed", fix or f"{PROG} payments lists this agent's requests")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        raise Refusal("Ignite's payment gate answered something that is not JSON", p.stdout[:200], "tell the owner")


def in_turn():
    if not os.environ.get("IGNITE_CONVERSATION"):
        raise Refusal("asaas pay runs inside an Ignite turn", "IGNITE_CONVERSATION is not set, so no conversation can be woken with the outcome",
                      "pay from an agent's turn; a person pays in the Asaas app")


def ask_gate(request):
    row = gate("request", "--provider", CONNECTOR, "--request", "-", stdin=json.dumps(request))
    wait = float(os.environ.get(GATE_WAIT_ENV, "30") or 0)
    deadline = time.monotonic() + wait
    while row.get("state") == "approved" and time.monotonic() < deadline:
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
        row = gate("show", row["id"])
    return row


def state_line(row):
    state, reason = row.get("state"), row.get("reason") or ""
    if state == "sent":
        return "sent: approved by the owner" if row.get("decided_by") == "owner" else f"sent: approved by rule ({reason or 'within the limits'})"
    if state == "approved":
        return "approved: Ignite is sending it"
    return f"{state}: {reason}" if reason else state


def request_line(row):
    rid, state = row.get("id"), row.get("state")
    if state == "pending":
        return f"{rid}, sent to the owner for approval"
    if state in ("approved", "uncertain"):
        return f"{rid}, the outcome arrives in this conversation"
    if state == "sent":
        receipt = row.get("receipt_url")
        return f"{rid}, Asaas id {field(row, 'connector_id', 'provider_id')}" + (f", receipt {receipt}" if receipt else "")
    return rid


def report(args, row):
    r = row.get("recipient") or {}
    amount = brl_cents(row.get("amount_cents")) + (f" + fee {brl_cents(row['fee_cents'])}" if row.get("fee_cents") else "")
    lines = [f"Recipient   {' · '.join(x for x in (r.get('name'), r.get('document'), r.get('bank')) if x) or r.get('key')}",
             f"Amount      {amount}",
             f"State       {state_line(row)}",
             f"Request     {request_line(row)}"]
    if row.get("state") == "pending":
        lines.append(f"Next        end this turn waiting_workers: Ignite wakes this conversation with the owner's decision; "
                     f"{PROG} payment {row.get('id')} shows it meanwhile")
    elif row.get("state") == "approved":
        lines.append(f"Next        {PROG} payment {row.get('id')} shows when it is sent")
    elif row.get("state") == "uncertain":
        lines.append(f"Next        do not ask again: Ignite reads it at Asaas and wakes this conversation with the outcome; "
                     f"{PROG} statement shows whether it left")
    out(args, row, lines)
    return EXIT_FAILED if row.get("state") in ("refused", "failed", "cancelled") else EXIT_OK


def cmd_pay_pix(args):
    in_turn()
    if args.key.strip().startswith("000201"):
        raise Refusal("this is a Pix QR code (copy and paste), not a Pix key", "a QR code is paid as a QR code",
                      f"{PROG} pay qr PAYLOAD --note TEXT")
    recipient = pix_owner(args.key, args.type)
    return report(args, ask_gate({"method": "pix", "recipient": recipient, "amount_cents": args.amount,
                                  "fee_cents": 0, "note": args.note, "details": {}}))


def qr_decode(payload):
    """The QR code as Asaas reads it: its receiver, and the amount in cents it fixes (None when the payer chooses)."""
    data = call("POST", "/pix/qrCodes/decode", body={"payload": payload})
    if not data.get("canBePaid"):
        raise Refusal("Asaas cannot pay this QR code", str(data.get("cannotBePaidReason") or "it gave no reason"),
                      "ask the owner to pay it", created=False)
    receiver = data.get("receiver") or {}
    value = data.get("totalValue") if data.get("totalValue") is not None else data.get("value")
    fixed = round(value * 100) if isinstance(value, (int, float)) and value > 0 else None
    recipient = {"name": receiver.get("name"), "key": payload, "key_type": "QR",
                 "document": receiver.get("cpfCnpj"), "bank": receiver.get("ispbName")}
    return recipient, fixed, bool(data.get("canBePaidWithDifferentValue"))


def cmd_pay_qr(args):
    in_turn()
    recipient, fixed, changeable = qr_decode(args.payload)
    amount = args.amount
    if fixed is None and amount is None:
        raise Refusal("this QR code carries no amount", "the payer chooses it",
                      f"{PROG} pay qr PAYLOAD --amount 35,00 --note TEXT")
    if fixed is not None and amount is not None and amount != fixed and not changeable:
        raise Refusal(f"this QR code charges {brl_cents(fixed)}, not {brl_cents(amount)}", "its amount cannot be changed",
                      f"{PROG} pay qr PAYLOAD --note TEXT   (without --amount)")
    return report(args, ask_gate({"method": "qr", "recipient": recipient, "amount_cents": amount or fixed,
                                  "fee_cents": 0, "note": args.note, "details": {}}))


def bill_simulation(line):
    """The bill as Asaas simulates it: its recipient, value and fee in cents, and its details."""
    sim = call("POST", "/bill/simulate", body={"identificationField": line})
    info = sim.get("bankSlipInfo") or {}
    value = info.get("value")
    if not isinstance(value, (int, float)) or value <= 0:
        raise Refusal("this bill has no amount to pay", "Asaas's simulation returned no value for it",
                      "pay a bill that carries its amount; a bill with an open amount is not supported", created=False)
    recipient = {"name": info.get("beneficiaryName") or info.get("companyName"), "key": line, "key_type": None,
                 "document": info.get("beneficiaryCpfCnpj"), "bank": info.get("bank")}
    details = {"due_date": info.get("dueDate"), "company": info.get("companyName"),
               "minimum_schedule_date": sim.get("minimumScheduleDate")}
    return recipient, round(value * 100), round((sim.get("fee") or 0) * 100), details


def cmd_pay_bill(args):
    in_turn()
    recipient, value, fee, details = bill_simulation(args.line)
    if not args.json:
        due = f", due {details['due_date']}" if details.get("due_date") else ""
        print(f"Simulated   bill {brl_cents(value)}, fee {brl_cents(fee)}{due}: {brl_cents(value + fee)} counts toward the limits",
              flush=True)
    return report(args, ask_gate({"method": "bill", "recipient": recipient, "amount_cents": value,
                                  "fee_cents": fee, "note": args.note, "details": details}))


def cmd_pay_recharge(args):
    in_turn()
    recipient = {"name": None, "key": args.phone, "key_type": "PHONE", "document": None, "bank": None}
    return report(args, ask_gate({"method": "recharge", "recipient": recipient, "amount_cents": args.amount,
                                  "fee_cents": 0, "note": None, "details": {}}))


def stdin_request(rid):
    try:
        req = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        raise Refusal("no request on stdin", str(e), "Ignite's waking service runs this command; an agent pays with asaas pay")
    if not isinstance(req, dict) or req.get("id") != rid or field(req, "connector", "provider") != CONNECTOR:
        raise Refusal(f"stdin is not the request {rid}", "the id or the connector differs", "Ignite's waking service runs this command")
    return req


def resolve_recipient(method, key, key_type):
    """The recipient as Asaas names it, with what Asaas fixes: (recipient, amount_cents, fee_cents, changeable, details).
    amount_cents is None when the payer chooses it; changeable says whether a fixed QR amount may differ."""
    if method == "pix":
        return pix_owner(key, key_type), None, None, None, {}
    if method == "qr":
        recipient, fixed, changeable = qr_decode(key)
        return recipient, fixed, None, changeable, {}
    if method == "bill":
        recipient, amount, fee, details = bill_simulation(key)
        return recipient, amount, fee, False, details
    if method == "recharge":
        try:
            phone = phone_number(key)
        except argparse.ArgumentTypeError as e:
            raise Refusal("the request's phone is not a mobile number", str(e), "tell the owner")
        return {"name": None, "key": phone, "key_type": "PHONE", "document": None, "bank": None}, None, None, None, {}
    raise Refusal(f"asaas cannot resolve a {method} request", "this version pays pix, qr, bill and recharge", "tell the owner")


def recipient_lines(recipient, amount, fee):
    return [f"Recipient {' · '.join(x for x in (recipient['name'], recipient['document'], recipient['bank']) if x) or '-'}",
            f"Key       {recipient['key']}",
            f"Amount    {brl_cents(amount)}" + (f" + fee {brl_cents(fee)}" if fee else "")]


def cmd_pay_resolve(args):
    if args.id == "draft":
        return cmd_pay_resolve_draft(args)
    req = stdin_request(args.id)
    r = req.get("recipient") or {}
    method = req.get("method")
    recipient, amount, fee, changeable, _ = resolve_recipient(method, r.get("key") or "", r.get("key_type"))
    if method == "qr" and changeable:
        amount = None
    out(args, {**recipient, "amount_cents": amount, "fee_cents": fee}, recipient_lines(recipient, amount, fee))


def cmd_pay_resolve_draft(args):
    """`pay resolve draft`: the pay port command's lookup before the gate. The draft on stdin is
    {connector, method, recipient: {key, key_type}, amount_cents, note}; no request exists yet."""
    try:
        draft = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        raise Refusal("no draft on stdin", str(e), "the pay command runs this verb with the draft request on stdin")
    if not isinstance(draft, dict) or field(draft, "connector", "provider") != CONNECTOR:
        raise Refusal("stdin is not a draft for asaas", "the connector differs", "the pay command runs this verb with the draft request on stdin")
    r = draft.get("recipient") or {}
    recipient, amount, fee, changeable, details = resolve_recipient(draft.get("method"), r.get("key") or "", r.get("key_type"))
    payload = {"recipient": recipient, "amount_cents": amount, "fee_cents": fee, "changeable": changeable, "details": details}
    out(args, payload, recipient_lines(recipient, amount, fee))


def not_created(args, err):
    """A send that cannot have created an operation: the service records the request failed, not uncertain."""
    if args.json:
        print(json.dumps({"created": False, "reason": f"{err.what}: {err.why}"}, ensure_ascii=False, sort_keys=True))
    return fail(err)


def cmd_pay_execute(args):
    try:
        req = stdin_request(args.id)
        if req.get("state") != "approved":
            raise Refusal(f"{args.id} is {req.get('state')}", "only an approved request is sent", "Ignite's waking service sends approved requests")
        if req.get("method") not in ("pix", "qr", "bill", "recharge"):
            raise Refusal(f"asaas cannot send a {req.get('method')} request", "this version sends pix, qr, bill and recharge", "tell the owner")
    except Refusal as err:
        return not_created(args, err)
    r = req.get("recipient") or {}
    value = round(req["amount_cents"] / 100, 2)
    method = req["method"]
    try:
        if method == "pix":
            data = call("POST", "/transfers", body={"value": value, "pixAddressKey": r.get("key"), "pixAddressKeyType": r.get("key_type"),
                                                    "description": req.get("note"), "externalReference": req["id"]})
        elif method == "bill":
            data = call("POST", "/bill", body={"identificationField": r.get("key"), "description": req.get("note"),
                                               "externalReference": req["id"]})
        elif method == "qr":
            data = call("POST", "/pix/qrCodes/pay", body={"qrCode": {"payload": r.get("key")}, "value": value,
                                                          "description": req.get("note")})
        else:
            data = call("POST", "/mobilePhoneRecharges", body={"value": value, "phoneNumber": r.get("key")})
    except Refusal as err:
        if err.created is False:
            return not_created(args, err)
        raise
    if not data.get("id"):
        raise Refusal("Asaas returned no operation id", json.dumps(data)[:200], "check the statement before asking again")
    payload = {"provider_id": str(data.get("id")), "status": data.get("status"), "receipt_url": data.get("transactionReceiptUrl")}
    out(args, payload, [f"Sent      {req['id']} as Asaas {payload['provider_id']} ({payload['status']})"])


STATUS_READ = {
    "pix": ("/transfers/{}", TRANSFER_FINAL, lambda d: d.get("failReason")),
    "bill": ("/bill/{}", BILL_FINAL, lambda d: "; ".join(d.get("failReasons") or []) or None),
    "qr": ("/pix/transactions/{}", QR_FINAL, lambda d: d.get("refusalReason")),
    "recharge": ("/mobilePhoneRecharges/{}", RECHARGE_FINAL, lambda d: None),
}


def cmd_pay_status(args):
    req = stdin_request(args.id)
    pid = field(req, "connector_id", "provider_id")
    if not pid:
        raise Refusal(f"{args.id} has no Asaas id", "it was not sent", "ignite payment show " + args.id)
    if req.get("method") not in STATUS_READ:
        raise Refusal(f"asaas cannot read a {req.get('method')} request", "this version pays pix, qr, bill and recharge", "tell the owner")
    path, finals, why = STATUS_READ[req["method"]]
    data = call("GET", path.format(urllib.parse.quote(str(pid), safe="")))
    status = data.get("status")
    payload = {"provider_id": str(pid), "status": status, "final": status in finals, "ok": finals.get(status, True),
               "receipt_url": data.get("transactionReceiptUrl"), "reason": why(data)}
    out(args, payload, [f"Status    {status}", f"Receipt   {payload['receipt_url'] or '-'}"])


def cmd_payments(args):
    rows = gate("list", *(["--state", args.state] if args.state else [])).get("payments", [])
    lines = [f"{r['id']}  {r['state']:<9} {brl_cents(r['amount_cents'] + r['fee_cents']):>12}  "
             f"{(r.get('recipient') or {}).get('name') or (r.get('recipient') or {}).get('key')}"
             + (f"  ({r['reason']})" if r.get("reason") else "") for r in rows] or [f"No {args.state + ' ' if args.state else ''}payment requests."]
    out(args, {"payments": rows}, lines)


def cmd_payment(args):
    row = gate("show", args.id, fix=UNKNOWN_FIX)
    r = row.get("recipient") or {}
    lines = [f"Request     {row['id']}  {row['method']}",
             f"Recipient   {' · '.join(x for x in (r.get('name'), r.get('document'), r.get('bank')) if x) or r.get('key') or '-'}",
             f"Key         {r.get('key')}",
             f"Amount      {brl_cents(row['amount_cents'])}" + (f" + fee {brl_cents(row['fee_cents'])}" if row.get("fee_cents") else ""),
             f"Note        {row.get('note') or '-'}",
             f"State       {state_line(row)}",
             f"Asaas id    {field(row, 'connector_id', 'provider_id') or '-'}"
             + (f" ({field(row, 'connector_status', 'provider_status')})" if field(row, "connector_status", "provider_status") else ""),
             f"Receipt     {row.get('receipt_url') or '-'}"]
    out(args, row, lines)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise Refusal(f"Asaas answered HTTP {e.code} for the receipt", url, "check the link, or run again if Asaas was unavailable")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Refusal(f"could not reach Asaas ({RECEIPT_SITE})", str(getattr(e, "reason", e)), "check the network and run the same command again")


def cmd_receipt(args):
    ref = args.ref
    if REQUEST_ID_RE.match(ref):
        row = gate("show", ref, fix=UNKNOWN_FIX)
        link = row.get("receipt_url")
        if not link:
            raise Refusal(f"{ref} has no receipt yet", f"it is {row.get('state')}; Asaas gives a receipt once the payment is done",
                          f"{PROG} payment {ref} shows when it has one")
        name = ref
    elif ref.startswith(RECEIPT_SITE + "/"):
        link, name = ref, None
    else:
        raise Refusal(f"{ref} is neither a request id nor an Asaas receipt link",
                      f"a receipt link starts with {RECEIPT_SITE}/", f"pass a request id such as P-0007, or the receipt link")
    page = fetch(link).decode("utf-8", "replace")
    m = RECEIPT_PDF_RE.search(page)
    if not m:
        raise Refusal("the receipt page has no PDF link", "Asaas may have changed its receipt page", f"open the link in a browser: {link}")
    pdf = fetch(RECEIPT_SITE + m.group(1))
    if not pdf.startswith(b"%PDF-"):
        raise Refusal("Asaas did not return a PDF", f"{RECEIPT_SITE + m.group(1)} answered {len(pdf)} bytes of something else",
                      f"open the link in a browser: {link}")
    path = Path(args.out or f"{name or 'receipt-' + m.group(1).rsplit('/', 1)[1]}.pdf")
    if path.exists():
        raise Refusal(f"{path} already exists", "the receipt is never written over a file", "pass --out with another path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf)
    out(args, {"path": str(path.resolve()), "bytes": len(pdf), "receipt_url": link},
        [f"Saved     {path.resolve()} ({len(pdf) // 1024} KB)", f"Receipt   {link}"])


def cmd_cancel(args):
    row = gate("show", args.id, fix=UNKNOWN_FIX)
    if row.get("state") == "pending":
        row = gate("cancel", args.id)
        out(args, row, [f"Cancelled   {row['id']}: withdrawn before the owner decided"])
        return
    if row.get("state") == "sent" and field(row, "connector_id", "provider_id") and row.get("method") in ("pix", "bill"):
        pid = field(row, "connector_id", "provider_id")
        data = call("DELETE", f"/transfers/{pid}/cancel") if row.get("method") == "pix" else call("POST", f"/bill/{pid}/cancel", body={})
        payload = {"id": row["id"], "provider_id": pid, "status": data.get("status")}
        out(args, payload, [f"Cancelled   {row['id']} at Asaas ({pid}): {data.get('status')}",
                            "The gate counts it until Ignite reads the operation as cancelled."])
        return
    if row.get("state") == "sent":
        raise Refusal(f"{args.id} is a {row.get('method')} payment Asaas already has", "this tool cancels Pix key transfers and bills only",
                      "ask the owner to cancel it in the Asaas app while Asaas allows it")
    raise Refusal(f"{args.id} is {row.get('state')}: nothing to cancel",
                  "a pending request is withdrawn, a sent one is cancelled at Asaas while it can be",
                  f"{PROG} payment {args.id}")


# ───────────────────────────────────────────────────────────── parser

def parser():
    p = argparse.ArgumentParser(prog=PROG, description=(
        "An Asaas bank account for agents. Reads balance, statement and Pix keys, and pays only through "
        "Ignite's payment gate: the owner's limits or the owner's approval decide, never the agent. "
        f"Key: ${KEY_ENV}, else its line in the installation's .rbtv/config/env/.env."),
        epilog="Exit codes: 0 success, including a payment that waits for the owner (pending); "
               "1 refused or failed (stderr says why and the fix); 2 invalid arguments.")
    p.add_argument("--json", action="store_true", help="one JSON object on stdout instead of text")
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    s = sub.add_parser("balance", help="the available balance")
    s.set_defaults(fn=cmd_balance)

    s = sub.add_parser("statement", help="money in and out, newest first")
    s.add_argument("--from", dest="from_", metavar="DATE", help="first day, YYYY-MM-DD")
    s.add_argument("--to", metavar="DATE", help="last day, YYYY-MM-DD")
    s.add_argument("--limit", type=int, default=20, choices=range(1, 101), metavar="N", help="rows, 1 to 100 (default 20)")
    s.add_argument("--offset", type=int, default=0, metavar="N", help="skip N rows (the More: line gives it)")
    s.set_defaults(fn=cmd_statement)

    pix = sub.add_parser("pix", help="Pix lookups that move no money")
    psub = pix.add_subparsers(dest="pix_command", required=True, metavar="COMMAND")
    s = psub.add_parser("lookup", help="who owns a Pix key, before paying it (5 per minute)")
    s.add_argument("key", help="email, +55 phone, CPF, CNPJ or random key")
    s.add_argument("--type", choices=PIX_KEY_TYPES, help="needed only when 11 digits could be a CPF or a phone")
    s.set_defaults(fn=cmd_pix_lookup)
    s = psub.add_parser("decode", help="amount and receiver of a Pix QR code (copy and paste text)")
    s.add_argument("payload", help="the QR code's copy-and-paste text")
    s.set_defaults(fn=cmd_pix_decode)

    pay = sub.add_parser("pay", help="pay through Ignite's payment gate (inside an Ignite turn)", description=(
        "Resolves the recipient, asks Ignite's payment gate, and prints its answer: pending (waits for the owner; "
        "end the turn waiting_workers and Ignite wakes this conversation with the outcome), sent (approved by the "
        "owner's limits and sent by Ignite), or refused. Never calls a paying endpoint itself: Ignite's waking "
        "service sends what the gate approved."))
    paysub = pay.add_subparsers(dest="pay_command", required=True, metavar="COMMAND")
    s = paysub.add_parser("pix", help="Pix to a key: looks up its owner, then asks the gate")
    s.add_argument("key", help="email, +55 phone, CPF, CNPJ or random key")
    s.add_argument("amount", type=amount_cents, help="reais, like 99 or 99,90")
    s.add_argument("--note", type=note_text, required=True, help=f"what it is for, up to {NOTE_MAX} characters; the recipient sees it")
    s.add_argument("--type", choices=PIX_KEY_TYPES, help="needed only when 11 digits could be a CPF or a phone")
    s.set_defaults(fn=cmd_pay_pix)
    s = paysub.add_parser("qr", help="a Pix QR code (copy and paste text): decodes it (receiver, amount), then asks the gate")
    s.add_argument("payload", type=qr_payload, help="the QR code's copy-and-paste text, starting 000201")
    s.add_argument("--amount", type=amount_cents, help="reais, like 35 or 35,90: needed when the QR code carries no amount")
    s.add_argument("--note", type=note_text, required=True, help=f"what it is for, up to {NOTE_MAX} characters")
    s.set_defaults(fn=cmd_pay_qr)
    s = paysub.add_parser("bill", help="a boleto or utility bill: simulates it (amount and fee, shown first), then asks the gate")
    s.add_argument("line", type=bill_line, help="the bill's digitable line (linha digitável), 47 or 48 digits")
    s.add_argument("--note", type=note_text, required=True, help=f"what it is for, up to {NOTE_MAX} characters")
    s.set_defaults(fn=cmd_pay_bill)
    s = paysub.add_parser("recharge", help="a mobile top-up: asks the gate to credit a phone")
    s.add_argument("phone", type=phone_number, help="the mobile number with its area code, like 11912345678 or \"11 91234-5678\" (quoted when it has spaces; +55 optional)")
    s.add_argument("amount", type=amount_cents, help="reais, like 20 or 20,00; the operator's top-up values apply")
    s.set_defaults(fn=cmd_pay_recharge)
    s = paysub.add_parser("resolve", help="Ignite's waking service and the pay command only: read the request's recipient on stdin from Asaas",
                          description="Ignite's waking service and the pay command only. Reads the request ID as JSON on stdin and "
                                      "prints its recipient as Asaas names it (Pix key lookup, QR code decode, bill simulation), with "
                                      "the amount and fee Asaas fixes, before the owner is asked. With ID draft, reads a draft "
                                      "{connector, method, recipient: {key, key_type}, amount_cents, note} that no request records yet "
                                      "and prints {recipient, amount_cents, fee_cents, changeable, details}. Moves no money.")
    s.add_argument("id", help="the request id, such as P-0007, or draft")
    s.set_defaults(fn=cmd_pay_resolve)
    s = paysub.add_parser("execute", help="Ignite's waking service only: send the approved request on stdin",
                          description="Ignite's waking service only. Reads the approved request ID as JSON on stdin "
                                      "(ignite payment show ID --json) and sends it to Asaas: a transfer or a bill with ID as "
                                      "externalReference, a QR payment or a top-up without one. Prints the Asaas id and status; "
                                      'with --json, {"created": false, "reason"} when Asaas refused it or no call was made. '
                                      "An agent pays with pay pix, qr, bill or recharge.")
    s.add_argument("id", help="the request id, such as P-0007")
    s.set_defaults(fn=cmd_pay_execute)
    s = paysub.add_parser("status", help="Ignite's waking service only: read the sent request on stdin from Asaas",
                          description="Ignite's waking service only. Reads the sent request ID as JSON on stdin and "
                                      "prints its status at Asaas, whether it is final, and its receipt link. "
                                      "An agent reads a request with asaas payment ID.")
    s.add_argument("id", help="the request id, such as P-0007")
    s.set_defaults(fn=cmd_pay_status)

    s = sub.add_parser("payments", help="this agent's payment requests, newest first")
    s.add_argument("--state", choices=("pending", "approved", "sent", "uncertain", "refused", "cancelled", "failed"), help="keep one state")
    s.set_defaults(fn=cmd_payments)
    s = sub.add_parser("payment", help="one payment request: state, Asaas id, receipt link")
    s.add_argument("id", help="the request id, such as P-0007")
    s.set_defaults(fn=cmd_payment)
    s = sub.add_parser("cancel", help="withdraw a pending request, or cancel a sent payment at Asaas while it can be")
    s.add_argument("id", help="the request id, such as P-0007")
    s.set_defaults(fn=cmd_cancel)
    s = sub.add_parser("receipt", help="save a payment's receipt as PDF, from this agent's request id or an Asaas receipt link")
    s.add_argument("ref", help="a request id such as P-0007, or a receipt link (https://www.asaas.com/...)")
    s.add_argument("--out", help="the PDF file to write (default: <request id>.pdf in this folder); never overwritten")
    s.set_defaults(fn=cmd_receipt)

    leaves = [sub.choices["balance"], sub.choices["statement"], psub.choices["lookup"], psub.choices["decode"],
              *paysub.choices.values(), sub.choices["payments"], sub.choices["payment"], sub.choices["cancel"], sub.choices["receipt"]]
    for sp in leaves:
        sp.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    args.json = getattr(args, "json", False)
    try:
        code = args.fn(args)
    except Refusal as err:
        return fail(err)
    return EXIT_OK if code is None else code


if __name__ == "__main__":
    sys.exit(main())
