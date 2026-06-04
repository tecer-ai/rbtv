# Research R4 — Agent-Comment Instructions Block

**Date:** 2026-06-03
**Scope:** Conventions for embedding machine-readable AI-agent instructions inside an HTML document, with format design for hypresent's agent-tagged comment feature.
**No files were modified other than this one.**

---

## 1. Existing and Emerging Conventions (What Actually Exists in 2025–2026)

### 1a. `llms.txt` — External file, not in-document

Proposed by Jeremy Howard (Answer.AI / fast.ai) in September 2024. A markdown file at `<domain>/llms.txt` giving LLMs a table-of-contents view of site content. As of early 2026, 849+ websites have adopted it, including OpenAI, Anthropic, Stripe, Vercel, and Cloudflare. **This is a file-at-server-root convention, not an in-document embedding technique.**

Source: llmstxt.org; Answer.AI post 2024-09-03 [1]

### 1b. `<script type="text/llms.txt">` — Vercel proposal, August 2025 — the closest match

On 2025-08-21, Vercel CTO Malte Ubl published a proposal to embed inline LLM instructions directly in HTML using an unknown script type:

```html
<script type="text/llms.txt">
  # Instructions for AI agents
  Content here (any markdown — cannot contain </script>).
</script>
```

**Technical basis:** HTML5 browsers silently discard `<script>` elements whose `type` attribute value they do not recognize. The element's text content is preserved verbatim in the DOM source but never executed. Unknown script elements can hold any text content (with the sole exception of the literal string `</script>`), making them valid containers for markdown or structured instructions.

Vercel shipped this on their default 401 authentication-error pages. The block guides agents toward authentication bypass flows and available MCP servers.

The proposal explicitly states it "doesn't need to be a formal standard — you can just start using it now." Agents find it by searching the raw HTML `<head>` for the type string.

Source: Vercel blog, 2025-08-21 [2]; DEV Community coverage [3]

### 1c. `AGENTS.md` — Repository-level file, not in-document

Launched August 2025 by OpenAI (Codex), adopted by Anthropic, Google, GitHub Copilot, Cursor, Windsurf, Amp, Devin, and others. Governed by the Linux Foundation's Agentic AI Foundation as of December 2025. 60,000+ repositories use it. Plain markdown, read natively by every major coding agent. **Lives in the repository filesystem, not inside HTML files.**

Source: agents.md; Augment Code guide 2026 [4]

### 1d. `CLAUDE.md` / `.cursor/rules/` / `.github/copilot-instructions.md` — Tool-specific files

Each coding agent ecosystem has its own instruction-file convention. All are filesystem-level markdown files. No tool has a standardized spec for discovering or acting on instructions embedded inside the source of an HTML content file being edited. **This is the gap hypresent's agent-comment feature fills.**

Source: gist by 0xdevalias; deployhq.com guide [5]

### 1e. Meta tags, JSON-LD, data attributes — Vaporware or off-target

No proposal for `<meta name="llm-instructions">` or a JSON-LD `@type` for agent instructions has reached even draft status as of 2026-06-03. JSON-LD is semantically correct for structured data but is designed for web-indexing schemas (Schema.org), not per-element coding instructions. Data attributes are element-scoped and not suitable for document-level preambles. **None of these are viable candidates.**

---

## 2. What Coding Agents Reliably Ingest

All major coding agents (Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI) operate on **raw source text** — they read the file content as a string, not a rendered DOM. This has two implications:

1. **Position and delimiter clarity matter more than MIME types.** A comment block at the very top of a file is found before any parsing; a `<script>` in `<head>` is also reliably found. Neither requires the agent to understand HTML semantics.
2. **Stable, unique open/close markers are essential.** Agents search files for patterns. Markers like `=====` fence lines or structured comment blocks with a consistent sentinel string are trivially greppable by both agents and humans.

Evidence for "agents read raw source":
- The Vercel `<script type="text/llms.txt">` proposal explicitly says "LLMs can look for it in the head section of a web page" — i.e., scan the source text for the type string.
- All AGENTS.md / CLAUDE.md tools load raw file content as context, not rendered output.
- Code generators (v0, Lovable) rely on system-prompt instructions, not embedded file annotations, for their own generation context — but their outputs are consumed as raw text by subsequent agents.

