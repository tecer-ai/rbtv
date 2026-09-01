---
description: "Read at the moment an HTML page is being produced or reviewed — the five content-quality rules every page-type and both production models must meet."
tags: [document]
---

# html-quality — cross-type content quality

Normative. Binds every page-type and both production models: agent-authored HTML, and schema + deterministic builder. A page that fails any rule below has failed, regardless of look.

These rules are applied against the page. They are not a production procedure.

## 1. No jargon

Written for a reader who does not know the project. Never a plan-internal label, story id, verdict tag, bare acronym, or a term whose meaning lives in another document, without a plain-language definition at first use. Default to not using the token — state the idea.

**Failure test:** if deleting the explanation leaves the reader guessing, the page has failed.

## 2. Self-explanatory

The page stands alone. A reader with zero project context can follow it.

**Failure test:** if following the page requires another document, a prior briefing, or unstated project knowledge, the page has failed.

## 3. Standardized terminology

One name, one meaning, matching the project's settled terms when a term is genuinely needed (and defined on first use).

**Failure test:** two names for one thing, or one name for two meanings, is a fail.

## 4. Information fidelity beats visual polish

The HTML carries the source's real structure, boundaries, and dependencies, verifiable against the source. Design never replaces, obscures, or distorts it. The look serves the information; it never substitutes for it.

**Failure test:** an attractive approximation that drops, merges, or invents structure, boundaries, or dependencies has failed — even if it looks better.

## 5. The glossary bar

Every technical term, acronym, or piece of jargon gets a plain one-sentence definition. A definition that itself uses jargon is a defect. Undefined jargon is a FAIL.

**Failure test:** any leftover undefined token, or a definition the reader still cannot parse without knowing jargon, is a fail.

## How definitions surface

Only the definition requirement is cross-type. The surfacing mechanism is not.

Learning (schema + deterministic builder) surfaces definitions on hover/focus via builder CSS.

Review and Presentation (agent-authored HTML) define in prose or a static definition list, never tooltips.
