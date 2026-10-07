"""A link written from the repository root or from `.rbtv/` is rewritten to an
absolute path in each copy the program writes: a rule for each harness, the
prompt of an agent placed in an installation, and a skill or a command. A
relative link stays as written in a rule and a prompt; in the copy of a skill
or a command it becomes an absolute path into the source's folder."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from discovery import module_folders, scan_all

from lib.agents import add_agent
from lib.constants import MATRIX, REPO_ROOT
from lib.operations import do_install

from .fixture import _component, _file_md, _w

# A path from the source's folder, written three ways.
RELATIVE = ("[beside](./sibling.md)", "[above](../other.md)", "[bare](bare.md)")
# Left as written in every copy.
FIXED = ("[url](https://example.com/core/page.md)", "[anchor](#section)")
# Left as written in a rule and a prompt.
AS_WRITTEN = RELATIVE + FIXED


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
    skill = comp / "skills/linked-skill.md"
    _file_md(skill, "linked-skill", "A skill with links", body + "A path in code: `./sibling.md`.\n")
    command = comp / "commands/linked-command.md"
    _file_md(command, "linked-command", "A command with links", body)
    prompt = comp / "agents/research/agent.md"
    _w(prompt, "---\nname: research\n---\n\n" + body)
    _w(comp / "agents/research/agent.json",
       '{"name": "research", "description": "Research."}\n')
    before = {path: path.read_bytes() for path in (rule, skill, command, prompt)}
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

    ws = tmp / "ws-link-paths-copy"
    ws.mkdir()
    do_install(ws, catalog, ["moda/comp"], ["claude", "codex", "opencode"], dry_run=False,
               parts=["moda/comp#linked-skill", "moda/comp#linked-command"])

    def from_source(source: Path) -> list[str]:
        """The three relative links as absolute paths into the source's folder."""
        return [f"[{label}]({form})" for label, to in (
                    ("beside", source.parent / "sibling.md"),
                    ("above", source.parent.parent / "other.md"),
                    ("bare", source.parent / "bare.md"))
                for form in [to.resolve().as_posix()]]

    def angled(link: str) -> str:
        return link.replace("](", "](<").replace(")", ">)")

    for kind, source in (("skill", skill), ("command", command)):
        for harness in ("claude", "codex", "opencode"):
            rel = MATRIX[kind][harness].format(name=source.stem)
            text = (ws / rel).read_text(encoding="utf-8")
            check(f"LP-{kind}-{harness} — the links from the repository root and from "
                  f"`.rbtv/` are absolute paths in {rel}", rewritten(text, ws), text)
            check(f"LP-{kind}-{harness}-relative — `./`, `../` and bare targets are "
                  "absolute paths into the source's folder",
                  all(link in text or angled(link) in text for link in from_source(source))
                  and not any(link in text for link in RELATIVE), text)
            check(f"LP-{kind}-{harness}-fixed — a URL and an anchor are left as written",
                  all(link in text for link in FIXED), text)
    text = (ws / MATRIX["skill"]["claude"].format(name="linked-skill")).read_text(
        encoding="utf-8")
    check("LP-skill-code — a path inside a code span is left as written",
          "`./sibling.md`" in text, text)

    ws = tmp / "ws-link-paths-agent"
    ws.mkdir()
    with patch("lib.agents.cast_catalog", return_value={"claude": {"m1": {"rungs": ["low", "high"], "selected": True}}}):
        add_agent(ws, "research", [], set(), catalog, False,
                  {"harness": "claude", "model": "m1", "effort": "high"})
    text = (ws / ".rbtv/agents/research/agent.md").read_text(encoding="utf-8")
    check("LP-prompt — the two links of a placed agent's prompt are absolute paths",
          rewritten(text, ws), text)
    check("LP-prompt-relative — a relative link, a URL and an anchor are left as written",
          all(link in text for link in AS_WRITTEN), text)
    check("LP-source — the source files are not changed",
          all(path.read_bytes() == data for path, data in before.items()))
