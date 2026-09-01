---
id: email-voice
description: Draft a plain-text email in the workspace voice — invoked directly by any agent, not only from inside a document workflow. Resolve the brand-pack voice, draft, then compact.
inputs: recipient context (who, relationship stage, what they already know); the ask (what this email must make happen); the language; brand-pack `voice.md` (required) and optional additive `voice-email.md`
outcome: the caller holds a plain-text email body the recipient can read once, top to bottom, and act on — never a markdown document, never an invented voice
outputs: the plain-text email body returned to the caller (not a named file)
---

# email-voice

A standalone skill. Any agent drafting an email invokes it directly; it is not reachable only from inside a document workflow. There is no host workflow.

## Hard output rule

The output MUST be a plain-text email body suitable for ordinary mail clients (Gmail, Outlook). It MUST NEVER contain markdown tables, markdown bold, or headers-as-markup (`##`). Use colon-labels (`Parameters:`), numbered lists, and bullets. The recipient reads it in a mail client, not a renderer.

## Brand-pack resolution — no search, no discovery

`voice.md` and the optional `voice-email.md` resolve by reading the fixed path `.rbtv/config/office/`. Resolution is per-file, not per-pack:

1. If this run carries a project slug, check `.rbtv/config/office/projects/<project-slug>/<file>` first. If that file exists, it shadows the workspace default.
2. If absent, fall back to `.rbtv/config/office/<file>`.
3. No project slug in the run → workspace pack only (`.rbtv/config/office/<file>`). NEVER consult `projects/`.

This is a fixed-path read. NEVER search. NEVER discover.

`voice.md` is required. `voice-email.md` is optional and additive: when present, apply it on top of `voice.md` for email-specific divergences; when absent, `voice.md` alone governs.

## Guided setup — missing `voice.md`

**Ruling:** interactive prompt in the current sitting, never a scaffolding command.

**Why this shape.** `voice.md` is free-form Markdown whose only reader is an LLM drafting prose — a command with flags cannot fill it. The occupant is already in a sitting about to draft, so in-band collection is the cheapest path. A scaffolding command would be a new artifact this module does not ship. Sister capabilities (`deck-production`, `converter`) that meet a missing pack file follow this same shape for the file they require; this section is the one home of that experience.

**Trigger.** Resolved `voice.md` is absent — neither the project override (when a slug is in the run) nor `.rbtv/config/office/voice.md` exists. A present file, even a thin one, is not this trigger. Missing `voice-email.md` is not this trigger.

**What the user is shown.**

```
email-voice needs a brand-pack voice file and none was found.

Looked at:
- .rbtv/config/office/projects/<project-slug>/voice.md  (only if a project slug is in this run)
- .rbtv/config/office/voice.md

Without voice.md this capability will not invent a voice and will not draft.

Set up a workspace voice now? (yes / no)
```

**What is asked** — if yes, ONE message, these six questions, matching the ruled `voice.md` sections:

1. Mission — what is this voice FOR, one paragraph.
2. Core directives — 3–7 non-negotiable rules.
3. Sentence-level preferences — length, person, punctuation habits.
4. Anti-patterns — phrases to avoid, and what to write instead.
5. Examples — one or two short before/after passages.
6. Revision checklist — checks a piece must pass to count as in voice.

Mission and core directives are the minimum. If those two are refused, treat as decline. Thin answers to 3–6 are written as given; do not pad.

**What is written, where.** Write `.rbtv/config/office/voice.md` — always the workspace default, never a project override. Guided setup fires only when resolution found nothing; a workspace file is then inherited by every project. Project overrides are a later explicit act. Format: free-form Markdown, six numbered sections (mission, core directives, sentence-level preferences, anti-pattern table, examples, revision checklist). Do not write `voice-email.md`.

**Decline path.** User says no, walks away, or the sitting cannot reach a human: STOP. Do not draft. Do not invent a voice. Do not write a stub or placeholder file. Tell the caller the email was not drafted because `voice.md` is missing.

## Language

Language is an input. If it is not given, ask. NEVER assume Portuguese. When the language is Portuguese (pt-BR), load `references/email-voice-pt-br.md` as an additive overlay AFTER `voice.md` and `voice-email.md`. When the language is not Portuguese, do not load it. That overlay is not the default and is not this capability.

## Procedure

1. Resolve `voice.md` (and `voice-email.md` if present) per Brand-pack resolution. If `voice.md` is absent, run Guided setup. If that ends in decline, stop.
2. Read the resolved voice file(s).
3. If the language is Portuguese, load the pt-BR overlay. Otherwise skip it.
4. Draft the email against Stance, Vocabulary, Structure, Commitment discipline below, plus the brand-pack voice, plus the overlay when loaded.
5. Run 2–3 iterative compaction passes (see Compaction). Compaction serves read-through: the recipient reads it once, top to bottom, and acts.
6. Return the plain-text body. Do not wrap it in markdown fences unless the caller asked to inspect it as a quote.

