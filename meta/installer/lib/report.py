"""Printing what a run planned or did, in the form a human reads."""
from __future__ import annotations


from .constants import FENCE_ID, MANAGED_MARK, PATH_BOOTSTRAP


def print_result(data: dict) -> None:
    for key in ("installed", "uninstalled"):
        if data.get(key):
            print(f"{key}: {', '.join(data[key])}")
    if data.get("harnesses"):
        print(f"harnesses: {', '.join(data['harnesses'])}")
    # Printed BEFORE the dry-run branch: a planned takeover of another tool's
    # file is exactly what a human needs to see while deciding to proceed.
    for rel in data.get("adopted") or []:
        print(f"  ^ {rel} (adopted — its own head proves a tool generated it, "
              "so it is not authored content; now ours)")
    for rel in data.get("released") or []:
        print(f"  ! {rel} (released — the `{MANAGED_MARK}` marker is gone, so "
              "someone took this file over: dropped from the book, left on "
              "disk, never deleted)")
    if data.get("dry_run"):
        print(f"DRY RUN — would write {len(data.get('skipped') or [])} file(s) "
              f"and hold {len(data.get('shared') or [])} shared-file claim(s):")
        for rel in data.get("skipped") or []:
            print(f"  + {rel}")
        for rel in data.get("shared") or []:
            print(f"  ~ {rel}")
        for rel in data.get("deleted") or []:
            print(f"  - {rel}")
        for rel in data.get("shared_removed") or []:
            print(f"  ~- {rel}")
        _print_report_rows(data.get("report") or {}, planned=True)
        _print_gitignore(data.get("report") or {}, planned=True)
        _print_guidance(data.get("report") or {}, planned=True)
        return
    for rel in data.get("written") or []:
        print(f"  + {rel}")
    for rel in data.get("skipped") or []:
        print(f"  = {rel} (unchanged)")
    for rel in data.get("shared") or []:
        print(f"  ~ {rel}")
    for rel in data.get("deleted") or []:
        print(f"  - {rel}")
    for rel in data.get("shared_removed") or []:
        print(f"  ~- {rel}")
    report = data.get("report") or {}
    _print_report_rows(report, planned=False)
    _print_gitignore(report, planned=False)
    _print_guidance(report, planned=False)


def _print_report_rows(report: dict, planned: bool) -> None:
    """Why a manifest row minted nothing. Printed on DRY RUNS TOO, marked as
    planned (task 7.622): `install --component X --dry-run` is the command the
    acceptance sketches name, and suppressing these rows there left the human
    ~11 lines with no per-row detail while the data sat in `--json` all along.
    The two lists are the SAME data a real run prints; only the tense moves."""
    verb = "would skip" if planned else "skipped"
    tail = "would mint nothing" if planned else "nothing minted"
    for row in report.get("skipped_inventory_rows") or []:
        print(f"  · {verb} `{row['method']}` row {row['component']}/"
              f"{row['part']} ({row['entry_point']}) — inventory only, "
              "mints nothing")
    for row in report.get("skill_folders") or []:
        print(f"  · {'would copy' if planned else 'copied'} skill FOLDER "
              f"{row['component']} whole — {row['files']} file(s) into "
              + ", ".join(row["roots"]) + " (D15)")
    for row in report.get("no_realization") or []:
        print(f"  · {row['harness']} has no realization for method "
              f"{row['method']} ({row['component']}/{row['part']}) — {tail}")
    pathrep = report.get("path") or {}
    for name in pathrep.get("linked") or []:
        print(f"  · {'would link' if planned else 'linked'} PATH {name}")
    for name in pathrep.get("relinked") or []:
        print(f"  · {'would relink' if planned else 'relinked'} PATH {name}")
    for name in pathrep.get("unlinked") or []:
        print(f"  · {'would unlink' if planned else 'unlinked'} PATH {name}")
    if any(pathrep.get(k) for k in ("linked", "relinked", "ok")):
        print(f"  · add to shell (first wins over ~/.local/bin): "
              f"{report.get('path_bootstrap') or PATH_BOOTSTRAP}")


def _print_gitignore(report: dict, planned: bool) -> None:
    """What the `.gitignore` block covers — and what it cannot (D14)."""
    gi = report.get("gitignore")
    if not gi:
        return
    if not gi.get("claimed"):
        print(f"  · .gitignore: not claimed ({gi.get('reason')})")
        return
    print(f"  · .gitignore: {'would keep' if planned else 'keeps'} "
          f"{gi['count']} artifact path(s) out of git, in one "
          f"`{FENCE_ID}:start` block (D14)")
    for rel in gi.get("tracked") or []:
        print(f"    ⚠ {rel} is ALREADY TRACKED by git — no ignore rule reaches "
              "a tracked file. Untrack it (`git rm --cached`) or accept that "
              "it is committed.")


def _print_guidance(report: dict, planned: bool) -> None:
    """The guidance-mirror summary and the blocks the human must place. Printed
    on DRY RUNS TOO: the basis is never written, so this is the only channel
    that ever names what the human still has to do (7.622's bug class)."""
    verb = "would generate" if planned else "generated"
    mirror = report.get("guidance_mirror")
    if mirror and mirror.get("skipped"):
        print(f"  · guidance mirror: SKIPPED ({mirror['skipped']}) — not "
              "re-rendered; both root guidance files were left untouched. Fix "
              "the basis on the next install.")
    elif mirror and mirror.get("basis") and not mirror.get("targets"):
        print(f"  · guidance mirror: nothing to render — every installed "
              f"harness reads {mirror['basis']}, which is the basis and is "
              "never written (D13).")
    elif mirror and mirror.get("basis"):
        print(f"  · guidance mirror: {mirror['count']} file(s) — "
              f"{', '.join(mirror['targets'])} {verb} from "
              f"{mirror['basis']} (one set beside every {mirror['basis']} in "
              "the tree; no basis file is ever written)"
              + (f"; excluding {', '.join(mirror['excludes'])}"
                 if mirror.get("excludes") else ""))
        if mirror.get("banner_stripped"):
            print("    a generated banner was stripped from these bases before "
                  "mirroring (never stacked): "
                  + ", ".join(mirror["banner_stripped"]))
    elif mirror:
        print("  · guidance mirror: OFF — no basis recorded. Set one with "
              "`rbtv install set artifact CLAUDE.md|AGENTS.md` (D13).")
    if report.get("guidance_debannered"):
        print(f"  · {'would clean' if planned else 'cleaned'} a stale GENERATED "
              "banner off the file(s) you now author: "
              + ", ".join(report["guidance_debannered"]))
    for name, block in (report.get("guidance_manual") or {}).items():
        print(f"\nAdd this block to {name} — an installed harness reads it and "
              "this installer never writes it (D8). Copy from the next line to "
              "the closing fence:\n")
        # Flush, never indented: four leading spaces make markdown swallow the
        # whole block as a code span when it is pasted into the guidance file.
        print(block.rstrip())
