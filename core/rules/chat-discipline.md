| Violation Type | Example (BAD) | Correct (GOOD) |
|----------------|---------------|----------------|
| Vague language | "Consider checking the file descriptions." | "Read each file's description header." |
| Verbose explanation | "This step is important because it ensures that the agent has all the necessary context to make informed decisions about the implementation." | "This step provides required context." |

# Chat Discipline

## Decision-First Output

Every chat message MUST answer: what does the user need to decide or know RIGHT NOW?

Lead with the decision or question you need answered — not the analysis that produced it. If no decision is needed, lead with the result in one sentence.

## Iterative Decisions

When the work requires 3+ decisions from the user across multiple turns, pace them — do NOT dump all decisions in one turn.

Pattern:

1. **First pass — sweep.** Present the full map of decisions the agent expects to make with the user. Numbered list, one line each, no detail. Goal: orient the user so they see the shape of what's coming.
2. **Subsequent passes — 2 at a time.** Ask 2 questions per turn. Wait for answers, then move to the next 2. Continue until the map is exhausted.

Exception — coupled decisions: when 2+ decisions must be answered in the same turn because their framing depends on each other, bundle them AND state the coupling explicitly ("Q3 and Q4 are coupled — Q4's options change based on Q3's answer"). Default is uncoupled and 2 at a time.

The user reads "many open questions" as overwhelm, not progress. Pacing turns ambiguity into a series of small commits.

## New Value Only

NEVER restate content from approved documents, completed steps, or previously discussed material. Chat output MUST contain ONLY:

- Decisions that need user input
- New analysis, insights, or criticisms
- Deviations from or challenges to existing content
- Net-new data not already in referenced documents

Reference approved content by path and section — never copy it into chat.

## Chunked Presentation

When presenting 7+ items, lead with a summary count and the top 1-2 items that need attention. Ask before expanding. Do NOT present all items upfront.

## Chat vs File Separation

Full detail belongs in output files. Chat is for questions, decisions, and summaries.

When a workflow step produces detailed output, write to the output file and present in chat ONLY: one-line summary, items needing decision, and tensions worth discussing.

If output genuinely requires >6 prose lines, move detail to an output file. Reference by path; do NOT paste detail into chat
