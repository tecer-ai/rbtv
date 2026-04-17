---
name: output-routing
description: "Interactive workflow — scan workspace, read existing CLAUDE.md files, propose File Routing blocks per level, confirm with user, write/edit."
---

# Output Routing Setup

Purpose: encode RBTV component output paths into the workspace's CLAUDE.md files so that the `rbtv-output-resolution` rule can resolve paths at runtime without prompting.

## Step 1 — Discover workspace structure

Ask the user, sequentially:

1. "Is this a single-project workspace (one repo/product) or a multi-project workspace (several projects under one root)?"
2. If multi-project: "Please list the top-level project directories you want routing for. I'll skip any you don't mention."
3. Read the installed `rbtv.yaml` to determine which RBTV modules (and therefore which output types) are active. Output types by module:
   - `core`: planning, doc, meeting-summary, create-component
   - `innovation`: business-innovation, product-discovery
   - `work-productivity`: pitch, design-extraction
   - `writing`: writing, tone-extraction

## Step 2 — Read existing CLAUDE.md files

Walk the identified projects plus workspace root:

- Read each `CLAUDE.md` that exists.
- For each, check whether a `## File Routing` section is already present (between `<!-- file-routing-start -->` / `<!-- file-routing-end -->` markers). If present, read its current routing table.
- Record: file path, whether a block exists, existing entries if any.

## Step 3 — Propose routing per file

For each level (workspace root, then each project), present to the user:

- The file path.
- The CURRENT state (no block / block with entries X, Y).
- The PROPOSED block, with entries that fit this level. Rules of thumb:
  - Workspace root CLAUDE.md: handles output types that apply to the entire workspace, or DELEGATES to sub-projects (e.g. "pitch" → route into `tecer-biz/` so that tecer-biz's own CLAUDE.md can refine).
  - Sub-project CLAUDE.md: handles output types specific to that project, using project-relative paths.
  - Use placeholders like `{client}`, `{project}`, `{prospect}` for segments the user will specify at runtime. Do NOT try to enumerate specific clients or projects in the routing block — that is runtime data.

Present proposals as a diff. Ask the user to approve, edit, or skip per file.

## Step 4 — Write the routing blocks

For each approved proposal:

- If the CLAUDE.md does not contain a `## File Routing` section, append one at the end of the file (after existing content). Wrap the table in the markers.
- If the section exists WITH markers, replace ONLY the content between `<!-- file-routing-start -->` and `<!-- file-routing-end -->`. Never touch content outside the markers.
- If the section exists WITHOUT markers, ASK the user whether to add markers (replacing the existing section content) or preserve it as-is (skip this file).

Confirm each write with the user before executing.

## Step 5 — Summary

Report:

- Which CLAUDE.md files were created or updated.
- Which output types now have routing.
- Which output types remain unrouted — these will trigger the degraded-mode behavior in `rbtv-output-resolution` (user prompted per-write). Suggest re-running this command when the right paths are known.
- If the workspace is a git repo, suggest committing the CLAUDE.md changes.
