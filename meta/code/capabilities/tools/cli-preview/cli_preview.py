#!/usr/bin/env python3
"""cli-preview: init / check / build a CLI output review as offline HTML.

Standard library only. Invoke by path, e.g.:
    python cli_preview.py init my-review/
    python cli_preview.py check my-review/
    python cli_preview.py build my-review/ --out my-review/preview.html

Exit codes: 0 success; 1 refused or check failed; 2 invalid arguments
(argparse's own convention for a bad command line, e.g. a missing
required option or an unknown flag).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import contract  # noqa: E402
import renderer  # noqa: E402


def _print_issues_text(issues: list[dict]) -> None:
    for it in issues:
        loc = it["file"] if it["line"] is None else f"{it['file']}:{it['line']}"
        print(f"{loc}: {it['message']}\n  fix: {it['fix']}")


def _emit(json_mode: bool, ok: bool, payload: dict, text_lines: list[str] | None = None) -> int:
    """Always produce visible output: JSON on stdout in --json mode, or the
    given text_lines (title, result, recovery hint) in text mode. A missing
    text_lines with ok=False falls back to the 'error' payload field so a
    refusal is never silent."""
    if json_mode:
        print(json.dumps({"ok": ok, **payload}, ensure_ascii=False))
    else:
        if text_lines:
            for line in text_lines:
                print(line)
        elif not ok and "error" in payload:
            print(f"ERROR: {payload['error']}")
    return 0 if ok else 1


_argv_has_json = False  # set once per main() call, read by every (sub)parser's error()


class _JsonAwareArgumentParser(argparse.ArgumentParser):
    """On a parse error, emit one JSON failure on stdout (and nothing on
    stderr) when --json was anywhere on the command line, matching the
    --json contract even for arguments argparse itself rejects. Subparsers
    (created via add_subparsers) inherit this class automatically, and are
    invoked through parse_known_args rather than parse_args, so the --json
    flag is detected once via the module-level flag, not per-instance."""

    def error(self, message: str) -> None:
        if _argv_has_json:
            print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
            self.exit(2)
        super().error(message)


TEMPLATE_REVIEW_MD = """# Review: Example CLI review

Fixture: describe the tool/version under review and any fictional state
screens rely on (e.g. "workspace `demo/` has two items installed").

## Command inventory

List every command path in scope, one per bullet, exactly as it will be
typed (bare paths, no flags). Every entry here needs at least one screen
below with a matching `Command-path:`, `Help: yes`, and a -h/--help token
in its `Command:`.

- `example`
- `example list`
"""

TEMPLATE_SCREENS_MD = """<!--
Screen file. Sorted with other *.md files (not review.md) by filename.
Each screen is:

  ## <numeric id>. <title>
  Category: ...
  Command: `...`
  Terminal width: 100
  Scenario: ...
  Exit code: 0
  Command-path: example         (required, must match review.md inventory)
  Help: yes                      (optional; needs -h/--help in Command)

  ```text
  <exact literal terminal output>
  ```

A ```json fence must be strict, valid JSON (no NaN/Infinity). Screen ids
must be globally unique across every screens file but need not be
contiguous, and must be positive integers. Terminal width is a positive
integer; Exit code is 0-255. If a screen needs BOTH streams shown, declare
`Stream: both` and use two fenced blocks, each preceded by a literal
"Stdout:" or "Stderr:" line, stdout first. A single-stream screen showing
stderr instead of stdout declares `Stream: stderr`.
-->

## 1. Root help

Category: Help
Command: `example -h`
Terminal width: 100
Scenario: Fresh checkout, no config
Exit code: 0
Command-path: example
Help: yes

```text
usage: example [-h] {list} ...

Commands:
  list    List items

options:
  -h, --help  show this help message and exit
```

## 2. List help

Category: Help
Command: `example list -h`
Terminal width: 100
Scenario: Fresh checkout, no config
Exit code: 0
Command-path: example list
Help: yes

```text
usage: example list [-h]

List installed items.

options:
  -h, --help  show this help message and exit