---

## 3. Placement Constraints

### 3a. Before `<!DOCTYPE html>`

An HTML comment is syntactically legal before the DOCTYPE declaration. The HTML5 parser (WHATWG living standard) processes comment tokens in the "initial insertion mode" by inserting them as comment nodes and **staying in the initial insertion mode** — it does not set the document's compatibility mode. The compatibility mode is determined solely by the DOCTYPE token that follows. A comment before DOCTYPE **does not trigger quirks mode in any modern browser** (Firefox, Chrome, Safari, Edge).

**The IE exception (legacy, irrelevant):** Internet Explorer 6–9 triggered quirks mode on anything before DOCTYPE, including comments. This behavior was specific to IE's pre-HTML5 parser and does not apply to any browser in active use as of 2026.

Authoritative source: htmlparser.info idiosyncrasies guide; WHATWG parsing spec §13.2.6.4.1 [6][7]

**Tradeoff of pre-DOCTYPE placement:**
- Pro: found immediately at byte offset 0 — no HTML parsing required; trivially located by any text scanner or agent tool call.
- Pro: never entangled with document content regardless of malformed `<head>` structures.
- Con: slightly unconventional; the HTML specification's "best practices" say DOCTYPE should be first. Technically legal; aesthetically unusual.
- Con: if a document is later processed by an HTML serializer that normalizes structure (e.g., tidy), the pre-DOCTYPE comment may be moved or removed.

### 3b. Inside `<head>` as first child

The canonical location for the Vercel `<script type="text/llms.txt">` proposal. First child of `<head>` is:
- Spec-legal, zero rendering impact.
- Resistant to HTML serializer normalization.
- Requires parsing past `<!DOCTYPE html>` and `<html>` and `<head>` to locate — trivial for any tool, but more characters before the block begins.

**Tradeoff:** slightly deeper in the file than pre-DOCTYPE but survives round-trips through HTML normalizers far better.

### Verdict on "beginning of the html code"

Both placements satisfy the requirement. For hypresent's use case — the file is a standalone HTML document read as raw source by AI coding agents — the operationally important property is a **stable sentinel string at the top of the file**, not exact DOM position. Either placement works. `<head>` first-child is recommended for its better round-trip resilience.

---

## 4. Format Design — Three Concrete Options

All three options share these invariants:
- The block is **derived entirely from the comment island** (`<script type="application/json" id="hyp-comments">`) on every save. It is never edited manually.
- It is **removed entirely** when no agent-tagged comments remain.
- The island is the **single source of truth**; the block at the top is a derived read-only cache for agents.
- Each entry references: comment id, DOM anchor (path + native id + context text), the instruction body, author, created date.

---

### Option A — Delimited HTML comment block (recommended)

```html
<!-- ===== HYPRESENT AGENT INSTRUCTIONS =====
This block is auto-generated from agent-tagged review comments in this file.
Each entry describes a change an AI coding agent should make to the element identified by its anchor.
Do not edit this block manually — it is regenerated on every save and removed when no agent comments remain.

[agent:1]
anchor: div:1/section:3 | id="slide-3" | "Tecer reduces operational"
instruction: Replace the bullet list with a two-column comparison table: left column "Before Tecer", right column "After Tecer". Keep existing copy verbatim in left column.
author: Henrique
date: 2026-06-03T14:22:00Z

[agent:2]
anchor: div:1/section:7/h2:1 | id="" | "Why Now?"
instruction: Change heading text to "The Market Window" and add a subtitle paragraph below: "Three forces converging in 2026."
author: Henrique
date: 2026-06-03T14:35:00Z
===== END HYPRESENT AGENT INSTRUCTIONS ===== -->
```

**Placement:** First child of `<head>`, before any other element.

