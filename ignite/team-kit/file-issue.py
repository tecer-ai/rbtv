#!/usr/bin/env python3
"""file-issue — the ignite-engine register's filer, validator and written record.

The command inventory lives in the argument parser: run `file-issue --help`.
The entry format, the class enum, the status vocabulary and the HISTORY entry
shape live in one place too: run `file-issue schema`.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
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
# The entry format, in frontmatter order. One home: `render_filing` writes these,
# `validate_entry` requires them, `schema` prints them.
ENTRY_KEYS = (
    "id", "filed-by", "when", "surface", "class", "symptom",
    "evidence", "suggested-action", "risk", "status",
)
STATUS_LIFECYCLE = (
    "open", "triaged", "approved", "building", "judged", "deployed",
    "verified", "closed",
)
STATUS_TERMINAL = ("duplicate", "invalid", "wont-fix")
STATUSES = STATUS_LIFECYCLE + STATUS_TERMINAL
HISTORY_FIELDS = ("component", "id", "seen", "missed", "held")
HISTORY_ENTRY = {
    "file": "<rbtv repo>/<component>/HISTORY.md",
    "header-when-created": "# HISTORY — <component>",
    "heading": "## <UTC date YYYY-MM-DD> — <register-id> — <first line of --seen>",
    "lines": [
        "**Seen:** <what was seen>",
        "**Missed:** <the trials that missed, and why>",
        "**Held:** <the solution that held>",
    ],
}
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


def normalize_surface(raw: str, repo: Path | None) -> str | None:
    """A path under ignite/ or meta/ of the rbtv repo, repo-relative — or None."""
    text = raw.strip()
    if not text:
        return None
    p = Path(text)
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
    fm = "\n".join(f"{k}: {yaml_scalar(rec[k])}" for k in ENTRY_KEYS)
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


def register_files(reg: Path):
    """(register-relative name, path) for every entry file, open then closed."""
    for folder in ("open", "closed"):
        d = reg / folder
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            yield f"{folder}/{path.name}", path


def validate_entry(path: Path) -> str | None:
    """The first defect code of one register entry, or None when it validates."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unreadable"
    rec = parse_frontmatter(text)
    if not rec:
        return "frontmatter-unparsed"
    for key in ENTRY_KEYS:
        if not str(rec.get(key, "")).strip():
            return f"missing-field:{key}"
    if rec["class"] not in CLASSES:
        return "class-not-in-vocabulary"
    if rec["status"] not in STATUSES:
        return "status-not-in-vocabulary"
    if rec["id"] != path.stem:
        return "id-not-filename-stem"
    if f"## {path.stem} — " not in text:
        return "heading-missing"
    if "Destination: ignite-engine" not in text:
        return "destination-missing"
    return None


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
    surface = normalize_surface(values["surface"], rbtv_repo(ws))
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
        derive_note = None
    except Refuse as exc:
        reg = None
        derive_note = exc.message
    exists = bool(reg and reg.is_dir())
    writable = bool(exists and os.access(reg, os.W_OK))
    open_n = closed_n = 0
    rows, invalid = [], []
    if exists:
        open_n = len(list((reg / "open").glob("*.md"))) if (reg / "open").is_dir() else 0
        closed_n = len(list((reg / "closed").glob("*.md"))) if (reg / "closed").is_dir() else 0
        for name, path in register_files(reg):
            code = validate_entry(path)
            rows.append((name, code))
            if code:
                invalid.append({"file": name, "code": code})
    if not exists:
        refuse_code = "register-missing"
    elif not writable:
        refuse_code = "register-not-writable"
    elif invalid:
        refuse_code = "entries-invalid"
    else:
        refuse_code = None
    payload = {
        "ok": refuse_code is None,
        "register": str(reg) if reg else None,
        "exists": exists,
        "writable": writable,
        "open": open_n,
        "closed": closed_n,
        "valid": len(rows) - len(invalid),
        "invalid": invalid,
        "refuse": refuse_code,
    }
    if derive_note:
        payload["note"] = derive_note
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if refuse_code is None else 1
    for name, code in rows:
        print(f"invalid {name} {code}" if code else f"ok {name}")
    print(f"register: {payload['register']}")
    print(f"exists: {exists}")
    print(f"writable: {writable}")
    print(f"open: {open_n}")
    print(f"closed: {closed_n}")
    print(f"valid: {payload['valid']}")
    print(f"invalid: {len(invalid)}")
    print(f"refuse: {refuse_code or 'none'}")
    if invalid:
        print(f"next: file-issue show {Path(invalid[0]['file']).stem}")
    elif refuse_code is None:
        print("next: file-issue list --status open")
    return 0 if refuse_code is None else 1


