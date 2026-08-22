---
description: decision procedure for when a capability exists at all and what its in-place instruction file carries
tags: [planning]
---

# capability — the invoked kind

Record first: `sd-graph show capability`. It rules meaning and legality; this guide rules the judgment calls. On any mismatch, the record wins.

## what it optimizes for

Reuse without a lifecycle: a purpose-independent ability any consumer can reach mid-work, documented once, in place — never assembled into a prompt.

## why it exists

Work keeps needing the same abilities. Rebuilding one per consumer violates one-fact-one-home; leaving one goal-local strands it. A capability is the cataloged, reachable form — an INVOKED cognitive unit, reached during work through its exposure or a prompt's resources bridge.

## when one exists at all

The hardest rung-1 call in the system. Walk it in order and stop at the first holding rung:

1. **Shop first** — does the scaffolding already have it? Check the capability cards before building anything.
2. **Is it a capability at all?** The test is purpose-independence, not step-count: its logic references no consuming workflow's purpose, and it owns no deliverable-with-completion. Owns a lifecycle → it is a workflow. Applied rather than executed → it is a reference.
3. **Would the file restate an existing surface?** A capability file that paraphrases a CLI's own `--help` must not exist — the help IS the documentation; a worse copy of it is a restatement liability, born to drift and be deleted.
4. **Needed but missing?** It is not built by the planning seat: plan a toolsmith task, ordered by `after` edges before the tasks that need it.

A capability ALWAYS lands in the scaffolding — registered and exposed, never left goal-local. It is purpose-independent by definition and has no goal to die with; a toolsmith task's done contract includes that registration.

## what belongs — and what never does

One in-place instruction file (no XML section — invoked kinds keep in-place files):

- **Body** — the procedure: the capability's own instructions; the manual for its tool when one exists, plain executable steps otherwise.
- **Frontmatter** — the i/o spec: inputs · outcome · outputs, in place, never a separate file (author them per `references/kind-io-spec.md`).
- Optionally a tool — a script or CLI as its executable core; not every capability has one.

Never: a consuming workflow's purpose baked into the logic · restated tool help or record content · goal- or run-specific values · its own done contract (a capability has no lifecycle to complete).

## where that file lives — component root, or a `capabilities/` folder

Same in-place file either way; only the depth differs. Start shallow and make the folder EARN itself:

| The component holds | The file lives at |
|---|---|
| ONE capability, carrying no tool and no sub-structure | `<name>.md` at the component root — the live shape of `.rbtv/mirror/web/browse/browse.md` (owner-ruled 2026-08-08; the reasoning is in that component's `component.md`) |
| MORE THAN ONE capability, or one carrying `tool*/` code or any other sub-structure | `capabilities/<name>/<name>.md` — the folder exists to hold that payload beside the file |

A second capability or a first tool is what MOVES the file; never pre-build the folder for sub-structure the capability may never grow. Check the shape before writing — `sd-graph show "capability folder"` · `sd-graph show "cognitive-unit file"`: the KG file schema states the folder path, and the root-file form is the corpus's attested one-capability variant of the same in-place rule. Neither form excuses registration or exposure.

## how to write an optimal one

1. Answer the meta-question in one line — what this capability optimizes for, why it exists. No answer → do not create it.
2. Write the procedure for a consumer with zero context: entry point, steps, failure modes.
3. Declare the i/o spec frontmatter-first; a capability whose interface cannot be declared is not yet understood.
4. Keep it purpose-free: name no consuming workflow. If you cannot, it is not a capability — reclassify it.
5. Register and expose it in the scaffolding in the same act that creates it — the artifact set per `component-anatomy.md`, the exposure method and row decision per `exposure.md` (siblings in this folder).