**Why this works:**
- Zero rendering impact in all browsers regardless of placement; HTML comment syntax is universally understood.
- Delimiters (`===== HYPRESENT AGENT INSTRUCTIONS =====` and `===== END HYPRESENT AGENT INSTRUCTIONS =====`) are grep-stable and unique.
- No dependency on any MIME type or script type convention; readable by any agent without prior knowledge of hypresent.
- The one-sentence preamble on line 2 tells any reading agent exactly what the block is and what to do with it — no external docs required.
- Entries use a simple `[agent:N]` heading + `key: value` lines; trivially parseable with regex or line-by-line scanning.
- Cannot interfere with JavaScript or CSS parsers.

**Constraint:** HTML comment content cannot contain `-->`. Instruction body must escape or rephrase any `-->` sequence (extremely rare in prose). The serializer must sanitize this.

---

### Option B — `<script type="text/llms.txt">` block

```html
<script type="text/llms.txt">
# HYPRESENT AGENT INSTRUCTIONS
This block is auto-generated from agent-tagged review comments in this file.
Each entry describes a change an AI coding agent should make to the element identified by its anchor.
Do not edit manually — regenerated on every save.

## [agent:1]
- anchor: div:1/section:3 | id="slide-3" | "Tecer reduces operational"
- instruction: Replace the bullet list with a two-column comparison table: left "Before Tecer", right "After Tecer".
- author: Henrique
- date: 2026-06-03T14:22:00Z

## [agent:2]
- anchor: div:1/section:7/h2:1 | id="" | "Why Now?"
- instruction: Change heading text to "The Market Window"; add subtitle "Three forces converging in 2026."
- author: Henrique
- date: 2026-06-03T14:35:00Z
</script>
```

**Placement:** First child of `<head>`, before any other element.

**Why this works:**
- Aligns with the Vercel/llms.txt ecosystem convention (August 2025); discoverable via standard type-string scan.
- Browsers ignore it; spec-legal per HTML5.
- Markdown-formatted content is cleanly rendered in any LLM context window.
- Cannot contain the literal string `</script>` — the serializer must detect and escape/replace this if it appears in instruction text.

**Risk:** The `text/llms.txt` type string has no IANA registration and no formal standard as of 2026-06-03. It is an informal convention with minimal adoption outside Vercel's own 401 pages. Coding agents do not yet actively scan for it when editing local files (as opposed to fetching web pages). For a local-file editor tool, raw-source discoverability via a visible sentinel string (Option A) is more reliable than type-attribute sniffing.

---

### Option C — Dual-format: HTML comment fence wrapping a JSON block

```html
<!-- ===== HYPRESENT AGENT INSTRUCTIONS =====
This block is auto-generated from agent-tagged review comments. Do not edit manually.
Each entry: anchor identifies the target element; instruction is the change to make.
===== -->
<script type="application/json" id="hyp-agent-instructions">
[
  {
    "id": "1",
    "anchor": { "path": "div:1/section:3", "nativeId": "slide-3", "contextText": "Tecer reduces operational" },
    "instruction": "Replace the bullet list with a two-column comparison table: left 'Before Tecer', right 'After Tecer'. Keep existing copy verbatim in left column.",
    "author": "Henrique",
    "date": "2026-06-03T14:22:00Z"
  }
]
</script>
<!-- ===== END HYPRESENT AGENT INSTRUCTIONS ===== -->
```

**Placement:** First child of `<head>`.

**Why this works:**
- JSON is maximally parseable by code (agents writing code to process it can use `JSON.parse`).
- The surrounding comment fences make it trivially greppable even without JSON parsing.
- The `id="hyp-agent-instructions"` mirrors the comment island pattern already established in hypresent.

**Drawback:** The JSON island is not human-readable in diff/review without tooling. Instruction text requiring escaping (quotes, backslashes) adds friction. The comment island already stores JSON; wrapping instructions in a second JSON block duplicates the schema overhead without providing new discoverability benefits over Option A.

---

## 5. Should Agent Comments Also Remain in the Island?

**Yes. The island is the single source of truth.**

