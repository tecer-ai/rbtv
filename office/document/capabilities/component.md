# document

The `office` skill (`skills/office.md`) routes ordinary office requests to this component and the sibling storytelling and design skills. Meeting summarization stays in its own component.

`document/` owns every finished deliverable this module ships. It hosts the HTML standards
library every page-type builds against, the `html-review` and `visual-check`-consuming production
capabilities (deck production, conversion, email voice), and the two cataloged workflows —
`meeting-prep` and `presentation` — that chain `storytelling/`'s locked narrative and `design/`'s
visual system into a delivered artifact. Meeting summarization itself is owned by
`transcript-summarizer-build`'s `office/meeting-summarizer`; this component points at it and never
builds its own.

## Entry points

| Part | What it is |
|---|---|
| `skills/html-standards.md` | The HTML standards library router — one file per subject, reached through this router, never separately exposed. |
| `skills/html-review.md` | Reviews HTML output against the standards library. |
| `skills/deck-production.md` | Produces the HTML deck + matching PDF (1280×720, matching `@page` print settings). |
| `skills/converter.md` | Document conversion (e.g. markdown → DOCX). First-party CLI at `capabilities/converter/tool/md-to-docx.py`. |
| `skills/email-voice.md` | Applies the brand pack's email voice variant. Invocable directly, not only inside document workflows. |
| `skills/posh.md` | Deterministic document presentation: machine-fills an HTML template from a structured source (v1: a /plan seat-plan folder as a status dashboard). First-party CLI at `capabilities/posh/tool/posh.py`. |
| `skills/meeting-prep.md` | Chains storytelling + document capabilities into a meeting-prep cheat sheet. |
| `skills/presentation.md` | Chains storytelling + design + document capabilities into a finished deck + PDF. Interactive execution mode (owner gates). |

Summaries are referenced, not owned — see `office/meeting-summarizer`. `ai-anti-patterns` is
`storytelling/`'s row, not this component's.
