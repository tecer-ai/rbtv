# briefing template — copy into {run-package}/workers/{agent}/agent.md

One FOLDER per seat: `workers/{agent}/` holds `agent.md` (this briefing), a thin `CLAUDE.md` +
`AGENTS.md` loader pair (read briefing → memory → package protocol; mark memoryless seats
MEMORYLESS), `memory.md` (closer-written — persistent seats only, never pre-created), and
`transcripts/` (created by export). Fill every section; delete the guidance comments. Rules for
authoring briefings: `protocol.md` § Briefing authoring rules (isolation, folder form +
frontmatter keys, verifiable premises, pre-declared done gate).

```markdown
---
type: document
tags:
  - rbtv-sb-merge-refactor
agent: {agent-name}        # roster signature — launch discovers briefings by this key
harness: claude            # optional; claude | codex | opencode (default claude)
model: opus                # claude alias, or provider/model slug for opencode (REQUIRED there);
                           # omit on codex for the plan default. Fable for taste/rigor seats
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
                           # persistent seat is flagged to leader with the exact
                           # `close <agent> --renew` command to run
---

# {agent-name} — {one-line role}

**Status: {SPECIFIED — execute on launch | SPECIFIED, GATED — do not execute step X without Y}**

## Mission

{What this agent exists to produce, in 2–5 sentences. Outcome, not activity.}

## Surfaces you own (single-writer)

{Exact files/folders this agent may write. Anything else: claim via message first.}

## Pre-reads (paths only — never another worker's briefing)

{Absolute paths, each with one line saying what the agent needs FROM it.}

## Premises to verify first (R-audit-premises)

{Every factual claim this briefing makes about the target, as commands to run.}

## Execution contract

{Numbered steps. Coordination points marked. Owner-gated steps marked OWNER-GATED.
 Persistent seats end with a completion message then plain `checkout` — it exports the seat's
 transcript first (`--no-export` is the escape for a dead pane). Ephemeral seats end with plain
 `depart`, which exports, checks out and kills their own pane. Neither command takes a name —
 the seat's identity is resolved from its pane (protocol item 8).}

## Done gate (pre-declared — judges rule against THIS)

{Objective criteria. Each one checkable by a third party without this agent's help.}

## Never

{The specific things this agent must not do, with the reason stated once.}
```
