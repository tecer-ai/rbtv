#!/usr/bin/env python3
"""file-issue — file one system issue into the ignite-engine register.

    file-issue file --surface ignite/… --class docs --symptom "…" …
    file-issue list [--status open|closed|all] [--class X]
    file-issue show <id>
    file-issue doctor
    file-issue selftest
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CLASSES = (
    "daemon-crash", "launch-cage", "coordination", "bridge-chat", "probe-gap",
    "data-ledger", "catalog-meta", "docs", "change-notice", "other",
)
FILE_FIELDS = (
    "surface", "class", "symptom", "evidence", "suggested-action", "risk",
)
REGISTER_REL = Path(".rbtv") / "goals" / "ignite-engine" / "register"


class Refuse(Exception):
    def __init__(self, code, message, *, route=None, extra=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.route = route
        self.extra = extra or {}


def workspace_root(start: Path) -> Path | None:
    for parent in (start, *start.parents):
        if (parent / ".rbtv" / "config").is_dir():
            return parent
    return None


def rbtv_repo(ws: Path | None) -> Path | None:
    if ws is None:
        return None
    book = ws / "rbtv.json"
    if not book.is_file():
        return None
    try:
        raw = json.loads(book.read_text(encoding="utf-8")).get("rbtv_path") or ""
    except (OSError, ValueError):
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_absolute() else (ws / p)


def register_root(cwd: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    ws = workspace_root(cwd)
    if ws is None:
        raise Refuse(
            "register-missing",
            "no .rbtv/config/ above cwd — cannot derive the engine register "
            "(override with --register only in tests)",
        )
    return ws / REGISTER_REL


def derive_as(cwd: Path) -> str | None:
    here = cwd.resolve()
    seat_md = None
    for parent in (here, *here.parents):
        cand = parent / "seat.md"
        if cand.is_file():
            seat_md = cand
            break
    if seat_md is None:
        return None
    seat = None
    for line in seat_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("seat:"):
            seat = line.split(":", 1)[1].strip().strip("'\"")
            break
    if not seat:
        return None
    parts = seat_md.resolve().parts
    goal = None
    if "goals" in parts and "seats" in parts:
        gi, si = parts.index("goals"), parts.index("seats")
        if si == gi + 2:
            goal = parts[gi + 1]
    if not goal:
        return None
    return f"{goal}/{seat}"


def normalize_surface(raw: str, ws: Path | None) -> str | None:
    text = raw.strip()
    if not text:
        return None
    p = Path(text)
    repo = rbtv_repo(ws)
    if p.is_absolute():
        if repo is None:
            return None
        try:
            rel = p.resolve().relative_to(repo.resolve())
        except ValueError:
            return None
        parts = rel.parts
    else:
        parts = Path(text).parts
        if parts and parts[0] == ".":
            parts = parts[1:]
    if not parts or parts[0] not in ("ignite", "meta"):
        return None
    return str(Path(*parts))


def yaml_scalar(value: str) -> str:
    s = "" if value is None else str(value)
    if s == "" or any(c in s for c in ":#\n\"'") or s != s.strip() or s[:1] in "[{":
        return json.dumps(s, ensure_ascii=False)
    return s


def render_filing(rec: dict) -> str:
    keys = (
        "id", "filed-by", "when", "surface", "class", "symptom",
        "evidence", "suggested-action", "risk", "status",
    )
    fm = "\n".join(f"{k}: {yaml_scalar(rec[k])}" for k in keys)
    body = (
        f"## {rec['id']} — {rec['symptom']}\n"
        f"Destination: ignite-engine\n"
        f"**Surface:** {rec['surface']}\n"
        f"**Class:** {rec['class']}\n"
        f"**Symptom:** {rec['symptom']}\n"
        f"**Evidence:** {rec['evidence']}\n"
        f"**Suggested-action:** {rec['suggested-action']}\n"
        f"**Risk:** {rec['risk']}\n"
        f"**Filed-by:** {rec['filed-by']}\n"
    )
    return f"---\n{fm}\n---\n{body}"


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    out = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v[:1] in "\"'":
            try:
                v = json.loads(v)
            except ValueError:
                v = v.strip("'\"")
        out[k.strip()] = v
    return out


def existing_ids(reg: Path) -> set[str]:
    found = set()
    for folder in ("open", "closed"):
        d = reg / folder
        if not d.is_dir():
            continue
        for p in d.glob("*.md"):
            found.add(p.stem)
    return found


def mint_id(seat: str, when: datetime, taken: set[str], override: str | None) -> str:
    if override:
        base = override
    else:
        base = f"G-{seat}-{when.strftime('%m%d-%H%M')}"
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def seat_from_as(filed_by: str) -> str:
    return filed_by.rsplit("/", 1)[-1]


def route_pointer(filed_by: str | None) -> str:
    if filed_by and "/" in filed_by:
        goal = filed_by.split("/", 1)[0]
        return f".rbtv/goals/{goal}/issues.md"
    return "this goal's issues.md"


def check_register(reg: Path) -> str | None:
    if not reg.is_dir():
        return "register-missing"
    if not os.access(reg, os.W_OK):
        return "register-not-writable"
    return None


def emit(payload, *, as_json: bool, exit_code: int) -> int:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif payload.get("ok") is False:
        ref = payload.get("refusal", {})
        print(f"refused: {ref.get('code')}", file=sys.stderr)
        if ref.get("message"):
            print(f"why: {ref['message']}", file=sys.stderr)
        if ref.get("route"):
            print(f"route: file it on {ref['route']} instead", file=sys.stderr)
        if ref.get("fix"):
            print(f"fix: {ref['fix']}", file=sys.stderr)
    else:
        text = payload.get("text")
        if text:
            print(text)
    return exit_code


def refuse_payload(exc: Refuse, as_json: bool) -> int:
    ref = {"code": exc.code, "message": exc.message, **exc.extra}
    if exc.route:
        ref["route"] = exc.route
    return emit({"ok": False, "refusal": ref}, as_json=as_json, exit_code=2)


def cmd_file(args, cwd: Path) -> int:
    as_json = args.json
    filed_by = args.as_who or derive_as(cwd)
    missing = []
    values = {
        "surface": args.surface,
        "class": args.klass,
        "symptom": args.symptom,
        "evidence": args.evidence,
        "suggested-action": args.suggested_action,
        "risk": args.risk,
    }
    for name in FILE_FIELDS:
        if not (values[name] or "").strip():
            missing.append(name)
    if not filed_by:
        missing.append("as")
    if missing:
        name = missing[0]
        return refuse_payload(Refuse(
            f"missing-field:{name}",
            f"--{name} is required",
            extra={"fix": f"pass --{name} (see file-issue file --help)"},
        ), as_json)

    ws = workspace_root(cwd)
    surface = normalize_surface(values["surface"], ws)
    if surface is None:
        return refuse_payload(Refuse(
            "scope-refused",
            "surface must be under ignite/ or meta/ of the rbtv repo",
            route=route_pointer(filed_by),
            extra={"fix": "pass --surface ignite/… or --surface meta/…"},
        ), as_json)

    try:
        reg = register_root(cwd, args.register)
    except Refuse as exc:
        return refuse_payload(exc, as_json)
    code = check_register(reg)
    if code:
        return refuse_payload(Refuse(
            code,
            "engine register is missing" if code == "register-missing"
            else "engine register is not writable from here",
            extra={"register": str(reg)},
        ), as_json)

    now = datetime.now(timezone.utc)
    seat = seat_from_as(filed_by)
    fid = mint_id(seat, now, existing_ids(reg), args.id)
    rec = {
        "id": fid,
        "filed-by": filed_by,
        "when": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "surface": surface,
        "class": values["class"],
        "symptom": values["symptom"].strip(),
        "evidence": values["evidence"].strip(),
        "suggested-action": values["suggested-action"].strip(),
        "risk": values["risk"].strip(),
        "status": "open",
    }
    open_dir = reg / "open"
    try:
        open_dir.mkdir(exist_ok=True)
        tmp = reg / f".tmp.{fid}.{os.getpid()}"
        tmp.write_text(render_filing(rec), encoding="utf-8")
        tmp.replace(open_dir / f"{fid}.md")
    except OSError as exc:
        return refuse_payload(Refuse(
            "register-not-writable",
            f"could not write filing: {exc}",
            extra={"register": str(reg)},
        ), as_json)

    dest = open_dir / f"{fid}.md"
    payload = {
        "ok": True,
        "id": fid,
        "path": str(dest),
        "status": "open",
        "text": f"filed {fid}\n{dest}\nnext: file-issue show {fid}",
    }
    return emit(payload, as_json=as_json, exit_code=0)


def iter_filings(reg: Path):
    for status in ("open", "closed"):
        d = reg / status
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            rec = parse_frontmatter(p.read_text(encoding="utf-8"))
            rec.setdefault("id", p.stem)
            rec.setdefault("status", status)
            rec["_path"] = str(p)
            yield rec


def cmd_list(args, cwd: Path) -> int:
    try:
        reg = register_root(cwd, args.register)
    except Refuse as exc:
        return refuse_payload(exc, args.json)
    code = check_register(reg)
    if code == "register-missing":
        return refuse_payload(Refuse(code, "engine register is missing",
                                    extra={"register": str(reg)}), args.json)
    want = args.status or "open"
    rows = []
    for rec in iter_filings(reg):
        st = rec.get("status") or "open"
        if want != "all" and st != want:
            continue
        if args.klass and rec.get("class") != args.klass:
            continue
        rows.append({
            "id": rec.get("id"),
            "when": rec.get("when"),
            "class": rec.get("class"),
            "surface": rec.get("surface"),
            "symptom": rec.get("symptom"),
            "filed-by": rec.get("filed-by"),
            "status": st,
        })
    if args.json:
        return emit({"ok": True, "filings": rows}, as_json=True, exit_code=0)
    if not rows:
        print("no filings")
        return 0
    for r in rows:
        print(f"{r['id']}\t{r['when']}\t{r['class']}\t{r['surface']}\t{r['symptom']}\t{r['filed-by']}\t{r['status']}")
    print(f"next: file-issue show {rows[0]['id']}")
    return 0


def cmd_show(args, cwd: Path) -> int:
    try:
        reg = register_root(cwd, args.register)
    except Refuse as exc:
        return refuse_payload(exc, args.json)
    if check_register(reg) == "register-missing":
        return refuse_payload(Refuse("register-missing", "engine register is missing",
                                    extra={"register": str(reg)}), args.json)
    hit = None
    for rec in iter_filings(reg):
        if rec.get("id") == args.id:
            hit = rec
            break
    if hit is None:
        return refuse_payload(Refuse(
            "not-found",
            f"no filing {args.id}",
            extra={"fix": "file-issue list --status all"},
        ), args.json)
    if args.json:
        body = {k: hit[k] for k in hit if not k.startswith("_")}
        body["path"] = hit["_path"]
        return emit({"ok": True, "filing": body}, as_json=True, exit_code=0)
    print(Path(hit["_path"]).read_text(encoding="utf-8"), end="")
    return 0


def cmd_doctor(args, cwd: Path) -> int:
    try:
        reg = register_root(cwd, args.register)
        derived_ok = True
        derive_note = None
    except Refuse as exc:
        reg = None
        derived_ok = False
        derive_note = exc.message
    exists = bool(reg and reg.is_dir())
    writable = bool(exists and os.access(reg, os.W_OK))
    open_n = closed_n = 0
    if exists:
        open_n = len(list((reg / "open").glob("*.md"))) if (reg / "open").is_dir() else 0
        closed_n = len(list((reg / "closed").glob("*.md"))) if (reg / "closed").is_dir() else 0
    if not derived_ok or not exists:
        refuse_code = "register-missing"
    elif not writable:
        refuse_code = "register-not-writable"
    else:
        refuse_code = None
    payload = {
        "ok": refuse_code is None,
        "register": str(reg) if reg else None,
        "exists": exists,
        "writable": writable,
        "open": open_n,
        "closed": closed_n,
        "refuse": refuse_code,
    }
    if derive_note:
        payload["note"] = derive_note
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"register: {payload['register']}")
        print(f"exists: {exists}")
        print(f"writable: {writable}")
        print(f"open: {open_n}")
        print(f"closed: {closed_n}")
        print(f"refuse: {refuse_code or 'none'}")
    return 0 if refuse_code is None else 1


def _run(argv, *, cwd=None):
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *argv],
        cwd=cwd, capture_output=True, text=True,
    )


def _ok(label, cond, detail=""):
    mark = "ok  " if cond else "FAIL"
    print(f"{mark} {label}" + (f" — {detail}" if detail else ""))
    return cond


def cmd_selftest(_args, _cwd: Path) -> int:
    passed = True
    with tempfile.TemporaryDirectory(prefix="file-issue-selftest-") as td:
        root = Path(td)
        ws = root / "ws"
        (ws / ".rbtv" / "config").mkdir(parents=True)
        (ws / "rbtv.json").write_text(
            json.dumps({"rbtv_path": str(root / "rbtv")}), encoding="utf-8")
        (root / "rbtv" / "ignite").mkdir(parents=True)
        (root / "rbtv" / "meta").mkdir(parents=True)
        reg = ws / ".rbtv" / "goals" / "ignite-engine" / "register"
        reg.mkdir(parents=True)
        seat_dir = ws / ".rbtv" / "goals" / "fx-goal" / "seats" / "leader"
        seat_dir.mkdir(parents=True)
        (seat_dir / "seat.md").write_text("---\nseat: leader\n---\n", encoding="utf-8")

        common = ["--register", str(reg), "--json"]
        file_args = [
            "file", *common,
            "--surface", "ignite/engine/reconcile.js",
            "--class", "coordination",
            "--symptom", "cursor treated as mail",
            "--evidence", "probe-x",
            "--suggested-action", "fix the cursor",
            "--risk", "silent stall",
            "--as", "fx-goal/leader",
            "--id", "G-leader-0101-0000",
        ]
        r1 = _run(file_args)
        d1 = json.loads(r1.stdout) if r1.stdout.strip() else {}
        listed = _run(["list", *common, "--status", "open"])
        shown = _run(["show", "G-leader-0101-0000", *common])
        show_ok = shown.returncode == 0 and "G-leader-0101-0000" in shown.stdout
        list_ok = listed.returncode == 0 and "G-leader-0101-0000" in listed.stdout
        passed &= _ok("green: file-list-show",
                      r1.returncode == 0 and d1.get("id") == "G-leader-0101-0000"
                      and list_ok and show_ok,
                      f"file={r1.returncode} list={listed.returncode} show={shown.returncode}")

        r2 = _run(file_args)
        d2 = json.loads(r2.stdout) if r2.stdout.strip() else {}
        passed &= _ok("green: id-collision",
                      r2.returncode == 0 and d2.get("id") == "G-leader-0101-0000-2",
                      d2.get("id"))

        r3 = _run([
            "file", *common,
            "--surface", "meta/planning/references/exposure.md",
            "--class", "change-notice",
            "--symptom", "owner commit on exposure",
            "--evidence", "git show",
            "--suggested-action", "observe",
            "--risk", "none",
            "--as", "fx-goal/leader",
            "--id", "G-leader-0101-0001",
        ])
        d3 = json.loads(r3.stdout) if r3.stdout.strip() else {}
        body = (reg / "open" / "G-leader-0101-0001.md").read_text(encoding="utf-8")
        passed &= _ok("green: change-notice",
                      r3.returncode == 0 and d3.get("id") == "G-leader-0101-0001"
                      and "class: change-notice" in body
                      and "## G-leader-0101-0001 — owner commit on exposure" in body)

        r4 = _run([
            "file", "--register", str(reg), "--json",
            "--surface", "ignite/server/spawn.js",
            "--class", "launch-cage",
            "--symptom", "derived as",
            "--evidence", "cwd",
            "--suggested-action", "keep",
            "--risk", "low",
            "--id", "G-leader-0101-0002",
        ], cwd=seat_dir)
        d4 = json.loads(r4.stdout) if r4.stdout.strip() else {}
        rec4 = parse_frontmatter(
            (reg / "open" / "G-leader-0101-0002.md").read_text(encoding="utf-8"))
        passed &= _ok("green: as-derivation",
                      r4.returncode == 0 and rec4.get("filed-by") == "fx-goal/leader",
                      rec4.get("filed-by"))

        r5 = _run([
            "file", *common, "--class", "docs", "--symptom", "x",
            "--evidence", "e", "--suggested-action", "s", "--risk", "r",
            "--as", "fx-goal/leader",
        ])
        d5 = json.loads(r5.stdout) if r5.stdout.strip() else {}
        passed &= _ok("red: missing-field",
                      r5.returncode == 2
                      and d5.get("refusal", {}).get("code") == "missing-field:surface"
                      and not list((reg / "open").glob("G-leader-0101-0099*")),
                      d5.get("refusal", {}).get("code"))

        r6 = _run([
            "file", *common,
            "--surface", "2-areas/x.md",
            "--class", "docs", "--symptom", "x", "--evidence", "e",
            "--suggested-action", "s", "--risk", "r", "--as", "fx-goal/leader",
        ])
        d6 = json.loads(r6.stdout) if r6.stdout.strip() else {}
        passed &= _ok("red: scope-refused",
                      r6.returncode == 2
                      and d6.get("refusal", {}).get("code") == "scope-refused"
                      and "issues.md" in (d6.get("refusal", {}).get("route") or ""),
                      d6.get("refusal", {}).get("code"))

        missing_reg = root / "no-such-register"
        r7 = _run([
            "file", "--register", str(missing_reg), "--json",
            "--surface", "ignite/x.py", "--class", "other",
            "--symptom", "x", "--evidence", "e",
            "--suggested-action", "s", "--risk", "r", "--as", "fx-goal/leader",
        ])
        d7 = json.loads(r7.stdout) if r7.stdout.strip() else {}
        passed &= _ok("red: register-missing",
                      r7.returncode == 2
                      and d7.get("refusal", {}).get("code") == "register-missing",
                      d7.get("refusal", {}).get("code"))

        locked = root / "locked-reg"
        locked.mkdir()
        os.chmod(locked, stat.S_IRUSR | stat.S_IXUSR)
        try:
            r8 = _run([
                "file", "--register", str(locked), "--json",
                "--surface", "ignite/x.py", "--class", "other",
                "--symptom", "x", "--evidence", "e",
                "--suggested-action", "s", "--risk", "r", "--as", "fx-goal/leader",
            ])
        finally:
            os.chmod(locked, stat.S_IRWXU)
        d8 = json.loads(r8.stdout) if r8.stdout.strip() else {}
        passed &= _ok("red: not-writable",
                      r8.returncode == 2
                      and d8.get("refusal", {}).get("code") == "register-not-writable",
                      d8.get("refusal", {}).get("code"))

    print("selftest: PASS" if passed else "selftest: FAIL")
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="file-issue",
        description="File one system issue into the ignite-engine register.",
        epilog="next: file-issue file --help",
    )
    p.add_argument("--register", help="override register dir (tests only)")
    p.add_argument("--json", action="store_true", help="stable JSON on stdout")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("file", help="write one filing into register/open/<id>.md",
                       epilog="next: file-issue show <id>")
    f.add_argument("--surface", help="path under ignite/ or meta/ of the rbtv repo")
    f.add_argument("--class", dest="klass", choices=CLASSES, help="filing class")
    f.add_argument("--symptom", help="one-line symptom")
    f.add_argument("--evidence", help="path or command")
    f.add_argument("--suggested-action", dest="suggested_action", help="what to do")
    f.add_argument("--risk", help="one-line risk")
    f.add_argument("--as", dest="as_who", help="who files: <goal>/<seat>")
    f.add_argument("--id", help="override id (collision still suffixes -2, -3)")
    f.add_argument("--register", help="override register dir (tests only)")
    f.add_argument("--json", action="store_true")
    f.set_defaults(_fn=cmd_file)

    l = sub.add_parser("list", help="list filings", epilog="next: file-issue show <id>")
    l.add_argument("--status", choices=("open", "closed", "all"), default="open")
    l.add_argument("--class", dest="klass", choices=CLASSES)
    l.add_argument("--register", help="override register dir (tests only)")
    l.add_argument("--json", action="store_true")
    l.set_defaults(_fn=cmd_list)

    s = sub.add_parser("show", help="print one filing", epilog="next: file-issue list")
    s.add_argument("id")
    s.add_argument("--register", help="override register dir (tests only)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(_fn=cmd_show)

    d = sub.add_parser("doctor", help="register path, exists, writable, counts")
    d.add_argument("--register", help="override register dir (tests only)")
    d.add_argument("--json", action="store_true")
    d.set_defaults(_fn=cmd_doctor)

    t = sub.add_parser("selftest", help="hermetic green and red arms")
    t.set_defaults(_fn=cmd_selftest)
    return p


def main(argv=None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    cwd = Path.cwd()
    try:
        return args._fn(args, cwd)
    except Refuse as exc:
        return refuse_payload(exc, getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