Rationale:
- The island already stores all thread data including the resolved flag, replies, author, anchor, and context text.
- The top-of-file block is a **derived projection** — it is regenerated from the island on every save, and removed when the agent-tagged comment is resolved or deleted.
- Storing the agent flag only in the island (as a boolean field, e.g., `"agentComment": true`) and deriving the top block from it preserves the existing round-trip guarantee: `comments.js` writes the island, `serializer.js` reads it, and the new top-block generator reads it too.
- If the island is present but the top block is absent (e.g., stripped by an external tool), the editor can regenerate the block on next open/save. If the top block is present but the island is absent, the block becomes stale and should be removed on next save — the island is authoritative.

**Recommended island field addition:** `"agentInstruction": true` (boolean, default absent/false). The instruction text is already in `"body"`. No new fields needed; the flag alone is sufficient.

---

## 6. Recommendation

**Use Option A — the delimited HTML comment block.**

Rationale:
1. **Discoverability without convention knowledge.** Any agent reading the file from the top encounters the sentinel string `HYPRESENT AGENT INSTRUCTIONS` in the first N bytes without needing to know about `text/llms.txt` or any external spec.
2. **No MIME type dependency.** The `text/llms.txt` convention (Option B) is an informal web-serving pattern; coding agents editing local files do not yet implement type-string scanning of local HTML.
3. **Spec-legal and quirks-safe.** An HTML comment in `<head>` is inert in all browsers; no rendering or parsing side effects.
4. **Round-trip safe.** The sentinel strings are stable across HTML serializers that normalize whitespace and element order within `<head>`. A pre-DOCTYPE placement would be more vulnerable to normalization.
5. **Simpler implementation.** The serializer only needs string interpolation, not JSON serialization. The only escaping constraint is `-->` in instruction text, which is easy to detect.
6. **Human readable.** Diffs, PR reviews, and manual inspection all work without tooling.

The one-sentence preamble (line 2 of the block) satisfies requirement 5 directly:

```
This block is auto-generated from agent-tagged review comments in this file. Each entry describes a change an AI coding agent should make to the element identified by its anchor.
```

---

## Sources

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1–10 | Threshold: TS ≥ 6

[1] /llms.txt — A proposal to provide information to help LLMs use a website — https://www.answer.ai/posts/2024-09-03-llmstxt.html — 2026-06-03 — 2024-09-03 — TS:8.7 (AT:9 TR:9 TM:8)

[2] A proposal for inline LLM instructions in HTML based on llms.txt — https://vercel.com/blog/a-proposal-for-inline-llm-instructions-in-html — 2026-06-03 — 2025-08-21 — TS:9.0 (AT:9 TR:9 TM:9)

[3] Vercel Proposed a Deeper Integration of LLMs in HTML via Script — https://dev.to/fedtti/vercel-proposed-a-deeper-integration-of-llms-in-html-via-script-cfg — 2026-06-03 — 2025-08-22 — TS:7.0 (AT:7 TR:7 TM:7)

[4] How to Build Your AGENTS.md (2026) — https://www.augmentcode.com/guides/how-to-build-agents-md — 2026-06-03 — 2026-01 — TS:7.7 (AT:8 TR:7 TM:8)

[5] Some notes on AI Agent Rule / Instruction / Context files — https://gist.github.com/0xdevalias/f40bc5a6f84c4c5ad862e314894b2fa6 — 2026-06-03 — 2025 — TS:7.3 (AT:7 TR:8 TM:7)

[6] Idiosyncrasies of the HTML parser — https://htmlparser.info/parser/ — 2026-06-03 — 2024 — TS:8.7 (AT:9 TR:9 TM:8)

[7] Understanding quirks and standards modes — https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Quirks_mode_and_standards_mode — 2026-06-03 — 2025 — TS:9.3 (AT:10 TR:9 TM:9)

[8] Lobsters discussion: proposal for inline LLM instructions in HTML — https://lobste.rs/s/5mlh66/proposal_for_inline_llm_instructions — 2026-06-03 — 2025-08 — TS:6.7 (AT:7 TR:7 TM:6)

[9] AI Agent Rule Files Chaos — https://www.everydev.ai/p/blog-ai-coding-agent-rules-files-fragmentation-formats-and-the-push-to-standardize — 2026-06-03 — 2025 — TS:7.0 (AT:7 TR:7 TM:7)

---

## Sources Discarded

No sources discarded — all sources met TS ≥ 6 threshold.
