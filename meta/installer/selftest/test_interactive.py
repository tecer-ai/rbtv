"""The guided flow: its widgets, and one whole run of it end to end."""
from __future__ import annotations

import contextlib
import io
import os
import sys

from discovery import Refuse

from lib import tui
from lib.constants import BASIS_NONE, GUIDANCE_NAMES, HARNESSES
from lib.catalog import is_installable
from lib.guidance import resolve_basis
from lib.interactive import interactive
from lib.state import read_state


@contextlib.contextmanager
def _typed(answers: list[str]):
    """Drive the widgets the way a pipe or a script does: typed lines, no tty.

    `RICH_MODE_OVERRIDE` is forced rather than relied upon: a suite that ran
    green only because the machine happened to have no terminal would go red on
    a developer's laptop, which is the opposite of a check.
    """
    saved_stdin, saved_mode = sys.stdin, tui.RICH_MODE_OVERRIDE
    sys.stdin = io.StringIO("\n".join(answers) + "\n")
    tui.RICH_MODE_OVERRIDE = False
    try:
        yield
    finally:
        sys.stdin, tui.RICH_MODE_OVERRIDE = saved_stdin, saved_mode


def guided_flow(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nI — the guided flow, driven end to end without a terminal")
    ws = tmp / "ws-interactive"
    ws.mkdir()
    installable = [cid for cid in sorted(catalog)
                   if is_installable(catalog[cid])]
    pick = installable.index("fixmod/goodcomp") + 1
    out = io.StringIO()
    with _typed([str(ws), str(pick), "1", "", "y"]):
        with contextlib.redirect_stdout(out):
            code = interactive(ws, catalog)
    said = out.getvalue()

    check("I — the flow completes and installs what was ticked",
          code == 0
          and "fixmod/goodcomp" in (read_state(ws).get("components") or {}),
          f"exit {code}; booked "
          f"{sorted(read_state(ws).get('components') or {})}")
    check("I — every question was asked as a numbered list, not a raw number "
          "prompt", f"{pick}. " in said
          and "Which AI tools get files written for them?" in said
          and "Root guidance file" in said, said[:300])
    check("I — the AI tools ticked are the ones recorded",
          read_state(ws).get("harnesses") == ["claude"],
          str(read_state(ws).get("harnesses")))
    check("I — a blank answer to the guidance question means `none`",
          read_state(ws).get("guidance_basis") == BASIS_NONE,
          str(read_state(ws).get("guidance_basis")))
    # Re-run: the two workspace settings are recorded now, so D16 says they are
    # NOT asked again. Only the path, the components and the confirmation.
    out2 = io.StringIO()
    with _typed([str(ws), str(pick), "y"]):
        with contextlib.redirect_stdout(out2):
            code2 = interactive(ws, catalog)
    said2 = out2.getvalue()
    check("I — D16: a second run does not re-ask the recorded settings",
          code2 == 0
          and "Which AI tools get files written for them?" not in said2
          and "Root guidance file" not in said2
          and "recorded for this workspace" in said2, said2[:300])
    picked_row = [line for line in said2.splitlines()
                  if "fixmod/goodcomp" in line
                  and line.strip().startswith(str(pick) + ".")]
    check("I — what is already installed comes back pre-ticked and says so",
          len(picked_row) == 1 and "[x]" in picked_row[0]
          and "· installed" in picked_row[0],
          str(picked_row))

    out3 = io.StringIO()
    with _typed([str(ws), "", "n"]):
        with contextlib.redirect_stdout(out3):
            code3 = interactive(ws, catalog)
    check("I — answering the confirmation with `n` installs nothing",
          code3 == 0 and "Cancelled." in out3.getvalue(),
          f"exit {code3}")
    ctx.keep(locals())


def fumbled_answers_reask(ctx) -> None:
    check = ctx.check

    print("\nI2 — a fumbled answer costs one re-ask, never the whole run")
    items = [{"label": "AGENTS.md"}, {"label": "CLAUDE.md"},
             {"label": BASIS_NONE}]
    out = io.StringIO()
    with _typed(["9", "2"]):
        with contextlib.redirect_stdout(out):
            picked = tui.select_one("basis", items, default_index=2)
    check("I2 — an out-of-range choice re-asks and the next answer lands",
          picked == 1 and "no such option: '9'" in out.getvalue(),
          f"{picked}; {out.getvalue()[-120:]!r}")

    out = io.StringIO()
    with _typed([""]):
        with contextlib.redirect_stdout(out):
            picked = tui.select_one("basis", items, default_index=2)
    check("I2 — a blank answer takes the default, it does not refuse",
          picked == 2, str(picked))

    out = io.StringIO()
    with _typed(["x", "y", "z"]):
        try:
            with contextlib.redirect_stdout(out):
                tui.select_one("basis", items, default_index=2)
            bounded = "no error"
        except ValueError as exc:
            bounded = str(exc)
    check("I2 — the re-ask is BOUNDED: three bad answers stop the question",
          "z" in bounded, bounded)

    items = [{"label": h, "selected": h == "claude"} for h in HARNESSES]
    out = io.StringIO()
    with _typed([""]):
        with contextlib.redirect_stdout(out):
            kept = tui.checkbox("tools", items)
    check("I2 — a blank answer to a multi-select keeps what was pre-ticked",
          kept == [0], str(kept))

    # The non-interactive side is what the owner asked to leave alone: it takes
    # its basis from a flag and still refuses a bad one on the first try.
    try:
        resolve_basis(None, "CLAUDE.MD")
        direct = "no refusal"
    except Refuse as exc:
        direct = exc.code
    check("I2 — NON-interactive resolve_basis is unchanged: a bad value "
          "refuses at once", direct == "guidance-basis-invalid", direct)
    check("I2 — the guidance choices offered are exactly the accepted ones",
          list(GUIDANCE_NAMES) == ["AGENTS.md", "CLAUDE.md"],
          str(GUIDANCE_NAMES))


def zero_width_terminal(ctx) -> None:
    """A terminal that reports NO width must not take the installer down.

    Found by driving the arrow-key path under a freshly forked pty, which
    reports 0 columns instead of raising: the redraw divides by the width, so
    the whole picker died with ZeroDivisionError before drawing a single row.
    A user hits the same thing in a detached multiplexer pane or a CI runner.
    """
    check = ctx.check

    print("\nI3 — a terminal reporting zero columns")
    saved = os.get_terminal_size
    os.get_terminal_size = lambda *a: os.terminal_size((0, 0))
    try:
        cols = tui._term_cols()
        try:
            rows = tui._visual_line_count("a" * 200, cols)
        except ZeroDivisionError as exc:
            # Reported as a FAIL, never raised: a check that takes the whole
            # suite down with it prints no verdict at all, and a run with no
            # verdict reads to a grep like a run with no failures.
            rows = f"crashed: {exc}"
    finally:
        os.get_terminal_size = saved
    check("I3 — a zero-column report is floored where the width is read",
          cols == tui.DEFAULT_COLS, str(cols))
    check("I3 — the wrap count survives it instead of dividing by zero",
          rows == 3, str(rows))
    check("I3 — a normal width still counts wrapping the same way",
          tui._visual_line_count("a" * 200, 80) == 3
          and tui._visual_line_count("", 80) == 1,
          str(tui._visual_line_count("a" * 200, 80)))
