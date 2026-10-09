# Reviewing for over-engineering

The result: a list of what to cut from the code in scope, one line per finding with its location, what to cut and what replaces it, closing with the net lines possible. Nothing is applied; the user decides what to cut.

Inputs: the scope, which is one of two. A diff: the change under review, or the working tree against a base the user names. A whole tree: a repository or a folder. When the user names neither, review the uncommitted change; when there is none, ask which tree to review.

The judgment covers over-engineering and complexity only. A correctness bug, a security hole or a performance problem is out of scope: name it in one closing line for a normal review pass, without a finding. A single smoke test or `assert`-based self-check is the minimum the coding skill requires, never bloat; do not flag it.

## Hunt

Read the code in scope whole before judging; a finding on a function whose callers you did not read is a guess. Look for: a dependency the standard library or the platform already ships; a hand-rolled version of a standard-library function; an interface with one implementation; a factory with one product; a wrapper that only delegates; a file exporting one thing; a layer with one caller; configuration nobody sets; a dead flag; a speculative feature; dead code; a loop or block that a shorter form writes.

## Tags

Each finding carries one tag:

| Tag | What it marks | Replacement |
|---|---|---|
| `delete` | dead code, unused flexibility, a speculative feature | nothing |
| `stdlib` | a hand-rolled thing the standard library ships | the function, named |
| `native` | a dependency or code doing what the platform already does | the feature, named |
| `yagni` | an abstraction with one implementation, configuration nobody sets, a layer with one caller | inline it until a second case exists |
| `shrink` | the same logic in fewer lines | the shorter form, shown |

## Output

One line per finding:

- For a diff: `L<line>: <tag>: <what>. <replacement>.`, or `<file>:L<line>: <tag>: <what>. <replacement>.` when the diff spans files, in file order.
- For a whole tree: `<tag>: <what to cut>. <replacement>. [<path>]`, ranked with the biggest cut first.

A finding names the location, what is wrong there in a few words and the replacement. A sentence that hedges ("this class might be more complex than necessary; have you considered whether all these rules are needed?") is not a finding. For example: `L12-38: stdlib: 27-line validator class. "@" in email, 1 line; real validation is the confirmation mail.`

Close with `net: -<N> lines possible.` for a diff, or `net: -<N> lines, -<M> deps possible.` for a whole tree. When there is nothing to cut, write `Lean already. Ship.` and stop.
