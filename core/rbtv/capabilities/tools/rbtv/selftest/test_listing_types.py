"""The listing types `module` and `component`, the one source of the type
meanings, a mirror skill's block-scalar description, and what `status` says
about an installation's `.rbtv/` folders."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from discovery import SKILLS_DIR, scan_all
from lib import commands, present
from lib.help_pages import PAGES

from .fixture import _component, _file_md, _w

FOLDED = ("Folds a long description over several lines. Holds a colon: here, and a "
          "second sentence.")


def listing_types(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nLT — the listing types module and component")
    src, mirror = tmp / "lt-source", tmp / "lt-mirror"
    _file_md(_component(src, "alpha", "tools") / "skills/hammer.md", "hammer", "Drives a nail.")
    _file_md(_component(src, "alpha", "tools") / "rules/gloves.md", "gloves", "Wear gloves.")
    _file_md(_component(src, "beta", "paint") / "skills/brush.md", "brush", "Paints a wall.")
    _w(src / "beta/paint/paint.json", json.dumps(
        {"description": "Colouring walls, with a zebrawood finish.", "dependencies": []}))
    # A component of capabilities only: no installable file.
    _w(_component(src, "beta", "standards") / "capabilities/grades.md", "# Grades\n")
    _w(mirror / SKILLS_DIR / "folded" / "SKILL.md",
       "---\nname: folded\ndescription: >\n  Folds a long description over several lines.\n"
       "  Holds a colon: here, and a second sentence.\n---\n\nBody.\n")
    catalog, _ = scan_all(mirror, src)
    ws = tmp / "lt-installation"
    ws.mkdir()

    def run(*argv, as_json=True):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(catalog, [])), \
                patch.dict("os.environ", {"COLUMNS": "200"}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commands.main([*argv, "--target", str(ws), *(["--json"] if as_json else [])])
        return code, (json.loads(out.getvalue()) if as_json else out.getvalue() + err.getvalue())

    _, bare = run("list")
    _, modules = run("list", "--type", "module")
    check("LT-module — list --type module is the table bare list prints",
          modules["scope"] == "modules" and modules["files"] == bare["files"]
          and [row["id"] for row in modules["files"]] == ["hub", "alpha", "beta"], str(modules))
    _, one = run("list", "beta", "--type", "module")
    check("LT-module-name — with a module as NAME it is that module's row",
          [row["id"] for row in one["files"]] == ["beta"], str(one))
    _, comps = run("list", "--type", "component")
    ids = [row["id"] for row in comps["files"]]
    check("LT-component — list --type component is every component across modules, "
          "one without installable files included",
          comps["scope"] == "components"
          and ids == ["_hub/skills/folded", "alpha/tools", "beta/paint", "beta/standards"]
          and next(r for r in comps["files"] if r["id"] == "beta/standards")["source_files"] == 0
          and next(r for r in comps["files"] if r["id"] == "alpha/tools")["source_files"] == 2,
          str(comps))
    _, of_module = run("list", "beta", "--type", "component")
    _, plain_module = run("list", "beta")
    check("LT-component-module — with a module as NAME it is list MODULE",
          of_module["files"] == plain_module["files"]
          and [row["id"] for row in of_module["files"]] == ["beta/paint", "beta/standards"],
          str(of_module))
    _, short = run("list", "paint", "--type", "component")
    check("LT-component-name — a component's short name gives its row",
          [row["id"] for row in short["files"]] == ["beta/paint"], str(short))
    code, mixed = run("list", "--type", "module,skill")
    code_show, mixed_show = run("show", "alpha", "--type", "component,skill")
    check("LT-alone — module or component beside another type is a usage refusal",
          code == code_show == 2 and mixed["error"]["code"] == "usage"
          and "stands alone" in mixed["error"]["message"]
          and "stands alone" in mixed_show["error"]["message"], str((mixed, mixed_show)))
    for verb in ("add", "remove"):
        for kind in ("pack", "module", "component"):
            code, refused = run(verb, "--type", kind)
            check(f"LT-change — {verb} --type {kind} is an unknown type there",
                  code == 2 and f"--type '{kind}' is unknown" in refused["error"]["message"]
                  and "\n  pack " not in refused["error"]["message"], str(refused))

    code, shown = run("show", "paint")
    check("LT-show-short — show reads a name that is no file as a component's short name",
          code == 0 and shown["selection"]["scope"] == "component"
          and shown["selection"]["id"] == "beta/paint", str(shown))
    code, empty = run("show", "standards")
    code_text, empty_text = run("show", "beta/standards", as_json=False)
    check("LT-show-empty — a component without installable files is shown, not refused",
          code == code_text == 0 and empty["selection"]["id"] == "beta/standards"
          and empty["selection"]["files"] == []
          and empty["next"].startswith("rbtv list beta ")
          and "Local source: 0 file(s) in this component." in empty_text, str(empty))
    _w(src / "alpha/tools/skills/tools.md",
       "---\nname: tools\ndescription: \"A file named as its component.\"\n---\n\nBody.\n")
    catalog, _ = scan_all(mirror, src)
    _, as_file = run("show", "tools")
    _, as_component = run("show", "tools", "--type", "component")
    check("LT-show-type — a name shared by a file and a component is the file; "
          "--type component reads it as the component",
          as_file["selection"]["scope"] == "file"
          and as_component["selection"]["scope"] == "component"
          and as_component["selection"]["id"] == "alpha/tools", str((as_file, as_component)))
    code, as_module = run("show", "alpha", "--type", "module")
    code_bad, not_module = run("show", "paint", "--type", "module")
    check("LT-show-module — --type module requires a module",
          code == 0 and as_module["selection"]["scope"] == "module"
          and code_bad == 1 and not_module["error"]["code"] == "module-unknown",
          str((as_module, not_module)))
    code, unknown = run("show", "nothing-like-it")
    check("LT-show-unknown — a name that is neither stays an unknown name",
          code == 1 and unknown["error"]["code"] == "name-unknown", str(unknown))

    _, found = run("search", "zebrawood")
    check("LT-search — search matches a component's description by default",
          [(row["id"], row["type"]) for row in found["files"]] == [("beta/paint", "component")]
          and found["files"][0]["source_files"] == 1, str(found))
    _, by_module = run("search", "beta", "--type", "module")
    _, by_component = run("search", "beta", "--type", "component")
    check("LT-search-type — --type module or component narrows a search to those rows",
          [row["id"] for row in by_module["files"]] == ["beta"]
          and [row["id"] for row in by_component["files"]] == ["beta/paint", "beta/standards"],
          str((by_module, by_component)))
    _, text = run("search", "zebrawood", as_json=False)
    check("LT-search-text — a component among search results shows its count of files",
          "component  0/1 files" in text
          and "installed files out of source files for a module or component" in text, text)

    print("\nLT — one source for the type meanings")
    lib = Path(present.__file__).resolve().parent
    source = "".join(p.read_text(encoding="utf-8") for p in sorted(lib.glob("*.py")))
    check("LT-one-source — the tool and pack meanings are written once under lib/",
          source.count(present.TYPE_MEANING["tool"]) == 1
          and source.count(present.TYPE_MEANING["pack"]) == 1
          and "COMMAND_GROUPS" not in source and "root_help" not in source)
    check("LT-pages — list, search and show carry every listing type; add and remove "
          "carry the exposure methods only",
          all(present.types_block() in PAGES[page] for page in ("list", "search", "show"))
          and all(present.types_block(change=page) in PAGES[page]
                  and "\n  pack " not in PAGES[page] and "\n  module " not in PAGES[page]
                  for page in ("add", "remove")))

    print("\nLT — a mirror skill's description written as a block")
    _, skills = run("list", "--type", "skill", "--full")
    row = next(r for r in skills["files"] if r["id"] == "_hub/skills/folded#folded")
    _, short_rows = run("list", "--type", "skill")
    short_row = next(r for r in short_rows["files"] if r["id"] == "_hub/skills/folded#folded")
    _, shown = run("show", "folded")
    check("LT-folded — list shows a folded description's text, whole with --full, "
          "and show the whole text",
          row["description"] == FOLDED
          and short_row["description"] == "Folds a long description over several lines."
          and shown["selection"]["files"][0]["description"] == FOLDED,
          str((row, short_row)))

    print("\nLT — status names the .rbtv/ folders that exist")
    _, before = run("status")
    run("add", "hammer", "--harness", "claude", "--guidance", "none")
    _, after = run("status")
    (ws / ".rbtv/runtime").mkdir()
    _, with_runtime = run("status")
    _, text = run("status", as_json=False)
    check("LT-status — one line per existing folder with its page; no folder, no block",
          before["installation_folder"] == {}
          and list(after["installation_folder"]) == ["mirror", "config"]
          and list(with_runtime["installation_folder"]) == ["mirror", "config", "runtime"]
          and "  runtime/  operational data. Page: core/rbtv/capabilities/glossary/runtime.md\n"
          in text and "memory/" not in text
          and "Installation folder .rbtv/ (pages are in the rbtv source, " in text, text)
    check("LT-status-pages — every page the folder table names exists in the rbtv source",
          all((present.REPO_ROOT / page).is_file()
              for page in (present.RBTV_FOLDER_PAGE, *(row[2] for row in present.RBTV_FOLDERS))))
