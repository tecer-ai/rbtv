---
name: rbtv-web-search
description: Navigate the web — preview link metadata (OG tags, oEmbed), extract clean content from URLs with Defuddle, and conduct rigorous multi-source research with source evaluation and citation standards. Use when the user provides a URL to read, asks to research a topic, or any task requires web information.
---

# Web Search

Single skill for all web interaction. Three modes based on intent.

## Mode Selection

| Signal | Mode |
|--------|------|
| Need only title/description of a URL (link identification, reading list, categorization) | **Preview** |
| User provides a URL to read/analyze full content | **Extract** |
| User asks to research a topic, compare options, gather data | **Research** |
| Task requires a quick fact check | **Extract** if URL known, **Research** if not |

---

## Preview Mode

Lightweight metadata extraction — just title, description, and domain. Use when you need to identify what a link is about, NOT when you need its full content.

### Fallback Chain

Try each step in order. Stop at the first success.

| Step | Method | Command / Tool |
|------|--------|----------------|
| 1 | Defuddle metadata | `defuddle parse <url> -p title` then `-p description` |
| 2 | oEmbed API (social platforms) | `WebFetch` → `https://publish.twitter.com/oembed?url=<url>` (Twitter/X), `https://www.youtube.com/oembed?url=<url>&format=json` (YouTube), `https://noembed.com/embed?url=<url>` (generic) |
| 3 | WebFetch with meta-scoped prompt | `WebFetch` with prompt: "Extract only the page title and meta description from the HTML head. Return title and description, nothing else." |
| 4 | Ask user | Report domain and what was recovered. Request title/description manually. |

### When NOT to use Preview

- You need the article body, full text, or detailed content → use **Extract**
- You need to verify claims or gather data → use **Research**

---

## Extract Mode

Use Defuddle CLI to pull clean readable content from web pages. Removes navigation, ads, and clutter — saves tokens vs raw WebFetch.

If not installed: `npm install -g defuddle`

### Usage

Always use `--md` for markdown output:

```bash
defuddle parse <url> --md
```

Save to file:

```bash
defuddle parse <url> --md -o content.md
```

Extract specific metadata:

```bash
defuddle parse <url> -p title
defuddle parse <url> -p description
defuddle parse <url> -p domain
```

### Output Formats

| Flag | Format |
|------|--------|
| `--md` | Markdown (default choice) |
| `--json` | JSON with both HTML and markdown |
| (none) | HTML |
| `-p <name>` | Specific metadata property |

### Fallback

If defuddle returns empty or errors, fall back to `WebFetch`. This happens with SPAs, paywalled content, or pages requiring JavaScript rendering.

---

## Research Mode

Rigorous multi-source research with data integrity, source evaluation, and citation standards. Every claim verified, every source scored, every citation formatted.

### Critical Rules

- **NEVER** present information without verified sources — `WebSearch` is REQUIRED for factual claims.
- **NEVER** fabricate, estimate, or extrapolate data — state "DATA NOT FOUND IN SOURCES" if unavailable.
- Sources with TS < 6 are **FORBIDDEN**.
- Every research response **MUST** include: legend, scored citations, and Sources Discarded section.

### Procedure

#### 1. Identify Research Topic

- Structured input ("Research Topic: X", "Context: Y") → use directly.
- Otherwise → user's most recent question is the topic. Context implied by conversation.

#### 2. Load Standards

Read `{rbtv_path}/skills/web-search/web-research-standards.md`. Internalize all rules: data integrity, quantification, source evaluation, citation format, tone.

#### 3. Conduct Research

**3a. Execute Web Searches**
- Use `WebSearch` to find information on the topic.
- Gather multiple sources — critical claims require 2+ independent sources.
- Use `defuddle` (Extract Mode) to read content from found URLs.

**3b. Evaluate Each Source**
- Score: Authority (AT), Trustability (TR), Topic Match (TM). Scale 1–10.
- Total Score (TS) = average of AT, TR, TM. Discard sources with TS < 6.
- Apply marketing language penalty to TR where applicable (see standards file).

**3c. Group Domain Sources**
- Multiple links from same domain count as ONE source unless they meet exception criteria (see standards file).
- Nest sub-sources under parent; each nested entry gets its own evaluation.

#### 4. Apply Data Standards

**4a. Data Integrity**
- Every number, statistic, or claim must cite its source inline (e.g., "[Source 12]").
- State exact years/dates — never "recently" without defining the period.

**4b. Quantification**
- Explicit units: $ billions for market sizes, % for shares, % CAGR for growth rates.
- Full rules in standards file.

**4c. Fact vs Analysis**

| Type | Rule |
|------|------|
| **Fact** | Directly from verified source — cite with URL |
| **Analysis** | Your interpretation — state explicitly as analysis |
| **Speculation** | Hypothesis — flag with confidence level |

#### 5. Format Output

**Legend (mandatory — every research response):**

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

**Citation format (mandatory):**

```
[n] Title — URL — Research Date (YYYY-MM-DD) — Source Date — TS:x (AT:x TR:x TM:x)
```

**Sources Discarded section (mandatory):**

List sources with TS < 6 with reason. If none discarded, state: "No sources discarded — all sources met TS >= 6 threshold."

### When to Stop

- No sources found with TS >= 6 → report and request guidance from user.
- Critical claims cannot be verified with 2+ sources → flag explicitly before proceeding.
