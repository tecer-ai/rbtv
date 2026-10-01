"""Printing what a run planned or did, in the form a human reads.

Layout: title, target, a summary of aligned fields (what was selected, the
receiving tools, file counts), then the sections Warnings, Items, File list
and Notes.
Owner-ruled compact default: every warning prints in full, routine lists
(files, claims, copied folders) print as counts, and a selection longer
than `LIST_LIMIT` prints as its count; `--details` prints every list in
full, one entry per line. `--json` always carries the full data either way.
"""
from __future__ import annotations

from . import present

_UPDATE_LABEL = {"guidance": "guidance", "scaffolding": "scaffolding",
                 "all": "all selected files"}

# A longer selection prints as its count unless --details is given.
LIST_LIMIT = 10


def _title(data: dict) -> str:
    """The `RBTV install — <outcome>` line — one authored place so
    configure/add/remove/update never spell their own title separately."""
    if data.get("_title"):
        return data["_title"]
    verb = data.get("_verb") or ""
    dry = bool(data.get("dry_run"))
    if verb == "configure":
        if data.get("changed") is False:
            return "configuration unchanged"
        return "configuration preview" if dry else "configuration saved"
    if verb == "add":
        return "add preview" if dry else "items added"
    if verb == "remove":
        if not data.get("uninstalled") and "report" in data:
            return "shared shortcut claims released"
        if not data.get("uninstalled") and not data.get("selected_items"):
            return "nothing removed"
        return "removal preview" if dry else "items removed"
    if verb == "update":
        label = _UPDATE_LABEL.get(data.get("scope", ""), data.get("scope", "update"))
        return f"{label} update preview" if dry else f"{label} updated"
    return "result"


class _Out:
    """Collects one result screen: summary fields, then named sections.
    `full` is --details. `hidden` records whether a routine list was
    counted instead of printed, so the screen can say where it is."""

    def __init__(self, full: bool) -> None:
        self.full = full
        self.hidden = False
        self.summary: list[tuple[str, str]] = []
        self.sections: dict[str, list[str]] = {
            "Warnings": [], "Items": [], "File list": [], "Notes": []}

    def ids(self, values: list[str], noun: str) -> str:
        """A short selection by name; a long one by count. With --details
        the full selection is listed one ID per line under Items."""
        if self.full:
            self.sections["Items"].extend(f"  {value}" for value in values)
        elif len(values) > LIST_LIMIT:
            self.hidden = True
        else:
            return ", ".join(values)
        return f"{len(values)} {noun if len(values) != 1 else noun[:-1]}"

    def bullet(self, section: str, text: str) -> None:
        self.sections[section].extend(
            present.wrap(text, indent="  · ", hang="    "))

    def group(self, rows: list[str], summary: str) -> None:
        """A routine Notes list: its one-line count by default, every row
        as its own bullet with --details."""
        if not rows:
            return
        if self.full:
            for row in rows:
                self.bullet("Notes", row)
        else:
            self.hidden = True
            self.bullet("Notes", summary)

    def listing(self, section: str, heading: str, values: list[str]) -> None:
        """A labeled block, one entry per line, never shortened; blocks in
        one section are separated by a blank line."""
        if not values:
            return
        lines = self.sections[section]
        if lines:
            lines.append("")
        lines.append(f"  {heading} ({len(values)})")
        lines.extend(f"    {value}" for value in values)

    def files(self, heading: str, paths: list[str]) -> None:
        """Routine file paths: counted in the summary, listed only with
        --details (owner ruling: counts by default)."""
        if self.full:
            self.listing("File list", heading, paths)
        elif paths:
            self.hidden = True


