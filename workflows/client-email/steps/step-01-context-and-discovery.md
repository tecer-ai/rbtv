# Step 01 — Context and Discovery

Gather context AND user intent before drafting. The drill forces articulation — that is the value, not the information. Skip it and the draft serves the agent's assumed intent, not the user's actual one.

The discovery runs in two waves around a focused read of the recipient's files.

## 1. Anchor

Ask the user where the recipient's files live. Typical layout: profile, status, fit, prior correspondence, relevant meetings. Skip the ask only if the user has already pointed you to the files or attached relevant content.

## 2. Pre-read questions

Ask ONE AT A TIME. Do NOT batch. Skip a question only if the user explicitly answered it in the prompt.

| Type | Question | Run rule |
|---|---|---|
| Traction (locked phrasing) | **pt-BR (verbatim):** "O que tá te deixando inseguro nesse email?" — **EN:** "What's making you stuck on this email?" | ALWAYS — even with rich pre-loaded context. Forces articulation. |
| Conditional (flexible phrasing) | Goal of the email. Examples: "Qual o objetivo desse email — avançar, destravar, decidir, informar?" / "What outcome do you want from this email?" | Skip if the user explicitly stated the goal in the prompt. |

## 3. Focused read

Read the anchor files informed by the user's pre-read answers. Look for the specific tensions or gaps the user named. Do NOT do a generic read.

## 4. Post-read questions

Ask ONE AT A TIME. Order matters — state delta first, then conditional.

| Type | Question | Run rule |
|---|---|---|
| Traction (locked phrasing) | **pt-BR (verbatim):** "Tem algo na relação atual que os arquivos ainda não refletem?" — **EN:** "Is there anything in the relationship state the files don't yet reflect?" | ALWAYS — even when files look current. Catches signed contracts not logged, recent verbal commits, deal moves, surfaced tensions. |
| Conditional (flexible phrasing) | Recipient strategy — primary and CC. Examples: "Quem é o destinatário primário e quem entra em cópia?" / "Who's primary and who's in CC?" | Skip if obvious from the prior correspondence (single-recipient thread) or already stated. |
| Conditional (flexible phrasing) | Gap analysis trigger. Examples: "Rodo gap analysis dos itens não respondidos antes de propor estrutura?" / "Should I run a gap analysis of what's open before proposing structure?" | Run only if the email is a response to a recipient reply OR a follow-up after recipient silence on a prior request OR a follow-up after our own silence on a prior commitment. Skip on fresh first-contact emails. |

## 5. Restate and confirm

After all post-read questions, restate the picture in 3-4 lines: goal, stuck point, recipient strategy, state delta, and (if applicable) gap analysis trigger. Wait for the user to confirm or redirect. Do NOT proceed to step-03 until confirmed.

Format example:
> Resumindo: objetivo é X, você tá stuck em Y, primário é Z (CC: W), [estado real diferente do arquivo: ...]. Faz sentido?

Skip restate only when the user explicitly said "move on" / "you have enough" mid-discovery.

## 6. Capture deltas

If the user surfaced state-delta context (post-read Traction question), note it for post-send propagation. After step-04 delivers the accepted draft, propose updates to the entity's files (`profile.md`, `status.md`, `fit.md`, `solution.md` as applicable) per the entity's collection CLAUDE.md propagation gate.

## Exit conditions

End the drill when ANY of:

- Restate confirmed (default exit).
- User says "you have enough" / "move on" / equivalent.
- Each new question would yield only marginal information (self-detect diminishing returns).
