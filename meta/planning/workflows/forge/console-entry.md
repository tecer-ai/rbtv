# forge — the console entry point

**You are reading this because the `build` router (`references/build.md`, this component's one
router surface) routed a request here.** Forge builds ONE small part of a component that already
exists — a reference, a prompt, a task, a seat, a capability, an exposure entry, or a sub-agent
definition — and it builds what it specifies in the same run. Your job is setup: you get the user
from "I want to add/change/read X" to **one command they type in a real terminal**. You never
author the part yourself, and you never run the forge workflow yourself — its own seats do that.

Written to be read cold. Nothing below assumes you saw an earlier turn.

---

## 1 — Routing lives in the router

The kind router — per-kind authoring guide, target-path shape, registration act, escalation
conditions, and the `<component-root>` write-destination rule — lives in `references/build.md`
§1–§2 (owner-ruled 2026-08-21; it moved there from this file). If you arrived without reading it,
read it now and confirm the request truly is forge-shaped before scaffolding anything.

---

## 2 — Goal scaffolding

The generic procedure is NOT repeated here. Read the plan-console workflow's console entry point —
`workflows/plan-console/console-entry.md`, a sibling folder of this one — and run its steps 0 through 3
exactly. Forge substitutes five values into them, and nothing else changes:

| Where planning says | Forge uses |
|---|---|
| workflow `plan-console` | workflow `forge` (`--workflow forge`; the manifest resolves as `<catalog-root>/planning/workflows/forge/forge.csv`) |
| a goal name of the user's choosing | `forge-<kind>-<subject>`, lowercase kebab-case — e.g. `forge-reference-cage-grants` |
| the goal contract file | the user's request text, verbatim — it IS the goal seed `forg-intake` reads |
| the goal's retry threshold | `2` (owner ruling 2026-08-12) — up to two automatic FAIL→rebuild rounds through the judge's `on-fail-relaunch` loop, then the owner (`rbtv-goal retry-threshold`) |
| the bindings sheet | the casting sheet for `forge.csv`, under `.rbtv/config/modules/meta/planning/bindings/` — one file per workflow, authored only through the `bindings` tool |

Everything else in that document binds unchanged: the workflow's `default-execution-mode` is read
from `workflows/forge/workflow.md`, the lane question is asked rather than defaulted, materialization
is create-only, and the `rbtv run` command is handed over rather than run for the user.

---

## 3 — Run-time configuration

Forge reads ONE value from ONE file, `forge.json`, under this component's module configuration
folder — `.rbtv/config/modules/meta/planning/forge.json` relative to the workspace root:

| Key | What it names | Read by |
|---|---|---|
| `kg_query_command` | the read-only knowledge-graph query command `component-lint` is handed as `--kg` | `forg-builder` and `forg-judge`, on every lint run |

The value is never typed into a prompt, a task, or a manifest — that is why it lives here. The file
is the owner's to author, and a missing key is a REFUSAL of the lint step, never a guess: tell the
user which key is absent and let them write it. A CLI piece needs no key of its own — a CLI is a
capability's tool and lands at `capabilities/<name>/tool/` inside its owning component, a target path
the intake resolves like any other piece's.
