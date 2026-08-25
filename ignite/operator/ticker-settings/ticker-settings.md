# ticker-settings — the tick cadence-edit operator surface

The **first consumer `settings.json` has ever had** (core-build task 7.66). It implements § 2.3 of
`1-projects/rbtv-sb-merge-refactor-structure/ignite-operator-surface-design.md` — write the
machine-keyed cadence, append the audit line, show the consequence, restart to apply.

Reached as **`rbtv ignite ticker <verb>`**; the tool itself is `tool/rbtv-ignite-ticker`. It is an
OPERATOR surface (design § 1.1): it edits a config file and drives a systemd unit, presents no
token, never crosses the gateway, and **works with the daemon DOWN** — which is exactly when a
cadence that wedged the box needs changing.

| Verb | Does |
|---|---|
| `show [--json]` | this machine's effective ticker settings, each marked `set` or `default`, plus the tick-denominated ladder the current cadence implies |
| `set-interval <dur> [--restart]` | validate → write → append history → print the ladder → say it is not in effect, or restart to apply |
| `history [-n N]` | the last N settings changes, decoded |
| `selftest` | the probes below, run as one |

`<dur>` **requires a unit** — `15s` or `15000ms`. A bare number is REFUSED: `15` could mean 15 ms or
15 s, a 1000× difference in what the box does, and guessing either way is silently wrong.

## Where the values live

**One home, and it is the registry's:** `architecture/CMP-1-rbtv-runtime-root.md` § *Ticker settings
schema*. This document does not restate the schema (`PRIN-11`); it states how to drive it. In code
the one home is `ignite/runtime/settings.js`, shared by this surface and the daemon's boot path so
the two cannot drift.

```
.rbtv/modules/ignite/settings.json          machines.<hostname>.ticker.tick_interval_ms
.rbtv/modules/ignite/settings-history.jsonl one appended line per change, never rewritten
```

**Machine-keyed, not flat.** `.rbtv/modules/ignite/` is git-committed and travels to every machine,
so one flat value would be right on the VPS and wrong on the PC — DEC-7 sub-ruling 3's reasoning for
`server.json`, applied to the same problem.

## Two enforcement points, fail-closed at both

A cadence outside the floor/ceiling is refused **at this surface** (exit 3, nothing written) *and*
**at daemon boot** (a named error, the daemon refuses to start). The second exists because the first
can be walked around with a text editor, and **a surface-only bound is not a bound**. It is the
runtime's established idiom — `RBTV_IGNITE_LOG_RETENTION_DAYS` rejects a sub-floor window at boot in
the same place.

Floor (5 000 ms), ceiling (60 000 ms) and the periodic-job admission minimum (60 s) are
**owner-approved DEFAULTS carried by named config variables, not constants** (2026-07-26,
`system-definition/decisions.md#d-operator-surface-apply`). Lowering the floor legalises a faster
cadence — that is the point of their being configurable, and the probes prove it.

## Live-reload is REJECTED, not unimplemented

Design § 2.3, four reasons, the short form: the daemon materializes config once at boot and the
ticker engine is stateless between ticks with numbering continuing from `MAX(tick)+1` across
restarts, so **the restart a reload would avoid is already nearly free**; a reload path would be a
second code path with no second consumer (`PRIN-7`); in-memory tick-denominated caches have a
defined recovery contract for a RESTART and none for a mid-flight change; and restart is already an
operator verb. Write-then-restart composes two mechanisms that exist.

Accepted cost, stated plainly: changing the cadence interrupts in-flight supervision for the restart
window.

## ⚠ Which workspace — the surface refuses rather than guesses

The daemon takes `RBTV_IGNITE_WORKSPACE_ROOT` from its unit. This surface asks the unit for that
answer, and falls back to walking up from the cwd only when no unit names one. **If the two
disagree it REFUSES (exit 2), naming both.**

That refusal exists because the first build walked up from the cwd alone, and **the rbtv repo has
its own `.rbtv/`** — so an operator editing the cadence from inside the repo wrote a settings file
the live daemon would never read, with the edit reporting success and appending history. Found by
running the command, not by reading it.

## ⚠ The ladder this edit retimes

One engine duration is still stored in TICKS (`warnings.js` announce every 6), so **a cadence edit
silently retimes it**. Design § 2.2 rules it re-expressed in wall-clock; **that is R3's coupling
fix and is NOT task 7.66**. Until it lands, `set-interval` prints the derived value at the new
cadence so the consequence is visible before it takes effect. Showing it is not a substitute for
fixing it. (The tick-silence stall ladder this table used to also show — `stall_warn_ticks` /
`stall_halt_ticks` / `stall_kill_ticks` — is deleted [T4-R1]: no-progress is measured off
work-product, never off ticks of silence.)

## Probes

`probes/` — discovered and counted by `ignite/deploy/probe-suite.js`. Run one with
`node ignite/deploy/probe-suite.js --only <name>`, which keeps preserve mode (`G-163`).

| Probe | Proves |
|---|---|
| `probe-ticker-settings` | read + write: both live seed shapes, machine-keying, another machine's block left byte-intact, the six history keys, `from` computed from stored state, no history line on a no-op, both enforcement points, the configurable floor actually moving, the duration grammar |
| `probe-ticker-cadence-flow` | the criterion END TO END against a **throwaway daemon on a throwaway systemd unit** — default cadence at boot, an edit genuinely pending without `--restart`, adoption after it, and **supervision resuming measured by the observed interval between ticks**, not by the daemon's self-report |

Both assert their own completeness: a short tally is a FAILURE however many checks passed
(`G-121` — a truncated run reads greener than a complete one). Discriminating power is recorded in
`mutations.md` beside them.

**The live daemon is never touched by either probe.** The throwaway-unit pattern is `C1-standin`'s,
built for 7.67 and inherited here rather than re-derived; the flow probe asserts its target unit is
the throwaway one before every lifecycle call.

## Retirement

None. Unlike `daemon-operator`, this is not a v1 stand-in — it is the surface itself, reached
through the `rbtv` CLI where the design homes it (§ 1.4).