def print_result(data: dict) -> None:
    preview = bool(data.get("dry_run"))
    out = _Out(bool(data.get("_details")))
    print(present.title(_title(data)))
    print()
    if data.get("target"):
        print(f"Target: {data['target']} "
              f"({present.target_source_label(data.get('source'))})")
    if data.get("message"):
        for line in present.wrap(data["message"]):
            print(line)

    out.summary.extend(data.get("_fields") or [])
    selected = data.get("selected_items") or []
    removing = bool(data.get("uninstalled"))
    if selected:
        label = ("Would remove" if removing else "Would install") if preview \
            else ("Removed" if removing else "Installed")
        out.summary.append((label, out.ids(selected, "items")))
    elif data.get("installed"):
        out.summary.append(("Would refresh" if preview else "Refreshed",
                            out.ids(data["installed"], "components")))
    elif removing:
        out.summary.append(("Would remove" if preview else "Removed",
                            out.ids(data["uninstalled"], "components")))
    if data.get("harnesses"):
        out.summary.append(("Receiving tools", ", ".join(data["harnesses"])))
    _changes(out, data, preview)
    _warnings(out, data, preview)
    report = data.get("report") or {}
    claims = data.get("shared_removed") or []
    release = "would release" if preview else "released"
    out.group([f"{release} claim {cid}" for cid in claims],
              f"{release} {len(claims)} claim(s) inside shared files")
    _report_rows(out, report, preview)
    _gitignore(out, report, preview)
    _guidance(out, report, preview, scope=data.get("scope"))
    _guidance_sections(out, report, preview)

    lines = present.fields(out.summary)
    if lines:
        print()
        print("\n".join(lines))
    for heading, body in out.sections.items():
        if body:
            print()
            print(heading)
            print("\n".join(body))
    print()
    if out.hidden:
        # Never suggests repeating a change that already ran.
        hint = ("Add --details to this preview to list every item and file."
                if preview else
                "Lists are counted, not printed. To list every item and "
                "file, preview the next change with --dry-run --details.")
        for line in present.wrap(hint + " --json always carries the full lists."):
            print(line)
        print()
    print("Next: " + data.get("next", "rbtv install status"))


def _changes(out: _Out, data: dict, preview: bool) -> None:
    """File counts and path lists. ONE shape for both a preview (`apply()`'s
    `planned_changes`) and a real run's written/deleted/shared_* result —
    real counts only: a run that carries no file result (a no-op removal,
    unchanged settings) prints no counts at all rather than a fake zero.
    Ordinary and shared files are counted on separate rows, each from its
    own lists. Shared-CLAIM ids never enter these counts."""
    if preview:
        planned = data.get("planned_changes")
        if planned is None:
            return
        write, delete, same = (planned.get("write_files") or [],
                               planned.get("delete_files") or [],
                               planned.get("unchanged_files") or [])
        s_write, s_delete, s_same = (planned.get("write_shared_files") or [],
                                     planned.get("delete_shared_files") or [],
                                     planned.get("unchanged_shared_files") or [])
    else:
        if "written" not in data:
            return
        write, delete, same = (data.get("written") or [],
                               data.get("deleted") or [],
                               data.get("skipped") or [])
        s_write, s_delete, s_same = (data.get("shared_written") or [],
                                     data.get("shared_deleted") or [],
                                     data.get("shared_skipped") or [])
    w, d = ("would write", "would delete") if preview else ("wrote", "deleted")
    sw = "would change" if preview else "changed"
    out.summary.append((data.get("_files_label") or "Files",
                        f"{w} {len(write)}, {d} {len(delete)}, "
                        f"{len(same)} already up to date"))
    if s_write or s_delete or s_same:
        out.summary.append(("Shared files", f"{sw} {len(s_write)}, "
                                            f"{d} {len(s_delete)}, "
                                            f"{len(s_same)} already up to date"))
    if s_delete:
        out.bullet("Notes", "Shared-file deletions remove the whole file. "
                   "Released claims identify the managed sections or keys "
                   "taken back.")
    out.files("Would write" if preview else "Written", write)
    out.files("Would delete" if preview else "Deleted", delete)
    out.files("Already up to date", same)
    out.files("Shared, would change" if preview else "Shared, changed", s_write)
    out.files("Shared, would delete whole files" if preview
              else "Shared, deleted whole files", s_delete)
    out.files("Shared, already up to date", s_same)


