# Blind CLI usability testing

Use this procedure before source-assisted changes to an existing interface, and again after the changed interface is built. For a new CLI, a proposed-output mock can expose confusion before implementation; a fresh pass must use the actual installed command afterward. The thing being tested is the interface, not a reviewer's skill.

## Prepare the test without briefing the reviewer on the design

The test owner defines realistic user jobs, a runnable command or navigable mock, and an exact safe boundary. Keep the designer, any source-informed verifier, and each cold reviewer distinct. For a new CLI or major redesign, default to two or three fresh reviewers with independently scoped user jobs; prefer different models where available. For a small change, use a focused fresh test of the changed path. A reviewer must not inherit this design discussion or another reviewer's context.

Before allowing commands, inspect what each candidate command can read, reveal, contact, and change. Names such as `--help` and `--dry-run` do not prove they are safe. Bound the data and live network/services in scope. Use synthetic or isolated data, or real reads explicitly authorized for this test; redact sensitive values from retained transcripts. A harmless authorized read needs no elaborate sandbox. Prepare a disposable target. For mutating exercises, also isolate the reviewer's home, configuration, environment variables, and any shared state or command ownership the CLI can affect. If the needed read boundary or write isolation cannot be established, use a safe mock or narrower exercise and label the omitted behavior unverified. A dry-run can establish preview behavior but cannot establish that real writes succeed.

The cold brief contains only:

- How to access the executable or mock and where it may run.
- One or more user job scenarios stated as outcomes, without command names or answer hints.
- Allowed and forbidden side effects, the disposable target, and when to stop.
- A request to record literal invocations, exit status, standard output, standard error, what was inferred, and what remained uncertain.

Do not pass source, README, benchmark, complete command inventory, rubric, expected output, suspected defect, proposed repair, previous reports, or the author's decision record. Do not say “try this command” unless it is only the invocation needed to launch the tool. Do not steer one reviewer toward a failure another found. A false impression from the interface is evidence, even when a source-informed author knows what the CLI meant.

## Reusable cold brief

Fill only the access, scenario, and safety placeholders below. Keep the evaluation criteria in the informed review, outside this brief.

> You are evaluating the tool's usability, not your own performance. Work only from the interface at `[access]`. Do not read its source code, repository documentation, or prior reviews. Your job is `[user outcome]`. You may operate within `[safe target and allowed effects]`; stop before `[forbidden effects]`. Explore as a new user would. Record the commands you actually tried with their exit status, standard output, and standard error. Based only on what the interface showed, explain what you believe the tool is for, which actions and argument values you discovered, what those actions affect, and how a user recovers from a mistake. Separate observations from guesses and say where you remain unsure. Do not look up hidden answers or work around confusion to appear competent.

For a mock, replace “commands” with the literal actions or navigation used and state that it cannot prove execution. Keep the same separation from source and design notes.

## Review transcripts after the blind phase

The informed reviewer reconstructs, from each transcript alone, what a new user could discover: purpose, available commands, argument forms and accepted values, effects and side effects, recovery from failure, and a first-use route. Match claims to literal invocations and output; a report's summary without evidence is not proof. Separate:

- Convergence: independently observed behavior or confusion.
- Unique coverage: one reviewer reached a path the others did not; do not call this a disagreement.
- Real contradiction: the same conditions produced incompatible observations, with both transcripts retained.
- Uncertainty: unrun commands, mocks, previews, or unisolated writes.

Only after this synthesis, inspect implementation and caller contracts to locate the cause of material findings. Agreement from reviewers using the [Panel](../../../../coordinate/capabilities/methods/panel.md) method supports a usability conclusion, not a source-level diagnosis. Repair reproducible problems and give fresh reviewers new cold contexts for the final pass. Keep rounds bounded: if material confusion remains, report the remaining evidence and limit rather than declaring success.
