---
name: doc-export
description: "Export markdown to branded PDF or DOCX. Handles brand discovery, style category detection, and config artifact generation."
---

# doc-export Workflow

Two modes. Determine which mode to run from context: if the user provides a markdown file path, run Mode 2. If the user asks to set up or generate branding configs, run Mode 1.

---

## Mode 1: Config Creation

Generates all branding config artifacts for a workspace.

### Steps

1. Read the workspace root `CLAUDE.md`. Find the brand-related folder (look for references to brand, branding, assets, visual identity).
2. If no brand folder is found in `CLAUDE.md` → ask the user for the brand folder path.
3. Read all brand documents in that folder. Extract:
   - Font family (primary)
   - Monospace font
   - Color palette: primary brand color, heading color, table header background, table border color, alternating row color
   - Logo file path (relative to workspace root)
   - Heading sizes (h1, h2, h3)
   - Page margins
   - Line spacing
4. Generate ALL THREE artifacts in the brand folder in one pass. Present them to the user for confirmation before writing any file.

#### Artifact 1: `document-style.yaml`

Feeds the DOCX engine. Use the schema from `./shared/document-style-template.yaml`. Populate all fields from extracted brand values. Set `page.size` to `"a4"` or `"letter"` based on workspace context (default: `"letter"`).

#### Artifact 2: `document-style.css`

Feeds the PDF engine. Read `./engines/pdf/styling.md` for CSS patterns and structure. Generate a complete stylesheet using extracted brand values. Replace placeholder colors (e.g., `#1a3a5c`) with the workspace's actual brand colors. Retain all page-break rules and table structure patterns.

#### Artifact 3: `document-config.js`

Feeds the PDF engine. Read `./engines/pdf/branding.md` for `config.js` patterns. Generate with:
- `fs.readFileSync` to base64-encode the logo at the resolved logo path
- Branded `headerTemplate` with logo on the right and document title on the left
- Page number `footerTemplate`
- Correct margin settings (top margin must clear header height — minimum 35mm when logo is present)
- `stylesheet` pointing to `document-style.css` in the same folder

5. Present all three artifact contents to the user. Wait for confirmation. Write only after approval.

---

## Mode 2: Generate Document

Converts a markdown file to PDF or DOCX.

### Steps

1. Receive the markdown file path (from the invoking context or user message).
2. Ask the user: PDF or DOCX?
3. Determine style category:
   - Legal documents (contracts, agreements, terms, legal analysis, NDAs) → **legal styling**
   - All other documents (proposals, pitches, reports, plans) → **branded styling**

### If branded styling

4a. Read the workspace root `CLAUDE.md`. Find the brand folder.
4b. Look for `document-style.yaml`, `document-style.css`, and `document-config.js` in that folder.
4c. If not found → ask: run Config Creation mode now, or provide paths manually?
4d. Confirm the resolved config paths with the user before proceeding.

### If legal styling

4a. Read `./legal/legal-style.md` for conventions.
4b. Skip brand discovery entirely.
4c. Use `./legal/legal-pdf-style.css` for PDF output.
4d. Use `./legal/legal-docx-style.yaml` for DOCX output.

### Generate the document

5. Resolve output path: same directory as the input file, same base name, target extension (`.pdf` or `.docx`). If a file already exists at that path, warn the user before overwriting.
6. Generate:

**PDF:**
```
md-to-pdf --config-file {brand_folder}/document-config.js {input.md}
```
For legal PDF:
```
md-to-pdf --stylesheet {workflow_dir}/legal/legal-pdf-style.css {input.md}
```
Read `./engines/pdf/reference.md` for CLI flags and gotchas before running.

**DOCX:**
```
python {workflow_dir}/engines/docx/md-to-docx.py {input.md} {output.docx} --style {document-style.yaml} --workspace-root {workspace_root}
```
For legal DOCX:
```
python {workflow_dir}/engines/docx/md-to-docx.py {input.md} {output.docx} --style {workflow_dir}/legal/legal-docx-style.yaml
```
Requires: `python-docx`, `pyyaml` (`pip install python-docx pyyaml`).

7. Report the output path on success. Surface the full error message on failure — never swallow errors.

---

## Constraints

- Always confirm resolved config paths with the user before generating.
- Never infer a brand folder path not referenced in a `CLAUDE.md` or confirmed by the user.
- `{workflow_dir}` is the absolute path to this workflow's directory (`doc-export/`).
- Never hardcode company names in generated artifacts.
- The DOCX engine requires `python-docx` and `pyyaml`.
- The PDF engine requires `md-to-pdf` (npm package, install globally: `npm install -g md-to-pdf`).
