"""The structure page, the optional PARA component, and `rbtv structure`."""
from __future__ import annotations

import contextlib
import io
import re

from discovery import scan_all

from lib import commands, frontmatter, present
from lib.constants import REPO_ROOT
from lib.operations import do_install, do_uninstall

_LABELS = (
    "ST-01 — structure agent prints the agent section of the maintained page",
    "ST-02 — meta/para is an optional component with unnumbered targets",
    "ST-03 — structure with no kind lists the five kinds",
    "ST-04 — a scratch copy of the agent section changes the output",
    "ST-05 — structure para refuses until the component is installed, then prints its page",
    "ST-06 — an unknown kind is usage, and the command writes nothing",
    "ST-07 — installing meta/para keeps an sb block and outside text, and a re-run changes nothing",
    "ST-08 — a mirror folder-instructions component uses the same marked section, and removal restores outside text",
    "ST-09 — area and project templates render a name into the sb-os index shape",
    "ST-10 — structure agent, project and area each print the work convention from the page",
)

_NUMBERED = re.compile(r"1-projects|2-areas|3-resources|4-archives|5-workbench")
_SB = "<!-- sb:start v=1 -->\nsb kept\n<!-- sb:end -->\n"


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = commands.main(argv)
    return code, out.getvalue(), err.getvalue()


def _render(text: str, name: str) -> str:
    return text.replace("{name}", name)


