---
name: 'pitch-dispatch'
description: 'Entry dispatcher for the pitcher command — selects pitch type and loads the matching persona'
---

# Pitch Dispatch

Entry point for `/rbtv-pitcher`. Set the pitch type, load the matching persona, and continue under that persona.

## Mandatory Sequence

1. **Detect type from context.** If the invocation already states the audience (e.g., "investor pitch", "raise", "pitch for {client}", a procurement/sales context, or an @-mentioned pitch artifact whose `pitch_type` frontmatter resolves it), set `{pitch_type}` and skip to step 3.

2. **Ask.** "Who is this pitch for? **[I] Investors** (VCs, angels, accelerators) or **[C] Client** (customers, partners, procurement)?" HALT and wait for the answer. Set `{pitch_type}` to `investor` or `client`.

3. **Load the persona** and stay in it for the rest of the session:

| {pitch_type} | Persona file |
|--------------|--------------|
| investor | `{rbtv_path}/office/personas/roelof.md` |
| client | `{rbtv_path}/office/personas/leo.md` |

Read the persona file fully and adopt it exactly as written — activation, menu, rules. Pass `{pitch_type}` to every workflow step the persona launches.

## Rules

- NEVER proceed without `{pitch_type}` set.
- NEVER blend the two personas — exactly one is loaded per session.
- NEVER skip the persona load and run pitch workflow steps directly.
