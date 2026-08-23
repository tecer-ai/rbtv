#!/usr/bin/env python3
"""file-issue — the ignite-engine register's filer/validator, and the ignite
build-memory filer.

The command inventory lives in the argument parser: run `file-issue --help`.
The register's entry format, class enum and status vocabulary live in one
place too: run `file-issue schema`. The build memory (closed issues and
creations under `ignite/work-on-ignite/memory/<component>/`) is documented in
`ignite/work-on-ignite/references/build-memory.md`; this file only writes it.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
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
REGISTER_REL = Path(".rbtv") / "goals" / "ignite-engine" / "register"

# The 19 build-memory components: the 15 top-level ignite/ folders (minus
# node_modules) plus the four meta/ trees. One memory folder per name under
# ignite/work-on-ignite/memory/. See work-on-ignite.md.
MEMORY_COMPONENTS = (
    "bridges", "capabilities", "cli", "config", "deploy", "engine", "gateway",
    "injection-ladder", "jobs", "launch-profiles", "lib", "server", "skills",
    "team-kit", "work-on-ignite",
    "meta-installer", "meta-leader", "meta-master-agent", "meta-planning",
)
MEMORY_ISSUE_HEADINGS = ("Seen", "Missed", "Held")
MEMORY_CREATION_HEADINGS = ("What it is", "Why", "How to use & where wired", "ATTENTION")
MEMORY_LINE_TARGET = 280
MEMORY_LINE_CAP = 400


class Refuse(Exception):
    def __init__(self, code, message, *, route=None, extra=None, exit_code=2):
        super().__init__(message)
        self.code = code
        self.message = message
        self.route = route
        self.extra = extra or {}
        self.exit_code = exit_code


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
    return emit({"ok": False, "refusal": ref}, as_json=as_json, exit_code=exc.exit_code)


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


def unknown_component_refusal(component: str) -> Refuse:
    return Refuse(
        "unknown-component",
        f"{component!r} is not one of the 19 memory components",
        extra={"fix": "pick one of: " + ", ".join(MEMORY_COMPONENTS)},
    )


def memory_root(cwd: Path, override: str | None) -> Path:
    repo = repo_root(cwd, override)
    return repo / "ignite" / "work-on-ignite" / "memory"


def kebab(text: str, limit: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:limit].rstrip("-") or "entry"


def entry_stem(mem_dir: Path, date_compact: str, letter: str, name: str) -> str:
    base = f"{date_compact}-{letter}-{name}"
    if not (mem_dir / f"{base}.md").exists():
        return base
    n = 2
    while (mem_dir / f"{base}-{n}.md").exists():
        n += 1
    return f"{base}-{n}"


def parse_sections(text: str) -> dict:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def missing_heading(sections: dict, kind: str) -> str | None:
    required = MEMORY_ISSUE_HEADINGS if kind == "issue" else MEMORY_CREATION_HEADINGS
    for h in required:
        content = sections.get(h)
        if content is None or not any(l.strip() for l in content):
            return h
    return None


def first_nonempty(lines: list[str]) -> str:
    for l in lines:
        if l.strip():
            return one_line(l)
    return ""


def derive_clause(sections: dict, kind: str) -> str:
    if kind == "issue":
        seen = first_nonempty(sections.get("Seen", []))
        held = first_nonempty(sections.get("Held", []))
        if seen and held:
            return f"{seen} → {held}"
        return seen or held
    return first_nonempty(sections.get("What it is", []))


def merge_attention(body_text: str, bullets: list[str]) -> str:
    if not bullets:
        return body_text
    lines = body_text.splitlines()
    bullet_lines = [f"- {b}" for b in bullets]
    idx = None
    for i, l in enumerate(lines):
        if l.strip() == "## ATTENTION":
            idx = i
            break
    if idx is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("## ATTENTION")
        lines.extend(bullet_lines)
    else:
        j = idx + 1
        while j < len(lines) and not lines[j].startswith("## "):
            j += 1
        lines[j:j] = bullet_lines
    return "\n".join(lines)


def render_memory_header(stem: str, title: str, kind: str, component: str, date: str,
                          commit: str | None, deployed: str | None, pin: str | None,
                          components: str | None, seeded: bool, register_id: str | None) -> str:
    lines = [f"# {stem} — {title}", "", f"kind: {kind}", f"component: {component}", f"date: {date}"]
    if commit:
        lines.append(f"commit: {commit}")
    if deployed:
        lines.append(f"deployed: {deployed}")
    if pin:
        lines.append(f"pin: {pin}")
    if components:
        lines.append(f"components: {components}")
    if seeded:
        lines.append("seeded: true")
    if register_id:
        lines.append(f"register-id: {register_id}")
    lines.append("")
    return "\n".join(lines) + "\n"


def compose_index_line(date: str, kind: str, seeded: bool, title: str, clause: str,
                        commit: str | None, other_components: str | None, attention: bool) -> str:
    parts = [date, kind]
    if seeded:
        parts.append("seeded")
    parts.append(title)
    if clause:
        parts.append(clause)
    parts.append(commit or "pending")
    parts.append(other_components or "—")
    line = " · ".join(parts)
    if attention:
        line += " · ⚠"
    return one_line(line)


def read_index_lines(mem_dir: Path, index_name: str) -> list[str]:
    p = mem_dir / index_name
    if not p.is_file():
        return []
    return [l for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def reconstruct_stem(date: str, kind: str, title: str) -> str:
    letter = "i" if kind == "issue" else "c"
    return f"{date.replace('-', '')}-{letter}-{kebab(title, 30)}"


def cmd_memory_file(args, cwd: Path) -> int:
    as_json = args.json
    kind = args.kind
    missing = []
    for name, val in (("kind", kind), ("component", args.component),
                       ("title", args.title), ("body-file", args.body_file)):
        if not (val or "").strip():
            missing.append(name)
    if missing:
        name = missing[0]
        return refuse_payload(Refuse(
            f"missing-field:{name}", f"--{name} is required",
            extra={"fix": f"pass --{name} (see file-issue memory file --help)"},
        ), as_json)
    if len(args.title) > 60:
        return refuse_payload(Refuse(
            "title-too-long", f"--title is {len(args.title)} chars (cap 60)",
        ), as_json)
    if args.component not in MEMORY_COMPONENTS:
        return refuse_payload(unknown_component_refusal(args.component), as_json)

    try:
        repo = repo_root(cwd, args.repo)
    except Refuse as exc:
        return refuse_payload(exc, as_json)
    mem_dir = repo / "ignite" / "work-on-ignite" / "memory" / args.component
    if not mem_dir.is_dir():
        return refuse_payload(Refuse(
            "component-dir-missing", f"{mem_dir} does not exist",
        ), as_json)

    body_path = Path(args.body_file).expanduser()
    try:
        body_text = body_path.read_text(encoding="utf-8")
    except OSError as exc:
        return refuse_payload(Refuse(
            "body-file-unreadable", f"could not read {body_path}: {exc}",
        ), as_json)

    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    merged_body = merge_attention(body_text, args.attention or [])
    sections = parse_sections(merged_body)
    bad = missing_heading(sections, kind)
    if bad:
        return emit({
            "ok": False,
            "refusal": {"code": f"missing-field:{kebab(bad, 40)}",
                        "message": f"body is missing required section '## {bad}'"},
        }, as_json=as_json, exit_code=1)

    letter = "i" if kind == "issue" else "c"
    name = kebab(args.title, 30)
    date_compact = date.replace("-", "")
    stem = entry_stem(mem_dir, date_compact, letter, name)

    clause = derive_clause(sections, kind)
    has_attention = bool(any(l.strip() for l in sections.get("ATTENTION", [])))
    if args.line:
        line = one_line(args.line)
    else:
        line = compose_index_line(date, kind, bool(args.seeded), args.title, clause,
                                   args.commit, args.components, has_attention)

    if len(line) > MEMORY_LINE_CAP:
        return refuse_payload(Refuse(
            "index-line-too-long",
            f"index line is {len(line)} chars (cap {MEMORY_LINE_CAP})",
            extra={"length": len(line)},
        ), as_json)
    if len(line) > MEMORY_LINE_TARGET:
        print(f"warn: index line is {len(line)} chars (target {MEMORY_LINE_TARGET})",
              file=sys.stderr)

    header = render_memory_header(stem, args.title, kind, args.component, date,
                                   args.commit, args.deployed, args.pin,
                                   args.components, bool(args.seeded), args.register_id)
    entry_path = mem_dir / f"{stem}.md"
    try:
        entry_path.write_text(header + merged_body.strip("\n") + "\n", encoding="utf-8")
    except OSError as exc:
        return refuse_payload(Refuse(
            "entry-not-writable", f"could not write {entry_path}: {exc}",
        ), as_json)

    index_name = "_issues.md" if kind == "issue" else "_creations.md"
    index_path = mem_dir / index_name
    try:
        with index_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as exc:
        return refuse_payload(Refuse(
            "index-not-writable", f"could not write {index_path}: {exc}",
        ), as_json)

    payload = {
        "ok": True, "path": str(entry_path), "index": str(index_path), "line": line,
        "text": f"filed {entry_path}\nindex: {index_path}\n"
                f"next: file-issue memory show --component {args.component}",
    }
    return emit(payload, as_json=as_json, exit_code=0)


def cmd_memory_show(args, cwd: Path) -> int:
    as_json = args.json
    if not (args.component or "").strip():
        return refuse_payload(Refuse(
            "missing-field:component", "--component is required",
        ), as_json)
    if args.component not in MEMORY_COMPONENTS:
        return refuse_payload(unknown_component_refusal(args.component), as_json)
    try:
        mem_dir = memory_root(cwd, args.repo) / args.component
    except Refuse as exc:
        return refuse_payload(exc, as_json)

    rows = []
    if args.kind in (None, "issue"):
        rows += [("issue", l) for l in read_index_lines(mem_dir, "_issues.md")]
    if args.kind in (None, "creation", "change"):
        for l in read_index_lines(mem_dir, "_creations.md"):
            fields = [x.strip() for x in l.split(" · ")]
            k = fields[1] if len(fields) > 1 else "creation"
            if args.kind and k != args.kind:
                continue
            rows.append((k, l))
    flat = [l for _, l in rows]
    if args.last:
        flat = flat[-args.last:]
    if as_json:
        return emit({"ok": True, "component": args.component, "lines": flat},
                     as_json=True, exit_code=0)
    for l in flat:
        print(l)
    if not flat:
        print(f"no entries for {args.component}")
    return 0


def cmd_memory_rotate(args, cwd: Path) -> int:
    as_json = args.json
    if not (args.component or "").strip():
        return refuse_payload(Refuse(
            "missing-field:component", "--component is required",
        ), as_json)
    if args.component not in MEMORY_COMPONENTS:
        return refuse_payload(unknown_component_refusal(args.component), as_json)
    try:
        mem_dir = memory_root(cwd, args.repo) / args.component
    except Refuse as exc:
        return refuse_payload(exc, as_json)
    if not mem_dir.is_dir():
        return refuse_payload(Refuse(
            "component-dir-missing", f"{mem_dir} does not exist",
        ), as_json)

    keep = args.keep
    threshold = args.threshold
    report = {}
    for index_name in ("_issues.md", "_creations.md"):
        p = mem_dir / index_name
        heading = None
        lines = []
        if p.is_file():
            raw = p.read_text(encoding="utf-8").splitlines()
            if raw and raw[0].startswith("#"):
                heading = raw[0]
                lines = [l for l in raw[1:] if l.strip()]
            else:
                lines = [l for l in raw if l.strip()]
        count = len(lines)
        if count > threshold:
            to_archive, to_keep = lines[:-keep] if keep else lines, lines[-keep:] if keep else []
        else:
            to_archive, to_keep = [], lines
        report[index_name] = {"count": count, "archived": len(to_archive), "kept": len(to_keep)}
        if args.dry_run or not to_archive:
            continue
        archive_path = mem_dir / "_issues-archive.md"
        if not archive_path.is_file() or not archive_path.read_text(encoding="utf-8").strip():
            archive_path.write_text(
                f"# {args.component} — date · kind · title · symptom→cause · "
                f"commit · others · ⚠ | rotated, newest last\n", encoding="utf-8")
        with archive_path.open("a", encoding="utf-8") as fh:
            for l in to_archive:
                fh.write(l + "\n")
        new_content = (heading or f"# {args.component} — index") + "\n"
        new_content += "\n".join(to_keep) + ("\n" if to_keep else "")
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(new_content, encoding="utf-8")
        tmp.replace(p)

    payload = {
        "ok": True, "component": args.component, "dry_run": bool(args.dry_run),
        "report": report,
        "text": f"rotate {'(dry-run) ' if args.dry_run else ''}{args.component}: "
                + ", ".join(f"{k}={v}" for k, v in report.items()),
    }
    return emit(payload, as_json=as_json, exit_code=0)


def cmd_memory_check(args, cwd: Path) -> int:
    as_json = args.json
    if not (args.component or "").strip():
        return refuse_payload(Refuse(
            "missing-field:component", "--component is required",
        ), as_json)
    if args.component not in MEMORY_COMPONENTS:
        return refuse_payload(unknown_component_refusal(args.component), as_json)
    try:
        mem_dir = memory_root(cwd, args.repo) / args.component
    except Refuse as exc:
        return refuse_payload(exc, as_json)
    if not mem_dir.is_dir():
        return refuse_payload(Refuse(
            "component-dir-missing", f"{mem_dir} does not exist",
        ), as_json)

    findings = []
    all_lines = []
    for index_name in ("_issues.md", "_creations.md", "_issues-archive.md"):
        for l in read_index_lines(mem_dir, index_name):
            all_lines.append((index_name, l))

    expected_stems = set()
    for src, line in all_lines:
        if len(line) > MEMORY_LINE_CAP:
            findings.append({"code": "line-too-long", "file": src,
                              "length": len(line), "line": line[:60] + "…"})
        parts = [x.strip() for x in line.split(" · ")]
        if len(parts) < 4:
            findings.append({"code": "line-malformed", "file": src, "line": line[:80]})
            continue
        date, kind = parts[0], parts[1]
        idx = 3 if parts[2] == "seeded" else 2
        if idx >= len(parts):
            findings.append({"code": "line-malformed", "file": src, "line": line[:80]})
            continue
        title = parts[idx]
        stem = reconstruct_stem(date, kind, title)
        expected_stems.add(stem)
        candidates = {stem} | {f"{stem}-{n}" for n in range(2, 6)}
        if not any((mem_dir / f"{c}.md").is_file() for c in candidates):
            findings.append({"code": "entry-missing", "file": src, "expected": f"{stem}.md"})

    stripped_expected = {re.sub(r"-\d+$", "", s) for s in expected_stems}
    entry_files = sorted(p for p in mem_dir.glob("*.md") if not p.name.startswith("_"))
    for p in entry_files:
        base = re.sub(r"-\d+$", "", p.stem)
        if base not in stripped_expected:
            findings.append({"code": "file-without-line", "file": p.name})
        text = p.read_text(encoding="utf-8")
        for field in ("kind:", "component:", "date:"):
            if field not in text:
                findings.append({"code": "header-missing-field", "file": p.name,
                                  "field": field.rstrip(":")})

    ok = not findings
    payload = {"ok": ok, "component": args.component, "findings": findings}
    if as_json:
        return emit(payload, as_json=True, exit_code=0 if ok else 1)
    if ok:
        print(f"check: PASS ({len(entry_files)} entries, {len(all_lines)} index lines)")
    else:
        for f in findings:
            print(f"finding: {f}")
        print("check: FAIL")
    return 0 if ok else 1


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
                      and set(sd) == {"entry-keys", "classes", "statuses"}
                      and sd.get("entry-keys") == want_keys
                      and sd.get("statuses", {}).get("lifecycle") == want_life
                      and sd.get("statuses", {}).get("terminal") == want_term,
                      f"txt={sc_txt.returncode} json={sc_json.returncode} keys={sorted(sd)}")

        # ---- memory: fixture tree, never the real memory folder -------------------
        repo_dir = root / "rbtv"
        mem_root = repo_dir / "ignite" / "work-on-ignite" / "memory"
        for c in MEMORY_COMPONENTS:
            cdir = mem_root / c
            cdir.mkdir(parents=True, exist_ok=True)
            heading = f"# {c} — date · kind · title · symptom→cause · commit · others · ⚠ | newest last\n"
            (cdir / "_issues.md").write_text(heading, encoding="utf-8")
            (cdir / "_creations.md").write_text(heading, encoding="utf-8")
            (cdir / "_issues-archive.md").write_text(heading, encoding="utf-8")
            (cdir / "_summary.md").write_text("No distillation yet — read the live index.\n",
                                               encoding="utf-8")
        scratch = root / "scratch"
        scratch.mkdir()
        mcommon = ["--repo", str(repo_dir), "--json"]

        issue_body = scratch / "issue-body.md"
        issue_body.write_text(
            "## Seen\nthe launcher spawned twice on restart\n\n"
            "## Missed\nrestarting alone did not stop the double spawn\n\n"
            "## Held\nadded a pid lock file before spawn\n", encoding="utf-8")

        mf1 = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "issue",
                    "--title", "double spawn on restart", "--body-file", str(issue_body),
                    "--commit", "abc1234", "--deployed", "yes", "--pin", "NONE"])
        dmf1 = json.loads(mf1.stdout) if mf1.stdout.strip() else {}
        entry1 = Path(dmf1["path"]) if dmf1.get("path") else None
        issues_line1 = read_index_lines(mem_root / "engine", "_issues.md")
        passed &= _ok("green: memory-file-issue",
                      mf1.returncode == 0 and entry1 is not None and entry1.is_file()
                      and "kind: issue" in entry1.read_text(encoding="utf-8")
                      and "## Seen" in entry1.read_text(encoding="utf-8")
                      and issues_line1 and "double spawn on restart" in issues_line1[-1]
                      and "abc1234" in issues_line1[-1],
                      f"exit={mf1.returncode} path={dmf1.get('path')} line={issues_line1[-1:]}")

        creation_body = scratch / "creation-body.md"
        creation_body.write_text(
            "## What it is\nA pid lock file the launcher takes before spawning\n\n"
            "## Why\nprevents the double-spawn seen on restart\n\n"
            "## How to use & where wired\nwired into launch-profiles/spawn\n\n"
            "## ATTENTION\n- watch lock-file permissions on a fresh clone\n", encoding="utf-8")
        mf2 = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "creation",
                    "--title", "pid lock file", "--body-file", str(creation_body),
                    "--commit", "def5678"])
        dmf2 = json.loads(mf2.stdout) if mf2.stdout.strip() else {}
        entry2 = Path(dmf2["path"]) if dmf2.get("path") else None
        creations_line1 = read_index_lines(mem_root / "engine", "_creations.md")
        passed &= _ok("green: memory-file-creation",
                      mf2.returncode == 0 and entry2 is not None and entry2.is_file()
                      and "kind: creation" in entry2.read_text(encoding="utf-8")
                      and creations_line1 and "pid lock file" in creations_line1[-1]
                      and creations_line1[-1].endswith("⚠"),
                      f"exit={mf2.returncode} line={creations_line1[-1:]}")

        bad_body = scratch / "bad-issue.md"
        bad_body.write_text("## Seen\nx\n\n## Held\ny\n", encoding="utf-8")
        mf3 = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "issue",
                    "--title", "bad body missing missed", "--body-file", str(bad_body)])
        dmf3 = json.loads(mf3.stdout) if mf3.stdout.strip() else {}
        passed &= _ok("red: memory-missing-missed",
                      mf3.returncode == 1
                      and dmf3.get("refusal", {}).get("code") == "missing-field:missed",
                      dmf3.get("refusal", {}))

        mf4 = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "issue",
                    "--title", "long line probe", "--body-file", str(issue_body),
                    "--line", "x" * 401])
        dmf4 = json.loads(mf4.stdout) if mf4.stdout.strip() else {}
        entries_before_leak = list((mem_root / "engine").glob("*long-line-probe*"))
        passed &= _ok("red: memory-line-too-long",
                      mf4.returncode == 2
                      and dmf4.get("refusal", {}).get("code") == "index-line-too-long"
                      and not entries_before_leak,
                      dmf4.get("refusal", {}))

        mf5a = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "issue",
                     "--title", "clash entry", "--body-file", str(issue_body)])
        mf5b = _run(["memory", "file", *mcommon, "--component", "engine", "--kind", "issue",
                     "--title", "clash entry", "--body-file", str(issue_body)])
        dmf5a = json.loads(mf5a.stdout) if mf5a.stdout.strip() else {}
        dmf5b = json.loads(mf5b.stdout) if mf5b.stdout.strip() else {}
        passed &= _ok("green: memory-clash-suffix",
                      mf5a.returncode == 0 and mf5b.returncode == 0
                      and dmf5a.get("path") != dmf5b.get("path")
                      and (dmf5b.get("path") or "").endswith("-2.md"),
                      f"a={dmf5a.get('path')} b={dmf5b.get('path')}")

        mf6 = _run(["memory", "file", *mcommon, "--component", "not-a-real-component",
                    "--kind", "issue", "--title", "x", "--body-file", str(issue_body)])
        dmf6 = json.loads(mf6.stdout) if mf6.stdout.strip() else {}
        passed &= _ok("red: memory-unknown-component",
                      mf6.returncode == 2
                      and dmf6.get("refusal", {}).get("code") == "unknown-component",
                      dmf6.get("refusal", {}).get("code"))

        rotate_dir = mem_root / "capabilities"
        seed_lines = [
            f"2026-08-{(i % 28) + 1:02d} · issue · seed entry {i} · x → y · c{i:04d} · —"
            for i in range(61)
        ]
        (rotate_dir / "_issues.md").write_text(
            "# capabilities — date · kind · title · symptom→cause · commit · others · ⚠ "
            "| newest last\n" + "\n".join(seed_lines) + "\n", encoding="utf-8")
        rdry = _run(["memory", "rotate", *mcommon, "--component", "capabilities", "--dry-run"])
        ddry = json.loads(rdry.stdout) if rdry.stdout.strip() else {}
        rep_dry = ddry.get("report", {}).get("_issues.md", {})
        passed &= _ok("green: memory-rotate-dry-run",
                      rdry.returncode == 0 and rep_dry.get("count") == 61
                      and rep_dry.get("archived") == 31 and rep_dry.get("kept") == 30
                      and len(read_index_lines(rotate_dir, "_issues.md")) == 61,
                      rep_dry)

        rreal = _run(["memory", "rotate", *mcommon, "--component", "capabilities"])
        dreal = json.loads(rreal.stdout) if rreal.stdout.strip() else {}
        kept_after = read_index_lines(rotate_dir, "_issues.md")
        archived_after = read_index_lines(rotate_dir, "_issues-archive.md")
        passed &= _ok("green: memory-rotate-apply",
                      rreal.returncode == 0 and len(kept_after) == 30
                      and len(archived_after) == 31
                      and kept_after[0] == seed_lines[-30]
                      and archived_after[-1] == seed_lines[30],
                      f"kept={len(kept_after)} archived={len(archived_after)}")

        check_body = scratch / "check-body.md"
        check_body.write_text(
            "## Seen\ncheck target seen\n\n## Missed\nnothing\n\n## Held\nheld\n",
            encoding="utf-8")
        mcf = _run(["memory", "file", *mcommon, "--component", "gateway", "--kind", "issue",
                    "--title", "check target", "--body-file", str(check_body)])
        chk_ok = _run(["memory", "check", *mcommon, "--component", "gateway"])
        dchk_ok = json.loads(chk_ok.stdout) if chk_ok.stdout.strip() else {}
        passed &= _ok("green: memory-check-pass",
                      mcf.returncode == 0 and chk_ok.returncode == 0
                      and dchk_ok.get("ok") is True and dchk_ok.get("findings") == [],
                      dchk_ok)

        gw_issues = mem_root / "gateway" / "_issues.md"
        raw_lines = gw_issues.read_text(encoding="utf-8").splitlines()
        raw_lines[-1] = "a hand-broken line with no separators at all"
        gw_issues.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
        chk_bad = _run(["memory", "check", *mcommon, "--component", "gateway"])
        dchk_bad = json.loads(chk_bad.stdout) if chk_bad.stdout.strip() else {}
        passed &= _ok("red: memory-check-fail",
                      chk_bad.returncode == 1 and dchk_bad.get("ok") is False
                      and any(f.get("code") == "line-malformed"
                              for f in dchk_bad.get("findings", [])),
                      dchk_bad.get("findings"))

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
        "schema", help="the written record: entry keys, classes and status vocabulary",
        description="The one written record of the register's format. Every other doc\n"
                    "points here instead of restating it.",
        epilog="example: file-issue schema --json\nnext: file-issue doctor",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    sc.set_defaults(_fn=cmd_schema)

    m = sub.add_parser(
        "memory", help="the ignite build memory: file/show/rotate/check closed craft",
        description="File, read and maintain ignite/work-on-ignite/memory/<component>/ —\n"
                    "the closed-issue and creation record that replaced per-component\n"
                    "HISTORY.md. See ignite/work-on-ignite/references/build-memory.md for the shape.",
        epilog="next: file-issue memory file --help",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    msub = m.add_subparsers(dest="memory_cmd", required=True)

    mf = _shared(msub.add_parser(
        "file", help="file one issue/creation/change entry + its index line",
        description="Copy --body-file into a new memory entry (validating it carries the\n"
                    "mandatory sections for --kind), prepend a small header, then append\n"
                    "one index line to _issues.md or _creations.md. Never rewrites an\n"
                    "existing entry or index line.",
        epilog=("example: file-issue memory file --component work-on-ignite \\\n"
                "    --kind creation --title \"cp2 probe\" --body-file body.md\n"
                "next: file-issue memory show --component <component>"),
        formatter_class=argparse.RawDescriptionHelpFormatter))
    mf.add_argument("--component", metavar="COMPONENT",
                     help="one of the 19 memory components (see MEMORY_COMPONENTS)")
    mf.add_argument("--kind", choices=("issue", "creation", "change"), help="entry kind")
    mf.add_argument("--title", help="short title, <=60 chars")
    mf.add_argument("--body-file", dest="body_file", help="path to the body markdown")
    mf.add_argument("--commit", help="hash, or comma-separated hashes")
    mf.add_argument("--deployed", help="yes|no|<iso date/time of the deploy>")
    mf.add_argument("--pin", help="probe path, or NONE")
    mf.add_argument("--components", help="other components touched, comma-separated")
    mf.add_argument("--attention", action="append",
                     help="an ATTENTION bullet (repeatable)")
    mf.add_argument("--date", help="backdate YYYY-MM-DD (seeding)")
    mf.add_argument("--seeded", action="store_true", help="mark as a backfilled entry")
    mf.add_argument("--register-id", dest="register_id", help="the OPEN-side register id, if any")
    mf.add_argument("--line", help="override the computed index line verbatim")
    mf.add_argument("--repo", default=argparse.SUPPRESS,
                     help="override the rbtv repo root (tests only)")
    mf.set_defaults(_fn=cmd_memory_file, repo=None)

    ms = _shared(msub.add_parser(
        "show", help="print a component's live index lines (newest last)",
        description="Print _issues.md and/or _creations.md index lines for one component.",
        epilog="example: file-issue memory show --component engine --last 10\n"
               "next: file-issue memory file --component <component> ...",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    ms.add_argument("--component", metavar="COMPONENT")
    ms.add_argument("--kind", choices=("issue", "creation", "change"))
    ms.add_argument("--last", type=int, help="only the last N lines")
    ms.add_argument("--repo", default=argparse.SUPPRESS,
                     help="override the rbtv repo root (tests only)")
    ms.set_defaults(_fn=cmd_memory_show, repo=None)

    mr = _shared(msub.add_parser(
        "rotate", help="move older index lines to _issues-archive.md past --threshold",
        description="When a component's live index passes --threshold lines, move all\n"
                    "but the newest --keep to _issues-archive.md. Both _issues.md and\n"
                    "_creations.md rotate into the same archive file.",
        epilog="example: file-issue memory rotate --component engine --dry-run\n"
               "next: file-issue memory check --component <component>",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    mr.add_argument("--component", metavar="COMPONENT")
    mr.add_argument("--keep", type=int, default=30)
    mr.add_argument("--threshold", type=int, default=60)
    mr.add_argument("--dry-run", action="store_true")
    mr.add_argument("--repo", default=argparse.SUPPRESS,
                     help="override the rbtv repo root (tests only)")
    mr.set_defaults(_fn=cmd_memory_rotate, repo=None)

    mc = _shared(msub.add_parser(
        "check", help="lint a component's memory: line length, entry↔line pairing, fields",
        description="Every index line <=400 chars, every line's entry file exists, every\n"
                    "entry file has a line, and every entry header carries kind/component/date.",
        epilog="example: file-issue memory check --component engine\n"
               "next: file-issue memory rotate --component <component>",
        formatter_class=argparse.RawDescriptionHelpFormatter))
    mc.add_argument("--component", metavar="COMPONENT")
    mc.add_argument("--repo", default=argparse.SUPPRESS,
                     help="override the rbtv repo root (tests only)")
    mc.set_defaults(_fn=cmd_memory_check, repo=None)

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
