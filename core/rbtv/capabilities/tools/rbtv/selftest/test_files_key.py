"""A record whose key is `units` is read as one whose key is `files`, and the
next write of that record carries `files`: install.json, agent.json, a pack."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from discovery import file_rows, scan_all

from lib.agents import update_agent
from lib.catalog import catalog_packs
from lib.commands import _HANDLERS
from lib.constants import AGENT_RECORD, STATE_REL
from lib.parser import build_parser
from lib.state import read_state

from .fixture import _component, _file_md, _w


def _with_old_key(path: Path) -> list[str]:
    """Rewrite the record at `path` as an earlier program wrote it, with its
    chosen files under `units`. Returns that list."""
    record = json.loads(path.read_text(encoding="utf-8"))
    record["units"] = record.pop("files")
    _w(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record["units"]


def _on_disk(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def old_key_read_and_rewritten(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    catalog = ctx.frame()[0]
    print("\nFK — a record with the key `units` is read, and rewritten with `files`")

    def run(target: Path, *argv: str) -> int:
        args = build_parser().parse_args(list(argv))
        with contextlib.redirect_stdout(io.StringIO()):
            return _HANDLERS[args.verb](args, target, catalog, [])

    for scope in ("scaffolding", "all"):
        root = tmp / f"ws-files-key-{scope}"
        root.mkdir()
        run(root, "add", "fixskill", "--harness", "claude", "--guidance", "none")
        book = root / STATE_REL
        check(f"FK-write-{scope} — install.json is written with `files`, never `units`",
              _on_disk(book).get("files") == ["fixmod/goodcomp#fixskill"]
              and "units" not in _on_disk(book), str(sorted(_on_disk(book))))
        chosen = _with_old_key(book)
        read = read_state(root)
        check(f"FK-read-{scope} — install.json with `units` is read as `files`",
              read.get("files") == chosen and "units" not in read, str(sorted(read)))
        (root / ".claude/skills/fixskill/SKILL.md").unlink()
        previewed = run(root, "update", scope, "--dry-run")
        check(f"FK-preview-{scope} — a preview leaves the old record as it is",
              previewed == 0 and _on_disk(book).get("units") == chosen
              and "files" not in _on_disk(book), str(sorted(_on_disk(book))))
        updated = run(root, "update", scope)
        check(f"FK-rewrite-{scope} — `rbtv update {scope}` applies the old record "
              "and writes it with `files`",
              updated == 0 and _on_disk(book).get("files") == chosen
              and "units" not in _on_disk(book)
              and (root / ".claude/skills/fixskill/SKILL.md").is_file(),
              str(sorted(_on_disk(book))))

    agent_root = tmp / "ws-files-key-agent"
    agent = agent_root / ".rbtv/agents/scout"
    _w(agent / "agent.md", "---\nname: scout\n---\n\nScout.\n")
    _w(agent / AGENT_RECORD, json.dumps({
        "name": "scout", "description": "Scout.", "harness": "claude",
        "model": "m1", "effort": "high",
        "units": ["fixmod/goodcomp#fixskill"], "packs": []}) + "\n")
    result = update_agent(agent_root, "scout", "scaffolding", catalog, False)
    record = _on_disk(agent / AGENT_RECORD)
    check("FK-agent — `rbtv agent update` applies an agent.json with `units` "
          "and writes it with `files`",
          result["files"] == ["fixmod/goodcomp#fixskill"]
          and record.get("files") == ["fixmod/goodcomp#fixskill"]
          and "units" not in record
          and (agent / ".claude/skills/fixskill/SKILL.md").is_file(), str(sorted(record)))

    source = tmp / "files-key-source"
    comp = _component(source, "moda", "comp")
    _file_md(comp / "rules/kiss.md", "kiss", "Kiss", "body\n")
    _w(comp / "packs/old.json", json.dumps({
        "description": "A pack written with the old key",
        "units": ["moda/comp#kiss"]}))
    _w(comp / "agents/research/agent.md", "---\nname: research\n---\n\nResearch.\n")
    _w(comp / "agents/research/agent.json", json.dumps({
        "name": "research", "description": "Research.", "units": ["kiss"], "packs": []}) + "\n")
    old_catalog, _ = scan_all(tmp / "files-key-mirror", source)
    pack = catalog_packs(old_catalog).get("old") or {}
    check("FK-pack — a pack with `units` is read as `files`",
          pack.get("files") == ["moda/comp#kiss"] and "units" not in pack, str(pack))
    shipped = next(row["data"] for row in file_rows(old_catalog["moda/comp"])
                   if row["method"] == "agent")
    check("FK-shipped-agent — an agent.json a component ships with `units` is read as `files`",
          shipped.get("files") == ["kiss"] and "units" not in shipped, str(shipped))