## Stance

- Co-construction over prescription. Frame proposals as joint design. Offer optionality where it exists. "Open to reprioritize, depending on what makes most sense for you" beats "we will deliver X."
- Hedge where authority is not earned. If the relationship has not yet earned assertion, use modal hedges rather than declarations.
- Agency over impersonal voice. "We understood that..." beats "It became clear that..."
- Direct personal address from line one. Open with recipients by name, not a generic greeting.
- Relationship calibration over fixed register. Imperative voice and curt formulations require earned warmth. Default to permissive or conditional forms in first direct contact ("would you be able to share", "let me know if you can"). Move to imperative only after the relationship has warmed. Calibrate per person, not per company. Recipients in the same organization can be at different points on this curve.
- Do NOT restate what the recipient said back to them. Listening goes implicit through scope discipline and the offer to reprioritize. Explicit recap reads as patronizing.
- Do NOT prescribe what the next meeting will produce. "We'll come out of the meeting with X locked" sounds salesy.

## Vocabulary

- Plain language over jargon. Full forms over acronyms when speaking the recipient's domain ("accounts receivable" not "AR" in recipient-facing text).
- Preserve local terms the recipient already uses. Domain-native words (POC, Pix, GAAP) are part of their daily vocabulary — translating them strangers the tone.
- No abbreviations in formal text. "30 minutes" not "30 min".
- Plain verbs over corporate verbs. "Below is..." beats "We hereby submit..."
- Concrete dates beat vague timeframes. "By the 15th" beats "next week".
- Simplify numbers for the reader. "30% of volume" beats "27% (90% × 30%)".
- Parentheses are the default for asides; em-dash sparingly. Em-dash for true breaks, short inline lists, or strong emphasis — not as the default compression tool.

## Structure

- Design for skim. A 20–30 second scan MUST convey the structural picture: greeting, opening frame, section labels, ask. Recipients triage "read now vs read later" by skimming first; "read later" usually becomes "never".
- Plain-text-friendly formatting. Bullets and numbered lists. No tables. No markdown bold.
- Sub-bullets only when they carry substantive information. If a sub-bullet just clarifies, fold it into the parent sentence.
- Cohesion of commitments. Everything the recipient is committing to lives in ONE place.
- Each idea has one home. No cross-section repetition.
- Headers earn their keep. Drop a section label if its content can fit elsewhere without orphaning.
- Use simple labels with colons in plain-text destinations ("Parameters:", "Security:") rather than `## Headers` that will not render.

## Commitment discipline

- Concrete parameters beat hedged ones. Duration, cost, success criterion, exit clause MUST be specific. "Around 6 weeks, starting by [date], operational by [date]" beats "a few weeks soon".
- Soft continuation hooks. "Open conversation about continuity and next waves" beats "we will negotiate the contract."
- Always include exit explicitly. State what happens if the engagement does NOT meet criteria.
- Anticipate the obvious question. If the reader will spot an asymmetry — a security claim that begs "how does access work then?", a recipient missing from CC, an undefined reference — answer it preemptively in one short clause or parenthetical. Imprecise claims and unexplained gaps invite scrutiny; preemption earns trust.

## Negative patterns — cut these

- Self-flagellation in the opening.
- Justifying what you are NOT doing. The offer stands on its own.
- Restating what the recipient said.
- Prescribing the meeting outcome before it happens.
- Empathy signals about decisions already visible in the artifact (the design itself is the proof).
- Repetition across sections.
- Markdown that breaks in plain-text destinations.
- Form without target — rhetorical addresses, CTAs, or labels left in place after the context that justified them is gone. Cut the form rather than redirect it to a wrong target.

## Compaction

Master principle: compaction serves read-through. Every word added raises the chance the reader defers. Include detail necessary for understanding — no more.

After the first draft, run 2–3 iterative compaction passes, each with a distinct focus. New ceremony becomes visible only after prior ceremony is removed.

| Pass | Focus | Cut |
|---|---|---|
| 1 | Structural | Whole sections, sub-bullets that fold to inline prose, listening recaps |
| 2 | Redundancy | Headers that became labels-without-content, empathy comments duplicated by the artifact, cross-section repetition |
| 3 | Ceremony | Self-justifications, CTAs without a clear target, format-defending phrases ("this format works better than...") |

Test after each pass: for every sentence, "if I cut this, do I lose action — or just words?" If "just words", cut it.

Typical result of full iteration: 35–45% word reduction without loss of action or tone.
