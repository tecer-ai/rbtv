# Hypresent — Compounding Learnings (T21)

Lessons that generalize beyond hypresent. All product code was authored by the `kimi` CLI driven by orchestration agents; these are the orchestration- and process-level takeaways.

## Kimi headless orchestration

1. **Small, focused, fully self-contained prompts win.** Every accepted kimi run was scope-locked to one module with its contract, spec sections, namespacing mandate, and acceptance inlined. Kimi is a non-reasoning executor — it does not resolve ambiguity, so the prompt must carry every decision.
2. **Make kimi read its own contract.** Pointing the prompt at the authoritative `04` row + named `01`/`02`/`03` sections (rather than paraphrasing them) kept output aligned with the locked spec.
3. **Sub-agent Bash shells detach from long kimi runs.** Build-lead sub-agents repeatedly returned mid-flight because kimi runs exceeding ~10 min detach from the sub-agent's shell. Fix: run long kimi calls as orchestrator-level background processes, not inside a sub-agent's foreground Bash. This is the single biggest workflow lesson.
4. **Confinement is the caller's job.** Headless kimi auto-approves every tool call with no native allowlist; the only reliable write gate is a post-run `git diff` against the task's declared file list.

## Process & verification

5. **Adversarial spec review pays for itself before any code exists.** The pre-build review caught an UNIMPLEMENTABLE contract — "DOMPurify keeps the document's own scripts and strips injected ones" is impossible (DOMPurify has no provenance signal). Catching it pre-build avoided shipping a serializer that could never satisfy its own spec. Resolution: strip-only-by-namespace.
6. **Strip-only-by-namespace is the coexistence pattern.** Removing ONLY `hyp-`-prefixed nodes/attrs/classes + injected inline styles (and re-embedding one inert JSON island) lets the editor's chrome leave cleanly while the user's own scripts/SVG/`data-*` survive by simply not being touched. No sanitizer pass needed.
7. **Checkpoint browser verification catches what code-level checks cannot.** `node --check` and HTTP probes passed on every foundation task, yet real-browser checkpoints surfaced 6 integration bugs: 3 boot-wiring gaps (foundation-smoke), the serializer TreeWalker off-by-one (CP1), and the comment-island off-by-one + color-popover panel-wipe + font-size nesting (CP2). Static checks verify shape; only the browser verifies behavior.
8. **`node --check` does NOT catch ESM duplicate-identifier errors.** A duplicate `threads` declaration parsed clean under CommonJS `node --check` but threw a SyntaxError that killed the entire runtime module graph at browser ESM load. Lesson: parse runtime ES modules as ESM (e.g. `node --check` on a `.mjs`, or an ESM-aware linter) — a CJS syntax check is not sufficient for `type="module"` code.
9. **Node-count guards are correct but unforgiving — get the count math exactly right.** The serializer's integrity guard (pre/post node delta must equal removed chrome + re-embedded island) twice returned `null` from off-by-one counting (TreeWalker excluding subtree roots; island counted as 1 node when it is 2). The guard did its job — it refused to emit a file it couldn't prove safe — but the lesson is that any node-counting invariant must account for subtree roots and multi-node inserts.
10. **Record file-layout deviations, do not silently absorb them.** The planned `toolbar.js` / `comment-panel.js` / `outline.js` shell modules were consolidated into `main.js`; the build log notes each deviation so the docs match reality.