def schema_payload() -> dict:
    return {
        "entry-keys": list(ENTRY_KEYS),
        "classes": list(CLASSES),
        "statuses": {
            "lifecycle": list(STATUS_LIFECYCLE),
            "terminal": list(STATUS_TERMINAL),
        },
        "history-entry": dict(HISTORY_ENTRY),
    }


def cmd_schema(args, _cwd: Path) -> int:
    if args.json:
        print(json.dumps(schema_payload(), ensure_ascii=False, sort_keys=True))
        return 0
    print("entry keys — frontmatter, in this order, all present and non-empty:")
    for key in ENTRY_KEYS:
        print(f"  {key}")
    print("body: '## <id> — <symptom>' and the line 'Destination: ignite-engine'")
    print("classes:")
    print(f"  {' '.join(CLASSES)}")
    print("status vocabulary — lifecycle, in this order:")
    print(f"  {' -> '.join(STATUS_LIFECYCLE)}")
    print("status vocabulary — terminal closes:")
    print(f"  {' '.join(STATUS_TERMINAL)}")
    print(f"HISTORY entry — file {HISTORY_ENTRY['file']}:")
    print(f"  header when created: {HISTORY_ENTRY['header-when-created']}")
    print(f"  {HISTORY_ENTRY['heading']}")
    for line in HISTORY_ENTRY["lines"]:
        print(f"  {line}")
    print("next: file-issue doctor")
    return 0


