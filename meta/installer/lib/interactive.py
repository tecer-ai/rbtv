"""The guided flow: ask for the workspace, the components, the AI tools and the
guidance file, then install.
"""
from __future__ import annotations

from pathlib import Path

from discovery import HUB_DIR, Refuse, SKILLS_DIR, scan_all

from . import tui
from .constants import BASIS_NONE, GUIDANCE_NAMES, HARNESSES, REPO_ROOT
from .catalog import _hub_refuse_message, catalog_parts_map, is_installable
from .state import book_harnesses, read_state
from .operations import do_install
from .report import print_result

# What each harness IS, for the human choosing them. The ids are the vocabulary
# everywhere else in this tool; a picker showing only the ids asks someone to
# recognise three lowercase words with nothing to recognise them by.
HARNESS_NOTE = {
    "claude": "Claude Code",
    "codex": "OpenAI Codex",
    "opencode": "opencode (also serves the Kimi and GLM models)",
}


def _target_error(value: str) -> str | None:
    """Why this answer cannot be an install root, or None when it can.

    Asked as a validator rather than checked after, so a mistyped path costs
    one re-ask instead of throwing away every answer already given.
    """
    path = Path(value).expanduser()
    if path.is_dir():
        return None
    if path.exists():
        return f"{value} is a file, not a directory."
    return f"{value} does not exist."


def interactive(target: Path, catalog: dict[str, dict]) -> int:
    print("rbtv installer — interactive\n")
    answer = tui.text_input("Installation path (target workspace)",
                            default=str(target), validator=_target_error)
    chosen = Path(answer).expanduser()
    if chosen.resolve() != target.resolve():
        target = chosen
        catalog, _ = scan_all(target / ".rbtv" / "mirror", REPO_ROOT)
    if not target.is_dir():
        raise Refuse("target-missing", f"target is not a directory: {target}")

    installable = [cid for cid in sorted(catalog)
                   if is_installable(catalog[cid])]
    if not installable:
        print("Nothing installable — no component on either tree carries an "
              f"exposure manifest, and no {HUB_DIR}/ (or legacy "
              f"{SKILLS_DIR}/) folder exists.")
        return 1

    # Refused units are named OUTSIDE the picker: a picker row can be ticked or
    # greyed out, and neither says "this one is broken, here is why".
    refused = [(cid, _hub_refuse_message(catalog[cid]))
               for cid in sorted(catalog)
               if not is_installable(catalog[cid])
               and catalog[cid].get("hub_refusal")]
    if refused:
        print("Not installable:")
        for cid, why in refused:
            print(f"  {cid} — {why}")
        print()

    installed = set(read_state(target).get("components") or {})
    parts = catalog_parts_map(catalog)
    items = [{"label": cid,
              "selected": cid in installed,
              "hint": f"{len(parts[cid])} part(s) · {catalog[cid]['tree']}"
                      + (" · installed" if cid in installed else "")}
             for cid in installable]

    def _detail(index: int) -> str:
        cid = installable[index]
        rows = [f"  {cid}   [{catalog[cid]['tree']}]", ""]
        for part in parts[cid]:
            rows.append(f"    {part['id']:<30} {part['method']}")
        return "\n".join(rows)

    picked = [installable[i] for i in
              tui.checkbox("Components to install", items,
                           detail_callback=_detail)]
    if not picked:
        print("Nothing selected — cancelled.")
        return 0

    # D16 — both settings are asked ONCE per target and only when the book has
    # no answer yet; thereafter the D16b settings forms own them
    # (`add|rm harness`, `set artifact`, `add|rm artifact exclude`).
    st = read_state(target)
    recorded = book_harnesses(st)
    if recorded is None:
        harnesses = [HARNESSES[i] for i in tui.checkbox(
            "\nWhich AI tools get files written for them?",
            [{"label": h, "hint": HARNESS_NOTE[h], "selected": True}
             for h in HARNESSES],
            min_selected=1)]
    else:
        harnesses = recorded
        print(f"\nHarnesses: {', '.join(harnesses)} — recorded for this "
              "workspace. Change it with `rbtv install add|rm harness`.")

    # D13 — asked ONCE per target; a recorded answer (incl. `none`) is not
    # re-asked, and every non-interactive path skips this entirely.
    basis: str | None = None
    if "guidance_basis" not in st:
        choices = list(GUIDANCE_NAMES) + [BASIS_NONE]
        hints = {BASIS_NONE: "no mirror — write each root file yourself"}
        basis = choices[tui.select_one(
            "\nRoot guidance file — which one do you author? The other is "
            "GENERATED from it on every run, and the one you author is never "
            "written to.",
            [{"label": c,
              "hint": hints.get(c, f"you author {c}; the others mirror it")}
             for c in choices],
            default_index=choices.index(BASIS_NONE))]

    print(f"\nInstalling {', '.join(picked)} for {', '.join(harnesses)} "
          f"into {target}")
    print_result(do_install(target, catalog, picked, harnesses, dry_run=True,
                            guidance_basis=basis))
    if not tui.confirm("\nProceed?", default=False):
        print("Cancelled.")
        return 0
    print_result(do_install(target, catalog, picked, harnesses, dry_run=False,
                            guidance_basis=basis))
    return 0
