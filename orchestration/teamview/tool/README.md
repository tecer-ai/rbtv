# `teamview` — responsive team-run dashboard CLI

One live screen for a multi-agent tmux run: the session's windows/panes with agent names, plus
the coordination log's last sends.

> **Plan limits are not here any more.** The provider plan-limit bars moved OUT of teamview to
> the **`acct`** CLI (`acct usage`, `acct usage --posh` for the live bar view). Accounts and
> their plan windows are a property of the BOX; teamview renders ONE RUN. Keeping both in one
> screen also cost teamview its entire credential-reading, network-calling and process-scanning
> surface — see [Proving the boundary](#proving-the-boundary), which is one lane shorter for it.

> **teamview RENDERS the run's state; it no longer SENSES it** (settle ledger R24, task 7.34).
> `team-monitor` is the run's one raw-source sensor — it reads the tmux panes, the harness session
> files and `/proc`, and writes ONE canonical snapshot to `{goal}/runs/run-{n}/state.json`.
> teamview reads that file and nothing else. It **always shows the snapshot's age**, and a **stale
> snapshot renders as a visible WARNING** rather than as silently-current data. See
> [Proving the boundary](#proving-the-boundary) for what is deliberately outside it, and
> [What changed in R24](#what-changed-in-r24) for the two behaviour changes this cost. Below the constant first line, the
body renders the COMBINED view (every window/pane, plus messages) statically whenever the
measured frame is large enough to show everything at once; only when it is too small does the
body CYCLE every ~10s instead — the windows/panes view (itself paged into as many views as the
height needs), then the messages view (the coordination log's last sends, off the snapshot),
then back around. `--view {auto,panes,messages,combined}` pins
one body instead of the adaptive default. An orchestration-module component (runnable CLI,
python3 stdlib-only — no install step). Generalized: nothing user-, workspace-, or
machine-specific is baked in.

Origin: promoted 2026-07-24 from a workspace team-kit's overview tooling after it proved
out on a live multi-agent run.

## Run

```bash
python3 orchestration/teamview/tool/teamview.py                  # the run package found by walking
                                                                #   UP from the current directory
python3 .../teamview.py --package <run-folder>                  # or name the run folder outright
                                                                #   (the canonical form)
python3 .../teamview.py <session>                               # a name is CHECKED against the
python3 .../teamview.py session <session>                       #   snapshot's own `session` field
python3 .../teamview.py --once | --interval 5                   # one snapshot / repaint cadence
python3 .../teamview.py --once --no-rotate                      # COMPLETE combined snapshot:
                                                                #   every window/pane + messages,
                                                                #   no view cycle (can exceed
                                                                #   terminal height)
python3 .../teamview.py --view panes | messages                 # pin one body: windows+panes only
                                                                #   / last coordination sends only,
                                                                #   no alternation ever (auto is
                                                                #   the fit-based default;
                                                                #   combined = --no-rotate)
python3 .../teamview.py --help-security | --help-panes          # audit surface (what is read,
                                                                #   never-touches-tmux) / pane states
python3 .../teamview.py --selftest                              # must exit 0 after ANY edit here

acct usage --posh                                               # the plan-limit bars, now their
                                                                #   own CLI (see acct --help)
```

**Nothing resolves to a guess.** With no `--package` and no `state.json` in any parent
directory, teamview REFUSES — printing the two runnable commands that fix it (point at a run
folder; or start the sensor if the run folder is right but has no snapshot) to stderr, and
exiting 2 with an empty stdout. A positional name that disagrees with the snapshot's own
`session` refuses the same way. This is the old unknown-session refusal's contract kept
verbatim: a wrapper script must never record success for a view that showed nothing.

Every failure to READ the snapshot — missing, corrupt, wrong-shaped, or listing zero panes —
renders as a loud error frame naming the cause, never as an empty dashboard. An empty dashboard
reads as a quiet room, and that mistake has a number in this project (G-153).

`--interval` is the DISPLAY repaint cadence. The snapshot is RE-READ every frame, which is
what makes the age advance and the STALE warning fire while teamview keeps running.

Symlink it onto PATH per machine (like `ignite` / `sd-graph` — never synced by git):
`ln -s <abs>/teamview.py ~/.local/bin/teamview && chmod +x ~/.local/bin/teamview`.

## What it shows

- **Session block** — an ASCII grid: each window is a column (bold header, `*` = active
  window; see the R24 note on window LABELS below) with its PANES stacked beneath it; a seat
  that has been ACTIVE RECENTLY carries a trailing `+` (⚠ R24 CHANGED THIS SIGNAL'S INSTRUMENT
  AND ITS MEANING: it used to mean "this pane's visible content differed across two tmux
  captures ~0.6s apart"; it now means "this seat's harness wrote to its transcript within 45s
  of the capture". Coarser, and from a different instrument — relabelled here rather than
  silently reused under the old description). A pane whose harness has exited (a bare shell) renders dim with an explicit
  `shell` tag — distinct from a live pane whose agent info merely failed to resolve. An
  empty-titled pane with no roster name renders a dim `?`. Work is often bursty,
  so a seat flips between `+` and unmarked as it starts and finishes turns — that is honest,
  not a glitch. Seat names come from the snapshot's own `seat` field (team-monitor resolves
  them against the run roster) because agent TUIs rewrite their own pane titles; a pane whose
  occupant has not checked in yet carries no seat name and falls back to its cleaned title —
  a launched-but-silent harness is a real state and is reported as one, never guessed. Pure ASCII
  markers throughout — no arrow or box-drawing glyphs (ambiguous-width characters break column
  alignment in some terminal fonts). Narrow/tiny layouts render each window as its own flowed
  line block (`*name:` then panes), wrapping between panes. The BODY renders the COMBINED
  view (every window/pane + messages) STATICALLY whenever the measured frame is large enough to
  show everything at once; only when it is too small does the view CYCLE every ~10s instead
  (stateless — derived from wall clock, so the refresh loop cycles naturally and `--once`
  shows whichever page is current): the windows view — paged into as many views as the height
  needs, with a `(windows N-M/T - rotating)` note — then ONE
  messages view (see below; the slot exists only when the snapshot carries a message tail),
  then back around; nothing is permanently hidden, and the first line stays constant across
  every phase. `--view {auto,panes,messages,combined}` pins one body instead of this
  adaptive default: `panes` or `messages` show only that body at every tick (never
  alternating), `combined` forces the static
  combined frame (= `--no-rotate`), and `auto` (default) is the fit-based behavior above.
  The WINDOWS header carries the run's average dispatch payload — `dispatch ~N tok avg/seat`,
  the ~tokens a freshly launched seat must read before working regardless of its prompt or
  agent type (shared boot files + its own `seat.md`/`memory.md`), rendered straight off the
  snapshot's `dispatch_tokens` field and rendered as NOTHING (never a fake 0) when the
  snapshot predates the field.
- **Messages block** — the coordination log's last sends off the snapshot's `messages` field
  (team-monitor parses `coordination/messages.md`; teamview never opens the log — R24), in
  log order (newest LAST), one aligned row each: how long ago · sender → recipient · as much
  of the text as the row can hold (`…` marks the cut; the age and route columns pad to the
  block's widest so the text starts on one straight edge). Overflow drops the OLDEST rows
  with a `(+N older not shown)`
  note, never the newest. A snapshot without the field renders a loud explanation on the
  messages page rather than an empty one.
  A SINGLE window with more panes than fit rotates its OWN pane list
  the same way, with a `(panes N-M/T - rotating)` note — a 6-seat window in a 1-pane-tall
  slot never renders as if it were a dead 1-seat window with no hint the rest exist. A
  CRITICAL pane — past its own ctx-refresh threshold, at/above 85% context regardless of
  `--package`, or stuck awaiting approval — is PINNED into every rotation page instead of
  cycling out of view (the note gains a `· pinned` tag when this holds a page steady); the
  pin holds the WHOLE cycle on that windows page — the messages view waits until the pane is
  dealt with, while the alarm-rollup header line keeps every phase honest. The pin only
  matters while CYCLING: a frame that fits the static combined view renders every window and
  pane regardless, so nothing is hidden for the pin to hold open.
  `--no-rotate` (= `--view combined`) disables the cycle entirely for a COMPLETE combined
  snapshot in one frame — every window and every pane at once, plus the messages block, best
  paired with `--once` (the output can grow taller than the terminal). A seat stuck at a
  permission or trust prompt renders its name RED
  with a trailing `?!` (detected in the same busy-sampling capture — claude's numbered
  Yes/No dialogs, codex's "Action Required", and generic trust-this-folder prompts — no
  extra tmux call), overriding the busy `+` marker.
- **Per-seat context-refresh warning** — with `--package`, each seat's `ctx-refresh:` % is
  read from its OWN `workers/<agent>/agent.md` frontmatter (no key = no threshold, never
  enforced). A pane whose context used % has reached that seat's own threshold renders its
  ctx cell RED with a trailing `!` (e.g. `ctx55%!`), regardless of the normal green/yellow/
  red color band it would otherwise get. WITHOUT `--package` this check never runs — the
  session-stats line then carries a `no --package: thresholds/roster off` cue so a plain
  green `ctxN%` is never mistaken for "confirmed under threshold" when it really means "never
  checked" (an operator made a wrong renewal call on exactly this silent gap).
- **Graceful degradation at every width** — the no-package cue, every rotation footer, and
  every ctx VALUE shrink to a shorter but still-COMPLETE form as the pane
  narrows (down to ~60 cols) instead of relying on the outer hard clip's blind mid-word cut.
  A seat's harness/age drop before
  its ctx% (and any past-threshold `!`) does; a rotation footer shrinks from
  `(windows 2-3/5 - rotating)` down to a bare `(2-3/5)` or `+3` before disappearing
  entirely — it is never shown at a length that would need cutting mid-value.
- **System RAM+CPU readout** — the header line also carries available RAM and CPU load
  (`RAM 1989MB/7746MB  CPU 0.7/4`), read stdlib-only from `/proc/meminfo` and
  `os.getloadavg()`/`os.cpu_count()` — no new deps. Colored by pressure (green comfortable,
  yellow past ~1.5GB-available/75%-load, red past ~500MB-available/at-or-over core count)
  so an operator spots an OOM risk at a glance (this run hit an OOM cascade
  with no such warning). Degrades the same graceful way as every other cue — RAM detail
  shrinks before CPU drops, then the whole cue vanishes rather than clip mid-value — and
  disappears entirely (no crash) on a platform where neither reading is available.
- **Alarm rollup line** — every layout's windows header also carries a fixed one-line
  rollup — `13 panes · worst ctx94%~ · 1 red · 0 ?!` (total panes, worst context %, count
  at/past red, count awaiting approval) — above the rotating detail, so a single glance
  proves (or disproves) "nothing is alarming" even when rotation currently hides most
  panes. It shrinks to a short form (`13p ctx94%~ 1r 0?!`) before ever clipping.
- **Marker legend — OFF the dashboard entirely** (owner ruling 2026-07-28). No layout renders
  a legend at any size, on either phase: every row goes to data. This REVERSES the earlier
  decision that put a one-line mini legend on the strip/narrow/tiny layouts, and the accepted
  cost is stated plainly — an operator on a small pane now has no on-screen key for `?`
  (awaiting approval) or the color bands, and must run the command below to decode them.

  The key lives in one place: **`teamview interface-legend`** — prints every marker, one per
  line, and exits. It is a positional subcommand intercepted BEFORE package discovery, so it
  works from anywhere, including outside a run package where the dashboard itself refuses with
  exit 2; reading the key never depends on having a live run. It touches no snapshot, no cache,
  no network. It renders from the SAME `LEGEND_ITEMS` / `LEGEND_CTX` tuples the pane cells mark
  with, so a marker added to the dashboard cannot silently go undocumented (pinned by a
  selftest). The same legend text remains in `-h`'s description, and `--help-panes` documents
  every pane state with its cause and remedy. Truncation glyphs are split: `…` marks EVERY text cut
  (names, titles, clipped lines); `~` means ONLY ctx-match uncertainty, never truncation.
  Color-band thresholds are explicit everywhere: green <60, yellow <85, red ≥85 (plain red
  = high value; red with `!` = past this seat's own threshold).
- **Per-pane agent info** — every pane row also carries the agent running in it:
  `seat+ harness:model ctxN% age` — harness (the pane command, dim), model, context-window
  used % (colored green <60 / yellow <85 / red ≥85), and last-activity age (`now`, `Nm`,
  `NhMMm`, `NdNh`). Resolved by the sibling **ctx-monitor** CLI
  (`orchestration/team-monitor/tool/ctx_monitor.py`, imported by path) from each harness's own
  session record — claude transcript (exact pid→transcript map when the team-kit statusline
  is installed), codex rollout, opencode db, kimi wire, argv/TUI fallbacks — see its README.
  Without ctx-monitor the rows degrade to seat + pane command.
Every layout leads with two fixed rows: the **session-stats line** (windows · panes · time) on its own — constant across the whole cycle — then the current view's own bold+underlined header (`WINDOWS · PANES` or `MESSAGES`), carrying the alarm rollup, scoped over the body beneath. So the session stats are never misread as a table header, and every cycle phase names itself. (`--no-rotate` renders both headers in its one combined frame.)

## Proving the boundary

The R24 criterion is that **no raw-source read remains** in teamview. ONE lane is deliberately
outside that boundary, and it is NAMED rather than quietly scoped out — a proof that passes
because someone narrowed it, without saying what was narrowed away, is theatre.

⚠ **This list SHRANK; it was not widened.** The provider plan-limit lane used to be the second
row here — task 7.34's own `_Note:_` ordered it left in place (*"do not 'purify' them out while
refactoring"*), which was right at the time. It has now left teamview ENTIRELY for the `acct`
CLI, taking `ps_processes`, `claude_account_of` (`/proc/<pid>/environ`), `opencode_store`, the
OAuth/statusline readers and every network call with it. The exemption was retired, not relaxed.

| Lane | Why it is outside | Its reads |
|---|---|---|
| **Box CPU usage %** | `state.json`'s `box{}` carries RAM, swap, load, cores and memory pressure — and NO cpu field. Ruled PROVISIONAL by the run-2 leader (2026-07-27), extending the `_Note:_`'s own classification to a second named lane. | `cpu_usage_pct` (`/proc/stat`) |

⚠ **Box CPU is not a field to "just move" into `box{}` later.** `cpu_usage_pct` is a
**between-frames delta** — teamview repaints every ~1s, so it reads like `top`'s. team-monitor
captures every ~20s. Adding a `cpu` field at the sensor's cadence, under the same label, would
silently turn a ~1-second reading into a 20-second average. Whoever closes that follow-on must
change the LABEL too, or not ship it.

`--selftest` proves the boundary mechanically, and it is an **AST walk, not a grep**: written as
a text scan it matched this file's own prose — the module docstring's `/proc/meminfo`, the
`--help-security` text, and the source of the check itself. A proof that counts the words
DESCRIBING a read as a read is not a proof. The hand-runnable grep, for a human who wants to see
it directly (every hit must fall in a lane above):

```bash
grep -n '/proc/\|"tmux"\|ctx_monitor' teamview.py | grep -v '^\s*#'
```

## What changed in R24

Two behaviour changes, stated rather than left to be discovered:

1. **Bare `teamview` no longer auto-picks the only running tmux session.** It resolves a run
   package — `--package`, else a walk UP from the current directory (the convention `coordinate`
   already uses, so it keeps working from any seat pane). From OUTSIDE any run package it now
   refuses with the exact command to run. That auto-pick was a *tmux* capability, and R24 removes
   teamview's right to ask tmux anything; restoring it would mean inventing a scan of
   `.rbtv/goals/*/runs/*` from an assumed vault root, a discovery convention this system does not
   have.

2. **Window headers show `INDEX NAME`, and the `*` marker works again.** Field (1) of the R24
   follow-on is CLOSED. The sensor chain now asks tmux for `#{window_name}`, `#{window_active}`
   and `#{pane_active}` alongside `#{window_index}` (`ctx_monitor.list_panes`), and
   `team_monitor` carries all three into `seats[].window_name` / `.window_active` /
   `.pane_active`.

   The INDEX always leads the header and is never dropped — it is the tmux target, while the
   name is display-only and drifts independently of what the window holds.

   The two active flags are **distinct facts and are never collapsed**: tmux has one active
   window per SESSION and one active pane per WINDOW. So `*` on a header marks the single tab
   you'd land on when attaching, while `*` prefixing a seat name marks that window's focused
   split — several of those show at once, and the starred header is what ranks them. It is a
   PREFIX by design: the suffix slot already carries `+` (busy) and `?` (awaiting approval),
   and cells shrink from the right, so a suffixed star would be the first casualty on exactly
   the narrow frames where focus matters most.

   A snapshot written by a pre-follow-on sensor still renders — bare index, nothing starred.
   It degrades by one field; it never blanks or crashes.

   Field (2), box CPU%, is deliberately NOT closed with it — at the sensor's ~20s cadence it
   becomes a different metric wearing teamview's ~1s label. See `ideas.md`.

Also new: `roster_absent` (the GHOSTROW input — a roster row whose pane left the room, or whose
pane is still there holding no harness process) renders as a trailing `absent` pseudo-window.
Dropping it would render a vanished seat as nothing, which is absence indistinguishable from
health.

## Responsive layouts (chosen from the pane's own size, re-measured every frame)

| Pane shape | Layout |
|------------|--------|
| ≥70 cols, ≥16 rows | **full** — sectioned view: big bars + per-window member list |
| wide, <16 rows | **strip** — full-width window grid and full-width folded bars, one per cycle phase when cycling (the team-kit control-panel shape); `--no-rotate`/`--view combined` render them side by side |
| <70 cols, tall | **narrow** — stacked mini-bars + window list |
| <70 cols, <18 rows (≈1/6 screen) | **tiny** — token summary lines, no bars. Plan-usage limits render ONE `label: N%` per line (never two flowed onto the same line) so a percent can never visually read as belonging to a neighboring label at this width — and the percent KEEPS its green/yellow/red urgency color (color costs zero columns; a bare `97%` rendering identically to `12%` was a verified false all-clear) |

## Where the plan limits went

`acct` — `.rbtv/mirror/meta/providers/capabilities/acct/` (moved out of this module 2026-08-14), on PATH as `acct`. It owns provider accounts end to end:
parking logins in named slots and switching between them (`acct claude use rbtv`), and reading
each account's plan windows (`acct usage`, or `acct usage --posh` for the live bar view this
dashboard used to render). Its own `acct providers` documents every usage source and endpoint.
