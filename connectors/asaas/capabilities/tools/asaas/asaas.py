#!/usr/bin/env python3
"""asaas — an Asaas bank account from one command, for agents.

Version 1 reads: balance, statement, Pix key lookup and Pix QR code decode.
Nothing here moves money. Payment commands come with Ignite's payment gate
(projects/ignite-0.2.2/asaas-connector/specification.md in the vault).

Key: $ASAAS_API_KEY from the process environment first, then the line
ASAAS_API_KEY=... of the installation's .rbtv/config/env/.env, read literally:
an Asaas key starts with "$", so a shell that sources the file expands it away.
"""

import argparse
import json
import os
import re
import sys
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

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2

PIX_KEY_TYPES = ("CPF", "CNPJ", "EMAIL", "PHONE", "EVP")
EVP_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z", re.I)
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class Refusal(Exception):
    def __init__(self, what, why, fix):
        super().__init__(what)
        self.what, self.why, self.fix = what, why, fix


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
                  f"add a line {KEY_ENV}=<key> to .rbtv/config/env/.env of the installation")


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
        if e.code == 401:
            raise Refusal("Asaas refused the key (401)", detail,
                          f"check {KEY_ENV}: a production key starts $aact_prod_, and an unused key is disabled after 3 months")
        if e.code == 429:
            raise Refusal("Asaas rate limit (429)", detail, "wait and run the same command again later")
        raise Refusal(f"Asaas answered HTTP {e.code} on {method} {path}", detail,
                      "correct the input named above, or run again if Asaas was unavailable")
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


def cmd_pix_lookup(args):
    ktype = pix_key_type(args.key, args.type)
    key = re.sub(r"\D", "", args.key) if ktype in ("CPF", "CNPJ") else args.key.strip()
    data = call("GET", "/pix/addressKeys/external", {"type": ktype, "key": key})
    owner = data.get("owner") or {}
    inst = data.get("financialInstitution") or {}
    payload = {"key": data.get("key", key), "type": data.get("type", ktype),
               "owner_name": owner.get("name"), "owner_document": owner.get("cpfCnpj"),
               "bank": inst.get("name") or data.get("ispbName")}
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
    lines = [f"Receiver  {payload['receiver_name']}  {payload['receiver_document'] or ''}".rstrip(),
             f"Amount    {brl(payload['total_value'] if payload['total_value'] is not None else payload['value'])}",
             f"Payable   {'yes' if payload['can_be_paid'] else 'no: ' + str(payload['cannot_be_paid_reason'])}"]
    out(args, payload, lines)


# ───────────────────────────────────────────────────────────── parser

def parser():
    p = argparse.ArgumentParser(prog=PROG, description=(
        "An Asaas bank account for agents. Reads only in this version: no command moves money. "
        f"Key: ${KEY_ENV}, else its line in the installation's .rbtv/config/env/.env."),
        epilog="Exit codes: 0 success; 1 refused or failed (stderr says why and the fix); 2 invalid arguments.")
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

    for sp in (sub.choices["balance"], sub.choices["statement"], psub.choices["lookup"], psub.choices["decode"]):
        sp.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    args.json = getattr(args, "json", False)
    try:
        args.fn(args)
    except Refusal as err:
        return fail(err)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
