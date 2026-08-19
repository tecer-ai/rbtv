# briefing template — copy into {run-package}/workers/{agent}/agent.md

One FOLDER per seat: `workers/{agent}/` holds `agent.md` (this briefing), a thin `CLAUDE.md` +
`AGENTS.md` loader pair (read briefing → memory → package protocol; mark memoryless seats
MEMORYLESS), `memory.md` (written by the seat's own `checkout --renew --handoff`, and by a closer
on the leader-initiated failure close — persistent seats only, never pre-created), and
`transcripts/` (created by export). Fill every section; delete the guidance comments. Rules for
authoring briefings: `briefing-authoring.md` beside the protocol (isolation, folder form +
frontmatter keys, verifiable premises, pre-declared done gate) — read it before filling this
template.

```markdown
---
type: document
tags:
  - rbtv-sb-merge-refactor
agent: {agent-name}        # roster signature — launch discovers briefings by this key
harness: claude            # optional; claude | codex | opencode (default claude)
model: opus                # claude alias, or provider/model slug for opencode (REQUIRED there);
                           # omit on codex for the plan default. Fable for taste/rigor seats.
                           # launch pre-validates the alias/slug shape and refuses the whole
                           # launch before opening any pane on a bad value (PROP-8)
effort: high               # claude only; optional (default high)
window: yes                # optional; yes -> own tmux window (tab) — ephemeral/loop seats.
                           # A NAME (e.g. wave-haiku) -> SHARED window of that name: first
                           # seat creates it, later seats become panes in it (wave layout).
                           # Omit for long-lived core seats (tiled pane in the leader window)
ephemeral: yes             # optional; memoryless one-pass seat: fresh relaunch each pass,
                           # departs itself, no memory.md, never closed/renewed
ctx-refresh: 50            # optional; context-refresh threshold % for THIS seat. watch.py reads
                           # it and enforces it per seat, falling back to its own global
                           # --context-pct for seats that declare none: past the threshold a
                           # persistent seat is flagged to leader, who relays it — renewal is
                           # YOUR act: `checkout --renew`, then the second call it prints,
                           # carrying `--handoff "<what your next session must do>"`
                           # ⚠ NO `outputs:` key here — RETIRED (D3, 2026-08-18) and REFUSED
                           # on sight at check-out and at materialize. Declared outputs live
                           # in the body's io-spec `## Outputs` block below.
---

# {agent-name} — {one-line role}

**Status: {SPECIFIED — execute on launch | SPECIFIED, GATED — do not execute step X without Y}**

## Mission

{What this agent exists to produce, in 2–5 sentences. Outcome, not activity.}

<io-spec>
## Outputs
{The seat's done contract (7.676/D3) — the ONE declared-outputs surface, read by BOTH the
 done-contract grading at `checkout` and the caged-launch admission gate. Each output is a
 backticked goal-relative token carrying a `/` and an extension — `seats/{agent-name}/plan.md`,
 or `./plan.md` for a file in the seat's own cwd (relative tokens resolve against `cwd:`; folder
 form: the seat's own folder). Plain `checkout` REFUSES to record `done` while any declared
 token is missing or zero-byte. A section with NO such token records `outputs-undeclarable`
 (nothing verified — loud); omit the whole block and the record says `none-declared`. NOT the
 "Surfaces you own" claim below — that is what a seat may WRITE; this is what it must have
 PRODUCED. Details: `briefing-authoring.md`.}
</io-spec>

## Surfaces you own (single-writer)

{Exact files/folders this agent may write. Anything else: claim via message first.}

## Pre-reads (paths only — never another worker's briefing)

{Absolute paths, each with one line saying what the agent needs FROM it.
 Two kit files are role-scoped and reach a seat ONLY through this list — omit them for every other
 seat: `{team-kit}/roles.md` for a leader, deputy, scientist, judge, verifier or closer
 seat and for any codex/opencode seat; `{team-kit}/briefing-authoring.md` for the seat that
 authors this run's briefings or seat descriptors.}

## Premises to verify first (R-audit-premises)

{Every factual claim this briefing makes about the target, as commands to run.}

## Execution contract

{Numbered steps. Coordination points marked. Owner-gated steps marked OWNER-GATED.
 Persistent seats end with a completion message then `checkout` — plain for the done disposition;
 `checkout --renew --handoff "<note>"` when the seat renews or context-refreshes instead (the CLI
 teaches the two-step; the handoff lands in the seat's `memory.md`; a `close: mechanical` seat is
 refused there — leader-side close-and-relaunch is its path; evidence at protocol item 8). It
 exports the seat's transcript first (`--no-export` is the escape for a dead pane). Ephemeral seats end with plain
 `depart`, which exports, checks out and kills their own pane. Neither command takes a name —
 the seat's identity is resolved from its pane (protocol item 8).}

## Done gate (pre-declared — judges rule against THIS)

{Objective criteria. Each one checkable by a third party without this agent's help.
 For every fix this briefing commissions, pre-register the acceptance bar HERE, before the work:
 the exact observation that will count as proof, and the ones that will NOT. A fix to a
 detection/matching/parsing mechanic must be proved against a fixture captured from the REAL
 regime it fails in — a hand-authored fixture is not evidence (`briefing-authoring.md`).}

## Never

{The specific things this agent must not do, with the reason stated once.}
```
