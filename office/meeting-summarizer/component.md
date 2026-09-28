---
description: "The meeting-summarizer capability — detects new meeting transcripts across a watched Google account and Tactiq's Drive auto-save, produces exactly one corrected summary per meeting through the summarizer skill, files it with its transcripts at its resolved destination, and tracks doubts an owner must answer. No chat transport of its own: an agent's own reply mechanism carries the ask/answer."
---

# meeting-summarizer

A capability (owner ruling 2026-09-28, `decisions.md` "Agent settings vs capabilities"): a reusable
skill plus its tools, installable into any agent home. It carries no agent-specific value —
accounts, destinations, and checkout locations are settings an installing agent supplies, never
typed here.

## What it does

One cycle: `detection-cycle` polls every watched account and source (Google Meet, Tactiq's
Drive-autosaved export, Gemini notes) once, settling meeting identity and advancing one watermark.
For each new meeting, `per-meeting-job` stages its transcript, drives the summarizer skill (a
separate, unattended model turn it launches itself) to write exactly one corrected summary, and
records a doubt-handoff row when the summary carries an unresolved term. `publish-job` files each
settled summary and its transcripts at the resolved destination, commits, and pushes. `doubt-answer`
is this capability's own owner-Q&A ledger — which doubts are open, which have been asked, and
applying an owner's answer back through the summarizer skill's amendment mode — reused by whichever
reply mechanism the installing agent has; it posts nothing itself.

## Entry points

- **`summarizer-cycle`** (skill) — the one entry an agent's turn loads on a scheduled wake: runs a
  whole cycle inline, in the foreground, reading the settings and state paths it is given.
- **`detection-cycle`, `artifact-bindings`, `per-meeting-job`, `publish-job`, `doubt-answer`** (tools)
  — the CLIs `summarizer-cycle` calls, each independently runnable for diagnosis.
- **`destination-resolver`, `source-adapter`, `meeting-matcher`, `transcript-merge`,
  `artifact-reader`, `channel-protocol`, `validate-seams`, `verify-access`** (tools) — library/support
  tools the entries above call; `verify-access` is also runnable directly when a detection tick
  refuses at the account boundary.
- **`meeting-summarizer`** (skill) — the actual summarizer skill content
  (`workflows/summarization/workflow.md`) `per-meeting-job` drives; never forked, only read.

## Settings and state — supplied by the installing agent, never carried here

Per the "Agent settings vs capabilities" ruling, this capability holds no settings file and no
workspace path of its own. Every tool below resolves its config-module home from an explicit
`--config-root`/`--config-dir` argument, or, when omitted, the environment variable
`MEETING_SUMMARIZER_CONFIG_ROOT` — never a hardcoded relative path. An agent installing this
capability points that argument (or the env var) at its own settings folder (e.g.
`<agent-home>/config/`) and its own state folder (`<agent-home>/state/`, for `doubts.jsonl`,
`outcomes.jsonl`, `resolved-doubts.jsonl`, and the rest) — both starting EMPTY for a new agent; no
state migrates from a prior instance.

## What this component is NOT

- **Not a summarizer of its own.** Producing the summary from a transcript is
  `workflows/summarization/workflow.md`'s job; `per-meeting-job` drives it and never forks it.
- **Not a router that guesses.** No destination is invented. It comes from the installing agent's
  route table (`destination-routing` config key); absent a match, the owner is asked.
- **Not a chat transport.** `doubt-answer` tracks doubts and applies answers; it never posts a
  message anywhere. The installing agent's own reply mechanism is the transport.

## Standing gaps (carried from the product this capability was extracted from, still true)

1. **The Google tokens carry no Meet or Drive scope by default** — `gtools meet records` refuses
   with `ACCESS_TOKEN_SCOPE_INSUFFICIENT` until the owner widens the relevant `gtools` config and
   re-auths. Widening scope is always an owner call, never this capability's.
2. **Tactiq has no CLI** — only an MCP server, itself unreliable on a non-Team plan. Detection
   reaches Tactiq transcripts through its Drive auto-save folder, not the MCP server; a harness with
   no Drive access cannot see Tactiq content at all and must say so rather than reporting "no new
   meetings".