def _warnings(out: _Out, data: dict, preview: bool) -> None:
    """Everything a human must see before trusting the run — never collapsed.
    Tense follows `preview`: a dry run adopts nothing, so claiming "now
    managed" before anything was written would be a false completed-action
    claim on a run that changed zero bytes."""
    for rel in data.get("adopted") or []:
        out.bullet("Warnings", f"{rel}: previously generated by a tool; "
                   + ("would become managed here" if preview
                      else "now managed here"))
    # Different from whole-file adoption: only the owned section inside an
    # existing file is taken over; the rest of that file is never touched.
    for rel in data.get("adopted_sections") or []:
        out.bullet("Warnings", f"{rel}: "
                   + ("would adopt its existing owned section only" if preview
                      else "adopted its existing owned section only")
                   + " (the rest of the file is untouched)")
    for rel in data.get("released") or []:
        out.bullet("Warnings", f"{rel}: no longer managed here; kept on disk")
    missing = data.get("source_missing") or []
    if missing:
        out.bullet("Warnings", f"{len(missing)} recorded component(s) are "
                   "missing from local RBTV source and were not refreshed: "
                   + ", ".join(missing))
    report = data.get("report") or {}
    legacy = (report.get("path") or {}).get("legacy_preserved") or []
    if legacy:
        out.bullet("Warnings", f"kept {len(legacy)} command shortcut(s) whose "
                   "earlier ownership is uncertain: " + ", ".join(legacy))
    warning = report.get("path_warning")
    if warning:
        out.bullet("Warnings", "component installation succeeded, but PATH "
                   f"setup failed: {warning['message']}")
        out.bullet("Warnings", "Recovery: " + warning["recovery"])
    gi = report.get("gitignore") or {}
    for rel in gi.get("tracked") or []:
        out.bullet("Warnings", f"{rel} is ALREADY TRACKED by git — no ignore "
                   "rule reaches a tracked file. Untrack it (`git rm --cached`) "
                   "or accept that it is committed.")
    mirror = report.get("guidance_mirror") or {}
    if mirror.get("skipped"):
        out.bullet("Warnings", f"guidance mirror: SKIPPED ({mirror['skipped']}) "
                   "— the maintained-text copy step was skipped; fix the basis "
                   "on the next install. Other files this run planned may "
                   "still be written.")


def _report_rows(out: _Out, report: dict, planned: bool) -> None:
    """Why a unit minted nothing, and the PATH shortcut changes. Printed on
    DRY RUNS TOO, marked as planned (task 7.622): the SAME data a real run
    prints; only the tense moves."""
    tail = "no file would be written" if planned else "no file was written"
    # A selected item a receiving tool cannot use is an exception, never
    # routine: always under Warnings, every item named, one bullet per
    # tool and type so a long run stays readable.
    unused: dict[tuple[str, str], list[str]] = {}
    for row in report.get("no_realization") or []:
        unused.setdefault((row["harness"], row["type"]), []).append(
            f"{row['component']}#{row['part']}")
    for (harness, kind), keys in unused.items():
        out.bullet("Warnings", f"{harness} cannot use {len(keys)} selected "
                   f"{kind} item(s) — {tail} for: " + ", ".join(keys))
    gone = report.get("source_gone") or []
    if gone:
        out.bullet("Notes", f"{'would remove' if planned else 'removed'} "
                   "(source no longer exists): " + ", ".join(gone))
    pathrep = report.get("path") or {}
    for key, verb in (("linked", "link"), ("relinked", "relink"),
                      ("unlinked", "unlink")):
        names = pathrep.get(key) or []
        if names:
            done = f"would {verb}" if planned else f"{verb}ed"
            out.bullet("Notes", f"{done} PATH shortcut(s): " + ", ".join(names))
    shared = pathrep.get("kept_shared") or []
    if shared:
        out.bullet("Notes", "kept shared shortcut(s) for another workspace: "
                   + ", ".join(shared))
    setup = report.get("path_setup") or {}
    if planned and any(pathrep.get(k) for k in ("linked", "relinked", "ok")):
        out.bullet("Notes", "applying this plan would attempt to put "
                   "~/.rbtv/bin on the user PATH")
    elif setup.get("attempted") and setup.get("ok"):
        out.bullet("Notes", "~/.rbtv/bin is on the user PATH")


