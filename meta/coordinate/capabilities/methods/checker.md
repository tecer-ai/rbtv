# Checker

A checker is one sub-agent that judges one result against its done contract and returns pass or fail with findings. It exists because a report arrives equally confident whether it is right or wrong, and the coordinator cannot tell the two apart by reading harder.

Where a [panel](panel.md) gathers several views to settle a judgment, a checker gives a binary verdict on one result. Where a direct check (run the command, open the file, try it in a throwaway folder) settles a claim, no checker is needed: the direct check is cheaper and more certain.

## When a checker pays

- A claim your decision rests on cannot be settled by one cheap command: a sub-agent reports "every caller was updated", "the tests pass on both platforms", "the page says X", and confirming it means reading what the sub-agent read.
- The cost of being wrong is high: the result will be committed, published, relayed to the user as fact, or fed to the next wave as its input.
- The result is a judgment of its own (a review, a diagnosis, a synthesis) whose evidence you would otherwise have to re-read to trust.

When none of these holds, do not check. A checker on a trivial result (a count, a file's existence, a one-line edit) spends an agent to confirm what one command confirms. A checker on a result nobody will act on spends it for nothing.

## What the checker receives

- The result: the sub-agent's output page and the files it names, by path.
- The done contract of the task that produced it, verbatim.
- The main documents the contract refers to, by path, so the checker can verify a claim against its source.
- A scope: what it may read (the result, the contract, the named documents, and the commands the contract names), and nothing it may change.

Not the producer's reasoning, transcript or log. A checker that reads how the producer arrived at a claim tends to follow the same path to the same conclusion; it must reach the claim from the evidence alone.

## Choice of model

Route the checker as a bounded text job and launch it on a different model from the producer, from a different provider when the catalog offers one (`cast models list --catalog`). The point is independence: two instances of one model share blind spots, and an agreement between them is weaker evidence than it looks. When only one model fits, a fresh instance of it is still better than no check; say so in your report.

A checker that must run commands (tests, a tool, a reproduction) needs the harness's command access; route it with `--access open` when it must discover files.

## The verdict

The output format is fixed, because a checker's page is read without interpretation:

```markdown
Verdict: pass | fail
Checked: <each condition of the done contract, with what was observed and where>
Findings: <one row per miss: location, what is wrong, the evidence>
UNVERIFIED: <conditions the checker could not observe, and why>
```

A fail names what to send back to the producer and whether the next action is a corrected re-run or a stop. A pass with a non-empty UNVERIFIED line is a partial pass: the coordinator decides whether the unverified conditions matter, and that decision is its own, not the checker's.

## What a checker is not

- Not a reviewer of quality or style; it checks the contract's conditions and nothing beyond them. A finding outside the contract goes in a separate line, marked as such, and does not turn a pass into a fail.
- Not a second producer; it does not fix what it finds.
- Not a panel; when the result is a judgment that several views should weigh, convene a panel instead.
