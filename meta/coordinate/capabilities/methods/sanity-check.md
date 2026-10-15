# Sanity check

A sanity check verifies what the session just produced or concluded, before the user acts on it, with sub-agents that reach the claims from the sources and not from the session's answer. Where a [checker](checker.md) judges a sub-agent's result against its done contract and a [panel](panel.md) weighs a judgment through several lenses, a sanity check takes the session's own output apart into claims and has each claim re-derived, refuted or traced by an agent that did not produce it.

Two facts govern every run. Independence comes from different prompts: a second model is a bonus, never a substitute, because two agents given the same prompt and the session's conclusion return the same confirmation twice. And whenever angle A is in the run, at least one agent is blind: it receives the question and the sources, never the session's answer.

Inputs: the target (what the user is about to rely on), the level when the user names one, and the sources the target rests on. The user's words "sanity check", "double check with sub agents" or "check this independently" select this page; a review of a code diff and a render check of a page or document are not sanity checks.

## 1. Build the claim sheet

The target is what the session produced in its last turn, all of it when that turn produced several artifacts, unless the user named another. When the session produced no artifact, number, draft or conclusion, ask the user one question naming the two most likely targets, and stop.

Write the claim sheet: a numbered list of every checkable claim in the target. Each claim has a label that names it without its value ("total of invoice 412", "recipient list", "status of the September payment"), its value, and the exact source: an absolute path, a message id, a thread permalink or a command. Checkable claims are amounts, dates, counts, names, recipients, statuses ("paid", "sent", "signed", "active") and cause statements ("because X"). A claim with no source is listed with source `none`: that is already a finding.

A status claim ("sent", "paid", "signed", "exists", "did not go out", "never answered") gets a PLACES list instead of one source: every place the evidence could live, whether or not the session already opened it. Walk these four and name the exact one for this claim, or write `n/a`: mail (which account, which query), the chat workspace (which channel and thread), the shared drive folder of that client, vendor or matter (its signed-documents folder and any e-signature summary included), the local project folder. Evidence that sits with another person (their mailbox, their e-signature account) is `out of reach: <whose>`.

At level low only, keep the five claims with the highest stakes, ranked money, recipients, dates and deadlines, statuses, everything else. Medium and high check the whole sheet.

## 2. Pick the angles

| Angle | The agent receives | Its job |
|---|---|---|
| A. Blind re-derive | The question, the claim labels and the sources; never the values or the session's conclusion | Produce its own value for each label from the sources: recompute the numbers, or reach its own recommendation |
| B. Adversarial refuter | Every claim on the sheet and the sources they cite | Assume at least one claim is wrong and find it; trace every claim to a file and line, or to the message that states it |
| C. History sweep | Only the status and "already done" claims, with the accounts, workspaces and folders to search | Find evidence this was already done, sent, paid, asked or decided: mail, chat (thread and channel), handoffs, logs |
| D. Recipient read | The draft, its intended recipients, one line on who each is; nothing else | Read as the recipient: internal reasoning leaking, a recipient who should not see this, unexplained terms, claims the recipient can contradict, tone |
| E. Live state | What should be running and its status command, or the project folder when the command is unknown (the agent finds it in that folder's instruction file) | Run the read-only status or dry-run command and report what is loaded, active and last run; never a real booking, send or write |
| F. Docs consistency | Only the claims about docs, rules or skills, the change, and the files that describe it | Find every place that still states the old behavior, or a copy that was not updated |

Scope every agent: it receives only the claims its row names and only the sources those claims cite, each as an exact file, message or command; never a whole folder, mailbox or channel when the claim cites one item in it. The one exception is a status claim: its agent searches every place on the PLACES list, each as a named folder or a stated query.

Use the first row that matches, top to bottom:

| Target | Pair | Third agent |
|---|---|---|
| A message or mail about to go out | B + D | A when it carries amounts or dates, otherwise C |
| Amounts, a reconciliation, a table of numbers | A + B | C |
| "Did we already do this?" | C + B | A |
| "Is it working?" (a bot, a job, a script) | E + B | F |
| Docs, rules or skills changed | F + B | E |
| A plan, a decision, or anything else | A + B | C |

| Level | Agents | Picked when the user names no level |
|---|---|---|
| low | 1: the first angle of the pair, on the Mid tier | The target is one fact or one number, stays inside the session, and carries no money to pay or invoice, no legal filing and no personal data of a third party |
| medium | 2: the pair | Every case that is neither low nor high |
| high | 3: the pair and the third agent | The output leaves the session after the check (send, post, upload, pay, file), or carries money to pay or invoice, a legal filing or personal data of a third party, or the user says "everything", "final", "300%" |

A level the user names runs exactly as named, whatever the target and whatever follows the check; never raise or lower it. "4" or "two and two" runs each angle of the pair twice, once per tier, the second copy with the claims in reverse order. A count, angles or models the user names are used exactly.

## 3. Route the tiers

The tiers are the model levels of `cast route`: Strong is `--class broad` (level L1), Mid is `--class bounded` (level L2), each with `--access bounded --type text` and `--optimize price` unless the user asks for quality. In a one-agent run the agent runs on Mid. In a two- or three-agent run, A and B run on Strong and C, D, E, F on Mid. In a four-agent run every angle runs once on each tier. Angle E, and any angle that must read a folder it was not handed, routes `--access open`. A model the user names overrides the verdict for that agent.

## 4. Dispatch

Launch the agents through `cast` as the coordinate skill's rules say, all in one turn so they run in parallel. Every task is self-contained and states: the question in one sentence and the angle's job from step 2; every source as an absolute path, message id or permalink; "Read-only: do not edit, move, send, post, upload or schedule anything"; for each source the agent will touch through a connector (mail, calendar, drive, chat, messaging), the installed tool that wraps it, by name, with "run it with `-h` first"; "every exact figure comes from a computation you ran, shown with its output"; and the return format. Angle A returns `label | value found | evidence`; every other angle returns `# | value found | verdict | evidence (path:line, id or command output)` with the verdict one of `CONFIRMED`, `WRONG`, `UNVERIFIABLE`.

Before sending, reread the angle A task and delete any claim value or conclusion that slipped in.

## 5. Reconcile

1. Diff angle A's values against the claim sheet; a mismatch is a `WRONG` candidate.
2. For every `WRONG`, every mismatch and every claim on which two agents disagree, open the source yourself or run the computation, and settle it. Never settle by majority.
3. `UNVERIFIABLE` stays flagged; never upgrade it to confirmed. A status claim is `UNVERIFIABLE` only after every reachable place on its PLACES list was searched; a place an agent skipped, the session searches before reporting.
4. Fix each confirmed error in the target and say what changed. A fix to a message draft goes through the user's voice or writing skill when one is installed.

## 6. Report

First line: `Sanity check: N claims - X confirmed, Y wrong, Z unverifiable.` Y counts every confirmed error, fixed or not. Then a table of only the wrong and unverifiable claims (claim, was, is, evidence, fixed yes or no); every unverifiable row says where it was searched and where it was not, with `n/a` or `out of reach: <whose>`. Then one line naming the level, whether the user named it or it was picked, the angles and tiers used, and at level low how many claims were left off the sheet. Confirmed claims are not listed.

An outward action the user made conditional on the check ("if ok then send") runs only when Y and Z are both zero. Otherwise hold the action, show the user the corrected target, and wait for their word.
