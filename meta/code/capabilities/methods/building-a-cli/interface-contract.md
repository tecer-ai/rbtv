# CLI interface contract

Use this contract to design or review a command-line interface (CLI) that a person or agent can understand from the installed command alone. Apply each item to the relevant command; record “not applicable” with a reason rather than adding a feature just to satisfy a list. Product vocabulary and existing callers decide the actual command names, hierarchy, formats, and exit numbers.

## Inventory the complete surface

Record every root command, group, leaf, alias, positional, and option. For each argument and option, specify:

- Meaning, type, accepted literal values and what each value does; for dynamic values, the discovery command and constraints; whether required, optional, or repeatable.
- Default and omitted behavior; if repeated or comma-separated values are accepted, whether later values replace or append.
- Ranges, empty values, quoting/path expectations, and which combinations are valid or refused.
- Precedence among command arguments, environment, saved settings, and discovery; the selected context or target made visible when relevant.
- Read versus write effects, external requests, setup needs, confirmation and preview semantics, files or shared resources touched, and whether prompts can occur.
- Text and structured outputs, standard output versus standard error, empty/error results, and exit status meaning.
- Existing callers, including scripts, agent instructions, and parsers of structured output.

Use a coverage matrix with a row per documented command path and columns for help positions, argument/value classes, ordinary/empty/failure output, structured mode, mutation, and applicable contexts. A command group has its own row. Pairwise or risk-based tests cover interacting options; a full cross-product is rarely useful. A coverage cell marked “not applicable” needs the reason.

## Verbs, arguments, flags and options

Every word after the program name is one of four kinds. Name the kind of each word in the inventory, and give it the form of its kind.

- **Verb** (subcommand; a leaf or a group in the inventory): picks the action. A bare word, before any argument: `list` in `cast list`. A group is a verb that holds verbs: `agent` in `rbtv agent list`.
- **Argument** (positional): the thing the action applies to. A bare value whose position gives it its meaning: `scout` in `spark list scout`.
- **Flag**: a switch that changes how the action runs and takes no value: `--json`, `--dry-run`.
- **Option**: a flag that takes one value: `--target FOLDER`. The value is required. An option whose value may be left out makes the next word ambiguous, so "all" and "one" are two words: a flag and an option (`--agents`, `--agent NAME`).

A flag or an option is written in the form almost every command-line tool uses, the POSIX short form and the GNU long form:

- **Long form: two dashes and a whole word**, with a hyphen between words: `--json`, `--dry-run`, `--target FOLDER`.
- **Short form: one dash and ONE letter**: `-h`, `-p TEXT`. Use it only for what is typed often.
- **NEVER a whole word after one dash** (`-models`). Under the standard it reads as several one-letter flags written together (`-m -o -d -e -l -s`), and a parser or a reader that follows the standard takes it that way.
- `--` alone ends the flags and options: every word after it is an argument, even one that starts with a dash.
- A long name is lowercase. A short form is one letter, in either case (`-s`, `-S`, `-A`). One name means one thing on every verb of the tool.

When a tool being created or edited holds a form outside this standard, record it in the inventory as nonconforming, with its callers. A new or changed word takes the standard form. Changing a form that callers already use breaks them, so it is an owner decision, made with the list of callers.

## Cover every result, not only help

A command is used for what it prints when it runs, not only for its help. Alongside the coverage matrix, keep a separate finite result matrix: one row per verb — a leaf command that performs one operation — or per group of verbs sharing a result shape, and one column per outcome class. Read verbs cover success and a valid empty result. Mutation verbs cover success, no-op, and dry-run or preview where the product offers it. Any verb can meet partial completion, refusal, and failure. Each applicable cell specifies:

- The selected target and the exact identifiers the result names, so a reader can tell what was acted on.
- Summary, details, and recovery: what happened or would happen, where to see more, and the next step; a refusal or failure adds a concrete recovery route.
- The stream that carries it (standard output or standard error) and the exit status.
- Rendered forms: normal and narrow width, no-color, and redirected output.
- The structured value for that outcome, covering structured success and structured failure where a structured mode exists.

A cell marked “not applicable” needs the reason. The matrix demands coverage of what the product already does; it never mandates a new feature, an outcome the product cannot produce, or a universal structured envelope. An interactive command’s settled result — what it shows once its interaction completes — is in scope; the route through prompts may stay interactive.

## Help is a working interface

Design help to work at every command depth: root, groups, and leaves. Support `-h` and `--help` before and after command tokens, global options, and positionals wherever those tokens are options. A request for help succeeds without required arguments, credentials, saved configuration, network, or side effects, and shows the deepest command context the parser can identify. Define how ambiguous help mixed with an invalid token is resolved, then implement and test that policy. Respect the `--` option terminator and literal values such as `--name=-h`; raw token scanning that mistakes values for help breaks commands.