def _gitignore(out: _Out, report: dict, planned: bool) -> None:
    """What the `.git/info/exclude` block covers; tracked files it cannot
    reach are listed under Warnings (D14)."""
    gi = report.get("gitignore")
    if not gi:
        return
    if not gi.get("claimed"):
        out.bullet("Notes", f"git exclude: not claimed ({gi.get('reason')})")
        return
    out.bullet("Notes", f"Git ignore list {'would keep' if planned else 'keeps'} "
               f"{gi['count']} generated path(s) out of commits")


def _guidance(out: _Out, report: dict, planned: bool, *,
              scope: str | None = None) -> None:
    """The guidance-MIRROR summary only — the maintained HUMAN text this
    scope copies from the basis into each counterpart file; it never copies
    generated sections. A destination's OWN generated section survives
    untouched only when `scope == "guidance"` (`_add_mirror` skips rewriting
    it there); `all`/`add` rebuild it in the same run, so claiming it "is
    preserved" there would be false — `_guidance_sections` reports that
    regeneration. Printed on dry runs too, with the tense moved."""
    verb = "would generate" if planned else "generated"
    mirror = report.get("guidance_mirror") or {}
    if not mirror or mirror.get("skipped"):  # a skip is under Warnings
        pass
    elif mirror.get("basis") and not mirror.get("targets"):
        out.bullet("Notes", "guidance mirror: nothing to copy — every installed "
                   f"harness reads {mirror['basis']} directly, so there is no "
                   "separate counterpart file to maintain.")
    elif mirror.get("basis"):
        out.bullet("Notes", f"guidance mirror: {mirror['count']} file(s) — "
                   f"{', '.join(mirror['targets'])}: maintained text {verb} "
                   f"from {mirror['basis']}; generated sections are not copied "
                   "from the basis"
                   + (f"; excluding {', '.join(mirror['excludes'])}"
                      if mirror.get("excludes") else ""))
        if scope == "guidance":
            out.bullet("Notes", "each destination's own existing generated "
                       "instruction section is preserved as-is by this copy")
        if mirror.get("banner_stripped"):
            out.bullet("Notes", "a generated banner was stripped from these "
                       "bases before mirroring (never stacked): "
                       + ", ".join(mirror["banner_stripped"]))
    else:
        out.bullet("Notes", "guidance copies: off. To choose an authored file, "
                   "run `rbtv install configure --guidance CLAUDE.md` or "
                   "`rbtv install configure --guidance AGENTS.md`.")
    if report.get("guidance_debannered"):
        out.bullet("Notes", f"{'would clean' if planned else 'cleaned'} a stale "
                   "GENERATED banner off the file(s) you now author: "
                   + ", ".join(report["guidance_debannered"]))


def _guidance_sections(out: _Out, report: dict, planned: bool) -> None:
    """`report.guidance_sections`: the root instruction files whose owned
    fenced section this run REGENERATES — never "merely present" or "left
    as-is". One GENERATED section inside a file the human still authors."""
    sections = report.get("guidance_sections") or []
    if sections:
        verb = "will regenerate" if planned else "regenerated"
        out.bullet("Notes", f"{verb} the automatically managed instruction "
                   "section in: " + ", ".join(sections))
