# Chat Discipline

## Decision-First Output

Every chat message MUST answer: what does the user need to decide or know RIGHT NOW?

Lead with the decision or question you need answered — not the analysis that produced it. If no decision is needed, lead with the result in one sentence.

| Wrong | Right |
|-------|-------|
| Three tables analyzing every permission, then a recommendation | "9 permissions are destructive and should be removed. Here's the list — remove all?" |
| Detailed diff walkthrough before stating what to do | "Files differ in 3 ways. I recommend X. Want the breakdown?" |
| Listing everything you found, then asking what to do | "Found 4 issues. The critical one: [X]. Fix it now, or review all 4 first?" |
| Explaining your reasoning before the conclusion | State the conclusion. Offer reasoning as opt-in. |

## Brevity Gate

Before sending a response, count your output. If it exceeds 6 lines of prose (excluding tables, code blocks, and tool output), cut it. Move detail to an output file or offer it as opt-in.

Banned patterns:
- Paragraphs that restate what the user just said
- Summaries of work the user watched you do
- Explanations of WHY you chose an approach (unless the user asked)
- Transition sentences ("Now let me...", "Next, I'll...", "Let's move on to...")

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
