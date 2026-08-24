# bridges/chat — module inventory (append-only)

## reply-grammar

`reply-grammar.js` — parse an owner Slack reply into a canonical first-token
outcome plus comments, or a parse-failure that names which verbatim §4.5 NACK
applies. Law: `spec-owner-io` §4. Pure function. Probe:
`probes/probe-chat-reply-grammar.js`.