Root help lets a newcomer find command groups and first-use steps. Group help lists every child and the purpose of each. A usage form appears only in the help of the command it invokes: root and group help point to each child's own help for its usage. A root or group that does work when run without a child shows the usage of that form, and no other. A usage form is a line that spells out a command's options and arguments. A child's entry in the list may show that child's positional arguments, never its options. An example, a next step or a recovery command that names another command is not a usage form. Leaf help includes, where relevant:

- Purpose and complete usage forms, including aliases or alternate forms that actually work.
- Every positional and option at the point of use; accepted values with short meanings, defaults, omission and replace/append behavior, and meaningful ranges.
- Selection scope and filter combinations; exact addressing versus broad discovery where the product offers both.
- Target/context precedence, setup and authentication needed for execution (not for help), read/write effects, preview, confirmation, and interactive behavior.
- Text and structured formats, output streams, errors and exit statuses, plus a realistic example and the next related command when helpful.

Concise shared explanations can be linked or named consistently, but a leaf must still explain enough to choose its arguments. Do not put unexplained internal labels in help or errors. Verify help against the actual parser, not only a hand-authored manual.

## Address and resolve things honestly

When a product has a hierarchy, show its real levels and let a named scope stay within them. Exact names or identifiers must never silently broaden into description search. Give broad discovery its own explicit route where useful. Resolve a short name only when unique; ambiguity refuses action and shows copyable choices. Preserve stable full identifiers in results, errors, and follow-up commands. An explicit filter must apply inside the selected scope and must not be silently ignored at a different depth. Use one public term for the same classification across help, tables, errors, and structured fields.

Distinguish a source catalog from a selected target and a saved selection from checked file or service health. Name where a check ran: selected target, local source, shared command path, or external service. A global `PATH` check (the shell's command lookup order) can matter to a target when it determines which command runs; label its scope instead of removing it for being outside the target folder.

## Default text and structured output

Default text is readable to people and agents without a special pretty flag. Terminal output is plain text: Markdown table pipes or headings will not render as a page. Use a short command title and whitespace between sections or consecutive command results, with compact aligned tables when they aid scanning. Keep full copyable identifiers, item type and state; shorten descriptions first. At narrow widths, switch to labeled per-item blocks if essential columns cannot fit. A list that shortens a description takes the flag `--full`: it shows every description whole, as labeled per-item blocks when a table cannot hold them, and its structured value carries the whole text too. When the list shortened something, a line under it names `--full`. `--full` means only this, on every tool. Never split or truncate an identifier. Avoid decorative lines that consume space without carrying information.

A bulk result — one command acting on many items — leads with its outcome: success, partial success, or failure, with the counts behind it: changed, unchanged, failed. Warnings and partial-success conditions stay in that leading summary, never demoted behind a detail view; complete per-item detail remains reachable in the same result or through a stated follow-up where the product offers one. Choose the split deliberately for the product's jobs: a compact summary with details accessible is one valid shape, not a flag every command must offer.

Color is optional emphasis, never the sole state signal. Honor `NO_COLOR` and redirected output. Use deterministic ordering, a bounded default for collections, and a real continuation mechanism such as cursor or offset. State the limit and next page in usable terms. An empty collection succeeds when it is a valid result; label it clearly and distinguish it from a failed query.

In structured mode, emit exactly one documented, stable, undecorated value on standard output for success **and** failure; a failure also exits nonzero. Define the product's success/error fields, field meanings, null/absence behavior, and exit numbers without assuming a universal envelope. Keep titles, colors, extra prose, and progress out of that value. Put diagnostics and progress on standard error without duplicating the structured failure there. Keep secrets out of both streams, including error and raw-response paths. When authentication is needed, prefer standard environment, configuration, or provider mechanisms to token arguments that appear in shell history. If a command creates a file, return a usable file path and relevant outcome details in structured mode where those are part of the job.

Human-readable errors state the attempted action and scope, the reason for refusal or failure, whether anything changed, and a concrete recovery command when the context makes one certain. Preserve exact quoted identifiers; otherwise point to discovery or help rather than inventing an identifier.

## One operation for all users

Every human or agent control for an action must reach the same underlying operation: interactive and noninteractive terminal modes, graphical controls, and agent tools may present it differently, but cannot keep separate state-changing logic. An agent must be able to discover and perform the same relevant actions a human can without driving a graphical interface when a direct tool route is feasible. Noninteractive calls must not unexpectedly prompt; required choices become explicit arguments or a clear refusal. Define write boundaries for every route, including an optional raw command. Preview and dry-run outputs state what would happen and cannot claim a write happened.

Prefer narrow, composable operations for repeated jobs, exact reads after discovery, stable IDs, bounded listing, and named writes. Include only operations the product needs. Setup, health checks, raw escape hatches, authentication storage, and companion agent instructions are conditional features, not a fixed CLI skeleton.