```

## 3. List

Category: Catalog
Command: `example list`
Terminal width: 100
Scenario: Two items installed
Exit code: 0
Command-path: example list
Help: no

```text
ID    Description
a1    First item
a2    Second item
```
"""


def cmd_init(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    if folder.exists():
        if not folder.is_dir():
            return _emit(args.json, False, {"error": f"{folder} exists and is not a folder; refusing to overwrite"},
                          [f"init {folder}: refused", f"  {folder} exists and is a file, not a folder",
                           "  fix: choose a different path, or remove that file first"])
        if any(folder.iterdir()):
            return _emit(args.json, False, {"error": f"{folder} already exists and is not empty; refusing to overwrite"},
                          [f"init {folder}: refused", f"  {folder} already exists and is not empty",
                           "  fix: choose an empty or new folder path"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "review.md").write_text(TEMPLATE_REVIEW_MD, encoding="utf-8")
    (folder / "01-screens.md").write_text(TEMPLATE_SCREENS_MD, encoding="utf-8")
    return _emit(args.json, True, {"created": str(folder), "files": ["review.md", "01-screens.md"]},
                 [f"init {folder}: created review.md, 01-screens.md",
                  f"next: python {Path(__file__).name} check {folder}"])


def cmd_check(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        return _emit(args.json, False, {"error": f"{folder} is not a folder"},
                      [f"check {folder}: refused", f"  {folder} is not a folder", "  fix: pass an existing folder path"])
    result = contract.parse_folder(folder)
    if result.ok:
        return _emit(args.json, True, {"issues": [], "screen_count": len(result.screens)},
                      [f"check {folder}: OK",
                       f"  {len(result.screens)} screens, {len(result.inventory)} declared commands",
                       f"next: python {Path(__file__).name} build {folder} --out {folder}/preview.html"])
    lines = [f"check {folder}: FAILED ({len(result.issues)} issue(s))"]
    for it in result.issues:
        loc = it["file"] if it["line"] is None else f"{it['file']}:{it['line']}"
        lines.append(f"  {loc}: {it['message']}")
        lines.append(f"    fix: {it['fix']}")
    return _emit(args.json, False, {"issues": result.issues, "screen_count": len(result.screens)}, lines)


def cmd_build(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    out = Path(args.out)
    if not folder.is_dir():
        return _emit(args.json, False, {"error": f"{folder} is not a folder"},
                      [f"build {folder}: refused", f"  {folder} is not a folder", "  fix: pass an existing folder path"])

    result = contract.parse_folder(folder)
    if not result.ok:
        lines = [f"build {folder}: refused, check failed ({len(result.issues)} issue(s)), nothing written"]
        for it in result.issues:
            loc = it["file"] if it["line"] is None else f"{it['file']}:{it['line']}"
            lines.append(f"  {loc}: {it['message']}")
            lines.append(f"    fix: {it['fix']}")
        lines.append(f"fix: python {Path(__file__).name} check {folder} for the full list, then rerun build")
        return _emit(args.json, False, {"issues": result.issues}, lines)

    input_paths = {p.resolve() for p in folder.glob("*.md")}
    if out.resolve() in input_paths:
        msg = f"--out {out} collides with a Markdown input file in {folder}"
        return _emit(args.json, False, {"error": msg}, [f"build {folder}: refused", f"  {msg}", "  fix: choose an --out path outside the review folder's *.md inputs"])
    if out.exists() and not args.force:
        msg = f"{out} already exists; pass --force to overwrite"
        return _emit(args.json, False, {"error": msg}, [f"build {folder}: refused", f"  {msg}"])

    render_screens = []
    for s in result.screens:
        entry = {
            "id": s["id"],
            "title": s["title"],
            "category": s["category"],
            "command": s["command"],
            "width": s["width"],
            "scenario": s["scenario"],
            "exitCode": s["exitCode"],
            "type": s["type"],
            "content": s["content"],
            "stream": s["stream"],
        }
        if s.get("stderr_content") is not None:
            entry["stderrContent"] = s["stderr_content"]
        render_screens.append(entry)

    disclaimer = result.disclaimer or "Design preview only — no command here executes anything."
    html = renderer.render(result.title, disclaimer, render_screens)

    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(out.parent), prefix=f".{out.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        os.replace(tmp_name, out)
    except OSError as e:
        Path(tmp_name).unlink(missing_ok=True)
        msg = f"could not write {out}: {e}"
        return _emit(args.json, False, {"error": msg}, [f"build {folder}: failed", f"  {msg}"])

    return _emit(args.json, True, {"out": str(out), "screen_count": len(result.screens), "bytes": len(html.encode("utf-8"))},
                 [f"build {folder}: wrote {out} ({len(html.encode('utf-8'))} bytes, {len(result.screens)} screens)"])


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    p = _JsonAwareArgumentParser(
        prog="cli_preview.py",
        description=(
            "Author, validate, and render a CLI output review as one offline HTML file.\n"
            "Never runs, executes, or crawls any command; it only reads *.md text you give it."
        ),
        epilog=(
            "Run 'cli_preview.py COMMAND -h' for a command's usage, arguments and examples.\n\n"
            "Exit codes: 0 success; 1 refused or check failed; 2 invalid arguments."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="Create a review.md + example screens file in FOLDER",
        description="Create FOLDER (if needed) with a review.md and an example 01-screens.md. Writes two new files; never overwrites or modifies an existing non-empty FOLDER.",
        epilog="Example: cli_preview.py init my-review/\nExit codes: 0 created; 1 FOLDER exists and is non-empty, or is a file; 2 invalid arguments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_init.add_argument("folder", help="Folder to create (must not already exist as a non-empty folder or as a file)")
    p_init.add_argument("--json", action="store_true", help="Emit one JSON object on stdout instead of text; no output on stderr either way")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser(
        "check",
        help="Validate FOLDER's review.md and screens files, read-only",
        description="Read-only validation of FOLDER against the cli-preview Markdown contract (required fields, unique screen IDs, strict JSON, declared-command help coverage). Never writes to disk.",
        epilog="Example: cli_preview.py check my-review/ --json\nExit codes: 0 no issues found; 1 one or more issues found; 2 invalid arguments.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_check.add_argument("folder", help="Folder to validate")
    p_check.add_argument("--json", action="store_true", help="Emit one JSON object (ok, issues[], screen_count) on stdout instead of text")
    p_check.set_defaults(func=cmd_check)

    p_build = sub.add_parser(
        "build",
        help="Validate FOLDER, then render it to a single offline HTML file",
        description="Runs the same validation as 'check'; on any issue, writes nothing and exits 1. On success, atomically writes one self-contained offline HTML file (search, navigation, copy buttons; no network, no external assets) to --out.",
        epilog=(
            "Examples:\n"
            "  cli_preview.py build my-review/ --out my-review/preview.html\n"
            "  cli_preview.py build my-review/ --out my-review/preview.html --force\n"
            "Exit codes: 0 written; 1 check failed, --out exists without --force, or --out collides with an input *.md; 2 invalid arguments."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_build.add_argument("folder", help="Folder to build")
    p_build.add_argument("--out", required=True, help="Output HTML file path (must not already exist, unless --force; must not be one of FOLDER's own *.md files)")
    p_build.add_argument("--force", action="store_true", help="Overwrite --out if it already exists (side effect: replaces that file's contents)")
    p_build.add_argument("--json", action="store_true", help="Emit one JSON object (ok, out, screen_count, bytes) on stdout instead of text")
    p_build.set_defaults(func=cmd_build)

    return p, {"init": p_init, "check": p_check, "build": p_build}


def _maybe_print_help(parser: argparse.ArgumentParser, subparsers: dict, argv: list[str]) -> bool:
    """Detect a real -h/--help request and print help for it, BEFORE
    argparse's own required-argument validation runs. Without this, e.g.
    'build --out -h' fails with "argument --out: expected one argument" —
    argparse tries to consume '-h' as --out's value before it ever gets a
    chance to recognize it as a help flag. Honors '--' (nothing after it is
    an option, so a literal -h there is not help) and distinguishes a bare
    '-h' token from a '--out=-h' assignment (a single different token, so
    plain equality already tells them apart)."""
    effective = []
    for tok in argv:
        if tok == "--":
            break
        effective.append(tok)
    if not any(tok in ("-h", "--help") for tok in effective):
        return False
    chosen = None
    for tok in effective:
        if tok in ("-h", "--help"):
            break
        if tok in subparsers:
            chosen = tok
            break
    (subparsers[chosen] if chosen else parser).print_help()
    return True


def main(argv: list[str] | None = None) -> int:
    global _argv_has_json
    argv = argv if argv is not None else sys.argv[1:]
    _argv_has_json = "--json" in argv
    parser, subparsers = build_parser()
    if _maybe_print_help(parser, subparsers, argv):
        return 0
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
