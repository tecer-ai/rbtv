"""Printing what a run planned or did, in the form a human reads.

Layout: title, target, a summary of aligned fields (what was selected, the
receiving tools, file counts), then the sections Warnings, Files, File list
and Notes.
Owner-ruled compact default: every warning prints in full, routine lists
(files, claims, copied folders) print as counts, and a selection longer
than `LIST_LIMIT` prints as its count; `--details` prints every list in
full, one entry per line. `--json` always carries the full data either way.
"""
from __future__ import annotations

from . import present, subagents

_UPDATE_LABEL = {"guidance": "guidance", "scaffolding": "scaffolding",
                 "all": "all selected files"}

# A longer selection prints as its count unless --details is given.
LIST_LIMIT = 10


def _title(data: dict) -> str:
    """The `rbtv — <outcome>` line — one authored place so
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
        return "add preview" if dry else "files added"
    if verb == "remove":
        if data.get("not_installed"):
            return "nothing to remove"
        if not data.get("uninstalled") and not data.get("selected_files"):
            if "report" in data:
                return "shared shortcut claims released"
            return "nothing removed"
        return "removal preview" if dry else "files removed"
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
            "Warnings": [], "Files": [], "File list": [], "Notes": []}

    def ids(self, values: list[str], noun: str, *, listed: bool = True) -> str:
        """A selection by name, inline. A long one (more than `LIST_LIMIT`)
        prints as its count unless --details is given; with --details the
        full selection is also listed one ID per line under Files. A
        component row passes `listed=False`: its components are not files."""
        if listed and self.full:
            self.sections["Files"].extend(f"  {value}" for value in values)
        if self.full or len(values) <= LIST_LIMIT:
            return ", ".join(values)
        self.hidden = True
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
    facts = data.get("_facts") or {}
    out = _Out(bool(data.get("_details")))
    print(present.title(_title(data)))
    print()
    if data.get("target"):
        print(f"Target: {data['target']} "
              f"({present.target_source_label(data.get('source'))})")
    if data.get("message"):
        for line in present.wrap(data["message"]):
            print(line)
    if data.get("_verb") == "update" and data.get("scope") == "guidance":
        print()
        print("\n".join(_guidance_lines(data, facts, preview)))
        print()
        print("Next: " + data.get("next", "rbtv status"))
        return
    if facts.get("changed") is not None:
        print()
        print(f"Changed {_count(facts['changed'], 'file')}, unchanged "
              f"{_count(facts['unchanged'], 'file')}, failed "
              f"{len(_failed_files(data))}.")

    out.summary.extend(data.get("_fields") or [])
    selected = data.get("selected_files") or []
    added, removed = data.get("added") or [], data.get("removed") or []
    if data.get("_verb") == "update":
        out.summary.append(("Would add" if preview else "Added",
                            out.ids(added, "files") if added else "none"))
        out.summary.append(("Would remove" if preview else "Removed",
                            out.ids(removed, "files") if removed else "none"))
    removing = data.get("_verb") == "remove"
    if selected:
        label = ("Would remove" if removing else "Would add") if preview \
            else ("Removed" if removing else "Installed")
        out.summary.append((label, out.ids(selected, "files")))
    elif data.get("installed"):
        out.summary.append(("Would refresh" if preview else "Refreshed",
                            out.ids(data["installed"], "components", listed=False)))
    elif data.get("uninstalled"):
        out.summary.append(("Would remove" if preview else "Removed",
                            out.ids(data["uninstalled"], "components", listed=False)))
    elif data.get("not_installed"):
        out.summary.append(("Not installed", out.ids(data["not_installed"], "files")))
    if data.get("harnesses"):
        out.summary.append(("Receiving tools",
                            _receiving(data["harnesses"], facts, preview)))
    _installed_row(out, facts, data)
    out.summary.extend(subagents.rows(data.get("sub_agents") or []))
    for name, component, on in facts.get("packs") or []:
        out.summary.append(("Pack", f"{name} ({component}) "
                            + ("on" if on else "off")))
    _changes(out, data, preview)
    _warnings(out, data, preview)
    report = data.get("report") or {}
    claims = data.get("shared_removed") or []
    release = "would release" if preview else "released"
    out.group([f"{release} claim {cid}" for cid in claims],
              f"{release} {len(claims)} claim(s) inside shared files")
    skipped = data.get("skipped_agents") or []
    if skipped:
        out.bullet("Notes", "skipped agent(s) a component ships: " + ", ".join(skipped)
                   + f". Add one by name with --on {subagents.ON_FORM}, or place "
                   "it with `rbtv agent add NAME`.")
    for text in subagents.notes(data.get("sub_agents") or []):
        out.bullet("Notes", text)
    for gap in data.get("sub_agents_missing") or []:
        out.bullet("Notes", subagents.missing_note(
            gap["name"], gap["written_for"], gap["harness"], gap["command"]))
    _report_rows(out, report, preview, data.get("target") or "")
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
        hint = ("Add --details to this preview to list every file and harness file."
                if preview else
                "Lists are counted, not printed. To list every file and "
                "harness file, preview the next change with --dry-run --details.")
        for line in present.wrap(hint + " --json always carries the full lists."):
            print(line)
        print()
    print("Next: " + data.get("next", "rbtv status"))


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _failed_files(data: dict) -> set[tuple[str, str]]:
    """Selected files a receiving tool cannot use: the run's failures."""
    return {(row["component"], row["part"])
            for row in (data.get("report") or {}).get("no_realization") or []}


