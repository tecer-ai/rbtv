"""A link written from the repository root or from `.rbtv/` is rewritten to an
absolute path in each copy the program writes: a rule for each harness, and the
prompt of an agent placed in an installation. A relative link stays as written."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from discovery import module_folders, scan_all

from lib.agents import add_agent
from lib.constants import MATRIX, REPO_ROOT
from lib.operations import do_install

from .fixture import _component, _file_md, _w

# Left as written: a path from the source's folder, a URL, an anchor.
AS_WRITTEN = ("[beside](./sibling.md)", "[above](../other.md)", "[bare](bare.md)",
              "[url](https://example.com/core/page.md)", "[anchor](#section)")


def links_rewritten_on_copy(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nLP — a link from the repository root or from `.rbtv/` is absolute in every copy")
    module = module_folders(REPO_ROOT)[0]
    body = (f"Open [the page]({module}/some/page.md#part) and "
            "[the note](.rbtv/memory/note.md).\n\n"
            + "\n".join(f"- {link}" for link in AS_WRITTEN) + "\n")
    source = tmp / "link-paths-source"
    comp = _component(source, "moda", "comp")
    rule = comp / "rules/linked.md"
    _file_md(rule, "linked", "A rule with links", body)
    prompt = comp / "agents/research/agent.md"
    _w(prompt, "---\nname: research\n---\n\n" + body)
    _w(comp / "agents/research/agent.json",
       '{"name": "research", "description": "Research."}\n')
    before = {path: path.read_bytes() for path in (rule, prompt)}
    catalog, _ = scan_all(tmp / "link-paths-mirror", source)

    def rewritten(text: str, installation: Path) -> bool:
        page = (REPO_ROOT / module / "some/page.md").resolve().as_posix() + "#part"
        note = (installation / ".rbtv/memory/note.md").resolve().as_posix()
        # A path with a space in it (a temporary folder on Windows) is written in angles.
        return (any(f"[the page]({form})" in text for form in (page, f"<{page}>"))
                and any(f"[the note]({form})" in text for form in (note, f"<{note}>"))
                and f"]({module}/" not in text and "](.rbtv/" not in text)

    for harness, rel in (("claude", MATRIX["rule"]["claude"].format(name="linked")),
                         ("codex", "AGENTS.md"), ("opencode", "AGENTS.md")):
        ws = tmp / f"ws-link-paths-{harness}"
        ws.mkdir()
        do_install(ws, catalog, ["moda/comp"], [harness], dry_run=False,
                   parts=["moda/comp#linked"])
        text = (ws / rel).read_text(encoding="utf-8")
        check(f"LP-rule-{harness} — the rule's two links are absolute paths in {rel}",
              rewritten(text, ws), text)
        check(f"LP-rule-{harness}-relative — a relative link, a URL and an anchor are "
              "left as written",
              all(link in text for link in AS_WRITTEN), text)

    ws = tmp / "ws-link-paths-agent"
    ws.mkdir()
    with patch("lib.agents.cast_catalog", return_value={"claude": {"m1": ["low", "high"]}}):
        add_agent(ws, "research", [], set(), catalog, False,
                  {"harness": "claude", "model": "m1", "effort": "high"})
    text = (ws / ".rbtv/agents/research/agent.md").read_text(encoding="utf-8")
    check("LP-prompt — the two links of a placed agent's prompt are absolute paths",
          rewritten(text, ws), text)
    check("LP-prompt-relative — a relative link, a URL and an anchor are left as written",
          all(link in text for link in AS_WRITTEN), text)
    check("LP-source — the source files are not changed",
          all(path.read_bytes() == data for path, data in before.items()))
