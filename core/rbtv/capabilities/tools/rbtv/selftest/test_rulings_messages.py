"""What an `add` prints when it touches more than the names it was given: the
unchanged-file list of a re-added name, and the refusal on a guidance file
rbtv did not write."""
from __future__ import annotations

from discovery import Refuse, scan_all

from .fixture import _component, _file_md, _w
from .test_rulings_ops import _run

_NAMED = "Already up to date, of the files named"


def rulings_messages(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    print("\nRM — an add lists the named files and names the exclusion command")
    source, mirror = tmp / "messages-source", tmp / "messages-mirror"
    comp = _component(source, "modm", "one")
    _file_md(comp / "rules/alpha.md", "alpha", "Alpha", "body\n")
    _file_md(comp / "rules/beta.md", "beta", "Beta", "body\n")
    catalog, _ = scan_all(mirror, source)

    # ---- R3: a re-added name lists its own unchanged files ----
    root = tmp / "ws-messages-list"
    root.mkdir()
    _run(root, catalog, "add", "modm/one#alpha", "modm/one#beta",
         "--harness", "claude", "--guidance", "none")
    for label, flags in (("preview", ("--dry-run", "--details")),
                         ("run", ("--details",))):
        code, text = _run(root, catalog, "add", "modm/one#alpha", *flags)
        check(f"RM-list-{label} — a re-added name lists only its own files "
              "as already up to date",
              code == 0 and _NAMED + " (1) .claude/rules/alpha.md" in text
              and ".claude/rules/beta.md" not in text, text)
        check(f"RM-count-{label} — the Files row still counts the whole "
              "installation", "2 already up to date" in text, text)
    code, text = _run(root, catalog, "add", "modm/one#alpha", "--dry-run", "--json")
    check("RM-list-json — --json still carries every unchanged file",
          code == 0 and '"unchanged_files": [ ".claude/rules/alpha.md", '
          '".claude/rules/beta.md" ]' in text, text)
    code, text = _run(root, catalog, "update", "all", "--dry-run", "--details")
    check("RM-list-update — an update, which names no file, lists every "
          "unchanged file",
          code == 0 and "Already up to date (2) .claude/rules/alpha.md "
          ".claude/rules/beta.md" in text, text)

    # ---- R6: the refusal on a foreign guidance file names the exclusion ----
    root = tmp / "ws-messages-refusal"
    _w(root / "CLAUDE.md", "# Root guidance\n")
    _run(root, catalog, "add", "modm/one#alpha",
         "--harness", "claude,codex", "--guidance", "CLAUDE.md")
    _w(root / "sub/CLAUDE.md", "# Sub guidance\n")
    _w(root / "sub/AGENTS.md", "# Written by hand\n")
    refusal = None
    try:
        _run(root, catalog, "add", "modm/one#beta")
    except Refuse as exc:
        refusal = exc
    check("RM-refusal — adding one file is refused on a guidance file rbtv "
          "did not write, and the refusal names the exclusion command",
          refusal is not None and refusal.code == "guidance-mirror-collision"
          and "sub/AGENTS.md" in str(refusal)
          and "`rbtv add guidance exclude <folder>`" in str(refusal),
          str(refusal))
    _run(root, catalog, "add", "guidance", "exclude", "sub")
    code, _text = _run(root, catalog, "add", "modm/one#beta")
    check("RM-refusal-next — after the named exclusion the same add is "
          "accepted and the hand-written file is unchanged",
          code == 0 and (root / ".claude/rules/beta.md").is_file()
          and (root / "sub/AGENTS.md").read_text(encoding="utf-8")
          == "# Written by hand\n")
