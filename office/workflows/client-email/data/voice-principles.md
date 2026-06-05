# Client Email — Voice Principles

Loaded by `../workflow.md` Step 4. Language-agnostic. Portuguese (pt-BR) tonal realization lives in `voice-pt-br.md`.

## Master Principle: Compaction Serves Read-Through

Every word added raises the chance the reader defers reading. The goal is for the email to be read NOW, not LATER. Include detail necessary for understanding — but no more than necessary. Every other principle below is an instrument serving this one.

## Stance

- **Co-construction over prescription.** Frame proposals as joint design, not delivery. Offer optionality where it exists. "Open to reprioritize, depending on what makes most sense for you" beats "we will deliver X."
- **Hedge where authority is not earned.** If the relationship has not yet earned assertion, use modal hedges ("we imagine you'll want", "we could explore") rather than declarations.
- **Agency over impersonal voice.** "We understood that..." beats "It became clear that..." — same length, more ownership.
- **Direct personal address from line one.** Open with recipients by name, not generic greeting.
- **Relationship calibration over fixed register.** Imperative voice and curt formulations require earned warmth. Default to permissive or conditional forms in first direct contact with a recipient ("would you be able to share", "let me know if you can"). Move to imperative ("share", "let me know") only after the relationship has warmed. Recipients within the same organization can be at different points on this curve — calibrate per person, not per company. Language-specific realization lives in `voice-pt-br.md` Calibração de Relação.
- **Do NOT restate what the recipient said back to them.** The listening signal goes implicit through scope discipline and offer to reprioritize. Explicit recap reads as patronizing.
- **Do NOT prescribe what the next meeting will produce.** "We'll come out of the meeting with X locked" sounds salesy. Let the meeting be what it has to be.

## Vocabulary

- **Plain language over jargon.** Use full forms over acronyms when speaking the recipient's domain ("accounts receivable" not "AR" in client-facing text).
- **Preserve local terms the recipient already uses.** Domain-native words (e.g., POC, Pix, ACT, GAAP) are part of the recipient's daily vocabulary — translating them strangers the tone.
- **No abbreviations in formal text.** "30 minutes" not "30 min".
- **Plain verbs over corporate verbs.** "Below is..." beats "We hereby submit..."
- **Concrete dates beat vague timeframes.** "By the 15th" beats "next week".
- **Simplify numbers for the reader.** "30% of volume" is easier than "27% (90% × 30%)" — the reader resolves the math if they care.
- **Parentheses are the default for asides; em-dash sparingly.** Em-dash for true breaks, short inline lists, or strong emphasis — not as default compression tool.

## Structure

- **Design for skim.** A 20-30 second scan should convey the structural picture: greeting, opening frame, section labels, ask. Recipients triage "read now vs read later" by skimming first; "read later" usually becomes "never". Section labels with colons, numbered lists, and consistent visual hierarchy let the reader get the picture without reading prose. The other Structure rules below serve this goal.
- **Plain-text-friendly formatting.** Bullets and numbered lists, no tables, no markdown bold (the email is sent in Gmail/Outlook, not rendered as markdown).
- **Sub-bullets only when they carry substantive information.** If a sub-bullet just clarifies, fold it into the parent sentence.
- **Cohesion of commitments.** Everything the recipient is committing to lives in ONE place — don't split "what they invest" across the document.
- **Each idea has one home.** No cross-section repetition. If security has its own section, don't also list "security questions" in the closing checklist.
- **Headers earn their keep.** Drop a section label if its content can fit elsewhere without orphaning. Structural labels without enough content under them inflate.
- **Use simple labels with colons in plain-text destinations** ("Parameters:", "Security:") rather than `## Headers` that won't render.

## Commitment Discipline

- **Concrete parameters beat hedged ones.** Duration, cost, success criterion, exit clause must be specific. "Around 6 weeks, starting by [date], operational by [date]" beats "a few weeks soon".
- **Soft continuation hooks.** "Open conversation about continuity and next waves" beats "we will negotiate the contract."
- **Always include exit explicitly.** State what happens if the engagement does NOT meet criteria. Removes implicit lock-in fear.
- **Anticipate the obvious question.** If the reader will spot an asymmetry — a security claim that begs "how does access work then?", a recipient missing from CC, an undefined reference — answer it preemptively in one short clause or parenthetical. Examples: "without a public endpoint, accessed only via authenticated dashboard"; "(X is not in copy because we did not have their email)". Imprecise claims and unexplained gaps invite scrutiny; preemption earns trust.

## Negative Patterns — Things to Cut

- Self-flagellation in opening ("we realize we wasted your time on the last meeting...").
- Justifying what you are NOT doing ("offering a call rather than a doc, which would be less effective"). The offer stands on its own.
- Restating what the recipient said.
- Prescribing the meeting outcome before it happens.
- Empathy signals about decisions already visible in the artifact ("we heard you say API is unstable, so we propose fallback" — the fallback design itself is the proof).
- Repetition across sections.
- Markdown that breaks in plain-text destinations.
- Form without target — rhetorical addresses, CTAs, or labels left in place after the context that justified them is gone (e.g., "X, here's the summary" kept after X leaves the CC; a section header preserved after its content moves elsewhere). Cut the form rather than redirect it to a wrong target.

## Iterative Compaction Technique

After the first draft, run AT LEAST 2-3 additional passes, each with a distinct focus. The technique is iterative because new ceremony becomes visible only after prior ceremony is removed.

| Pass | Focus | Examples |
|------|-------|----------|
| 1 | Structural cuts | Whole sections, sub-bullets that fold to inline prose, listening recaps |
| 2 | Redundancy cuts | Headers that became labels-without-content, empathy comments duplicated by the artifact, cross-section repetition |
| 3 | Ceremony cuts | Self-justifications, CTAs without a clear target, format-defending phrases ("this format works better than...") |

**Test after each pass:** for every sentence, ask "if I cut this, do I lose action — or just words?" If the answer is "just words", cut it.

Typical result of full iteration: 35-45% word reduction without loss of action or tone.

## Reference

For Portuguese (pt-BR) tonal realization — greetings, closings, pronouns, modal verbs, business conventions, before/after pairs — read `voice-pt-br.md`.