def repo_root(cwd: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    repo = rbtv_repo(workspace_root(cwd))
    if repo is None:
        raise Refuse(
            "repo-missing",
            "no rbtv.json above cwd — cannot derive the rbtv repo root",
            extra={"fix": "run from inside the workspace (override with --repo in tests)"},
        )
    return repo


def one_line(value: str) -> str:
    return " ".join(value.split())


def scope_refusal(what: str) -> Refuse:
    return Refuse(
        "scope-refused",
        f"--{what} must be a path under ignite/ or meta/ of the rbtv repo",
        extra={"fix": f"pass --{what} ignite/… or --{what} meta/…"},
    )


def cmd_history_append(args, cwd: Path) -> int:
    as_json = args.json
    values = {
        "component": args.component, "id": args.id,
        "seen": args.seen, "missed": args.missed, "held": args.held,
    }
    for name in HISTORY_FIELDS:
        if not (values[name] or "").strip():
            return refuse_payload(Refuse(
                f"missing-field:{name}",
                f"--{name} is required",
                extra={"fix": f"pass --{name} "
                              f"(see file-issue history append --help)"},
            ), as_json)
    try:
        repo = repo_root(cwd, args.repo)
        reg = register_root(cwd, args.register)
    except Refuse as exc:
        return refuse_payload(exc, as_json)

    component = normalize_surface(values["component"], repo)
    if component is None:
        return refuse_payload(scope_refusal("component"), as_json)

    known = existing_ids(reg)
    if values["id"] not in known:
        near = difflib.get_close_matches(values["id"], sorted(known), n=1)
        message = f"{values['id']} is in neither register/open nor register/closed"
        if near:
            message += f" — did you mean {near[0]}?"
        return refuse_payload(Refuse(
            "unknown-id", message,
            extra={"fix": "file-issue list --status all"},
        ), as_json)

    title = one_line(values["seen"].splitlines()[0])
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = (
        f"## {date} — {values['id']} — {title}\n"
        f"**Seen:** {one_line(values['seen'])}\n"
        f"**Missed:** {one_line(values['missed'])}\n"
        f"**Held:** {one_line(values['held'])}\n"
    )
    hist = repo / component / "HISTORY.md"
    created = not hist.exists()
    try:
        with hist.open("a", encoding="utf-8") as fh:
            if created:
                fh.write(f"# HISTORY — {component}\n")
            fh.write("\n" + entry)
    except OSError as exc:
        return refuse_payload(Refuse(
            "history-not-writable",
            f"could not write {hist}: {exc}",
            extra={"fix": f"check that {repo / component} exists and is writable"},
        ), as_json)

    payload = {
        "ok": True,
        "path": str(hist),
        "component": component,
        "id": values["id"],
        "date": date,
        "created": created,
        "text": f"{'created' if created else 'appended'} {hist}\n"
                f"next: file-issue history show --component {component}",
    }
    return emit(payload, as_json=as_json, exit_code=0)


def parse_history(text: str) -> list[dict]:
    entries = []
    for line in text.splitlines():
        if not line.startswith("## "):
            continue
        parts = [x.strip() for x in line[3:].split(" — ")]
        entries.append({
            "heading": line,
            "date": parts[0] if parts else "",
            "id": parts[1] if len(parts) > 1 else "",
            "title": " — ".join(parts[2:]) if len(parts) > 2 else "",
        })
    return entries


def cmd_history_show(args, cwd: Path) -> int:
    as_json = args.json
    if not (args.component or "").strip():
        return refuse_payload(Refuse(
            "missing-field:component",
            "--component is required",
            extra={"fix": "pass --component (see file-issue history show --help)"},
        ), as_json)
    try:
        repo = repo_root(cwd, args.repo)
    except Refuse as exc:
        return refuse_payload(exc, as_json)
    component = normalize_surface(args.component, repo)
    if component is None:
        return refuse_payload(scope_refusal("component"), as_json)
    hist = repo / component / "HISTORY.md"
    exists = hist.is_file()
    entries = parse_history(hist.read_text(encoding="utf-8")) if exists else []
    if as_json:
        return emit({
            "ok": True, "component": component, "path": str(hist),
            "exists": exists, "entries": entries,
        }, as_json=True, exit_code=0)
    if not exists:
        print(f"no HISTORY for {component}")
        return 0
    for e in entries:
        print(f"{e['date']}\t{e['id']}\t{e['title']}")
    print(f"{len(entries)} in {hist}")
    print(f"next: file-issue history append --component {component} --id <register-id>")
    return 0


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


        # ---- doctor validates the register the tool itself wrote ----------------
        dv = _run(["--json", "--register", str(reg), "doctor"])
        ddv = json.loads(dv.stdout) if dv.stdout.strip() else {}
        passed &= _ok("green: doctor-valid",
                      dv.returncode == 0 and ddv.get("invalid") == []
                      and ddv.get("valid") == 4 and ddv.get("open") == 4,
                      f"exit={dv.returncode} valid={ddv.get('valid')} "
                      f"invalid={ddv.get('invalid')}")

        victim_name = "G-leader-0101-0001.md"
        reg_mk = root / "reg-missing-key"
        shutil.copytree(reg, reg_mk)
        vmk = reg_mk / "open" / victim_name
        vmk.write_text("\n".join(
            ln for ln in vmk.read_text(encoding="utf-8").splitlines()
            if not ln.startswith("risk:")) + "\n", encoding="utf-8")
        dmk = _run(["--json", "--register", str(reg_mk), "doctor"])
        dd_mk = json.loads(dmk.stdout) if dmk.stdout.strip() else {}
        passed &= _ok("red: doctor-missing-key",
                      dmk.returncode != 0
                      and {"file": f"open/{victim_name}", "code": "missing-field:risk"}
                      in dd_mk.get("invalid", [])
                      and dd_mk.get("valid") == 3,
                      f"exit={dmk.returncode} invalid={dd_mk.get('invalid')}")

        reg_bs = root / "reg-bad-status"
        shutil.copytree(reg, reg_bs)
        vbs = reg_bs / "open" / victim_name
        vbs.write_text(vbs.read_text(encoding="utf-8")
                       .replace("status: open", "status: parked", 1), encoding="utf-8")
        dbs = _run(["--json", "--register", str(reg_bs), "doctor"])
        dd_bs = json.loads(dbs.stdout) if dbs.stdout.strip() else {}
        passed &= _ok("red: doctor-off-vocabulary-status",
                      dbs.returncode != 0
                      and {"file": f"open/{victim_name}",
                           "code": "status-not-in-vocabulary"} in dd_bs.get("invalid", []),
                      f"exit={dbs.returncode} invalid={dd_bs.get('invalid')}")

        # ---- schema is the one written record -----------------------------------
        want_keys = ["id", "filed-by", "when", "surface", "class", "symptom",
                     "evidence", "suggested-action", "risk", "status"]
        want_life = ["open", "triaged", "approved", "building", "judged",
                     "deployed", "verified", "closed"]
        want_term = ["duplicate", "invalid", "wont-fix"]
        sc_txt = _run(["schema"])
        sc_json = _run(["schema", "--json"])
        try:
            sd = json.loads(sc_json.stdout)
        except ValueError:
            sd = {}
        passed &= _ok("green: schema",
                      sc_txt.returncode == 0 and sc_json.returncode == 0
                      and "suggested-action" in sc_txt.stdout
                      and "wont-fix" in sc_txt.stdout
                      and "**Missed:**" in sc_txt.stdout
                      and set(sd) == {"entry-keys", "classes", "statuses", "history-entry"}
                      and sd.get("entry-keys") == want_keys
                      and sd.get("statuses", {}).get("lifecycle") == want_life
                      and sd.get("statuses", {}).get("terminal") == want_term,
                      f"txt={sc_txt.returncode} json={sc_json.returncode} keys={sorted(sd)}")

        # ---- history: create, then append without touching a byte ----------------
        comp = "ignite/team-kit"
        repo_dir = root / "rbtv"
        (repo_dir / comp).mkdir(parents=True, exist_ok=True)
        hist = repo_dir / comp / "HISTORY.md"
        hcommon = ["--repo", str(repo_dir), "--register", str(reg), "--json"]
        h1 = _run(["history", "append", *hcommon, "--component", comp,
                   "--id", "G-leader-0101-0000",
                   "--seen", "doctor passed an entry with no status",
                   "--missed", "a body grep — it matched the prose, not the frontmatter",
                   "--held", "validate the parsed frontmatter against the ten entry keys"])
        dh1 = json.loads(h1.stdout) if h1.stdout.strip() else {}
        after1 = hist.read_text(encoding="utf-8") if hist.is_file() else ""
        h2 = _run(["history", "append", *hcommon, "--component", comp,
                   "--id", "G-leader-0101-0001",
                   "--seen", "the second entry", "--missed", "nothing", "--held", "append"])
        dh2 = json.loads(h2.stdout) if h2.stdout.strip() else {}
        after2 = hist.read_text(encoding="utf-8") if hist.is_file() else ""
        hshow = _run(["history", "show", "--repo", str(repo_dir),
                      "--component", comp, "--json"])
        dhs = json.loads(hshow.stdout) if hshow.stdout.strip() else {}
        ents = dhs.get("entries", [])
        passed &= _ok("green: history-create-append",
                      h1.returncode == 0 and dh1.get("created") is True
                      and after1.startswith(f"# HISTORY — {comp}\n")
                      and "**Seen:** doctor passed an entry with no status" in after1
                      and "**Missed:**" in after1 and "**Held:**" in after1
                      and h2.returncode == 0 and dh2.get("created") is False
                      and after2.startswith(after1) and len(after2) > len(after1)
                      and hshow.returncode == 0 and len(ents) == 2
                      and ents[0].get("id") == "G-leader-0101-0000"
                      and ents[1].get("id") == "G-leader-0101-0001",
                      f"c1={h1.returncode} created={dh1.get('created')} "
                      f"c2={h2.returncode} appended={after2.startswith(after1)} "
                      f"entries={len(ents)}")

        hr1 = _run(["history", "append", *hcommon, "--component", comp,
                    "--id", "G-leader-0101-0000", "--seen", "x", "--missed", "y"])
        dr1 = json.loads(hr1.stdout) if hr1.stdout.strip() else {}
        passed &= _ok("red: history-missing-field",
                      hr1.returncode == 2
                      and dr1.get("refusal", {}).get("code") == "missing-field:held",
                      dr1.get("refusal", {}).get("code"))

        hr2 = _run(["history", "append", *hcommon, "--component", "5-workbench/x",
                    "--id", "G-leader-0101-0000", "--seen", "x", "--missed", "y",
                    "--held", "z"])
        dr2 = json.loads(hr2.stdout) if hr2.stdout.strip() else {}
        passed &= _ok("red: history-scope-refused",
                      hr2.returncode == 2
                      and dr2.get("refusal", {}).get("code") == "scope-refused"
                      and not (repo_dir / "5-workbench").exists(),
                      dr2.get("refusal", {}).get("code"))

        hr3 = _run(["history", "append", *hcommon, "--component", comp,
                    "--id", "G-nobody-9999-9999", "--seen", "x", "--missed", "y",
                    "--held", "z"])
        dr3 = json.loads(hr3.stdout) if hr3.stdout.strip() else {}
        passed &= _ok("red: history-unknown-id",
                      hr3.returncode == 2
                      and dr3.get("refusal", {}).get("code") == "unknown-id"
                      and hist.read_text(encoding="utf-8") == after2,
                      dr3.get("refusal", {}).get("code"))

        # ---- the non-JSON refusal names the route on stderr ----------------------
        rp = _run(["file", "--register", str(reg),
                   "--surface", "5-workbench/x", "--class", "other",
                   "--symptom", "x", "--evidence", "e", "--suggested-action", "s",
                   "--risk", "r", "--as", "fx-goal/leader"])
        passed &= _ok("red: stderr-route-pointer",
                      rp.returncode == 2 and rp.stdout.strip() == ""
                      and "refused: scope-refused" in rp.stderr
                      and ".rbtv/goals/fx-goal/issues.md" in rp.stderr,
                      rp.stderr.strip().replace("\n", " | "))

    print("selftest: PASS" if passed else "selftest: FAIL")
    return 0 if passed else 1


def _shared(sp):
    """--register / --json on a subcommand, without clobbering the top-level flag."""
    sp.add_argument("--register", default=argparse.SUPPRESS,
                    help="override register dir (tests only)")
    sp.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                    help="stable JSON on stdout")
    return sp


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="file-issue",
        description="File, validate and record ignite-engine register entries.",
        epilog="next: file-issue file --help",
    )
    p.add_argument("--register", help="override register dir (tests only)")
    p.add_argument("--json", action="store_true", help="stable JSON on stdout")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = _shared(sub.add_parser(
        "file", help="write one filing into register/open/<id>.md",
        description="File one system issue whose surface is under ignite/ or meta/.",
        epilog="next: file-issue show <id>"))
    f.add_argument("--surface", help="path under ignite/ or meta/ of the rbtv repo")
    f.add_argument("--class", dest="klass", choices=CLASSES, help="filing class")
    f.add_argument("--symptom", help="one-line symptom")
    f.add_argument("--evidence", help="path or command")
    f.add_argument("--suggested-action", dest="suggested_action", help="what to do")
    f.add_argument("--risk", help="one-line risk")
    f.add_argument("--as", dest="as_who", help="who files: <goal>/<seat>")
    f.add_argument("--id", help="override id (collision still suffixes -2, -3)")
    f.set_defaults(_fn=cmd_file)

    l = _shared(sub.add_parser(
        "list", help="list filings",
        description="List register entries, newest folder order, open by default.",
        epilog="next: file-issue show <id>"))
    l.add_argument("--status", choices=("open", "closed", "all"), default="open")
    l.add_argument("--class", dest="klass", choices=CLASSES)
    l.set_defaults(_fn=cmd_list)

    sh = _shared(sub.add_parser(
        "show", help="print one filing",
        description="Print one register entry whole, by id.",
        epilog="next: file-issue list"))
    sh.add_argument("id")
    sh.set_defaults(_fn=cmd_show)

    d = _shared(sub.add_parser(
        "doctor", help="validate every register entry; register path and counts",
        description="Can this tool work here, and does every entry hold the format?\n"
                    "Validates each register/open/*.md and register/closed/*.md against\n"
                    "`file-issue schema`: one line per file, then the counts. Exit 1 when\n"
                    "any entry is invalid, or the register is missing or unwritable.",
        epilog="example: file-issue --json doctor\nnext: file-issue show <id>",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    d.set_defaults(_fn=cmd_doctor)

    sc = _shared(sub.add_parser(
        "schema", help="the written record: entry keys, classes, statuses, HISTORY shape",
        description="The one written record of the register's format. Every other doc\n"
                    "points here instead of restating it.",
        epilog="example: file-issue schema --json\nnext: file-issue doctor",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    sc.set_defaults(_fn=cmd_schema)

    h = sub.add_parser(
        "history", help="the per-component memory: append one entry, or list them",
        description="Read or extend <rbtv repo>/<component>/HISTORY.md — what was seen,\n"
                    "the trials that missed, and the solution that held, per register id.",
        epilog="next: file-issue history show --component ignite/team-kit",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    hsub = h.add_subparsers(dest="history_cmd", required=True)

    ha = _shared(hsub.add_parser(
        "append", help="append one entry (creates HISTORY.md with its header when absent)",
        description="Append one dated entry to a component's HISTORY.md, creating the file\n"
                    "with its header line when it does not exist yet. Refuses a missing\n"
                    "field, a component outside ignite/ or meta/, and an id that is in\n"
                    "neither register/open nor register/closed.",
        epilog=("example: file-issue history append --component ignite/team-kit \\\n"
                "    --id G-leader-0101-0000 \\\n"
                '    --seen "doctor passed an entry with no status" \\\n'
                '    --missed "a body grep — it matched the prose, not the frontmatter" \\\n'
                '    --held "validate the parsed frontmatter against the ten entry keys"\n'
                "next: file-issue history show --component ignite/team-kit"),
        formatter_class=argparse.RawDescriptionHelpFormatter))
    ha.add_argument("--component", help="repo-relative dir under ignite/ or meta/")
    ha.add_argument("--id", help="the register id this entry belongs to")
    ha.add_argument("--seen", help="what was seen (its first line becomes the heading)")
    ha.add_argument("--missed", help="the trials that missed, and why")
    ha.add_argument("--held", help="the solution that held")
    ha.add_argument("--repo", default=argparse.SUPPRESS,
                    help="override the rbtv repo root (tests only)")
    ha.set_defaults(_fn=cmd_history_append, repo=None)

    hs = _shared(hsub.add_parser(
        "show", help="list a component's HISTORY entries",
        description="One line per entry: date, register id, heading. Quiet when the\n"
                    "component has no HISTORY.md yet.",
        epilog="example: file-issue history show --component meta/planning --json\n"
               "next: file-issue history append --component <dir> --id <register-id>",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    hs.add_argument("--component", help="repo-relative dir under ignite/ or meta/")
    hs.add_argument("--repo", default=argparse.SUPPRESS,
                    help="override the rbtv repo root (tests only)")
    hs.set_defaults(_fn=cmd_history_show, repo=None)

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
