# Slack Message Formatting

> Loaded on demand when channel is Slack. Use mrkdwn format ONLY — standard markdown does not render in Slack.

*Rules — apply without exception:*

- *Bold:* `*text*` — NEVER `**text**`
- _Italic:_ `_text_` — single underscore only
- Strikethrough: `~text~`
- Links: `<url|label>`
- Headers: use `*Bold Line*` on its own line — NEVER `##`, `###`, or any `#` prefix
- Code: single backtick for inline `` `code` ``, triple backtick for blocks
- Lists: `- item` or `• item`
- Quotes: `> text`
- Tables: NEVER use `| |` table syntax — use labeled lines instead: `*Label:* value`
- Images: NEVER use `![alt](url)` syntax
- No nested formatting, no HTML, no markdown header hierarchy
