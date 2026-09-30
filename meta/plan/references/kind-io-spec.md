---
description: Author the input, outcome, and output section of a reusable prompt or capability
tags: [planning]
---

# `<io-spec>` — input and result

Describe the input shape, the observable outcome, and each output a consumer receives. Keep paths and owner-specific values as runtime inputs. A task file has its own aim, scope, and done contract and does not carry this section.

A result is useful when its consumer knows how to tell a completed output from an empty or partial one. State what happens when no result can be produced.
