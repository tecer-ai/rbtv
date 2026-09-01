---
description: "Renders a structured vault document as a polished static HTML page via a deterministic template-filling CLI — no agent-authored HTML. First document type: a /plan seat-plan folder rendered as a status dashboard (seats by dependency wave, statuses, owner touchpoints, expandable seat bodies, companion files)."
inputs: "a document folder of a supported type (v1: a /plan seat-plan folder carrying seats.md)"
outcome: "a self-contained, self-explanatory HTML page of the document's current state, regenerable on demand"
outputs: "one .html file (default: inside the source folder), plus a machine-readable result line under --json"
# W6 — the CLIs this capability routes to (`exposes:` reference grammar).
exposes-cli:
  - posh-cli
---

# posh — deterministic document presentation

Turns a structured vault document into a polished HTML page by machine-filling a shipped
template — the **schema + deterministic builder** production model of
`references/html-standards.md`. The agent NEVER writes HTML here; the template owns the look,
the CLI owns the filling, and the markdown source files remain the source of truth.

Document types are CLI subcommands, each pairing a parser with a template in
`templates/`. v1 ships ONE type: `plan`.

## Procedure

1. Run the tool — it self-documents (`-h` per subcommand):

   ```
   python3 <this-folder>/tool/posh.py plan <plan-folder>
   ```

   Default output is `<plan-folder>/plan.html`, overwritten in place. `--out <file>` redirects;
   `--json` prints a machine-readable result (`type`, `source`, `output`, `seats`, `waves`,
   `pct_done`, `warnings`).
2. The page is a SNAPSHOT. When the plan's state changes (a status flip, a new seat), re-run the
   same command — regeneration IS the refresh mechanism; NEVER hand-edit the generated page.
3. Stderr `posh: note:` lines report parse degradations (an unknown status, a missing seat body,
   a dependency cycle); the same notes appear on the page. They are non-fatal by design — the
   page still renders, with the unrecognized content shown raw.
4. Workspace duties stay the caller's: where the workspace keeps a front-door index of
   reader-facing HTML pages, register (and on deletion, de-register) the generated page there in
   the SAME change.

## What `plan` renders

From `seats.md`: progress tiles and bar, seats grouped into dependency WAVES (computed from the
`after` column — the mermaid diagram is not re-rendered), status badges with the evidence notes
from each status cell, `⚠ owner touchpoint` flags, the owner-checkpoint table, and every
non-table remainder of the file under "Rules & contract". From the rest of the folder: each
seat's `seat.md` (executor line from its frontmatter, full body expandable), plus `read-first.md`,
`status.md`, `decisions.md`, `issues.md`, `loose-ends.md`, `doubts.md`, `ideas.md`,
`checkpoints/*.md`, and `judgements/*.md` when present — each a collapsible section. Nothing
found in the folder is silently dropped.

## Adding a document type

A new type is a parser + template pair: a `templates/<type>.html` template (markup blocks
delimited `<!-- posh:<name> -->` … `<!-- /posh:<name> -->`), a `render_<type>` function and
subcommand in `tool/posh.py`. The page MUST meet `references/html-quality.md` (self-explanatory,
jargon defined on the page) — the template carries the explanations, so a reader with zero
project context can follow the output.