def structure(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nST — structure page and PARA guidance")
    if getattr(commands, "cmd_structure", None) is None or not hasattr(present, "STRUCTURE_KINDS"):
        for label in _LABELS:
            check(label, False, "structure command absent")
        return

    page_path = REPO_ROOT / "core/rbtv/capabilities/methods/folder-structure.md"
    para_root = REPO_ROOT / "meta/para"
    page = page_path.read_text(encoding="utf-8")
    agent = commands.kind_text(page_path, "agent")
    ws = tmp / "st-structure"
    ws.mkdir()
    code, out, err = _run(["structure", "agent", "--target", str(ws)])
    check(_LABELS[0],
          code == 0 and out == agent and err == ""
          and page.splitlines()[0] != ""
          and page.startswith("# Folder structure\n")
          and "## Mandatory for rbtv" in page
          and ".rbtv/" in page
          and "config/install.json" in page
          and "mirror/" in page
          and "agents/" in page
          and "foundations" in agent
          and "backlog/" in agent
          and "prompt.md" in agent
          and "work/" in agent
          and "tmp/" in agent
          and "## project" not in agent
          and "one index" in commands.section_text(page_path, "project").lower()
          and "instruction file" in commands.section_text(page_path, "area").lower()
          and "workflow.md" in commands.section_text(page_path, "plan")
          and "agents/" in commands.section_text(page_path, "plan"),
          out[:240] + err[:240])

    numbered = []
    build_hits = []
    targets = {}
    for path in para_root.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _NUMBERED.search(text):
            numbered.append(path.name)
        if "build/" in text or "build/old/" in text:
            build_hits.append(path.name)
        if path.parent.name == "folder-instructions":
            fm, _body = frontmatter.split(text)
            targets[path.name] = None if fm is None else fm.get("target")
    record = para_root / "para.json"
    check(_LABELS[1],
          record.is_file()
          and "capabilities/templates/" in record.read_text(encoding="utf-8")
          and not numbered and not build_hits
          and targets == {
              "root.md": ".",
              "projects.md": "projects",
              "areas.md": "areas",
              "resources.md": "resources",
              "archives.md": "archives",
              "workbench.md": "workbench",
          }
          and (para_root / "capabilities/methods/para.md").is_file(),
          f"numbered={numbered} build={build_hits} targets={targets}")

    code, listed, err = _run(["structure", "--target", str(ws)])
    check(_LABELS[2],
          code == 0 and err == ""
          and all(name in listed and purpose in listed
                  for name, purpose in present.STRUCTURE_KINDS)
          and listed.count("para") >= 1,
          listed[:300])

    scratch = tmp / "scratch-structure.md"
    scratch.write_text(page.replace("## agent\n", "## agent\nSCRATCH-MARK\n", 1),
                       encoding="utf-8")
    saved = commands.structure_page
    commands.structure_page = scratch
    try:
        code, changed, err = _run(["structure", "agent", "--target", str(ws)])
    finally:
        commands.structure_page = saved
    check(_LABELS[3],
          code == 0 and "SCRATCH-MARK" in changed and changed != agent and err == "",
          changed[:200])

    code, refused, err = _run(["structure", "para", "--target", str(ws)])
    catalog, _shadowed = scan_all(tmp / "st-no-mirror", REPO_ROOT)
    installed = do_install(ws, catalog, ["meta/para"], ["claude"], False)
    code_after, printed, err_after = _run(["structure", "para", "--target", str(ws)])
    para_text = (para_root / "capabilities/methods/para.md").read_text(encoding="utf-8")
    if not para_text.endswith("\n"):
        para_text += "\n"
    check(_LABELS[4],
          code != 0 and "rbtv add meta/para" in (refused + err)
          and "rbtv add meta/para" in (para_text)
          and ".rbtv/mirror/" in para_text
          and code_after == 0 and printed == para_text and err_after == ""
          and "meta/para" in installed.get("installed", installed.get("report", {})),
          f"before={code} {err[:200]} after={code_after} {printed[:120]}")

    before = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*"))
    code, _out, err = _run(["structure", "no-such-kind", "--target", str(ws), "--dry-run"])
    after = sorted(p.relative_to(ws).as_posix() for p in ws.rglob("*"))
    check(_LABELS[5],
          code == 2 and "unknown" in err and before == after,
          err[:240])

    coexist = tmp / "st-coexist"
    owner_before = "Keep this.\n"
    owner_after = "And this.\n"
    original = owner_before + _SB + owner_after
    (coexist / "CLAUDE.md").parent.mkdir(parents=True)
    (coexist / "CLAUDE.md").write_text(original, encoding="utf-8")
    first = do_install(coexist, catalog, ["meta/para"], ["claude"], False)
    body = (coexist / "CLAUDE.md").read_text(encoding="utf-8")
    projects = coexist / "projects" / "CLAUDE.md"
    again = do_install(coexist, catalog, ["meta/para"], ["claude"], False)
    check(_LABELS[6],
          body.startswith(owner_before)
          and _SB in body
          and owner_after in body
          and "<!-- rbtv:start meta/para -->" in body
          and projects.is_file()
          and "<!-- rbtv:start meta/para -->" in projects.read_text(encoding="utf-8")
          and again.get("written") == [] and again.get("shared_written") == []
          and (coexist / "CLAUDE.md").read_text(encoding="utf-8") == body,
          f"first={first.get('written')} again={again.get('written')} body={body[:400]}")

    mirror_ws = tmp / "st-mirror"
    mirror_ws.mkdir()
    owner = "Mirror owner.\n"
    (mirror_ws / "CLAUDE.md").write_text(owner, encoding="utf-8")
    mirror = mirror_ws / ".rbtv" / "mirror"
    comp = mirror / "stmirror" / "stbox"
    (comp / "stmirror.json").parent.mkdir(parents=True)
    (mirror / "stmirror" / "stmirror.json").write_text(
        '{"description": "Mirror module for the structure check."}\n', encoding="utf-8")
    (comp / "stbox.json").write_text(
        '{"description": "Mirror folder instructions for the structure check.", "dependencies": []}\n',
        encoding="utf-8")
    guide = comp / "folder-instructions" / "note.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("---\ntarget: .\n---\n\nmirror section\n", encoding="utf-8")
    mirror_cat, _shadowed = scan_all(mirror, tmp / "st-mirror-repo")
    do_install(mirror_ws, mirror_cat, ["stmirror/stbox"], ["claude"], False)
    marked = (mirror_ws / "CLAUDE.md").read_text(encoding="utf-8")
    do_uninstall(mirror_ws, mirror_cat, ["stmirror/stbox"], False)
    restored = (mirror_ws / "CLAUDE.md").read_text(encoding="utf-8")
    check(_LABELS[7],
          "<!-- rbtv:start stmirror/stbox -->" in marked
          and "mirror section" in marked
          and owner in marked
          and restored == owner,
          f"marked={marked!r} restored={restored!r}")

    rendered_ok = True
    detail = ""
    names = ("area-index.md", "project-index.md", "area-instructions.md", "project-instructions.md")
    template_dir = para_root / "capabilities/templates"
    for name in names:
        path = template_dir / name
        if not path.is_file():
            rendered_ok = False
            detail = f"missing {name}"
            break
        rendered = _render(path.read_text(encoding="utf-8"), "launch-review")
        if name.endswith("instructions.md"):
            ok = (rendered.startswith("read `launch-review.md` first.")
                  and "## Rules of this folder" in rendered
                  and "| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |" not in rendered
                  and "<!--" not in rendered
                  and not rendered.startswith("---"))
        else:
            fm, body = frontmatter.split(rendered)
            ok = (isinstance(fm, dict)
                  and fm.get("type") == "index"
                  and isinstance(fm.get("tags"), list)
                  and fm["tags"][:1] == ["launch-review"]
                  and "## Description" in body
                  and "| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |" in body
                  and (name != "project-index.md" or "area" in fm))
        if not ok:
            rendered_ok = False
            detail = f"{name} {rendered[:240]}"
            break
    check(_LABELS[8], rendered_ok, detail)

    sentence = (
        "Loose ends of work are filed in `loose-ends/` inside the `backlog/` "
        "of the convention's root"
    )
    shared = commands.section_text(page_path, "Work convention")
    printed = {}
    for kind in ("agent", "project", "area"):
        code, out, err = _run(["structure", kind, "--target", str(ws)])
        printed[kind] = (code, out, err)
    kind_only = {
        kind: commands.section_text(page_path, kind)
        for kind in ("agent", "project", "area")
    }
    scratch = tmp / "convention-scratch.md"
    scratch.write_text(
        page.replace("## Work convention\n", "## Work convention\nCONVENTION-MARK\n", 1),
        encoding="utf-8")
    saved = commands.structure_page
    commands.structure_page = scratch
    try:
        marked = {
            kind: _run(["structure", kind, "--target", str(ws)])
            for kind in ("agent", "project", "area")
        }
    finally:
        commands.structure_page = saved
    check(_LABELS[9],
          page.count(sentence) == 1
          and sentence in shared
          and all(code == 0 and err == "" and shared in out and sentence not in kind_only[kind]
                   for kind, (code, out, err) in printed.items())
          and all(code == 0 and "CONVENTION-MARK" in out
                   for code, out, _err in marked.values()),
          f"once={page.count(sentence)} printed={ {k: v[0] for k, v in printed.items()} }")