def _receiving(now: list[str], facts: dict, preview: bool) -> str:
    """The receiving tools, with what they were when the harnesses changed."""
    text = ", ".join(now)
    before = facts.get("harnesses_before")
    if before is None or before == now:
        return text
    return f"{text} ({'would replace' if preview else 'was'} {', '.join(before)})"


def _installed_row(out: _Out, facts: dict, data: dict) -> None:
    """`Installed files: N (was M)`, or `(unchanged)`. An update that added or
    removed files prints the count alone (the Added and Removed rows say it)."""
    if "files" not in facts:
        return
    before, after = facts["files"]
    if data.get("_verb") == "update" and (data.get("added") or data.get("removed")):
        text = str(after)
    elif before == after:
        text = f"{after} (unchanged)"
    else:
        text = f"{after} (was {before})"
    out.summary.append(("Installed files", text))


def _guidance_lines(data: dict, facts: dict, preview: bool) -> list[str]:
    """`update guidance`: whether the guidance copies were made and whether the
    folder matches the file. It never adds or removes a file."""
    mirror = (data.get("report") or {}).get("guidance_mirror") or {}
    if mirror.get("basis"):
        copied = "would copy" if preview else "copied"
        lines = [f"Guidance copies {copied} maintained text from "
                 f"{mirror['basis']} to {len(mirror.get('targets') or [])} file(s)."]
    else:
        lines = ["Guidance copies are off. No maintained text to copy."]
    listed = facts.get("listed_missing") or []
    unlisted = facts.get("on_disk_unlisted") or []
    if listed or unlisted:
        sentences = ([f"{file} is listed and missing." for file in listed]
                     + [f"{file} is on disk and is not listed." for file in unlisted])
        lines.append("The folder does not match install.json. "
                     + " ".join(sentences) + " Added none. Removed none.")
        lines.append(f"Fix: rbtv update scaffolding --target {data['target']}")
    else:
        lines.append("The folder matches the file. Added none. Removed none. "
                     f"Installed files stay {facts['files'][1]}.")
    return [line for text in lines for line in present.wrap(text)]


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
    stale = data.get("recorded_source_gone") or []
    if stale:
        out.bullet("Warnings", "the record lists file(s) whose source is gone: "
                   + ", ".join(stale)
                   + ". Run `rbtv update all` to remove them.")
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


def _report_rows(out: _Out, report: dict, planned: bool, target: str) -> None:
    """Why a file minted nothing, and the PATH shortcut changes. Printed on
    DRY RUNS TOO, marked as planned (task 7.622): the SAME data a real run
    prints; only the tense moves."""
    tail = "no file would be written" if planned else "no file was written"
    # A selected file a receiving tool cannot use is an exception, never
    # routine: always under Warnings, every file named, one bullet per
    # tool and type so a long run stays readable.
    unused: dict[tuple[str, str], list[str]] = {}
    for row in report.get("no_realization") or []:
        unused.setdefault((row["harness"], row["type"]), []).append(
            f"{row['component']}#{row['part']}")
    for (harness, kind), keys in unused.items():
        out.bullet("Warnings", f"{harness} cannot use {len(keys)} selected "
                   f"{kind} file(s) — {tail} for: " + ", ".join(keys))
    for key in report.get("sub_agents_unset") or []:
        out.bullet("Warnings", subagents.unset_note(key, target))
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
        out.bullet("Notes", "kept shared shortcut(s) for another installation: "
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
        out.bullet("Notes", f"Git ignore list not claimed ({gi.get('reason')})")
        return
    out.bullet("Notes", f"Git ignore list {'would keep' if planned else 'keeps'} "
               f"{gi['count']} harness file path(s) out of commits")


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
                   "run `rbtv configure --guidance CLAUDE.md` or "
                   "`rbtv configure --guidance AGENTS.md`.")
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
